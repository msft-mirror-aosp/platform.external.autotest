# Lint as: python2, python3
# Copyright 2022 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import unittest

from unittest.mock import ANY, MagicMock, call, patch
from autotest_lib.client.common_lib import error
from autotest_lib.server import utils
from autotest_lib.server.cros.tradefed import adb


class MockHost:
    """Mock Host object."""

    def __init__(self, hostname='hostname', port='22'):
        self.hostname = hostname
        self.port = port

    def ssh_command(self, options):
        """Returns a mock SSH command."""
        return f'ssh {options} {self.hostname}'


class AdbTest(unittest.TestCase):
    """Tests for Adb."""

    def test_add_paths(self):
        instance = adb.Adb()
        instance.add_path('/some/install/path')
        instance.add_path('/another/directory')

        self.assertEqual(set(['/some/install/path', '/another/directory']),
                         instance.get_paths())

    def test_set_create_tunnel(self):
        mock_tunnel = MagicMock()
        mock_ctx = MagicMock()
        mock_tunnel.create.return_value = mock_ctx

        a = adb.Adb()
        a.set_tunnel(mock_tunnel)
        with a.create_tunnel():
            mock_tunnel.create.assert_called_once()
            mock_ctx.__enter__.assert_called_once()
        mock_ctx.__exit__.assert_called_once()

    def test_get_adb_target(self):
        mock_tunnel = MagicMock()
        mock_host = MockHost()

        a = adb.Adb()
        a.set_tunnel(mock_tunnel)
        with a.create_tunnel():
            a.get_adb_target(mock_host)

        mock_tunnel.create.assert_called_once()
        mock_tunnel.get_adb_target.assert_called_once_with(mock_host)

    def test_get_adb_targets(self):
        mock_tunnel = MagicMock()
        mock_host1 = MockHost()
        mock_host2 = MockHost()
        mock_host3 = MockHost()

        a = adb.Adb()
        a.set_tunnel(mock_tunnel)
        with a.create_tunnel():
            a.get_adb_targets([mock_host1, mock_host2, mock_host3])

        mock_tunnel.create.assert_called_once()
        mock_tunnel.get_adb_target.assert_has_calls([
                call(mock_host1),
                call(mock_host2),
                call(mock_host3),
        ])

    @patch('autotest_lib.server.utils.run')
    def test_run(self, mock_run):
        instance = adb.Adb()
        instance.add_path('/some/install/path')

        mock_host = MockHost('123.76.0.29', 3467)

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


class NullAdbTunnelTest(unittest.TestCase):
    """Tests for NullAdbTunnel."""

    def test_create(self):
        t = adb.NullAdbTunnel()
        with t.create():
            pass

    def test_get_adb_target_ipv4(self):
        mock_host = MockHost('123.76.0.29', 3467)

        t = adb.NullAdbTunnel()
        target = t.get_adb_target(mock_host)
        self.assertEqual(target, '123.76.0.29:3467')

    def test_get_adb_target_ipv6(self):
        mock_host = MockHost('2409::3', 1234)

        t = adb.NullAdbTunnel()
        target = t.get_adb_target(mock_host)
        self.assertEqual(target, '[2409::3]:1234')

    # Verify that a host name works.
    def test_get_adb_target_hostname(self):
        mock_host = MockHost('some.hostname.cros', 4792)

        t = adb.NullAdbTunnel()
        target = t.get_adb_target(mock_host)
        self.assertEqual(target, 'some.hostname.cros:4792')


class SshAdbTunnelTest(unittest.TestCase):
    """Tests for SshAdbTunnel."""

    @patch('autotest_lib.server.utils.BgJob')
    @patch('autotest_lib.server.utils.nuke_subprocess')
    @patch('autotest_lib.server.utils.join_bg_jobs')
    def test_basic(self, mock_join_bg_jobs, mock_nuke_subprocess, mock_bgjob):
        host1 = MockHost('host1')
        host2 = MockHost('host2')
        hosts = [host1, host2]
        mock_jobs = [MagicMock(), MagicMock()]
        mock_bgjob.side_effect = mock_jobs

        t = adb.SshAdbTunnel(hosts)
        with t.create():
            mock_bgjob.assert_has_calls([
                    call('ssh -v -N -L9222:localhost:22 host1',
                         nickname=ANY,
                         stderr_level=ANY,
                         stdout_tee=ANY,
                         stderr_tee=ANY),
                    call('ssh -v -N -L9223:localhost:22 host2',
                         nickname=ANY,
                         stderr_level=ANY,
                         stdout_tee=ANY,
                         stderr_tee=ANY),
            ])

            target1 = t.get_adb_target(host1)
            self.assertEqual(target1, 'localhost:9222')
            target2 = t.get_adb_target(host2)
            self.assertEqual(target2, 'localhost:9223')

        mock_nuke_subprocess.assert_has_calls([
                call(mock_jobs[0].sp),
                call(mock_jobs[1].sp),
        ])
        mock_join_bg_jobs.assert_called_once_with(mock_jobs)
