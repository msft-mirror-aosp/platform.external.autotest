# Copyright 2018 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from autotest_lib.client.common_lib import error
from autotest_lib.server.cros.faft.cr50_test import Cr50Test


class firmware_Cr50DevMode(Cr50Test):
    """Verify cr50 can tell the state of the dev mode switch."""
    version = 1


    def check_dev_mode(self, dev_mode):
        """Verify the cr50 tpm info matches the devmode state."""
        if self.gsc.in_dev_mode() != dev_mode:
            raise error.TestFail('Cr50 should%s think dev mode is active' %
                    ('' if dev_mode else "n't"))


    def run_once(self):
        """Check cr50 can see dev mode correctly."""
        # If the board uses ec-efs2, servo has to use gsc_reset for cold_reset.
        if (self.servo.main_device_is_flex() and
            self.gsc.uses_board_property('BOARD_EC_CR50_COMM_SUPPORT')):
            if (not self.servo.has_control('cold_reset_select') or
                not self.servo.has_control('cold_reset_select')):
                raise error.TestError('Servo setup issue: board uses EC-EFS2, '
                        'but ec_efs2.xml was not included by servod')

            self.servo.set_nocheck('cold_reset_select', 'gsc_reset')

        self.enter_mode_after_checking_cr50_state('normal')
        self.check_dev_mode(False)
        self.enter_mode_after_checking_cr50_state('dev')
        self.check_dev_mode(True)
        self.enter_mode_after_checking_cr50_state('normal')
        self.check_dev_mode(False)
