# Lint as: python2, python3
# Copyright (c) 2022 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

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

    def __init__(self):
        self.perf_monitoring_data = {}

    def start_monitoring_throughput(self, host):
        """
        Start monitoring throughput until stop_monitoring_throughput
        is called.

        @param host the host for running mpstat.
        """

    def stop_monitoring_throughput(self):
        """
        Stop monitoring throughput.
        """

    def _throughput_perf_analytics(self):
        """
        Calculate throughput metrics.
        """

    def _graph_throughput_metrics(self):
        """
        Graph throughput metrics.
        """
