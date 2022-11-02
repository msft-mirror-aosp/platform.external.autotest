# Copyright 2021 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import logging
import re

from autotest_lib.client.common_lib import error
from autotest_lib.server.cros.faft.firmware_test import FirmwareTest
from autotest_lib.server.cros.faft.utils.elog_verifier import ElogVerifier


class CbmemVerifier:
    """Verifier for parsing cbmem firmware log."""

    def __init__(self, system, cmd):
        self.entries = system.run_shell_command_get_output(cmd, True)
        if not self.entries:
            raise error.TestError('Failed to retrieve cbmem log by %s' % cmd)

    def find_word(self, keyword=''):
        """Search for certain keyword in the whole cbmem firmware log."""
        output = [line for line in self.entries if keyword in line]
        logging.info('Search for %s in cbmem log, found %d matches', keyword,
                     len(output))
        return output


class firmware_MiniDiag(FirmwareTest):
    """Servo based MiniDiag firmware boot test."""
    version = 1

    def initialize(self, host, cmdline_args):
        super(firmware_MiniDiag, self).initialize(host, cmdline_args)

        if not self.menu_switcher:
            raise error.TestNAError('Test skipped for menuless UI')
        if not self.check_minidiag_capability():
            raise error.TestNAError('MiniDiag is not enabled for this board')
        # Need apreset to leave MiniDiag
        if not self.ec.has_command('apreset'):
            raise error.TestNAError('EC command apreset is not supported')

        self.switcher.setup_mode('normal')
        self.setup_usbkey(usbkey=False)

    def verify_elog(self):
        """Verify that event log contains MiniDiag launch."""
        verifier = ElogVerifier(self.faft_client.system)

        # Search for ELOG_DEPRECATED_TYPE_CROS_DIAGNOSTICS or
        # ELOG_TYPE_FW_VBOOT_INFO of diagnostic mode
        if not verifier.find_events(r'Launch Diagnostics|boot_mode=Diagnostic',
                                    2):
            raise error.TestError('No MiniDiag launch event detected')

        logging.info('Verify event log passed')

    def verify_cbmem(self):
        """Verify that cbmem log contains MiniDiag data."""
        cbmem_loss_msg = ' cbmem logs may be lost or incomplete'
        verifier = CbmemVerifier(self.faft_client.system, 'cbmem -2')

        # Verify storage health info by "<Storage health info>"
        # or "<Health info>"
        if not (verifier.find_word('<Storage health info>')
                or verifier.find_word('<Health info>')):
            raise error.TestError('No storage health info log found,' +
                                  cbmem_loss_msg)

        # Verify quick memory test by "<Memory check (quick)>"
        if not verifier.find_word('<Memory check (quick)>'):
            raise error.TestError('No quick memory test log found,' +
                                  cbmem_loss_msg)

        if verifier.find_word('Memory test failed:'):
            raise error.TestError('Quick memory test failed')

        output = verifier.find_word('memory_test_run_step')
        fmt = re.compile(
                r'([0-9]+) ms \(([0-9]+) bytes/us\) ... \(([0-9]+)%\)')
        for entry in output:
            # src/diag/memory.c:[line]:memory_test_run_step:[pattern_name]:
            # [memory range]: state
            _, _, _, _, _, state = entry.split(':')
            # [loop time] ms ([speed] bytes/us) ... ([percentage]%)
            _, speed, _ = fmt.search(state).groups()
            if int(speed) == 0:
                raise error.TestError('Memory test stuck')

        logging.info('Verify cbmem log passed')

    def run_once(self):
        """Method which actually runs the test."""
        # Trigger MiniDiag by menu navigation
        logging.info('Trigger MiniDiag by menu navigation')
        self.switcher.enable_rec_mode_and_reboot(usb_state='host')
        self.switcher.wait_for_client_offline()
        self.menu_switcher.trigger_rec_to_minidiag()

        # Navigator MiniDiag
        logging.info('Navigate among MiniDiag screens')
        self.menu_switcher.navigate_minidiag_quick_memory_check()
        self.menu_switcher.navigate_minidiag_storage()

        # Leave MiniDiag and reboot
        logging.info('Leave MiniDiag and reboot')
        self.menu_switcher.reset_and_leave_minidiag()
        logging.info('Expect normal mode boot, done')
        self.switcher.wait_for_client()

        # Verify logs
        if self.check_minidiag_capability(['event_log_launch_count']):
            logging.info('Verify event log for MiniDiag')
            self.verify_elog()
        else:
            logging.info('Skip verifying event log')

        if self.check_minidiag_capability(['cbmem_preserved_by_ap_reset']):
            logging.info('Verify cbmem log for MiniDiag')
            self.verify_cbmem()
        else:
            logging.info('Skip verifying cbmem log')
