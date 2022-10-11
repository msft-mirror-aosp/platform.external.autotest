# Lint as: python2, python3
# Copyright (c) 2022 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import logging

from autotest_lib.client.common_lib import error
from autotest_lib.client.common_lib.cros.network import iw_runner

class PerfMonitorCommandRunner(object):
    """Run monitor commands and return the data."""

    def _gather_data(self, host, command):
        """
        Run command line command and return the output.

        @param host the host used to run command line commands.
        """
        logging.debug(f'Running {command}.')
        result = host.run(command)

        if result is None:
            raise error.TestFail(f'No results; cmd: {command}')

        return result.stdout

    def _gather_and_parse_wireless_interface_data(self, host):
        """
        Parse the data from the rx and tx files in the
        /sys/class/net/*/statistics folder and place it into a
        dictionary.

        @param host the host used to run command line commands.
        @return dictionary displays the wireless interface statistics.
        """
        data = {}
        labels = ['rx_bytes', 'rx_compressed', 'rx_crc_errors',
                  'rx_dropped', 'rx_errors', 'rx_fifo_errors',
                  'rx_frame_errors', 'rx_length_errors', 'rx_missed_errors',
                  'rx_nohandler', 'rx_over_errors', 'rx_packets',
                  'tx_aborted_errors', 'tx_bytes', 'tx_carrier_errors',
                  'tx_compressed', 'tx_dropped', 'tx_errors',
                  'tx_fifo_errors', 'tx_heartbeat_errors', 'tx_packets',
                  'tx_window_errors']
        iw = iw_runner.IwRunner(remote_host=host)
        interfaces = iw.list_interfaces()
        if not interfaces:
            return data
        if_name = interfaces[0][1]
        for label in labels:
            data[label] = int(self._gather_data(host,
                f'cat /sys/class/net/{if_name}/statistics/{label}').split()[0])
        return data

    def _parse_mpstat_data(self, input_data):
        """
        Parse the data from the command 'mpstat -P ALL 1 1' and place it into a
        dictionary of softirq percentage by cpu.

        @param input_data the data from the mpstat command.
        example input_data:
        10:56:36  CPU   %usr  %nice  %sys %iowait  %irq  %soft  %steal  %guest  %gnice   %idle
        10:56:37  all   0.25   0.00  0.25    0.00  0.50   0.25    0.00    0.00    0.00   98.76
        10:56:37    0   0.00   0.00  0.00    0.00  2.00   1.00    0.00    0.00    0.00   97.00
        10:56:37    1   0.99   0.00  0.99    0.00  0.00   0.99    0.00    0.00    0.00   97.03
        10:56:37    2   0.98   0.00  0.98    0.00  0.98   0.00    0.00    0.00    0.00   97.06
        10:56:37    3   0.00   0.00  0.00    0.00  0.00   0.00    0.00    0.00    0.00  100.00
        10:56:37    4   0.00   0.00  0.00    0.00  0.00   0.00    0.00    0.00    0.00  100.00
        10:56:37    5   0.00   0.00  0.00    0.00  0.99   0.00    0.00    0.00    0.00   99.01
        10:56:37    6   0.00   0.00  0.00    0.00  0.00   0.00    0.00    0.00    0.00  100.00
        10:56:37    7   0.00   0.00  0.00    0.00  0.00   0.00    0.00    0.00    0.00  100.00

        @return dictionary maps cpu to softirq percentage.
        """
        lines = input_data.splitlines()
        data = {}
        labels = []
        for label in lines[2].split()[2:]:
            labels.append(label)
        for line in lines[4:]:
            line = line.split()
            if not line:
                break
            cpu = int(line[1])
            data[cpu] = {}
            for index, value in enumerate(line[2:]):
                data[cpu][labels[index]] = value

        # The 4th line has the all cpu usage, so take the data from that line
        cpu_line = lines[3].split()
        cpu = cpu_line[1]
        data[cpu] = {}
        # add overall cpu usage
        for index, value in enumerate(cpu_line[2:]):
            data[cpu][labels[index]] = value
        return data

    def _parse_softnet_stat_data(self, input_data):
        """
        Parse the data from the /proc/net/softnet_stat file and place it into a
        dictionary of timesqueezes by cpu.

        @param input_data the data from the /proc/net/softnet_stat file.
        example input_data:
        0006b04d 00000000 0000008e 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000
        0007faae 00000000 00000104 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000001
        0001e928 00000000 00000016 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000002
        000f55c6 00000000 0000005d 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000003
        0006be8f 00000000 000001b5 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000004
        0004520c 00000000 000001b1 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000005
        0004ed71 00000000 00000344 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000006
        0005d592 00000000 00000182 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000007

        @return dictionary maps of softnet statistics.
        """
        lines = input_data.splitlines()
        data = {}
        labels = ["packet_process", "packet_drop", "time_squeeze",
                  "cpu_collision", "received_rps", "flow_limit_count"]
        for cpu, line in enumerate(lines):
            line = line.split()
            data[cpu] = {}
            index = 0
            for value in line[:3]:
                data[cpu][labels[index]] = int(value, 16)
                index += 1
            for value in line[8:11]:
                data[cpu][labels[index]] = int(value, 16)
                index += 1
        return data

    def _parse_snmp_data(self, input_data):
        """
        Parse the data from the input file and place it into a dictionary.

        @param input_data the data from the /proc/net/snmp file.
        example input_data:
        Ip: Forwarding DefaultTTL InReceives InHdrErrors InAddrErrors ForwDatagrams InUnknownProtos InDiscards InDelivers OutRequests OutDiscards OutNoRoutes ReasmTimeout ReasmReqds ReasmOKs ReasmFails FragOKs FragFails FragCreates
        Ip: 1 64 3036075 0 0 16 0 0 2971470 2255721 37 3 0 0 0 0 0 0 0
        Icmp: InMsgs InErrors InCsumErrors InDestUnreachs InTimeExcds InParmProbs InSrcQuenchs InRedirects InEchos InEchoReps InTimestamps InTimestampReps InAddrMasks InAddrMaskReps OutMsgs OutErrors OutDestUnreachs OutTimeExcds OutParmProbs OutSrcQuenchs OutRedirects OutEchos OutEchoReps OutTimestamps OutTimestampReps OutAddrMasks OutAddrMaskReps
        Icmp: 530 1 0 69 0 0 0 0 14 447 0 0 0 0 518 0 57 0 0 0 0 447 14 0 0 0 0
        IcmpMsg: InType0 InType3 InType8 OutType0 OutType3 OutType8
        IcmpMsg: 447 69 14 14 57 447
        Tcp: RtoAlgorithm RtoMin RtoMax MaxConn ActiveOpens PassiveOpens AttemptFails EstabResets CurrEstab InSegs OutSegs RetransSegs InErrs OutRsts InCsumErrors
        autoserv| Tcp: 1 200 120000 -1 1097 1776 12 3 41 1613794 3636485 1 0 25 0
        Udp: InDatagrams NoPorts InErrors OutDatagrams RcvbufErrors SndbufErrors InCsumErrors IgnoredMulti
        Udp: 1507733 121 0 1681318 0 33 0 0
        UdpLite: InDatagrams NoPorts InErrors OutDatagrams RcvbufErrors SndbufErrors InCsumErrors IgnoredMulti
        UdpLite: 0 0 0 0 0 0 0 0

        @return dictionary of snmp values.
        """
        lines = input_data.splitlines()
        data = {}
        data_id = []
        for line in lines:
            line = line.split()
            if line[1].isdigit():
                data[line[0].replace(":", "")] = dict(zip(data_id,
                        map(int, line[1:])))
            else:
                data_id = line[1:]
        return data

    def get_mpstat_data(self, host):
        """
        Get the cpu softirq data from the mpstat command.

        @param host the host used to run command line commands.
        @return dictionary maps cpu to softirq percentage.
        """
        data_from_file = self._gather_data(host, 'mpstat -P ALL 1 1')
        mpstat_data = self._parse_mpstat_data(data_from_file)
        return mpstat_data

    def get_softnet_data(self, host):
        """
        Get the time squeeze data from the /proc/net/softnet_stat file.

        @param host the host used to run command line commands.
        @return dictionary maps of softnet statistics.
        """
        data_from_file = self._gather_data(host, 'cat /proc/net/softnet_stat')
        softnet_data = self._parse_softnet_stat_data(data_from_file)
        return softnet_data

    def get_snmp_data(self, host):
        """
        Get the socket data from the /proc/net/snmp file.

        @param host the host used to run command line commands.
        @return dictionary of snmp values.
        """
        data_from_file = self._gather_data(host, 'cat /proc/net/snmp')
        snmp_data = self._parse_snmp_data(data_from_file)
        return snmp_data

    def get_wireless_interface_data(self, host):
        """
        Get the wireless interface statistics from the
        /sys/class/net/*/statistics file.

        @param host the host used to run command line commands.
        @return dictionary displays the wireless interface statistics.
        """
        wireless_interface_data = self._gather_and_parse_wireless_interface_data(host)
        return wireless_interface_data
