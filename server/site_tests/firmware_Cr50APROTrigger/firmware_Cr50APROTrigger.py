# Copyright 2022 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import logging
import pprint
import time

from autotest_lib.client.common_lib import error
from autotest_lib.client.common_lib.cros import cr50_utils
from autotest_lib.server.cros.faft.cr50_test import Cr50Test


class firmware_Cr50APROTrigger(Cr50Test):
    """Verify AP RO verification status gets set and cleared correctly."""
    version = 1

    # This only verifies V1 output right now.
    TEST_AP_RO_VER = 1

    # DBG image has to be able to set the AP RO hash with the board id set.
    MIN_DBG_VER = '1.6.100'
    MIN_RELEASE_MAJOR = 5
    MIN_RELEASE_MINOR = 260

    APRO_NOT_RUN = 0
    APRO_FAIL = 2
    APRO_UNSUPPORTED_TRIGGERED = 5
    APRO_IN_PROGRESS = 7

    # The AP RO result can be cleared after 10s.
    APRO_RESET_DELAY = 10
    # Regex to search for the end of the AP RO output. Every run should end with
    # a flog message.
    APRO_OUTPUT_RE = r'.*flog.*\]'

    # Delay the gsctool command that starts verification, so the test can start
    # looking for the AP RO verify command output before the gsctool command
    # runs.
    START_DELAY = 5
    TIMEOUT_UNSUPPORTED = 3

    # These messages should never happen. Fail if they show up in any AP RO
    # verificaton output.
    ERR_MESSAGES = ['Could not find GBB area', 'WATCHDOG']

    def initialize(self, host, cmdline_args, full_args={}):
        """Initialize servo"""
        self.ran_test = False
        super(firmware_Cr50APROTrigger,
              self).initialize(host,
                               cmdline_args,
                               full_args,
                               restore_cr50_image=True)
        if not self.gsc.ap_ro_version_is_supported(self.TEST_AP_RO_VER):
            raise error.TestNAError('GSC does not support AP RO v%s' %
                                    self.TEST_AP_RO_VER)

        self._original_timeout = float(self.servo.get('cr50_uart_timeout'))
        rw_ver = self.get_saved_cr50_original_version()[1]
        _, major, minor = rw_ver.split('.')
        if (int(major) < self.MIN_RELEASE_MAJOR
                    or int(minor) < self.MIN_RELEASE_MINOR):
            raise error.TestNAError(
                    'Test does not support cr50 (%r). Update '
                    'to 0.%s.%s' %
                    (rw_ver, self.MIN_RELEASE_MAJOR, self.MIN_RELEASE_MINOR))

        dbg_ver = cr50_utils.InstallImage(self.host,
                                          self.get_saved_dbg_image_path(),
                                          '/tmp/cr50.bin')[1][1]
        if cr50_utils.GetNewestVersion(dbg_ver,
                                       self.MIN_DBG_VER) == self.MIN_DBG_VER:
            raise error.TestNAError('Update DBG image to 6.100 or newer.')

    def update_to_dbg_and_clear_hash(self):
        """Clear the Hash."""
        # Make sure the AP is up before trying to update.
        self.recover_dut()
        self._retry_gsc_update_with_ccd_and_ap(self._dbg_image_path, 3, False)
        self._hash_desc = 'cleared hash'
        self.gsc.send_command('ap_ro_info erase')
        time.sleep(3)
        if self.gsc.get_ap_ro_info()['hash']:
            raise error.TestError('Could not erase hash')
        self._try_to_bring_dut_up()

    def after_run_once(self):
        """Reboot cr50 to recover the dut."""
        try:
            self.recover_dut()
        finally:
            super(firmware_Cr50APROTrigger, self).after_run_once()

    def set_hash(self, regions):
        """Set the Hash.

        @param regions: a space separated string with the names of the regions
                        to include in the hash. ex "FMAP GBB"
        """
        self.recover_dut()
        result = self.host.run('ap_ro_hash.py -v True %s' % regions)
        logging.info(result)
        time.sleep(3)
        ap_ro_info = self.gsc.get_ap_ro_info()
        self._hash_desc = 'hash (%s)' % regions
        ap_ro_info = self.gsc.get_ap_ro_info()
        if ap_ro_info['supported'] and not ap_ro_info['hash']:
            raise error.TestError('Could not set hash %r' % result)

    def rollback_to_release_image(self):
        """Update to the release image."""
        self._retry_gsc_update_with_ccd_and_ap(
                self.get_saved_cr50_original_path(), 3, rollback=True)
        self._try_to_bring_dut_up()

    def cleanup(self):
        """Clear the hash, remove the test ro vpd key, and restore the flags."""
        try:
            if not self.ran_test:
                return
            logging.info('Cleanup')
            self.recover_dut()
            self.update_to_dbg_and_clear_hash()
            self.rollback_to_release_image()
        finally:
            super(firmware_Cr50APROTrigger, self).cleanup()

    def recover_dut(self):
        """Reboot gsc to recover the dut."""
        logging.info('Recover DUT')
        ap_ro_info = self.gsc.get_ap_ro_info()
        logging.info(ap_ro_info)
        if ap_ro_info['result'] != self.APRO_FAIL:
            self._try_to_bring_dut_up()
            return
        time.sleep(3)
        self.gsc.send_command('ccd testlab open')
        time.sleep(3)
        self.gsc.reboot()
        time.sleep(self.faft_config.delay_reboot_to_ping)
        self.gsc.get_ap_ro_info()
        self._try_to_bring_dut_up()
        self.gsc.send_command('ccd testlab open')

    def verification_in_progress(self):
        """Returns True if AP RO verification is running."""
        return self.gsc.get_ap_ro_info()['result'] == self.APRO_IN_PROGRESS

    def run_apro_verification(self):
        """Start the AP RO verification process."""
        return self.host.run('gsctool -aB start').stdout

    def trigger_verification(self, exp_result, timeout):
        """Trigger verification.

        Trigger verification. Verify the AP RO behavior by checking the result
        matches the expected result. Check that cr50 calculated the expected
        number of hashes within timeout seconds. Check the gbb value from
        ap_ro_info matches exp_gbb and all of the expected strings show up
        in the output.

        @param exp_result: expected value for the ap_ro_info result field after
                           verification runs.
        @param timeout: maximum time in seconds that the AP RO verification run
                        can take.
        """
        self._desc = ('%s: saved hash(%s) - expected result(%d)' %
                      (self._prefix, self._hash_desc, exp_result))
        # CCD has to be open to trigger verification.
        self.fast_ccd_open(True)
        logging.info('Run: %s', self._desc)

        logging.info('Triggered verification: %s',
                     self.run_apro_verification())

        ap_ro_info = self.gsc.get_ap_ro_info()
        if ap_ro_info['supported']:
            raise error.TestFail('Verification should not be supported')
        logging.info('AP RO verification is unsupported')
        if exp_result != ap_ro_info['result']:
            raise error.TestFail(
                    '%s: %r not found in status %r -- stored' %
                    (self._desc, exp_result, ap_ro_info['result']))

        logging.info('Results: %s', pprint.pformat(ap_ro_info))
        time.sleep(self.APRO_RESET_DELAY)
        self.servo.get_power_state_controller().reset()
        ap_ro_info = self.gsc.get_ap_ro_info()
        if self.APRO_NOT_RUN != ap_ro_info['result']:
            raise error.TestFail('%s: AP RO result not cleared after %ds' %
                                 (self._desc, self.APRO_RESET_DELAY))

    def run_once(self):
        """Save hash and trigger verification"""
        self.ran_test = True
        if self.gsc.get_ap_ro_info()['hash']:
            self.update_to_dbg_and_clear_hash()
            self.rollback_to_release_image()
        self._prefix = 'no hash'
        self._hash_desc = 'cleared hash'
        # This is a pretty basic test. If the board says verification is
        # unsupported, fail with TestNA.
        self.trigger_verification(self.APRO_UNSUPPORTED_TRIGGERED,
                                  self.TIMEOUT_UNSUPPORTED)
        self.update_to_dbg_and_clear_hash()
        self.set_hash('RO_VPD')
        self.rollback_to_release_image()
        self.fast_ccd_open(True)
        self._prefix = 'set hash'
        self.trigger_verification(self.APRO_UNSUPPORTED_TRIGGERED,
                                  self.TIMEOUT_UNSUPPORTED)
