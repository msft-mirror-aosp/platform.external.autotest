# Lint as: python2, python3
# Copyright 2024 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""A Batch of Bluetooth and Wi-Fi coex performance tests."""

import logging
import threading
import time

from autotest_lib.client.common_lib import error
from autotest_lib.client.cros.bluetooth.bluetooth_audio_test_data import A2DP
from autotest_lib.server.cros.bluetooth.bluetooth_adapter_audio_tests import (
        BluetoothAdapterAudioTests)
from autotest_lib.server.cros.bluetooth.bluetooth_adapter_hidreports_tests import (
        BluetoothAdapterHIDReportTests)
from autotest_lib.server.cros.bluetooth.bluetooth_adapter_quick_tests import (
        BluetoothAdapterQuickTests)
from autotest_lib.server.cros.network import perf_test_manager as perf_manager
from autotest_lib.server.cros.network import wifi_cell_perf_test_base


def calculate_events_average_delay(devices_events_time_diff,
                                   devices_os_time_diff):
    """Calculates the delay between sent and received events.

    Calculate the delay in seconds between sent Bluetooth events and received
    ones.

    @param devices_events_time_diff: A dictionary contains device name
                                     and the events time differences between
                                     DUT and Peer.
    @param devices_os_time_diff: A dictionary contains device name and the OS
                                 time differences.

    @return: A dictionary contains device name and OS time difference.
    """
    result = {}
    for key_ev in devices_os_time_diff:
        events = devices_events_time_diff[key_ev]
        os_time_diff = devices_os_time_diff[key_ev]
        # Adjust the OS time difference to align the Bluetooth audio device's
        # clock with the sender's clock (DUT). For HID devices, the peer device
        # is the sender. For A2DP (audio) devices, the DUT is the sender.
        # Therefore, os_time_diff for Bluetooth audio need to be negated to
        # align the clocks.
        if key_ev == 'bluetooth_audio':
            os_time_diff = -os_time_diff
        average = sum(events) / len(events) + os_time_diff
        result[key_ev] = average
    return result


