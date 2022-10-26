# Lint as: python2, python3
# Copyright (c) 2022 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import time
import datetime
import threading

from server.cros.network.perf_monitor_data import PerfMonitorData
from server.cros.network.perf_monitor_command_runner import PerfMonitorCommandRunner
from server.cros.network.perf_monitor_graph import PerfMonitorGraph
from server.cros.network.perf_monitor_throughput_analytics import PerfMonitorThroughputAnalytics

class PerfMonitorService(object):
    """
    Encapsulates logic to parse and represent throughput monitoring results.
    To fetch network stack performance details, clients should create an
    instance of this class and trigger start_monitoring_throughput() to
    start performance monitoring and should call
    stop_monitoring_throughput() to stop performance monitoring. Stopping
    the performance monitoring will post process the collected data and
    create graphs of performance results in the result directory.

    start_monitoring_throughput() is executed in a separate thread and is
    non-blocking.
    """

    SECONDS_BETWEEN_ITERATION = 15

    def __init__(self, host):
        self.monitoring_throughput = False
        self.perf_monitoring_data = {}
        self.host = host
        self.thread = threading.Thread(target=self._monitor_throughput)

    def start_monitoring_throughput(self):
        """
        Begin monitoring throughput in a separate thread until
        stop_monitoring_throughput() is called.
        """
        self.thread.start()

    def _monitor_throughput(self):
        """
        Monitor throughput by calling PerfMonitorCommandRunner functions until
        stop_monitoring_throughput() is called.

        @param host the host used to run command line commands.
        """
        self.monitoring_throughput = True
        timestamp = time.time()
        command_runner = PerfMonitorCommandRunner()

        # Gather the initial values
        initial_softnet_data = command_runner.get_softnet_data(self.host)
        initial_snmp_data = command_runner.get_snmp_data(self.host)
        previous_snmp_data = initial_snmp_data
        initial_wireless_interface_data = command_runner.get_wireless_interface_data(self.host)
        ratio_labels = ['InReceives', 'InDelivers']

        while self.monitoring_throughput:
            #exactly SECONDS_BETWEEN_ITERATION seconds between each function call
            time.sleep(max(0, self.SECONDS_BETWEEN_ITERATION -
                       ((time.time() - timestamp) % 60.0)))
            timestamp = time.time()
            timestamp_date = datetime.datetime.fromtimestamp(float(timestamp))
            self.perf_monitoring_data[timestamp_date] = PerfMonitorData()
            self.perf_monitoring_data[timestamp_date].mpstat_data = (
                command_runner.get_mpstat_data(self.host))

            # Subtract the initial values from the new values so the values
            # begin at 0 and increase throughout the test.
            softnet_data = command_runner.get_softnet_data(self.host)
            for cpu in softnet_data.keys():
                for key in softnet_data[cpu].keys():
                    softnet_data[cpu][key] = (softnet_data[cpu][key] -
                        initial_softnet_data[cpu].get(key, 0))
            self.perf_monitoring_data[timestamp_date].softnet_data = softnet_data
            snmp_data = command_runner.get_snmp_data(self.host)
            for data_id in snmp_data.keys():
                for key in snmp_data[data_id].keys():
                    if key in ratio_labels:
                        previous_value = previous_snmp_data.get(key, 0)
                        previous_snmp_data[key] = snmp_data[data_id][key]
                        snmp_data[data_id][key] = (snmp_data[data_id][key] - previous_value)
                    else:
                        snmp_data[data_id][key] = (snmp_data[data_id][key] -
                                            initial_snmp_data[data_id].get(key, 0))
            self.perf_monitoring_data[timestamp_date].snmp_data = snmp_data
            wireless_interface_data = command_runner.get_wireless_interface_data(self.host)
            for label in wireless_interface_data.keys():
                wireless_interface_data[label] = (wireless_interface_data[label] -
                                     initial_wireless_interface_data.get(label, 0))
            self.perf_monitoring_data[timestamp_date].wireless_interface_data = wireless_interface_data

    def stop_monitoring_throughput(self):
        """
        Stop monitoring throughput and call to graph the throughput metrics.
        """
        self.monitoring_throughput = False
        self.thread.join()
        self._throughput_perf_analytics()
        self._graph_throughput_metrics()

    def _throughput_perf_analytics(self):
        """
        Calculate throughput metrics.
        """
        analyzer = PerfMonitorThroughputAnalytics()
        analyzer.analyze_cpu_usage(self.perf_monitoring_data)

    def _graph_throughput_metrics(self):
        """
        Graph throughput metrics.
        """
        grapher = PerfMonitorGraph()
        grapher.graph_cpu_data(self.perf_monitoring_data)
        grapher.graph_softnet_data(self.perf_monitoring_data)
        grapher.graph_snmp_data(self.perf_monitoring_data)
        grapher.graph_wireless_interface_data(self.perf_monitoring_data)
