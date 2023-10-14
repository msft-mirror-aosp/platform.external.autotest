# Lint as: python3
# Copyright 2023 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Server side test that controls charging the DUT with Servo v4."""

from autotest_lib.client.common_lib import error
from autotest_lib.client.common_lib.cros import force_discharge_utils
from autotest_lib.server import autotest
from autotest_lib.server import test

# Expect that most discharges we expect to see can happen within 4 hours.
_DEFAULT_TIMEOUT = 4 * 60 * 60


class power_BatteryDrainControl(test.test):
    """Server side test that controls draining the DUT battery.

    This server side test acts as a wrapper around the client side test,
    power_BatteryDrain. It is primarily used by other tests to ensure that a
    specific charge is reach. This test only uses force discharge instead of
    relying on servo.
    """
    version = 1

    def run_once(self, host, drain_to_percent, drain_timeout=_DEFAULT_TIMEOUT):
        """Running the test.

        @param host: CrosHost object representing the DUT.
        @param drain_to_percent: percentage of the charge capacity charge
                to drain to.
        @param drain_timeout: max duration in seconds to discharge for.
        """
        autotest_client = autotest.Autotest(host)
        try:
            autotest_client.run_test('power_BatteryDrain',
                                     drain_to_percent=drain_to_percent,
                                     drain_timeout=drain_timeout,
                                     force_discharge=True)
        finally:
            try:
                # Ensure that force discharge is turned off
                force_discharge_utils.charge_control_by_ectool(True, host=host)
            except:
                raise error.TestNAError(
                        "Skip test: Force discharge not supported")
