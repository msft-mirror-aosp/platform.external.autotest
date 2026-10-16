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

    Stubbing only autotest_lib.server.utils (rather than autotest_lib.server)
    keeps the real autotest_lib.server.subcommand importable when tests call
    PackageManager.upload_pkg(). mock.patch.dict restores sys.modules on exit
    so the stub does not leak into other tests.
    """
    try:
        from autotest_lib.utils import packager
        return packager
    except TypeError:
        with mock.patch.dict(sys.modules,
                             {'autotest_lib.server.utils': mock.MagicMock()}):
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
        if cmd.startswith('md5sum '):
            path = cmd[len('md5sum '):].strip()
            digest = 'md5-' + os.path.basename(path)
            return utils.CmdResult(command=cmd,
                                   stdout='%s  %s\n' % (digest, path),
                                   exit_status=0)
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

    def test_tar_packages_excludes_and_dual_publishes_both_formats(self):
        """tar_packages builds both .tar.zst and .tar.bz2 and excludes both."""
        dep_dir = os.path.join(self.temp_dir, 'deps')
        os.makedirs(os.path.join(dep_dir, 'foo'))
        pm = self._make_pkgmgr()
        seen_calls = []

        def fake_tar(pkg_name, src_dir, dest_dir, exclude_string=None):
            seen_calls.append((pkg_name, exclude_string))
            return os.path.join(dest_dir, pkg_name)

        pm.tar_package = fake_tar
        tarballs = packager.tar_packages(pm, 'dep', 'foo', dep_dir,
                                         self.temp_dir)
        self.assertEqual([os.path.basename(p) for p in tarballs],
                         ['dep-foo.tar.zst', 'dep-foo.tar.bz2'])
        self.assertEqual(len(seen_calls), 2)
        for _, exclude_string in seen_calls:
            self.assertIn('--exclude="**dep-foo.tar.bz2"', exclude_string)
            self.assertIn('--exclude="**dep-foo.tar.bz2.checksum"',
                          exclude_string)
            self.assertIn('--exclude="**dep-foo.tar.zst"', exclude_string)
            self.assertIn('--exclude="**dep-foo.tar.zst.checksum"',
                          exclude_string)

    def test_process_packages_upload_dual_publishes_both_formats(self):
        """ACTION_UPLOAD tars and uploads both .tar.zst and .tar.bz2."""
        dep_dir = os.path.join(self.temp_dir, 'deps')
        os.makedirs(os.path.join(dep_dir, 'foo'))
        repo_dir = os.path.join(self.temp_dir, 'repo')
        os.makedirs(repo_dir)
        pm = self._make_pkgmgr(upload_paths=[repo_dir])

        temp_snapshots = []

        def fake_tar(pkg_name, src_dir, dest_dir, exclude_string=None):
            # Each earlier format's temp tarball must already be deleted before
            # the next format is built in dest_dir.
            temp_snapshots.append(sorted(os.listdir(dest_dir)))
            out = os.path.join(dest_dir, pkg_name)
            with open(out, 'w') as f:
                f.write('payload-' + pkg_name)
            return out

        pm.tar_package = fake_tar
        with mock.patch.object(packages, 'check_diskspace'), \
                mock.patch.object(pm, 'upload_pkg',
                                  wraps=pm.upload_pkg) as mock_upload, \
                mock.patch.object(packager.shutil,
                                  'rmtree',
                                  wraps=packager.shutil.rmtree) as mock_rmtree:
            packager.process_packages(pm,
                                      'dep',
                                      'foo',
                                      dep_dir,
                                      action=packager.ACTION_UPLOAD)

        self.assertEqual(temp_snapshots, [[], []])
        mock_rmtree.assert_called_once()
        mock_upload.assert_has_calls([
                mock.call(mock.ANY, update_checksum=True),
                mock.call(mock.ANY, update_checksum=True),
        ])
        for call in mock_upload.call_args_list:
            self.assertFalse(os.path.exists(call[0][0]))
        self.assertEqual([
                os.path.basename(c[0][0]) for c in mock_upload.call_args_list
        ], ['dep-foo.tar.zst', 'dep-foo.tar.bz2'])
        self.assertTrue(
                os.path.isfile(os.path.join(repo_dir, 'dep-foo.tar.zst')))
        self.assertTrue(
                os.path.isfile(os.path.join(repo_dir, 'dep-foo.tar.bz2')))
        with open(os.path.join(repo_dir, packages.CHECKSUM_FILE)) as f:
            checksum_contents = f.read()
        self.assertIn('md5-dep-foo.tar.zst dep-foo.tar.zst', checksum_contents)
        self.assertIn('md5-dep-foo.tar.bz2 dep-foo.tar.bz2', checksum_contents)

    def test_tar_packages_single_preexisting_format_rebuilds_both(self):
        """tar_packages rebuilds both formats if only one exists in pkg_dir."""
        dep_dir = os.path.join(self.temp_dir, 'deps')
        pkg_dir = os.path.join(dep_dir, 'foo')
        os.makedirs(pkg_dir)
        with open(os.path.join(pkg_dir, 'dep-foo.tar.bz2'), 'w') as f:
            f.write('stale-bz2')

        pm = self._make_pkgmgr()
        tarred = []

        def fake_tar(pkg_name, src_dir, dest_dir, exclude_string=None):
            tarred.append(pkg_name)
            out = os.path.join(dest_dir, pkg_name)
            with open(out, 'w') as f:
                f.write('fresh-' + pkg_name)
            return out

        pm.tar_package = fake_tar
        out_dir = os.path.join(self.temp_dir, 'tar_out')
        os.makedirs(out_dir)
        tarballs = packager.tar_packages(pm, 'dep', 'foo', dep_dir, out_dir)
        self.assertEqual(tarred, ['dep-foo.tar.zst', 'dep-foo.tar.bz2'])
        self.assertTrue(all(p.startswith(out_dir) for p in tarballs))

    def test_process_packages_upload_single_preexisting_format_rebuilds_both(
            self):
        """ACTION_UPLOAD rebuilds and uploads both if only one exists."""
        dep_dir = os.path.join(self.temp_dir, 'deps')
        pkg_dir = os.path.join(dep_dir, 'foo')
        os.makedirs(pkg_dir)
        stale_bz2 = os.path.join(pkg_dir, 'dep-foo.tar.bz2')
        with open(stale_bz2, 'w') as f:
            f.write('stale-bz2')

        repo_dir = os.path.join(self.temp_dir, 'repo')
        os.makedirs(repo_dir)
        pm = self._make_pkgmgr(upload_paths=[repo_dir])
        tarred = []

        def fake_tar(pkg_name, src_dir, dest_dir, exclude_string=None):
            tarred.append(pkg_name)
            out = os.path.join(dest_dir, pkg_name)
            with open(out, 'w') as f:
                f.write('fresh-' + pkg_name)
            return out

        pm.tar_package = fake_tar
        with mock.patch.object(packages, 'check_diskspace'):
            packager.process_packages(pm,
                                      'dep',
                                      'foo',
                                      dep_dir,
                                      action=packager.ACTION_UPLOAD)

        self.assertEqual(tarred, ['dep-foo.tar.zst', 'dep-foo.tar.bz2'])
        with open(os.path.join(repo_dir, 'dep-foo.tar.bz2')) as f:
            self.assertEqual(f.read(), 'fresh-dep-foo.tar.bz2')
        with open(os.path.join(repo_dir, 'dep-foo.tar.zst')) as f:
            self.assertEqual(f.read(), 'fresh-dep-foo.tar.zst')
        self.assertTrue(os.path.isfile(stale_bz2))

    def test_preexisting_all_formats_reuses_both_and_preserves_pkg_dir(self):
        """When all formats pre-exist in pkg_dir, both are reused and kept."""
        dep_dir = os.path.join(self.temp_dir, 'deps')
        pkg_dir = os.path.join(dep_dir, 'foo')
        os.makedirs(pkg_dir)
        prebuilt_zst = os.path.join(pkg_dir, 'dep-foo.tar.zst')
        prebuilt_bz2 = os.path.join(pkg_dir, 'dep-foo.tar.bz2')
        with open(prebuilt_zst, 'w') as f:
            f.write('prebuilt-zst')
        with open(prebuilt_bz2, 'w') as f:
            f.write('prebuilt-bz2')

        repo_dir = os.path.join(self.temp_dir, 'repo')
        os.makedirs(repo_dir)
        pm = self._make_pkgmgr(upload_paths=[repo_dir])
        pm.tar_package = mock.Mock(
                side_effect=AssertionError('tar_package should not be called'))

        out_dir = os.path.join(self.temp_dir, 'tar_out')
        os.makedirs(out_dir)
        reused = packager.tar_packages(pm, 'dep', 'foo', dep_dir, out_dir)
        self.assertEqual(reused, [prebuilt_zst, prebuilt_bz2])
        pm.tar_package.assert_not_called()

        with mock.patch.object(packages, 'check_diskspace'):
            packager.process_packages(pm,
                                      'dep',
                                      'foo',
                                      dep_dir,
                                      action=packager.ACTION_UPLOAD)
        pm.tar_package.assert_not_called()
        # Pre-existing files in pkg_dir must not be deleted by ACTION_UPLOAD.
        self.assertTrue(os.path.isfile(prebuilt_zst))
        self.assertTrue(os.path.isfile(prebuilt_bz2))
        with open(os.path.join(repo_dir, 'dep-foo.tar.zst')) as f:
            self.assertEqual(f.read(), 'prebuilt-zst')
        with open(os.path.join(repo_dir, 'dep-foo.tar.bz2')) as f:
            self.assertEqual(f.read(), 'prebuilt-bz2')

    def test_process_packages_upload_skips_unchanged_format_only(self):
        """ACTION_UPLOAD uploads only the format whose checksum changed."""
        dep_dir = os.path.join(self.temp_dir, 'deps')
        os.makedirs(os.path.join(dep_dir, 'foo'))
        repo_dir = os.path.join(self.temp_dir, 'repo')
        os.makedirs(repo_dir)
        pm = self._make_pkgmgr(upload_paths=[repo_dir])

        def fake_tar(pkg_name, src_dir, dest_dir, exclude_string=None):
            out = os.path.join(dest_dir, pkg_name)
            with open(out, 'w') as f:
                f.write('payload-' + pkg_name)
            return out

        pm.tar_package = fake_tar
        pm._checksum_dict = {'dep-foo.tar.zst': 'md5-dep-foo.tar.zst'}

        with mock.patch.object(packages, 'check_diskspace'), \
                mock.patch.object(pm, 'upload_pkg',
                                  wraps=pm.upload_pkg) as mock_upload:
            packager.process_packages(pm,
                                      'dep',
                                      'foo',
                                      dep_dir,
                                      action=packager.ACTION_UPLOAD)

        self.assertEqual(mock_upload.call_count, 1)
        self.assertEqual(os.path.basename(mock_upload.call_args[0][0]),
                         'dep-foo.tar.bz2')

    def test_process_packages_upload_propagates_packaging_error(self):
        """ACTION_UPLOAD fails hard if tar_package raises PackagingError."""
        dep_dir = os.path.join(self.temp_dir, 'deps')
        os.makedirs(os.path.join(dep_dir, 'foo'))
        repo_dir = os.path.join(self.temp_dir, 'repo')
        os.makedirs(repo_dir)
        pm = self._make_pkgmgr(upload_paths=[repo_dir])
        pm.tar_package = mock.Mock(
                side_effect=error.PackagingError('zstd missing'))

        with mock.patch.object(packages, 'check_diskspace'):
            with self.assertRaises(error.PackagingError):
                packager.process_packages(pm,
                                          'dep',
                                          'foo',
                                          dep_dir,
                                          action=packager.ACTION_UPLOAD)

    def test_published_tarball_suffixes_controls_what_is_built(self):
        """PUBLISHED_TARBALL_SUFFIXES limits built formats, excluding all."""
        dep_dir = os.path.join(self.temp_dir, 'deps')
        os.makedirs(os.path.join(dep_dir, 'foo'))
        pm = self._make_pkgmgr()
        seen_calls = []

        def fake_tar(pkg_name, src_dir, dest_dir, exclude_string=None):
            seen_calls.append((pkg_name, exclude_string))
            return os.path.join(dest_dir, pkg_name)

        pm.tar_package = fake_tar
        with mock.patch.object(packages, 'PUBLISHED_TARBALL_SUFFIXES',
                               (packages.ZSTD_TARBALL_SUFFIX, )):
            tarballs = packager.tar_packages(pm, 'dep', 'foo', dep_dir,
                                             self.temp_dir)
        self.assertEqual([os.path.basename(p) for p in tarballs],
                         ['dep-foo.tar.zst'])
        self.assertEqual(len(seen_calls), 1)
        self.assertIn('--exclude="**dep-foo.tar.bz2"', seen_calls[0][1])
        self.assertIn('--exclude="**dep-foo.tar.zst"', seen_calls[0][1])

    def test_process_packages_tar_only_dual_publishes_both_formats(self):
        """ACTION_TAR_ONLY writes tarballs and .checksums for both formats."""
        dep_dir = os.path.join(self.temp_dir, 'deps')
        os.makedirs(os.path.join(dep_dir, 'foo'))
        dest_dir = os.path.join(self.temp_dir, 'out')
        build_dir = os.path.join(dest_dir, 'client', 'deps', 'foo')
        os.makedirs(build_dir)
        pm = self._make_pkgmgr()

        def fake_tar(pkg_name, src_dir, out_dir, exclude_string=None):
            out = os.path.join(out_dir, pkg_name)
            with open(out, 'w') as f:
                f.write('payload-' + pkg_name)
            return out

        pm.tar_package = fake_tar
        pm.compute_checksum = lambda path: 'md5-' + os.path.basename(path)

        with mock.patch.object(packages, 'check_diskspace'):
            packager.process_packages(pm,
                                      'dep',
                                      'foo',
                                      dep_dir,
                                      action=packager.ACTION_TAR_ONLY,
                                      dest_dir=dest_dir)

        for pkg_name in ('dep-foo.tar.zst', 'dep-foo.tar.bz2'):
            self.assertTrue(os.path.isfile(os.path.join(build_dir, pkg_name)))
            checksum_path = os.path.join(build_dir, pkg_name + '.checksum')
            self.assertTrue(os.path.isfile(checksum_path))
            with open(checksum_path) as f:
                self.assertEqual(f.read(), 'md5-' + pkg_name)


if __name__ == '__main__':
    unittest.main()
