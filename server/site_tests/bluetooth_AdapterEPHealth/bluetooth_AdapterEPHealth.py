# Copyright 2021 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""A Batch of of Bluetooth enterprise policy health tests"""

from __future__ import absolute_import

import time

from autotest_lib.client.common_lib import error
from autotest_lib.client.cros.bluetooth.bluetooth_audio_test_data import A2DP
from autotest_lib.server.cros.bluetooth.bluetooth_adapter_quick_tests import (
        BluetoothAdapterQuickTests)
from autotest_lib.server.cros.bluetooth.bluetooth_adapter_audio_tests import (
        BluetoothAdapterAudioTests)
from autotest_lib.server.cros.bluetooth.bluetooth_adapter_hidreports_tests \
        import BluetoothAdapterHIDReportTests

from autotest_lib.server.cros.bluetooth.bluetooth_test_utils import (
        BluetoothPolicy)

class bluetooth_AdapterEPHealth(BluetoothAdapterQuickTests,
                                BluetoothAdapterAudioTests,
                                BluetoothAdapterHIDReportTests):
    """A Batch of Bluetooth enterprise policy health tests."""

    # A delay for disconnection to finish.
    DISCONNECT_SLEEP_SECS = 2

    # With raspberry pi peer, it takes a moment before the device is
    # registered as an input device. Without delay, the input recorder
    # doesn't find the device
    CONNECT_SLEEP_SECS = 1

    test_wrapper = BluetoothAdapterQuickTests.quick_test_test_decorator
    batch_wrapper = BluetoothAdapterQuickTests.quick_test_batch_decorator


    def get_device_verifier(self, device):
        """Helper function to get a proper test method for verifying device
           avalibility depending on its type

        @param device: a peer device
        @returns: a test method if the device type can be recongnized,
                  None otherwise.
        """
        if device.device_type == 'KEYBOARD':
            return self.run_keyboard_tests
        elif device.device_type == 'BLUETOOTH_AUDIO':
            return lambda device: self.test_a2dp_sinewaves(device, A2DP, 0)
        else:
            raise error.TestError('Failed to find verifier for device type %s' %
                                  device.device_type)


    def ep_outgoing_connection(self, device, expected_pass):
        """Run outoging connection tests

        @param device: the peer device
        @param expected_pass: True if the test is expected to pass
        """
        self.test_discover_device(device.address)
        time.sleep(self.TEST_SLEEP_SECS)

        self.test_pairing(device.address, device.pin, trusted=True)
        time.sleep(self.CONNECT_SLEEP_SECS)

        self.check_if_blocked_by_policy(device, not expected_pass)

        verifier = self.get_device_verifier(device)

        # Whether the test should pass or fail depends on expected_pass.
        self.expect_test(expected_pass, verifier, device)


    def ep_incoming_connection(self, device, expected_pass):
        """Run incoming connection tests

        @param device: the peer device
        @param expected_pass: True if the test is expected to pass
        """
        self.test_discover_device(device.address)
        time.sleep(self.TEST_SLEEP_SECS)

        self.test_pairing(device.address, device.pin, trusted=True)
        time.sleep(self.CONNECT_SLEEP_SECS)

        self.test_disconnection_by_device(device)
        time.sleep(self.DISCONNECT_SLEEP_SECS)

        if expected_pass:
            self.test_connection_by_device(device)
        else:
            # ignore the result of connection by device since bluez could
            # disconnect the device connection if there is no service
            # available
            adapter_address = self.bluetooth_facade.address
            device.ConnectToRemoteAddress(adapter_address)
        time.sleep(self.CONNECT_SLEEP_SECS)

        self.check_if_blocked_by_policy(device, not expected_pass)

        verifier = self.get_device_verifier(device)

        # Whether the test should pass or fail depends on expected_pass.
        self.expect_test(expected_pass, verifier, device)


    def ep_auto_reconnection(self, device, expected_pass):
        """Run auto reconnection tests

        @param device: the peer device
        @param expected_pass: True if the test is expected to pass
        """
        self.test_discover_device(device.address)
        time.sleep(self.TEST_SLEEP_SECS)

        self.test_pairing(device.address, device.pin, trusted=True)
        time.sleep(self.CONNECT_SLEEP_SECS)

        device.AdapterPowerOff()
        time.sleep(self.TEST_SLEEP_SECS)
        # device should be connected after power on
        device.AdapterPowerOn()

        self.check_if_blocked_by_policy(device, not expected_pass)

        verifier = self.get_device_verifier(device)

        self.expect_test(expected_pass, verifier, device)


    def reset_allowlist_and_raise_fail(self, err_msg):
        """Reset the allowlist and raise TestFail.

        @param err_msg: the error message
        """
        self.test_reset_allowlist()
        raise error.TestFail(err_msg)


    def run_test_method(self, ep_test_method, device, uuids='',
                        expected_pass=True):
        """Run a specified ep_test_method.

        @param ep_test_method: the test method to run
        @param device: a peer device
        @param uuids: the uuids in the allowlist to set.
                If uuids is None, it means not to set Allowlist.
                The default value is '' which means to allow all UUIDs.
        @param expected_pass: True if the ep_test_method is expected to pass.
                The default value is True.
        """
        if uuids is not None:
            self.test_check_set_allowlist(uuids, True)

        if device.device_type == 'BLUETOOTH_AUDIO':
            self.initialize_bluetooth_audio(device, A2DP)

        ep_test_method(device, expected_pass)

        if device.device_type == 'BLUETOOTH_AUDIO':
            self.cleanup_bluetooth_audio(device, A2DP)


    @test_wrapper('Set Allowlist with Different UUIDs')
    def ep_check_set_allowlist(self):
        """The Enterprise Policy set valid and invalid allowlists test."""
        # Duplicate valid UUIDs
        self.test_check_set_allowlist('abcd,0xabcd', True)

        # Mix of valid UUID16, UUID32, and UUID128
        self.test_check_set_allowlist(
                '0xabcd,abcd1234,'
                'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee', True)

        # Mix of valid UUID16, UUID32, and UUID128 with duplicate UUIUDs
        self.test_check_set_allowlist(
                'abcd,0xabcd,abcd1234,0xabcd1234,'
                'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee', True)

        # Single valid classic HID UUID
        self.test_check_set_allowlist(BluetoothPolicy.UUID_HID, True)

        # Empty allowlist
        self.test_check_set_allowlist('', True)

        # Invalid UUID should fail.
        self.test_check_set_allowlist(
                'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee-ffff', False)

        # Invalid UUID should fail.
        self.test_check_set_allowlist('aaaaaaaa-bbbb-cccc-dddd', False)


    @test_wrapper('Outgoing: HID: Service in Allowlist', devices={'KEYBOARD':1})
    def ep_outgoing_hid_service_in_allowlist(self):
        """The test with service in allowlist for outgoing connection."""
        device = self.devices['KEYBOARD'][0]
        self.run_test_method(self.ep_outgoing_connection, device,
                             uuids=BluetoothPolicy.UUID_HID, expected_pass=True)


    @test_wrapper('Outgoing: Audio: Service in Allowlist',
                  devices={'BLUETOOTH_AUDIO':1})
    def ep_outgoing_audio_services_in_allowlist(self):
        """The test with service in allowlist for outgoing connection."""
        device = self.devices['BLUETOOTH_AUDIO'][0]
        self.run_test_method(self.ep_outgoing_connection, device,
                             uuids=BluetoothPolicy.ALLOWLIST_AUDIO,
                             expected_pass=True)


    @test_wrapper('Outgoing: HID: Service not in Allowlist',
                  devices={'KEYBOARD':1})
    def ep_outgoing_hid_service_not_in_allowlist(self):
        """The test with service not in allowlist for outgoing connection."""
        device = self.devices['KEYBOARD'][0]
        self.run_test_method(self.ep_outgoing_connection, device,
                             uuids='0xaabb', expected_pass=False)


    @test_wrapper('Outgoing: Audio: Service not in Allowlist',
                  devices={'BLUETOOTH_AUDIO':1})
    def ep_outgoing_audio_services_not_in_allowlist(self):
        """The test with service not in allowlist for outgoing connection."""
        device = self.devices['BLUETOOTH_AUDIO'][0]
        self.run_test_method(self.ep_outgoing_connection, device,
                             uuids=BluetoothPolicy.ALLOWLIST_AUDIO_INCOMPLETE,
                             expected_pass=False)


    @test_wrapper('Outgoing: HID: Empty Allowlist',
                  devices={'KEYBOARD':1})
    def ep_outgoing_hid_empty_allowlist(self):
        """The test with an empty allowlist for outgoing connection."""
        device = self.devices['KEYBOARD'][0]
        self.run_test_method(self.ep_outgoing_connection, device,
                             uuids='', expected_pass=True)


    @test_wrapper('Outgoing: Audio: Empty Allowlist',
                  devices={'BLUETOOTH_AUDIO':1})
    def ep_outgoing_audio_empty_allowlist(self):
        """The test with an empty allowlist for outgoing connection."""
        device = self.devices['BLUETOOTH_AUDIO'][0]
        self.run_test_method(self.ep_outgoing_connection, device,
                             uuids='', expected_pass=True)


    @test_wrapper('Incoming: HID: Service in Allowlist',
                  devices={'KEYBOARD':1})
    def ep_incoming_hid_service_in_allowlist(self):
        """Service in allowlist for incoming reconnection from device."""
        device = self.devices['KEYBOARD'][0]
        self.run_test_method(self.ep_incoming_connection, device,
                             uuids=BluetoothPolicy.UUID_HID, expected_pass=True)


    @test_wrapper('Incoming: Audio: Service in Allowlist',
                  devices={'BLUETOOTH_AUDIO':1})
    def ep_incoming_audio_service_in_allowlist(self):
        """Service in allowlist for incoming reconnection from device."""
        device = self.devices['BLUETOOTH_AUDIO'][0]
        self.run_test_method(self.ep_incoming_connection, device,
                             uuids=BluetoothPolicy.ALLOWLIST_AUDIO,
                             expected_pass=True)


    @test_wrapper('Incoming: HID: Service not in Allowlist',
                  devices={'KEYBOARD':1})
    def ep_incoming_hid_service_not_in_allowlist(self):
        """Service not in allowlist for incoming reconnection from device."""
        device = self.devices['KEYBOARD'][0]
        self.run_test_method(self.ep_incoming_connection, device,
                             uuids='0xaabb', expected_pass=False)


    @test_wrapper('Incoming: Audio: Service not in Allowlist',
                  devices={'BLUETOOTH_AUDIO':1})
    def ep_incoming_audio_service_not_in_allowlist(self):
        """Service not in allowlist for incoming reconnection from device."""
        device = self.devices['BLUETOOTH_AUDIO'][0]
        self.run_test_method(self.ep_incoming_connection, device,
                             uuids=BluetoothPolicy.ALLOWLIST_AUDIO_INCOMPLETE,
                             expected_pass=False)


    @test_wrapper('Incoming: HID: Service empty Allowlist',
                  devices={'KEYBOARD':1})
    def ep_incoming_hid_service_empty_allowlist(self):
        """The test with an empty allowlist for incoming connection."""
        device = self.devices['KEYBOARD'][0]
        self.run_test_method(self.ep_incoming_connection, device,
                             uuids='',
                             expected_pass=True)


    @test_wrapper('Incoming: Audio: Service empty Allowlist',
                  devices={'BLUETOOTH_AUDIO':1})
    def ep_incoming_audio_service_empty_allowlist(self):
        """The test with an empty allowlist for incoming connection."""
        device = self.devices['BLUETOOTH_AUDIO'][0]
        self.run_test_method(self.ep_incoming_connection, device,
                             uuids='',
                             expected_pass=True)


    @test_wrapper('Outgoing: BLE Keyboard: Services in Allowlist',
                  devices={'BLE_KEYBOARD':1})
    def ep_outgoing_ble_hid_services_in_allowlist(self):
        """The test for BLE gatt services in allowlist."""
        device = self.devices['BLE_KEYBOARD'][0]
        self.run_test_method(self.ep_outgoing_connection, device,
                             uuids=BluetoothPolicy.ALLOWLIST_BLE_HID,
                             expected_pass=True)


    @test_wrapper('Outgoing: BLE Keyboard: Services not in Allowlist',
                  devices={'BLE_KEYBOARD':1})
    def ep_outgoing_ble_hid_services_not_in_allowlist(self):
        """The test for BLE gatt services not in allowlist."""
        device = self.devices['BLE_KEYBOARD'][0]
        self.run_test_method(self.ep_outgoing_connection, device,
                             uuids=BluetoothPolicy.ALLOWLIST_BLE_HID_INCOMPLETE,
                             expected_pass=False)


    @test_wrapper('Outgoing: BLE Keyboard: Empty Allowlist',
                  devices={'BLE_KEYBOARD':1})
    def ep_outgoing_ble_hid_empty_allowlist(self):
        """The test for BLE gatt services and an empty allowlist."""
        device = self.devices['BLE_KEYBOARD'][0]
        self.run_test_method(self.ep_outgoing_connection, device,
                             uuids='', expected_pass=True)


    @test_wrapper('Reconnection: BLE Keyboard: Service in Allowlist',
                  devices={'BLE_KEYBOARD':1})
    def ep_reconnection_ble_hid_service_in_allowlist(self):
        """Service in allowlist for auto reconnection from device."""
        device = self.devices['BLE_KEYBOARD'][0]
        self.run_test_method(self.ep_auto_reconnection, device,
                             uuids=BluetoothPolicy.ALLOWLIST_BLE_HID,
                             expected_pass=True)


    @test_wrapper('Reconnection: BLE Keyboard: Service not in Allowlist',
                  devices={'BLE_KEYBOARD':1})
    def ep_reconnection_ble_hid_service_not_in_allowlist(self):
        """Service in allowlist for auto reconnection from device."""
        device = self.devices['BLE_KEYBOARD'][0]
        self.run_test_method(self.ep_auto_reconnection, device,
                             uuids=BluetoothPolicy.ALLOWLIST_BLE_HID_INCOMPLETE,
                             expected_pass=False)


    @test_wrapper('Combo: Set Allowlist and Disconnect', devices={'KEYBOARD':1})
    def ep_combo_set_allowlist_and_disconnect(self):
        """Set a new allowlist and current connection should be terminated."""
        device = self.devices['KEYBOARD'][0]
        self.run_test_method(self.ep_outgoing_connection, device,
                             uuids=BluetoothPolicy.UUID_HID, expected_pass=True)

        # Setting a non-HID UUID should disconnect the device.
        self.test_check_set_allowlist('abcd', True)
        time.sleep(self.DISCONNECT_SLEEP_SECS)
        self.test_device_is_not_connected(device.address)


    @test_wrapper('Combo: Successive Allowlist', devices={'KEYBOARD':1})
    def ep_combo_successive_allowlists(self):
        """A new allowlist overwrites previoius one and allows connection."""
        device = self.devices['KEYBOARD'][0]

        # Setting a non-HID UUID initially.
        self.test_check_set_allowlist('abcd', True)

        # A subsequent HID UUID should supersede the previous setting.
        self.run_test_method(self.ep_outgoing_connection, device,
                             uuids=BluetoothPolicy.UUID_HID, expected_pass=True)


    @test_wrapper('Combo: HID Allowlist Persists Adapter Reset',
                  devices={'KEYBOARD':1})
    def ep_combo_hid_persists_adapter_reset(self):
        """The Allowlist with HID UUID should persist adapter reset."""
        device = self.devices['KEYBOARD'][0]
        self.test_check_set_allowlist(BluetoothPolicy.UUID_HID, True)
        self.test_reset_on_adapter()
        self.run_test_method(self.ep_outgoing_connection, device,
                             uuids=None, expected_pass=True)


    @test_wrapper('Combo: Non-HID Allowlist Persists Adapter Reset',
                  devices={'KEYBOARD':1})
    def ep_combo_non_hid_persists_adapter_reset(self):
        """The Allowlist with non-HID UUID should persist adapter reset."""
        device = self.devices['KEYBOARD'][0]
        self.test_check_set_allowlist('abcd', True)
        self.test_reset_on_adapter()
        self.run_test_method(self.ep_outgoing_connection, device,
                             uuids=None, expected_pass=False)


    @test_wrapper('Combo: HID Allowlist Persists bluetoothd restart',
                  devices={'KEYBOARD':1})
    def ep_combo_hid_persists_bluetoothd_restart(self):
        """The Allowlist with HID UUID should persist bluetoothd restart."""
        device = self.devices['KEYBOARD'][0]
        self.test_check_set_allowlist(BluetoothPolicy.UUID_HID, True)
        self.test_stop_bluetoothd()
        self.test_start_bluetoothd()
        self.run_test_method(self.ep_outgoing_connection, device,
                             uuids=None, expected_pass=True)


    @test_wrapper('Combo: Non-HID Allowlist Persists bluetoothd restart',
                  devices={'KEYBOARD':1})
    def ep_combo_non_hid_persists_bluetoothd_restart(self):
        """The Allowlist with non-HID UUID should persist bluetoothd restart."""
        device = self.devices['KEYBOARD'][0]
        self.test_check_set_allowlist('abcd', True)
        self.test_stop_bluetoothd()
        self.test_start_bluetoothd()
        self.run_test_method(self.ep_outgoing_connection, device,
                             uuids=None, expected_pass=False)


    @test_wrapper('Combo: HID Allowlist Persists reboot',
                  devices={'KEYBOARD':1})
    def ep_combo_hid_persists_reboot(self):
        """The Allowlist with HID UUID should persist reboot."""
        device = self.devices['KEYBOARD'][0]
        self.test_check_set_allowlist(BluetoothPolicy.UUID_HID, True)
        self.reboot()
        self.run_test_method(self.ep_outgoing_connection, device,
                             uuids=None, expected_pass=True)


    @test_wrapper('Combo: Non-HID Allowlist Persists reboot',
                  devices={'KEYBOARD':1})
    def ep_combo_non_hid_persists_reboot(self):
        """The Allowlist with non-HID UUID should persist reboot."""
        device = self.devices['KEYBOARD'][0]
        self.test_check_set_allowlist('aaaa', True)
        self.reboot()
        self.run_test_method(self.ep_outgoing_connection, device,
                             uuids=None, expected_pass=False)


    @batch_wrapper('EP Health')
    def ep_health_batch_run(self, num_iterations=1, test_name=None):
        """Run the EP health test batch or a specific given test.

        @param num_iterations: how many iterations to run
        @param test_name: specific test to run otherwise None to run the
                whole batch
        """

        self.ep_check_set_allowlist()

        self.ep_outgoing_hid_service_in_allowlist()
        self.ep_outgoing_hid_service_not_in_allowlist()
        self.ep_outgoing_hid_empty_allowlist()

        self.ep_outgoing_ble_hid_services_in_allowlist()
        self.ep_outgoing_ble_hid_services_not_in_allowlist()
        self.ep_outgoing_ble_hid_empty_allowlist()

        self.ep_incoming_hid_service_in_allowlist()
        self.ep_incoming_hid_service_not_in_allowlist()
        self.ep_incoming_hid_service_empty_allowlist()

        self.ep_outgoing_audio_services_in_allowlist()
        self.ep_outgoing_audio_services_not_in_allowlist()
        self.ep_outgoing_audio_empty_allowlist()

        self.ep_incoming_audio_service_in_allowlist()
        self.ep_incoming_audio_service_not_in_allowlist()
        self.ep_incoming_audio_service_empty_allowlist()

        self.ep_reconnection_ble_hid_service_in_allowlist()
        self.ep_reconnection_ble_hid_service_not_in_allowlist()

        self.ep_combo_set_allowlist_and_disconnect()
        self.ep_combo_successive_allowlists()
        self.ep_combo_hid_persists_adapter_reset()
        self.ep_combo_non_hid_persists_adapter_reset()
        self.ep_combo_hid_persists_bluetoothd_restart()
        self.ep_combo_non_hid_persists_bluetoothd_restart()
        self.ep_combo_hid_persists_reboot()
        self.ep_combo_non_hid_persists_reboot()


    def run_once(self,
                 host,
                 num_iterations=1,
                 args_dict=None,
                 test_name=None,
                 flag='Quick Health'):
        """Run the batch of Bluetooth enterprise policy health tests

        @param host: the DUT, usually a chromebook
        @param num_iterations: the number of rounds to execute the test
        @param test_name: the test to run, or None for all tests
        """

        # Initialize and run the test batch or the requested specific test
        self.quick_test_init(host,
                             use_btpeer=True,
                             flag=flag,
                             args_dict=args_dict)
        self.ep_health_batch_run(num_iterations, test_name)
        self.quick_test_cleanup()
