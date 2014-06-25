# Copyright (c) 2011 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import logging

from autotest_lib.server.cros.faft.firmware_test import FirmwareTest


class firmware_CorruptFwSigB(FirmwareTest):
    """
    Servo based firmware signature B corruption test.
    """
    version = 1

    def initialize(self, host, cmdline_args, dev_mode=False):
        super(firmware_CorruptFwSigB, self).initialize(host, cmdline_args)
        self.backup_firmware()
        self.setup_dev_mode(dev_mode)
        self.setup_usbkey(usbkey=False)

    def cleanup(self):
        self.restore_firmware()
        super(firmware_CorruptFwSigB, self).cleanup()

    def run_once(self):
        logging.info("Expected firmware A boot and corrupt "
                     "firmware signature B.")
        self.check_state((self.checkers.crossystem_checker, {
                              'mainfw_act': 'A',
                              'tried_fwb': '0',
                              }))
        self.faft_client.bios.corrupt_sig('b')
        self.reboot_warm()

        logging.info("Expected firmware A boot and set try_fwb flag.")
        self.check_state((self.checkers.crossystem_checker, {
                              'mainfw_act': 'A',
                              'tried_fwb': '0',
                              }))
        if self.fw_vboot2:
            self.faft_client.system.set_fw_try_next('B')
        else:
            self.faft_client.system.set_try_fw_b()
        self.reboot_warm()

        logging.info("Expected firmware A boot and restore firmware B.")
        self.check_state((self.checkers.crossystem_checker, {
                              'mainfw_act': 'A',
                              'tried_fwb': '0' if self.fw_vboot2 else '1',
                              }))
        self.faft_client.bios.restore_sig('b')
        self.reboot_warm()

        logging.info("Final check and done.")
        self.check_state((self.checkers.crossystem_checker, {
                              'mainfw_act': 'A',
                              'tried_fwb': '0',
                              }))
