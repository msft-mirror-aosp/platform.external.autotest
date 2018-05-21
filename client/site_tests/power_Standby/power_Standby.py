# Copyright (c) 2011 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import logging, math, time

from autotest_lib.client.bin import test
from autotest_lib.client.common_lib import error
from autotest_lib.client.cros import rtc
from autotest_lib.client.cros.power import power_dashboard
from autotest_lib.client.cros.power import power_status
from autotest_lib.client.cros.power import power_telemetry_utils
from autotest_lib.client.cros.power import power_utils
from autotest_lib.client.cros.power import sys_power


class power_Standby(test.test):
    """Measure Standby power test."""
    version = 1
    _percent_min_charge = 10
    _min_sample_hours = 0.1

    def initialize(self):
        """Reset force discharge state."""
        self._force_discharge_enabled = False

    def run_once(self, test_hours=None, sample_hours=None,
                 max_milliwatts_standby=500, ac_ok=False,
                 force_discharge=False):
        """Put DUT to suspend state for |sample_hours| and measure power."""
        if not power_utils.has_battery():
            raise error.TestNAError('Skipping test because DUT has no battery.')

        if test_hours < sample_hours:
            raise error.TestFail('Test hours must be greater than sample '
                                 'hours.')

        # If we're measuring < 6min of standby then the S0 time is not
        # negligible. Note, reasonable rule of thumb is S0 idle is ~10-20 times
        # standby power.
        if sample_hours < self._min_sample_hours:
            raise error.TestFail('Must standby more than %.2f hours.' % \
                                 sample_hours)

        power_stats = power_status.get_status()

        if not ac_ok and power_stats.on_ac():
            raise error.TestError('On AC, please unplug power supply.')

        if force_discharge:
            if not power_stats.on_ac():
                raise error.TestError('Not on AC, please plug in power supply '
                                      'to attempt force discharge.')
            if not power_utils.charge_control_by_ectool(False):
                raise error.TestError('Unable to force discharge.')

            self._force_discharge_enabled = True

        charge_start = power_stats.battery[0].charge_now
        voltage_start = power_stats.battery[0].voltage_now

        max_hours = ((charge_start * voltage_start) /
                     (max_milliwatts_standby / 1000.))
        if max_hours < test_hours:
            raise error.TestFail('Battery not charged adequately for test.')

        elapsed_hours = 0

        results = {}
        loop = 0
        power_telemetry_utils.start_measurement()

        while elapsed_hours < test_hours:
            charge_before = power_stats.battery[0].charge_now
            before_suspend_secs = rtc.get_seconds()
            sys_power.do_suspend(sample_hours * 3600)
            after_suspend_secs = rtc.get_seconds()

            power_stats.refresh()
            if power_stats.percent_current_charge() < self._percent_min_charge:
                logging.warning('Battery = %.2f%%.  Too low to continue.')
                break

            # check that the RTC slept the correct amount of time as there could
            # potentially be another wake source that would spoil the test.
            actual_hours = (after_suspend_secs - before_suspend_secs) / 3600.0
            percent_diff = math.fabs((actual_hours - sample_hours) / (
                    (actual_hours + sample_hours) / 2) * 100)
            if percent_diff > 2:
                err = 'Requested standby time and actual varied by %.2f%%.' \
                    % percent_diff
                raise error.TestFail(err)

            # Check resulting charge consumption
            charge_used = charge_before - power_stats.battery[0].charge_now
            elapsed_hours += actual_hours
            logging.debug(
                    'loop%d done: loop hours %.3f, elapsed hours %.3f '
                    'charge used: %.3f', loop, actual_hours, elapsed_hours,
                    charge_used)
            loop += 1

        power_telemetry_utils.end_measurement()
        charge_end = power_stats.battery[0].charge_now
        total_charge_used = charge_start - charge_end
        if total_charge_used <= 0:
            raise error.TestError('Charge used is suspect.')

        voltage_end = power_stats.battery[0].voltage_now
        standby_hours = power_stats.battery[0].charge_full_design / \
                        total_charge_used * elapsed_hours
        energy_used = (voltage_start + voltage_end) / 2 * \
                      total_charge_used

        results['ah_charge_start'] = charge_start
        results['ah_charge_now'] = charge_end
        results['ah_charge_used'] = total_charge_used
        results['force_discharge'] = self._force_discharge_enabled
        results['hours_standby_time'] = standby_hours
        results['hours_standby_time_tested'] = elapsed_hours
        results['v_voltage_start'] = voltage_start
        results['v_voltage_now'] = voltage_end
        results['w_energy_rate'] = energy_used / elapsed_hours
        results['wh_energy_used'] = energy_used

        self.write_perf_keyval(results)
        pdash = power_dashboard.SimplePowerLoggerDashboard(
                test_hours * 3600., results['w_energy_rate'],
                self.tagged_testname, self.resultsdir)
        pdash.upload()

        self.output_perf_value(description='hours_standby_time',
                               value=results['hours_standby_time'],
                               units='hours', higher_is_better=True)
        self.output_perf_value(description='w_energy_rate',
                               value=results['w_energy_rate'], units='watts',
                               higher_is_better=False)

        # need to sleep for some time to allow network connection to return
        time.sleep(10)

    def cleanup(self):
        """Clean up force discharge."""
        if self._force_discharge_enabled:
            power_utils.charge_control_by_ectool(True)
