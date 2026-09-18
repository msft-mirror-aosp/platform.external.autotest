#!/usr/bin/python3
# Lint as: python3
# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Unit tests for utils/packager.py."""

import os
import re
import shutil
import sys
import tempfile
import unittest
from unittest import mock

import common
from autotest_lib.client.common_lib import error
from autotest_lib.client.common_lib import packages
from autotest_lib.client.common_lib import utils


def _import_packager():
    """Imports utils.packager, stubbing server.utils if protobuf >= 4.

    Note: mock.patch.dict restores sys.modules on exit so the fake
    autotest_lib.server entry does not leak into other tests; this removes
    autotest_lib.utils.packager from sys.modules as well while keeping the
    returned module object bound to `packager` below.
    """
    try:
        from autotest_lib.utils import packager
        return packager
    except TypeError:
        with mock.patch.dict(sys.modules,
                             {'autotest_lib.server': mock.MagicMock()}):
            from autotest_lib.utils import packager
            return packager


packager = _import_packager()


class PackagerActionTests(unittest.TestCase):
    """Tests for utils/packager.py remove and exclude behavior."""

    def setUp(self):
        super().setUp()
        self.temp_dir = tempfile.mkdtemp(prefix='packager_unittest_')
        self.addCleanup(shutil.rmtree, self.temp_dir, ignore_errors=True)
        self.existing_files = {}

    def _fake_run(self, cmd, *_args, **_dargs):
        """Simulates shell commands issued by PackageManager during remove."""
        if cmd.startswith('test -e '):
            path = cmd[len('test -e '):].strip()
            if path in self.existing_files or os.path.exists(path):
                return utils.CmdResult(command=cmd, exit_status=0)
            raise error.CmdError(cmd,
                                 utils.CmdResult(command=cmd, exit_status=1))
        if cmd.startswith('echo '):
            match = re.match(r'^echo "(.*)" > (\S+)\s*$', cmd, re.DOTALL)
            if match:
                content, path = match.groups()
                self.existing_files[path] = content + '\n'
                if os.path.isdir(os.path.dirname(path)):
                    with open(path, 'w') as f:
                        f.write(content + '\n')
            return utils.CmdResult(command=cmd, stdout='', exit_status=0)
        if cmd.startswith('cat '):
            path = cmd[len('cat '):].strip()
            if path in self.existing_files:
                return utils.CmdResult(command=cmd,
                                       stdout=self.existing_files[path],
                                       exit_status=0)
            if os.path.isfile(path):
                with open(path, 'r') as f:
                    return utils.CmdResult(command=cmd,
                                           stdout=f.read(),
                                           exit_status=0)
            raise error.CmdError(cmd,
                                 utils.CmdResult(command=cmd, exit_status=1))
        return utils.CmdResult(command=cmd, stdout='', exit_status=0)

    def _make_pkgmgr(self, upload_paths=None):
        """Constructs a PackageManager backed by self._fake_run."""
        return packages.PackageManager(self.temp_dir,
                                       upload_paths=upload_paths,
                                       do_locking=False,
                                       run_function=self._fake_run)

    def test_process_packages_remove_zst_only(self):
        """ACTION_REMOVE removes a .tar.zst package when .tar.bz2 is absent."""
        repo_dir = os.path.join(self.temp_dir, 'repo')
        os.makedirs(repo_dir)
        zst_file = os.path.join(repo_dir, 'dep-foo.tar.zst')
        with open(zst_file, 'w') as f:
            f.write('zst')

        pm = self._make_pkgmgr(upload_paths=[repo_dir])
        pm._checksum_dict = {
                'dep-foo.tar.zst': '1111',
                'dep-keep.tar.bz2': '2222',
        }
        packager.process_packages(pm,
                                  'dep',
                                  'foo',
                                  self.temp_dir,
                                  action=packager.ACTION_REMOVE)
        self.assertFalse(os.path.exists(zst_file))
        repo_checksum = os.path.join(repo_dir, packages.CHECKSUM_FILE)
        self.assertTrue(os.path.isfile(repo_checksum))
        with open(repo_checksum, 'r') as f:
            contents = f.read()
        self.assertNotIn('dep-foo.tar.zst', contents)
        self.assertIn('2222 dep-keep.tar.bz2', contents)

    def test_process_packages_remove_both_formats(self):
        """ACTION_REMOVE removes both .tar.bz2 and .tar.zst when present."""
        repo_dir = os.path.join(self.temp_dir, 'repo')
        os.makedirs(repo_dir)
        for name in ('dep-foo.tar.bz2', 'dep-foo.tar.zst'):
            with open(os.path.join(repo_dir, name), 'w') as f:
                f.write('data')

        pm = self._make_pkgmgr(upload_paths=[repo_dir])
        packager.process_packages(pm,
                                  'dep',
                                  'foo',
                                  self.temp_dir,
                                  action=packager.ACTION_REMOVE)
        self.assertFalse(
                os.path.exists(os.path.join(repo_dir, 'dep-foo.tar.bz2')))
        self.assertFalse(
                os.path.exists(os.path.join(repo_dir, 'dep-foo.tar.zst')))
        self.assertTrue(
                os.path.isfile(os.path.join(repo_dir, packages.CHECKSUM_FILE)))

    def test_process_packages_remove_neither_present_names_all_candidates(
            self):
        """ACTION_REMOVE raises PackageRemoveError naming every candidate."""
        repo_dir = os.path.join(self.temp_dir, 'repo')
        os.makedirs(repo_dir)
        pm = self._make_pkgmgr(upload_paths=[repo_dir])
        with self.assertRaises(error.PackageRemoveError) as ctx:
            packager.process_packages(pm,
                                      'dep',
                                      'foo',
                                      self.temp_dir,
                                      action=packager.ACTION_REMOVE)
        self.assertIn('dep-foo.tar.bz2', str(ctx.exception))
        self.assertIn('dep-foo.tar.zst', str(ctx.exception))

    def test_tar_packages_excludes_both_formats(self):
        """tar_packages excludes pre-existing .tar.bz2 and .tar.zst files."""
        dep_dir = os.path.join(self.temp_dir, 'deps')
        os.makedirs(os.path.join(dep_dir, 'foo'))
        pm = self._make_pkgmgr()
        seen_excludes = []

        def fake_tar(pkg_name, src_dir, dest_dir, exclude_string=None):
            seen_excludes.append(exclude_string)
            return os.path.join(dest_dir, pkg_name)

        pm.tar_package = fake_tar
        packager.tar_packages(pm, 'dep', 'foo', dep_dir, self.temp_dir)
        self.assertEqual(len(seen_excludes), 1)
        self.assertIn('--exclude="**dep-foo.tar.bz2"', seen_excludes[0])
        self.assertIn('--exclude="**dep-foo.tar.bz2.checksum"',
                      seen_excludes[0])
        self.assertIn('--exclude="**dep-foo.tar.zst"', seen_excludes[0])
        self.assertIn('--exclude="**dep-foo.tar.zst.checksum"',
                      seen_excludes[0])


if __name__ == '__main__':
    unittest.main()
