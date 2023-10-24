# Lint as: python2, python3
# Copyright 2019 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Server side bluetooth tests about sending bluetooth HID reports."""

from __future__ import absolute_import

import logging
import time

import common
from autotest_lib.server.cros.bluetooth import bluetooth_adapter_tests


class BluetoothAdapterHIDReportTests(
        bluetooth_adapter_tests.BluetoothAdapterTests):
    """Server side bluetooth tests about sending bluetooth HID reports.

    This test tries to send HID reports to a DUT and verifies if the DUT
    could receive the reports correctly. For the time being, only bluetooth
    mouse events are tested. Bluetooth keyboard events will be supported
    later.
    """

    HID_TEST_SLEEP_SECS = 5
    # Regex to find HCI connection event handle for Bluetooth LE in btmon log,
    # e.g.
    # HCI Event: LE Meta Event (0x3e) plen 31             #509 [hci0] 37.342083
    #       LE Enhanced Connection Complete (0x0a)
    #         Status: Success (0x00)
    #         Handle: 3585
    #         Role: Central (0x00)
    #         Peer address type: Public (0x00)
    #         Peer address: DC:A6:32:AE:EC:13
    LE_ACL_CONNECTION_HANDLE_REGEX = (r"HCI Event: LE Meta Event .* #\d+ \["
                                      r"hci\d+\].*\s.*(?:LE Enhanced "
                                      r"Connection Complete|LE Connection "
                                      r"Complete).*\n.*Status: Success \("
                                      r"0x00\)\n.*Handle: (\d+)(?:.|\n)*Peer "
                                      r"address: {}")

    # Regex to find HCI connection event time for Bluetooth LE in btmon log
    # e.g.
    # HCI Event: LE Meta Event (0x3e) plen 31             #509 [hci0] 37.342083
    #       LE Enhanced Connection Complete (0x0a)
    #         Status: Success (0x00)
    #         Handle: 3585
    #         Role: Central (0x00)
    #         Peer address type: Public (0x00)
    #         Peer address: DC:A6:32:AE:EC:13
    LE_ACL_CONNECTED_REGEX = (r"HCI Event: LE Meta Event .* #\d+ \[hci\d+\] ("
                              r"\d+\.\d+)\s.*(?:LE Enhanced Connection "
                              r"Complete|LE Connection Complete).*\s.*Status: "
                              r"Success \(0x00\)(?:.|\n)*Peer address: {}")

    # Regex to find ACL data event time for Bluetooth LE in btmon log, e.g.
    # ACL Data RX: Handle 3585 flags 0x02 dlen 11         #708 [hci0] 45.644842
    #       ATT: Handle Value Notification (0x1b) len 6
    #         Handle: 0x000c
    #           Data: 02000000
    LE_HID_NOTIFICATION_REGEX = (
            r"ACL Data (?:RX|TX): Handle {}.* #\d+ \["
            r"hci\d+\] ("
            r"\d+\.\d+)\s.*ATT: Handle Value Notification")

    # Regex to find HCI connection event handle for Bluetooth BR in btmon log,
    # e.g.
    # HCI Event: Connect Complete (0x03) plen 11          #881 [hci0] 47.119272
    #         Status: Success (0x00)
    #         Handle: 256
    #         Address: DC:A6:32:AE:EC:13
    CL_ACL_CONNECTION_HANDLE_REGEX = (
            r"HCI Event: Connect Complete.* #\d+ \["
            r"hci\d+\].*\n.*Status: Success \("
            r"0x00\)\n.*Handle: (\d+)\n.*Address: {}")

    # Regex to find HCI connection event time for Bluetooth BR in btmon log,
    # e.g.
    # HCI Event: Connect Complete (0x03) plen 11          #881 [hci0] 47.119272
    #         Status: Success (0x00)
    #         Handle: 256
    #         Address: DC:A6:32:AE:EC:13
    CL_ACL_CONNECTED_REGEX = (
            r"HCI Event: Connect Complete.* #\d+ \[hci\d+\] ("
            r"\d+\.\d+)\n.*Status: Success \("
            r"0x00\)\n.*\n.*Address: {}")

    # Regex to find ACL data event time for Bluetooth BR in btmon log, e.g.
    # ACL Data RX: Handle 256 flags 0x02 dlen 10         #1069 [hci0] 60.837835
    #       Channel: 68 len 6 [PSM 19 mode Basic (0x00)] {chan 2}
    #         a1 02 00 00 00 00
    # PSM with value 19 was taken from this refrence:
    # https://btprodspecificationrefs.blob.core.windows.net/assigned-numbers/
    # Assigned%20Number%20Types/Assigned_Numbers.pdf
    CL_HID_NOTIFICATION_REGEX = (r"ACL Data (?:RX|TX): Handle {}.* #\d+ \["
                                 r"hci\d+\] ("
                                 r"\d+\.\d+)\s.*PSM 19 .*\s.*a1")

    def run_mouse_tests(self, device):
        """Run all bluetooth mouse reports tests.

        @param device: the bluetooth HID device.

        """
        self.test_mouse_left_click(device)
        self.test_mouse_right_click(device)
        self.test_mouse_move_in_x(device, 80)
        self.test_mouse_move_in_y(device, -50)
        self.test_mouse_move_in_xy(device, -60, 100)
        self.test_mouse_scroll_down(device, 70)
        self.test_mouse_scroll_up(device, 40)
        self.test_mouse_click_and_drag(device, 90, 30)


    def run_keyboard_tests(self, device):
        """Run all bluetooth keyboard reports tests.

        @param device: the bluetooth HID device.

        """

        self.test_keyboard_input_from_trace(device, "simple_text")


    def run_battery_reporting_tests(self, device):
        """Run battery reporting tests.

        @param device: the Bluetooth device.

        """

        self.test_battery_reporting(device)

    def __get_chameleon_board(self, device):
        """Gets device chameleon board object.

        @param device: The Bluetooth device.

        @return: Bluetooth device chameleon board.
        """
        for btpeer in self.host.btpeer_list:
            if btpeer.get_bluetooth_mac_address() == device.address:
                return btpeer

    def __get_acl_connection_handle_regex(self, device):
        """Gets ACL connection handle regex.

        @param device: The Bluetooth device.

        @return: ACL connection handle regex.
        """
        return self.LE_ACL_CONNECTION_HANDLE_REGEX if 'ble_' in device._name else (
                self.CL_ACL_CONNECTION_HANDLE_REGEX)

    def __get_acl_connection_regex(self, device):
        """Gets ACL connection regex.

        @param device: The Bluetooth device.

        @return: ACL connection regex.
        """
        return self.LE_ACL_CONNECTED_REGEX if 'ble_' in device._name else (
                self.CL_ACL_CONNECTED_REGEX)

    def __get_hid_notification_regex(self, device):
        """Gets HID notification regex.

        @param device: The Bluetooth device.

        @return: HID connection regex.
        """
        return self.LE_HID_NOTIFICATION_REGEX if 'ble_' in device._name else (
                self.CL_HID_NOTIFICATION_REGEX)

    # This function currently only works with public addresses.
    # TODO(b/308882697): Make HID performance tests compatible with random
    #  address.
    def get_peer_hid_notif_timestamps(self, device):
        """Gets peer HID notifications timestamp.

        @param device: The Bluetooth device.

        @return: List of peer notifications timestamp.
        """
        peer = self.__get_chameleon_board(device)
        connection_handle = peer.find_btmon_patterns([
                self.__get_acl_connection_handle_regex(device).format(
                        self.bluetooth_facade.address)
        ])[0][0]

        connect_regex = self.__get_acl_connection_regex(device)
        notification_regex = self.__get_hid_notification_regex(device).format(
                connection_handle)

        peer_connect_times, peer_data_times = (peer.find_btmon_patterns([
                connect_regex.format(self.bluetooth_facade.address),
                notification_regex
        ]))

        connect_time = peer_connect_times[-1] if len(peer_connect_times) else 0
        notification_time_stamps = []
        if connect_time and len(peer_data_times):
            for p in peer_data_times:
                notification_time_stamps.append(float(p) - float(connect_time))
        return notification_time_stamps

    # This function currently only works with public addresses.
    # TODO(b/308882697): Make HID performance tests compatible with random
    #  address.
    def get_dut_hid_notif_timestamps(self, device):
        """Gets DUT HID notifications timestamp.

        @param device: The Bluetooth device.

        @return: List of DUT notifications timestamp.
        """

        connection_handle = self.bluetooth_facade.find_btmon_patterns([
                self.__get_acl_connection_handle_regex(device).format(
                        device.address)
        ], self.dut_btmon_log_path)[0][0]

        connect_regex = self.__get_acl_connection_regex(device)
        notification_regex = self.__get_hid_notification_regex(device).format(
                connection_handle)

        dut_connect_times, dut_data_times = (
                self.bluetooth_facade.find_btmon_patterns([
                        connect_regex.format(device.address),
                        notification_regex
                ], self.dut_btmon_log_path))

        connect_time = dut_connect_times[-1] if len(dut_connect_times) else 0
        notification_time_stamps = []
        if connect_time and len(dut_data_times):
            for d in dut_data_times:
                notification_time_stamps.append(float(d) - float(connect_time))
        return notification_time_stamps

    def run_hid_reports_test(self,
                             device,
                             check_connected_method=lambda device: True,
                             suspend_resume=False,
                             reboot=False,
                             restart=False,
                             inq_mode=None):
        """Running Bluetooth HID reports tests."""
        logging.info("run hid reports test")
        # Reset the adapter and set it pairable.
        if not self.test_reset_on_adapter():
            return
        if not self.test_pairable():
            return

        def run_hid_test():
            """Checks if the device is connected and can be used."""
            time.sleep(self.HID_TEST_SLEEP_SECS)
            if not self.test_device_name(device.address, device.name):
                return False

            time.sleep(self.HID_TEST_SLEEP_SECS)
            if not check_connected_method(device):
                return False
            return True

        dev_paired = False
        dev_connected = False
        try:
            original_inq_mode = None
            if inq_mode and self.test_valid_inquiry_mode(inq_mode):
                original_inq_mode = self.read_inquiry_mode()

                if original_inq_mode == inq_mode:
                    original_inq_mode = None
                else:
                    self.write_inquiry_mode(inq_mode)

            # Let the adapter pair, and connect to the target device.
            self.test_discover_device(device.address)
            dev_paired = self.test_pairing(device.address,
                                           device.pin,
                                           trusted=True)
            if not dev_paired:
                return
            dev_connected = self.test_connection_by_adapter(device.address)
            if not dev_connected:
                return

            # Run hid test to make sure profile is connected
            if not run_hid_test():
                return

            if suspend_resume:
                self.suspend_resume()

                time.sleep(self.HID_TEST_SLEEP_SECS)
                if not self.test_device_is_paired(device.address):
                    return

                # Check if peripheral is connected after suspend resume, reconnect
                # and try again if it isn't.
                if not self.ignore_failure(check_connected_method, device):
                    logging.info("device not connected after suspend_resume")
                    if not self.test_connection_by_device(device):
                        return
                run_hid_test()

            if reboot:
                self.reboot()

                time.sleep(self.HID_TEST_SLEEP_SECS)
                # TODO(b/173146480) - Power on the adapter for now until this bug
                # is resolved.
                if not self.bluetooth_facade.is_powered_on():
                    self.test_power_on_adapter()

                if not self.test_device_is_paired(device.address):
                    return

                time.sleep(self.HID_TEST_SLEEP_SECS)
                if not self.test_connection_by_device(device):
                    return
                run_hid_test()

            if restart:
                self.test_stop_bluetoothd()
                self.test_start_bluetoothd()

                if not self.ignore_failure(self.test_device_is_connected,
                                           device.address):
                    if not self.test_connection_by_device(device):
                        return
                run_hid_test()

        finally:
            # Cleans up the test
            if dev_connected:
                self.test_disconnection_by_adapter(device.address)
            if dev_paired:
                self.test_remove_pairing(device.address)
            if original_inq_mode:
                self.write_inquiry_mode(original_inq_mode)
