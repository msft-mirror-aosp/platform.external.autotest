# Lint as: python2, python3
# Copyright 2015 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import logging
import time


from autotest_lib.client.common_lib import error
from autotest_lib.client.common_lib.cros.network import ping_runner
from autotest_lib.server.cros.network import perf_test_manager as perf_manager
from autotest_lib.server.cros.network import wifi_cell_perf_test_base
from autotest_lib.server.cros.bluetooth import bluetooth_device
from autotest_lib.server.cros.bluetooth.bluetooth_adapter_audio_tests import \
        BluetoothAdapterAudioTests

class network_WiFi_BluetoothScanPerf(
        wifi_cell_perf_test_base.WiFiCellPerfTestBase):
    """Test the effect of bluetooth scanning on wifi performance.

    Conducts a performance test for a set of specified router configurations
    while scanning for bluetooth devices and reports results as keyval pairs.

    """

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
        super(network_WiFi_BluetoothScanPerf, self).parse_additional_arguments(
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

        signal_level = self.context.client.wifi_signal_level
        signal_description = '_'.join(['signal', test_str])
        self.write_perf_keyval({signal_description: signal_level})

        results = session.run(config)
        if not results:
            logging.error('Failed to take measurement for %s',
                          config.test_type)
            return
        values = [result.throughput for result in results]
        self.output_perf_value(config.test_type + ' ' + bt_tag,
                               values,
                               units='Mbps',
                               higher_is_better=True,
                               graph=ap_config_tag)
        result = manager.get_result(results)
        self.write_perf_keyval(
                result.get_keyval(
                        prefix='_'.join([config.test_type, test_str])))

        # Test latency with ping.
        result_ping = self.context.client.ping(get_ping_config(3))
        self.write_perf_keyval(
            { '_'.join(['ping', test_str]): result_ping.avg_latency })
        logging.info('Ping statistics with %s: %r', bt_tag, result_ping)



    def run_once(self, host):
        """Test body."""
        start_time = time.time()

        # Prepare Bluetooth to scan, but do not start yet.
        bt_device = bluetooth_device.BluetoothDevice(host)
        if not bt_device.reset_on():
            raise error.TestFail('DUT could not be reset to initial state')

        for ap_config in self._ap_configs:
            # Set up the router and associate the client with it.
            self.configure_and_connect_to_ap(ap_config)

            manager = perf_manager.PerfTestManager(self._use_iperf)

            ap_config_tag = ap_config.perf_loggable_description

            for test_type in self.PERF_TEST_TYPES:
                config = manager.get_config(test_type)

                session = manager.get_session(test_type, self.context.client,
                                              self.context.router)

                self.test_one(
                        manager, session, config, ap_config_tag,
                        BluetoothAdapterAudioTests.CONNECTION_STATE_QUIET)
                if not bt_device.start_discovery()[0]:
                    raise error.TestFail('Could not start discovery on DUT')
                try:
                    self.test_one(
                            manager, session, config, ap_config_tag,
                            BluetoothAdapterAudioTests.CONNECTION_STATE_SCANNING)
                finally:
                    if not bt_device.stop_discovery()[0]:
                        logging.warning('Failed to stop discovery on DUT')
                self.test_one(
                        manager, session, config, ap_config_tag,
                        BluetoothAdapterAudioTests.CONNECTION_STATE_QUIET_AGAIN)

            # Clean up router and client state for the next run.
            self.context.client.shill.disconnect(self.context.router.get_ssid())
            self.context.router.deconfig()

        end_time = time.time()
        logging.info('Running time %0.1f seconds.', end_time - start_time)
