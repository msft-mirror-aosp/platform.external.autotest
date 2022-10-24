# Lint as: python3
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
  version = 2
  _before_test_cool_down_sec = 30
  _cellular_on_off_time_sec = 1800
  _measurement_tag_cool_down = 'cool_down'
  _measurement_tag_cellular_on = 'cellular_on'
  _measurement_tag_cellular_off = 'cellular_off'
  _modem_on_power_high_threshold = 0.4  # unit is "W"
  _modem_on_power_low_threshold = 0.005  # unit is "W"

  def initialize(self, pdash_note='', force_discharge=True):
    """Perform necessary initialization prior to test run."""
    super(power_CellularIdle, self).initialize(
        seconds_period=10.,
        pdash_note=pdash_note,
        force_discharge=force_discharge)

  def _is_cellular_on(self):
    """Return whether cellular is enabled."""
    enabled_devices = self.chrome_net.get_enabled_devices()
    return self.chrome_net.CELLULAR in enabled_devices

  def _verify_connected_to_network(self):
    """Raise TestNAError if not connected to network, else do nothing."""
    networks = self.chrome_net.get_cellular_networks()
    logging.info('Networks found: %s', networks)

    for network in networks:
      if network['ConnectionState'] == 'Connected':
        logging.info('Connected to network: %s', network)
        return

    logging.info('Not connected to network.')
    raise error.TestNAError('Not connected to network.')

  def postprocess_iteration(self):
    """<Modem ON power> - <Modem LOW power>"""
    cellular_on_power = None
    cellular_off_power = None
    cellular_on_power_key = self._measurement_tag_cellular_on + '_system_pwr_avg'
    cellular_off_power_key = self._measurement_tag_cellular_off + '_system_pwr_avg'

    super(power_CellularIdle, self).postprocess_iteration()
    if cellular_on_power_key in self.keyvals:
      cellular_on_power = self.keyvals[cellular_on_power_key]
      logging.info('cellular_on_power: %f', cellular_on_power)
    else:
      logging.info('cellular_on_power: None')

    if cellular_off_power_key in self.keyvals:
      cellular_off_power = self.keyvals[cellular_off_power_key]
      logging.info('cellular_off_power: %f', cellular_off_power)
    else:
      logging.info('cellular_off_power: None')

    if cellular_on_power and cellular_off_power:
      modem_on_power = cellular_on_power - cellular_off_power
      self.output_perf_value(
          description='modem_on_pwr_avg',
          value=modem_on_power,
          units='W',
          higher_is_better=False)
      if modem_on_power > self._modem_on_power_high_threshold:
        raise error.TestError('Modem on power is too high: %f > %f (W)',
                              modem_on_power,
                              self._modem_on_power_high_threshold)
      elif modem_on_power < self._modem_on_power_low_threshold:
        raise error.TestError('Modem on power is too low: %f < %f (W)',
                              modem_on_power,
                              self._modem_on_power_low_threshold)

  def run_once(self):
    """Collect power stats when cellular is on or off"""
    run_time = self._cellular_on_off_time_sec
    logging.info('cellular on/off run_time(s): %d', run_time)
    extra_browser_args = ['--disable-sync']
    with cntc.ChromeNetworkingTestContext() as testing_context, \
         chrome.Chrome(autotest_ext=True,
                       extra_browser_args=extra_browser_args) as self.cr:
      tab = self.cr.browser.tabs.New()
      tab.Activate()
      power_utils.set_fullscreen(self.cr)

      self.start_measurements()
      start_time = time.time()
      time.sleep(self._before_test_cool_down_sec)
      self.checkpoint_measurements(self._measurement_tag_cool_down, start_time)

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
      logging.info('Start cellular on test for %d seconds', run_time)
      # Test system idle with cellular turned on.
      start_time = time.time()
      time.sleep(run_time)
      self.checkpoint_measurements(self._measurement_tag_cellular_on,
                                   start_time)

      # Disable cellular.
      self.chrome_net.disable_network_device(self.chrome_net.CELLULAR)
      if self._is_cellular_on():
        raise error.TestNAError('Failed to disable cellular.')

      power_utils.set_display_power(power_utils.DISPLAY_POWER_ALL_OFF)
      logging.info('Start cellular off test for %d seconds', run_time)
      # Test system idle with cellular turned off.
      start_time = time.time()
      time.sleep(run_time)
      self.checkpoint_measurements(self._measurement_tag_cellular_off,
                                   start_time)

      # Turn on cellular and wifi before leaving the test.
      self.chrome_net.enable_network_device(self.chrome_net.CELLULAR)
      self.chrome_net.enable_network_device(self.chrome_net.WIFI_DEVICE)
      power_utils.set_display_power(power_utils.DISPLAY_POWER_ALL_ON)
