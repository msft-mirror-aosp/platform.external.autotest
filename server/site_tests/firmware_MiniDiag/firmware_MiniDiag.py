# Copyright 2021 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import logging
import re

from autotest_lib.client.common_lib import error
from autotest_lib.client.common_lib import utils
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

    STORAGE_HEALTH_INFO_STR = 'Storage health info'
    MEMORY_CHECK_QUICK_STR = 'Memory check (quick)'

    def initialize(self, host, cmdline_args):
        super(firmware_MiniDiag, self).initialize(host, cmdline_args)

        if not self.menu_switcher:
            raise error.TestNAError('Test skipped for menuless UI')
        if not self.check_minidiag_capability():
            raise error.TestNAError('MiniDiag is not enabled for this board')

        self.switcher.setup_mode('normal')
        self.setup_usbkey(usbkey=False)

    def verify_elog_launch_count(self):
        """Verify that event log contains MiniDiag launch."""
        elog_verifier = ElogVerifier(self.faft_client.system)

        # Search for ELOG_DEPRECATED_TYPE_CROS_DIAGNOSTICS or
        # ELOG_TYPE_FW_VBOOT_INFO of diagnostic mode
        if not elog_verifier.find_events(
                r'Launch Diagnostics|boot_mode=Diagnostic', 2):
            raise error.TestError('No MiniDiag launch event detected')

        logging.info('Event log launch count verified')

    def verify_cbmem(self):
        """Verify that cbmem log contains MiniDiag data."""
        cbmem_loss_msg = ' cbmem logs may be lost or incomplete'
        verifier = CbmemVerifier(self.faft_client.system, 'cbmem -2')

        # Verify storage health info by "<Storage health info>"
        # or "<Health info>"
        if not (verifier.find_word(
                '<' + self.STORAGE_HEALTH_INFO_STR + '> menu')
                or verifier.find_word('<Health info> menu')):
            raise error.TestError('No storage health info log found,' +
                                  cbmem_loss_msg)

        # Verify quick memory test by "<Memory check (quick)>"
        if not verifier.find_word('<' + self.MEMORY_CHECK_QUICK_STR + '> menu'):
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

        logging.info('Cbmem log verified')

    def _verify_elog_test_report_event(self, match, type_str, result_str):
        logging.info(
                'Expect an event with type=%s and result=%s...',
                type_str, result_str)
        if match[0].lower() != type_str.lower() or match[1] != result_str:
            raise error.TestError(
                    'Error: got type=%s and result=%s',
                    match[0], match[1])

    def verify_elog_test_report(self):
        """Verify that event log contains MiniDiag test report."""
        elog_verifier = ElogVerifier(self.faft_client.system)

        EVENT_PATTERN = 'type=([\w \(\)]+), result=(\w+), time=([\d]+m[\d]+s)'
        event_pattern = re.compile(EVENT_PATTERN)

        elog_events = elog_verifier.find_events(
                r'Diagnostics Mode | Diagnostics Logs', 2)
        if len(elog_events) != 1:
            raise error.TestError(
                    'Expect 1 elog test report, but got %d', len(elog_events))

        events = event_pattern.findall(elog_events[0])

        if len(events) != 2:
            raise error.TestError(
                    'Expect 2 events in the report, but got %d', len(events))

        # Event #0 should be a passed Storage Health Info
        self._verify_elog_test_report_event(
                events[0], self.STORAGE_HEALTH_INFO_STR, 'Passed')
        # Event #1 should be an aborted Memory Check (quick)
        self._verify_elog_test_report_event(
                events[1], self.MEMORY_CHECK_QUICK_STR, 'Aborted')

        logging.info('Event log test report verified')

    def launch_minidiag(self):
        """Launch MiniDiag, navigate, and back to the OS."""
        # Trigger MiniDiag by menu navigation
        logging.info('Trigger MiniDiag by menu navigation')
        self.switcher.enable_rec_mode_and_reboot(usb_state='host')
        self.switcher.wait_for_client_offline()
        self.menu_switcher.trigger_rec_to_minidiag()

        # Navigate MiniDiag
        logging.info('Navigate among MiniDiag screens')
        self.menu_switcher.navigate_minidiag_quick_memory_check()
        self.menu_switcher.navigate_minidiag_storage()

        logging.info('MiniDiag navigation finished')

    def run_once(self):
        """Method which actually runs the test."""
        # Check which type of reset we need
        need_warm_reset = self.check_minidiag_capability(
                ['cbmem_preserved_by_ap_reset'])
        need_power_off = self.check_minidiag_capability(
                ['event_log_test_report'])

        # Warm reset: This preserves cbmem
        # This will not trigger writing test report to event log, so we need two
        # phases of MiniDiag navigation.
        if need_warm_reset:
            logging.info('Launch MiniDiag and leave with warm reset')
            self.launch_minidiag()
            self.switcher.simple_reboot(reboot_type='warm',
                                        sync_before_boot=False)
            self.switcher.wait_for_client()

            # Verify logs
            logging.info('Verify cbmem log for MiniDiag')
            self.verify_cbmem()
        else:
            logging.info('Skip verifying with warm reset')

        # Power off: This triggers writing test report to event log
        # We should at least navigate MiniDiag once
        if need_power_off or not need_warm_reset:
            logging.info('Launch MiniDiag and leave with power off')
            self.launch_minidiag()
            self.run_shutdown_process(
                    shutdown_action=utils.wrapped_partial(
                            self.menu_switcher.power_off,
                            wait_for_screen=False),
                    post_power_action=self.switcher.wait_for_client)

            # Verify logs
            if need_power_off:
                logging.info('Verify event log test report for MiniDiag')
                self.verify_elog_test_report()
            else:
                logging.info('Skip verifying event log test report')
        else:
            logging.info('Skip verifying with power off')

        # Verify event log launch count.
        if self.check_minidiag_capability(['event_log_launch_count']):
            logging.info('Verify event log launch count for MiniDiag')
            self.verify_elog_launch_count()
        else:
            logging.info('Skip verifying event log launch count')
