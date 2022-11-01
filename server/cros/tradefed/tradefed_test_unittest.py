# Lint as: python2, python3
# Copyright 2022 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import unittest
import os
import tempfile
import shutil
import stat

from unittest.mock import Mock, ANY, patch
from autotest_lib.client.common_lib import error
from autotest_lib.server.cros.tradefed import tradefed_test


class TradefedTestTest(unittest.TestCase):
    """Tests for TradefedTest class."""

    def setUp(self):
        self._mockjob_tmpdirs = []
        self._bindir = tempfile.mkdtemp()
        self._outputdir = tempfile.mkdtemp()
        self.mock_adb = Mock()
        self.tradefed = tradefed_test.TradefedTest(self.create_mock_job(),
                                                   self._bindir,
                                                   self._outputdir,
                                                   adb=self.mock_adb)

    def tearDown(self):
        shutil.rmtree(self._bindir)
        shutil.rmtree(self._outputdir)
        for tmpdir in self._mockjob_tmpdirs:
            shutil.rmtree(tmpdir)

    def create_mock_job(self):
        """Creates a mock necessary for constructing tradefed_test instance."""
        mock_job = Mock()
        mock_job.pkgmgr = None
        mock_job.autodir = None
        mock_job.tmpdir = tempfile.mkdtemp()
        self._mockjob_tmpdirs.append(mock_job.tmpdir)
        return mock_job

    # Verify that try_adb_connect fails when run_adb_cmd fails.
    @patch('autotest_lib.server.cros.tradefed.adb.get_adb_target')
    def test_try_adb_connect_run_adb_fail(self, mock_get_adb_target):
        mock_run_adb_cmd = self.mock_adb.run

        # Exit status is set to non-0 to exit _try_adb_connect() early.
        mock_run_adb_cmd.return_value.exit_status = 1
        mock_get_adb_target.return_value = '123.76.0.29:3467'

        self.assertFalse(self.tradefed._try_adb_connect(Mock()))
        mock_run_adb_cmd.assert_called_with(ANY,
                                            args=('connect',
                                                  '123.76.0.29:3467'),
                                            verbose=ANY,
                                            env=ANY,
                                            ignore_status=ANY,
                                            timeout=ANY)

    # Verify that _run_tradefed_with_timeout works.
    @patch('autotest_lib.server.cros.tradefed.tradefed_test.TradefedTest._run')
    @patch('autotest_lib.server.cros.tradefed.tradefed_test.TradefedTest._tradefed_cmd_path'
           )
    @patch('autotest_lib.server.cros.tradefed.tradefed_utils.adb_keepalive')
    @patch('autotest_lib.server.cros.tradefed.adb.get_adb_targets')
    def test_run_tradefed_with_timeout(self, mock_get_adb_targets, _,
                                       mock_tradefed_cmd_path, mock_run):
        self.tradefed._install_paths = '/any/install/path'

        mock_host1 = Mock()
        mock_host2 = Mock()
        self.tradefed._hosts = [mock_host1, mock_host2]

        mock_get_adb_targets.return_value = ['host1:4321', 'host2:22']

        mock_tradefed_cmd_path.return_value = '/any/path'

        self.tradefed._run_tradefed_with_timeout(['command'], 1234)
        mock_get_adb_targets.assert_called_with(self.tradefed._hosts)

    def test_kill_adb_server(self):
        mock_run = self.mock_adb.run
        self.tradefed._kill_adb_server()
        mock_run.assert_called_with(None,
                                    args=('kill-server', ),
                                    timeout=ANY,
                                    verbose=ANY)

    def test_verify_arc_hosts_single_host(self):
        mock_run = self.mock_adb.run
        mock_host = Mock()
        self.tradefed._hosts = [mock_host]

        self.tradefed._verify_arc_hosts()

        mock_run.assert_called_with(mock_host,
                                    args=('shell', 'getprop',
                                          'ro.build.fingerprint'))

    # Verify that multiple hosts with differet fingerprints fail.
    def test_verify_arc_hosts_different_fingerprints(self):
        mock_run = self.mock_adb.run
        mock_host1 = Mock()
        mock_host2 = Mock()
        self.tradefed._hosts = [mock_host1, mock_host2]

        side_effects = [Mock(), Mock()]
        side_effects[0].stdout = 'fingerprint1'
        side_effects[1].stdout = 'fingerprint2'
        mock_run.side_effect = side_effects

        self.assertRaises(error.TestFail, self.tradefed._verify_arc_hosts)

        mock_run.assert_any_call(mock_host1,
                                 args=('shell', 'getprop',
                                       'ro.build.fingerprint'))
        mock_run.assert_any_call(mock_host2,
                                 args=('shell', 'getprop',
                                       'ro.build.fingerprint'))

    # Verify that wait for arc boot uses polling with adb.
    @patch('autotest_lib.server.utils.poll_for_condition')
    def test_wait_for_arc_boot(self, mock_poll_for_condition):
        mock_run = self.mock_adb.run

        # stdout just has to be something that evaluates to True.
        mock_run.return_value.stdout = 'anything'

        mock_host = Mock()
        self.tradefed._wait_for_arc_boot(mock_host)

        self.assertEqual(mock_run.call_count, 0)

        # Verify that the condition function uses the expected adb command.
        self.assertEqual(mock_poll_for_condition.call_count, 1)
        args = mock_poll_for_condition.call_args[0]
        condition_func = args[0]
        self.assertTrue(condition_func())

        mock_run.assert_called_with(mock_host,
                                    args=('shell', 'pgrep', '-f',
                                          'org.chromium.arc.intent_helper'),
                                    ignore_status=True)

    def test_disable_adb_install_dialog_android_version_over_29(self):
        mock_run = self.mock_adb.run
        mock_run.return_value.stdout = 'disabled'

        self.tradefed._android_version = 30
        mock_host = Mock()
        self.tradefed._disable_adb_install_dialog(mock_host)

        mock_run.assert_called_with(mock_host,
                                    args=('shell', 'settings', 'put', 'global',
                                          'verifier_verify_adb_installs', '0'),
                                    verbose=ANY)

    def test_disable_adb_install_dialog_android_version_under_29(self):
        mock_run = self.mock_adb.run

        mock_run.return_value.stdout = 'disabled'

        self.tradefed._android_version = 28
        mock_host = Mock()
        self.tradefed._disable_adb_install_dialog(mock_host)

        mock_run.assert_called_with(mock_host,
                                    args=('shell', 'settings', 'put', 'global',
                                          'verifier_verify_adb_installs', '0'),
                                    verbose=ANY)

        mock_host.run.assert_called_with(
                'android-sh -c \'setprop persist.sys.disable_rescue true\'')

    def test_fetch_helpers_from_dut(self):
        mock_run = self.mock_adb.run
        self.tradefed._repository = '/repo/path'

        mock_host = Mock()
        self.tradefed._hosts = [mock_host]

        # '::' is intentional and should be skipped.
        mock_run.return_value.stdout = 'package1:package2::package3'

        self.tradefed._fetch_helpers_from_dut()

        mock_run.assert_called_with(
                mock_host,
                args=('shell', 'getprop',
                      'ro.vendor.cts_interaction_helper_packages'))

        self.assertEqual(mock_host.get_file.call_count, 3)

        mock_host.get_file.assert_any_call(
                '/usr/local/opt/google/vms/android/package1.apk',
                '/repo/path/testcases',
        )

        mock_host.get_file.assert_any_call(
                '/usr/local/opt/google/vms/android/package2.apk',
                '/repo/path/testcases',
        )

        mock_host.get_file.assert_any_call(
                '/usr/local/opt/google/vms/android/package3.apk',
                '/repo/path/testcases',
        )

    def test_get_abilist(self):
        mock_run = self.mock_adb.run
        mock_host = Mock()
        self.tradefed._hosts = [mock_host]

        mock_run.return_value.stdout = 'arm,x86,my_awesome_architecture'

        self.assertEqual(['arm', 'x86', 'my_awesome_architecture'],
                         self.tradefed._get_abilist())

        mock_run.assert_called_with(mock_host,
                                    args=('shell', 'getprop',
                                          'ro.product.cpu.abilist'))

    def test_copy_extra_artifacts_dut(self):
        mock_run = self.mock_adb.run
        mock_host = Mock()

        extra_artifacts = ['artifacts', '/path/to/some/file']
        self.tradefed._copy_extra_artifacts_dut(extra_artifacts, mock_host,
                                                self._outputdir)

        self.assertEqual(mock_run.call_count, 2)

        mock_run.assert_any_call(
                mock_host,
                args=('pull', 'artifacts', self._outputdir),
                verbose=ANY,
                timeout=ANY,
        )

        mock_run.assert_any_call(
                mock_host,
                args=('pull', '/path/to/some/file', self._outputdir),
                verbose=ANY,
                timeout=ANY,
        )

    # TODO(rkuroiwa): This test was added to test Adb.add_path.
    # So most of these tradefed_test functions are mocked because
    # they are not ncecessarily ready to be tested.
    # Once the rest of the modules are tested, reevaluate unmocking them.
    @patch('os.chmod')
    @patch('autotest_lib.server.cros.tradefed.tradefed_test.TradefedTest._instance_copyfile'
           )
    @patch('autotest_lib.server.cros.tradefed.tradefed_test.TradefedTest._validate_download_cache'
           )
    @patch('autotest_lib.server.cros.tradefed.tradefed_test.TradefedTest._download_to_cache'
           )
    @patch('autotest_lib.server.cros.tradefed.tradefed_test.TradefedTest._invalidate_download_cache'
           )
    @patch('autotest_lib.server.cros.tradefed.tradefed_utils.lock')
    def test_install_files(self, mock_lock, mock_invalidate_download_cache,
                           mock_download_to_cache,
                           mock_validate_download_cache, mock_instance_copy,
                           mock_chmod):
        mock_add_path = self.mock_adb.add_path
        self.tradefed._tradefed_cache_lock = '/lock/lock_file'
        self.tradefed._install_paths = []

        mock_download_to_cache.return_value = '/path/to/downloaded/file'
        mock_instance_copy.return_value = '/path/to/local/downloaded_file'

        self.tradefed._install_files('gs://mybucket/path/to/dir', ['anyfile'],
                                     stat.S_IRWXU)

        mock_lock.assert_called_with('/lock/lock_file')
        mock_invalidate_download_cache.assert_called()
        mock_validate_download_cache.assert_called()
        mock_chmod.assert_called_with('/path/to/local/downloaded_file',
                                      stat.S_IRWXU)
        mock_add_path.assert_called_with('/path/to/local')

        self.assertEqual(self.tradefed._install_paths, ['/path/to/local'])

    @patch('autotest_lib.server.utils.run')
    @patch('os.renames')
    @patch('tempfile.mkdtemp')
    @patch('os.path.isdir')
    def test_unzip_no_password(self, mock_isdir, mock_mkdtemp, mock_renames,
                               mock_run):
        mock_isdir.return_value = False
        mock_mkdtemp.return_value = '/a/temp/dir'

        self.tradefed._unzip('/path/to/archive.zip')

        mock_run.assert_called_with('unzip',
                                    args=('-d', '/a/temp/dir',
                                          '/path/to/archive.zip'))

    @patch('autotest_lib.server.utils.run')
    @patch('os.renames')
    @patch('tempfile.mkdtemp')
    @patch('os.path.isdir')
    def test_unzip_with_password(self, mock_isdir, mock_mkdtemp, mock_renames,
                                 mock_run):
        mock_isdir.return_value = False
        mock_mkdtemp.return_value = '/a/temp/dir'

        self.tradefed._unzip('/path/to/archive.zip', 'extraction_password!!')

        mock_run.assert_called_with('unzip',
                                    args=('-P', 'extraction_password!!', '-d',
                                          '/a/temp/dir',
                                          '/path/to/archive.zip'))

    # Verify that parsing gsutil ls -L output correctly extracts the ETag and
    # returns in hex.
    @patch('autotest_lib.server.utils.run')
    def test_parse_ETag(self, mock_run):
        mock_run.return_value = Mock(
                stdout="""gs://path/to/a.zip:
                        Creation time:          Wed, 15 Jun 2022 16:53:14 GMT
                        Update time:            Wed, 15 Jun 2022 16:53:14 GMT
                        Storage class:          STANDARD
                        Content-Language:       en
                        Content-Length:         201832881
                        Content-Type:           application/zip
                        Hash (crc32c):          TN1ctw==
                        Hash (md5):             ZArA7Yt7EREmkFmTanLHdA==
                        ETag:                   COOOrtv1r/gCEAE=
                        TOTAL: 1 objects, 201832881 bytes (192.48 MiB) """)
        etag_hex = tradefed_test._GetETagFromGsUri('gs://path/to/a.zip')
        self.assertEqual(etag_hex, '434f4f4f72747631722f67434541453d')

    # For the first time, it should call _download_to_dir to download the
    # bundle.
    @patch('autotest_lib.server.cros.tradefed.tradefed_test.TradefedTest._download_to_dir'
           )
    @patch('autotest_lib.server.utils.run')
    @patch('os.path.exists')
    def test_download_to_cache_initial_download(self, mock_exists, mock_run,
                                                mock_download_to_dir):
        mock_run.return_value = Mock(
                stdout='ETag: COOOrtv1r/gCEAE=')
        mock_exists.return_value = False

        self.tradefed._tradefed_cache = '/any/test/dir'

        self.tradefed._download_to_cache(
                'gs://some-fake-bucket/path/to/bundle.zip')

        mock_download_to_dir.assert_called_with(
                'gs://some-fake-bucket/path/to/bundle.zip',
                os.path.join(self.tradefed._tradefed_cache,
                             '434f4f4f72747631722f67434541453d'))

        mock_run.assert_called_with(
                'gsutil',
                args=('ls', '-L',
                      'gs://some-fake-bucket/path/to/bundle.zip'),
                verbose=ANY)

    # Redownload a same-name-bundle that had been downloaded, but different
    # Etag.
    @patch('autotest_lib.server.cros.tradefed.tradefed_test.TradefedTest._download_to_dir'
           )
    @patch('autotest_lib.server.utils.run')
    @patch('os.path.exists')
    def test_download_to_cache_same_google_storage_path_different_bundle(
            self, mock_exists, mock_run, mock_download_to_dir):
        mock_run.return_value = Mock(
                stdout='ETag: COOOrtv1r/gCEAE=')

        # Let os.path.exist return false. Must also check what value was passed to the mock (below).
        mock_exists.return_value = False

        self.tradefed._tradefed_cache = '/any/test/dir'

        self.tradefed._download_to_cache(
                'gs://some-fake-bucket/path/to/bundle.zip')

        mock_download_to_dir.assert_called_with(
                'gs://some-fake-bucket/path/to/bundle.zip',
                os.path.join(self.tradefed._tradefed_cache,
                             '434f4f4f72747631722f67434541453d'))

        mock_exists.assert_called_with(
                os.path.join(self.tradefed._tradefed_cache,
                             '434f4f4f72747631722f67434541453d'))

        # Now let it return a different hash value, for the same path.
        mock_run.return_value = Mock(
                stdout='ETag: SomeOtherEtag')
        self.tradefed._download_to_cache(
                'gs://some-fake-bucket/path/to/bundle.zip')

        # Verify that os.path.exists was called with different values than the
        # first time.
        mock_exists.assert_called_with(
                os.path.join(self.tradefed._tradefed_cache,
                             '536f6d654f7468657245746167'))

    @patch('autotest_lib.server.cros.tradefed.tradefed_test.TradefedTest._download_to_dir'
           )
    @patch('hashlib.md5')
    @patch('os.path.exists')
    def test_download_to_cache_non_google_storage(self, mock_exists, mock_md5,
                                                  mock_download_to_dir):
        mock_exists.return_value = False
        mock_md5.return_value.hexdigest.return_value = '6ae0e7fc911c1b310d85c0d9fa592c08'

        self.tradefed._tradefed_cache = '/any/test/dir'

        self.tradefed._download_to_cache(
                'https://dl.google.com/dl/android/xts/bundle.zip')

        mock_exists.assert_called_with(
                os.path.join(self.tradefed._tradefed_cache,
                             '6ae0e7fc911c1b310d85c0d9fa592c08'))

        mock_download_to_dir.assert_called_with(
                'https://dl.google.com/dl/android/xts/bundle.zip',
                os.path.join(self.tradefed._tradefed_cache,
                             '6ae0e7fc911c1b310d85c0d9fa592c08'))

    # Verify that downloaded bundles is not redownloaded.
    @patch('autotest_lib.server.cros.tradefed.tradefed_test.TradefedTest._download_to_dir'
           )
    @patch('hashlib.md5')
    @patch('os.path.exists')
    @patch('os.listdir')
    def test_download_to_cache_same_hash(self, mock_listdir, mock_exists,
                                         mock_md5, mock_download_to_dir):
        # os.path.exists returning true means it has been downloaded.
        mock_exists.return_value = True
        mock_md5.return_value.hexdigest.return_value = '6ae0e7fc911c1b310d85c0d9fa592c08'
        mock_listdir.return_value = ['non', 'empty', 'list']

        self.tradefed._tradefed_cache = '/any/test/dir'

        self.tradefed._download_to_cache(
                'https://dl.google.com/dl/android/xts/bundle.zip')

        mock_exists.assert_called_with(
                os.path.join(self.tradefed._tradefed_cache,
                             '6ae0e7fc911c1b310d85c0d9fa592c08'))

        mock_download_to_dir.assert_not_called()

    # The path exists but the output dir is empty. It should redownload.
    @patch('autotest_lib.server.cros.tradefed.tradefed_test.TradefedTest._download_to_dir'
           )
    @patch('hashlib.md5')
    @patch('os.path.exists')
    @patch('os.listdir')
    def test_download_to_cache_same_hash_empty_listdir(self, mock_listdir,
                                                       mock_exists, mock_md5,
                                                       mock_download_to_dir):
        mock_exists.return_value = True
        mock_md5.return_value.hexdigest.return_value = '6ae0e7fc911c1b310d85c0d9fa592c08'
        mock_listdir.return_value = []

        self.tradefed._tradefed_cache = '/any/test/dir'

        self.tradefed._download_to_cache(
                'https://dl.google.com/dl/android/xts/bundle.zip')

        mock_exists.assert_called_with(
                os.path.join(self.tradefed._tradefed_cache,
                             '6ae0e7fc911c1b310d85c0d9fa592c08'))

        mock_download_to_dir.assert_called()

    # Verify that an exception is raised if there isn't an ETag in the gsutil
    # output.
    @patch('autotest_lib.server.utils.run')
    def test_failed_to_find_ETag(self, mock_run):
        mock_run.return_value = Mock(
                stdout='This message does not contain an ETag.')
        self.assertRaises(tradefed_test.ETagNotFoundException,
                          tradefed_test._GetETagFromGsUri,
                          'gs://anything/here')
