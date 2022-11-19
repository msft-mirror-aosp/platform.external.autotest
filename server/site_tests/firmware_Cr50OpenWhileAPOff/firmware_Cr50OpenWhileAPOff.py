# Copyright 2018 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import logging
import time

from autotest_lib.client.common_lib import error
from autotest_lib.server.cros.faft.cr50_test import Cr50Test
from autotest_lib.server.cros.servo import servo


class firmware_Cr50OpenWhileAPOff(Cr50Test):
    """Verify the console can be opened while the AP is off.

    Make sure it runs ok when cr50 saw the AP turn off and when it resets while
    the AP is off.

    This test would work the same with any cr50 ccd command that uses vendor
    commands. 'ccd open' is just one.
    """
    version = 1

    # Ti50 delays deep sleep for 60 seconds after AP turns on.
    SLEEP_DELAY = 65
    SHORT_DELAY = 2
    CCD_PASSWORD_RATE_LIMIT = 3

    def initialize(self, host, cmdline_args, full_args):
        """Initialize the test"""
        self.changed_dut_state = False
        super(firmware_Cr50OpenWhileAPOff, self).initialize(host, cmdline_args,
                full_args)

        if not hasattr(self, 'gsc'):
            raise error.TestNAError('Test can only be run on devices with '
                                    'access to the GSC console')

        # c2d2 uses cr50 for ec reset. The setting doesn't survive deep sleep.
        # This test needs ec reset to survive deep sleep to keep the AP off.
        if 'c2d2' in self.servo.get_servo_type():
            raise error.TestNAError('Cannot rely on ecrst with c2d2')

        # TODO(mruthven): replace with dependency on servo v4 with servo micro
        # and type c cable.
        if ('servo_v4' not in self.servo.get_servo_type()
                    or not self.servo.main_device_is_flex()):
            raise error.TestNAError('Must use servo v4 with servo_micro')

        if not self.gsc.servo_dts_mode_is_valid():
            raise error.TestNAError('Plug in servo v4 type c cable into ccd '
                    'port')

        self.fast_ccd_open(enable_testlab=True)
        # make sure password is cleared.
        self.gsc.ccd_reset()
        # Set GscFullConsole to Always, so we can always use gpioset.
        self.gsc.set_cap('GscFullConsole', 'Always')
        # You can only open cr50 from the console if a password is set. Set
        # a password, so we can use it to open cr50 while the AP is off.
        self.set_ccd_password(self.CCD_PASSWORD)

        # Asserting warm_reset will hold the AP in reset if the system uses
        # SYS_RST instead of PLT_RST. If the system uses PLT_RST, we have to
        # hold the EC in reset to guarantee the device won't turn on during
        # open.
        # warm_reset doesn't interfere with rdd, so it's best to use that when
        # possible.
        self.reset_ec = self.gsc.uses_board_property('BOARD_USE_PLT_RESET')
        self.changed_dut_state = True
        if self.reset_ec and not self.check_deep_sleep_while_off():
            # Some devices can't tell the AP is off when the EC is off. Try
            # deep sleep with just the AP off.
            self.reset_ec = False
            # If deep sleep doesn't work at all, we can't run the test.
            if not self.check_deep_sleep_while_off():
                raise error.TestNAError('Skipping test on device without deep '
                        'sleep support')
            # We can't hold the ec in reset and enter deep sleep. Set the
            # capability so physical presence isn't required for open.
            logging.info("deep sleep doesn't work with EC in reset. skipping "
                         "physical presence checks.")
            # set OpenNoLongPP so open won't require pressing the power button.
            self.gsc.set_cap('OpenNoLongPP', 'Always')
        else:
            logging.info('Physical presence can be used during open')


    def cleanup(self):
        """Make sure the device is on at the end of the test"""
        # If we got far enough to start changing the DUT power state, attempt to
        # turn the DUT back on and reenable the cr50 console.
        try:
            if self.changed_dut_state:
                self.restore_dut()
        finally:
            super(firmware_Cr50OpenWhileAPOff, self).cleanup()


    def restore_dut(self):
        """Turn on the device and reset cr50

        Do a deep sleep reset to fix the cr50 console. Then turn the device on.

        Raises:
            TestFail if the cr50 console doesn't work
        """
        logging.info('attempt cr50 console recovery')

        # The console may be hung. Run through reset manually, so we dont need
        # the console.
        self.turn_device('off')
        # Toggle dts mode to enter and exit deep sleep
        self.toggle_dts_mode()
        # Turn the device back on
        self.turn_device('on')

        # Verify the cr50 console responds to commands.
        try:
            logging.info(self.gsc.get_ccdstate())
        except servo.ResponsiveConsoleError as e:
            logging.info('Console is responsive. Unable to match output: %s',
                         str(e))
        except servo.UnresponsiveConsoleError as e:
            raise error.TestFail('Could not restore GSC console')
        logging.info('GSC console ok.')


    def turn_device(self, state):
        """Turn the device off or on.

        If we are testing ccd open fully, it will also assert device reset so
        power button presses wont turn on the AP
        """
        # Assert or deassert the device reset signal. The reset signal state
        # should be the inverse of the device state.
        reset_signal_state = 'on' if state == 'off' else 'off'
        if self.reset_ec:
            self.servo.set('cold_reset', reset_signal_state)
        else:
            self.servo.set('warm_reset', reset_signal_state)

        time.sleep(self.SHORT_DELAY)

        # Press the power button to turn on the AP, if it doesn't automatically
        # turn on after deasserting the reset signal. ap_is_on will print the
        # ccdstate which is useful for debugging. Do that first, so it always
        # happens.
        if not self.gsc.ap_is_on() and state == 'on':
            self.servo.power_normal_press()
            time.sleep(self.SHORT_DELAY)


    def check_deep_sleep_while_off(self):
        """Check Cr50 entered deep sleep when device was off.

        Returns:
            True if Cr50 entered deep sleep
        """
        self.turn_device('off')
        # Do a deep sleep reset to restore the cr50 console.
        ds = self.check_deep_sleep()
        self.turn_device('on')
        return ds


    def set_dts(self, state):
        """Set servo v4 dts mode"""
        self.servo.set_dts_mode(state)
        # Some boards can't detect DTS mode when the EC is off. After 0.X.18,
        # we can set CCD_MODE_L manually using gpioset. If detection is working,
        # this won't do anything. If it isn't working, it'll force cr50 to
        # disconnect ccd.
        if state == 'off':
            time.sleep(self.SHORT_DELAY)
            self.gsc.send_command('gpioset CCD_MODE_L 1')


    def toggle_dts_mode(self):
        """Toggle DTS mode to enable and disable deep sleep"""
        # We cant use cr50 ccd_disable/enable, because those uses the cr50
        # console. Call servo_v4_dts_mode directly.
        self.set_dts('off')

        time.sleep(self.SLEEP_DELAY)
        self.set_dts('on')


    def check_deep_sleep(self):
        """Toggle ccd to enter deep sleep

        Returns:
            True if Cr50 entered deep sleep
        """
        start_count = self.gsc.get_deep_sleep_count()
        # CCD is what's keeping Cr50 awake. Toggle DTS mode to turn off ccd
        # so cr50 will enter deep sleep
        self.toggle_dts_mode()
        # Return the number of times cr50 entered deep sleep.
        return self.gsc.get_deep_sleep_count() > start_count


    def try_ccd_open(self, deep_sleep):
        """Try 'ccd open' and make sure the console doesn't hang"""
        self.gsc.set_ccd_level('lock', self.CCD_PASSWORD)
        try:
            self.turn_device('off')
            if deep_sleep:
                if not self.check_deep_sleep():
                    raise error.TestFail('Did not detect deep sleep')
            # Verify ccd open
            self.gsc.set_ccd_level('open', self.CCD_PASSWORD)
        finally:
            self.restore_dut()


    def run_once(self):
        """Turn off the AP and try ccd open."""
        self.try_ccd_open(False)
        self.try_ccd_open(True)
