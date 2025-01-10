# Lint as: python2, python3
# Copyright 2014 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from autotest_lib.client.common_lib import error
from autotest_lib.server import autotest, test

class power_BrightnessResetAfterReboot(test.test):
    """Verifies that the panel brightness level resets after device reboots.
    """
    version = 2

    def run_once(self, host, client_autotest):
        """This test verifies that the panel brightness level resets after
           device reboots.
        """
        if host.has_internal_display() is None:
            raise error.TestNAError('Device has no internal display.')
        autotest_client = autotest.Autotest(host)
        host.reboot()
        # Disable powerd to ensure ALS doesn't affect brightness during testing.
        # See b/378347551 for for additional details.
        disable_powerd(host)
        autotest_client.run_test(client_autotest, exit_without_logout=True)

        initial_brightness = get_backlight(host)
        if (initial_brightness < 10.0 or initial_brightness > 90.0):
            raise error.TestFail('Default brightness level is out of scope '
                                 '(10.0%% - 90.0%%): %f' % initial_brightness)

        brightness_min = 0.0
        if (not set_backlight(host, brightness_min) or
                get_backlight(host) != brightness_min):
            raise error.TestFail('Unable to change the brightness to minimum '
                                 '(%f%%) level.' % brightness_min)

        brightness_max = 100.0
        if (not set_backlight(host, brightness_max) or
                get_backlight(host) != brightness_max):
            raise error.TestFail('Unable to change the brightness to maximum '
                                 '(%f%%) level.' % brightness_max)

        host.reboot()
        # Disable powerd to ensure ALS doesn't affect brightness during testing.
        disable_powerd(host)
        autotest_client.run_test(client_autotest, exit_without_logout=True)
        brightness_after_reboot = get_backlight(host)
        if not initial_brightness == brightness_after_reboot:
            raise error.TestFail(
                    'Unable to reset internal display brightness back '
                    'to default after reboot.\n'
                    'Previous boot default brightness: %f\n'
                    'Current boot default brightness: %f' %
                    (initial_brightness, brightness_after_reboot))

    def cleanup(self, host):
        """Cleanup the test"""
        host.run('start powerd')

def set_backlight(host, percentage):
    """Executes backlight_tool to set internal display backlight.
       @param host: host object representing the DUT.
       @param percentage: linear percentage to set internal display
                          backlight to.
    """
    cmd = 'backlight_tool --set_brightness_percent=%f' % percentage
    try:
        exit_status = host.run(cmd).exit_status
    except error.CmdError:
        raise error.TestFail(cmd)
    return not exit_status # 0 is cmd success.


def get_backlight(host):
    """Executes backlight_tool to get internal display backlight.
       @param host: host object representing the DUT.
    """
    cmd = 'backlight_tool --get_brightness_percent'
    try:
        result = host.run_output(cmd)
    except error.CmdError:
        raise error.TestFail(cmd)
    return float(result)


def disable_powerd(host):
    """disable powerd"""
    cmd = 'stop powerd'
    try:
        host.run(cmd)
    except error.CmdError:
        raise error.TestFail(cmd)