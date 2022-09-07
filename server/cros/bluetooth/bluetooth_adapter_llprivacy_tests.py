# Lint as: python2, python3
# Copyright 2022 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Server side bluetooth tests on LL Privacy"""

from autotest_lib.server.cros.bluetooth import bluetooth_adapter_tests

import logging

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
        """Enable LE advertising, check random address is generated"""
        device.SetDiscoverable(True)  # no return value
        advertising = device.SetAdvertising(True)
        after_address = device.GetRandomAddress()
        self.results = {
                'set_advertising': advertising,
                'not_bdaddr_any': after_address != "00:00:00:00:00:00",
                'not_public': after_address != device.address
        }
        device.rpa = after_address
        return all(self.results.values())

    @test_retry_and_log(True)
    def test_stop_device_advertise_with_rpa(self, device):
        """Stop LE advertising, remove RPA from device"""
        advertising = device.SetAdvertising(False)
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
        add_dev_to_resolv_list = self.bluetooth_facade.btmon_find(
                'LE Add Device To Resolving List')
        use_accept_list = self.bluetooth_facade.btmon_find(
                'Filter policy: Ignore not in accept list (0x01)')

        self.results = {
                'enable_address_resolution': enable_address_resolution,
                'add_device_to_resolving_list': add_dev_to_resolv_list,
                'use_accept_list': use_accept_list
        }
        return all(self.results.values())

    @test_retry_and_log(False)
    def test_pairing_with_rpa(self, device):
        """Expect new IRK exchange during pairing and address is resolvable

        Random address: 54:35:24:F9:18:25 (Resolvable)

        @param device: device to pair with RPA stored

        @returns: true if IRK received and address is resolvable
        """
        # Device must advertise with RPA
        device_has_rpa = hasattr(device, 'rpa') and device.rpa is not None
        self.results = {
                'device_has_rpa': device_has_rpa,
                'addr_resolvable': False
        }
        if not device_has_rpa:
            logging.error("Device has no RPA set. Start LE advertising first.")
            return False

        self._get_btmon_log(lambda: self.test_pairing(device.rpa,
                                                      device.pin,
                                                      trusted=True,
                                                      identity_address=device.
                                                      address))

        self.results['addr_resolvable'] = self.bluetooth_facade.btmon_find(
                device.rpa + ' (Resolvable)')

        return all(self.results.values())
