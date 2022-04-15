# Lint as: python2, python3
# Copyright 2015 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
import logging
import threading
import time

from autotest_lib.client.common_lib.cros.network import interface
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
            perf_manager.PerfTestTypes.TEST_TYPE_UDP_RX,
            perf_manager.PerfTestTypes.TEST_TYPE_UDP_BIDIRECTIONAL,
    ]

    def parse_additional_arguments(self, commandline_args, additional_params):
        """Hook into super class to take control files parameters.

        @param commandline_args dict of parsed parameters from the autotest.
        @param additional_params list of HostapConfig objects.

        """
        super(network_WiFi_BluetoothStreamPerf, self).parse_additional_arguments(
                commandline_args)

        self._ap_configs, self._use_iperf = additional_params

    def test_one(self, manager, session, config, ap_config_tag, bt_tag):
        """Run one iteration of wifi testing.

        @param manager: a PerfTestManager instance
        @param session NetperfSession or IperfSession session
        @param config NetperfConfig or IperfConfig config
        @param ap_config_tag string for AP configuration
        @param bt_tag string for BT operation

        """
        get_ping_config = lambda period: ping_runner.PingConfig(
                self.context.get_wifi_addr(),
                interval=1,
                count=period,
                source_iface=self.context.client.wifi_if)

        logging.info('testing config %s, ap_config %s, BT:%s',
                     config.test_type, ap_config_tag, bt_tag)
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
        # baseline.  Only positive values are valid.  Report the drop as a
        # whole integer percentage of (base_through-through)/base_through.
        if bt_tag == 'BT_disconnected':
            self.base_through = result.throughput
        elif self.base_through > 0:
            drop = int( (self.base_through - result.throughput) * 100 /
                        self.base_through)
            self.output_perf_value(config.test_type + '_' + bt_tag + '_drop',
                                   drop,
                                   units='percent_drop',
                                   higher_is_better=False,
                                   graph=ap_config_tag + '_drop')
            self.write_perf_keyval(
                    {'_'.join([config.test_type, test_str, 'drop']): drop})
            logging.info('logging drop value as %d%%', drop)

        # Test latency with ping.
        result_ping = self.context.client.ping(get_ping_config(3))
        self.write_perf_keyval(
            { '_'.join(['ping', test_str]): result_ping.avg_latency })
        logging.info('Ping statistics with %s: %r', bt_tag, result_ping)

    def pair_audio_device(self, device):
        """Pair an audio device pre-test to simplify later re-connection"""
        self.test_device_set_discoverable(device, True)
        self.test_discover_device(device.address)
        self.test_pairing(device.address, device.pin, trusted=True)
        device.SetTrustedByRemoteAddress(self.bluetooth_facade.address)
        self.test_disconnection_by_adapter(device.address)

    def do_audio_test(self, device):
        """Run the body of the audio test"""
        self.test_a2dp_sinewaves(device, A2DP, 60)

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

            session.MEASUREMENT_MAX_SAMPLES = 6.

            self.base_through = 0
            self.test_one(manager, session, config, ap_config_tag,
                            'BT_disconnected')

            self.test_connection_by_device(device)
            self.test_one(manager, session, config, ap_config_tag,
                            'BT_connected_but_not_streaming')

            # Start playing audio in background
            audio_thread = threading.Thread(target=self.do_audio_test,
                                            args=(device, ))
            audio_thread.start()
            self.test_one(manager, session, config, ap_config_tag,
                            'BT_streaming_audiofile')

            # Wait for audio thread to complete
            audio_thread.join()
            self.test_disconnection_by_adapter(device.address)
            self.test_one(manager, session, config, ap_config_tag,
                            'BT_disconnected_again')

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

        self.configure_and_run_tests()

        self.cleanup_bluetooth_audio(self.bt_device, A2DP)
        end_time = time.time()
        logging.info('Running time %0.1f seconds.', end_time - start_time)

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
