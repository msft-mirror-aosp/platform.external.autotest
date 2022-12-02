# Copyright 2019 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Power utils for server tests."""

import logging
import re
import time
from xml.parsers import expat

from autotest_lib.client.common_lib import error
from autotest_lib.server import autotest
from autotest_lib.server.cros.power import servo_charger
import six


def put_host_battery_in_range(host, min_level, max_level, timeout):
    """
    Charges or drains the host's battery to the specified range within the
    timeout. This uses a servo v4 and either the power_BatteryCharge or the
    power_BatteryDrain client test.

    @param host: DUT to use
    @param min_level: battery percentage
    @param max_level: battery percentage
    @param timeout: in seconds

    @throws: A TestFail error if getting the current battery level, setting the
             servo's charge state, or running either of the client tests fails.
    """
    current_level = host.get_battery_display_percentage()
    if current_level >= min_level and current_level <= max_level:
        return

    autotest_client = autotest.Autotest(host)
    charge_manager = servo_charger.ServoV4ChargeManager(host, host.servo)
    if current_level < min_level:
        charge_manager.start_charging()
        autotest_client.run_test('power_BatteryCharge',
                                 max_run_time=timeout,
                                 percent_target_charge=min_level,
                                 use_design_charge_capacity=False)
    if current_level > max_level:
        charge_manager.stop_charging()
        autotest_client.run_test('power_BatteryDrain',
                                 drain_to_percent=max_level,
                                 drain_timeout=timeout)


def get_power_state(ec):
    """
    Return the current power state of the AP (via EC 'powerinfo' command)

    @return the name of the power state, or None if a problem occurred
    """
    pattern = r'power state (\w+) = (\w+),'

    try:
        match = ec.send_command_get_output("powerinfo", [pattern],
                                           retries=3)
    except (error.TestFail, expat.ExpatError) as err:
        logging.warning("powerinfo command encountered an error: %s", err)
        return None
    if not match:
        logging.warning("powerinfo output did not match pattern: %r",
                        pattern)
        return None
    (line, state_num, state_name) = match[0]
    logging.debug("power state info %r", match)
    return state_name


def _check_power_state(expected_power_state, actual_power_state):
    """
    Check for correct power state of the AP (via EC 'powerinfo' command)

    @param expected_power_state: full-string regex of power state you are
    expecting
    @param actual_power_state: the power state returned from get_power_state
    @return: the line and the match, if the output matched.
    @raise error.TestFail: if output didn't match after the delay.
    """
    if not isinstance(expected_power_state, six.string_types):
        raise error.TestError('%s is not a string while it should be.' %
                              expected_power_state)
    if not isinstance(actual_power_state, six.string_types):
        raise error.TestError('%s is not a string while it should be.' %
                              actual_power_state)
    if re.match('^' + expected_power_state + '$', actual_power_state):
        return True
    return False


def wait_power_state(ec, power_state, retries, retry_delay=3):
    """
    Wait for certain power state.

    @param power_state: full-string regex of power state you are expecting
    @param retries: retries.  This is necessary if AP is powering down
    and transitioning through different states.
    @param retry_delay: delay between retries in seconds
    """
    logging.info('Checking power state "%s" maximum %d times.',
                 power_state, retries)

    last_power_state = ''
    while retries > 0:
        logging.debug("try count: %d", retries)
        start_time = time.time()
        try:
            retries = retries - 1
            actual_power_state = get_power_state(ec)
            if last_power_state != actual_power_state:
                logging.info("power state: %s", actual_power_state)
            if actual_power_state is None:
                continue
            if _check_power_state(power_state, actual_power_state):
                return True
            last_power_state = actual_power_state
        except (error.TestFail, expat.ExpatError):
            pass
        delay_time = retry_delay - time.time() + start_time
        if delay_time > 0:
            time.sleep(delay_time)
    return False
