# Copyright 2022 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import logging
import pprint
import re
import time

from autotest_lib.client.bin import utils
from autotest_lib.client.common_lib import error
from autotest_lib.client.common_lib.cros import cr50_utils
from autotest_lib.server.cros.faft.cr50_test import Cr50Test


class firmware_GSCAPROV1Trigger(Cr50Test):
    """Verify GSC response after triggering AP RO V1 verification."""
    version = 1

    # This only verifies V1 output right now.
    TEST_AP_RO_VER = 1

    # DBG image has to be able to set the AP RO hash with the board id set.
    MIN_DBG_VER = '1.6.100'
    MIN_RELEASE_MAJOR = 5
    MIN_RELEASE_MINOR = 141

    APRO_PASS = 6
    APRO_FAIL = 2
    APRO_IN_PROGRESS = 7
    # Regex to search for the end of the AP RO output. Every run should end with
    # "AP RO PASS!" or "AP RO FAIL! evt - status". Collect all output up until
    # that point.
    APRO_OUTPUT_RE = r'.*AP RO ([\S]*)![^\n]*\n'

    TIMEOUT_ALL_FLAGS = 240
    # If the flags are wrong, verification should fail quickly.
    TIMEOUT_SINGLE_RUN = 30
    TIMEOUT_FLAG_FAILURE = 10
    # Delay the gsctool command that starts verification, so the test can start
    # looking for the AP RO verify command output before the gsctool command
    # runs.
    START_DELAY = 5

    DIGEST_RE = r' digest ([0-9a-f]{64})'
    CALCULATED_DIGEST_RE = 'Calculated' + DIGEST_RE
    STORED_DIGEST_RE = 'Stored' + DIGEST_RE

    # The FAFT GBB flags are innocuous. Check that the DUT is using those or
    # doesn't have any flags set.
    SUPPORTED_FLAGS = [0, 0x140]
    TEST_RO_VPD_KEY = 'faft_apro_test_key'

    # Cr50 tries to recalculate the hash with 8 of the common factory flags.
    FACTORY_FLAG_COUNT = 8
    # 0x42b9 is the last value in the cr50 factory flag list. Use it to verify
    # cr50 can regenerate the hash with all factory flags in a reasonable time.
    LAST_FACTORY_FLAG_VAL = 0x42b9
    FLAG_0 = 0

    FLAGS_NONE = None
    FLAG_42B9 = '0x%x' % LAST_FACTORY_FLAG_VAL
    FLAG_0 = '0x%x' % FLAG_0
    FLAG_NA = 'na'

    # GBB status bits
    GBBS_INJECT_FLAGS = 1
    GBBS_FLAGS_IN_HASH = 2
    GBBD_INVALID = 'na (10)'
    GBBD_SAVED = 'ok (%d)'
    # If the flags are 0, then cr50 won't try to inject them.
    STATUS_0 = GBBS_FLAGS_IN_HASH
    # If the gbb flags are in the hash and they were non-zero when the hash
    # was generated, then cr50 should try to inject them when calculating
    # the hash.
    STATUS_LAST_FLAG = (GBBS_FLAGS_IN_HASH | GBBS_INJECT_FLAGS)
    # The flags aren't in the hash, so they're not injected. Cr50 should save
    # the status as 0.
    STATUS_OUTSIDE_HASH = 0
    GBBD_SAVED_0 = GBBD_SAVED % STATUS_0
    GBBD_SAVED_LAST_FLAG = GBBD_SAVED % STATUS_LAST_FLAG
    GBBD_SAVED_FLAGS_NOT_IN_HASH = GBBD_SAVED % STATUS_OUTSIDE_HASH

    def initialize(self, host, cmdline_args, full_args={}):
        """Initialize servo"""
        self.ran_test = False
        super(firmware_GSCAPROV1Trigger,
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
        if (int(major) < self.MIN_RELEASE_MAJOR or
            int(minor) < self.MIN_RELEASE_MINOR):
            raise error.TestNAError('Test does not support cr50 (%r). Update '
                                    'to 0.%s.%s' % (rw_ver,
                                                    self.MIN_RELEASE_MAJOR,
                                                    self.MIN_RELEASE_MINOR))

        dbg_ver = cr50_utils.InstallImage(self.host,
                                          self.get_saved_dbg_image_path(),
                                          '/tmp/cr50.bin')[1][1]
        if cr50_utils.GetNewestVersion(dbg_ver,
                                       self.MIN_DBG_VER) == self.MIN_DBG_VER:
            raise error.TestNAError('Update DBG image to 6.100 or newer.')

        self._start_gbb_flags = self.faft_client.bios.get_gbb_flags()
        logging.info('GBB flags: %x', self._start_gbb_flags)
        # Refuse to run with unsupported gbb flags, because this test sets the
        # flags to 0 and it could prevent the device from booting if it's
        # currently relying on the FORCE_DEV_MODE flag.
        if self._start_gbb_flags not in self.SUPPORTED_FLAGS:
            raise error.TestNaError('Unsupported DUT GBB flags 0x%x. Set the '
                                    'flags to one of %r to run the test.' %
                                    (self._start_gbb_flags,
                                     self.SUPPORTED_FLAGS))

    def run_ro_vpd_cmd(self, cmd):
        """Run RO_VPD command

        @param cmd: the RO vpd command to run
        """
        return self.host.run('vpd -i RO_VPD ' + cmd)

    def delete_test_ro_vpd_key(self):
        """Remove the test key from the RO_VPD"""
        self.run_ro_vpd_cmd('-d ' + self.TEST_RO_VPD_KEY)

    def set_test_ro_vpd_key(self, val):
        """Remove the test key from the RO_VPD"""
        self.run_ro_vpd_cmd('-s %s=%s' % (self.TEST_RO_VPD_KEY, val))

    def restore_ro(self):
        """Restore the original test RO_VPD test key value."""
        self.set_test_ro_vpd_key('original_val')
        self._ro_desc = 'ok'

    def modify_ro(self):
        """Change a RO_VPD value to modify RO."""
        self.set_test_ro_vpd_key('modified_val')
        self._ro_desc = 'modified'

    def update_to_dbg_and_clear_hash(self):
        """Clear the Hash."""
        # Make sure the AP is up before trying to update.
        self.recover_dut()
        self._retry_gsc_update_with_ccd_and_ap(self._dbg_image_path, 3, False)
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
            super(firmware_GSCAPROV1Trigger, self).after_run_once()

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
        self._hash_desc = '%s flags' % self._flag_desc
        if not self.gsc.get_ap_ro_info()['hash']:
            raise error.TestError('Could not set hash %r' % result)

    def rollback_to_release_image(self):
        """Update to the release image."""
        self._retry_gsc_update_with_ccd_and_ap(
                self.get_saved_cr50_original_path(), 3, rollback=True)
        self._try_to_bring_dut_up()

    def set_gbb_flags(self, flags):
        """Set the GBB flags.

        @params flags: integer value to set the gbb flags to.
        """
        self.host.run('/usr/share/vboot/bin/set_gbb_flags.sh 0x%x' % flags)
        logging.info('Set GBB: %x', self.faft_client.bios.get_gbb_flags())

    def set_factory_gbb_flags(self):
        """Set the GBB flags to one of the cr50 factory flags."""
        self.set_gbb_flags(self.LAST_FACTORY_FLAG_VAL)
        self._flag_desc = '%x' % self.LAST_FACTORY_FLAG_VAL

    def clear_gbb_flags(self):
        """Set the GBB flags to 0."""
        self.set_gbb_flags(0)
        self._flag_desc = 'cleared'

    def cleanup(self):
        """Clear the hash, remove the test ro vpd key, and restore the flags."""
        try:
            if not self.ran_test:
                return
            logging.info('Cleanup')
            self.recover_dut()
            self.update_to_dbg_and_clear_hash()
            self.rollback_to_release_image()
            self.delete_test_ro_vpd_key()
            self.faft_client.bios.set_gbb_flags(self._start_gbb_flags)
        finally:
            super(firmware_GSCAPROV1Trigger, self).cleanup()

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
        return self.gsc.get_ap_ro_info()['result']  == self.APRO_IN_PROGRESS

    def get_apro_output(self, timeout):
        """Get the AP RO console output.

        @param timeout: time in seconds to wait for AP RO verification to
                        finish.
        """
        self.servo.set_nocheck('cr50_uart_timeout', timeout + self.START_DELAY)
        start_time = time.time()
        try:
            # AP RO verification will start in the background. Wait for cr50 to
            # finish verification collect all of the AP RO output.
            cmd = 'noop_wait_apro ' + self._desc
            rv = self.gsc.send_command_get_output(cmd, [self.APRO_OUTPUT_RE])
        finally:
            self.servo.set_nocheck('cr50_uart_timeout', self._original_timeout)
        logging.info('AP RO verification ran in %ds', time.time() - start_time)
        return rv[0][0]

    def _start_apro_verify(self):
        """Start AP RO verification with a delay.

        Delay starting AP RO verification, so the test can get the full
        AP RO console output.
        """
        apro_start_cmd = utils.sh_escape('sleep %d ; gsctool -aB start' %
                                         self.START_DELAY)
        full_ssh_cmd = '%s "%s"' % (self.host.ssh_command(options='-tt'),
                                    apro_start_cmd)
        # Start running the Cr50 Open process in the background.
        self._apro_start = utils.BgJob(full_ssh_cmd,
                                         nickname='apro_start',
                                         stdout_tee=utils.TEE_TO_LOGS,
                                         stderr_tee=utils.TEE_TO_LOGS)

    def _close_apro_start(self):
        """Terminate the process and check the results."""
        exit_status = utils.nuke_subprocess(self._apro_start.sp)
        delattr(self, '_apro_start')
        if exit_status:
            logging.info('exit status: %d', exit_status)

    def trigger_verification(self, exp_result, exp_calculations,
                             timeout, exp_gbb, exp_flags):
        """Trigger verification.

        Trigger verification. Verify the AP RO behavior by checking the result
        matches the expected result. Check that cr50 calculated the expected
        number of hashes within timeout seconds. Check the gbb value from
        ap_ro_info matches exp_gbb and all of the expected strings show up
        in the output.

        @param exp_result: expected value for the ap_ro_info result field after
                           verification runs.
        @param exp_calculations: expected number of hashes cr50 will generate
                                 during verification.
        @param timeout: maximum time in seconds that the AP RO verification run
                        can take.
        @param exp_gbb: string that should be found in the ap_ro_info gbb field.
        @param exp_flags: None or the flag string if the gbbd is saved
        """
        self._desc = ('%s: current flags(%s) ro(%s) saved hash(%s) - '
                      'expected result(%d)' %
                      (self._prefix, self._flag_desc, self._ro_desc,
                       self._hash_desc, exp_result))
        # CCD has to be open to trigger verification.
        self.fast_ccd_open(True)
        logging.info('Run: %s', self._desc)

        self.recover_dut()
        try:
            self._start_apro_verify()
            contents = self.get_apro_output(timeout)
        finally:
            self._close_apro_start()
        logging.info('finished %r:%s', self._desc, contents)

        if self.verification_in_progress():
            raise error.TestFail('%s: Verification did not finish in %ds' %
                                 (self._desc, timeout))

        ap_ro_info = self.gsc.get_ap_ro_info()
        self.recover_dut()

        # cr50 only prints calculated and stored hashes after AP RO verificaiton
        # fails. These sets will be empty if verification passed every time.
        calculated = set(re.findall(self.CALCULATED_DIGEST_RE, contents))
        stored = set(re.findall(self.STORED_DIGEST_RE, contents))
        logging.info('Stored: %r', stored)
        logging.info('Calculated (%d): %s', len(calculated),
                     pprint.pformat(calculated))
        logging.info('Results: %s', pprint.pformat(ap_ro_info))

        if len(calculated) != exp_calculations:
            raise error.TestFail('%s: Calculated %d digests instead of %d' %
                                 (self._desc, len(calculated),
                                  exp_calculations))
        if exp_flags != ap_ro_info['flags']:
            raise error.TestFail(
                    '%s: %r not found in flags %r -- stored: %r calc: %r' %
                    (self._desc, exp_flags, ap_ro_info['flags'], stored,
                     calculated))
        if exp_gbb not in ap_ro_info['gbbd']:
            raise error.TestFail(
                    '%s: %r not found in gbb %r -- stored: %r calc: %r' %
                    (self._desc, exp_gbb, ap_ro_info['gbbd'], stored,
                     calculated))
        if exp_result != ap_ro_info['result']:
            raise error.TestFail(
                    '%s: %r not found in status %r -- stored: %r calc: %r' %
                    (self._desc, exp_result, ap_ro_info['result'], stored,
                     calculated))

    def run_once(self):
        """Save hash and trigger verification"""
        self.ran_test = True
        # The DBG image can set the hash when the board id is saved. The release
        # image can't. Set the hash with the DBG image, so the test doesn't need
        # to erase the board id. This test verifies triggering AP RO
        # verification. It's not about saving the hash. Whenever the test
        # updates the hash, it'll update to the dbg image, set the hash, and
        # then rollback to the released image.
        self.update_to_dbg_and_clear_hash()

        # Generate a hash with the GBB flags set to 0.
        # Set the GBB flags to 0.
        self.clear_gbb_flags()
        # The test creates a RO_VPD key and modifies it to modify RO. It's a
        # bogus key. It doesn't change any device behavior. It's just a way
        # to easily modify RO.
        self.restore_ro()
        self.set_hash('WP_RO')
        self.rollback_to_release_image()

        logging.info('Verifying standard behavior')
        logging.info('the hash was generated with 0 gbb flags')
        self._prefix = 'standard'
        # Set the flags to a non-zero value. Make sure it fails almost
        # immediately because the flags are wrong.
        self.set_factory_gbb_flags()
        self.trigger_verification(self.APRO_FAIL, 0,
                                  self.TIMEOUT_FLAG_FAILURE,
                                  self.GBBD_INVALID,
                                  self.FLAGS_NONE)
        # Modify RO. Cr50 should still fail immediately because the flags are
        # wrong.
        self.modify_ro()
        self.trigger_verification(self.APRO_FAIL, 0,
                                  self.TIMEOUT_FLAG_FAILURE,
                                  self.GBBD_INVALID,
                                  self.FLAGS_NONE)
        self.clear_gbb_flags()
        # Cr50 should try all factory flags and fail with a hash mismatch.
        self.trigger_verification(self.APRO_FAIL, self.FACTORY_FLAG_COUNT,
                                  self.TIMEOUT_ALL_FLAGS,
                                  self.GBBD_INVALID,
                                  self.FLAGS_NONE)
        # Restore RO. Check AP RO verification starts passing.
        self.restore_ro()
        # Verification should pass during the first flag check since the hash
        # was generated with gbb flags set to 0.
        self.trigger_verification(self.APRO_PASS, 0,
                                  self.TIMEOUT_SINGLE_RUN,
                                  self.GBBD_SAVED_0,
                                  self.FLAG_0)
        # Trigger verification multiple times. Make sure it doesn't fail or
        # change.
        self.trigger_verification(self.APRO_PASS, 0,
                                  self.TIMEOUT_SINGLE_RUN,
                                  self.GBBD_SAVED_0,
                                  self.FLAG_0)
        self.trigger_verification(self.APRO_PASS, 0,
                                  self.TIMEOUT_SINGLE_RUN,
                                  self.GBBD_SAVED_0,
                                  self.FLAG_0)
        # With the saved flags AP RO verification should only try one flag. It
        # should fail more quickly.
        self.modify_ro()
        self.trigger_verification(self.APRO_FAIL, 1,
                                  self.TIMEOUT_SINGLE_RUN,
                                  self.GBBD_SAVED_0,
                                  self.FLAG_0)

        # Generate a hash with non-zero flags.
        self.update_to_dbg_and_clear_hash()
        self.restore_ro()
        self.set_factory_gbb_flags()
        self.set_hash('WP_RO')
        self.rollback_to_release_image()

        logging.info('Verifying the gbb workaround')
        logging.info('cr50 can handle hashes generated with non-zero flags')
        self._prefix = 'non-zero factory flags'
        # The gbb flags are non-zero. Cr50 should fail immediately since they're
        # non-zero.
        self.trigger_verification(self.APRO_FAIL, 0,
                                  self.TIMEOUT_SINGLE_RUN,
                                  self.GBBD_INVALID,
                                  self.FLAGS_NONE)

        # The flags are wrong and RO is wrong. Cr50 verifies the flags first, so
        # it should still fail immediately and not generate any hashes.
        self.modify_ro()
        self.trigger_verification(self.APRO_FAIL, 0,
                                  self.TIMEOUT_SINGLE_RUN,
                                  self.GBBD_INVALID,
                                  self.FLAGS_NONE)
        # The flags are ok. RO is wrong. Cr50 should try all factory flags and
        # fail with a hash mismatch.
        self.clear_gbb_flags()
        self.trigger_verification(self.APRO_FAIL, self.FACTORY_FLAG_COUNT,
                                  self.TIMEOUT_ALL_FLAGS,
                                  self.GBBD_INVALID,
                                  self.FLAGS_NONE)
        # The test saved the hash with the last factory flag. Cr50 should
        # calculate hashes with all of the factory flags and pass on the last
        # one.
        self.restore_ro()
        # Cr50 should match the gbb flag and then save it.
        self.trigger_verification(self.APRO_PASS, self.FACTORY_FLAG_COUNT - 1,
                                  self.TIMEOUT_ALL_FLAGS,
                                  self.GBBD_SAVED_LAST_FLAG,
                                  self.FLAG_42B9)
        # The next verification cr50 should load the matched flag and only try
        # that.
        self.trigger_verification(self.APRO_PASS, 0,
                                  self.TIMEOUT_SINGLE_RUN,
                                  self.GBBD_SAVED_LAST_FLAG,
                                  self.FLAG_42B9)
        # RO verificaiton will fail since the RO is changed, but cr50 should
        # only try the flag it matched originally.
        self.modify_ro()
        self.trigger_verification(self.APRO_FAIL, 1,
                                  self.TIMEOUT_SINGLE_RUN,
                                  self.GBBD_SAVED_LAST_FLAG,
                                  self.FLAG_42B9)
        # RO and the flags are wrong, but cr50 shouldn't try to generate a hash.
        # It should fail before that since the flags are wrong.
        self.set_factory_gbb_flags()
        # Cr50 checks the current flags, before it tries to use the saved gbbd.
        # Cr50 will fail with non-zero flags before it loads the gbbd, so
        # LOAD_42B9 shouldn't show up in the result. It should only have the
        # invalid gbb flags messages.
        self.trigger_verification(self.APRO_FAIL, 0,
                                  self.TIMEOUT_FLAG_FAILURE,
                                  self.GBBD_SAVED_LAST_FLAG,
                                  self.FLAG_42B9)

        # After the state is restored to a good state, cr50 should pass again.
        self.clear_gbb_flags()
        self.restore_ro()
        self.trigger_verification(self.APRO_PASS, 0,
                                  self.TIMEOUT_SINGLE_RUN,
                                  self.GBBD_SAVED_LAST_FLAG,
                                  self.FLAG_42B9)
        self.gsc.reboot()
        self._try_to_bring_dut_up()
        # Make sure it works the same after cr50 reboots.
        self.trigger_verification(self.APRO_PASS, 0,
                                  self.TIMEOUT_SINGLE_RUN,
                                  self.GBBD_SAVED_LAST_FLAG,
                                  self.FLAG_42B9)

        # Set a hash with FMAP in the hash and the GBB outside of the hash.
        # Cr50 should not care about the GBB flags in this case.
        self.update_to_dbg_and_clear_hash()
        self.restore_ro()
        self.set_factory_gbb_flags()
        self.set_hash('FMAP RO_VPD')
        self.rollback_to_release_image()

        logging.info('Verifying setup with GBB outside of hash')
        self._prefix = 'gbb outside of hash'

        # GBB flags are non-zero, but they're outside of the hash, so it
        # shouldn't matter.
        self.trigger_verification(self.APRO_PASS, 0,
                                  self.TIMEOUT_SINGLE_RUN,
                                  self.GBBD_SAVED_FLAGS_NOT_IN_HASH,
                                  self.FLAG_NA)
        # GBB flags are now zero, but they're outside of the hash, so it
        # shouldn't matter.
        self.clear_gbb_flags()
        self.trigger_verification(self.APRO_PASS, 0,
                                  self.TIMEOUT_SINGLE_RUN,
                                  self.GBBD_SAVED_FLAGS_NOT_IN_HASH,
                                  self.FLAG_NA)
        # Modify the RO_VPD. It's in the hash, so verification should fail.
        self.modify_ro()
        self.trigger_verification(self.APRO_FAIL, 1,
                                  self.TIMEOUT_SINGLE_RUN,
                                  self.GBBD_SAVED_FLAGS_NOT_IN_HASH,
                                  self.FLAG_NA)

        # Cr50 will fail verification if the FMAP is outside of the hash since
        # it can't trust the GBB location.
        self.update_to_dbg_and_clear_hash()
        self.restore_ro()
        self.clear_gbb_flags()
        self.set_hash('GBB')
        self.rollback_to_release_image()

        logging.info('Verifying setup with FMAP outside of hash')
        self._prefix = 'fmap not in hash'

        # There's no way to pass since FMAP isn't in the hash. The factory
        # process is standard. FMAP should be in the hash.
        self.trigger_verification(self.APRO_FAIL, 0,
                                  self.TIMEOUT_FLAG_FAILURE,
                                  self.GBBD_INVALID,
                                  self.FLAGS_NONE)
