# Copyright (c) 2011 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import logging
import time

from autotest_lib.server.cros.faft.firmware_test import FirmwareTest


class firmware_FwScreenPressPower(FirmwareTest):
    """
    Servo based power button triggered shutdown test during firmware screens.

    This test requires a USB disk plugged-in, which contains a Chrome OS test
    image (built by "build_image --test"). On runtime, this test triggers
    firmware screens (developer, remove, insert, yuck, and to_norm screens),
    and then presses the power button in order to power the machine down.
    """
    version = 1

    SHORT_SHUTDOWN_CONFIRMATION_PERIOD = 0.1

    def wait_second_screen_and_press_power(self):
        """Wait and trigger a second screen and press power button."""
        self.wait_fw_screen_and_trigger_recovery()
        self.wait_longer_fw_screen_and_press_power()

    def wait_yuck_screen_and_press_power(self):
        """Insert corrupted USB for yuck screen and press power button."""
        # This USB stick will be removed in cleanup phase.
        self.servo.switch_usbkey('dut')
        time.sleep(self.faft_config.load_usb)
        self.wait_longer_fw_screen_and_press_power()

    def initialize(self, host, cmdline_args):
        super(firmware_FwScreenPressPower, self).initialize(host, cmdline_args)
        self.assert_test_image_in_usb_disk()
        self.switcher.setup_mode('dev')
        self.servo.switch_usbkey('host')
        usb_dev = self.servo.probe_host_usb_dev()
        # Corrupt the kernel of USB stick. It is needed for triggering a
        # yuck screen later.
        self.corrupt_usb_kernel(usb_dev)

    def cleanup(self):
        self.servo.switch_usbkey('host')
        usb_dev = self.servo.probe_host_usb_dev()
        # Restore the kernel of USB stick which is corrupted on setup phase.
        self.restore_usb_kernel(usb_dev)
        super(firmware_FwScreenPressPower, self).cleanup()

    def run_once(self):
        logging.info("Expected dev mode and reboot. "
                     "When the next DEVELOPER SCREEN shown, press power button "
                     "to make DUT shutdown.")
        self.check_state((self.checkers.crossystem_checker, {
                              'devsw_boot': '1',
                              'mainfw_type': 'developer',
                              }))
        self.reboot_warm(wait_for_dut_up=False)
        self.run_shutdown_process(self.wait_fw_screen_and_press_power,
                                  None,
                                  self.wait_fw_screen_and_ctrl_d)
        self.wait_for_client()

        logging.info("Reboot. When the developer screen shown, press "
                     "enter key to trigger either TO_NORM screen (new) or "
                     "RECOVERY INSERT screen (old). Then press power button to "
                     "make DUT shutdown.")
        self.check_state((self.checkers.crossystem_checker, {
                              'devsw_boot': '1',
                              'mainfw_type': 'developer',
                              }))
        self.reboot_warm(wait_for_dut_up=False)
        self.run_shutdown_process(self.wait_second_screen_and_press_power,
                                  None,
                                  self.wait_fw_screen_and_ctrl_d,
                                  self.SHORT_SHUTDOWN_CONFIRMATION_PERIOD)
        self.wait_for_client()

        logging.info("Request recovery boot. When the RECOVERY INSERT "
                     "screen shows, press power button to make DUT shutdown.")
        self.check_state((self.checkers.crossystem_checker, {
                              'devsw_boot': '1',
                              'mainfw_type': 'developer',
                              }))
        self.faft_client.system.request_recovery_boot()
        self.reboot_warm(wait_for_dut_up=False)
        self.run_shutdown_process(self.wait_longer_fw_screen_and_press_power,
                                  None,
                                  self.wait_fw_screen_and_ctrl_d,
                                  self.SHORT_SHUTDOWN_CONFIRMATION_PERIOD)
        self.wait_for_client()

        logging.info("Request recovery boot again. When the recovery "
                     "insert screen shows, insert a corrupted USB and trigger "
                     "a YUCK SCREEN. Then press power button to "
                     "make DUT shutdown.")
        self.check_state((self.checkers.crossystem_checker, {
                              'devsw_boot': '1',
                              'mainfw_type': 'developer',
                              }))
        self.faft_client.system.request_recovery_boot()
        self.reboot_warm(wait_for_dut_up=False)
        self.run_shutdown_process(self.wait_yuck_screen_and_press_power,
                                  None,
                                  self.wait_fw_screen_and_ctrl_d,
                                  self.SHORT_SHUTDOWN_CONFIRMATION_PERIOD)
        self.wait_for_client()

        logging.info("Switch back to normal mode.")
        self.check_state((self.checkers.crossystem_checker, {
                              'devsw_boot': '1',
                              'mainfw_type': 'developer',
                              }))
        self.switcher.reboot_to_mode(to_mode='normal')

        logging.info("Expected normal mode and request recovery boot. "
                     "Because an USB stick is inserted, a RECOVERY REMOVE "
                     "screen shows. Press power button to make DUT shutdown.")
        self.check_state((self.checkers.crossystem_checker, {
                              'devsw_boot': '0',
                              'mainfw_type': 'normal',
                              }))
        self.faft_client.system.request_recovery_boot()
        self.reboot_warm(wait_for_dut_up=False)
        self.run_shutdown_process(self.wait_longer_fw_screen_and_press_power,
                                  None,
                                  None,
                                  self.SHORT_SHUTDOWN_CONFIRMATION_PERIOD)
        self.wait_for_client()

        logging.info("Check and done.")
        self.check_state((self.checkers.crossystem_checker, {
                              'devsw_boot': '0',
                              'mainfw_type': 'normal',
                              }))
