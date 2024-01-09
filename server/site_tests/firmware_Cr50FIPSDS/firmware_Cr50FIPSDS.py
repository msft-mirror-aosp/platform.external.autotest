# Copyright 2022 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import logging
import time

from autotest_lib.client.common_lib import error
from autotest_lib.server.cros.faft.cr50_test import Cr50Test


class firmware_Cr50FIPSDS(Cr50Test):
    """
    Verify cr50 fips works after coming out of deep sleep.
    """
    version = 1

    def apshutdown(self):
        """Shutdown the AP and give cr50 enough time to enter deep sleep."""
        self._try_to_bring_dut_up()
        self.gsc.ccd_disable()
        self.faft_client.system.run_shell_command('poweroff', True)
        self.gsc.clear_deep_sleep_count()
        time.sleep(30)

    def check_ds_resume(self):
        """Check the system resumed ok."""

        if not self.gsc.fips_crypto_allowed():
            raise error.TestFail('Crypto not allowed after deep sleep')
        # Make sure the EC jumped to RW. This could catch ec-efs issues.
        logging.info(
                self.ec.send_command_get_output('sysinfo', ['Jumped: yes']))
        if not self.gsc.get_deep_sleep_count():
            raise error.TestError('Cr50 did not enter deep sleep')
        # Make sure the DUT fully booted and is sshable.
        logging.info('Running %r', self.gsc.get_version())
        logging.info('AP State %r', self.try_to_get_ap_state())

    def run_once(self, host):
        """Verify FIPS after deep sleep."""
        if not self.check_ec_capability(suppress_warning=True):
            raise error.TestNAError('Only supported on devices with ECs')
        if self.servo.main_device_is_ccd():
            raise error.TestNAError('Only supported with servo flex cable')
        if not self.gsc.has_command('fips'):
            raise error.TestNAError('Cr50 does not support fips')
        # Verify the EC console works.
        self.servo.enable_main_servo_device()
        try:
            self.ec.get_version()
        except Exception as e:
            raise error.TestError('EC console unresponsive: %s' % e)

        # Verify EC sysjump works on deep sleep resume.
        self.apshutdown()
        self.ec.reboot()
        time.sleep(7)
        self.check_ds_resume()

        # Verify the AP can boot after resume without EC reset.
        self.apshutdown()
        self.servo.power_normal_press()
        time.sleep(7)
        self.check_ds_resume()
