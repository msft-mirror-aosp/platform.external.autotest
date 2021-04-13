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
                        hostap_config.HostapConfig.HT_CHANNEL_WIDTH_20:
                        (61, 86),
                        hostap_config.HostapConfig.HT_CHANNEL_WIDTH_40_PLUS:
                        (115, 166),
                        hostap_config.HostapConfig.HT_CHANNEL_WIDTH_40_MINUS:
                        (115, 166)
                },
                hostap_config.HostapConfig.MODE_11AC_MIXED: {
                        hostap_config.HostapConfig.VHT_CHANNEL_WIDTH_80:
                        (200, 400)
                },
                hostap_config.HostapConfig.MODE_11AC_PURE: {
                        hostap_config.HostapConfig.VHT_CHANNEL_WIDTH_20:
                        (74, 103),
                        hostap_config.HostapConfig.VHT_CHANNEL_WIDTH_40:
                        (153, 221)
                }
        },
        netperf_runner.NetperfConfig.TEST_TYPE_TCP_STREAM: {
                hostap_config.HostapConfig.MODE_11N_PURE: {
                        hostap_config.HostapConfig.HT_CHANNEL_WIDTH_20:
                        (61, 86),
                        hostap_config.HostapConfig.HT_CHANNEL_WIDTH_40_PLUS:
                        (115, 166),
                        hostap_config.HostapConfig.HT_CHANNEL_WIDTH_40_MINUS:
                        (115, 166)
                },
                hostap_config.HostapConfig.MODE_11AC_MIXED: {
                        hostap_config.HostapConfig.VHT_CHANNEL_WIDTH_80:
                        (200, 400)
                },
                hostap_config.HostapConfig.MODE_11AC_PURE: {
                        hostap_config.HostapConfig.VHT_CHANNEL_WIDTH_20:
                        (74, 103),
                        hostap_config.HostapConfig.VHT_CHANNEL_WIDTH_40:
                        (153, 221)
                }
        },
        netperf_runner.NetperfConfig.TEST_TYPE_UDP_MAERTS: {
                hostap_config.HostapConfig.MODE_11N_PURE: {
                        hostap_config.HostapConfig.HT_CHANNEL_WIDTH_20:
                        (72, 101),
                        hostap_config.HostapConfig.HT_CHANNEL_WIDTH_40_PLUS:
                        (135, 195),
                        hostap_config.HostapConfig.HT_CHANNEL_WIDTH_40_MINUS:
                        (135, 195)
                },
                hostap_config.HostapConfig.MODE_11AC_MIXED: {
                        hostap_config.HostapConfig.VHT_CHANNEL_WIDTH_80:
                        (347, 500)
                },
                hostap_config.HostapConfig.MODE_11AC_PURE: {
                        hostap_config.HostapConfig.VHT_CHANNEL_WIDTH_20:
                        (87, 121),
                        hostap_config.HostapConfig.VHT_CHANNEL_WIDTH_40:
                        (180, 260)
                }
        },
        netperf_runner.NetperfConfig.TEST_TYPE_UDP_STREAM: {
                hostap_config.HostapConfig.MODE_11N_PURE: {
                        hostap_config.HostapConfig.HT_CHANNEL_WIDTH_20:
                        (72, 101),
                        hostap_config.HostapConfig.HT_CHANNEL_WIDTH_40_PLUS:
                        (135, 195),
                        hostap_config.HostapConfig.HT_CHANNEL_WIDTH_40_MINUS:
                        (135, 195)
                },
                hostap_config.HostapConfig.MODE_11AC_MIXED: {
                        hostap_config.HostapConfig.VHT_CHANNEL_WIDTH_80:
                        (347, 500)
                },
                hostap_config.HostapConfig.MODE_11AC_PURE: {
                        hostap_config.HostapConfig.VHT_CHANNEL_WIDTH_20:
                        (87, 121),
                        hostap_config.HostapConfig.VHT_CHANNEL_WIDTH_40:
                        (180, 260)
                }
        }
}

def get_expected_throughput_wifi(tag, mode, channel_width):
    """returns the expected throughput for WiFi only performance tests.

    @param tag: the netperf test type.

    @param mode: the WiFi mode such as 80211n.

    @param channel_width: the channel width used in the test.

    @return a tuple of two integers (must,should) of the expected throughputs in Mbps.

    """
    if tag in Expected_Throughput_WiFi:
        if mode in Expected_Throughput_WiFi[tag]:
            if channel_width in Expected_Throughput_WiFi[tag][mode]:
                return Expected_Throughput_WiFi[tag][mode][channel_width]
    ret_mode = hostap_config.HostapConfig.VHT_NAMES[channel_width]
    if ret_mode is None:
        ret_mode = hostap_config.HostapConfig.HT_NAMES[channel_width]
    raise error.TestFail(
            'Failed to find the expected throughput from the key values, test type = %s, mode = %s, channel width = %s'
            % (tag, mode, ret_mode))
