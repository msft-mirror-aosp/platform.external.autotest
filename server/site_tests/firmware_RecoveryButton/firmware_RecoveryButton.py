# Copyright (c) 2011 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import logging

from autotest_lib.server.cros import vboot_constants as vboot
from autotest_lib.server.cros.faft.firmware_test import FirmwareTest


class firmware_RecoveryButton(FirmwareTest):
    """
    Servo based recovery button test.

    This test requires a USB disk plugged-in, which contains a Chrome OS test
    image (built by "build_image --test"). On runtime, this test emulates
    recovery button pressed and reboots. It then triggers recovery mode by
    unplugging and plugging in the USB disk and checks success of it.
    """
    version = 1

    def ensure_normal_boot(self):
        """Ensure normal mode boot this time.

        If not, it may be a test failure during step 2, try to recover to
        normal mode by setting no recovery mode and rebooting the machine.
        """
        if not self.checkers.crossystem_checker(
                {'mainfw_type': ('normal', 'developer')}):
            self.servo.disable_recovery_mode()
            self.reboot_warm()

    def initialize(self, host, cmdline_args, dev_mode=False, ec_wp=None):
        super(firmware_RecoveryButton, self).initialize(host, cmdline_args,
                                                        ec_wp=ec_wp)
        self.switcher.setup_mode('dev' if dev_mode else 'normal')
        self.setup_usbkey(usbkey=True, host=False)

    def cleanup(self):
        self.ensure_normal_boot()
        super(firmware_RecoveryButton, self).cleanup()

    def run_once(self, dev_mode=False):
        logging.info("Switch to recovery mode and reboot.")
        self.check_state((self.checkers.crossystem_checker, {
                    'mainfw_type': 'developer' if dev_mode else 'normal',
                    }))
        self.switcher.reboot_to_mode(to_mode='rec',
                                     from_mode='dev' if dev_mode else 'normal')

        logging.info("Expected recovery boot and reboot.")
        self.check_state((self.checkers.crossystem_checker, {
                    'mainfw_type': 'recovery',
                    'recovery_reason': vboot.RECOVERY_REASON['RO_MANUAL'],
                    }))
        self.reboot_warm()

        logging.info("Expected normal boot.")
        self.check_state((self.checkers.crossystem_checker, {
                    'mainfw_type': 'developer' if dev_mode else 'normal',
                    }))
