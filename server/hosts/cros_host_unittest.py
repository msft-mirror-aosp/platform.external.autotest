#!/usr/bin/python2
# pylint: disable=missing-docstring

import mock
import unittest

import common

from autotest_lib.server.hosts import cros_host
from autotest_lib.server.hosts import servo_constants
from autotest_lib.server.hosts import host_info

CROSSYSTEM_RESULT = '''
fwb_tries              = 0                              # Fake comment
fw_vboot2              = 1                              # Fake comment
fwid                   = Google_Reef.9933.0.0           # Fake comment
fwupdate_tries         = 0                              #
fw_tried               = B                              #
fw_try_count           = 0                              #
'''

NON_UNI_LSB_RELEASE_OUTPUT = '''
CHROMEOS_RELEASE_BOARD=reef
'''

UNI_LSB_RELEASE_OUTPUT = '''
CHROMEOS_RELEASE_BOARD=coral
CHROMEOS_RELEASE_UNIBUILD=1
'''

SERVO_STATE_PREFIX = servo_constants.SERVO_STATE_LABEL_PREFIX


class MockCmd(object):
    """Simple mock command with base command and results"""

    def __init__(self, cmd, exit_status, stdout):
        self.cmd = cmd
        self.stdout = stdout
        self.exit_status = exit_status


class MockHost(cros_host.CrosHost):
    """Simple host for running mock'd host commands"""

    def __init__(self, *args):
        self._mock_cmds = {c.cmd: c for c in args}

    def run(self, command, **kwargs):
        """Finds the matching result by command value"""
        mock_cmd = self._mock_cmds[command]
        file_out = kwargs.get('stdout_tee', None)
        if file_out:
            file_out.write(mock_cmd.stdout)
        return mock_cmd


class GetPlatformModelTests(unittest.TestCase):
    """Unit tests for CrosHost.get_platform_model"""

    def test_cros_config_succeeds(self):
        host = MockHost(
                MockCmd('cat /etc/lsb-release', 0, UNI_LSB_RELEASE_OUTPUT),
                MockCmd('cros_config / name', 0, 'coral'))
        self.assertEqual(host.get_platform(), 'coral')

    def test_cros_config_resorts_to_fallback(self):
        host = MockHost(
                MockCmd('cat /etc/lsb-release', 0, UNI_LSB_RELEASE_OUTPUT),
                MockCmd('cros_config / name', 1, ''),
                MockCmd('mosys platform model', 0, 'coral'))
        self.assertEqual(host.get_platform(), 'coral')

    def test_cros_config_fails(self):
        host = MockHost(
                MockCmd('cat /etc/lsb-release', 0, UNI_LSB_RELEASE_OUTPUT),
                MockCmd('cros_config / name', 1, ''),
                MockCmd('mosys platform model', 1, ''),
                MockCmd('crossystem', 0, CROSSYSTEM_RESULT))
        self.assertEqual(host.get_platform(), 'reef')

    def test_non_unibuild(self):
        host = MockHost(
                MockCmd('cat /etc/lsb-release', 0, NON_UNI_LSB_RELEASE_OUTPUT),
                MockCmd('crossystem', 0, CROSSYSTEM_RESULT))
        self.assertEqual(host.get_platform(), 'reef')

    def test_cat_lsb_fails(self):
        host = MockHost(
                MockCmd('cat /etc/lsb-release', 1, ''),
                MockCmd('crossystem', 0, CROSSYSTEM_RESULT))
        self.assertEqual(host.get_platform(), 'reef')


class DictFilteringTestCase(unittest.TestCase):
    """Tests for dict filtering methods on CrosHost."""

    def test_get_chameleon_arguments(self):
        got = cros_host.CrosHost.get_chameleon_arguments({
            'chameleon_host': 'host',
            'spam': 'eggs',
        })
        self.assertEqual(got, {'chameleon_host': 'host'})

    def test_get_pdtester_arguments(self):
        got = cros_host.CrosHost.get_pdtester_arguments({
            'pdtester_host': 'host',
            'spam': 'eggs',
        })
        self.assertEqual(got, {'pdtester_host': 'host'})

    def test_get_servo_arguments(self):
        got = cros_host.CrosHost.get_servo_arguments({
            servo_constants.SERVO_HOST_ATTR: 'host',
            'spam': 'eggs',
        })
        self.assertEqual(got, {servo_constants.SERVO_HOST_ATTR: 'host'})


