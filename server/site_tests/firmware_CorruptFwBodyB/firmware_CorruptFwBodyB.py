# Copyright 2011 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# TODO(b/343308344): Remove from PVS testplans and remove this file.

import logging

from autotest_lib.server.cros.faft.firmware_test import FirmwareTest
from autotest_lib.server.cros.faft.firmware_test import ConnectionError


class firmware_CorruptFwBodyB(FirmwareTest):
    """
    Servo based firmware body B corruption test.

    The RW firmware B corruption will result booting the firmware A.
    """
    version = 1

    def initialize(self, host, cmdline_args, dev_mode=False):
        super(firmware_CorruptFwBodyB, self).initialize(host, cmdline_args)
        self.backup_firmware()
        self.switcher.setup_mode('dev' if dev_mode else 'normal',
                                 allow_gbb_force=True)
        self.setup_usbkey(usbkey=False)

    def cleanup(self):
        try:
            if self.is_firmware_saved():
                self.restore_firmware()
        except ConnectionError:
            logging.error("ERROR: DUT did not come up.  Need to cleanup!")
        super(firmware_CorruptFwBodyB, self).cleanup()

    def run_once(self):
        """Runs a single iteration of the test."""
        logging.info("Corrupt firmware body B.")
        self.check_state((self.checkers.fw_tries_checker, 'A'))
        offset_b, byte_b = self.faft_client.bios.get_body_one_byte('b')
        self.faft_client.bios.modify_body('b', offset_b, byte_b + 1)
        self.switcher.mode_aware_reboot()

        logging.info("Expected firmware A boot and set fw_try_next to B.")
        self.check_state((self.checkers.fw_tries_checker, 'A'))
        self.faft_client.system.set_fw_try_next('B', 1)
        self.switcher.mode_aware_reboot()

        logging.info("Still expected A boot since B is corrupted. "
                     "Restore B later.")
        self.check_state((self.checkers.fw_tries_checker, 'A'))
        self.faft_client.bios.modify_body('b', offset_b, byte_b)
        self.switcher.mode_aware_reboot()

        logging.info("Final check and done.")
        self.check_state((self.checkers.fw_tries_checker, 'A'))
