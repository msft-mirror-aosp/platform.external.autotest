# Copyright 2011 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# TODO(b/343308765): Remove from PVS testplans and remove this file.

import logging

from autotest_lib.server.cros.faft.firmware_test import FirmwareTest
from autotest_lib.server.cros.faft.firmware_test import ConnectionError


class firmware_CorruptFwSigA(FirmwareTest):
    """
    Servo based firmware signature A corruption test.
    """
    version = 1

    def initialize(self, host, cmdline_args, dev_mode=False):
        super(firmware_CorruptFwSigA, self).initialize(host, cmdline_args)
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
        super(firmware_CorruptFwSigA, self).cleanup()

    def run_once(self):
        """Runs a single iteration of the test."""
        logging.info("Corrupt firmware signature A.")
        self.check_state((self.checkers.fw_tries_checker, 'A'))
        offset_a, byte_a = self.faft_client.bios.get_sig_one_byte('a')
        self.faft_client.bios.modify_sig('a', offset_a, byte_a + 1)
        self.switcher.mode_aware_reboot()

        logging.info("Expected firmware B boot and set fw_try_next to B.")
        self.check_state((self.checkers.fw_tries_checker, 'B'))

        self.faft_client.system.set_fw_try_next('B')
        self.switcher.mode_aware_reboot()

        logging.info("Still expected firmware B boot and restore firmware A.")
        self.check_state((self.checkers.fw_tries_checker, 'B'))
        self.faft_client.bios.modify_sig('a', offset_a, byte_a)
        self.switcher.mode_aware_reboot()

        logging.info("Expected firmware B boot, done.")
        self.check_state((self.checkers.fw_tries_checker, 'B'))
