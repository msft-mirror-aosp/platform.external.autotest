# Copyright 2021 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import logging

from autotest_lib.client.common_lib import error
from autotest_lib.server.cros.faft.firmware_test import FirmwareTest


class firmware_MiniDiag(FirmwareTest):
    """
    Servo based diagnostics firmware boot test.
    """
    version = 1

    def initialize(self, host, cmdline_args, ec_wp=None):
        super(firmware_MiniDiag, self).initialize(host,
                                                  cmdline_args,
                                                  ec_wp=ec_wp)

        self.switcher.setup_mode('normal')
        self.setup_usbkey(usbkey=False)

    def run_once(self):
        """Method which actually runs the test."""
        self.check_state((self.checkers.mode_checker, 'normal'))

        # Verify if minidiag is enabled
        if not self.faft_config.minidiag_enabled:
            raise error.TestNAError('Minidiag is not enabled for this board')

        # Minidiag support menu_switcher only
        if self.faft_config.mode_switcher_type != 'menu_switcher':
            raise error.TestNAError('Test is only applicable to menu_switcher')

        # Trigger minidiag by menu navigation
        logging.info('Trigger minidiag by menu navigation.')
        self.switcher.enable_rec_mode_and_reboot(usb_state='host')
        self.switcher.wait_for_client_offline()
        self.menu_switcher.trigger_rec_to_minidiag()

        # Navigator minidiag
        logging.info('Navigate among minidiag screens.')
        self.menu_switcher.navigate_minidiag_storage()
        self.menu_switcher.navigate_minidiag_quick_memory_check()

        # Leave minidiag and reboot
        logging.info('Leave minidiag and reboot.')
        self.menu_switcher.reset_and_leave_minidiag()
        logging.info('Expected normal mode boot, done.')
        self.check_state((self.checkers.mode_checker, 'normal'))
