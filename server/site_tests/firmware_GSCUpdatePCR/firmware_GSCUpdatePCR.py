# Copyright 2023 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import logging
import time

from autotest_lib.client.common_lib import error
from autotest_lib.client.common_lib.cros import tpm_utils
from autotest_lib.server.cros.faft.firmware_test import FirmwareTest


class firmware_GSCUpdatePCR(FirmwareTest):
    """Verify GSC Update PCR."""
    version = 1

    INDEX = 5
    # 7 is pretty random. It doesn't really matter. For testing purposes just
    # verify the extended digest doesn't start with '36'
    EXTEND_VALUE = 7
    CMD_READ_PCR = 'trunks_client --read_pcr --index=%d' % INDEX
    CMD_EXTEND_PCR = 'trunks_client --extend_pcr --index=%d --value=' % INDEX
    ZERO_DIGEST = '0000000000000000000000000000000000000000000000000000000000000000'

    def initialize(self, host, cmdline_args):
        """Initialize GSC."""
        self.host = host
        super(firmware_GSCUpdatePCR, self).initialize(host, cmdline_args)
        if 'ccd' in self.servo.get_servo_version():
            self.servo.disable_ccd_watchdog_for_test()

        if self.faft_config.ec_forwards_short_pp_press:
            raise error.TestNAError(
                    'Not supported on devices with ec_forwards_short_pp_press')
        self.fast_ccd_open(True)
        self.gsc.ccd_reset_and_wipe_tpm()
        self.gsc.send_command('rddkeepalive disable')
        self.gsc.ccd_disable()

    def cleanup(self):
        """Open ccd to clear the tpm."""
        try:
            self.gsc.ccd_reset_and_wipe_tpm()
        finally:
            super(firmware_GSCUpdatePCR, self).cleanup()

    def resume(self, enter_ds):
        """Resume from suspend."""
        ds_disabled = self.gsc.ccdstate_ds_disabled()
        if enter_ds:
            self.gsc.clear_deep_sleep_count()
            time.sleep(self.gsc.DEEP_SLEEP_DELAY)
        else:
            time.sleep(10)
        ap_off = not self.gsc.ap_is_on()
        logging.info('Pressing power button to resume')
        self._power_state = self.get_power_state()
        self.servo.power_normal_press()
        entered_ds = not not self.gsc.get_deep_sleep_count()
        logging.info('Entered DS: %s', entered_ds)
        if enter_ds:
            if not ap_off:
                logging.info('AP did not turn off during suspend')
            elif ds_disabled:
                logging.info('AP disabled deep sleep')
            elif not entered_ds:
                raise error.TestFail(
                        'Did not enter deep sleep when ap was off')
        return entered_ds

    def suspend_and_resume(self, enter_ds):
        """Suspend and resume."""
        if enter_ds:
            self.gsc.ccd_disable()
        elif self.gsc.NAME == 'cr50':
            # Send command to disable deep sleep in S3.
            self.host.run('trunks_send --raw 80010000000c20000000003b')
        else:
            self.gsc.ccd_enable()
        self.suspend()
        return self.resume(enter_ds)

    def send_shutdown(self):
        """Send the tpm shutdown command to update the pcr value."""
        tpm_utils.SendTPMShutdownState(self.host)

    def read_pcr(self):
        """Get the PCR 5 gigest."""
        result = self.host.run(self.CMD_READ_PCR)
        logging.info('Read PCR: %s', result.stdout)
        return result.stdout.split(':')[-1].strip()

    def extend_pcr(self, value):
        """Extend PCR 5 with the given value."""
        result = self.host.run('%s%s' % (self.CMD_EXTEND_PCR, value))
        logging.info('Extend PCR: %s', result.stdout)
        return result.stdout

    def assert_digest_is_non_zero(self, desc):
        """Verify the PCR digest is some non-zero value."""
        digest = self.read_pcr()
        if digest == self.ZERO_DIGEST:
            raise error.TestFail('Digest is %s zero %s' % (digest, desc))
        return digest

    def assert_digest_is_zero(self, desc):
        """Verify the digest is all zeroes."""
        digest = self.read_pcr()
        if digest != self.ZERO_DIGEST:
            raise error.TestFail('Digest is %s not zero %s' % (digest, desc))

    def run_once(self):
        """Check cr50 can see dev mode correctly."""
        # After reboot, the pcr 5 digest should be 0.
        self.host.reboot()
        self.assert_digest_is_zero('after first reboot')
        # Extend it with some value. The value doesn't really matter.
        self.extend_pcr(self.EXTEND_VALUE)
        self.assert_digest_is_non_zero('after first extend')
        # Send tpm shutdown
        self.send_shutdown()
        # Extend it again.
        self.extend_pcr(self.EXTEND_VALUE)
        updated_digest = self.assert_digest_is_non_zero('after second extend')
        # Enter S3 and resume without entering deep sleep. This should send shutdown
        # and trigger update pcr should be equal to updated_digest.
        self.suspend_and_resume(False)
        digest_after_resume = self.read_pcr()
        logging.info('Before %s suspend: %s', self._power_state,
                     updated_digest)
        logging.info('After %s resume: %s', self._power_state,
                     digest_after_resume)
        if digest_after_resume != updated_digest:
            raise error.TestFail('Digest changed after suspend/resume')
        # Reboot device
        self.host.reboot()
        # pcr 5 should be back to 0
        self.assert_digest_is_zero('after second reboot')
        # Suspend and resume
        entered_ds = self.suspend_and_resume(True)
        # The loaded pcr 5 digest should still be 0
        self.assert_digest_is_zero(
                'after %s resume (%s ds)' %
                (self._power_state, 'enetered' if entered_ds else 'no'))
