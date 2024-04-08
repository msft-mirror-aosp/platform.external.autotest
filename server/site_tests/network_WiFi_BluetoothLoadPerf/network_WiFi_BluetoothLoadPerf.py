# Lint as: python2, python3
# Copyright 2024 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
import logging
import threading
import time

from autotest_lib.client.common_lib import error
from autotest_lib.client.common_lib.cros.network import ping_runner
from autotest_lib.server.cros.bluetooth.bluetooth_adapter_hidreports_tests import (
        BluetoothAdapterHIDReportTests)
from autotest_lib.server.cros.bluetooth.bluetooth_adapter_quick_tests import (
        BluetoothAdapterQuickTests)
from autotest_lib.server.cros.network import (expected_performance_results as
                                              expected_perf_data)
from autotest_lib.server.cros.network import perf_test_manager as perf_manager
from autotest_lib.server.cros.network import wifi_cell_perf_test_base


class network_WiFi_BluetoothLoadPerf(
        wifi_cell_perf_test_base.WiFiCellPerfTestBase,
        BluetoothAdapterHIDReportTests, BluetoothAdapterQuickTests):
    """Tests the effect of bluetooth load on Wi-Fi performance.

    Conducts a performance test for a set of specified router configurations
    and reports results as keyval pairs.
    """

    test_wrapper = BluetoothAdapterQuickTests.quick_test_test_decorator
    batch_wrapper = BluetoothAdapterQuickTests.quick_test_batch_decorator

    base_through = 0
    bt_devices = []
    test_name = None

    # Human-readable strings describing the current BT connection state.
    CONNECTION_STATE_DISCONNECTED = 'BT_disconnected'
    CONNECTION_STATE_CONNECTED = 'BT_connected'
    CONNECTION_STATE_WITH_LOAD = 'BT_connected_with_load'
    CONNECTION_STATE_DISCONNECTED_AGAIN = 'BT_disconnected_again'

    PERF_TEST_TYPES = [
            perf_manager.PerfTestTypes.TEST_TYPE_TCP_TX,
            perf_manager.PerfTestTypes.TEST_TYPE_TCP_RX,
            perf_manager.PerfTestTypes.TEST_TYPE_UDP_TX,
            perf_manager.PerfTestTypes.TEST_TYPE_UDP_RX
    ]

    # The default duration, in seconds, for BT load test.
    DEFAULT_BT_LOAD_TIME = 100
    # Additional preparation time, in seconds, added to the BT load test
    # duration.
    DEFAULT_BT_EXTRA_PREPARE_TIME = 10
    # The default delay, in seconds, between each BT click event.
    DEFAULT_BT_CLICK_DELAY = 0.05
    # The total number of BT click events.
    DEFAULT_BT_TOTAL_CLICK = int(
            (DEFAULT_BT_LOAD_TIME + DEFAULT_BT_EXTRA_PREPARE_TIME) /
            DEFAULT_BT_CLICK_DELAY / 2)

    # Define the default press/release delay for each keystroke.
    DEFAULT_PRESS_RELEASE_DELAY = 0.01
    # Define the default delay between consecutive keystrokes.
    DEFAULT_DELAY_BETWEEN_KEYSTROKES = 0.05
    # Calculate the total number of keystrokes.
    DEFAULT_BT_TOTAL_KEYSTROKES = int(
            (DEFAULT_BT_LOAD_TIME + DEFAULT_BT_EXTRA_PREPARE_TIME) /
            (DEFAULT_PRESS_RELEASE_DELAY + DEFAULT_DELAY_BETWEEN_KEYSTROKES))
    # Generate the input string with 'a' repeated for the total number of
    # keystrokes.
    INPUT_STRING = 'a' * DEFAULT_BT_TOTAL_KEYSTROKES

    def parse_additional_arguments(self, commandline_args, additional_params):
        """Hooks into super class to take control files parameters.

        @param commandline_args: Dict of parsed parameters from the autotest.
        @param additional_params: List of HostApConfig objects.
        """
        self._should_required = 'should' in commandline_args

        super(network_WiFi_BluetoothLoadPerf,
              self).parse_additional_arguments(commandline_args)

        self._ap_configs, self._use_iperf = additional_params

    def verify_wifi_tput_drop_rate_result(self, result_drop,
                                          should_expected_drop,
                                          must_expected_drop, test_type,
                                          failed_test_types, ap_config_tag,
                                          bt_tag):
        """Verifies that performance test meets MUST and SHOULD drop rates.

        @param result_drop: The drop rate result object.
        @param should_expected_drop: The max SHOULD be expected drop rate.
        @param must_expected_drop: The max MUST be expected drop rate.
        @param test_type: The performance test type.
        @param failed_test_types: A set of failed test_types.
        @param ap_config_tag: String for AP configuration.
        @param bt_tag: String for BT operation.
        """
        # Initialize list to store failed test types.
        failed_test_type_list = []

        # Checks if the actual drop rate exceeds the MUST expected drop rate.
        if result_drop > must_expected_drop:
            logging.error(
                    'Tput drop rate is too big for test_type: %s, '
                    'bt_status: %s. Expected (must drop rate) %d %%, '
                    'got %d.', test_type, bt_tag, must_expected_drop,
                    result_drop)
            # Appends failed test type information to the list.
            failed_test_type_list.append('[test_type=%s, ap_config_tag=%s, '
                                         'bt_tag=%s, actual_drop=%d, '
                                         'must_expected_drop_failed=%d]' %
                                         (test_type, ap_config_tag, bt_tag,
                                          result_drop, must_expected_drop))

        # Checks if the actual drop rate exceeds the SHOULD expected drop rate.
        if result_drop > should_expected_drop:
            # Checks if the SHOULD drop rate is required.
            if self._should_required:
                logging.error(
                        'Tput drop rate is too big for test_type: %s, '
                        'bt_status: %s. Expected (should drop rate) %d'
                        '%%, got %d.', test_type, bt_tag, should_expected_drop,
                        result_drop)
                # Appends failed test type information to the list.
                failed_test_type_list.append(
                        '[test_type=%s, ap_config_tag=%s,'
                        ' bt_tag=%s, actual_drop=%d, '
                        'should_expected_drop_failed=%d]' %
                        (test_type, ap_config_tag, bt_tag, result_drop,
                         should_expected_drop))
            else:
                logging.info(
                        'Tput drop rate is bigger than expectation for '
                        'test_type: %s, bt_status: %s. Expected '
                        '(should drop rate) %d %%, got %d.', test_type, bt_tag,
                        should_expected_drop, result_drop)

        if len(failed_test_type_list) != 0:
            # Adds failed test type information to the set of failed
            # test types.
            failed_test_types.add(', '.join(failed_test_type_list))

    def verify_wifi_tput_result(self, actual_tput, expected_should_tput,
                                expected_must_tput, test_type,
                                failed_test_types, ap_config_tag, bt_tag):
        """Verifies that performance test meets MUST and SHOULD throughput.

        @param actual_tput: The actual throughput result.
        @param expected_should_tput: The min SHOULD expect throughput.
        @param expected_must_tput: The min MUST expect throughput.
        @param test_type: The performance test type.
        @param failed_test_types: A set of failed test_types.
        @param ap_config_tag: String for AP configuration.
        @param bt_tag: String for BT operation.
        """
        # Initialize list to store failed test types.
        failed_test_type_list = []

        # Rounds the actual throughput value to two decimal places.
        actual_tput = round(actual_tput, 2)

        # Checks if the actual throughput is below the expected MUST
        # throughput.
        if actual_tput < expected_must_tput:
            logging.error(
                    'Throughput is too low for test_type: %s, '
                    'bt_status: %s. Expected (must) %0.2f Mbps, '
                    'got %0.2f.', test_type, bt_tag, expected_must_tput,
                    actual_tput)
            # Appends failed test type information to the list.
            failed_test_type_list.append('[test_type=%s, ap_config_tag=%s, '
                                         'bt_tag=%s, measured_Tput=%0.2f, '
                                         'must_expected_Tput_failed=%0.2f]' %
                                         (test_type, ap_config_tag, bt_tag,
                                          actual_tput, expected_must_tput))

        # Checks if the actual throughput is below the expected SHOULD
        # throughput.
        if actual_tput < expected_should_tput:
            # Checks if the SHOULD throughput is required.
            if self._should_required:
                logging.error(
                        'Throughput is too low for test_type: %s, '
                        'bt_status: %s. Expected (should) %0.2f Mbps, '
                        'got %0.2f.', test_type, bt_tag, expected_should_tput,
                        actual_tput)
                # Appends failed test type information to the list.
                failed_test_type_list.append(
                        '[test_type=%s, ap_config_tag=%s, '
                        'bt_tag=%s, measured_Tput=%0.2f, '
                        'should_expected_Tput_failed=%0.2f]' %
                        (test_type, ap_config_tag, bt_tag, actual_tput,
                         expected_should_tput))
            else:
                logging.info(
                        'Throughput is below (should) expectation for '
                        'test_type: %s, bt_status: %s. Expected (should) '
                        '%0.2f Mbps, got %0.2f.', test_type, bt_tag,
                        expected_should_tput, actual_tput)

        if len(failed_test_type_list) != 0:
            # Adds failed test type information to the set of failed test
            # types.
            failed_test_types.add(', '.join(failed_test_type_list))

    def verify_wifi_latency_result(self, actual_latency, expected_latency,
                                   test_type, failed_test_types, ap_config_tag,
                                   bt_tag):
        """Verifies that performance test result passes the latency requirement.

        @param actual_latency: The actual latency result.
        @param expected_latency: The expected latency result.
        @param test_type: The performance test type.
        @param failed_test_types: A set of failed test_types.
        @param ap_config_tag: String for AP configuration.
        @param bt_tag: String for BT operation.
        """
        # Rounds the actual latency value to two decimal places.
        actual_latency = round(actual_latency, 2)

        if actual_latency > expected_latency:
            logging.error(
                    'Latency value is too big for %s. Expected (latency)'
                    ' %0.2f, got %0.2f.', test_type, expected_latency,
                    actual_latency)

            failed_test_type_list = [
                    '[test_type=%s' % test_type,
                    'ap_config_tag=%s' % ap_config_tag,
                    'bt_tag=%s' % bt_tag,
                    'latency=%0.2f' % actual_latency,
                    'expected_latency_failed=%0.2f' % expected_latency,
            ]
            failed_test_types.add(', '.join(failed_test_type_list) + ']')

    def prepare_bt_device(self, device):
        """Pairs the hid device pre-test to simplify later re-connection.

        @param device: The BT peer device.
        """
        self.test_device_set_discoverable(device, True)
        self.test_discover_device(device.address)
        self.test_pairing(device.address, device.pin, trusted=True)
        self.test_disconnection_by_device(device)

    def do_mouse_click_load_test(self, device):
        """Runs the body of the mouse load test.

        @param device: The BT peer device.
        """
        self.test_continuous_mouse_left_click(
                device=device,
                num_clicks=self.DEFAULT_BT_TOTAL_CLICK,
                delay=self.DEFAULT_BT_CLICK_DELAY)

    def do_keyboard_load_test(self, device):
        """Runs the body of the keyboard load test.

        @param device: The BT peer device.
        """
        self.test_keyboard_input_from_string(
                device=device,
                string_to_send=self.INPUT_STRING,
                delay=self.DEFAULT_DELAY_BETWEEN_KEYSTROKES)

    def get_device_load(self, device_type):
        """Helper function to get load method based on input device type.

        @param device_type: The BT peer device type.
        """
        if device_type == 'MOUSE':
            return self.do_mouse_click_load_test
        elif device_type == 'KEYBOARD':
            return self.do_keyboard_load_test
        else:
            raise error.TestError('Failed to find load method for device type '
                                  '%s' % device_type)

    def run_tests_with_ip_configuration(self):
        """Configures IP settings and run tests.

        Brings interfaces up, assign IP addresses and add routes.
        Runs the test for all provided AP configs.
        """
        failed_performance_tests = set()

        for ap_config in self._ap_configs:
            # Sets up the router and associate the client with it.
            self.configure_and_connect_to_ap(ap_config)

            manager = perf_manager.PerfTestManager(self._use_iperf)

            # Executes the performance test and log the test types that failed
            # due to low throughput, high drop rate or high latency.
            failed_performance_tests.update(self.do_run(ap_config, manager))

            # Cleans up the router and client state for the next run.
            self.context.client.shill.disconnect(
                    self.context.router.get_ssid())
            self.context.router.deconfig()

        return failed_performance_tests

    def setup_and_run_tests(self):
        """Configures environment, pairs devices, sets IP, runs tests."""

        for device in self.bt_devices:
            self.prepare_bt_device(device)

        failed_perf_tests = self.run_tests_with_ip_configuration()

        if len(failed_perf_tests) != 0:
            failed_perf_tests = list(failed_perf_tests)
            raise error.TestFail('The test type(s) failed due to: %s' %
                                 ', '.join(failed_perf_tests))

    def test_one(self, manager, session, config, test_type, failed_test_types,
                 ap_config, ap_config_tag, bt_tag):
        """Runs one iteration of Wi-Fi testing.

        @param manager: A PerfTestManager instance.
        @param session: IperfSession session.
        @param config: PerfConfig config.
        @param test_type: The performance test type.
        @param failed_test_types: A set of failed test_types.
        @param ap_config: The AP configuration.
        @param ap_config_tag: String for AP configuration.
        @param bt_tag: String for BT operation.
        """
        get_ping_config = lambda period: ping_runner.PingConfig(
                self.context.get_wifi_addr(),
                interval=0.01,
                count=period,
                source_iface=self.context.client.wifi_if)

        logging.info('testing config %s, ap_config %s, BT:%s', test_type,
                     ap_config_tag, bt_tag)
        test_str = "_".join([ap_config_tag, bt_tag])
        time.sleep(1)

        # Records the signal level.
        signal_level = self.context.client.wifi_signal_level
        signal_description = '_'.join(['signal', test_str])
        self.write_perf_keyval({signal_description: signal_level})

        # Runs the iperf tool and log the results.
        results = session.run(config)
        if not results:
            logging.error('Failed to take measurement for %s',
                          config.test_type)
            return
        values = [result.throughput for result in results]
        self.output_perf_value(
                config.test_type + '_' + bt_tag,
                values,
                units='Mbps',
                higher_is_better=True,
                graph=ap_config_tag,
        )
        result = manager.get_result(results, config)
        self.write_perf_keyval(
                result.get_keyval(
                        prefix='_'.join([config.test_type, test_str])))

        # Logs the standard deviation.
        throughput_dev = result.throughput_dev
        self.output_perf_value(
                config.test_type + '_' + bt_tag + '_dev',
                throughput_dev,
                units='Mbps',
                higher_is_better=False,
                graph=ap_config_tag + '_dev',
        )
        self.write_perf_keyval({
                '_'.join([config.test_type, test_str, 'dev']):
                throughput_dev
        })

        # Logs the drop in throughput compared with the 'BT_disconnected'
        # baseline. Only positive values are valid. Report the drop as a
        # whole integer percentage of (base_through-through)/base_through.
        if bt_tag == self.CONNECTION_STATE_DISCONNECTED:
            self.base_through = result.throughput

        elif self.base_through > 0:
            test_name = self.test_name.lower().replace(' ', '_')
            expected_drop = (
                    expected_perf_data.get_expected_wifi_throughput_drop_rate(
                            test_type, test_name, ap_config, bt_tag))
            expected_tput = (expected_perf_data.get_expected_wifi_throughput(
                    test_type, test_name, ap_config, bt_tag))

            drop = int((self.base_through - result.throughput) * 100 /
                       self.base_through)
            logging.info('logging drop value as %d%%', drop)
            self.output_perf_value(
                    test_type + '_' + bt_tag + '_drop',
                    drop,
                    units='percent_drop',
                    higher_is_better=False,
                    graph=ap_config_tag + '_drop',
            )

            self.verify_wifi_tput_drop_rate_result(drop, expected_drop[0],
                                                   expected_drop[1], test_type,
                                                   failed_test_types,
                                                   ap_config_tag, bt_tag)

            self.verify_wifi_tput_result(result.throughput, expected_tput[0],
                                         expected_tput[1], test_type,
                                         failed_test_types, ap_config_tag,
                                         bt_tag)
            self.write_perf_keyval(
                    {'_'.join([config.test_type, test_str, 'drop']): drop})

            # Tests latency with ping.
            result_ping = self.context.client.ping(get_ping_config(3))
            self.write_perf_keyval(
                    {'_'.join(['ping', test_str]): result_ping.avg_latency})
            logging.info('Ping statistics with %s: %r', bt_tag, result_ping)
            expected_latency = (expected_perf_data.get_expected_wifi_latency(
                    test_type, test_name, ap_config, bt_tag))

            self.verify_wifi_latency_result(result_ping.avg_latency,
                                            expected_latency, test_type,
                                            failed_test_types, ap_config_tag,
                                            bt_tag)

        return failed_test_types

    def test_bt_device_connection(self):
        """Tests the connection of BT devices."""
        for device in self.bt_devices:
            self.test_connection_by_device(device)

            # Ensure HID device creation before further testing.
            self.ensure_hid_device_creation(device)

    def test_bt_device_disconnection(self):
        """Tests the disconnection of BT devices."""
        for device in self.bt_devices:
            self.test_disconnection_by_device(device)

    def do_run(self, ap_config, manager):
        """Runs a single set of perf tests, for a given AP and DUT config.

        @param ap_config: The AP configuration that is being used.
        @param manager: A PerfTestManager instance.

        @return: Set of failed configs.
        """
        failed_test_types = set()

        ap_config_tag = ap_config.perf_loggable_description

        # Iterates over each type of performance test.
        for test_type in self.PERF_TEST_TYPES:
            config = manager.get_config(test_type, self._is_openwrt)

            session = manager.get_session(test_type, self.context.client,
                                          self.context.router)

            # Performs the test without any BT connection.
            self.test_one(manager, session, config, test_type, None, ap_config,
                          ap_config_tag, self.CONNECTION_STATE_DISCONNECTED)

            # Tests Bluetooth device connection.
            self.test_bt_device_connection()

            # Performs the test after BT connection and update the failed test
            # types.
            failed_test_types.update(
                    self.test_one(manager, session, config, test_type,
                                  failed_test_types, ap_config, ap_config_tag,
                                  self.CONNECTION_STATE_CONNECTED))

            # List to hold the load device and its load test.
            devices_load_tests = []
            for device in self.bt_devices:
                # Assigns the appropriate load tests method based on the device
                # type.
                devices_load_tests.append(
                        (device, self.get_device_load(device.device_type)))

            # List to hold the load test threads.
            load_test_threads = []
            for device, load_test_name in devices_load_tests:
                # Starts applying test load in background for each device.
                load_test_thread = threading.Thread(target=load_test_name,
                                                    args=(device, ))
                load_test_thread.start()
                load_test_threads.append(load_test_thread)

            # Performs the test with BT load and update the failed test types.
            failed_test_types.update(
                    self.test_one(manager, session, config, test_type,
                                  failed_test_types, ap_config, ap_config_tag,
                                  self.CONNECTION_STATE_WITH_LOAD))

            # Waits for all load test threads to complete.
            for load_test_thread in load_test_threads:
                load_test_thread.join()

            # Tests Bluetooth device disconnection.
            self.test_bt_device_disconnection()

            # Performs the test after BT disconnection and update the failed
            # test types.
            failed_test_types.update(
                    self.test_one(manager, session, config, test_type,
                                  failed_test_types, ap_config, ap_config_tag,
                                  self.CONNECTION_STATE_DISCONNECTED_AGAIN))

        return failed_test_types

    @test_wrapper('Coex test with mouse click load',
                  devices={'MOUSE': 1},
                  supports_floss=True)
    def mouse_load(self):
        """Tests Wi-Fi BT coex with click mouse load."""
        self.bt_devices = [self.devices['MOUSE'][0]]
        self.setup_and_run_tests()

    @test_wrapper('Coex test with keyboard load',
                  devices={'KEYBOARD': 1},
                  supports_floss=True)
    def keyboard_load(self):
        """Tests Wi-Fi BT coex with keyboard load."""
        self.bt_devices = [self.devices['KEYBOARD'][0]]
        self.setup_and_run_tests()

    @test_wrapper('Coex test with BLE mouse click load',
                  devices={'BLE_MOUSE': 1},
                  supports_floss=True)
    def ble_mouse_load(self):
        """Tests Wi-Fi BT coex with click BLE mouse load."""
        self.bt_devices = [self.devices['BLE_MOUSE'][0]]
        self.setup_and_run_tests()

    @batch_wrapper('Bluetooth Load/Wi-Fi Coex Test Batch')
    def coex_health_batch_run(self, num_iterations=1, test_name=None):
        """Runs Bluetooth Load/Wi-Fi coex health test batch or specific test.

        @param num_iterations: How many iterations to run.
        @param test_name: Specific test to run otherwise None to run the whole
                          batch.
        """
        self.mouse_load()
        self.keyboard_load()
        self.ble_mouse_load()

    def run_once(self,
                 host,
                 num_iterations=1,
                 peer_required=True,
                 args_dict=None,
                 test_name=None,
                 flag='Quick Health',
                 floss=False):
        """Runs the batch of Bluetooth Load Wi-Fi coex health tests.

        @param host: The DUT, usually a chromebook.
        @param num_iterations: The number of rounds to execute the test.
        @param peer_required: Whether a btpeer is required.
        @param args_dict: Additional arguments to be passed to the test
                          function.
        @param test_name: A single test to run or leave None to run the batch.
        @param flag: Run 'Quick Health' tests or 'AVL' tests.
        @param floss: Enable Floss.
        """
        # Initialize and run the test batch or the requested specific test.
        self.quick_test_init(host,
                             use_btpeer=peer_required,
                             flag=flag,
                             start_browser=False,
                             args_dict=args_dict,
                             floss=floss)
        self.test_name = test_name
        self.coex_health_batch_run(num_iterations, test_name)
        self.quick_test_cleanup()
