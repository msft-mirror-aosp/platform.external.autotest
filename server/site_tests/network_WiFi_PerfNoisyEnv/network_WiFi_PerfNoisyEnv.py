# Lint as: python2, python3
# Copyright (c) 2022 The Chromium OS Authors.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import logging
import os
import time

from autotest_lib.client.common_lib import error
from autotest_lib.server import site_linux_rpi
from autotest_lib.client.common_lib.cros.network import interface
from autotest_lib.server.cros.network import ip_config_context_manager
from autotest_lib.server.cros.network import hackrf_runner_context_manager
from autotest_lib.server.cros.network import perf_test_manager as perf_manager
from autotest_lib.server.cros.network import wifi_cell_perf_test_base


class network_WiFi_PerfNoisyEnv(wifi_cell_perf_test_base.WiFiCellPerfTestBase):
    """ Test maximal achievable bandwidth while varying the gain of noise and
    identify the gain at which a DUT disconnects.

    For a given router configuration, broadcast noise while the gain is
    increased step by step until the DUT disconnects or no throughput is
    detected. The throughput at different gain values and the maximum gain
    at which there were meaningful throughput values are logged.

    After running it on more boards to gather more data, this test will include
    pass/fail criteria.
    """
    version = 1

    PERF_TEST_TYPES = [
            perf_manager.PerfTestTypes.TEST_TYPE_TCP_TX,
            perf_manager.PerfTestTypes.TEST_TYPE_TCP_RX,
            perf_manager.PerfTestTypes.TEST_TYPE_UDP_TX,
            perf_manager.PerfTestTypes.TEST_TYPE_UDP_RX,
            perf_manager.PerfTestTypes.TEST_TYPE_TCP_BIDIRECTIONAL,
            perf_manager.PerfTestTypes.TEST_TYPE_UDP_BIDIRECTIONAL
    ]

    MAX_TX_GAIN_ON_HACKRF = 47
    CHECK_CONNECTION_AND_PINGING_TIME = 30
    MAX_TEST_TIME = 250

    def parse_additional_arguments(self, commandline_args, additional_params):
        """Hook into super class to take control files parameters.

        @param commandline_args dict of parsed parameters from the autotest.
        @param additional_params the noise file name, list of HostapConfig
                objects and a boolean for whether to use iperf.
        """
        noise_parameters, self._ap_config, self._use_iperf = additional_params
        self._noise_file = noise_parameters[0]
        self._frequency = noise_parameters[1]
        self._start_gain = noise_parameters[2]
        self._gain_increment = noise_parameters[3]
        super(network_WiFi_PerfNoisyEnv, self).parse_additional_arguments(
                commandline_args)

    def warmup(self, *args, **kwargs):
        # This test requires include_rpi to be True and rpi_role to be set to
        # the RpiRole representing a HackRF Runner.
        kwargs['include_rpi'] = True
        kwargs['rpi_role'] = site_linux_rpi.RPiRole.HACKRF_RUNNER
        super(network_WiFi_PerfNoisyEnv, self).warmup(*args, **kwargs)


    def do_run(self, manager, gain=None, noise_file=None):
        """Run a single set of perf tests, for a given AP and DUT config, and
        gain value.

        @param manager: a PerfTestManager instance.
        @param gain: int the strength of the signal being trasmitted in dB,
                should be in the 0-47dB range or None.
        @param noise_file: string name of the noise file to be broadcast during
                the test including the absolute path to it on the HackRF Runner
                or None.
        """
        for test_type in self.PERF_TEST_TYPES:
            config = manager.get_config(test_type)
            pcap_lan_iface = interface.Interface(self._pcap_lan_iface_name,
                                                 self.context.pcap_host.host)
            session = manager.get_session(test_type,
                                          self.context.client,
                                          self.context.pcap_host,
                                          peer_device_interface=pcap_lan_iface,
                                          ignore_failures=True)
            ch_width = self._ap_config.channel_width
            if ch_width is None:
                raise error.TestFail(
                        'Failed to get the channel width used by the AP and client.'
                )
            if gain != None:
                gain_tag = 'gain%02d' % gain
                self.context.rpi.stop_broadcasting_file()
                # TODO(b/241004590): Currently, to prevent noise from being
                # broadcast without termination, we broadcast noise for the
                # longest time we can reliably play noise at 8MHz sample rate.
                # However, if this estimate is inaccurate, the noise might not
                # play for the entirety of the test. So, in the future, we
                # should look into broadcasting noise indefinitely and ensuring
                # that the broadcasting properly terminates.
                self.context.rpi.broadcast_file(rf_data_file=noise_file,
                                                duration=self.MAX_TEST_TIME,
                                                frequency=self._frequency,
                                                gain=gain,
                                                run_in_background=True)
                results = session.run(config,
                                      broadcast_rf_data=True,
                                      broadcast_rf_time=self.MAX_TEST_TIME)
            else:
                gain_tag = 'no_gain'
                results = session.run(config)
            if not results:
                logging.warning('Unable to take measurement for %s; '
                                'aborting', config.test_type)
                break
        return results

    def run_once(self):
        """Test body."""
        start_time = time.time()
        logging.info(self.context.client.board)
        max_gain = None

        # Install a specific noise file.
        noise_file_on_dut = os.path.join(self.bindir, 'test_data',
                                         self._noise_file)
        self.context.rpi.install_rf_data_file(noise_file_on_dut)
        noise_files_list = self.context.rpi.host.run('ls %s' %
                                                     self.context.rpi.RF_DATA_FILES_FOLDER).stdout.split()
        if self._noise_file not in noise_files_list:
            raise error.TestFail('Couldn\'t install %s on the HackRF Runner' %
                                 self._noise_file)
        noise_file_on_hackrf_runner = os.path.join(
            self.context.rpi.RF_DATA_FILES_FOLDER,
            self._noise_file)

        # Setup the router and associate the client with it.
        self.configure_and_connect_to_ap(self._ap_config)
        with ip_config_context_manager.IpConfigContextManager() as ip_context:
            self._setup_ip_config(ip_context)
            manager = perf_manager.PerfTestManager(self._use_iperf)
            # Determine baseline throughput (without noise).
            logging.info('Trying without gain')
            baseline_results = self.do_run(manager)
            # Measure throughput for various gain values of RF interference.
            for gain in range(self._start_gain, self.MAX_TX_GAIN_ON_HACKRF+1,
                              self._gain_increment):
                with hackrf_runner_context_manager.HackRFRunnerContextManager(
                self.context.rpi) as hackrf_runner_context:
                    logging.info('Trying gain = %d dB', gain)
                    self.context.rpi.broadcast_file(
                            rf_data_file=noise_file_on_hackrf_runner,
                            duration=self.CHECK_CONNECTION_AND_PINGING_TIME,
                            frequency=self._frequency, gain=gain,
                            run_in_background=True)

                    # Give this gain level a quick check. If we can't stay
                    # associated and handle a few pings, we probably won't get
                    # meaningful results out of iperf/netperf.
                    try:
                        self.context.wait_for_connection(self.context.router.get_ssid())
                    except error.TestFail as e:
                        logging.warning('Could not establish connection at %d'
                                        'dB (%s)', gain, str(e))
                        break

                    results = self.do_run(manager, gain,
                                          noise_file_on_hackrf_runner)
                    if not results:
                        logging.warning('No results for gain %d dB; '
                                        'terminating', gain)
                        break
                    max_gain = gain

            if max_gain == self.MAX_TX_GAIN_ON_HACKRF:
                logging.info('The maximum gain at which we get meaningful '
                             'throughput measurements is beyond the maximum '
                             'gain a HackRF can broadcast (%d dB).',
                             self.MAX_TX_GAIN_ON_HACKRF)
            elif not max_gain:
                raise error.TestFail('Did not succeed at any gain level')
            else:
                logging.info('Reached gain of: %d dB', max_gain)

        # Clean up router and client state for the next run.
        self.context.client.shill.disconnect(self.context.router.get_ssid())
        self.context.router.deconfig()

        # Delete a specific noise file.
        self.context.rpi.delete_rf_data_file(noise_file_on_hackrf_runner)
        noise_files_list = self.context.rpi.host.run('ls %s' %
                                                     self.context.rpi.RF_DATA_FILES_FOLDER).stdout.split()
        if self._noise_file in noise_files_list:
            logging.error('Couldn\'t delete %s from the HackRF Runner',
                          self._noise_file)

        end_time = time.time()
        logging.info('Running time %0.1f seconds.', end_time - start_time)