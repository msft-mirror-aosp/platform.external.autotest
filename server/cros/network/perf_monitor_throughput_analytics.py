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
