# Lint as: python2, python3
# Copyright (c) 2022 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import matplotlib.pyplot as plt
import os

class PerfMonitorGraph(object):
    """Graph performance monitors."""

    def graph_cpu_data(self, perf_data):
        """
        Graph the SoftIRQ percentages for each cpu by time over the polling
        period.

        @param perf_data the dictionary mapping from timestamp to
        PerfMonitorData object.
        """
        self._create_directory(r'graphs')
        graphdata = {}
        if len(perf_data.items()) > 0:
            for cpu in list(perf_data.values())[0].mpstat_data.keys():
                graphdata['timestamp'] = []
                graphdata[f'CPU {cpu}'] = []

            for timestamp, perf_object in perf_data.items():
                graphdata['timestamp'].append(timestamp)
                for cpu, values in perf_object.mpstat_data.items():
                    graphdata[f'CPU {cpu}'].append(float(values['%soft']))

        self._create_graph_plot('Softirq CPU Percentage', '% cpu',
                'graphs/cpu_graph.png', graphdata)

    def graph_softnet_data(self, perf_data):
        """
        Graph the counts of time squeezes, received rps, and flow limit by
        time over the polling period and save to separate graphs in
        /graphs.

        @param perf_data the dictionary mapping from timestamp to
        PerfMonitorData object.
        """
        self._create_directory(r'graphs')
        graphdata = {}
        labels = ['time_squeeze', 'received_rps', 'flow_limit_count']
        graphdata['timestamp'] = []
        for label in labels:
            graphdata[label] = []

        for timestamp, perf_object in perf_data.items():
            for count, values in enumerate(perf_object.softnet_data.values()):
                if count == 0:
                    graphdata['timestamp'].append(timestamp)
                    for label in labels:
                        graphdata[label].append(values[label])

                else:
                    for label in labels:
                        graphdata[label][-1] += values[label]

        for key in graphdata.keys():
            if key == 'timestamp':
                continue
            self._create_graph_plot(f'{key} count', f'{key} count',
                    f'graphs/{key}_graph.png',
                    {k: graphdata[k] for k in ('timestamp', key)})

    def _graph_snmp_ip_data(self, perf_data):
        """
        Graph the counts of SNMP IP data by time over the polling period
        and save to graphs/snmp.

        @param perf_data the dictionary mapping from timestamp to
        PerfMonitorData object.
        """
        graphdata = {}
        labels = ['InReceives', 'InAddrErrors', 'InDiscards',
                  'InDelivers', 'OutRequests', 'OutDiscards',
                  'InUnknownProtos', 'OutNoRoutes']
        graphdata['timestamp'] = []
        for label in labels:
            graphdata[label] = []

        for timestamp, perf_object in perf_data.items():
            graphdata['timestamp'].append(timestamp)
            for label in labels:
                graphdata[label].append(perf_object.snmp_data['Ip'][label])

        self._create_graph_plot('IP Metrics', 'count',
                'graphs/snmp/ip_graph.png', graphdata)

    def _graph_snmp_udp_data(self, perf_data):
        """
        Graph the counts of SNMP UDP data by time over the polling period
        and save to graphs/snmp.

        @param perf_data the dictionary mapping from timestamp to
        PerfMonitorData object.
        """
        graphdata = {}
        labels = ['InErrors', 'OutDatagrams', 'RcvbufErrors', 'SndbufErrors']
        graphdata['timestamp'] = []
        for label in labels:
            graphdata[label] = []

        for timestamp, perf_object in perf_data.items():
            graphdata['timestamp'].append(timestamp)
            for label in labels:
                graphdata[label].append(perf_object.snmp_data['Udp'][label])

        self._create_graph_plot('UDP Metrics', 'count',
                'graphs/snmp/udp_graph.png', graphdata)

    def _graph_snmp_tcp_data(self, perf_data):
        """
        Graph the counts of SNMP TCP data by time over the polling period
        and save to graphs/snmp.

        @param perf_data the dictionary mapping from timestamp to
        PerfMonitorData object.
        """
        graphdata = {}
        labels = ['RtoMin', 'RtoMax', 'InSegs', 'OutSegs']
        graphdata['timestamp'] = []
        for label in labels:
            graphdata[label] = []

        for timestamp, perf_object in perf_data.items():
            graphdata['timestamp'].append(timestamp)
            for label in labels:
                graphdata[label].append(perf_object.snmp_data['Tcp'][label])

        self._create_graph_plot('TCP Metrics', 'count',
                'graphs/snmp/tcp_graph.png', graphdata)

    def graph_snmp_data(self, perf_data):
        """
        Create the graphs/snmp directory and graph the SNMP data.

        @param perf_data the dictionary mapping from timestamp to
        PerfMonitorData object.
        """
        self._create_directory(r'graphs/snmp')
        self._graph_snmp_ip_data(perf_data)
        self._graph_snmp_udp_data(perf_data)
        self._graph_snmp_tcp_data(perf_data)

    def _graph_rx_error_data(self, perf_data):
        """
        Graph the counts of RX Errors by time over the polling period
        and save to graphs/wirelessinterface.

        @param perf_data the dictionary mapping from timestamp to
        PerfMonitorData object.
        """
        graphdata = {}
        labels = ['rx_compressed', 'rx_crc_errors',
                  'rx_dropped', 'rx_errors', 'rx_fifo_errors',
                  'rx_frame_errors', 'rx_length_errors', 'rx_missed_errors',
                  'rx_nohandler', 'rx_over_errors']
        graphdata['timestamp'] = []
        for label in labels:
            graphdata[label] = []

        for timestamp, perf_object in perf_data.items():
            graphdata['timestamp'].append(timestamp)
            for label in labels:
                graphdata[label].append(perf_object.wireless_interface_data[label])

        self._create_graph_plot('rx error counts', 'count',
                'graphs/wirelessinterface/rx_error_graph.png', graphdata)

    def _graph_tx_error_data(self, perf_data):
        """
        Graph the counts of TX Errors by time over the polling period
        and save to graphs/wirelessinterface.

        @param perf_data the dictionary mapping from timestamp to
        PerfMonitorData object.
        """
        graphdata = {}
        labels = ['tx_carrier_errors',
                  'tx_compressed', 'tx_dropped', 'tx_errors',
                  'tx_fifo_errors', 'tx_heartbeat_errors', 'tx_window_errors']
        graphdata['timestamp'] = []
        for label in labels:
            graphdata[label] = []

        for timestamp, perf_object in perf_data.items():
            graphdata['timestamp'].append(timestamp)
            for label in labels:
                graphdata[label].append(perf_object.wireless_interface_data[label])

        self._create_graph_plot('tx error counts', 'count',
                'graphs/wirelessinterface/tx_error_graph.png', graphdata)

    def _graph_rxtx_bytes_data(self, perf_data):
        """
        Graph the counts of RX and TX Bytes by time over the polling period
        and save to graphs/wirelessinterface.

        @param perf_data the dictionary mapping from timestamp to
        PerfMonitorData object.
        """
        graphdata = {}
        labels = ['rx_bytes', 'tx_bytes']
        graphdata['timestamp'] = []
        for label in labels:
            graphdata[label] = []

        for timestamp, perf_object in perf_data.items():
            graphdata['timestamp'].append(timestamp)
            for label in labels:
                graphdata[label].append(perf_object.wireless_interface_data[label])

        self._create_graph_plot('rx tx bytes', 'count',
                'graphs/wirelessinterface/rxtx_bytes_graph.png', graphdata)

    def _graph_rxtx_packets_data(self, perf_data):
        """
        Graph the counts of RX and TX Packets by time over the polling period
        and save to graphs/wirelessinterface.

        @param perf_data the dictionary mapping from timestamp to
        PerfMonitorData object.
        """
        graphdata = {}
        labels = ['rx_packets', 'tx_packets']
        graphdata['timestamp'] = []
        for label in labels:
            graphdata[label] = []

        for timestamp, perf_object in perf_data.items():
            graphdata['timestamp'].append(timestamp)
            for label in labels:
                graphdata[label].append(perf_object.wireless_interface_data[label])

        self._create_graph_plot('rx tx packets', 'count',
                'graphs/wirelessinterface/rxtx_packets_graph.png', graphdata)

    def graph_wireless_interface_data(self, perf_data):
        """
        Create the graphs/wirelessinterface directory and graph the wireless
        interface data.

        @param perf_data the dictionary mapping from timestamp to
        PerfMonitorData object.
        """
        self._create_directory(r'graphs/wirelessinterface')
        self._graph_rx_error_data(perf_data)
        self._graph_tx_error_data(perf_data)
        self._graph_rxtx_packets_data(perf_data)
        self._graph_rxtx_bytes_data(perf_data)

    def _create_graph_plot(self, title, ylabel, graph_filename, graphdata):
        """
        Create a plot of the graphdata and save it to the specified
        graph_filename location.

        @param title the title of the graph
        @param ylabel the label for the y-axis of the graph
        @param graph_filename the location to save the graph to
        @param graphdata dictionary of data to graph
        """
        _, ax = plt.subplots()
        plt.title(title)
        plt.xticks(rotation=90)
        ax.set_xlabel('timestamp')
        ax.set_ylabel(ylabel)
        for key in graphdata.keys():
            if key == 'timestamp':
                continue
            ax.step(graphdata['timestamp'], graphdata[key], label=key)
        plt.legend()
        plt.savefig(graph_filename, bbox_inches="tight")
        plt.close()

    def _create_directory(self, directory_name):
        """
        Create a new directory in the current working directory.

        @param directory_name the name of the directory to create
        """
        curr_directory = os.getcwd()
        new_directory_path = os.path.join(curr_directory, directory_name)
        if not os.path.exists(new_directory_path):
            os.mkdir(new_directory_path)