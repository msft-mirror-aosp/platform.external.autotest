# Copyright 2016 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import logging
import re

from autotest_lib.client.common_lib import error
from autotest_lib.server.cros.faft.firmware_test import FirmwareTest
from autotest_lib.server.cros.servo import pd_console


class firmware_PDProtocol(FirmwareTest):
    """
    Servo based USB PD protocol test.

    A charger must be connected to the DUT for this test.

    This test checks that when an appropriate zinger charger is connected that
    the PD is properly negotiated in dev mode and when booted from a test image
    through recovery that the PD is not negotiated.

    Example:
    PD Successfully negotiated
    - ServoV4 in SRC_READY or SNK_READY state

    PD not negotiated
    - ServoV4 in SRC_DISCOVERY or SNK_DISCOVERY state

    """
    version = 1
    NEEDS_SERVO_USB = True

    PD_NOT_SUPPORTED_PATTERN = 'INVALID_COMMAND'

    def initialize(self, host, cmdline_args, ec_wp=None):
        """Initialize the test"""
        super(firmware_PDProtocol, self).initialize(host, cmdline_args)
        self._setup_ec_write_protect(ec_wp)

        self.check_if_pd_supported()
        self.switcher.setup_mode('dev')
        # The USB disk is used for recovery. But this test wants a fine-grained
        # control, i.e. swapping the role just before booting into recovery,
        # not swapping here. So set used_for_recovery=False.
        self.setup_usbkey(usbkey=True, host=False, used_for_recovery=False)

        self.original_dev_boot_usb = self.faft_client.system.get_dev_boot_usb()
        logging.info('Original dev_boot_usb value: %s',
                     str(self.original_dev_boot_usb))

        self.hw_wp = self.servo.get('fw_wp_state')
        self.sw_wp = self.faft_client.ec.get_write_protect_status()
        logging.info('hw_wp=%s, sw_wp=%s', self.hw_wp, self.sw_wp)

    def cleanup(self):
        """Cleanup the test"""
        if hasattr(self, 'original_dev_boot_usb'):
            self.ensure_dev_internal_boot(self.original_dev_boot_usb)
        self._restore_ec_write_protect()
        if (self.servo.has_control('cold_reset_select')
                    and hasattr(self, 'cold_reset_select')):
            self.servo.set('cold_reset_select', self.cold_reset_select)
        super(firmware_PDProtocol, self).cleanup()

    def _setup_ec_write_protect(self, ec_wp):
        """Setup for EC write-protection.

        It makes sure the EC in the requested write-protection state. If not, it
        flips the state. Flipping the write-protection requires DUT reboot.

        @param ec_wp: True to request EC write-protected; False to request EC
                      not write-protected; None to do nothing.
        """
        if ec_wp is None:
            return
        # The default c2d2 cold_reset will reboot GSC, and this breaks the
        # hardware write protect.  If available, set cold_reset to
        # gsc_ecrst_pulse. This should always be available on c2d2 platforms.
        if (self.servo.has_control('cold_reset_select')
                    and self.servo.has_control('gsc_ecrst_pulse')):
            self.cold_reset_select = self.servo.get('cold_reset_select')
            self.servo.set('cold_reset_select', 'gsc_ecrst_pulse')
        self._old_wpsw_cur = self.checkers.crossystem_checker(
                {'wpsw_cur': '1'}, suppress_logging=True)
        if not self.faft_config.ap_access_ec_flash:
            raise error.TestNAError(
                    "Cannot change EC write-protect for this device")

        logging.info(
                'The test required EC is %swrite-protected. Reboot '
                'and flip the state.', '' if ec_wp else 'not ')
        self.switcher.mode_aware_reboot(
                'custom', lambda: self.set_ec_write_protect_and_reboot(ec_wp))
        wpsw_cur = '1' if ec_wp else '0'
        self.check_state((self.checkers.crossystem_checker, {
                'wpsw_cur': wpsw_cur
        }))

    def _restore_ec_write_protect(self):
        """Restore the original EC write-protection."""
        if (not hasattr(self,
                        '_old_wpsw_cur')) or (self._old_wpsw_cur is None):
            return
        if not self.checkers.crossystem_checker(
                {'wpsw_cur': '1' if self._old_wpsw_cur else '0'},
                suppress_logging=True):
            logging.info('Restore original EC write protection and reboot.')
            self.switcher.mode_aware_reboot(
                    'custom', lambda: self.set_ec_write_protect_and_reboot(
                            self._old_wpsw_cur))
        self.check_state((self.checkers.crossystem_checker, {
                'wpsw_cur': '1' if self._old_wpsw_cur else '0'
        }))

    def check_if_pd_supported(self):
        """ Checks if the DUT responds to ectool usbpdpower and skips the test
        if it isn't supported on the device.
        """
        output = self.run_command('ectool usbpdpower')

        if (not output or
            self.check_ec_output(output, self.PD_NOT_SUPPORTED_PATTERN)):
            raise error.TestNAError("PD not supported skipping test.")

    def boot_to_recovery(self):
        """Boot device into recovery mode."""
        logging.info('Reboot into Recovery...')
        self.switcher.reboot_to_mode(to_mode='rec')

        self.check_state((self.checkers.crossystem_checker,
                          {'mainfw_type': 'recovery'}))

    def run_command(self, command):
        """Runs the specified command and returns the output
        as a list of strings.

        @param command: The command to run on the DUT
        @return A list of strings of the command output
        """
        logging.info('Command to run: %s', command)

        output = self.faft_client.system.run_shell_command_get_output(command)

        logging.info('Command output: %s', output)

        return output

    def check_ec_output(self, output, pattern):
        """Checks if any line in the output matches the given pattern.

        @param output: A list of strings containg the output to search
        @param pattern: The regex to search the output for

        @return True upon first match found or False
        """
        logging.info('Checking %s for %s.', output, pattern)

        for line in output:
            if bool(re.search(pattern, line)):
                return True

        return False

    def run_once(self, host):
        """Main test logic"""
        # TODO(b/35573842): Refactor to use PDPortPartner to probe the port
        self.pdtester_port = 1 if 'servo_v4' in self.pdtester.servo_type else 0
        self.pdtester_pd_utils = pd_console.create_pd_console_utils(
                                 self.pdtester)

        self.ensure_dev_internal_boot(self.original_dev_boot_usb)

        # Check servo_v4 is negotiated
        if self.pdtester_pd_utils.is_disconnected(self.pdtester_port):
            raise error.TestNAError('PD not connected')

        # TODO(b:152148025): Directly set role as pdsnkdts might fail the
        # PD communication. In short term, we could use PR SWAP instead, and
        # should also fix the TCPM for handling SRCDTS -> SNKDTS case.
        if host.has_battery():
            self.set_servo_v4_role_to_snk(pd_comm=True)
        self.boot_to_recovery()

        # Check PD is not negotiated
        # We allow the chromebox/chromebase, to enable the PD in the
        # recovery mode.
        if (host.get_board_type() != 'CHROMEBOX'
                    and host.get_board_type() != 'CHROMEBASE'
                    and not self.pdtester_pd_utils.is_snk_discovery_state(
                            self.pdtester_port)):
            raise error.TestFail('Expect PD to be disabled, WP (HW/SW) %s/%s' %
                                 (self.hw_wp, self.sw_wp))

        # Check WP status. Only both SW/HW WP on should pass the test.
        if (not self.sw_wp) or ('off' in self.hw_wp):
            raise error.TestFail(
                'Expect HW and SW WP on, got hw_wp=%s, sw_wp=%s' %
                (self.hw_wp, self.sw_wp))
