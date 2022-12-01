# Lint as: python2, python3
# Copyright 2022 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import logging

class PerfMonitorThroughputAnalytics(object):
    """Calculate throughput metrics."""

    def analyze_cpu_usage(self, perf_data):
        """
        Calculate the average SoftIRQ percentages for each cpu over the polling
        period.

        @param perf_data the dictionary mapping from timestamp to
        PerfMonitorData object.
        """
        if not perf_data:
            return
        #TODO (b/257075290) find an appropriate threshold for the fleet based on baselines
        CPU_CONSUMPTION_THRESHOLD = 90
        cpu_consumption = {}
        num_iterations = 0
        instances_over_threshold = {}
        for cpu in list(perf_data.values())[0].mpstat_data.keys():
            cpu_consumption[cpu] = 0
            instances_over_threshold[cpu] = 0

        for perf_object in perf_data.values():
            num_iterations += 1
            for cpu, values in perf_object.mpstat_data.items():
                consumption = float(values['%soft'])
                cpu_consumption[cpu] += consumption
                if consumption > CPU_CONSUMPTION_THRESHOLD:
                    instances_over_threshold[cpu] += 1
        unused_cpus = []
        for cpu, consumption in cpu_consumption.items():
            consumption /= num_iterations
            cpu_consumption[cpu] = consumption
            if consumption > CPU_CONSUMPTION_THRESHOLD:
                logging.info(f"Exceeded {CPU_CONSUMPTION_THRESHOLD}% CPU Softirq Consumption Average Threshold."
                             f" Measured CPU {cpu} Softirq Consumption Average: {consumption}")
            elif consumption != 0:
                logging.info(f" Measured CPU {cpu} Softirq Consumption Average: {consumption}")
            else:
                unused_cpus.append(cpu)
        if unused_cpus and len(unused_cpus) != len(cpu_consumption):
            if len(unused_cpus) == 1:
                logging.info(f"CPU Softirq Consumption is not balanced. CPU {unused_cpus[0]} has zero Softirq usage")
            else:
                logging.info(f"CPU Softirq Consumption is not balanced. CPUs {unused_cpus} have zero Softirq usage")
        for cpu, count in instances_over_threshold.items():
            if count > 0:
                logging.info((f"CPU {cpu} exceeded {CPU_CONSUMPTION_THRESHOLD}% CPU Softirq"
                              f" Consumption Threshold {count} times in {num_iterations} iterations"))

    def analyze_time_squeeze(self, perf_data):
        """
        Calculate the rate of time_squeeze's during the polling
        period.

        @param perf_data the dictionary mapping from timestamp to
        PerfMonitorData object.
        """
        if len(perf_data) < 2:
            return
        #TODO (b/257075290) find an appropriate threshold for the fleet based on baselines
        TIME_SQUEEZE_THRESHOLD = 3
        prev_timestamp = list(perf_data.keys())[0]
        final_timestamp = list(perf_data.keys())[-1]
        prev_time_squeezes = 0
        for cpu in range(len(perf_data[prev_timestamp].softnet_data.values())):
                prev_time_squeezes += perf_data[prev_timestamp].softnet_data[cpu]['time_squeeze']

        for timestamp, perf_object in perf_data.items():
            if float((timestamp - prev_timestamp).total_seconds()) > 60 or timestamp == final_timestamp:
                total_time_squeezes = 0
                for cpu in range(len(perf_object.softnet_data.values())):
                    total_time_squeezes += perf_object.softnet_data[cpu]['time_squeeze']

                if prev_timestamp is not None:
                    curr_time_squeezes = total_time_squeezes - prev_time_squeezes
                    if(curr_time_squeezes > TIME_SQUEEZE_THRESHOLD):
                        logging.info(f"Exceeded {TIME_SQUEEZE_THRESHOLD} Time Squeezes Threshold"
                                    f" from time interval {prev_timestamp} to {timestamp}."
                                    f" Measured Time Squeezes over time interval: {curr_time_squeezes}")
                prev_timestamp = timestamp
                prev_time_squeezes = total_time_squeezes

    def analyze_rx_errors(self, perf_data):
        """
        Calculate the average Rx Errors over the polling period.

        @param perf_data the dictionary mapping from timestamp to
        PerfMonitorData object.
        """
        if len(perf_data) < 2:
            return
        #TODO (b/257075290) find an appropriate threshold for the fleet based on baselines
        RX_ERROR_THRESHOLD = 3
        total_rx_errors = 0
        labels = ['rx_compressed', 'rx_crc_errors',
                  'rx_dropped', 'rx_errors', 'rx_fifo_errors',
                  'rx_frame_errors', 'rx_length_errors', 'rx_missed_errors',
                  'rx_nohandler', 'rx_over_errors']
        prev_timestamp = list(perf_data.keys())[0]
        final_timestamp = list(perf_data.keys())[-1]
        prev_rx_errors = 0
        for label in labels:
            prev_rx_errors += perf_data[prev_timestamp].wireless_interface_data[label]

        for timestamp, perf_object in perf_data.items():
            if float((timestamp - prev_timestamp).total_seconds()) > 60 or timestamp == final_timestamp:
                total_rx_errors = 0
                for label in labels:
                    total_rx_errors += perf_object.wireless_interface_data[label]

                curr_rx_errors = total_rx_errors - prev_rx_errors
                if(curr_rx_errors > RX_ERROR_THRESHOLD):
                    logging.info(f"Exceeded {RX_ERROR_THRESHOLD} Rx Error Threshold"
                                f" from time interval {prev_timestamp} to {timestamp}."
                                f" Measured Rx Errors over time interval: {curr_rx_errors}")

                prev_timestamp = timestamp
                prev_rx_errors = total_rx_errors

    def analyze_tx_errors(self, perf_data):
        """
        Calculate the average Tx Errors over the polling period.

        @param perf_data the dictionary mapping from timestamp to
        PerfMonitorData object.
        """
        if len(perf_data) < 2:
            return
        #TODO (b/257075290) find an appropriate threshold for the fleet based on baselines
        TX_ERROR_THRESHOLD = 3
        total_tx_errors = 0
        labels = ['tx_carrier_errors',
                  'tx_compressed', 'tx_dropped', 'tx_errors',
                  'tx_fifo_errors', 'tx_heartbeat_errors', 'tx_window_errors']
        prev_timestamp = list(perf_data.keys())[0]
        final_timestamp = list(perf_data.keys())[-1]
        prev_tx_errors = 0
        for label in labels:
            prev_tx_errors += perf_data[prev_timestamp].wireless_interface_data[label]

        for timestamp, perf_object in perf_data.items():
            if float((timestamp - prev_timestamp).total_seconds()) > 60 or timestamp == final_timestamp:
                total_tx_errors = 0
                for label in labels:
                    total_tx_errors += perf_object.wireless_interface_data[label]

                curr_tx_errors = total_tx_errors - prev_tx_errors
                if(curr_tx_errors > TX_ERROR_THRESHOLD):
                    logging.info(f"Exceeded {TX_ERROR_THRESHOLD} Tx Error Threshold"
                                f" from time interval {prev_timestamp} to {timestamp}."
                                f" Measured Tx Errors over time interval: {curr_tx_errors}")

                prev_timestamp = timestamp
                prev_tx_errors = total_tx_errors
