# Copyright 2017 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import print_function

import difflib
import logging
import math
import time

from autotest_lib.client.common_lib import error
from autotest_lib.server import autotest
from autotest_lib.server.cros.faft.firmware_test import FirmwareTest


class firmware_Cr50DeepSleepStress(FirmwareTest):
    """Verify Cr50 deep sleep after running power_SuspendStress.

    Cr50 should enter deep sleep every suspend. Verify that by checking the
    idle deep sleep count.

    @param suspend_count: The number of times to reboot or suspend the device.
    @param reset_type: a str with the cycle type: 'freeze', 'mem', or 'reboot'
    """
    version = 1

    MIN_RESUME = 15
    # Initialize the FWMP with a non-zero value. Use 100, because it's an
    # unused flag and it wont do anything like lock out dev mode or ccd.
    DEFAULT_FWMP_FLAGS = '0x100'
    # The deep sleep count may not exactly match the suspend count. This is the
    # ratio of difference the test tolerates. If the difference/total suspend
    # count is greater than this ratio, fail the test.
    TOLERATED_ERROR = 0.05
    MEM_DISABLE_DS_PATH = '/etc/init/cr50-disable-sleep.conf'

    # Dictionary used to temporarily disable tests on certain devices. Used
    # to disable a test until a bug is resolved.
    # Key is the suspend type. The value is a list of board names to skip.
    TMP_SKIP_DEVICES = {
            'mem': [
                    # TODO(b/297884848): reenable after bug is resolved.
                    'rammus',
            ],
            'freeze': [],
            'reboot': [],
    }

    def initialize(self,
                   host,
                   cmdline_args,
                   suspend_count,
                   reset_type,
                   fwmp=None):
        """Make sure the test is running with access to the GSC console"""
        self.host = host
        if host.servo.main_device_is_ccd():
            raise error.TestNAError('deep sleep tests can only be run with a '
                                    'servo flex')
        super(firmware_Cr50DeepSleepStress, self).initialize(host, cmdline_args)
        if not hasattr(self, 'gsc'):
            raise error.TestNAError('Test can only be run on devices with '
                                    'access to the GSC console')
        self.fwmp = fwmp or self.DEFAULT_FWMP_FLAGS

        # Suspend longer than DEEP_SLEEP_DELAY to ensure entering deep sleep.
        self.min_suspend = self.gsc.DEEP_SLEEP_DELAY + 5

        # Reset the device
        self.host.reset_via_servo()

        # Save the original version, so we can make sure Cr50 doesn't rollback.
        self.original_cr50_version = self.gsc.get_active_version_info()
        self._suspend_diff = 0

        # TODO(b/218492933) : find better way to disable rddkeepalive
        # Disable rddkeepalive, so the test can disable ccd.
        self.gsc.send_command('ccd testlab open')
        self.gsc.send_command('rddkeepalive disable')
        # Lock cr50 so the console will be restricted
        self.gsc.set_ccd_level('lock')

    def cleanup(self):
        """Clear the fwmp."""
        try:
            self._try_to_bring_dut_up()
            self.clear_tpm_owner_and_fwmp()
        finally:
            super(firmware_Cr50DeepSleepStress, self).cleanup()


    def create_fwmp(self):
        """Create the FWMP."""
        self.fast_ccd_open(True)
        self.gsc.set_ccd_level('lock')
        self.clear_tpm_owner_and_fwmp()
        logging.info('Setting FWMP flags to %s', self.fwmp)
        autotest.Autotest(self.host).run_test('firmware_SetFWMP',
                                              flags=self.fwmp,
                                              fwmp_cleared=True,
                                              check_client_result=True)

        if self.fwmp_is_cleared():
            raise error.TestError('Unable to create the FWMP')


    def check_fwmp(self):
        """Returns an error message if the fwmp doesn't exist."""
        if self.fwmp_is_cleared():
            return 'FWMP was lost during test'
        logging.info('No issues detected with the FWMP')


    def check_cr50_version(self, expected_ver):
        """Return an error message if the version changed running the test."""
        version = self.gsc.get_active_version_info()
        logging.info('running %s', version)

        if version != expected_ver:
            return 'version changed from %s to %s' % (expected_ver, version)


    def run_reboots(self, suspend_count):
        """Reboot the device the requested number of times

        @param suspend_count: the number of times to reboot the device.
        """
        cr50_dev_mode = self.gsc.in_dev_mode()
        # Disable CCD so Cr50 can enter deep sleep
        self.gsc.ccd_disable()
        self.gsc.clear_deep_sleep_count()
        rv = self.check_cr50_deep_sleep(0)
        if rv:
            raise error.TestError('Issue setting up test %s' % rv)
        errors = []

        for i in range(suspend_count):
            if not self._dut_is_responsive():
                raise error.TestFail(
                        'Unable to ssh into DUT after %d resets: %s' %
                        (i, self.gsc.get_debug_ap_state()))
            self.host.run('ls /dev/tpm0')
            # Power off the device
            self.faft_client.system.run_shell_command('poweroff', True)

            time.sleep(self.min_suspend)

            # Power on the device
            self.servo.power_normal_press()
            time.sleep(self.MIN_RESUME)

            rv = self.check_cr50_deep_sleep(i + 1)
            if rv:
                errors.append(rv)
            # Make sure the device didn't boot into a different mode.
            if self.gsc.in_dev_mode() != cr50_dev_mode:
                errors.append('Switched out of %s mode' %
                              ('dev' if cr50_dev_mode else 'normal'))
            if errors:
                msg = 'Reboot %d failed (%s)' % (i, ' and '.join(errors))
                logging.info(msg)
                raise error.TestFail(msg)


    def _dut_is_responsive(self):
        """Returns True if the DUT eventually responds"""
        return self.ping_dut_with_eth_reset()


    def wait_for_client_after_changing_ccd(self, enable):
        """Change CCD and wait for client.

        @param enable: True to enable ccd. False to disable it.
        @returns an error message
        """
        start_msg = ('' if self._dut_is_responsive() else
                     'DUT unresponsive after suspend/resume %s' %
                     self.gsc.get_debug_ap_state())
        logging.info('SSH state afters suspend resume %r', start_msg or 'ok')
        if enable:
            self.gsc.ccd_enable()
        else:
            self.gsc.ccd_disable()
        # power suspend stress needs to ssh into the DUT. If ethernet goes
        # down, raise a test error, so we can tell the difference between
        # dts ethernet issues and the dut going down during the suspend stress.
        if self._dut_is_responsive():
            return
        msg = 'DUT is not pingable after %sabling ccd' % ('en' if enable else
                                                          'dis')
        logging.info(msg)

        self._try_to_bring_dut_up()

        is_sshable = self._dut_is_responsive()

        rv = start_msg or ('' if is_sshable else msg)
        logging.info('ssh state: %r', rv or 'ok')
        return rv


    def run_suspend_resume(self, suspend_count, suspend_type):
        """Suspend the device the requested number of times

        @param suspend_count: the number of times to suspend the device.
        @param suspend_type: the type of suspend to issue("mem" or "freeze")
        """
        # Disable CCD so Cr50 can enter deep sleep
        rv = self.wait_for_client_after_changing_ccd(False)
        if rv:
            raise error.TestFail('Network connection issue %s' % rv)
        self.gsc.clear_deep_sleep_count()
        rv = self.check_cr50_deep_sleep(0)
        if rv:
            raise error.TestError('Issue setting up test %s' % rv)
        client_at = autotest.Autotest(self.host)
        # Duration is set to 0, because it is required but unused when
        # iterations is given.
        client_at.run_test('power_SuspendStress',
                           tag='idle',
                           duration=0,
                           min_suspend=self.min_suspend,
                           min_resume=self.MIN_RESUME,
                           check_connection=False,
                           suspend_iterations=suspend_count,
                           suspend_state=suspend_type,
                           check_client_result=True)


    def check_cr50_deep_sleep(self, suspend_count):
        """Verify Cr50 has entered deep sleep the correct number of times.

        Also print ccdstate and sleepmask output to get some basic information
        about the Cr50 state.
        - sleepmask will show what may be preventing Cr50 from entering sleep.
        - ccdstate will show what Cr50 thinks the AP state is. If the AP is 'on'
          Cr50 won't enter deep sleep.
        All of these functions log the state, so no need to log the return
        values.

        @param suspend_count: The number of suspends.
        @returns a message describing errors found in the state
        """
        exp_count = suspend_count if self._enters_deep_sleep else 0
        act_count = self.gsc.get_deep_sleep_count()
        logging.info('suspend %d: deep sleep count exp %d got %d',
                     suspend_count, exp_count, act_count)

        # Cr50 sometimes misses a suspend. Don't fail if the mismatch is within
        # the tolerated difference.
        tolerated_diff = math.ceil(exp_count * self.TOLERATED_ERROR)
        act_diff = exp_count - act_count
        logging.debug('suspend %d: tolerated diff %d got %d', suspend_count,
                      tolerated_diff, act_diff)
        if act_diff != self._suspend_diff:
            logging.warning('suspend %d: mismatch changed from %d to %d',
                            suspend_count, self._suspend_diff, act_diff)
            self._suspend_diff = act_diff

        self.gsc.get_sleepmask()
        self.gsc.get_ccdstate()
        hibernate = self.gsc.was_reset('RESET_FLAG_HIBERNATE')

        errors = []
        if exp_count and not hibernate:
            errors.append('reset during suspend')

        # Use the absolute value, because Cr50 shouldn't suspend more or less
        # than expected.
        if abs(act_diff) > tolerated_diff:
            errors.append('count mismatch expected %d got %d' % (exp_count,
                                                                 act_count))
        return ', '.join(errors) if errors else None


    def check_flog_output(self, original_flog):
        """Check for new flog messages.

        @param original_flog: the original flog output.
        @returns an error message with the flog difference, if there are new
                 entries.
        """
        new_flog = self.gsc.get_flog()
        logging.debug('Final FLOG output:\n%s', new_flog)
        diff = difflib.unified_diff(original_flog.splitlines(),
                                    new_flog.splitlines())
        line_diff = '\n'.join(diff)
        if line_diff:
            logging.info('FLOG output:\n%s', line_diff)
            return 'New Flog messages (%s)' % ','.join(diff)
        else:
            logging.info('No new FLOG output')

    def run_once(self, host, suspend_count, reset_type):
        """Verify deep sleep after suspending for the given number of cycles

        The test either suspends to s0i3/s3 or reboots the device depending on
        reset_type. There are three valid reset types: freeze, mem, and reboot.
        The test will make sure that the device is off or in s0i3/s3 long enough
        to ensure Cr50 should be able to enter the corresponding suspend state.
        At the end of the test, it checks that Cr50 entered the suspend state
        the same number of times the DUT suspended.

        @param host: the host object representing the DUT.
        @param suspend_count: The number of cycles to suspend or reboot the
                device.
        @param reset_type: a str with the cycle type: 'freeze', 'mem' or
                'reboot'
        """
        if reset_type not in ['reboot', 'freeze', 'mem']:
            raise error.TestNAError('Invalid reset_type. Use "freeze", "mem" '
                                    'or "reboot"')
        if not suspend_count:
            raise error.TestFail('Need to provide non-zero suspend_count')
        original_flog = self.gsc.get_flog()
        logging.debug('Initial FLOG output:\n%s', original_flog)

        suspend_type = reset_type

        # x86 devices should suspend once per reset. ARM will only suspend
        # if the device enters s5.
        if reset_type == 'reboot':
            self._enters_deep_sleep = True
        elif not getattr(self.faft_config, 'suspend_cbmem', True):
            raise error.TestNAError(
                    'Cannot run power_SuspendStress without cbmem support')
        else:
            is_arm = self.check_ec_capability(['arm'], suppress_warning=True)

            # Check if the device supports S0ix.
            self.s0ix_supported = not self.host.run(
                    'check_powerd_config --suspend_to_idle',
                    ignore_status=True).exit_status

            # Check if the device supports S3.
            self.s3_supported = not self.host.run(
                    'grep -q deep /sys/power/mem_sleep',
                    ignore_status=True).exit_status

            if not self.s0ix_supported and not self.s3_supported:
                raise error.TestError(
                        'S3 and S0ix unsupported, can not run test')

            if not self.s0ix_supported and \
               self.check_cr50_capability(['deep_sleep_in_s0i3']):
                raise error.TestError(
                        'Invalid configuration, S0ix not supported, but '
                        'deep_sleep_in_s0i3 is true')

            # TODO(b/333523918): deep sleep stress works on fizz.
            # Remove this when s3 override to unsupported is set back to false
            # on fizz.
            if self.faft_config.platform == 'fizz':
                logging.info('Ignore fizz s3 config')
            elif (self.faft_config.s3_override_to_unsupported
                  or not self.s3_supported):
                logging.info(
                        'S3 unsupported. Switching suspend type from "mem" '
                        'to "freeze"')
                suspend_type = 'freeze'

            if self.check_cr50_capability(['deep_sleep_in_s0i3']) or not \
               self.s3_supported:
                logging.info('Switching suspend type from "mem" to "freeze"')
                suspend_type = 'freeze'

            # Check if the Cr50 enters deep sleep on this device.
            # This variable is used to determine error checks to be performed
            # at the end of testing(Suspend/Resume count vs Cr50 Deep Sleep)
            # Cr50 does not deep sleep on ARM
            # Cr50 does deep sleep in S3
            # Cr50 will only deep sleep in S0i3 on select systems.
            self._enters_deep_sleep = False
            if not is_arm and (suspend_type != 'freeze'
                               or self.check_cr50_capability(
                                       ['deep_sleep_in_s0i3'])):
                logging.info('Check for deep sleep disable script')
                # On suspend some systems send a deep sleep disable command.
                # GSC won't enter deep sleep if that file exists.
                self._enters_deep_sleep = (not self.host.path_exists(
                        self.MEM_DISABLE_DS_PATH))

        if self.faft_config.platform in self.TMP_SKIP_DEVICES[suspend_type]:
            raise error.TestNAError('%s skipped for %s' %
                                    (suspend_type, self.faft_config.platform))

        logging.info('Requested reset: %s', reset_type)
        logging.info('Running with: %s', suspend_type)
        logging.info('DS: %s', 'yes' if self._enters_deep_sleep else 'no')

        self.create_fwmp()

        main_error = None
        try:
            if reset_type == 'reboot':
                self.run_reboots(suspend_count)
            elif reset_type == 'mem' or reset_type == 'freeze':
                self.run_suspend_resume(suspend_count, suspend_type)
            else:
                raise error.TestError('Test can only be run with reset types:'
                                      'reboot, mem, or freeze')
        except Exception as e:
            main_error = e

        errors = []
        # Autotest has some stages in between run_once and cleanup that may
        # be run if the test succeeds. Do this here to make sure this is
        # always run immediately after the suspend/resume cycles.
        # Collect logs for debugging
        # Console information
        self.gsc.dump_nvmem()
        rv = self.check_cr50_deep_sleep(suspend_count)
        if rv:
            errors.append(rv)
        rv = self.check_cr50_version(self.original_cr50_version)
        if rv:
            errors.append(rv)
        # Reenable CCD. Reestablish network connection.
        rv = self.wait_for_client_after_changing_ccd(True)
        if rv:
            errors.append(rv)
        # Information that requires ssh
        rv = self.check_fwmp()
        if rv:
            errors.append(rv)
        rv = self.check_flog_output(original_flog)
        if rv:
            # TODO(b/260779816): enable on ti50 when flog issues are fixed.
            if self.gsc.NAME == 'ti50':
                logging.warning('Ignoring Flog Errors %r', rv)
            else:
                errors.append(rv)
        secondary_error = 'Suspend issues: %s' % ', '.join(errors)
        if main_error:
            logging.info(secondary_error)
            raise main_error
        if errors:
            raise error.TestFail(secondary_error)
