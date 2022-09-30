# Lint as: python2, python3
# Copyright (c) 2022 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import logging

from autotest_lib.client.common_lib import error

class PerfMonitorCommandRunner(object):
    """Run monitor commands and output to file."""

    def _gather_data_from_command(self, host, command):
        """
        Run mpstat and output results to mpstat_results.

        @param host the host for running mpstat.

        """
        logging.debug(f'Running {command}.')
        result = host.run(command)

        if result is None:
            raise error.TestFail('No results; cmd: mpstat -P ALL 1 1')

        return result.stdout

    def _gather_data_from_file(self, input_file_path):
        """
        Read data from file_path and output results to output_file.

        @param input_file_path string the file to query data from
        ex. file_path = /proc/net/softnet_stat
        """
        logging.info(f'Gathering data from {input_file_path}.')

        with open(input_file_path, 'r') as f:
            result = f.read()

        if result is None:
            raise error.TestFail(f'No results; cmd: open {input_file_path}')

        return result

    def _parse_mpstat_data(self):
        """
        Parse the data from the command 'mpstat -P ALL 1 1' and place it into a
        dictionary of softirq percentage by cpu.
        """

    def _parse_softnet_stat_data(self):
        """
        Parse the data from the /proc/net/softnet_stat file and place it into a
        dictionary of timesqueezes by cpu.
        """

    def _parse_interrupt_data(self):
        """
        Parse the data from the /proc/interrupts file and place it into a
        dictionary of total interrupts by irq.
        """

    def _parse_snmp_data(self):
        """
        Parse the data from the /proc/net/snmp data and place it into a dictionary
        of Ip and Icmp values.
        """

    def _parse_netstat_data(self):
        """
        Parse the data from the netstat command and place it into a dictionary
        of connections.
        """

    def get_cpu_data(self):
        """
        Get the cpu softirq data from the mpstat command.

        @return dictionary maps cpu to softirq percentage.
        """

    def get_time_squeeze_data(self):
        """
        Get the time squeeze data from the /proc/net/softnet_stat file.

        @return dictionary maps cpu to time squeezes.
        """

    def get_interrupt_data(self):
        """
        Get the interrupt data from the /proc/interrupts file.

        @return dictionary maps irq to dictionary of total interrupts by cpu.
        """

    def get_socket_data(self):
        """
        Get the socket data from the /proc/net/snmp file.

        @return dictionary maps to Ip and Icmp values.
        """

    def get_network_connection_data(self):
        """
        Get the TCP connection data from the mpstat command.

        @return dictionary displays the TCP connections.
        """
