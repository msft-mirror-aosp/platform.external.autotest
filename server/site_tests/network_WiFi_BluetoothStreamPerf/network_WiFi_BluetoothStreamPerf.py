# Lint as: python2, python3
# Copyright 2015 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
import logging
import threading
import time

from autotest_lib.client.common_lib import error
from autotest_lib.client.common_lib.cros.network import interface
from autotest_lib.server.cros.network import expected_performance_results
from autotest_lib.client.common_lib.cros.network import ping_runner
from autotest_lib.server.cros.network import perf_test_manager as perf_manager
from autotest_lib.server.cros.network import wifi_cell_perf_test_base

from autotest_lib.server.cros.bluetooth.bluetooth_adapter_quick_tests import \
     BluetoothAdapterQuickTests
from autotest_lib.server.cros.bluetooth.bluetooth_adapter_audio_tests import \
     BluetoothAdapterAudioTests
from autotest_lib.client.cros.bluetooth.bluetooth_audio_test_data import A2DP


class network_WiFi_BluetoothStreamPerf(
        wifi_cell_perf_test_base.WiFiCellPerfTestBase,
        BluetoothAdapterQuickTests, BluetoothAdapterAudioTests):
    """Test maximal achievable bandwidth on several channels per band.

    Conducts a performance test for a set of specified router configurations
    and reports results as keyval pairs.

    """

    test_wrapper = BluetoothAdapterQuickTests.quick_test_test_decorator
    batch_wrapper = BluetoothAdapterQuickTests.quick_test_batch_decorator

    version = 1

    PERF_TEST_TYPES = [
            perf_manager.PerfTestTypes.TEST_TYPE_TCP_TX,
            perf_manager.PerfTestTypes.TEST_TYPE_TCP_RX,
            perf_manager.PerfTestTypes.TEST_TYPE_TCP_BIDIRECTIONAL,
            perf_manager.PerfTestTypes.TEST_TYPE_UDP_TX,
            # TODO(b:251380100): investigate unstable results for UDP_RX
            # perf_manager.PerfTestTypes.TEST_TYPE_UDP_RX,
            perf_manager.PerfTestTypes.TEST_TYPE_UDP_BIDIRECTIONAL,
    ]

    BT_STREAMING_DURATION = 60

    def parse_additional_arguments(self, commandline_args, additional_params):
        """Hook into super class to take control files parameters.

        @param commandline_args dict of parsed parameters from the autotest.
        @param additional_params list of HostapConfig objects.

        """
        self._should_required = 'should' in commandline_args

        super(network_WiFi_BluetoothStreamPerf, self).parse_additional_arguments(
                commandline_args)

        self._ap_configs, self._use_iperf = additional_params

    def verify_result(self, result_drop, should_expected_drop,
                      must_expected_drop, test_type, failed_test_types,
                      ap_config_tag):
        """Verfiy that performance test result passes the must and should
        throughput requirements.

        @param result: the throughput result object
        @param must_expected_throughput: the min must expected throughput
        @param should_expected_throughput: the min should expected throughput
        @param test_type: the performance_test_types test type
        @param failed_test_types: a set of failed test_types
        @param power_save: powersaving configuration
        @param ap_config: the AP configuration
        """
        must_drop_failed = False
        should_drop_failed = False

        if result_drop > must_expected_drop:
            logging.error(
                    'Throughput drop is too big for %s. Expected (must) %d %%, got %d.',
                    test_type, must_expected_drop, result_drop)
            must_drop_failed = True
        if result_drop > should_expected_drop:
            if self._should_required:
                logging.error(
                        'Throughput drop is too big for %s. Expected (should) %d %%, got %d.',
                        test_type, should_expected_drop,
                        result_drop)
                should_drop_failed = True
            else:
                logging.info(
                        'Throughput drop is bigger then expectation for %s. Expected (should) %d %%, got %d.',
                        test_type, should_expected_drop,
                        result_drop)
        if must_drop_failed or should_drop_failed:
            failed_test_type_list = [
                    '[test_type=%s' % test_type,
                    'ap_config_tag=%s' % ap_config_tag,
                    'measured_drop=%d' % result_drop
            ]
            if must_drop_failed:
                failed_test_type_list.append(
                        'must_expected_drop_failed=%d' %
                        must_expected_drop)
            elif should_drop_failed:
                failed_test_type_list.append(
                        'should_expected_drop_failed=%d' %
                        should_expected_drop)
            failed_test_types.add(', '.join(failed_test_type_list) + ']')

    def test_one(self, manager, session, config, test_type, failed_test_types, ap_config, ap_config_tag, bt_tag):
        """Run one iteration of wifi testing.

        @param manager: a PerfTestManager instance
        @param session: NetperfSession or IperfSession session
        @param config: NetperfConfig or IperfConfig config
        @param test_type: the performance_test_types test type
        @param failed_test_types: a set of failed test_types
        @param ap_config: the AP configuration
        @param ap_config_tag: string for AP configuration
        @param bt_tag: string for BT operation

        """
        get_ping_config = lambda period: ping_runner.PingConfig(
                self.context.get_wifi_addr(),
                interval=1,
                count=period,
                source_iface=self.context.client.wifi_if)

        logging.info('testing config %s, ap_config %s, BT:%s',
                     test_type, ap_config_tag, bt_tag)
        test_str = '_'.join([ap_config_tag, bt_tag])
        time.sleep(1)

        # Record the signal level.
        signal_level = self.context.client.wifi_signal_level
        signal_description = '_'.join(['signal', test_str])
        self.write_perf_keyval({signal_description: signal_level})

        # Run perf tool and log the results.
        results = session.run(config)
        if not results:
            logging.error('Failed to take measurement for %s',
                          config.test_type)
            return
        values = [result.throughput for result in results]
        self.output_perf_value(config.test_type + '_' + bt_tag,
                               values,
                               units='Mbps',
                               higher_is_better=True,
                               graph=ap_config_tag)
        result = manager.get_result(results)
        self.write_perf_keyval(
                result.get_keyval(
                        prefix='_'.join([config.test_type, test_str])))

        # Log the drop in throughput compared with the 'BT_disconnected'
        # baseline. Only positive values are valid. Report the drop as a
        # whole integer percentage of (base_through-through)/base_through.
        if bt_tag == BluetoothAdapterAudioTests.CONNECTION_STATE_DISCONNECTED:
            self.base_through = result.throughput
        elif self.base_through > 0:
            expected_drop = expected_performance_results.get_expected_wifibt_coex_throughput_drop(
                    test_type, ap_config, bt_tag)
            drop = int( (self.base_through - result.throughput) * 100 /
                        self.base_through)
            self.output_perf_value(test_type + '_' + bt_tag + '_drop',
                                   drop,
                                   units='percent_drop',
                                   higher_is_better=False,
                                   graph=ap_config_tag + '_drop')
            self.verify_result(drop, expected_drop[0],
                               expected_drop[1], test_type,
                               failed_test_types, ap_config_tag)
            self.write_perf_keyval(
                    {'_'.join([config.test_type, test_str, 'drop']): drop})
            logging.info('logging drop value as %d%%', drop)

        # Test latency with ping.
        result_ping = self.context.client.ping(get_ping_config(3))
        self.write_perf_keyval(
            { '_'.join(['ping', test_str]): result_ping.avg_latency })
        logging.info('Ping statistics with %s: %r', bt_tag, result_ping)

        return failed_test_types

    def pair_audio_device(self, device):
        """Pair an audio device pre-test to simplify later re-connection"""
        self.test_device_set_discoverable(device, True)
        self.test_discover_device(device.address)
        self.test_pairing(device.address, device.pin, trusted=True)
        device.SetTrustedByRemoteAddress(self.bluetooth_facade.address)
        self.test_disconnection_by_adapter(device.address)

    def do_audio_test(self, device):
        """Run the body of the audio test"""
        self.test_a2dp_sinewaves(device, A2DP, self.BT_STREAMING_DURATION)

    def do_run(self, ap_config, manager, power_save, governor):
        """Run a single set of perf tests, for a given AP and DUT config.

        @param ap_config: the AP configuration that is being used
        @param manager: a PerfTestManager instance
        @param power_save: whether or not to use power-save mode on the DUT
                           (boolean)
        @ return set of failed configs
        """
        governor_name = self.setup_governor(governor)
        # If CPU governor is already set to self._governor, don't
        # perform the run twice
        if governor_name == self._governor:
            return

        failed_test_types = set()

        self.context.client.powersave_switch(power_save)
        ps_tag = 'PS%s' % ('on' if power_save else 'off')
        governor_tag = 'governor-%s' % governor_name
        ap_config_tag = '_'.join([ap_config.perf_loggable_description,
                                  ps_tag, governor_tag])

        device = self.bt_device

        for test_type in self.PERF_TEST_TYPES:
            config = manager.get_config(test_type)
            pcap_lan_iface = interface.Interface(self._pcap_lan_iface_name,
                                                 self.context.pcap_host.host)
            session = manager.get_session(test_type,
                                          self.context.client,
                                          self.context.pcap_host,
                                          peer_device_interface=pcap_lan_iface)

            session.MEASUREMENT_MAX_SAMPLES = int(self.BT_STREAMING_DURATION / 10)

            self.base_through = 0
            self.test_one(
                    manager, session, config, test_type, None, ap_config,
                    ap_config_tag,
                    BluetoothAdapterAudioTests.CONNECTION_STATE_DISCONNECTED)

            self.test_connection_by_device(device)
            failed_test_types.update(
                    self.test_one(
                            manager, session, config, test_type,
                            failed_test_types, ap_config, ap_config_tag,
                            BluetoothAdapterAudioTests.CONNECTION_STATE_CONNECTED))

            # Start playing audio in background
            audio_thread = threading.Thread(target=self.do_audio_test,
                                            args=(device, ))
            audio_thread.start()
            failed_test_types.update(
                    self.test_one(
                            manager, session, config, test_type,
                            failed_test_types, ap_config, ap_config_tag,
                            BluetoothAdapterAudioTests.CONNECTION_STATE_STREAMING))

            # Wait for audio thread to complete
            audio_thread.join()

            self.test_disconnection_by_adapter(device.address)
            failed_test_types.update(
                    self.test_one(
                            manager, session, config, test_type,
                            failed_test_types, ap_config, ap_config_tag,
                            BluetoothAdapterAudioTests.CONNECTION_STATE_DISCONNECTED_AGAIN))

        if governor:
            self.restore_scaling_governors()

        return failed_test_types

    @test_wrapper('Coex tests', devices={'BLUETOOTH_AUDIO': 1})
    def coex_test(self):
        """Test body."""
        start_time = time.time()
        self.bt_device = self.devices['BLUETOOTH_AUDIO'][0]
        self.initialize_bluetooth_audio(self.bt_device, A2DP)
        self.pair_audio_device(self.bt_device)

        high_drop_tests = self.configure_and_run_tests()

        self.cleanup_bluetooth_audio(self.bt_device, A2DP)
        end_time = time.time()
        logging.info('Running time %0.1f seconds.', end_time - start_time)
        if len(high_drop_tests) != 0:
            high_drop_tags = list(high_drop_tests)
            raise error.TestFail(
                    'Throughput drop level too high for test type(s): %s' %
                    ', '.join(high_drop_tags))

    @batch_wrapper('Coex batch')
    def coex_health_batch_run(self, num_iterations=1, test_name=None):
        """Run the bluetooth coex health test batch or a specific given test.

        @param num_iterations: how many iterations to run
        @param test_name: specific test to run otherwise None to run the
                whole batch
        """
        self.coex_test()

    def run_once(self, host, test_name=None, args_dict=None):
        self.host = host

        self.quick_test_init(host, use_btpeer=True, args_dict=args_dict)
        self.coex_health_batch_run(test_name=test_name)
        self.quick_test_cleanup()
