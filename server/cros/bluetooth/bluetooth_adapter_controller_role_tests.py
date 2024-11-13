# Lint as: python2, python3
# Copyright 2020 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Bluetooth tests to check controller role support

In preparation for Nearby features, we need to verify that our device
controllers support the LE connection roles that we will require
"""

from __future__ import absolute_import

import logging
import threading
import time

import common
from autotest_lib.client.common_lib import error
from autotest_lib.server.cros.bluetooth import advertisements_data
from autotest_lib.server.cros.bluetooth import bluetooth_adapter_tests

DEFAULT_MIN_ADV_INTERVAL = 200
DEFAULT_MAX_ADV_INTERVAL = 500

# Some chipsets have IOP issue with the incoming LE connection from RasPi.
# See b/364766107 b/332475530 b/375322353
LE_RECEIVER_FLOSS_IOP_ISSUE_CHIPSETS = [
        'MVL-8897', 'Intel-AX200', 'Intel-AX201', 'Intel-AX211', 'Intel-BE200'
]

class bluetooth_AdapterControllerRoleTests(
        bluetooth_adapter_tests.BluetoothAdapterTests):
    """Bluetooth controller role tests.

    This class comprises a number of test cases to verify our controllers
    support the minimum requirements for LE connection states.
    """

    def check_le_receiver_floss_iop_issue_chipsets(self):
        """Checks if we should skip the chipset due to IOP issue on le_role"""
        if self.floss and self.bluetooth_facade.get_chipset_name(
        ) in LE_RECEIVER_FLOSS_IOP_ISSUE_CHIPSETS:
            raise error.TestNAError(
                    "Test not supported in Floss due to IOP issue")

    def pair_adapter_to_device(self, device):
        """Pairs to device, then disconnects

        For our Nearby tests, we use a peer emulating a HID device to act as
        the Nearby device. Since HID profile requires bonding for connection to
        occur, this function exchanges the bonding information as a test
        prerequisite so the Nearby device can later connected

        @param device: handle to peripheral object
        """

        self.test_discover_device(device.address)
        time.sleep(self.TEST_SLEEP_SECS)
        self.test_pairing(device.address, device.pin, trusted=False)

        # DUT could reconnect to the peer right after the disconnection below
        # if peer keeps advertising. Disable it first.
        self.test_device_set_discoverable(device, False)

        # Disconnect from different sides depending on the stack.
        # This prevents the unexpected reconnection issue of BlueZ,
        # and the failing to send traffic issue of Floss.
        # See b/280534346 for more detail.
        if self.floss:
            self.test_disconnection_by_device(device)
        else:
            self.test_disconnection_by_adapter(device.address)


    def connect_and_test_secondary_device(self, device, secondary_test_func):
        """Creates connection to a secondary device and tests it

        @param device: handle to peripheral object
        @param secondary_test_func: function handle to test connection
        """
        logging.info('Setting up secondary device')
        if not self.test_discover_device(device.address):
            logging.error('connect_and_test_secondary_device exits early as '
                          'test_discover_device fails')
            return
        if not self.test_pairing(device.address, device.pin, trusted=False):
            logging.error('connect_and_test_secondary_device exits early as '
                          'test_pairing fails')
            return
        time.sleep(self.TEST_SLEEP_SECS)
        if not self.test_connection_by_adapter(device.address):
            logging.error('connect_and_test_secondary_device exits early as '
                          'test_connection_by_adapter fails')
            return
        time.sleep(self.TEST_SLEEP_SECS)
        secondary_test_func(device)


    def _receiver_discovery_async(self, device):
        """Asynchronously discovers and begins advertising from peer

        We want to verify that the DUT is scanning and advertising at the same
        time. This function returns a thread that waits, discovers the desired
        device, and then starts advertising back to emulate a Nearby Receiver
        device.

        @param device: handle to peripheral object

        @returns threading.Thread object with receiver discovery task
        """

        def _action_receiver_discovery():
            time.sleep(3)
            self.test_discover_by_device(device)
            self.test_device_set_discoverable(device, True)

        thread = threading.Thread(target=_action_receiver_discovery)
        return thread

    # ---------------------------------------------------------------
    # Definitions of controller readiness tests
    # ---------------------------------------------------------------

    ### General test for controller in secondary role
    def controller_secondary_role_test(self, primary_device, primary_test_func,
                                       secondary_info=None):
        """Advertise from DUT and verify we can handle connection as secondary

        Optional secondary device arguments allows us to try test with existing
        connection, or to establish new secondary connection during test

        @param primary_device: primary device of connection test
        @param primary_test_func: function to test connection to primary
        @param secondary_info: Optional tuple with structure
            (secondary_device_handle, secondary_test_func, use):
            secondary_device_handle: peer device to test with
            secondary_test_func: function handle to run connection test
            device_use: 'pre' - device should be connected before test runs - or
                        'mid' - device should be connected during test
        """

        #
        # Due to crbug/946835, some messages does not reach btmon
        # causing our tests to fails. This is seen on kernel 3.18 and lower.
        # Remove this check when the issue is fixed
        # TODO(crbug/946835)
        #
        self.is_supported_kernel_version(self.host.get_kernel_version(),
                                         '3.19',
                                         'Test cannnot proceed on this'
                                         'kernel due to crbug/946835 ')

        if secondary_info is not None:
            (secondary_device_handle, secondary_test_func,
                    device_use) = secondary_info

        # Start fresh, remove DUT from peer's known devices
        primary_device.RemoveDevice(self.bluetooth_facade.address)

        # Pair the primary device first - necessary for later connection to
        # secondary device
        self.pair_adapter_to_device(primary_device)

        # If test requires it, connect and test secondary device
        if secondary_info is not None and device_use == 'pre':
            self.connect_and_test_secondary_device(
                secondary_device_handle, secondary_test_func)

        # Register and start advertising instance
        # We ignore failure because the test isn't able to verify the min/max
        # advertising intervals, but this is ok.
        self.test_reset_advertising()
        # Floss does not support set advertising intervals.
        if not self.floss:
            self.test_set_advertising_intervals(DEFAULT_MIN_ADV_INTERVAL,
                                                DEFAULT_MAX_ADV_INTERVAL)
        self.test_register_advertisement(
                advertisements_data.gen_advertisements(0, floss=self.floss), 1)

        # Discover DUT from peer
        self.test_discover_by_device(primary_device)
        time.sleep(self.TEST_SLEEP_SECS)

        # Connect to DUT from peer, putting DUT in secondary role
        if self.floss:
            # Floss doesn't connect to HOG profile if it's not the initiator.
            # Explicitly connect to HOG with |test_connection_by_adapter| right
            # after the peer is connected.
            self.test_connection_by_device(primary_device,
                                           post_connection_delay=0)
            self.test_connection_by_adapter(primary_device.address)
        else:
            self.test_connection_by_device(primary_device)

        # If test requires it, connect and test secondary device
        if secondary_info is not None and device_use == 'mid':
            self.connect_and_test_secondary_device(
                secondary_device_handle, secondary_test_func)

        # Try transferring data over connection
        primary_test_func(primary_device)

        # Handle cleanup of connected devices
        if secondary_info is not None:
            self.test_disconnection_by_adapter(secondary_device_handle.address)

        self.test_disconnection_by_device(primary_device)
        self.test_reset_advertising()

    ### Nearby sender role test

    def nearby_sender_role_test(self, nearby_device, nearby_device_test_func,
                                secondary_info=None):
        """Test Nearby Sender role

        Optional secondary device arguments allows us to try test with existing
        connection, or to establish new secondary connection during test

        @param nearby_device: Device acting as Nearby Receiver in test
        @param nearby_device_test_func: function to test connection to device
        @param secondary_info: Optional tuple with structure
            (secondary_device_handle, secondary_test_func, use):
            secondary_device_handle: peer device to test with
            secondary_test_func: function handle to run connection test
            device_use: 'pre' - device should be connected before test runs - or
                        'mid' - device should be connected during test
        """

        #
        # Due to crbug/946835, some messages does not reach btmon
        # causing our tests to fails. This is seen on kernel 3.18 and lower.
        # Remove this check when the issue is fixed
        # TODO(crbug/946835)
        #
        self.is_supported_kernel_version(self.host.get_kernel_version(),
                                         '3.19',
                                         'Test cannnot proceed on this'
                                         'kernel due to crbug/946835 ')

        if secondary_info is not None:
            (secondary_device_handle, secondary_test_func,
                    device_use) = secondary_info

        # Start fresh, remove DUT from nearby device
        nearby_device.RemoveDevice(self.bluetooth_facade.address)

        # Pair the nearby device first - necessary for later connection to
        # secondary device
        self.pair_adapter_to_device(nearby_device)

        # If test requires it, connect and test secondary device
        if secondary_info is not None and device_use == 'pre':
            self.connect_and_test_secondary_device(
                secondary_device_handle, secondary_test_func)

        # Register and start non-connectable advertising instance
        # We ignore failure because the test isn't able to verify the min/max
        # advertising intervals, but this is ok.
        self.test_reset_advertising()
        # Floss does not support set advertising intervals.
        if not self.floss:
            self.test_set_advertising_intervals(DEFAULT_MIN_ADV_INTERVAL,
                                                DEFAULT_MAX_ADV_INTERVAL)

        # For now, advertise connectable advertisement. If we use a broadcast
        # advertisement, the Pi can't resolve the address and
        # test_discover_by_device will fail
        self.test_register_advertisement(
                advertisements_data.gen_advertisements(0, floss=self.floss), 1)

        # Second thread runs on peer, delays, discovers DUT, and then advertises
        # itself back
        peer_discover = self._receiver_discovery_async(nearby_device)
        peer_discover.start()

        if self.floss:
            # Floss automatically connects to the peer as soon as it's
            # discovered, without reporting any Adv events.
            self.test_device_is_connected(nearby_device.address, timeout=30)
        else:
            # Verify that we correctly receive advertisement from nearby device
            self.test_receive_advertisement(address=nearby_device.address,
                                            timeout=30)
            # Connect to peer from DUT
            self.test_connection_by_adapter(nearby_device.address)

        # Make sure peer thread completes
        peer_discover.join()

        # TODO(b/164131633) On 4.4 kernel, sometimes the input device is not
        # created if we connect a second device too quickly
        time.sleep(self.TEST_SLEEP_SECS)

        # If test requires it, connect and test secondary device
        if secondary_info is not None and device_use == 'mid':
            self.connect_and_test_secondary_device(
                secondary_device_handle, secondary_test_func)

        time.sleep(self.TEST_SLEEP_SECS)

        # Try data test with nearby device
        nearby_device_test_func(nearby_device)

        # Handle cleanup of connected devices
        if secondary_info is not None:
            self.test_disconnection_by_adapter(secondary_device_handle.address)

        self.test_disconnection_by_adapter(nearby_device.address)
        self.test_reset_advertising()

    # Nearby receiver role test

    def nearby_receiver_role_test(self,
                                  nearby_device,
                                  nearby_device_test_func,
                                  secondary_info=None,
                                  use_privacy=False):
        """Test Nearby Receiver role

        Optional secondary device arguments allows us to try test with existing
        connection, or to establish new secondary connection during test

        @param nearby_device: Device acting as Nearby Sender in test
        @param nearby_device_test_func: function to test connection to device
        @param secondary_info: Optional tuple with structure
            (secondary_device_handle, secondary_test_func, use):
            secondary_device_handle: peer device to test with
            secondary_test_func: function handle to run connection test
            device_use: 'pre' - device should be connected before test runs - or
                        'mid' - device should be connected in middle of test,
                                during advertisement
                        'end' - device should be connected at end of test, when
                                already connected to Nearby device
        """

        #
        # Due to crbug/946835, some messages does not reach btmon
        # causing our tests to fails. This is seen on kernel 3.18 and lower.
        # Remove this check when the issue is fixed
        # TODO(crbug/946835)
        #
        self.is_supported_kernel_version(self.host.get_kernel_version(),
                                         '3.19',
                                         'Test cannnot proceed on this'
                                         'kernel due to crbug/946835 ')

        if secondary_info is not None:
            (secondary_device_handle, secondary_test_func,
                    device_use) = secondary_info

        # Start fresh, remove device peer
        nearby_device.RemoveDevice(self.bluetooth_facade.address)

        # If test requires it, connect and test secondary device
        if secondary_info is not None and device_use == 'pre':
            self.connect_and_test_secondary_device(
                secondary_device_handle, secondary_test_func)

        # Verify that we correctly receive advertisement from peer
        # TODO ideally, peer would be broadcasting non-connectable adv with
        # 0xFE2C data, but this is not implemented yet on peer
        self.test_receive_advertisement(address=nearby_device.address,
                                        timeout=30)

        # Pair the nearby device first - necessary for later connection to
        # secondary device
        self.pair_adapter_to_device(nearby_device)

        # Register and start non-connectable advertising instance
        # We ignore failure because the test isn't able to verify the min/max
        # advertising intervals, but this is ok.
        self.test_reset_advertising()
        # Floss does not support set advertising intervals.
        if not self.floss:
            self.test_set_advertising_intervals(DEFAULT_MIN_ADV_INTERVAL,
                                                DEFAULT_MAX_ADV_INTERVAL)
        adv_data = advertisements_data.gen_advertisements(0, floss=self.floss)
        if use_privacy:
            adv_data["parameters"]["own_address_type"] = 1
        self.test_register_advertisement(adv_data, 1)

        # If test requires it, connect and test secondary device
        if secondary_info is not None and device_use == 'mid':
            self.connect_and_test_secondary_device(
                secondary_device_handle, secondary_test_func)

        # Discover DUT from peer
        self.test_discover_by_device(nearby_device)

        # Connect to DUT from peer
        if self.floss:
            # Floss doesn't connect to HOG profile if it's not the initiator.
            # Explicitly connect to HOG with |test_connection_by_adapter| right
            # after the peer is connected.
            self.test_connection_by_device(nearby_device,
                                           post_connection_delay=0)
            self.test_connection_by_adapter(nearby_device.address)
        else:
            self.test_connection_by_device(nearby_device)

        # TODO(b/164131633) On 4.4 kernel, sometimes the input device is not
        # created if we connect a second device too quickly
        time.sleep(self.TEST_SLEEP_SECS)

        # If test requires it, connect and test secondary device
        if secondary_info is not None and device_use == 'end':
            self.connect_and_test_secondary_device(
                secondary_device_handle, secondary_test_func)

        time.sleep(self.TEST_SLEEP_SECS)

        # Try data test with nearby device
        nearby_device_test_func(nearby_device)

        self.test_disconnection_by_device(nearby_device)
        self.test_reset_advertising()
