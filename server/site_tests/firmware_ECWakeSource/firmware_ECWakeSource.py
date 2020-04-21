# Copyright (c) 2012 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import logging
import time

from autotest_lib.client.common_lib import error
from autotest_lib.server import autotest
from autotest_lib.server.cros.faft.firmware_test import FirmwareTest
from autotest_lib.server.cros.faft.firmware_test import ConnectionError
from autotest_lib.server.cros.servo import servo


class firmware_ECWakeSource(FirmwareTest):
    """
    Servo based EC wake source test.
    """
    version = 1

    # The timeout (in seconds) to confirm the device is woken up from
    # suspend mode.
    RESUME_TIMEOUT = 60

    def initialize(self, host, cmdline_args):
        super(firmware_ECWakeSource, self).initialize(host, cmdline_args)
        # Only run in normal mode
        self.switcher.setup_mode('normal')

    def cleanup(self):
        # Restore the lid_open switch in case the test failed in the middle.
        self.servo.set('lid_open', 'yes')
        super(firmware_ECWakeSource, self).cleanup()

    def hibernate_and_wake_by_power_button(self):
        """Shutdown to G3/S5, hibernate EC, and then wake by power button."""
        self.run_shutdown_cmd()
        self.switcher.wait_for_client_offline()
        self.ec.send_command('hibernate 1000')
        time.sleep(self.WAKE_DELAY)
        # If the DUT enters hibernate mode successfully, EC console shouldn't
        # be responsive.
        if self.is_ec_console_responsive():
            raise error.TestFail('The DUT is not in hibernate mode.')
        self.servo.power_short_press()
        self.switcher.wait_for_client()

    def is_ec_console_responsive(self):
        """Test if EC console is responsive."""
        try:
            self.ec.send_command_get_output('help', ['.*>'])
            return True
        except servo.UnresponsiveConsoleError:
            return False

    def wake_by_lid_switch(self):
        """Wake up the device by lid switch."""
        self.servo.set('lid_open', 'no')
        time.sleep(self.LID_DELAY)
        self.servo.set('lid_open', 'yes')

    def suspend_and_wake(self, suspend_func, wake_func):
        """Suspend and then wake up the device.

        Args:
            suspend_func: The method used to suspend the device
            wake_func: The method used to resume the device
        """
        suspend_func()
        self.switcher.wait_for_client_offline()
        wake_func()
        self.switcher.wait_for_client(timeout=self.RESUME_TIMEOUT)

    def run_once(self, host):
        """Runs a single iteration of the test."""
        # Login as a normal user and stay there, such that closing lid triggers
        # suspend, instead of shutdown.
        autotest_client = autotest.Autotest(host)
        autotest_client.run_test('desktopui_SimpleLogin',
                                 exit_without_logout=True)
        original_boot_id = host.get_boot_id()

        logging.info('Suspend and wake by power button.')
        self.suspend_and_wake(self.suspend, self.servo.power_normal_press)

        if not self.check_ec_capability(['keyboard']):
            logging.info('The device has no internal keyboard. '
                         'Skip testing suspend/resume by internal keyboard.')
        else:
            logging.info('Suspend and wake by internal key press.')
            self.suspend_and_wake(self.suspend,
                                  lambda:self.ec.key_press('<enter>'))

        logging.info('Suspend and wake by USB HID key press.')
        try:
            self.suspend_and_wake(self.suspend,
                    lambda:self.servo.set_nocheck('usb_keyboard_enter_key',
                                                  'press'))
        except ConnectionError:
            raise error.TestFail('USB HID suspend/resume fails. Maybe try to '
                    'update firmware for Atmel USB KB emulator by running '
                    'firmware_FlashServoKeyboardMap test and then try again?')

        if not self.check_ec_capability(['lid']):
            logging.info('The device has no lid. '
                         'Skip testing suspend/resume by lid switch.')
        else:
            logging.info('Suspend and wake by lid switch.')
            self.suspend_and_wake(self.suspend, self.wake_by_lid_switch)
            logging.info('Close lid to suspend and wake by lid switch.')
            self.suspend_and_wake(lambda:self.servo.set('lid_open', 'no'),
                                  self.wake_by_lid_switch)

        boot_id = host.get_boot_id()
        if boot_id != original_boot_id:
            raise error.TestFail('Different boot_id. Unexpected reboot.')

        if self.servo.main_device_is_ccd():
            logging.info('Using CCD, ignore waking by power button.')
        else:
            logging.info('EC hibernate and wake by power button.')
            self.hibernate_and_wake_by_power_button()
