# Lint as: python2, python3
# Copyright 2013 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import logging
import time

from autotest_lib.client.common_lib import error
from autotest_lib.client.common_lib.cros.network import interface
from autotest_lib.server.cros.network import expected_performance_results
from autotest_lib.server.cros.network import perf_test_manager as perf_manager
from autotest_lib.server.cros.network import wifi_cell_perf_test_base
from autotest_lib.server.cros.network import perf_monitor_service


class network_WiFi_Perf(wifi_cell_perf_test_base.WiFiCellPerfTestBase):
    """Test maximal achievable bandwidth on several channels per band.

    Conducts a performance test for a set of specified router configurations
    and reports results as keyval pairs.

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
        self._should_required = 'should' in commandline_args

        super(network_WiFi_Perf, self).parse_additional_arguments(
                commandline_args)

        self._ap_configs, self._use_iperf = additional_params

    def verify_result(self, result, must_expected_throughput,
                      should_expected_throughput, test_type, failed_test_types,
                      power_save, ap_config):
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
        must_tput_failed = False
        should_tput_failed = False

        # If the must requirement is greater than our maximum expecation for a
        # board, use the maximum expectation instead of the must requirement.
        board_max_expectation = expected_performance_results.get_board_max_expectation(
                test_type, self.context.client.board)
        if board_max_expectation and board_max_expectation < must_expected_throughput:
            must_expected_throughput = board_max_expectation

        if result.throughput < must_expected_throughput:
            logging.error(
                    'Throughput is too low for %s. Expected (must) %0.2f Mbps, got %0.2f.',
                    test_type, must_expected_throughput, result.throughput)
            must_tput_failed = True
        if result.throughput < should_expected_throughput:
            if self._should_required:
                logging.error(
                        'Throughput is too low for %s. Expected (should) %0.2f Mbps, got %0.2f.',
                        test_type, should_expected_throughput,
                        result.throughput)
                should_tput_failed = True
            else:
                logging.info(
                        'Throughput is below (should) expectation for %s. Expected (should) %0.2f Mbps, got %0.2f.',
                        test_type, should_expected_throughput,
                        result.throughput)
        if must_tput_failed or should_tput_failed:
            failed_test_type_list = [
                    '[test_type=%s' % test_type,
                    'channel=%d' % ap_config.channel,
                    'power_save_on=%r' % power_save,
                    'measured_Tput=%0.2f' % result.throughput
            ]
            if must_tput_failed:
                failed_test_type_list.append(
                        'must_expected_Tput_failed=%0.2f' %
                        must_expected_throughput)
            elif should_tput_failed:
                failed_test_type_list.append(
                        'should_expected_Tput_failed=%0.2f' %
                        should_expected_throughput)
            failed_test_types.add(', '.join(failed_test_type_list) + ']')

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
        signal_level = self.context.client.wifi_signal_level
        signal_description = '_'.join([ap_config_tag, 'signal'])
        self.write_perf_keyval({signal_description: signal_level})
        for test_type in self.PERF_TEST_TYPES:
            config = manager.get_config(test_type)
            pcap_lan_iface = interface.Interface(self._pcap_lan_iface_name,
                                                 self.context.pcap_host.host)
            session = manager.get_session(test_type,
                                          self.context.client,
                                          self.context.pcap_host,
                                          peer_device_interface=pcap_lan_iface)
            ch_width = ap_config.channel_width
            if ch_width is None:
                raise error.TestFail(
                        'Failed to get the channel width used by the AP and client'
                )
            expected_throughput = expected_performance_results.get_expected_throughput_wifi(
                    test_type, ap_config.mode, ch_width)
            results = session.run(config)
            if not results:
                logging.error('Failed to take measurement for %s', test_type)
                continue

            values = [sample.throughput for sample in results]
            self.output_perf_value(test_type,
                                   values,
                                   units='Mbps',
                                   higher_is_better=True,
                                   graph=ap_config_tag)
            result = manager.get_result(results)
            self.verify_result(result, expected_throughput[0],
                               expected_throughput[1], test_type,
                               failed_test_types, power_save, ap_config)
            self.write_perf_keyval(
                    result.get_keyval(
                            prefix='_'.join([ap_config_tag, test_type])))

            # Log the standard deviation
            throughput_dev = result.throughput_dev
            self.output_perf_value(test_type + '_dev',
                                   throughput_dev,
                                   units='Mbps',
                                   higher_is_better=False,
                                   graph=ap_config_tag + '_dev')
            self.write_perf_keyval(
                {'_'.join([ap_config_tag, test_type, 'dev']): throughput_dev})

        if governor:
            self.restore_scaling_governors()

        return failed_test_types


    def run_once(self):
        """Test body."""
        start_time = time.time()

        perf_monitor = perf_monitor_service.PerfMonitorService(self.context.client.host)
        perf_monitor.start_monitoring_throughput()

        low_throughput_tests = self.configure_and_run_tests()

        perf_monitor.stop_monitoring_throughput()

        end_time = time.time()
        logging.info('Running time %0.1f seconds.', end_time - start_time)
        if len(low_throughput_tests) != 0:
            low_throughput_tags = list(low_throughput_tests)
            raise error.TestFail(
                    'Throughput performance too low for test type(s): %s' %
                    ', '.join(low_throughput_tags))
