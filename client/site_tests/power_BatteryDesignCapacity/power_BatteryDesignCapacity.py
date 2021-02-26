# Copyright 2020 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import time

from autotest_lib.client.common_lib import error
from autotest_lib.client.cros.power import power_status
from autotest_lib.client.cros.power import power_test
from autotest_lib.client.cros.power import power_utils

SEC_PERIOD = 1.0
SEC_WARMUP = 1.0
SEC_SLEEP = 5.0

RATIO_AND_CYCLE_COUNT = ('Device battery last full charge / design capacity '
                         'ratio is %f%%, cycle count is %d. ')

# For batteries with 11 to 50 charge cycles, require last full charge > 98%
# of battery design capacity. For batteries with 51 to 300 charge cycles,
# require last full charge > 75% of battery design capacity. For batteries
# outside these ranges, throw TestNAError.
BATTERY_REQUIREMENT = ((10, -1.0), (50, 98.0), (300, 75.0))


class power_BatteryDesignCapacity(power_test.power_Test):
    """Test to qualify whether last full charge meets battery design capacity.
    """
    version = 1

    def initialize(self, pdash_note=''):
        """Measure power with a short interval."""
        super(power_BatteryDesignCapacity,
              self).initialize(seconds_period=SEC_PERIOD,
                               pdash_note=pdash_note)

    def warmup(self):
        """Warm up for a short time."""
        super(power_BatteryDesignCapacity, self).warmup(warmup_time=SEC_WARMUP)

    def run_once(self, requirement=BATTERY_REQUIREMENT):
        """
        Collect battery charge data and check if last full charge meets battery
        design capacity.

        @param requirement: last full charge / battery design capacity percentage
                            expected for cycle count, listed from low cycle count
                            to high cycle count.
        """
        if not power_utils.has_battery():
            raise error.TestNAError(
                    'Skipping test because DUT has no battery.')

        self.start_measurements()

        b = power_status.get_status().battery
        keyvals = dict()
        err = None
        cycle_count = b.cycle_count
        keyvals['cycle_count'] = cycle_count
        keyvals['ah_charge_full'] = b.charge_full
        keyvals['ah_charge_full_design'] = b.charge_full_design
        percent_full_vs_design = 100.0 * b.charge_full / b.charge_full_design
        keyvals['percent_full_vs_design'] = percent_full_vs_design
        keyvals['battery_design_capacity_qualify'] = False
        keyvals['manufacturer'] = b.manufacturer
        keyvals['model_name'] = b.model_name
        keyvals['serial_number'] = b.serial_number
        keyvals['battery_id'] = (b.manufacturer + '_' + b.model_name + '_' +
                                 b.serial_number)

        if len(requirement) < 2:
            raise error.TestFail(
                    'Battery design capacity requirement has wrong format.')

        if cycle_count <= requirement[0][0]:
            err = error.TestNAError
            estr = ((RATIO_AND_CYCLE_COUNT +
                     'More than %d cycles are needed to judge whether '
                     'last full charge meets battery design capacity.') %
                    (percent_full_vs_design, cycle_count, requirement[0][0]))
        elif cycle_count > requirement[-1][0]:
            err = error.TestNAError
            estr = ((
                    RATIO_AND_CYCLE_COUNT +
                    'This is more than %d cycles which means that the battery '
                    'might have degraded. Please re-run this test with a newer '
                    'battery.') %
                    (percent_full_vs_design, cycle_count, requirement[-1][0]))
        else:
            for max_cycle, percent_required in requirement:
                if cycle_count > max_cycle:
                    continue
                if percent_full_vs_design >= percent_required:
                    keyvals['battery_design_capacity_qualify'] = True
                else:
                    err = error.TestFail
                    estr = ((RATIO_AND_CYCLE_COUNT +
                             'Ratio is lower than %f%%. This battery fails '
                             'design capacity qualification.') %
                            (percent_full_vs_design, cycle_count,
                             percent_required))
                break
        self.write_perf_keyval(keyvals)
        if err:
            raise err(estr)
        # Sleep for a bit to collect logger data.
        time.sleep(SEC_SLEEP)
