# Lint as: python2, python3
# Copyright 2022 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import unittest

from unittest.mock import Mock, patch
from autotest_lib.client.common_lib import error
from autotest_lib.server import utils
from autotest_lib.server.cros.tradefed import adb


class AdbTest(unittest.TestCase):
    """Tests for ADB module."""

    # Verify that ipv4 is put into IP:PORT format.
    def test_get_adb_target_ipv4(self):
        mock_host = Mock()
        mock_host.port = 3467
        mock_host.hostname = '123.76.0.29'
        target = adb.get_adb_target(mock_host)
        self.assertEqual(target, '123.76.0.29:3467')

    # Verify that ipv6 is put into [IP]:PORT format.
    def test_get_adb_target_ipv6(self):
        mock_host = Mock()
        mock_host.port = 1234
        mock_host.hostname = '2409::3'
        target = adb.get_adb_target(mock_host)
        self.assertEqual(target, '[2409::3]:1234')

    # Verify that a host name works.
    def test_get_adb_target_hostname(self):
        mock_host = Mock()
        mock_host.port = 4792
        mock_host.hostname = 'some.hostname.cros'
        target = adb.get_adb_target(mock_host)
        self.assertEqual(target, 'some.hostname.cros:4792')

    # Verify that a list of hosts work.
    def test_get_adb_targets(self):
        mock_host1 = Mock()
        mock_host2 = Mock()
        mock_host3 = Mock()
        mock_host1.port = 1111
        mock_host2.port = 2222
        mock_host3.port = 3333
        mock_host1.hostname = 'host1'
        mock_host2.hostname = 'host2'
        mock_host3.hostname = 'host3'

        targets = adb.get_adb_targets([mock_host1, mock_host2, mock_host3])
        self.assertEqual(targets, ['host1:1111', 'host2:2222', 'host3:3333'])

    def test_add_paths(self):
        instance = adb.Adb()
        instance.add_path('/some/install/path')
        instance.add_path('/another/directory')

        self.assertEqual(set(['/some/install/path', '/another/directory']),
                         instance.get_paths())

    @patch('autotest_lib.server.utils.run')
    def test_run(self, mock_run):
        instance = adb.Adb()
        instance.add_path('/some/install/path')

        mock_host = Mock()
        mock_host.port = 3467
        mock_host.hostname = '123.76.0.29'

        instance.run(mock_host, args=('some', 'command'), timeout=240)
        mock_run.assert_called_with('adb',
                                    args=('-L', 'tcp:localhost:5037', '-s',
                                          '123.76.0.29:3467', 'some',
                                          'command'),
                                    timeout=240,
                                    extra_paths=['/some/install/path'])

    @patch('autotest_lib.server.utils.run')
    def test_run_without_host(self, mock_run):
        instance = adb.Adb()
        instance.add_path('/some/install/path')

        instance.run(None, args=('some', 'command'), timeout=240)
        mock_run.assert_called_with('adb',
                                    args=('-L', 'tcp:localhost:5037', 'some',
                                          'command'),
                                    timeout=240,
                                    extra_paths=['/some/install/path'])

    @patch('autotest_lib.server.utils.run')
    @patch('random.randint', return_value=12345)
    def test_pick_random_port(self, mock_randint, mock_run):
        mock_run.return_value = utils.CmdResult(
            exit_status=0,
            stderr='daemon started successfully')

        instance = adb.Adb()
        instance.pick_random_port(max_retries=1, start_timeout=3)
        mock_randint.assert_called()
        mock_run.assert_called_once_with('adb',
                                         args=('-L', 'tcp:localhost:12345',
                                               'start-server'),
                                         extra_paths=[],
                                         timeout=3,
                                         verbose=True)

        self.assertEqual(instance.get_port(), 12345)

    @patch('autotest_lib.server.utils.run')
    @patch('random.randint')
    def test_pick_random_port_with_retry(self, mock_randint, mock_run):
        mock_randint.side_effect = [12340, 12341, 12342, 12343]
        mock_run.side_effect = [
            # 1st try: port occupied by ADB server
            utils.CmdResult(exit_status=0),
            # 2nd try: port occupied by some process, got invalid response
            error.CmdError(command=None, result_obj=None),
            # 3rd try: port occupied by some process, got no response
            error.CmdTimeoutError(command=None, result_obj=None),
            # 4th try: success
            utils.CmdResult(exit_status=0,
                            stderr='daemon started successfully'),
        ]

        instance = adb.Adb()

        # Try 4 times; should succeed on 4th try
        instance.pick_random_port(max_retries=4)
        self.assertEqual(instance.get_port(), 12343)