class bluetooth_WiFiCoexPerformance(
        wifi_cell_perf_test_base.WiFiCellPerfTestBase,
        BluetoothAdapterHIDReportTests, BluetoothAdapterQuickTests,
        BluetoothAdapterAudioTests):
    """Test the effect of Wi-Fi load on Bluetooth HID performance.

    Conducts a performance test for a set of Bluetooth device types.
    """
    test_wrapper = BluetoothAdapterQuickTests.quick_test_test_decorator
    batch_wrapper = BluetoothAdapterQuickTests.quick_test_batch_decorator
    devices_latest_index = {}
    running_threads = []

    # Bluetooth delay should not be less than 0.1 second.
    BT_DELAY_ACCEPTED_TIME = 0.1

    DEFAULT_BT_LOAD_TIME = 20
    # Default delay between BT events.
    DEFAULT_BT_CLICK_DELAY = 0.01
    # Expected events sent to BT device when you click the mouse/keyboard.
    EXPECTED_EVENTS_PER_CLICK = 2
    MOUSE_CLICKS_NUMBER = int(DEFAULT_BT_LOAD_TIME / DEFAULT_BT_CLICK_DELAY /
                              EXPECTED_EVENTS_PER_CLICK)

    # Keyboard string with 1000 char (2000 events).
    KEYBOARD_STRING = 'wasd' * 250

    # Number of expected events for each device (each click is two events).
    MOUSE_EVENTS_COUNTS = MOUSE_CLICKS_NUMBER * EXPECTED_EVENTS_PER_CLICK
    KEYBOARD_EVENTS_COUNTS = len(KEYBOARD_STRING) * EXPECTED_EVENTS_PER_CLICK

    # Define global constants for the amount of movement in the gamepad
    # thumbstick.
    DELTA_X = 6000
    DELTA_Y = 7000
    # The default delay, in seconds, between consecutive gamepad events.
    GAMEPAD_DEFAULT_EVENT_DELAY = 0.05
    # Number of gamepad events to be considered: button press, thumbstick
    # movements and button release including thumbstick stop.
    EXPECTED_EVENTS_PER_GAMEPAD_ACTION = 3
    # The default number of actions for the gamepad test.
    GAMEPAD_DEFAULT_NUM_ACTIONS = int(DEFAULT_BT_LOAD_TIME /
                                      GAMEPAD_DEFAULT_EVENT_DELAY /
                                      EXPECTED_EVENTS_PER_GAMEPAD_ACTION)
    GAMEPAD_EVENTS_COUNTS = (GAMEPAD_DEFAULT_NUM_ACTIONS *
                             EXPECTED_EVENTS_PER_GAMEPAD_ACTION)

    # Duration in seconds for BT audio streaming.
    BT_AUDIO_STREAMING_DURATION = 20
    AUDIO_DEVICE_TYPE = 'BLUETOOTH_AUDIO'
    # Number of transmitted events in the previous audio run.
    previous_audio_run_events_count = 0

    IPERF_RUN_TIME = 30

    PASS_RATE = 0.95  # 95%
    PERF_TEST_TYPES = [
            perf_manager.PerfTestTypes.TEST_TYPE_TCP_TX,
            perf_manager.PerfTestTypes.TEST_TYPE_TCP_RX,
            perf_manager.PerfTestTypes.TEST_TYPE_UDP_TX,
            perf_manager.PerfTestTypes.TEST_TYPE_UDP_RX
    ]

    def parse_additional_arguments(self, commandline_args, additional_params):
        """Hooks into super class to take control files parameters.

        @param commandline_args: Dict of parsed parameters from the autotest.
        @param additional_params: List of HostapConfig objects.
        """
        super(bluetooth_WiFiCoexPerformance,
              self).parse_additional_arguments(commandline_args)

        self._ap_configs, self._use_iperf = additional_params

    def __do_mouse_click_load_test(self, mouse):
        """Runs mouse load test.

        @param mouse: Mouse device.
        """
        time.sleep(2)
        # We ignored test failure to focus on btmon log result, not evtest.
        # Packet loss less than (5%) should be ok.
        self.ignore_failure(self.test_continuous_mouse_left_click,
                            device=mouse,
                            num_clicks=self.MOUSE_CLICKS_NUMBER,
                            delay=self.DEFAULT_BT_CLICK_DELAY)

    def __do_keyboard_click_load_test(self, keyboard):
        """Runs keyboard load test.

        @param keyboard: Keyboard device.
        """
        time.sleep(2)
        # We ignored test failure to focus on btmon log result, not evtest.
        # Packet loss less than (5%) should be ok.
        self.ignore_failure(self.test_keyboard_input_from_string,
                            device=keyboard,
                            string_to_send=self.KEYBOARD_STRING,
                            delay=self.DEFAULT_BT_CLICK_DELAY)

    def __do_gamepad_load_test(self, gamepad):
        """Runs gamepad load test.

        @param gamepad: gamepad device.
        """
        time.sleep(2)
        # We ignored test failure to focus on btmon log result, not evtest.
        # Packet loss less than (5%) should be ok.
        self.ignore_failure(
                self.test_gamepad_continuous_press_button_and_move_thumbstick,
                device=gamepad,
                button='GAMEPAD_BUTTON_A',
                stick='GAMEPAD_LEFT_THUMBSTICK',
                delta_x=self.DELTA_X,
                delta_y=self.DELTA_Y,
                num_iterations=self.GAMEPAD_DEFAULT_NUM_ACTIONS,
                delay=self.GAMEPAD_DEFAULT_EVENT_DELAY)

    def __do_audio_load_test(self, audio):
        """Runs audio load test.

        @param audio: Audio device.
        """
        time.sleep(2)
        self.test_a2dp_sinewaves(audio, A2DP, self.BT_AUDIO_STREAMING_DURATION)

    def connect_wifi(self):
        """Connects DUT to router."""
        for ap_config in self._ap_configs:
            # Sets up the router and associate the client with it.
            self.configure_and_connect_to_ap(ap_config)

    def clean_client(self):
        """Clears router connection with DUT."""
        self.context.client.shill.disconnect(self.context.router.get_ssid())
        self.context.router.deconfig()

    def is_audio_device(self, device):
        return device.device_type == self.AUDIO_DEVICE_TYPE

    def run_iperf(self, run_time, test_type):
        """Runs Iperf for a specific time.

        @param run_time: Time in seconds to run Iperf.
        @param test_type: The perf_manager perf test type.
        """
        manager = perf_manager.PerfTestManager(self._use_iperf)
        config = manager.get_config(test_type, True, run_time)
        run_result = manager.run(self.context.client,
                                 self.context.router,
                                 config,
                                 retry_count=1)

        return run_result

    def calculate_time_diff(self, devices, events_count):
        """Calculates time difference between DUT and Peers Bluetooth events.

        @param devices: List of Bluetooth devices.
        @param events_count: List represents number of expected events for each
                             device.

        @return: A dictionary contains device name and list of events time
                 difference.
        """
        devices_events_time_diff = {}
        for device, event_count in zip(devices, events_count):
            if self.is_audio_device(device):
                # btmon needs additional time to write audio data.
                time.sleep(5)
                receiver_results = self.get_peer_a2dp_notif_timestamps(device)
                transmitter_result = self.get_dut_a2dp_notif_timestamps(device)

                # Calculate the number of new events transmitted during the
                # current audio run.
                # btmon returns accumulated audio data for all runs, so to get
                # the count of events for the current run, subtract the count
                # of events from the previous runs from the total count of
                # events in transmitter_result.
                event_count = len(transmitter_result
                                  ) - self.previous_audio_run_events_count
                self.previous_audio_run_events_count = len(transmitter_result)
            else:
                receiver_results = self.get_dut_hid_notif_timestamps(device)
                transmitter_result = self.get_peer_hid_notif_timestamps(device)
            address = device.address

            last_receiver_index = self.devices_latest_index[address]
            if last_receiver_index == 0:
                first_receiver_index = 0
            else:
                first_receiver_index = last_receiver_index + 1

            # Set latest received timestamp.
            self.devices_latest_index[address] = len(receiver_results) - 1

            # NOTE: In case of one packet failed to be sent, all packets
            # after it will not be received.
            # i.e.: If we want to send 100 packets, the first 70 packets
            # received well, and packet 71 failed, then the receiver will not
            # receive all packets from 71 to 100.

            # Get the received result for this round.
            receiver_results = receiver_results[first_receiver_index:]

            # Checks percentage error.
            error_percentage = len(receiver_results) / event_count
            if error_percentage < self.PASS_RATE:
                raise error.TestFail(
                        'Expected error percentage of |%s|, got |%s|' %
                        (self.PASS_RATE, error_percentage))

            # Calculate time deference for current round.
            lost_timestamp_count = event_count - len(receiver_results)
            tot = [
                    round((a - b), 4) for a, b in zip(
                            receiver_results, transmitter_result[
                                    -event_count:-lost_timestamp_count
                                    if lost_timestamp_count else None])
            ]
            if tot:
                devices_events_time_diff[device._name] = tot
            else:
                logging.error('No returned results from device %s',
                              device._name)
        return devices_events_time_diff

    def get_devices_os_time_diff(self, devices):
        """Gets OS time difference between DUT and peers.

        Note: This method must be called only at the end of test.

        @param devices: List of Bluetooth devices.

        @return: A dictionary contains device name and OS time difference.
        """
        devices_os_time = {}
        for device in devices:
            time_diff = self.get_os_time_difference(device)
            devices_os_time[device._name] = round(time_diff, 4)
        return devices_os_time

    def initialize_bluetooth_audio_devices(self, devices):
        """Initializes bluetooth audio devices.

        @param devices: List of Bluetooth devices.
        """
        for device in devices:
            if self.is_audio_device(device):
                self.initialize_bluetooth_audio(device, A2DP)

    def pair_bluetooth_devices(self, devices):
        """Pairs the devices pre-test to simplify later re-connection.

        @param devices: List of Bluetooth devices.
        """
        for device in devices:
            self.test_discover_device(device.address)
            self.test_pairable()
            self.test_pairing(device.address, device.pin, trusted=True)

    def connect_bluetooth_devices(self, devices):
        """Connects devices with DUT.

        @param devices: List of Bluetooth HID devices.
        """
        for device in devices:
            self.test_connection_by_device(device)
            self.test_connection_by_adapter(device.address)

    def disconnect_bluetooth_devices(self, devices):
        """Disconnects devices from DUT.

        @param devices: List of Bluetooth devices.
        """
        for device in devices:
            self.test_disconnection_by_adapter(device.address)

    def cleanup_bluetooth_audio_devices(self, devices):
        """Cleanup for Bluetooth audio devices.

        @param devices: List of Bluetooth devices.
        """
        for device in devices:
            if self.is_audio_device(device):
                self.cleanup_bluetooth_audio(device, A2DP)

    def run_bt_load_tests(self, devices, load_tests):
        """Runs Bluetooth load tests.

         @param devices: List of Bluetooth devices.
         @param load_tests: List of load tests for each device.
        """
        for device, load_test in zip(devices, load_tests):
            if self.is_audio_device(device):
                device.StartAudioServer(A2DP)
                self.test_connection_by_device(device)
            thread = threading.Thread(target=load_test, args=(device, ))
            self.running_threads.append(thread)
            thread.start()

    def check_bluetooth_delay(self, devices, time_diff):
        """Checks Bluetooth devices delay values.

        Check if Bluetooth device delay through different status will be less
        than the "BT_DELAY_ACCEPTED_TIME" value.

        @param devices: List of Bluetooth devices.
        @param time_diff: A dictionary contains Wi-Fi state as a key and
                          device name with time difference between events as
                          a dictionary value.
                          e.g: {'before_wifi_connection': {
                          'bluetooth_mouse':0.0055}}

        """
        os_time_diff = self.get_devices_os_time_diff(devices)
        for key in time_diff:
            logging.info(key)
            avg_delay = calculate_events_average_delay(time_diff[key],
                                                       os_time_diff)
            logging.info(avg_delay)
            for device in avg_delay:
                if avg_delay[device] > self.BT_DELAY_ACCEPTED_TIME:
                    raise error.TestFail('%s device %s delay is %s, Expected '
                                         'lest than %s second' %
                                         (device, key, avg_delay[device],
                                          self.BT_DELAY_ACCEPTED_TIME))

    def _bluetooth_wifi_coex_load_test(self, devices, load_tests,
                                       events_count):
        """Tests BT Wi-Fi coex with Wi-Fi load.

        @param devices: List of Bluetooth devices.
        @param load_tests: List of load tests for each device.
        @param events_count: List of expected events count for each load test.
        """

        time_diff = {
                'before_wifi_connection': 0.0,
                'after_wifi_connection': 0.0,
                'during_tcp_tx_load': 0.0,
                'during_tcp_rx_load': 0.0,
                'during_udp_tx_load': 0.0,
                'during_udp_rc_load': 0.0,
                'after_wifi_load': 0.0
        }
        for device in devices:
            self.devices_latest_index[device.address] = 0

        self.initialize_bluetooth_audio_devices(devices)
        self.pair_bluetooth_devices(devices)
        self.connect_bluetooth_devices(devices)
        # Before Wi-Fi connection.
        logging.info('Start testing: Before Wi-Fi connection')
        self.run_bt_load_tests(devices, load_tests)
        for thread in self.running_threads:
            thread.join()
        time_diff['before_wifi_connection'] = self.calculate_time_diff(
                devices, events_count)
        logging.info('Finish testing: Before Wi-Fi connection')

        self.connect_wifi()

        # After Wi-Fi connection.
        logging.info('Start testing: After Wi-Fi connection.')

        self.run_bt_load_tests(devices, load_tests)
        for thread in self.running_threads:
            thread.join()
        time_diff['after_wifi_connection'] = self.calculate_time_diff(
                devices, events_count)
        logging.info('Finish testing: After Wi-Fi connection.')

        # During Wi-Fi load.
        logging.info('Start testing: During Wi-Fi load.')
        during_load_keys = [
                key for key in time_diff if key.startswith('during')
        ]
        for key, test_type in zip(during_load_keys, self.PERF_TEST_TYPES):
            self.run_bt_load_tests(devices, load_tests)
            logging.info(self.run_iperf(self.IPERF_RUN_TIME, test_type))
            for thread in self.running_threads:
                thread.join()
            time_diff[key] = self.calculate_time_diff(devices, events_count)

        logging.info('Finish testing: During Wi-Fi load.')

        self.clean_client()

        logging.info('Start testing: After Wi-Fi Load.')

        self.run_bt_load_tests(devices, load_tests)
        for thread in self.running_threads:
            thread.join()
        time_diff['after_wifi_load'] = self.calculate_time_diff(
                devices, events_count)
        logging.info('Finish testing: After Wi-Fi Load.')

        self.check_bluetooth_delay(devices, time_diff)
        self.disconnect_bluetooth_devices(devices)
        self.cleanup_bluetooth_audio_devices(devices)

    @test_wrapper('Coex tests with mouse click load',
                  devices={'MOUSE': 1},
                  supports_floss=True)
    def mouse_load(self):
        """Performs Bluetooth mouse load."""
        self._bluetooth_wifi_coex_load_test([self.devices['MOUSE'][0]],
                                            [self.__do_mouse_click_load_test],
                                            [self.MOUSE_EVENTS_COUNTS])

    @test_wrapper('Coex tests with BLE mouse click load',
                  devices={'BLE_MOUSE': 1},
                  supports_floss=True)
    def ble_mouse_load(self):
        """Performs BLE mouse load."""
        self._bluetooth_wifi_coex_load_test([self.devices['BLE_MOUSE'][0]],
                                            [self.__do_mouse_click_load_test],
                                            [self.MOUSE_EVENTS_COUNTS])

    @test_wrapper(
            'Coex tests with keyboard load',
            devices={'KEYBOARD': 1},
            supports_floss=True,
    )
    def keyboard_load(self):
        """Performs Bluetooth keyboard load."""
        self._bluetooth_wifi_coex_load_test(
                [self.devices['KEYBOARD'][0]],
                [self.__do_keyboard_click_load_test],
                [self.KEYBOARD_EVENTS_COUNTS])

    @test_wrapper('Coex tests with BLE keyboard load',
                  devices={'BLE_KEYBOARD': 1},
                  supports_floss=True)
    def ble_keyboard_load(self):
        """Performs BLE keyboard load."""
        self._bluetooth_wifi_coex_load_test(
                [self.devices['BLE_KEYBOARD'][0]],
                [self.__do_keyboard_click_load_test],
                [self.KEYBOARD_EVENTS_COUNTS])

    @test_wrapper(
            'Coex tests with gamepad load',
            devices={'GAMEPAD': 1},
            supports_floss=True,
    )
    def gamepad_load(self):
        """Performs Bluetooth gamepad load."""
        self._bluetooth_wifi_coex_load_test([self.devices['GAMEPAD'][0]],
                                            [self.__do_gamepad_load_test],
                                            [self.GAMEPAD_EVENTS_COUNTS])

    @test_wrapper(
            'Coex tests with audio load',
            devices={'BLUETOOTH_AUDIO': 1},
            supports_floss=True,
    )
    def audio_load(self):
        """Performs Bluetooth audio load."""
        self._bluetooth_wifi_coex_load_test(
                [self.devices['BLUETOOTH_AUDIO'][0]],
                [self.__do_audio_load_test], [None])

    @test_wrapper('Coex tests with keyboard and mouse load',
                  devices={
                          'KEYBOARD': 1,
                          'MOUSE': 1
                  },
                  supports_floss=True)
    def keyboard_with_mouse_load(self):
        """Performs Bluetooth keyboard and mouse load."""
        self._bluetooth_wifi_coex_load_test(
                [self.devices['KEYBOARD'][0], self.devices['MOUSE'][0]], [
                        self.__do_keyboard_click_load_test,
                        self.__do_mouse_click_load_test
                ], [self.KEYBOARD_EVENTS_COUNTS, self.MOUSE_EVENTS_COUNTS])

    @test_wrapper('Coex tests with keyboard and gamepad load',
                  devices={
                          'KEYBOARD': 1,
                          'GAMEPAD': 1
                  },
                  supports_floss=True)
    def keyboard_with_gamepad_load(self):
        """Performs Bluetooth keyboard and gamepad load."""
        self._bluetooth_wifi_coex_load_test([
                self.devices['KEYBOARD'][0], self.devices['GAMEPAD'][0]
        ], [self.__do_keyboard_click_load_test, self.__do_gamepad_load_test
            ], [self.KEYBOARD_EVENTS_COUNTS, self.GAMEPAD_EVENTS_COUNTS])

    @test_wrapper('Coex tests with gamepad and audio load',
                  devices={
                          'GAMEPAD': 1,
                          'BLUETOOTH_AUDIO': 1
                  },
                  supports_floss=True)
    def gamepad_with_audio_load(self):
        """Performs Bluetooth gamepad and audio load."""
        self._bluetooth_wifi_coex_load_test([
                self.devices['GAMEPAD'][0], self.devices['BLUETOOTH_AUDIO'][0]
        ], [self.__do_gamepad_load_test, self.__do_audio_load_test],
                                            [self.GAMEPAD_EVENTS_COUNTS, None])

    @test_wrapper('Coex tests with BLE keyboard and BLE mouse load',
                  devices={
                          'BLE_KEYBOARD': 1,
                          'BLE_MOUSE': 1
                  },
                  supports_floss=True)
    def ble_keyboard_with_ble_mouse_load(self):
        """Performs BLE keyboard and mouse load."""
        self._bluetooth_wifi_coex_load_test([
                self.devices['BLE_KEYBOARD'][0], self.devices['BLE_MOUSE'][0]
        ], [
                self.__do_keyboard_click_load_test,
                self.__do_mouse_click_load_test
        ], [self.KEYBOARD_EVENTS_COUNTS, self.MOUSE_EVENTS_COUNTS])

    @test_wrapper('Coex tests with BLE mouse and audio load',
                  devices={
                          'BLE_MOUSE': 1,
                          'BLUETOOTH_AUDIO': 1
                  },
                  supports_floss=True)
    def ble_mouse_with_audio_load(self):
        """Performs BLE mouse and audio load."""
        self._bluetooth_wifi_coex_load_test([
                self.devices['BLE_MOUSE'][0],
                self.devices['BLUETOOTH_AUDIO'][0]
        ], [self.__do_mouse_click_load_test, self.__do_audio_load_test],
                                            [self.MOUSE_EVENTS_COUNTS, None])

    @test_wrapper('Coex tests with mouse, gamepad and audio load',
                  devices={
                          'MOUSE': 1,
                          'GAMEPAD': 1,
                          'BLUETOOTH_AUDIO': 1
                  },
                  supports_floss=True)
    def mouse_gamepad_audio_load(self):
        """Performs mouse, gamepad and audio load."""
        self._bluetooth_wifi_coex_load_test([
                self.devices['MOUSE'][0], self.devices['GAMEPAD'][0],
                self.devices['BLUETOOTH_AUDIO'][0]
        ], [
                self.__do_mouse_click_load_test, self.__do_gamepad_load_test,
                self.__do_audio_load_test
        ], [self.MOUSE_EVENTS_COUNTS, self.GAMEPAD_EVENTS_COUNTS, None])

    @test_wrapper('Coex tests with BLE keyboard, BLE mouse and audio load',
                  devices={
                          'BLE_KEYBOARD': 1,
                          'BLE_MOUSE': 1,
                          'BLUETOOTH_AUDIO': 1
                  },
                  supports_floss=True)
    def ble_keyboard_ble_mouse_audio_load(self):
        """Performs BLE keyboard, BLE mouse and audio load."""
        self._bluetooth_wifi_coex_load_test([
                self.devices['BLE_KEYBOARD'][0], self.devices['BLE_MOUSE'][0],
                self.devices['BLUETOOTH_AUDIO'][0]
        ], [
                self.__do_keyboard_click_load_test,
                self.__do_mouse_click_load_test, self.__do_audio_load_test
        ], [self.KEYBOARD_EVENTS_COUNTS, self.MOUSE_EVENTS_COUNTS, None])

    @batch_wrapper('HID bluetooth Wi-Fi coex batch')
    def coex_health_batch_run(self, num_iterations=1, test_name=None):
        """Runs the bluetooth coex perf test batch or a specific given test.

        @param num_iterations: How many iterations to run.
        @param test_name: Specific test to run otherwise None to run the whole
                          batch.
        """
        self.mouse_load()
        self.ble_mouse_load()

    def run_once(self,
                 host,
                 num_iterations=1,
                 peer_required=True,
                 args_dict=None,
                 test_name=None,
                 flag='Quick Health',
                 floss=False):
        """Runs the batch of Bluetooth Wi-Fi coexist performance tests.

        @param host: The DUT, usually a chromebook.
        @param num_iterations: The number of rounds to execute the test.
        @param test_name: A single test to run or leave None to run the batch.
        @param peer_required: Whether a btpeer is required.
        @param flag: Run 'Quick Health' tests or 'AVL' tests.
        @param floss: Enable Floss.
        """
        # Initialize and run the test batch or the requested specific test.
        self.quick_test_init(host,
                             use_btpeer=peer_required,
                             flag=flag,
                             start_browser=False,
                             args_dict=args_dict,
                             floss=floss,
                             enable_debug_log=False)
        self.coex_health_batch_run(num_iterations, test_name)
        self.quick_test_cleanup()
