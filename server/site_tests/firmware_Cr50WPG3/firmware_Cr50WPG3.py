# Copyright 2019 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import logging
import re
import time

from autotest_lib.client.common_lib import error
from autotest_lib.server.cros.faft.cr50_test import Cr50Test


class firmware_Cr50WPG3(Cr50Test):
    """Verify WP in G3."""
    version = 1

    WAIT_FOR_STATE = 10
    WP_REGEX = r'write protect is ((en|dis)abled)\.'
    FLASHROM_WP_CMD = 'sudo flashrom -p raiden_debug_spi:target=AP,serial=%s '
    STATUS_CMD = '--wp-status'
    WP_ENABLE_CMD = '--wp-enable'
    WP_DISABLE_CMD = '--wp-disable'
    DISABLED = 'disabled'
    ENABLED = 'enabled'

    def cleanup(self):
        """Reenable servo wp."""
        self.gsc.send_command('ccd testlab open')
        try:
            # Reset the WP state.
            if hasattr(self, '_start_fw_wp_vref'):
                self.gsc.send_command('ccdblock IGNORE_SERVO enable')
                self.gsc.set_wp_state('disable atboot')
                self.set_sw_wp(self.WP_DISABLE_CMD)
                self.gsc.set_wp_state('follow_batt_pres atboot')
                self.servo.set_nocheck('fw_wp_state', self._start_fw_wp_state)
                if self._start_fw_wp_vref:
                    self.servo.set_nocheck('fw_wp_vref', self._start_fw_wp_vref)
            self.gsc.send_command('rddkeepalive disable')
            self.gsc.send_command('ccdblock IGNORE_SERVO disable')
            self.servo.enable_main_servo_device()
        finally:
            super(firmware_Cr50WPG3, self).cleanup()

    def generate_flashrom_wp_cmd(self):
        """Use the cr50 serialname to generate the flashrom command."""
        self._flashrom_cmd = self.FLASHROM_WP_CMD % self.gsc.get_serial()

    def get_wp_state(self):
        """Returns 'on' if write protect is enabled. 'off' if it's disabled."""
        output = self.servo.system_output(
                self._flashrom_cmd + self.STATUS_CMD)
        m = re.search(self.WP_REGEX, output)
        logging.info('WP is %s', m.group(1) if m else 'UKNOWN')
        logging.info('flashrom output\n%s', output)
        if not m:
            raise error.TestError('Unable to find WP status in flashrom output')
        return m.group(1)

    def set_sw_wp(self, cmd):
        """Set SW WP."""
        time.sleep(self.gsc.SHORT_WAIT)
        output = self.servo.system_output(self._flashrom_cmd + cmd,
                ignore_status=True)
        logging.debug('output: %r', output)
        time.sleep(self.gsc.SHORT_WAIT)
        return self.get_wp_state()

    def run_once(self):
        """Verify WP in G3."""
        if not self.servo.get_ccd_servo_device():
            raise error.TestNAError('Only supported with dual-v4')
        if self.check_cr50_capability(['wp_on_in_g3'], suppress_warning=True):
            raise error.TestNAError('WP not pulled up in G3')
        try:
            self.gsc.ccd_enable(True)
        except:
            raise error.TestNAError('CCD required to check wp.')
        self.generate_flashrom_wp_cmd()

        self.fast_ccd_open(True)
        # faft-cr50 runs with servo micro and type c servo v4. Use ccdblock to
        # get cr50 to ignore the fact servo is connected and allow the test to
        # use ccd to check wp status.
        self.gsc.send_command('ccdblock IGNORE_SERVO enable')
        self.gsc.send_command('rddkeepalive enable')
        self.gsc.get_ccdstate()

        if self.servo.main_device_is_flex():
            self._start_fw_wp_state = self.servo.get('fw_wp_state')
            # If nothing is forcing write protect, then the initial state is
            # "reset".
            if "force" not in self._start_fw_wp_state:
                self._start_fw_wp_state = "reset"
            self._start_fw_wp_vref = (self.servo.get('fw_wp_vref') if
                    self.servo.has_control('fw_wp_vref') else None)
            # Stop forcing wp using servo, so we can set it with ccd.
            self.servo.set_nocheck('fw_wp_state', 'reset')
            if self._start_fw_wp_vref:
                self.servo.set_nocheck('fw_wp_vref', 'off')

        # Disable HW WP.
        self.gsc.set_wp_state('disable atboot')

        # Disable SW WP.
        wp_state = self.set_sw_wp(self.WP_DISABLE_CMD)
        # Bring the DUT up since flashrom commands put the EC in reset.
        self._try_to_bring_dut_up()
        if wp_state != self.DISABLED:
            raise error.TestFail('Unable to disable SW WP with HW WP enabled')

        # Verify we can see it's disabled. This should always work. If it
        # doesn't, it may be a setup issue.
        logging.info('Checking WP from DUT')
        if not self.checkers.crossystem_checker({'wpsw_cur': '0'}):
            raise error.TestError("WP isn't disabled in S0")

        # Enable HW WP.
        self.gsc.set_wp_state('enable atboot')
        if not self.checkers.crossystem_checker({'wpsw_cur': '1'}):
            raise error.TestError("WP isn't enabled in S0")

        self.faft_client.system.run_shell_command('poweroff')
        time.sleep(self.WAIT_FOR_STATE)
        if hasattr(self, 'ec'):
            self.ec.send_command('hibernate')
            time.sleep(self.WAIT_FOR_STATE)

        # SW WP can be enabled at any time.
        logging.info('Check enabling SW WP with HW WP enabled')
        if self.set_sw_wp(self.WP_ENABLE_CMD) != self.ENABLED:
            self.gsc.reboot()
            self._try_to_bring_dut_up()
            raise error.TestFail('Unable to enable wp in G3')

        # It shouldn't be possible to disable SW WP with HW WP enabled.
        logging.info('Check disabling SW WP with HW WP enabled')
        if self.set_sw_wp(self.WP_DISABLE_CMD) == self.DISABLED:
            self.gsc.reboot()
            self._try_to_bring_dut_up()
            raise error.TestFail('Disabled SW WP with HW WP enabled')

        # It should be possible to disable SW WP after HW WP is disabled.
        logging.info('Check disabling SW WP with HW WP disabled')
        # Disable HW WP.
        self.gsc.set_wp_state('disable atboot')
        # Verify setting SW WP.
        if self.set_sw_wp(self.WP_DISABLE_CMD) != self.DISABLED:
            self.gsc.reboot()
            self._try_to_bring_dut_up()
            raise error.TestFail('Disabled SW WP with HW WP enabled')
        self._try_to_bring_dut_up()
