# Copyright 2022 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from autotest_lib.client.common_lib import error
from autotest_lib.server.cros.faft.firmware_test import FirmwareTest

import logging
import time


class firmware_Cr50OpenTPMRstDebounce(FirmwareTest):
    """Verify cr50 can open ccd when TPM_RST_L is debounced."""
    version = 1

    BRDPROP_SYSRST = 'BOARD_NEEDS_SYS_RST_PULL_UP'

    def setup_tpm_rst_debouncing(self):
        """Hold the device in reset and pulse sysrst to start tpmrst debouncing

        Use ecrst on to hold the device in reset and pulse sysrst to reset the
        tpm. This test only runs on TPM_RST_L boards, so pulsing sysrst will
        trigger tpm_rst_requests without the AP or EC. Cr50 should print that
        resets are already scheduled.
        """
        self.cr50.send_command('ecrst on')
        time.sleep(self.cr50.SHORT_WAIT)
        self.cr50.send_command('sysrst pulse')
        time.sleep(self.cr50.SHORT_WAIT)
        self.cr50.send_command_retry_get_output('sysrst pulse',
                                                ['.*already scheduled'])

    def run_once(self, host):
        """Check cr50 can open ccd when TPM_RST_L is debounced."""
        self.host = host
        if not self.cr50.uses_board_property(self.BRDPROP_SYSRST):
            raise error.TestNAError('Cannot run on pltrst board')
        try:
            self.fast_ccd_open(True)
            self.cr50.ccd_reset_factory()
            # Reset the DUT to reenable the TPM.
            self.servo.get_power_state_controller().reset()
            self.cr50.set_cap(self.cr50.CAP_SHORT_PP, self.cr50.CAP_IF_OPENED)
            self.cr50.set_cap(self.cr50.CAP_OPEN_NO_TPM_WIPE,
                              self.cr50.CAP_IF_OPENED)
            self.setup_tpm_rst_debouncing()
            self.cr50.set_ccd_level(self.cr50.LOCK)
            self.cr50.set_ccd_level(self.cr50.OPEN)
            logging.info('successfully opened ccd')
        finally:
            self.fast_ccd_open(True)
            self.cr50.send_command('ecrst off')
            self.cr50.ccd_reset()
            self.cr50.reboot()
            self._try_to_bring_dut_up()
