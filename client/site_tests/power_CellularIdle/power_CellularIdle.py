# Lint as: python2, python3
# Copyright 2022 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
import logging
import time

from autotest_lib.client.common_lib import error
from autotest_lib.client.common_lib.cros import chrome
from autotest_lib.client.cros.networking.chrome_testing \
        import chrome_networking_test_api as cnta
from autotest_lib.client.cros.networking.chrome_testing \
        import chrome_networking_test_context as cntc
from autotest_lib.client.cros.power import power_test
from autotest_lib.client.cros.power import power_utils


class power_CellularIdle(power_test.power_Test):
    """Class for power_CellularIdle test."""
    version = 1
    before_test_cool_down_secs = 30

    def initialize(self, pdash_note='', force_discharge=True):
        """Perform necessary initialization prior to test run."""
        super(power_CellularIdle,
              self).initialize(seconds_period=10.,
                               pdash_note=pdash_note,
                               force_discharge=force_discharge)

    def _is_cellular_on(self):
        """Return whether cellular is enabled."""
        enabled_devices = self.chrome_net.get_enabled_devices()
        return self.chrome_net.CELLULAR in enabled_devices

    def _verify_connected_to_network(self):
        """Raise error if not connected to network, else do nothing."""
        networks = self.chrome_net.get_cellular_networks()
        logging.info('Networks found: %s', networks)

        for network in networks:
            if network['ConnectionState'] == 'Connected':
                logging.info('Connected to network: %s', network)
                return

        logging.info('Not connected to network.')
        raise error.TestError('Not connected to network.')

    def run_once(self, idle_time=1800):
        """Collect power stats when cellular is on or off.

        Args:
            idle_time: time in seconds to stay idle and measure power
        """

        extra_browser_args = ['--disable-sync']
        with cntc.ChromeNetworkingTestContext() as testing_context, \
             chrome.Chrome(autotest_ext=True,
                           extra_browser_args=extra_browser_args) as self.cr:
            tab = self.cr.browser.tabs.New()
            tab.Activate()
            power_utils.set_fullscreen(self.cr)

            self.start_measurements()
            start_time = time.time()
            time.sleep(self.before_test_cool_down_secs)
            self.checkpoint_measurements('cooldown', start_time)

            self.chrome_net = cnta.ChromeNetworkProvider(testing_context)

            self.chrome_net.disable_network_device(self.chrome_net.WIFI_DEVICE)
            # Ensure cellular is enabled.
            if not self._is_cellular_on():
                self.chrome_net.enable_network_device(self.chrome_net.CELLULAR)
            if not self._is_cellular_on():
                raise error.TestNAError('Failed to enable cellular.')

            self.chrome_net.scan_for_networks()
            self._verify_connected_to_network()

            power_utils.set_display_power(power_utils.DISPLAY_POWER_ALL_OFF)
            # Test system idle with cellular turned on.
            start_time = time.time()
            time.sleep(idle_time)
            self.checkpoint_measurements('cellular_on', start_time)

            # Disable cellular.
            self.chrome_net.disable_network_device(self.chrome_net.CELLULAR)
            if self._is_cellular_on():
                raise error.TestError('Failed to disable cellular.')

            power_utils.set_display_power(power_utils.DISPLAY_POWER_ALL_OFF)
            # Test system idle with cellular turned off.
            start_time = time.time()
            time.sleep(idle_time)
            self.checkpoint_measurements('cellular_off', start_time)

            # Turn on cellular and wifi before leaving the test.
            self.chrome_net.enable_network_device(self.chrome_net.CELLULAR)
            self.chrome_net.enable_network_device(self.chrome_net.WIFI_DEVICE)
            power_utils.set_display_power(power_utils.DISPLAY_POWER_ALL_ON)
