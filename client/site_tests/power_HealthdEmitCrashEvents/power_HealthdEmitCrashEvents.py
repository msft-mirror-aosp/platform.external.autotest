# Lint as: python3
# Copyright 2023 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import logging
import time
from pathlib import Path
import signal

from autotest_lib.client.common_lib import utils
from autotest_lib.client.cros.power import power_test


class power_HealthdEmitCrashEvents(power_test.power_Test):
    """class for power_HealthdEmitCrashEvents test."""
    version = 1

    def initialize(self,
                   seconds_period=5.,
                   pdash_note='',
                   force_discharge='optional',
                   check_network=False,
                   disable_hdrnet=False):
        """initialize method."""
        super(power_HealthdEmitCrashEvents,
              self).initialize(seconds_period=seconds_period,
                               pdash_note=pdash_note,
                               force_discharge=force_discharge,
                               check_network=check_network,
                               disable_hdrnet=disable_hdrnet)

    def run_once(self,
                 uploaded,
                 duration=900,
                 num_crashes=5,
                 min_run_time_percent=100):
        """run_once method.

        @param uploaded: test with uploaded crashes or unuploaded crashes.
        @param duration: time in seconds to subscribe and measure power.
        @param num_crashes: number of crashes to manufacture.
        @param min_run_time_percent: int between 0 and 100;
                                     run time must be longer than
                                     min_run_time_percent / 100.0 * duration.
        """

        self.start_measurements()
        manufactured_crashes = 0
        while time.time() - self._start_time < duration:
            if manufactured_crashes < num_crashes * (
                    time.time() - self._start_time) // duration + 1:
                self._crash()
                if uploaded:
                    self._upload_crash()
                manufactured_crashes += 1
            # The subscription implicitly sleeps.
            self._subscribe_crash_events(30)
            self.check_force_discharge()
            self.status.refresh()
            if self.status.is_low_battery():
                logging.info('Low battery, stop test early after %.0f minutes',
                             (time.time() - self._start_time) / 60)
                break

        passed_time = time.time() - self._start_time
        if passed_time < min_run_time_percent / 100.0 * duration:
            logging.error(
                    f"The test has ended too soon in {passed_time} seconds, "
                    f"less than {min_run_time_percent}% "
                    f"of the set duration {duration} seconds.")
            return

    def _subscribe_crash_events(self, duration):
        """Subscribe to crash events."""
        utils.run("cros-health-tool event --category=crash "
                  f"--length_seconds={duration}")

    def _crash(self):
        """Manufactures a crash."""
        sleep_job = utils.BgJob("sleep 100")
        if utils.nuke_subprocess(sleep_job.sp, (signal.SIGKILL, )) is None:
            # If process could not be SIGKILL'd, log kernel stack.
            logging.warning(
                    Path('/proc/%d/stack' % sleep_job.sp.pid).read_text())

    def _upload_crash(self):
        """Convert unuploaded crashes to uploaded crashes."""
        utils.run("crash_sender --dev --max_spread_time=0 "
                  "--ignore_hold_off_time")
