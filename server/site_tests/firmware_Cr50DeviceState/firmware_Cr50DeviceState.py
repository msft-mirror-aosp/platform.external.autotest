# Copyright 2017 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import logging
import pprint
import time
import re

from autotest_lib.client.common_lib import error
from autotest_lib.server import autotest
from autotest_lib.server.cros.faft.cr50_test import Cr50Test

class firmware_Cr50DeviceState(Cr50Test):
    """Verify Cr50 tracks the EC and AP state correctly.

    Put the device through S0, S0ix, S3, and G3. Cr50 responds to these state
    changes by enabling/disabling uart and changing its suspend type. Verify
    that none of these cause any interrupt storms on Cr50. Make sure that there
    aren't any interrupt storms and that Cr50 enters regular or deep sleep a
    reasonable amount of times.
    """
    version = 1

    DEEP_SLEEP_STEP_SUFFIX = ' Num Deep Sleep Steps'

    # Use negative numbers to keep track of counts not in the IRQ list. The
    # actual number don't matter too much. Just make sure deep sleep is the
    # lowest, so it's printed first.
    KEY_DEEP_SLEEP = -10
    KEY_TPM_INIT = -4
    KEY_CMD_END_TIME = -3
    KEY_TIME = -2
    KEY_RESET = -1

    IGNORED_KEYS = [KEY_CMD_END_TIME]
    # TPM initialization time doesn't relate to the previous boot. Don't look
    # at the difference between each step. Look at each value independently.
    STEP_INDEPENDENT_KEYS = [KEY_TPM_INIT]
    GSC_STATUS_DICT = {
            KEY_TPM_INIT : 'TPM init (us)',
            KEY_RESET  : 'Reset Count',
            KEY_DEEP_SLEEP  : 'Deep Sleep Count',
            KEY_TIME  : 'GSC Time',
    }

    # Cr50 won't enable any form of sleep until it has been up for 20 seconds.
    SLEEP_DELAY = 20
    # The time in seconds to wait in each state. Wait one minute so it's long
    # enough for cr50 to settle into whatever state. 60 seconds is also long
    # enough that cr50 has enough time to enter deep sleep twice, so we can
    # catch extra wakeups.
    SLEEP_TIME = 60
    ENTER_STATE_WAIT = 10
    POWER_STATE_CHECK_TRIES = 6
    CONSERVATIVE_WAIT_TIME = SLEEP_TIME * 2

    TPM_INIT_MAX = 120000
    DEEP_SLEEP_MAX = 2
    ARM = 'ARM '
    # If there are over 100,000 interrupts, it is an interrupt storm.
    DEFAULT_COUNTS = [0, 100000]
    # A dictionary of ok count values for each irq that shouldn't follow the
    # DEFAULT_COUNTS range.
    EXPECTED_IRQ_COUNT_RANGE = {
        KEY_TPM_INIT : [0, TPM_INIT_MAX],
        KEY_RESET : [0, 0],
        KEY_DEEP_SLEEP : [0, DEEP_SLEEP_MAX],
        KEY_TIME : [0, CONSERVATIVE_WAIT_TIME],
        'S0ix' + DEEP_SLEEP_STEP_SUFFIX : [0, 0],
        # Cr50 may enter deep sleep an extra time, because of how the test
        # collects taskinfo counts. Just verify that it does enter deep sleep
        'S3' + DEEP_SLEEP_STEP_SUFFIX : [1, 2],
        'G3' + DEEP_SLEEP_STEP_SUFFIX : [1, 2],
        # ARM devices don't enter deep sleep in S3
        ARM + 'S3' + DEEP_SLEEP_STEP_SUFFIX : [0, 0],
        ARM + 'G3' + DEEP_SLEEP_STEP_SUFFIX : [1, 2],
        # Regular sleep is calculated based on the cr50 time
    }
    START = ''
    INCREASE = '+'
    DS_RESUME = 'DS'
    # Keys like tpm initialization time aren't related to the previous boot.
    # Don't look at the value from the previous step to determine anything.
    # Use ' ' since it has to be different from START.
    STEP_INDEPENDENT = ' '

    TMP_POWER_MANAGER_PATH = '/tmp/power_manager'
    POWER_MANAGER_PATH = '/var/lib/power_manager'
    MEM_SLEEP_PATH = '/sys/power/mem_sleep'
    MEM_SLEEP_S0IX = 'echo %s > %s ; sleep 1' % ('s2idle', MEM_SLEEP_PATH)
    MEM_SLEEP_S3 = 'echo %s > %s ; sleep 1' % ('deep', MEM_SLEEP_PATH)
    POWER_STATE_PATH = '/sys/power/state'
    POWER_STATE_S0IX = 'echo %s > %s' % ('freeze', POWER_STATE_PATH)
    POWER_STATE_S3 = 'echo %s > %s' % ('mem', POWER_STATE_PATH)
    # TODO(mruthven): remove ec chan restriction once soraka stops spamming host
    # command output. The extra activity makes it look like a interrupt storm on
    # the EC uart.
    CHAN_ALL = 0xffffffff
    CHAN_EVENTS = 0x20
    CHAN_ACPI = 0x400
    CHAN_HOSTCMD = 0x80
    CHAN_USBCHARGE = 0x200000
    CHAN_RESTRICTED = CHAN_ALL ^ (CHAN_EVENTS | CHAN_ACPI | CHAN_HOSTCMD
                                  | CHAN_USBCHARGE)


    def initialize(self, host, cmdline_args, full_args):
        super(firmware_Cr50DeviceState, self).initialize(host, cmdline_args,
                                                         full_args)
        # Don't bother if there is no Chrome EC or if EC hibernate doesn't work.
        if not self.check_ec_capability():
            raise error.TestNAError("Nothing needs to be tested on this device")

        self.INT_NAME = self.gsc.IRQ_DICT.copy()
        self.INT_NAME.update(self.GSC_STATUS_DICT)
        self.KEY_REGULAR_SLEEP = [k for k,v in self.INT_NAME.items()
                                    if 'WAKEUP' in v][0]
        self.SLEEP_KEYS = [ self.KEY_REGULAR_SLEEP, self.KEY_DEEP_SLEEP ]

        self.deep_sleep_in_s0i3 = self.check_cr50_capability(
            ['deep_sleep_in_s0i3'])

        # If the TPM is reset in S0i3, the CR50 may enter deep sleep during S0i3.
        # Cr50 may enter deep sleep an extra time, because of how the test
        # collects taskinfo counts. So the range is set conservatively to 0-2.
        if self.deep_sleep_in_s0i3:
            irq_s0ix_deep_sleep_key = 'S0ix' + self.DEEP_SLEEP_STEP_SUFFIX
            self.EXPECTED_IRQ_COUNT_RANGE[irq_s0ix_deep_sleep_key] = [0, 2]

    def get_tpm_init_time(self):
        """If the AP is on, return the time it took the tpm to initialize."""
        if not self.gsc.ap_is_on():
            return -1
        result = self.host.run('cbmem -t')
        match = re.search('TPM initialization.*\((.*)\)', result.stdout)
        return int(match.group(1).replace(',', ''))

    def mount_power_config(self):
        """Mounts power_manager settings to tmp,
        ensuring that any changes do not persist across reboots
        """
        self.faft_client.system.run_shell_command(
                'mkdir -p %s && \
            echo 0 > %s/suspend_to_idle && \
            mount --bind %s %s && \
            restart powerd' %
                (self.TMP_POWER_MANAGER_PATH, self.TMP_POWER_MANAGER_PATH,
                 self.TMP_POWER_MANAGER_PATH, self.POWER_MANAGER_PATH), True)

    def umount_power_config(self):
        """Unmounts power_manager settings"""
        self.faft_client.system.run_shell_command(
                'umount %s && restart powerd' % self.POWER_MANAGER_PATH, True)

    def set_suspend_to_idle(self, value):
        """Set suspend_to_idle by writing to power_manager settings"""
        # Suspend to idle expects 0/1 so %d is used
        self.faft_client.system.run_shell_command(
                'echo %d > %s/suspend_to_idle' %
                (value, self.TMP_POWER_MANAGER_PATH), True)

    def log_sleep_debug_information(self):
        """Log some information used for debugging sleep issues"""
        logging.debug(
            self.gsc.send_command_retry_get_output('sleepmask',
                                                    ['sleepmask.*>'],
                                                    safe=True)[0])
        logging.debug(
            self.gsc.send_command_retry_get_output('sysinfo',
                                                    ['sysinfo.*>'],
                                                    safe=True)[0])


    def get_taskinfo_output(self):
        """Return a dict with the irq numbers as keys and counts as values"""
        output = self.gsc.send_command_retry_get_output('taskinfo',
            self.gsc.GET_TASKINFO, safe=True, retries=10)[0][1]
        logging.debug(output)
        return output


    def get_irq_counts(self):
        """Return a dict with the irq numbers as keys and counts as values"""
        irq_counts = { self.KEY_REGULAR_SLEEP : 0 }
        # Running all of these commands may take a while. Track how much time
        # commands are running, so we can offset the cr50 time to set sleep
        # expectations
        start_cmd_time = int(self.gsc.gettime())
        irq_counts[self.KEY_TIME] = start_cmd_time

        output = self.get_taskinfo_output()
        irq_list = re.findall('\d+\s+\d+[\r\n]', output)
        # Make sure the regular sleep irq is in the dictionary, even if cr50
        # hasn't seen any interrupts. It's important the test sees that there's
        # never an interrupt.
        for irq_info in irq_list:
            logging.debug(irq_info)
            num, count = irq_info.split()
            irq_counts[int(num)] = int(count)
        irq_counts[self.KEY_RESET] = int(self.gsc.get_reset_count())
        irq_counts[self.KEY_DEEP_SLEEP] = int(self.gsc.get_deep_sleep_count())
        # Log some information, so we can debug issues with sleep.
        self.log_sleep_debug_information()
        # Track when the commands end, so the test can ignore the time spent
        # running these console commands.
        end_cmd_time = int(self.gsc.gettime())
        irq_counts[self.KEY_CMD_END_TIME] = end_cmd_time
        logging.info('Commands finished in %d seconds',
                     end_cmd_time - start_cmd_time)
        return irq_counts


    def get_expected_count(self, irq_key, cr50_time, idle, ds_resume):
        """Get the expected irq increase for the given irq and state

        Args:
            irq_key: the irq int
            cr50_time: the cr50 time in seconds
            idle: Cr50 should enter regular sleep while the device is idle.

        Returns:
            A list with the expected irq count range [min, max]
        """
        # CCD will prevent sleep
        if self.ccd_enabled and (irq_key in self.SLEEP_KEYS or
            self.DEEP_SLEEP_STEP_SUFFIX in str(irq_key)):
            return [0, 0]
        if irq_key == self.KEY_REGULAR_SLEEP:
            # If cr50_time is really low, we probably woke cr50 up using
            # taskinfo, which would be a pmu wakeup.
            if cr50_time < 5:
                return [0, 1]
            # Only enforce the minimum regular sleep count if the device is
            # idle. Cr50 may not enter regular sleep during power state
            # transitions.
            if idle:
                if cr50_time > self.SLEEP_DELAY:
                    if self.gsc.SLEEP_RATE == 0:
                        min_count = 1
                    else:
                        min_count = cr50_time - self.SLEEP_DELAY
                else:
                    min_count = 0
                # If deep sleep doesn't reset timer, then cr50_time can't be
                # used to know if there was enough time to enter regular sleep
                # after resume from deep sleep.
                if (not self.gsc.DS_RESETS_TIMER) and ds_resume:
                    min_count = 0
            else:
                min_count = 0
            # Check that cr50 isn't continuously entering and exiting sleep.
            # The PMU wakeups should happen around twice a second. Depending
            # on TPM activity it may occur more often. Add 2 to the multiplier
            # to allow for extra wakeups. This is mostly to catch issues that
            # cause cr50 to wake up 100 times a second
            max_count = cr50_time * (self.gsc.SLEEP_RATE + 2)
            return [min_count, max_count]
        # If ccd is disabled, ccd irq counts should not increase.
        if not self.ccd_enabled and (irq_key in self.gsc.CCD_IRQS):
            return [0, 0]
        return self.EXPECTED_IRQ_COUNT_RANGE.get(irq_key, self.DEFAULT_COUNTS)


    def check_increase(self, irq_key, name, increase, expected_range):
        """Verify the irq count is within the expected range

        Args:
            irq_key: the irq int
            name: the irq name string
            increase: the irq count
            expected_range: A list with the valid irq count range [min, max]

        Returns:
            '' if increase is in the given range. If the increase isn't in the
            range, it returns an error message.
        """
        min_count, max_count = expected_range
        if min_count > increase or max_count < increase:
            err_msg = '%s %s: %s not in range %s' % (name, irq_key, increase,
                expected_range)
            return err_msg
        return ''


    def get_step_events(self):
        """Use the deep sleep counts to determine the step events"""
        ds_counts = self.get_irq_step_counts(self.KEY_DEEP_SLEEP)
        events = []
        for i, count in enumerate(ds_counts):
            if not i:
                events.append(self.START)
            elif count != ds_counts[i - 1]:
                # If the deep sleep count changed, Cr50 recovered deep sleep
                # and the irq counts are reset.
                events.append(self.DS_RESUME)
            else:
                events.append(self.INCREASE)
        return events


    def get_irq_step_counts(self, irq_key):
        """Get a list of the all of the step counts for the given irq"""
        return [ irq_dict.get(irq_key, 0) for irq_dict in self.steps ]


    def check_for_errors(self, state):
        """Check for unexpected IRQ counts at each step.

        Find the irq count errors and add them to run_errors.

        Args:
            state: The power state: S0, S0ix, S3, or G3.
        """
        num_steps = len(self.steps)
        # Get all of the deep sleep counts
        events = self.get_step_events()

        irq_list = list(self.irqs)
        irq_list.sort()

        # Pad the start of the step names, so the names align with each step
        # count.
        irq_diff = ['%24s|%s|' % ('', '|'.join(self.step_names))]
        step_errors = [ [] for i in range(num_steps) ]

        end_cmd_times = self.get_irq_step_counts(self.KEY_CMD_END_TIME)
        start_cmd_times = self.get_irq_step_counts(self.KEY_TIME)
        cr50_time_diff = []
        for i, start_time in enumerate(start_cmd_times):
            # The test collects a lot of information using console commands.
            # These take a long time to run and cr50 isn't idle. The idle
            # time is the time this step started minus the time the last set of
            # commands finished running.
            if events[i] == self.INCREASE:
                cr50_time_diff.append(start_time - end_cmd_times[i - 1])
            else:
                cr50_time_diff.append(start_time)

        # Go through each irq and update its info in the progress dict
        for irq_key in irq_list:
            if irq_key in self.IGNORED_KEYS:
                continue
            name = self.INT_NAME.get(irq_key, 'Unknown')
            # Print the IRQ name on the left of the column and the irq number
            # on the right.
            irq_progress_str = ['%-19s %3s' % (name, irq_key)]

            irq_counts = self.get_irq_step_counts(irq_key)
            for step, count in enumerate(irq_counts):
                event = events[step]

                # The deep sleep counts are not reset after deep sleep. Change
                # the event to INCREASE.
                if irq_key == self.KEY_DEEP_SLEEP and event == self.DS_RESUME:
                    event = self.INCREASE

                # If time does not reset after deep sleep change the event to
                # INCREASE.
                if ((not self.gsc.DS_RESETS_TIMER) and
                    irq_key == self.KEY_TIME and event == self.DS_RESUME):
                    event = self.INCREASE

                if irq_key in self.STEP_INDEPENDENT_KEYS:
                    event = self.STEP_INDEPENDENT

                if event == self.INCREASE:
                    count -= irq_counts[step - 1]

                # Check that the count increase is within the expected value.
                if event != self.START:
                    step_name = self.step_names[step].strip()
                    # TODO(b/153891388): raise actual error once the servo
                    # character loss issue is fixed.
                    if count < 0:
                        raise error.TestNAError('%s test found negative %s '
                                                'count %r (likely due to servo '
                                                'dropping characters)' %
                                                (step, step_name, count))
                    expected_range = self.get_expected_count(irq_key,
                            cr50_time_diff[step], 'idle' in step_name,
                            event == self.DS_RESUME)

                    rv = self.check_increase(irq_key, name, count,
                            expected_range)
                    if rv:
                        logging.info('Unexpected count in %s test: %s %s',
                                     state, step_name, rv)
                        step_errors[step].append(rv)

                irq_progress_str.append(' %2s %8d' % (event, count))

            # Separate each step count with '|'. Add '|' to the start and end of
            # the line.
            irq_diff.append('|%s|' % '|'.join(irq_progress_str))

        errors = {}

        ds_key = self.ARM if self.is_arm else ''
        ds_key += state + self.DEEP_SLEEP_STEP_SUFFIX
        expected_range = self.get_expected_count(ds_key, 0, False, False)
        rv = self.check_increase(None, ds_key, events.count(self.DS_RESUME),
                expected_range)
        if rv:
            logging.info('Unexpected count for %s %s', state, rv)
            errors[ds_key] = rv
        for i, step_error in enumerate(step_errors):
            if step_error:
                logging.error('Step %d errors:\n%s', i,
                        pprint.pformat(step_error))
                step = '%s step %d %s' % (state, i, self.step_names[i].strip())
                errors[step] = step_error

        logging.info('DIFF %s IRQ Counts:\n%s', state, '\n'.join(irq_diff))
        if errors:
            logging.info('ERRORS %s IRQ Counts:\n%s', state,
                    pprint.pformat(errors))
            self.run_errors.update(errors)


    def ap_is_on_after_power_button_press(self):
        """Returns True if the AP is on after pressing the power button"""
        self.servo.power_normal_press()
        # Give the AP some time to turn on
        time.sleep(self.gsc.SHORT_WAIT)
        return self.gsc.ap_is_on()


    def trigger_s0(self):
        """Press the power button so the DUT will wake up."""
        if self.ap_is_on_after_power_button_press():
            return
        # Try a second time to see if the AP comes up.
        if not self.ap_is_on_after_power_button_press():
            raise error.TestError('Could not wake the AP using power button')
        logging.warning('Had to press power button twice to wake the AP')


    def enter_state(self, state):
        """Get the command to enter the power state"""
        if state == 'S0':
            self.trigger_s0()
            # Suppress host command output, so it doesn't look like an interrupt
            # storm. Set it whenever the system enters S0 to ensure the setting
            # is restored if the EC enters hibernate.
            time.sleep(2)
            logging.info('Setting EC chan %x', self.CHAN_RESTRICTED)
            self.ec.send_command('chan 0x%x' % self.CHAN_RESTRICTED)
        else:
            if state == 'S0ix':
                self.enter_suspend(state)
            elif state == 'S3':
                self.enter_suspend(state)
            elif state == 'G3':
                self.faft_client.system.run_shell_command('poweroff', True)

        time.sleep(self.ENTER_STATE_WAIT)
        # check state transition
        if not self.wait_power_state(state, self.POWER_STATE_CHECK_TRIES):
            raise error.TestFail('Platform failed to reach %s state.' % state)

    def enter_suspend(self, state):
        """Enter S0ix or S3"""
        # Different devices require different methods to enter S0ix or S3. The
        # ones that deep_sleep_in_s0i3 must use power_manager, but other devices
        # need to bypass power_manager. b/233898484
        if self.deep_sleep_in_s0i3:
            self.set_suspend_to_idle(state == 'S0ix')
            self.suspend()
        else:
            cmds = []
            if self.host.path_exists(self.MEM_SLEEP_PATH):
                if state == 'S0ix':
                    cmds.append(self.MEM_SLEEP_S0IX)
                else:
                    cmds.append(self.MEM_SLEEP_S3)
            if state == 'S0ix':
                cmds.append(self.POWER_STATE_S0IX)
            else:
                cmds.append(self.POWER_STATE_S3)
            cmds = '; '.join(cmds)
            logging.info('enter_suspend %s', cmds)
            self.faft_client.system.run_shell_command(cmds, False)

    def stage_irq_add(self, irq_dict, name=''):
        """Add the current irq counts to the stored dictionary of irq info"""
        self.steps.append(irq_dict)
        self.step_names.append(name.center(12))
        self.irqs.update(irq_dict.keys())
        logging.info('%s:\n%s', name, pprint.pformat(irq_dict))


    def reset_irq_counts(self):
        """Reset the test IRQ counts"""
        self.steps = []
        self.step_names = []
        self.irqs = set(self.GSC_STATUS_DICT.keys())


    def run_transition(self, state):
        """Enter the given power state and reenter s0

        Enter the power state and return to S0. Wait long enough to ensure cr50
        will enter sleep mode, so we can verify that as well.

        Args:
            state: the power state: S0ix, S3, or G3
        """
        self.reset_irq_counts()

        # Enter the given state
        self.enter_state(state)
        self.stage_irq_add(self.get_irq_counts(), 'entered %s' % state)

        logging.info('waiting %d seconds', self.SLEEP_TIME)
        time.sleep(self.SLEEP_TIME)
        # Nothing is really happening. Cr50 should basically be idle during
        # SLEEP_TIME.
        self.stage_irq_add(self.get_irq_counts(), 'idle in %s' % state)

        # Return to S0
        self.enter_state('S0')
        self.stage_irq_add(self.get_irq_counts(), 'entered S0')

        logging.info('waiting %d seconds', self.SLEEP_TIME)
        time.sleep(self.SLEEP_TIME)

        self.stage_irq_add(self.get_irq_counts(), 'idle in S0')

        self.steps[-1][self.KEY_TPM_INIT] = self.get_tpm_init_time()
        logging.info('Resume from %s tpm initialized in %dus', state,
                      self.steps[-1][self.KEY_TPM_INIT])

    def verify_state(self, state):
        """Verify cr50 behavior while running through the power state"""

        try:
            self.run_transition(state)
        finally:
            # reset the system to S0 no matter what happens
            self.trigger_s0()
            # Reenable EC chan output.
            time.sleep(2)
            logging.info('Setting EC chan %x', self.CHAN_ALL)
            self.ec.send_command('chan 0x%x' % self.CHAN_ALL)

        # Check that the progress of the irq counts seems reasonable
        self.check_for_errors(state)


    def is_arm_family(self):
        """Returns True if the DUT is an ARM device."""
        arch = self.host.run('arch').stdout.strip()
        return arch in ['aarch64', 'armv7l']


    def run_through_power_states(self):
        """Go through S0ix, S3, and G3. Verify there are no interrupt storms"""
        self._try_to_bring_dut_up()
        self.run_errors = {}
        self.ccd_str = 'ccd ' + ('enabled' if self.ccd_enabled else 'disabled')
        logging.info('Running through states with %s', self.ccd_str)

        self.gsc.get_ccdstate()
        if not self.gsc.get_sleepmask() and self.ccd_enabled:
            logging.info('Sleepmask is not keeping cr50 up with ccd enabled')
            self.all_errors[self.ccd_str] = 'usb is not active with ccd enabled'
            return

        # Login before entering S0ix so cr50 will be able to enter regular sleep
        client_at = autotest.Autotest(self.host)
        client_at.run_test('login_LoginSuccess')

        # Enter G3 first. All boards support it and tpm initialization will take
        # place. Entering G3 first ensures the tpm initialization data will be
        # from this test run.
        self.verify_state('G3')

        self.mount_power_config()
        try:
            if self.s0ix_supported:
                self.verify_state('S0ix')

            if self.s3_supported:
                self.verify_state('S3')
        finally:
            self.umount_power_config()

        if self.run_errors:
            self.all_errors[self.ccd_str] = self.run_errors


    def run_once(self, host):
        """Go through S0ix, S3, and G3. Verify there are no interrupt storms"""
        self.all_errors = {}
        self.host = host
        self.is_arm = self.is_arm_family()
        supports_dts_control = self.gsc.servo_dts_mode_is_valid()

        if supports_dts_control:
            self.gsc.ccd_disable(raise_error=True)

        self.ccd_enabled = self.gsc.ccd_is_enabled()
        # Check if the device supports S0ix.
        self.s0ix_supported = not self.host.run(
                'check_powerd_config --suspend_to_idle',
                ignore_status=True).exit_status
        # Check if the device supports S3.
        self.s3_supported = not self.host.run(
                'grep -q deep /sys/power/mem_sleep',
                ignore_status=True).exit_status

        self.run_through_power_states()

        if supports_dts_control:
            ccd_was_enabled = self.ccd_enabled
            self.gsc.ccd_enable(raise_error=supports_dts_control)
            self.ccd_enabled = self.gsc.ccd_is_enabled()
            # If the first run had ccd disabled, and the test was able to enable
            # ccd, run through the states again to make sure there are no issues
            # come up when ccd is enabled.
            if not ccd_was_enabled and self.ccd_enabled:
                self.run_through_power_states()
        else:
            logging.info('Current setup only supports test with ccd %sabled.',
                    'en' if self.ccd_enabled else 'dis')

        self.trigger_s0()
        if self.all_errors:
            raise error.TestFail('Unexpected Device State: %s' %
                    self.all_errors)
        if not supports_dts_control:
            raise error.TestNAError('Verified device state with %s. Please '
                    'run with type c servo v4 to test full device state.' %
                    self.ccd_str)
