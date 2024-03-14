# Lint as: python2, python3
# Copyright 2013 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import collections
import logging
import os.path
import time
import numpy

from autotest_lib.client.common_lib import error
from autotest_lib.client.common_lib.cros.network import xmlrpc_datatypes
from autotest_lib.server.cros.network import netperf_runner
from autotest_lib.server.cros.network import netperf_session
from autotest_lib.server.cros.network import wifi_cell_test_base
from autotest_lib.server.cros.network import perf_monitor_service


def _interpolate(tput, atten1, atten2, tput1, tput2):
    return atten1 + ((tput - tput1) * (atten2 - atten1)) / (tput2 - tput1)


class network_WiFi_AttenuatedPerf(wifi_cell_test_base.WiFiCellTestBase):
    """Test maximal achievable bandwidth while varying attenuation.

    Performs a performance test for a specified router configuration as
    signal attentuation increases.

    """

    version = 1

    CMDLINE_SERIES_NOTE = 'series_note'

    NETPERF_CONFIGS = [
            netperf_runner.NetperfConfig(
                       netperf_runner.NetperfConfig.TEST_TYPE_TCP_STREAM),
            netperf_runner.NetperfConfig(
                       netperf_runner.NetperfConfig.TEST_TYPE_TCP_MAERTS),
            netperf_runner.NetperfConfig(
                       netperf_runner.NetperfConfig.TEST_TYPE_UDP_STREAM),
            netperf_runner.NetperfConfig(
                       netperf_runner.NetperfConfig.TEST_TYPE_UDP_MAERTS),
    ]

    TSV_OUTPUT_DIR = 'tsvs'

    DataPoint = collections.namedtuple('DataPoint',
                                       ['attenuation', 'throughput',
                                        'variance', 'signal', 'test_type'])


    def parse_additional_arguments(self, commandline_args, additional_params):
        """Hook into super class to take control files parameters.

        @param commandline_args dict of parsed parameters from the autotest.
        @param additional_params list of dicts describing router configs.

        """
        self._ap_config = additional_params[0]
        self.series_note = None
        self._attenuation_increment = additional_params[1]
        self._final_attenuation = additional_params[2]
        if self.CMDLINE_SERIES_NOTE in commandline_args:
            self.series_note = commandline_args[self.CMDLINE_SERIES_NOTE]

    def run_once(self):
        try:
            # Start the performance monitoring of network throughput.
            perf_monitor = perf_monitor_service.PerfMonitorService(
                    self.context.client.host)
            perf_monitor.start_monitoring_throughput()
            self._run_once()

        finally:
            # Stop the performance monitoring of network throughput.
            perf_monitor.stop_monitoring_throughput()

    def _run_once(self):
        """Run test."""
        start_time = time.time()
        max_atten = None
        self.context.client.host.get_file('/etc/lsb-release', self.resultsdir)
        # Set up the router and associate the client with it.
        self.context.configure(self._ap_config)
        assoc_params = xmlrpc_datatypes.AssociationParameters(
                ssid=self.context.router.get_ssid(),
                security_config=self._ap_config.security_config)
        self.context.assert_connect_wifi(assoc_params)


        # Conduct the performance tests.  Ignore failures, since
        # at high attenuations, sometimes the control connection
        # is unable to terminate the test properly.
        session = netperf_session.NetperfSession(self.context.client,
                                                 self.context.router,
                                                 ignore_failures=True)
        session.warmup_stations()
        start_atten = self.context.attenuator.get_minimal_total_attenuation()

        throughput_data = self._run_sweep(session, self.NETPERF_CONFIGS,
                                          start_atten, self._final_attenuation,
                                          self._attenuation_increment, True)

        self._refine_knee_point(session, throughput_data)

        # Clean up router and client state.
        self.context.client.shill.disconnect(assoc_params.ssid)
        self.context.router.deconfig()
        end_time = time.time()
        logging.info('Running time %0.1f seconds.', end_time - start_time)

        max_atten = throughput_data[-1] if throughput_data else None
        if max_atten is None:
            raise error.TestFail('Did not succeed at any atten level')

        logging.info('Reached attenuation of: %d dB (signal %d)', max_atten[0],
                     max_atten[1])
        self.write_perf_keyval(
                {'ch%03d_max_atten' % self._ap_config.channel: max_atten[0]})
        self.write_perf_keyval(
                {'ch%03d_min_signal' % self._ap_config.channel: max_atten[1]})

        self._report_knee_results(throughput_data)
        self.write_throughput_tsv_files(throughput_data)

    def _report_knee_results(self, throughput_data):
        """Reports knee point results to crosbolt.

        @param throughput_data a list of Datapoint namedtuples gathered from
                tests.
        """
        for test_type in set([data.test_type for data in throughput_data]):
            # TODO(b/303452801): Once knee point calculation is verified as stable,
            # raise error after reporting if calculation fails for any configs
            knee_atten, knee_throughput = self._calculate_knee_point(
                    throughput_data, test_type)
            if not knee_atten:
                continue
            logging.info(
                    'Calculated knee point attenuation: %f, throughput %f',
                    knee_atten, knee_throughput)

            # Write to crosbolt.
            graph_name = '.'.join(
                    [self._ap_config.perf_loggable_description, test_type])
            self.output_perf_value("knee_atten",
                                   knee_atten,
                                   units='dBm',
                                   higher_is_better=True,
                                   graph=graph_name)
            self.output_perf_value("knee_throughput",
                                   knee_throughput,
                                   units='Mbps',
                                   higher_is_better=True,
                                   graph=graph_name)

            # Log knee point results.
            tag = '%s_%s' % (self._ap_config.perf_loggable_description,
                             test_type)
            self.write_perf_keyval({'%s_knee_atten' % tag: knee_atten})
            self.write_perf_keyval(
                    {'%s_knee_throughput' % tag: knee_throughput})

    def _refine_knee_point(self, session, throughput_data):
        """Runs additional refinement iterations around knee-points.

        Refinement results are not reported to Crosbolt, but are appended to
        existing results and included in the output *.tsv files.

        @param session the perf session
        @param throughput_data a list of Datapoint namedtuples gathered from
                tests.
        """
        # Calculate knee_point and re-run calculation for each config.
        for config in self.NETPERF_CONFIGS:
            knee_atten, knee_throughput = self._calculate_knee_point(
                    throughput_data, config.tag)
            if knee_atten is None:
                continue

            logging.info(
                    'Calculated knee point attenuation: %f, throughput %f',
                    knee_atten, knee_throughput)

            # Run knee point at double resolution around calculated value.
            used_attens = set([dp.attenuation for dp in throughput_data])
            # Midpoint round to keep results somewhat consistent.
            knee_atten = round(knee_atten)
            step_size = max(1, self._attenuation_increment // 2)
            min_atten = self.context.attenuator.get_minimal_total_attenuation()
            for atten in numpy.arange(knee_atten - step_size,
                                      knee_atten + step_size + 1, step_size):
                if atten in used_attens or atten < min_atten:
                    continue
                # Just run a single point.
                new_points = self._run_sweep(session, [config], atten,
                                             atten + 1, 1, False)
                throughput_data.extend(new_points)
                throughput_data.sort(key=lambda d: d.attenuation)

    def _calculate_knee_point(self, throughput_data, test_type):
        """Performs a simple linear interpolation to estimate knee point.

        Knee point is estimated to be at 90% of maximum throughput. This is not
        guaranteed to be unique since we're interpolating on the y value,
        however, results are generally well-behaved before the knee point and do
        not exhibit much noise in this region.

        @param throughput_data a list of Datapoint namedtuples gathered from
                tests.
        @return test_type the test_type of the Datapoints to filter on.
        """
        throughput_data = [
                dp for dp in throughput_data if dp.test_type == test_type
        ]
        max_throughput = max(throughput_data, key=lambda d: d.throughput)
        find = 0.9 * max_throughput.throughput
        logging.info('Looking for knee point at target throughput %f', find)

        for i in range(len(throughput_data) - 1):
            dp1 = throughput_data[i]
            dp2 = throughput_data[i + 1]
            # Point cannot occur before peak throughput (b/303452801).
            if dp1.attenuation < max_throughput.attenuation:
                continue

            if dp1.throughput > find and dp2.throughput < find:
                atten = _interpolate(find, dp1.attenuation, dp2.attenuation,
                                     dp1.throughput, dp2.throughput)
                return (atten, find)

            # Corner cases if knee point happens to fall exactly on a sample.
            if dp1.throughput == find:
                return (dp1.attenuation, dp1.throughput)
            if dp2.throughput == find:
                return (dp2.attenuation, dp2.throughput)

        logging.error('Failed to find knee_point')
        return (None, None)

    def _run_sweep(self, session, configs, start, end, step, report_results):
        """Sweeps through set of attenuations and configs and returns results.

        @param session the perf session
        @param configs the set of configurations to run
        @param start the starting attenuation
        @param end the final attenuation
        @param step the attenuation step size
        @param report_results true if the results should be reported to crosbolt
        """
        throughput_data = []
        for atten in numpy.arange(start, end, step):
            atten_tag = 'atten%03d' % atten
            self.context.attenuator.set_total_attenuation(
                    atten, self._ap_config.frequency)
            logging.info('RvR test: current attenuation = %d dB', atten)

            # Give this attenuation level a quick check. If we can't stay
            # associated and handle a few pings, we probably won't get
            # meaningful results out of netperf.
            try:
                self.context.wait_for_connection(self.context.router.get_ssid())
            except error.TestFail as e:
                logging.warning('Could not establish connection at %d dB (%s)',
                                atten, str(e))
                break

            for config in configs:
                results = session.run(config)
                if not results:
                    logging.warning('Unable to take measurement for %s; '
                                    'aborting', config.human_readable_tag)
                    break
                graph_name = '.'.join(
                        [self._ap_config.perf_loggable_description, config.tag])
                values = [result.throughput for result in results]
                # If no signal is detected with client.wifi_signal_level, set
                # signal_level to -100 to indicate weak signal.
                signal_level = (self.context.client.wifi_signal_level if
                        self.context.client.wifi_signal_level else -100)

                if report_results:
                    self.output_perf_value(atten_tag,
                                           values,
                                           units='Mbps',
                                           higher_is_better=True,
                                           graph=graph_name)
                    self.output_perf_value('_'.join([atten_tag, 'signal']),
                                           signal_level,
                                           units='dBm',
                                           higher_is_better=True,
                                           graph=graph_name)

                result = netperf_runner.NetperfResult.from_samples(results)
                throughput_data.append(self.DataPoint(
                        atten,
                        result.throughput,
                        result.throughput_dev,
                        signal_level,
                        config.tag))

                keyval_prefix = '_'.join([
                        self._ap_config.perf_loggable_description, config.tag,
                        atten_tag
                ])
                self.write_perf_keyval(result.get_keyval(prefix=keyval_prefix))

            signal_level = self.context.client.wifi_signal_level
            self.write_perf_keyval(
                    {'_'.join([atten_tag, 'signal']): signal_level})

            if not results:
                logging.warning('No results for atten %d dB; terminating',
                                atten)

        return throughput_data

    def write_throughput_tsv_files(self, throughput_data):
        """Write out .tsv files with plotable data from |throughput_data|.

        Each .tsv file starts with a label for the series that can be
        customized with a short note passed in from the command line.
        It then has column headers and fields separated by tabs.  This format
        is easy to parse and also works well with spreadsheet programs for
        custom report generation.

        @param throughput_data a list of Datapoint namedtuples gathered from
                tests.

        """
        logging.info('Writing .tsv files.')
        os.mkdir(os.path.join(self.resultsdir, self.TSV_OUTPUT_DIR))
        series_label_parts = [self.context.client.board,
                              'ch%03d' % self._ap_config.channel]
        if self.series_note:
            series_label_parts.insert(1, '(%s)' % self.series_note)
        header_parts = ['Attenuation', 'Throughput(Mbps)', 'StdDev(Mbps)',
                        'Client Reported Signal']
        mode = self._ap_config.printable_mode
        mode = mode.replace('+', 'p').replace('-', 'm').lower()
        result_file_prefix = '%s_ch%03d' % (mode, self._ap_config.channel)
        for test_type in set([data.test_type for data in throughput_data]):
            result_file = os.path.join(
                    self.resultsdir, self.TSV_OUTPUT_DIR,
                    '%s_%s.tsv' % (result_file_prefix, test_type))
            lines = [' '.join(series_label_parts),
                     '\t'.join(header_parts)]
            for result in sorted([datum for datum in throughput_data
                                  if datum.test_type == test_type]):
                lines.append('\t'.join(map(str, result[0:4])))
            with open(result_file, 'w') as f:
                f.writelines(['%s\n' % line for line in lines])
