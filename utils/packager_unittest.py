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
    """Tests for utils/packager.py upload, tar_only, remove, and exclude."""

    def setUp(self):
        super().setUp()
        self.temp_dir = tempfile.mkdtemp(prefix='packager_unittest_')
        self.addCleanup(shutil.rmtree, self.temp_dir, ignore_errors=True)
        self.existing_files = {}

    def _fake_run(self, cmd, *_args, **_dargs):
        """Simulates shell commands issued by PackageManager."""
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

    def test_tar_packages_publishes_zstd_only_and_excludes_both_formats(self):
        """tar_packages builds only .tar.zst while still excluding both."""
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
                         ['dep-foo.tar.zst'])
        self.assertEqual(len(seen_calls), 1)
        exclude_string = seen_calls[0][1]
        self.assertIn('--exclude="**dep-foo.tar.bz2"', exclude_string)
        self.assertIn('--exclude="**dep-foo.tar.bz2.checksum"', exclude_string)
        self.assertIn('--exclude="**dep-foo.tar.zst"', exclude_string)
        self.assertIn('--exclude="**dep-foo.tar.zst.checksum"', exclude_string)

    def test_process_packages_upload_publishes_zstd_only(self):
        """ACTION_UPLOAD tars and uploads only .tar.zst."""
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

        mock_rmtree.assert_called_once()
        mock_upload.assert_called_once_with(mock.ANY, update_checksum=True)
        uploaded_temp = mock_upload.call_args[0][0]
        self.assertFalse(os.path.exists(uploaded_temp))
        self.assertEqual(os.path.basename(uploaded_temp), 'dep-foo.tar.zst')
        self.assertTrue(
                os.path.isfile(os.path.join(repo_dir, 'dep-foo.tar.zst')))
        self.assertFalse(
                os.path.exists(os.path.join(repo_dir, 'dep-foo.tar.bz2')))
        with open(os.path.join(repo_dir, packages.CHECKSUM_FILE)) as f:
            checksum_contents = f.read()
        self.assertIn('md5-dep-foo.tar.zst dep-foo.tar.zst', checksum_contents)
        self.assertNotIn('dep-foo.tar.bz2', checksum_contents)

    def test_stale_preexisting_bz2_builds_fresh_zst_and_preserves_pkg_dir(
            self):
        """A stale .tar.bz2 in pkg_dir is ignored and not deleted."""
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
        out_dir = os.path.join(self.temp_dir, 'tar_out')
        os.makedirs(out_dir)
        tarballs = packager.tar_packages(pm, 'dep', 'foo', dep_dir, out_dir)
        self.assertEqual(tarred, ['dep-foo.tar.zst'])
        self.assertEqual(tarballs, [os.path.join(out_dir, 'dep-foo.tar.zst')])

        tarred.clear()
        with mock.patch.object(packages, 'check_diskspace'):
            packager.process_packages(pm,
                                      'dep',
                                      'foo',
                                      dep_dir,
                                      action=packager.ACTION_UPLOAD)

        self.assertEqual(tarred, ['dep-foo.tar.zst'])
        with open(os.path.join(repo_dir, 'dep-foo.tar.zst')) as f:
            self.assertEqual(f.read(), 'fresh-dep-foo.tar.zst')
        self.assertFalse(
                os.path.exists(os.path.join(repo_dir, 'dep-foo.tar.bz2')))
        self.assertTrue(os.path.isfile(stale_bz2))

    def test_preexisting_zst_reuses_and_preserves_pkg_dir(self):
        """A pre-existing .tar.zst in pkg_dir is reused and not deleted."""
        dep_dir = os.path.join(self.temp_dir, 'deps')
        pkg_dir = os.path.join(dep_dir, 'foo')
        os.makedirs(pkg_dir)
        prebuilt_zst = os.path.join(pkg_dir, 'dep-foo.tar.zst')
        with open(prebuilt_zst, 'w') as f:
            f.write('prebuilt-zst')

        repo_dir = os.path.join(self.temp_dir, 'repo')
        os.makedirs(repo_dir)
        pm = self._make_pkgmgr(upload_paths=[repo_dir])
        pm.tar_package = mock.Mock(
                side_effect=AssertionError('tar_package should not be called'))

        out_dir = os.path.join(self.temp_dir, 'tar_out')
        os.makedirs(out_dir)
        reused = packager.tar_packages(pm, 'dep', 'foo', dep_dir, out_dir)
        self.assertEqual(reused, [prebuilt_zst])
        pm.tar_package.assert_not_called()

        with mock.patch.object(
                packager.tempfile,
                'mkdtemp',
                side_effect=AssertionError('mkdtemp should not be called')):
            packager.process_packages(pm,
                                      'dep',
                                      'foo',
                                      dep_dir,
                                      action=packager.ACTION_UPLOAD)
        pm.tar_package.assert_not_called()
        self.assertTrue(os.path.isfile(prebuilt_zst))
        with open(os.path.join(repo_dir, 'dep-foo.tar.zst')) as f:
            self.assertEqual(f.read(), 'prebuilt-zst')

    def test_process_packages_upload_skips_unchanged_checksum(self):
        """ACTION_UPLOAD skips upload_pkg when the tarball checksum matches."""
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

        mock_upload.assert_not_called()

    def test_process_packages_upload_removes_stale_bz2_and_checksum(self):
        """ACTION_UPLOAD prunes leftover .tar.bz2 files and checksum entries."""
        dep_dir = os.path.join(self.temp_dir, 'deps')
        os.makedirs(os.path.join(dep_dir, 'foo'))
        repo_dir = os.path.join(self.temp_dir, 'repo')
        os.makedirs(repo_dir)
        stale_bz2 = os.path.join(repo_dir, 'dep-foo.tar.bz2')
        with open(stale_bz2, 'w') as f:
            f.write('stale-dual-publish-bz2')

        pm = self._make_pkgmgr(upload_paths=[repo_dir])
        pm._checksum_dict = {
                'dep-foo.tar.zst': 'old-md5-zst',
                'dep-foo.tar.bz2': 'old-md5-bz2',
                'dep-other.tar.zst': 'keep-md5',
        }

        def fake_tar(pkg_name, src_dir, dest_dir, exclude_string=None):
            out = os.path.join(dest_dir, pkg_name)
            with open(out, 'w') as f:
                f.write('payload-' + pkg_name)
            return out

        pm.tar_package = fake_tar
        with mock.patch.object(packages, 'check_diskspace'):
            packager.process_packages(pm,
                                      'dep',
                                      'foo',
                                      dep_dir,
                                      action=packager.ACTION_UPLOAD)

        self.assertFalse(os.path.exists(stale_bz2))
        self.assertTrue(
                os.path.isfile(os.path.join(repo_dir, 'dep-foo.tar.zst')))
        with open(os.path.join(repo_dir, packages.CHECKSUM_FILE)) as f:
            checksum_contents = f.read()
        self.assertIn('md5-dep-foo.tar.zst dep-foo.tar.zst', checksum_contents)
        self.assertIn('keep-md5 dep-other.tar.zst', checksum_contents)
        self.assertNotIn('dep-foo.tar.bz2', checksum_contents)

        # Also removes stale .tar.bz2 when .tar.zst checksum already matches.
        with open(stale_bz2, 'w') as f:
            f.write('stale-dual-publish-bz2-again')
        pm._checksum_dict['dep-foo.tar.bz2'] = 'old-md5-bz2'
        with mock.patch.object(packages, 'check_diskspace'), \
                mock.patch.object(pm, 'upload_pkg',
                                  wraps=pm.upload_pkg) as mock_upload:
            packager.process_packages(pm,
                                      'dep',
                                      'foo',
                                      dep_dir,
                                      action=packager.ACTION_UPLOAD)

        mock_upload.assert_not_called()
        self.assertFalse(os.path.exists(stale_bz2))
        with open(os.path.join(repo_dir, packages.CHECKSUM_FILE)) as f:
            checksum_contents = f.read()
        self.assertNotIn('dep-foo.tar.bz2', checksum_contents)

        # Fresh pkgmgr_dir with repo_urls=[] preserves pre-existing sibling
        # entries in repo_dir/packages.checksum across full ACTION_UPLOAD.
        fresh_dir = os.path.join(self.temp_dir, 'fresh_pkgmgr')
        os.makedirs(fresh_dir)
        with open(stale_bz2, 'w') as f:
            f.write('stale-bz2-fresh-run')
        with open(os.path.join(repo_dir, packages.CHECKSUM_FILE), 'w') as f:
            f.write('1111 dep-keep.tar.zst\n2222 dep-foo.tar.bz2\n')
        fresh_pm = packages.PackageManager(fresh_dir,
                                           repo_urls=[],
                                           upload_paths=[repo_dir],
                                           do_locking=False,
                                           run_function=self._fake_run)
        fresh_pm.tar_package = fake_tar
        with mock.patch.object(packages, 'check_diskspace'):
            packager.process_packages(fresh_pm,
                                      'dep',
                                      'foo',
                                      dep_dir,
                                      action=packager.ACTION_UPLOAD)

        self.assertFalse(os.path.exists(stale_bz2))
        with open(os.path.join(repo_dir, packages.CHECKSUM_FILE)) as f:
            checksum_contents = f.read()
        self.assertIn('1111 dep-keep.tar.zst', checksum_contents)
        self.assertIn('md5-dep-foo.tar.zst dep-foo.tar.zst', checksum_contents)
        self.assertNotIn('dep-foo.tar.bz2', checksum_contents)

    def test_process_all_packages_upload_removes_stale_bz2(self):
        """process_all_packages ACTION_UPLOAD prunes stale .tar.bz2 files."""
        client_dir = os.path.join(self.temp_dir, 'client')
        for subdir in ('tests', 'site_tests', 'profilers'):
            os.makedirs(os.path.join(client_dir, subdir))
        os.makedirs(os.path.join(client_dir, 'deps', 'foo'))

        repo_dir = os.path.join(self.temp_dir, 'repo')
        os.makedirs(repo_dir)
        for stale in ('dep-foo.tar.bz2', 'client-autotest.tar.bz2'):
            with open(os.path.join(repo_dir, stale), 'w') as f:
                f.write('stale-' + stale)

        pm = self._make_pkgmgr(upload_paths=[repo_dir])
        pm._checksum_dict = {
                'dep-foo.tar.bz2': 'old-dep-bz2',
                'client-autotest.tar.bz2': 'old-client-bz2',
        }

        def fake_tar(pkg_name, src_dir, dest_dir, exclude_string=None):
            out = os.path.join(dest_dir, pkg_name)
            with open(out, 'w') as f:
                f.write('payload-' + pkg_name)
            return out

        pm.tar_package = fake_tar
        with mock.patch.object(packages, 'check_diskspace'), \
                mock.patch.object(packager.client_utils, 'run'):
            packager.process_all_packages(pm,
                                          client_dir,
                                          action=packager.ACTION_UPLOAD)

        self.assertFalse(
                os.path.exists(os.path.join(repo_dir, 'dep-foo.tar.bz2')))
        self.assertFalse(
                os.path.exists(
                        os.path.join(repo_dir, 'client-autotest.tar.bz2')))
        self.assertTrue(
                os.path.isfile(os.path.join(repo_dir, 'dep-foo.tar.zst')))
        self.assertTrue(
                os.path.isfile(
                        os.path.join(repo_dir, 'client-autotest.tar.zst')))
        with open(os.path.join(repo_dir, packages.CHECKSUM_FILE)) as f:
            checksum_contents = f.read()
        self.assertNotIn('.tar.bz2', checksum_contents)
        self.assertIn('dep-foo.tar.zst', checksum_contents)
        self.assertIn('client-autotest.tar.zst', checksum_contents)

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

    def test_process_packages_tar_only_publishes_zstd_only(self):
        """ACTION_TAR_ONLY writes only the .tar.zst tarball and .checksum."""
        dep_dir = os.path.join(self.temp_dir, 'deps')
        os.makedirs(os.path.join(dep_dir, 'foo'))
        dest_dir = os.path.join(self.temp_dir, 'out')
        build_dir = os.path.join(dest_dir, 'client', 'deps', 'foo')
        os.makedirs(build_dir)
        for stale_name, content in (
                ('dep-foo.tar.bz2', 'stale-bz2'),
                ('dep-foo.tar.bz2.checksum', 'stale-bz2-md5'),
                ('dep-foo.tar.zst.checksum', 'stale-zst-md5'),
        ):
            with open(os.path.join(build_dir, stale_name), 'w') as f:
                f.write(content)
        pm = self._make_pkgmgr()

        def fake_tar(pkg_name, src_dir, out_dir, exclude_string=None):
            out = os.path.join(out_dir, pkg_name)
            with open(out, 'w') as f:
                f.write('payload-' + pkg_name)
            return out

        pm.tar_package = fake_tar

        with mock.patch.object(packages, 'check_diskspace'):
            packager.process_packages(pm,
                                      'dep',
                                      'foo',
                                      dep_dir,
                                      action=packager.ACTION_TAR_ONLY,
                                      dest_dir=dest_dir)

        self.assertTrue(
                os.path.isfile(os.path.join(build_dir, 'dep-foo.tar.zst')))
        self.assertFalse(
                os.path.exists(os.path.join(build_dir, 'dep-foo.tar.bz2')))
        self.assertFalse(
                os.path.exists(
                        os.path.join(build_dir, 'dep-foo.tar.bz2.checksum')))
        checksum_path = os.path.join(build_dir, 'dep-foo.tar.zst.checksum')
        self.assertTrue(os.path.isfile(checksum_path))
        with open(checksum_path) as f:
            self.assertEqual(f.read(), 'md5-dep-foo.tar.zst')


if __name__ == '__main__':
    unittest.main()
