# Copyright (c) 2021 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from autotest_lib.client.common_lib import error
from autotest_lib.server.cros.network import hostap_config
from autotest_lib.server.cros.network import netperf_runner
"""
This file defines the expected throughput values that should be used with the network_WiFi_Perf.*
tests.

In the meantime, the expected throughput values depend on the following parameters:
1- The test type:
    a) TCP_MAERTS
    b) TCP_STREAM
    c) UDP_MAERTS
    d) UDP_STREAM
    Note: The thoughput is viewed from the DUT perspective:
        MAERTS = streaming to DUT = Rx
        STREAM = streaming from DUT = Tx
2- The Connection mode:
    a) 80211n
    b) 80211ac
3- The channel width:
    a) 20 MHz
    b) 40 MHz
    c) 80 MHz
"""

Expected_Throughput_WiFi = {
        netperf_runner.NetperfConfig.TEST_TYPE_TCP_MAERTS: {
                hostap_config.HostapConfig.MODE_11N_PURE: {
                        hostap_config.HostapConfig.HT_CHANNEL_WIDTH_20: 85,
                        hostap_config.HostapConfig.HT_CHANNEL_WIDTH_40_PLUS:
                        110,
                        hostap_config.HostapConfig.HT_CHANNEL_WIDTH_40_MINUS:
                        110
                },
                hostap_config.HostapConfig.MODE_11AC_MIXED: {
                        hostap_config.HostapConfig.VHT_CHANNEL_WIDTH_80: 110
                }
        },
        netperf_runner.NetperfConfig.TEST_TYPE_TCP_STREAM: {
                hostap_config.HostapConfig.MODE_11N_PURE: {
                        hostap_config.HostapConfig.HT_CHANNEL_WIDTH_20: 85,
                        hostap_config.HostapConfig.HT_CHANNEL_WIDTH_40_PLUS:
                        140,
                        hostap_config.HostapConfig.HT_CHANNEL_WIDTH_40_MINUS:
                        140
                },
                hostap_config.HostapConfig.MODE_11AC_MIXED: {
                        hostap_config.HostapConfig.VHT_CHANNEL_WIDTH_80: 100
                }
        },
        netperf_runner.NetperfConfig.TEST_TYPE_UDP_MAERTS: {
                hostap_config.HostapConfig.MODE_11N_PURE: {
                        hostap_config.HostapConfig.HT_CHANNEL_WIDTH_20: 90,
                        hostap_config.HostapConfig.HT_CHANNEL_WIDTH_40_PLUS:
                        160,
                        hostap_config.HostapConfig.HT_CHANNEL_WIDTH_40_MINUS:
                        160
                },
                hostap_config.HostapConfig.MODE_11AC_MIXED: {
                        hostap_config.HostapConfig.VHT_CHANNEL_WIDTH_80: 260
                }
        },
        netperf_runner.NetperfConfig.TEST_TYPE_UDP_STREAM: {
                hostap_config.HostapConfig.MODE_11N_PURE: {
                        hostap_config.HostapConfig.HT_CHANNEL_WIDTH_20: 95,
                        hostap_config.HostapConfig.HT_CHANNEL_WIDTH_40_PLUS:
                        180,
                        hostap_config.HostapConfig.HT_CHANNEL_WIDTH_40_MINUS:
                        180
                },
                hostap_config.HostapConfig.MODE_11AC_MIXED: {
                        hostap_config.HostapConfig.VHT_CHANNEL_WIDTH_80: 130
                }
        }
}


def get_expected_throughput_wifi(tag, mode, channel_width):
    """returns the expected throughput for WiFi only performance tests.

    @param tag: the netperf test type.

    @param mode: the WiFi mode such as 80211n.

    @param channel_width: the channel width used in the test.

    @return an integer value of the expected throughputs in Mbps.

    """
    if tag in Expected_Throughput_WiFi:
        if mode in Expected_Throughput_WiFi[tag]:
            if channel_width in Expected_Throughput_WiFi[tag][mode]:
                return Expected_Throughput_WiFi[tag][mode][channel_width]
    raise error.TestFail(
            'Failed to find the expected throughput from the key values, test type = %s, mode = %s, channel width = %d',
            tag, mode, channel_width)
