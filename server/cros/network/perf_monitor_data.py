# Lint as: python2, python3
# Copyright 2022 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

class PerfMonitorData(object):
    """
    PerfMonitorData class to hold data from each of the following throughput
    monitors:

    mpstat_data: to hold softirq information

    softnet_data: to hold counts of time_squeeze, received_rps, and
    flow_limit_count

    snmp_data: to hold the socket packet information

    wireless_interface_data: to hold the packet, byte, and error statistics
    at the interface layer
    """

    def __init__(self):
        self.mpstat_data = {}
        self.softnet_data = {}
        self.snmp_data = {}
        self.wireless_interface_data = {}
