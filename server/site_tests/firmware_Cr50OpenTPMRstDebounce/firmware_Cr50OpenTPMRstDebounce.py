# Copyright 2022 The ChromiumOS Authors
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
        self.gsc.send_command('ecrst on')
        time.sleep(self.gsc.SHORT_WAIT)
        self.gsc.send_command('sysrst pulse')
        time.sleep(self.gsc.SHORT_WAIT)
        self.gsc.send_command_retry_get_output('sysrst pulse',
                                                ['.*already scheduled'])

    def run_once(self, host):
        """Check cr50 can open ccd when TPM_RST_L is debounced."""
        self.host = host
        if not self.gsc.uses_board_property(self.BRDPROP_SYSRST):
            raise error.TestNAError('Cannot run on pltrst board')
        try:
            self.fast_ccd_open(True)
            self.gsc.ccd_reset_factory()
            # Reset the DUT to reenable the TPM.
            self.servo.get_power_state_controller().reset()
            self.gsc.set_cap(self.gsc.CAP_SHORT_PP, self.gsc.CAP_IF_OPENED)
            self.gsc.set_cap(self.gsc.CAP_OPEN_NO_TPM_WIPE,
                              self.gsc.CAP_IF_OPENED)
            self.setup_tpm_rst_debouncing()
            self.gsc.set_ccd_level(self.gsc.LOCK)
            self.gsc.set_ccd_level(self.gsc.OPEN)
            logging.info('successfully opened ccd')
        finally:
            self.fast_ccd_open(True)
            self.gsc.send_command('ecrst off')
            self.gsc.ccd_reset()
            self.gsc.reboot()
            self._try_to_bring_dut_up()
