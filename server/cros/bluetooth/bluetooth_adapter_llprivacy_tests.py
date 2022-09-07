# Lint as: python2, python3
# Copyright 2022 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Server side bluetooth tests on LL Privacy"""

from autotest_lib.server.cros.bluetooth import bluetooth_adapter_tests

import logging
import time

DEVICE_CONNECTED_TIMEOUT = 45


class BluetoothAdapterLLPrivacyTests(
        bluetooth_adapter_tests.BluetoothAdapterTests):
    """Server side bluetooth adapter ll privacy Test.

    This class comprises a number of test cases to verify bluetooth
    LL privacy.
    """

    test_case_log = bluetooth_adapter_tests.test_case_log
    test_retry_and_log = bluetooth_adapter_tests.test_retry_and_log


    @test_retry_and_log(False)
    def test_set_device_privacy(self, device, enable):
        """Test privacy mode has been enabled."""
        return device.SetPrivacy(enable)

    @test_retry_and_log(False)
    def test_start_device_advertise_with_rpa(self, device):
        """Set discoverable, enable LE advertising, check random address is generated"""
        device.SetDiscoverable(True)
        advertising = device.SetAdvertising(True)
        after_address = device.GetRandomAddress()
        if isinstance(device.rpa, str):
            logging.debug('RPA updated: %r', device.rpa != after_address)
        self.results = {
                'set_advertising': advertising,
                'not_empty_addr': after_address != "00:00:00:00:00:00",
                'not_public': after_address != device.address,
        }
        device.rpa = after_address
        logging.info('Start device advertising with: %s', after_address)
        return all(self.results.values())

    @test_retry_and_log(False)
    def test_stop_device_advertise_with_rpa(self, device):
        """Stop LE advertising, set not discoverable, remove RPA from device"""
        logging.info('Stop device advertising with: %s', device.rpa)
        advertising = device.SetAdvertising(False)
        device.SetDiscoverable(False)
        device.rpa = None
        return advertising

    @test_retry_and_log(False)
    def test_power_cycle_with_address_resolution(self):
        """Check use resolving list. A device should be paired before running
        the power cycle.

        Steps:
        - Pair device with IRK/RPA. This step is done before this function by
          calling test_pairing_with_rpa().
        - Power off DUT
        - Power on DUT, check log

        Check the items:
        - Address resolution is enabled
        - Device is added to resolving list
        - Use policy 01 for passive scan
        """
        self.test_power_off_adapter()
        self._get_btmon_log(lambda: self.test_power_on_adapter())

        enable_address_resolution = self.bluetooth_facade.btmon_find(
                'Address resolution: Enabled')

        patterns = [
                '> HCI Event: Command Complete (0x0e)',
                'LE Add Device To Resolving List (0x08|0x0027)',
                'Status: Success (0x00)'
        ]
        add_dev_to_resolv_list = self.bluetooth_facade.btmon_find_consecutive(
                patterns)

        use_accept_list = self.bluetooth_facade.btmon_find(
                'Filter policy: Ignore not in accept list (0x01)')

        self.results = {
                'enable_address_resolution': enable_address_resolution,
                'add_device_to_resolving_list': add_dev_to_resolv_list,
                'use_accept_list': use_accept_list
        }
        return all(self.results.values())

    def auto_reconnect_loop_with_device_privacy(
            self,
            device,
            loops=1,
            check_connected_method=lambda device: True,
            disconnect_by_device=False):
        """Running a loop to verify the paired device can auto reconnect
        The device is in privacy mode.
        """
        self.test_set_device_privacy(device, True)

        # start advertising and set RPA
        self.test_start_device_advertise_with_rpa(device)
        self.test_discover_device(device.rpa)

        self.test_pairing_with_rpa(device)
        self.test_connection_by_adapter(device.init_paired_addr,
                                        device.address)

        self.test_stop_device_advertise_with_rpa(device)
        self.test_hid_device_created(device.address)
        check_connected_method(device)

        try:
            for i in range(loops):
                logging.info('iteration {} / {}'.format(i + 1, loops))
                if disconnect_by_device:
                    self.test_disconnection_by_device(device)
                else:
                    self.test_power_off_adapter()
                    self.test_power_on_adapter()
                self.test_disconnection_by_device(device)
                start_time = time.time()
                self.test_start_device_advertise_with_rpa(device)

                # Verify that the device is reconnected. Wait for the input device
                # to become available before checking the profile connection.
                self.test_device_is_connected(device.init_paired_addr,
                                              timeout=DEVICE_CONNECTED_TIMEOUT,
                                              identity_address=device.address)
                end_time = time.time()
                time_diff = end_time - start_time

                self.test_hid_device_created(device.address)
                check_connected_method(device)
                logging.info('reconnect time %s', str(time_diff))
                self.test_stop_device_advertise_with_rpa(device)
        finally:
            self.test_remove_pairing(device.init_paired_addr,
                                     identity_address=device.address)
            # Restore privacy setting
            self.test_set_device_privacy(device, False)

    @test_retry_and_log(False)
    def test_pairing_with_rpa(self, device):
        """Expect new IRK exchange during pairing and address is resolvable

        Random address: 54:35:24:F9:18:25 (Resolvable)

        @param device: device to pair with RPA stored

        @returns: true if IRK received and address is resolvable
        """
        # Device must advertise with RPA
        device_has_rpa = isinstance(device.rpa, str)
        self.results = {
                'device_has_rpa': device_has_rpa,
                'addr_resolvable': False
        }
        if not device_has_rpa:
            logging.error("Device has no RPA set. Start LE advertising first.")
            return False

        device.init_paired_addr = device.rpa
        self._get_btmon_log(lambda: self.test_pairing(device.rpa,
                                                      device.pin,
                                                      trusted=True,
                                                      identity_address=device.
                                                      address))

        self.results['addr_resolvable'] = self.bluetooth_facade.btmon_find(
                device.rpa + ' (Resolvable)')

        return all(self.results.values())

    @test_retry_and_log(False)
    def test_random_address_updated(self, device, should_update=True):
        """Check if RPA has changed for the device and update rpa in device."""
        if not isinstance(device.rpa, str):
            logging.error("RPA has not been set by start advertising.")
            return False
        old_random_address = device.rpa
        self.test_stop_device_advertise_with_rpa(device)
        self.test_start_device_advertise_with_rpa(device)
        self.results = {
                'old_rpa': old_random_address,
                'new_rpa': device.rpa,
        }
        updated = old_random_address != device.rpa
        return should_update == updated

    @test_retry_and_log(False)
    def test_update_rpa_timeout(self, device, test_timeout):
        """Test RPA timeout has been changed to test value."""
        if test_timeout < 30 or test_timeout > 3600:
            logging.error('RPA timeout must be in range [30, 3600]')
            return False

        self.results = {'test_timeout': test_timeout}
        old_timeout = device.GetRPATimeout()
        device.SetRPATimeout(test_timeout)
        new_timeout = device.GetRPATimeout()
        self.results['old_timeout'] = old_timeout
        self.results['new_timeout'] = new_timeout
        return new_timeout == test_timeout
