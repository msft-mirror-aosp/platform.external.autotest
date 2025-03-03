# Lint as: python3
# Copyright 2018 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import logging
import re
import time

from autotest_lib.client.common_lib import autotest_enum, error, utils
from autotest_lib.server import test
from autotest_lib.server.cros import servo_keyboard_utils
from autotest_lib.server.cros.dark_resume_utils import DarkResumeUtils
from autotest_lib.server.cros.faft.rpc_proxy import RPCProxy
from autotest_lib.server.cros.faft.utils.config import Config as FAFTConfig
from autotest_lib.server.cros.power import servo_charger
from autotest_lib.server.cros.power import utils as power_server_utils
from autotest_lib.server.cros.servo import chrome_ec

# Possible states base can be forced into.
BASE_STATE = autotest_enum.AutotestEnum('ATTACH', 'DETACH', 'RESET')

# Possible states for tablet mode as defined in common/tablet_mode.c via
# crrev.com/c/1797370.
TABLET_MODE = autotest_enum.AutotestEnum('ON', 'OFF', 'RESET')

# List of wake sources expected to cause a full resume.
FULL_WAKE_SOURCES = [
        'INTERNAL_KB', 'PWR_BTN', 'USB_KB', 'LID_OPEN', 'BASE_ATTACH',
        'BASE_DETACH', 'TABLET_MODE_ON', 'TABLET_MODE_OFF'
]

# Alternate List of wake sources expected to cause a full resume.
FULL_WAKE_SOURCES_ALTERNATE = [
        'USB_KB', 'INTERNAL_KB', 'PWR_BTN', 'LID_OPEN', 'BASE_ATTACH',
        'BASE_DETACH', 'TABLET_MODE_ON', 'TABLET_MODE_OFF'
]

# Set of model need to run USB KB before internal KB.
ALTERNATE_MODELS = (
        "arcada",
        "boten",
        "damu",
        "drallion",
        "drallion360",
        "esche",
        "fennel",
        "kappa",
        "katsu",
        "tomato",
)

# List of wake sources expected to cause a dark resume.
DARK_RESUME_SOURCES = ['RTC', 'AC_CONNECTED', 'AC_DISCONNECTED']

# Time in future after which RTC goes off when testing wake due to RTC alarm.
RTC_WAKE_SECS = 20

# Network may take up to 3 minutes to come back if the ethernet dongle is
# resumed in storage mode.
NET_UP_TIMEOUT = 180

# Max time taken by the device to suspend. This includes the time powerd takes
# trigger the suspend after receiving the suspend request from autotest script.
SECS_FOR_SUSPENDING = 25

# Number of seconds to wait after the DUT suspends before resuming it again.
DELAY_BEFORE_RESUMING_SECS = 5

# Time to allow lid transition to take effect.
WAIT_TIME_LID_TRANSITION_SECS = 5

# Time to wait for the DUT to see USB keyboard after restting the Atmega USB
# emulator on Servo.
USB_PRESENT_DELAY = 1

# Time to wait for dark resume listener updating dark resume count in case this
# process is slower than network reconnection.
WAIT_DARK_RESUME_COUNT_SECS = 2

# Time to wait for basestate change to take effect.
BASE_STATE_TRANSITION_SECS = 3

