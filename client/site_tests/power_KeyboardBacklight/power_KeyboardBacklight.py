# Lint as: python3
# Copyright 2022 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
import time

from autotest_lib.client.common_lib import error
from autotest_lib.client.cros import cros_ui
from autotest_lib.client.cros.power import power_test

class power_KeyboardBacklight(power_test.power_Test):
    """class for power_KeyboardBacklight test.

    Measures power consumption of the keyboard backlight at different
    brightnesses.
    """
    version = 1

    def run_once(self, sec_rest=30, percent_step_size=10, sec_per_step=30):
        """
        Measures power consumption of the keyboard backlight at different
        brightness steps.

        @param sec_rest: int in seconds to cool down before setting the
                keyboard backlight brightness.
        @param percent_step_size: int for brightness step size in nonlinear
                percentage.
        @param sec_per_step: int in seconds for how much time to measure in
                each step.

        @raise error.TestNAError: the DUT has no keyboard backlight.
        @raise KbdBacklightException: unable to control keyboard backlight
                brightness.
        """
        if not self.kbd_backlight:
            raise error.TestNAError('Keyboard backlight does not exist')

        cros_ui.stop(allow_fail=True)
        # Stop services and disable multicast again as Chrome might have
        # restarted them.
        self._services.stop_services()
        self.notify_ash_discharge_status()
        self._multicast_disabler.disable_network_multicast()

        brightnesses = [{
                'nonlinear':
                nonlinear,
                'linear':
                self.kbd_backlight.nonlinear_to_linear(nonlinear)
        } for nonlinear in range(100, -1, -percent_step_size)]

        self.kbd_backlight.set_percent(brightnesses[0]['linear'])
        time.sleep(sec_rest)

        self.start_measurements()

        for loop, brightness in enumerate(brightnesses):
            self.kbd_backlight.set_percent(brightness['linear'])
            tagname = (
                f'{self.tagged_testname}_'
                f'nonlinear_{brightness["nonlinear"]:.2f}_'
                f'linear_{brightness["linear"]:.2f}'
            )
            loop_start = time.time()
            self.loop_sleep(loop, sec_per_step)
            self.checkpoint_measurements(tagname, loop_start)

    def cleanup(self):
        """Reset to previous state."""
        cros_ui.start(allow_fail=True)
        super(power_KeyboardBacklight, self).cleanup()
