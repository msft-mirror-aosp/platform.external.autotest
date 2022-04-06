# Lint as: python2, python3
# Copyright 2022 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import unittest
import tempfile
import shutil

from unittest.mock import Mock, ANY, patch
from autotest_lib.server.cros.tradefed import tradefed_test


class TradefedTestTest(unittest.TestCase):
    """Tests for TradefedTest class."""

    def setUp(self):
        self._bindir = tempfile.mkdtemp()
        self._outputdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self._bindir)
        shutil.rmtree(self._outputdir)

    def create_mock_job(self):
        """Creates a mock necessary for constructing tradefed_test instance."""
        mock_job = Mock()
        mock_job.pkgmgr = None
        mock_job.autodir = None
        mock_job.tmpdir = tempfile.mkdtemp()
        return mock_job

    def test_instantiate(self):
        tradefed_test.TradefedTest(self.create_mock_job(), self._bindir,
                                   self._outputdir)

    @patch('autotest_lib.server.cros.tradefed.adb.tradefed_options')
    @patch('autotest_lib.server.cros.tradefed.tradefed_test.TradefedTest._run')
    def test_run_adb(self, mock_run, mock_tradefed_options):
        instance = tradefed_test.TradefedTest(self.create_mock_job(),
                                              self._bindir, self._outputdir)

        mock_tradefed_options.return_value = ('additional', 'options')
        instance._run_adb_cmd(args=('some', 'arguments'))
        mock_run.assert_called_with('adb',
                                    args=('additional', 'options', 'some',
                                          'arguments'))

    # Verify that try_adb_connect fails when run_adb_cmd fails.
    @patch('autotest_lib.server.cros.tradefed.tradefed_test.TradefedTest._run_adb_cmd'
           )
    @patch('autotest_lib.server.cros.tradefed.adb.get_adb_target')
    def test_try_adb_connect_run_adb_fail(self, mock_get_adb_target,
                                          mock_run_adb_cmd):
        instance = tradefed_test.TradefedTest(self.create_mock_job(),
                                              self._bindir, self._outputdir)
        # Exit status is set to non-0 to exit _try_adb_connect() early.
        mock_run_adb_cmd.return_value = Mock()
        mock_run_adb_cmd.return_value.exit_status = 1
        mock_get_adb_target.return_value = '123.76.0.29:3467'

        self.assertFalse(instance._try_adb_connect(Mock()))
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
        instance = tradefed_test.TradefedTest(self.create_mock_job(),
                                              self._bindir, self._outputdir)
        instance._install_paths = '/any/install/path'

        mock_host1 = Mock()
        mock_host2 = Mock()
        instance._hosts = [mock_host1, mock_host2]

        mock_get_adb_targets.return_value = ['host1:4321', 'host2:22']

        mock_tradefed_cmd_path.return_value = '/any/path'

        instance._run_tradefed_with_timeout(['command'], 1234)
        mock_get_adb_targets.assert_called_with(instance._hosts)