class power_WakeSources(test.test):
    """
    Verify that wakes from input devices can trigger a full
    resume. Currently tests :
        1. power button
        2. lid open
        3. base attach
        4. base detach

    Also tests that dark resume wake sources work as expected, such as:
        1. RTC
        2. AC_CONNECTED
        3. AC_DISCONNECTED

    """
    version = 1

    def _after_resume(self, wake_source):
        """Cleanup to perform after resuming the device.

        @param wake_source: Wake source that has been tested.
        """
        usb_count = self._get_usb_count()
        if wake_source in ['BASE_ATTACH', 'BASE_DETACH']:
            self._force_base_state(BASE_STATE.RESET)
            time.sleep(BASE_STATE_TRANSITION_SECS)
        elif wake_source == 'USB_KB':
            self._host.servo.set_nocheck('init_usb_keyboard', 'off')
            usb_count -= 1
        elif wake_source in ['TABLET_MODE_ON', 'TABLET_MODE_OFF']:
            self._force_tablet_mode(TABLET_MODE.RESET)
        elif wake_source in ['AC_CONNECTED', 'AC_DISCONNECTED']:
            self._chg_manager.start_charging()
        # Servo PD role change may cause Servo's USB devices reset.
        # Ensure any PD role change in previous wake source test will not
        # interrupt the next suspension.
        self._wait_until_usb_count_match(usb_count)

    def _before_suspend(self, wake_source):
        """Prep before suspend.

        @param wake_source: Wake source that is going to be tested.

        @return: Boolean, whether _before_suspend action is successful.
        """
        usb_count = self._get_usb_count()
        if wake_source == 'BASE_ATTACH':
            # Force detach before suspend so that attach won't be ignored.
            self._force_base_state(BASE_STATE.DETACH)
            time.sleep(BASE_STATE_TRANSITION_SECS)
        elif wake_source == 'BASE_DETACH':
            # Force attach before suspend so that detach won't be ignored.
            self._force_base_state(BASE_STATE.ATTACH)
            time.sleep(BASE_STATE_TRANSITION_SECS)
        elif wake_source == 'LID_OPEN':
            # Set the power policy for lid closed action to suspend.
            return self._host.run(
                'set_power_policy --lid_closed_action suspend',
                ignore_status=True).exit_status == 0
        elif wake_source == 'USB_KB':
            # Initialize USB keyboard.
            self._host.servo.set_nocheck('init_usb_keyboard', 'on')
            utils.poll_for_condition(
                    condition=lambda: servo_keyboard_utils.
                    is_servo_usb_keyboard_present(self._host) is True,
                    desc='Wait for the servo keyboard presence',
                    timeout=USB_PRESENT_DELAY)
            servo_keyboard_utils.set_servo_keyboard_persist(self._host)
        elif wake_source == 'TABLET_MODE_ON':
            self._force_tablet_mode(TABLET_MODE.OFF)
        elif wake_source == 'TABLET_MODE_OFF':
            self._force_tablet_mode(TABLET_MODE.ON)
        elif wake_source == 'AC_CONNECTED':
            self._chg_manager.stop_charging()
        elif wake_source == 'AC_DISCONNECTED':
            self._chg_manager.start_charging()
        # Servo PD role change may cause Servo's USB devices reset
        # Ensure all USB devices have been connected to avoid interrupting
        # the following suspension
        # Note that Servo's USB_KB is already on and connected during
        # _is_valid_wake_source so the usb_count is unchanged
        self._wait_until_usb_count_match(usb_count)
        return True

    def _force_tablet_mode(self, mode):
        """Send EC command to force the tablet mode.

        @param mode: mode to force. One of the |TABLET_MODE| enum.
        """
        ec_cmd = 'tabletmode '
        ec_arg = {
            TABLET_MODE.ON: 'on',
            TABLET_MODE.OFF: 'off',
            TABLET_MODE.RESET: 'r'
        }

        ec_cmd += ec_arg[mode]
        self._ec.send_command(ec_cmd)

    def _force_base_state(self, base_state):
        """Send EC command to force the |base_state|.

        @param base_state: State to force base to. One of |BASE_STATE| enum.
        """
        ec_cmd = 'basestate '
        ec_arg = {
            BASE_STATE.ATTACH: 'a',
            BASE_STATE.DETACH: 'd',
            BASE_STATE.RESET: 'r'
        }

        ec_cmd += ec_arg[base_state]
        self._ec.send_command(ec_cmd)

    def _x86_get_ec_wake_mask(self):
        # Check both the S0ix and S3 wake masks.
        try:
            s0ix_wake_mask = int(self._host.run(
                    'ectool hostevent get %d' %
                    chrome_ec.EC_HOST_EVENT_LAZY_WAKE_MASK_S0IX).stdout,
                                 base=16)
        except error.AutoservRunError as e:
            s0ix_wake_mask = 0
            logging.info(
                    '"ectool hostevent get" failed for s0ix wake mask with'
                    ' exception: %s', str(e))

        try:
            s3_wake_mask = int(self._host.run(
                    'ectool hostevent get %d' %
                    chrome_ec.EC_HOST_EVENT_LAZY_WAKE_MASK_S3).stdout,
                               base=16)
        except error.AutoservRunError as e:
            s3_wake_mask = 0
            logging.info(
                    '"ectool hostevent get" failed for s3 wake mask with'
                    ' exception: %s', str(e))

        return s0ix_wake_mask | s3_wake_mask

    def _arm_get_ec_wake_mask(self):
        try:
            s3_mkbpwakemask_out = self._host.run(
                    'ectool mkbpwakemask get hostevent').stdout
            match = re.match(r'MBKP hostevent wake mask: (0x[0-9A-Fa-f]+)',
                             s3_mkbpwakemask_out)
            if match:
                return int(match.group(1), base=16)
            else:
                logging.info(
                        '"ectool mkbpwakemask get hostevent" returned: %s',
                        s3_mkbpwakemask_out)
        except error.AutoservRunError as e:
            logging.info(
                    '"ectool mkbpwakemask get hostevent" failed with'
                    ' exception: %s', str(e))

        return 0

    def _get_usb_count(self):
        return int(self._host.run('lsusb | wc -l').stdout)

    def _wait_until_usb_count_match(self, expected_usb_count, timeout=5):
        start_time = time.time()
        while time.time() - start_time < timeout:
            usb_count = self._get_usb_count()
            if usb_count == expected_usb_count:
                return
            time.sleep(1)
        logging.warn('Timeout waiting for USB probing.')

    def _is_valid_wake_source(self, wake_source):
        """Check if |wake_source| is valid for DUT.

        @param wake_source: wake source to verify.
        @return: False if |wake_source| is not valid for DUT, True otherwise
        """
        if wake_source in ['BASE_ATTACH', 'BASE_DETACH']:
            return self._ec.has_command('basestate')
        if wake_source in ['TABLET_MODE_ON', 'TABLET_MODE_OFF']:
            return self._ec.has_command('tabletmode')
        if wake_source == 'PWR_BTN':
            # Chromebox with no external display will shutdown on PWR_BTN.
            return self._host.has_internal_display(
            ) or self._host.has_external_display()
        if wake_source == 'LID_OPEN':
            return self._dr_utils.host_has_lid()
        if wake_source == 'INTERNAL_KB':
            return self._faft_config.has_keyboard
        if wake_source == 'USB_KB':
            # Initialize USB keyboard.
            self._host.servo.set_nocheck('init_usb_keyboard', 'on')
            time.sleep(USB_PRESENT_DELAY)
            # Check if DUT can see a wake capable Atmel USB keyboard.
            if not servo_keyboard_utils.is_servo_usb_keyboard_present(
                    self._host):
                logging.error('DUT cannot see a Atmel USB keyboard.')
            elif not servo_keyboard_utils.is_servo_usb_wake_capable(
                    self._host):
                logging.error('Atmel USB keyboard does not have required wake '
                              'capability.')
            return True
        if wake_source in ['AC_CONNECTED', 'AC_DISCONNECTED']:
            if not self._host.has_battery():
                logging.info("%s is not supported on devices without battery",
                             wake_source)
                return False

            arch = self._host.get_architecture()
            wake_mask = 0
            if not self._chg_manager:
                logging.warning(
                    'Unable to test AC connect/disconnect with this '
                    'servo setup')
                return False
            elif arch.startswith('x86'):
                wake_mask = self._x86_get_ec_wake_mask()
            elif arch.startswith('arm'):
                wake_mask = self._arm_get_ec_wake_mask()

            supported = False
            if wake_source == 'AC_CONNECTED':
                supported = wake_mask & chrome_ec.HOSTEVENT_AC_CONNECTED
            elif wake_source == 'AC_DISCONNECTED':
                supported = wake_mask & chrome_ec.HOSTEVENT_AC_DISCONNECTED

            if not supported:
                logging.info(
                        '%s not supported. Platforms launched in 2020 or before'
                        ' may not require it. Wake mask: 0x%x', wake_source,
                        wake_mask)
                return False

        return True

    def _test_wake(self, wake_source, full_wake):
        """Test if |wake_source| triggers a full resume.

        @param wake_source: wake source to test. One of |FULL_WAKE_SOURCES|.
        @raises: error.TestFail if |wake_source| does not correctly trigger the
            expected type of wake.
        """
        is_success = True
        fail_msg = None
        logging.info(
                'Testing wake by %s triggers a %s wake when dark resume is '
                'enabled.', wake_source, 'full' if full_wake else 'dark')
        if not self._before_suspend(wake_source):
            logging.error('Before suspend action failed for %s', wake_source)
            # Still run the _after_resume callback since we can do things like
            # stop charging.
            self._after_resume(wake_source)
            raise error.TestFail(
                'Before suspend action failed for %s.' % wake_source)

        count_before = self._dr_utils.count_dark_resumes()
        rtc_wake = NET_UP_TIMEOUT
        if wake_source == 'RTC':
            rtc_wake = RTC_WAKE_SECS
        self._dr_utils.suspend(SECS_FOR_SUSPENDING + rtc_wake)
        if self._ec.has_command('powerinfo'):
            suspended = power_server_utils.wait_power_state(
                    self._ec,
                    'S0ix|S3',
                    retries=SECS_FOR_SUSPENDING,
                    retry_delay=1)
            if not suspended:
                logging.error('DUT failed to suspend for %s', wake_source)
                self._after_resume(wake_source)
                raise error.TestFail('DUT failed to suspend for %s.' %
                                     wake_source)
        logging.info('DUT suspended! Waiting to resume...')
        # Leave the DUT suspended for a short while before triggering resume,
        # so that there is a clear separation in the logs.
        time.sleep(DELAY_BEFORE_RESUMING_SECS)

        self._trigger_wake(wake_source)

        # Give enough time to reconnect if the ethernet dongle accidentally
        # comes up in storage mode.
        if not self._host.wait_up(timeout=NET_UP_TIMEOUT):
            # Try to reset the DUT's ethernet if it doesn't return, then wait
            # for it to come back online again.
            if self._host.servo.supports_eth_power_control():
                self._host.servo.eth_power_reset()
            else:
                self._host.servo.usb_mux_reset()
            if not self._host.wait_up(timeout=NET_UP_TIMEOUT):
                logging.error(
                        'Device did not resume from suspend for %s.'
                        ' Waking system with power button then RTC.',
                        wake_source)
                self._trigger_wake('PWR_BTN')
                self._after_resume(wake_source)
                if not self._host.is_up():
                    raise error.TestFail(
                            'Device failed to wakeup from backup wake sources'
                            ' (power button and RTC).')
                raise error.TestFail(
                        'Device did not resume from suspend for %s.' %
                        wake_source)

        time.sleep(WAIT_DARK_RESUME_COUNT_SECS)
        count_after = self._dr_utils.count_dark_resumes()
        if full_wake:
            if count_before != count_after:
                fail_msg = '%s incorrectly caused a dark resume.' % wake_source
                logging.error(fail_msg)
                is_success = False
            elif is_success:
                logging.info('%s caused a full resume.', wake_source)
        else:
            if count_before == count_after:
                fail_msg = '%s incorrectly caused a full resume.' % wake_source
                logging.error(fail_msg)
                is_success = False
            elif is_success:
                logging.info('%s caused a dark resume.', wake_source)

        # Press <ctrl_l> button to ensure a full resume instead of dark resume
        self._ec.key_press('<ctrl_l>')

        self._after_resume(wake_source)
        if not is_success:
            raise error.TestFail(fail_msg)

    def _trigger_wake(self, wake_source):
        """Trigger wake using the given |wake_source|.

        @param wake_source : wake_source that is being tested.
            One of |FULL_WAKE_SOURCES|.
        """
        if wake_source == 'PWR_BTN':
            self._host.servo.power_short_press()
        elif wake_source == 'LID_OPEN':
            self._host.servo.lid_close()
            time.sleep(WAIT_TIME_LID_TRANSITION_SECS)
            self._host.servo.lid_open()
        elif wake_source == 'BASE_ATTACH':
            self._force_base_state(BASE_STATE.ATTACH)
        elif wake_source == 'BASE_DETACH':
            self._force_base_state(BASE_STATE.DETACH)
        elif wake_source == 'TABLET_MODE_ON':
            self._force_tablet_mode(TABLET_MODE.ON)
        elif wake_source == 'TABLET_MODE_OFF':
            self._force_tablet_mode(TABLET_MODE.OFF)
        elif wake_source == 'INTERNAL_KB':
            self._host.servo.ctrl_key()
        elif wake_source == 'USB_KB':
            self._host.servo.set_nocheck('usb_keyboard_enter_key', '10')
        elif wake_source == 'RTC':
            # The RTC will wake on its own. We just need to wait
            time.sleep(RTC_WAKE_SECS)
        elif wake_source == 'AC_CONNECTED':
            self._chg_manager.start_charging()
        elif wake_source == 'AC_DISCONNECTED':
            self._chg_manager.stop_charging()

    def cleanup(self):
        """cleanup."""
        if hasattr(self, '_dr_utils'):
            self._dr_utils.resume_ethernet_check_on_host()
            self._dr_utils.stop_resuspend_on_dark_resume(False)
            self._dr_utils.teardown()

    def initialize(self, host):
        """Initialize wake sources tests.

        @param host: Host on which the test will be run.
        """
        self._host = host
        self._ec = chrome_ec.ChromeEC(self._host.servo)
        self._faft_client = RPCProxy(host)
        self._faft_config = FAFTConfig(
                self._faft_client.system.get_platform_name(),
                self._faft_client.system.get_model_name())
        self._kstr = host.get_kernel_version()
        usb_count = self._get_usb_count()
        # TODO(b/168939843) : Look at implementing AC plug/unplug w/ non-PD RPMs
        # in the lab.
        try:
            self._chg_manager = servo_charger.ServoV4ChargeManager(
                host, host.servo)
        except error.TestNAError:
            logging.warning('Servo does not support AC switching.')
            self._chg_manager = None
        # Servo PD role change may cause Servo's USB devices reset
        # Ensure all USB devices have been connected before start
        self._wait_until_usb_count_match(usb_count)

        # Skip the test if dark resume is disabled
        try:
            self._host.run('check_powerd_config --dark_resume_enabled')
        except error.AutoservRunError:
            raise error.TestNAError("Device does not have dark resume enabled")

        self._dr_utils = DarkResumeUtils(host)
        self._dr_utils.stop_resuspend_on_dark_resume()
        self._dr_utils.pause_ethernet_check_on_host()

    def run_once(self):
        """Body of the test."""

        passed_ws = []
        failed_ws = []
        skipped_ws = []
        fail_msgs = []

        full_wake_sources = FULL_WAKE_SOURCES
        if self._host.get_model_from_cros_config() in ALTERNATE_MODELS:
            full_wake_sources = FULL_WAKE_SOURCES_ALTERNATE

        for ws in full_wake_sources:
            if not self._is_valid_wake_source(ws):
                skipped_ws.append(ws)
                continue
            try:
                self._test_wake(ws, True)
            except error.TestFail as e:
                failed_ws.append(ws)
                fail_msgs.append(str(e))
            else:
                passed_ws.append(ws)

        for ws in DARK_RESUME_SOURCES:
            if not self._is_valid_wake_source(ws):
                skipped_ws.append(ws)
                continue
            try:
                self._test_wake(ws, False)
            except error.TestFail as e:
                failed_ws.append(ws)
                fail_msgs.append(str(e))
            else:
                passed_ws.append(ws)

        test_keyval = {}

        for ws in passed_ws:
            test_keyval.update({ws: 'PASS'})
        for ws in failed_ws:
            test_keyval.update({ws: 'FAIL'})
        for ws in skipped_ws:
            test_keyval.update({ws: 'SKIPPED'})
        self.write_test_keyval(test_keyval)

        if passed_ws:
            logging.info('[%s] woke the device as expected.',
                         ', '.join(passed_ws))

        if skipped_ws:
            logging.info(
                '[%s] are not wake sources on this platform. '
                'Please test manually if not the case.',
                ', '.join(skipped_ws))

        if failed_ws:
            logging.info(
                '[%s] wake sources did not behave as expected.',
                ', '.join(failed_ws))
            raise error.TestFail(' '.join(fail_msgs))
