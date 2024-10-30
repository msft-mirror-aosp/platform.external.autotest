# Copyright 2024 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import logging

from autotest_lib.client.common_lib import error
from autotest_lib.server.cros.faft.firmware_test import FirmwareTest


class firmware_GSCStraps(FirmwareTest):
    """Verify GSC can read the straps after reset."""

    version = 1

    # Wait up to 10 seconds for GSC to reset
    WAIT_FOR_RESET = 10
    # Error strings for invalid straps
    INVALID_STRAP_ERRORS = [
            # Cr50 Error messages
            ['Ambiguous strap cfg', True],
            ['ERROR INVALID STRAP PINS', True],
            # Ti50 Error messages
            ['Invalid strap', True],
    ]

    def run_once(self, host):
        """Check GSC can read straps after reset."""
        if not self.gsc:
            return error.TestNAError('Only supported on devices with GSC')
        self.host = host
        try:
            logging.info('Checking straps after GSC reboot')
            # Schedule a GSC reboot in 1000 ms
            self.host.run('gsctool -a --reboot 1000', ignore_timeout=True)
            self.gsc.wait_for_reboot(timeout=self.WAIT_FOR_RESET)
            self.gsc.check_for_console_errors('invalid straps after reboot',
                                              self.INVALID_STRAP_ERRORS)
            if not self.servo.has_control('gsc_reset'):
                return
            logging.info('Checking straps after GSC power-on reest')
            self.servo.set_nocheck('gsc_reset', 'on')
            self.servo.set_nocheck('gsc_reset', 'off')
            self.gsc.wait_for_reboot(timeout=self.WAIT_FOR_RESET)
            self.gsc.check_for_console_errors(
                    'invalid straps after power-on reset',
                    self.INVALID_STRAP_ERRORS)
        finally:
            self._try_to_bring_dut_up()
