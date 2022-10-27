# Lint as: python2, python3
# Copyright (c) 2022 The Chromium OS Authors. All rights reserved.
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
        for cpu in list(perf_data.values())[0].mpstat_data.keys():
            cpu_consumption[cpu] = 0

        for perf_object in perf_data.values():
            num_iterations += 1
            for cpu, values in perf_object.mpstat_data.items():
                consumption = float(values['%soft'])
                cpu_consumption[cpu] += consumption

        for cpu, consumption in cpu_consumption.items():
            consumption /= num_iterations
            cpu_consumption[cpu] = consumption
            if consumption > CPU_CONSUMPTION_THRESHOLD:
                logging.info(f"Exceeded {CPU_CONSUMPTION_THRESHOLD}% CPU Softirq Consumption Average Threshold."
                             f" Measured CPU {cpu} Softirq Consumption Average: {consumption}")

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
