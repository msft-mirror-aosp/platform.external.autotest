# Copyright 2018 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import logging

from autotest_lib.client.common_lib import error
from autotest_lib.server.cros.faft.cr50_test import Cr50Test


class firmware_Cr50DevMode(Cr50Test):
    """Verify cr50 can tell the state of the dev mode switch."""
    version = 1

    MRC_FILE = '/tmp/mrc.txt'
    MRC_INDEX = '0x0000100B'
    READ_MRC_CMD = 'tpm_manager_client read_space --index=%s --file=%s ; cat %s' % (
            MRC_INDEX, MRC_FILE, MRC_FILE)

    def switch_to_mode(self, mode):
        """Switch to the given mode (dev or normal)."""
        to_dev = mode == 'dev'
        logging.info('Entering: %s', mode)
        logging.info(self.host.run(self.READ_MRC_CMD, ignore_status=True))
        try:
            self.switcher.reboot_to_mode(to_mode=mode)
        except Exception as e:
            ap_info = self.try_to_get_ap_state()
            raise error.TestFail('Unable to enter %s mode %s: %r' %
                                 (mode, ap_info, e))

        if to_dev != self.gsc.in_dev_mode():
            raise error.TestFail('Cr50 should%s think dev mode is active' %
                                 ('' if to_dev else "n't"))

    def run_once(self):
        """Check cr50 can see dev mode correctly."""
        # Make gsc ecrst available if the board uses EC-EFS2.
        if (self.servo.main_device_is_flex() and
            self.gsc.uses_board_property('BOARD_EC_CR50_COMM_SUPPORT')):
            if not self.servo.has_control('cold_reset_select'):
                raise error.TestError('Servo setup issue: board uses EC-EFS2, '
                        'but ec_efs2.xml was not included by servod')
            if self.servo.has_control('gsc_ecrst_pulse'):
                self.servo.set_nocheck('cold_reset_select', 'gsc_ecrst_pulse')
            else:
                # TODO(b/294426380): remove when gsc_ecrst_pulse is in the lab.
                self.fast_ccd_open(True)
                self.gsc.enable_servo_control_caps()
                self.servo.set_nocheck('cold_reset_select', 'gsc_ec_reset')
                self.gsc.set_ccd_level('lock')

        self.switch_to_mode('normal')
        self.switch_to_mode('dev')
        self.switch_to_mode('normal')