class DictFilteringTestCase(unittest.TestCase):
    """Test to verify servo_state was set-up as label in host_info_store"""

    def create_host(self):
        host = MockHost()
        host.servo = None
        host._servo_host = mock.Mock()
        host._servo_host.get_servo.return_value = 'Not Empty'
        host._servo_host.get_servo_state.return_value = 'SOME_STATE'
        host.host_info_store = host_info.InMemoryHostInfoStore()
        return host

    def test_do_not_update_label_when_servo_host_is_not_inited(self):
        host = self.create_host()
        host._servo_host = None

        host.set_servo_state('some_status')
        self.assertEqual(host.host_info_store.get().get_label_value(SERVO_STATE_PREFIX), 'some_status')

    def test_do_not_update_label_when_servo_state_is_None(self):
        host = self.create_host()

        host.set_servo_state(None)
        host._servo_host.get_servo_state.assert_not_called()
        self.assertEqual(host.host_info_store.get().get_label_value(SERVO_STATE_PREFIX), '')

    def test_repair_servo_set_servo_state_after_repair_when_repair_is_fail(self):
        host = self.create_host()
        host._servo_host.repair.side_effect = Exception('Something bad')

        try:
            host.repair_servo()
            self.assertEqual("Exception is", 'expecting to raise')
        except:
            pass
        host._servo_host.get_servo_state.assert_called()
        self.assertEqual(host.host_info_store.get().get_label_value(SERVO_STATE_PREFIX), 'SOME_STATE')

    def test_repair_servo_set_servo_state_after_repair_when_repair_is_not_fail(self):
        host = self.create_host()
        try:
            host.repair_servo()
        except:
            self.assertEqual("Exception is not", 'expected')
            pass
        host._servo_host.get_servo_state.assert_called()
        self.assertEqual(host.host_info_store.get().get_label_value(SERVO_STATE_PREFIX), 'SOME_STATE')

    def test_set_servo_host_update_servo_state_when_host_exist(self):
        host = self.create_host()
        host._servo_host = mock.Mock()
        host._servo_host.get_servo.return_value = 'Not Empty'
        host._servo_host.get_servo_state.return_value = 'SOME_STATE'
        self.assertEqual(host.host_info_store.get().get_label_value(SERVO_STATE_PREFIX), '')

        try:
            host.repair_servo()
        except:
            self.assertEqual("Exception is not", 'expected')
            pass
        host._servo_host.get_servo_state.assert_called()
        self.assertEqual(host.host_info_store.get().get_label_value(SERVO_STATE_PREFIX), 'SOME_STATE')

    def test_set_servo_host_use_passed_servo_state_when_host_is_None(self):
        host = self.create_host()

        host.set_servo_host(None, 'passed_State')
        self.assertEqual(host.host_info_store.get().get_label_value(SERVO_STATE_PREFIX), 'passed_State')

    def test_set_servo_host_use_servo_state_from_host_when_host_is_passed(self):
        host = self.create_host()
        servo_host = mock.Mock()
        servo_host.get_servo.return_value = 'Not Empty'
        servo_host.get_servo_state.return_value = 'state_of_host'

        host.set_servo_host(servo_host)
        self.assertEqual(host.host_info_store.get().get_label_value(SERVO_STATE_PREFIX), 'state_of_host')

        servo_host.get_servo_state.return_value = 'state_of_host2'
        host.set_servo_host(servo_host, 'passed_State')
        self.assertEqual(host.host_info_store.get().get_label_value(SERVO_STATE_PREFIX), 'state_of_host2')

if __name__ == "__main__":
    unittest.main()

