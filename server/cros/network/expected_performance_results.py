# Copyright (c) 2021 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from autotest_lib.client.common_lib import error
from autotest_lib.server.cros.network import hostap_config
from autotest_lib.server.cros.network import performance_test_types as test_types
"""
This file defines the expected throughput values that should be used with the network_WiFi_Perf.*
tests.

The expected throughput values depend on the following parameters:
1- The test type:
    a) TCP_BIDIRECTIONAL
    b) TCP_RX
    c) TCP_TX
    a) UDP_BIDIRECTIONAL
    b) UDP_RX
    c) UDP_TX
    Note: The thoughput is viewed from the DUT perspective:
        streaming to DUT = RX
        streaming from DUT = TX
        simultaneous TX + RX = BIDIERECTIONAL
2- The Connection mode:
    a) 80211n
    b) 80211ac
3- The channel width:
    a) 20 MHz
    b) 40 MHz
    c) 80 MHz
"""

Expected_Throughput_WiFi = {
        test_types.TEST_TYPE_TCP_BIDIRECTIONAL: {
                hostap_config.HostapConfig.MODE_11N_PURE: {
                        hostap_config.HostapConfig.HT_CHANNEL_WIDTH_20: (0, 0),
                        hostap_config.HostapConfig.HT_CHANNEL_WIDTH_40_PLUS:
                        (0, 0),
                        hostap_config.HostapConfig.HT_CHANNEL_WIDTH_40_MINUS:
                        (0, 0)
                },
                hostap_config.HostapConfig.MODE_11AC_MIXED: {
                        hostap_config.HostapConfig.VHT_CHANNEL_WIDTH_80: (0, 0)
                },
                hostap_config.HostapConfig.MODE_11AC_PURE: {
                        hostap_config.HostapConfig.VHT_CHANNEL_WIDTH_20:
                        (0, 0),
                        hostap_config.HostapConfig.VHT_CHANNEL_WIDTH_40: (0, 0)
                }
        },
        test_types.TEST_TYPE_UDP_BIDIRECTIONAL: {
                hostap_config.HostapConfig.MODE_11N_PURE: {
                        hostap_config.HostapConfig.HT_CHANNEL_WIDTH_20: (0, 0),
                        hostap_config.HostapConfig.HT_CHANNEL_WIDTH_40_PLUS:
                        (0, 0),
                        hostap_config.HostapConfig.HT_CHANNEL_WIDTH_40_MINUS:
                        (0, 0)
                },
                hostap_config.HostapConfig.MODE_11AC_MIXED: {
                        hostap_config.HostapConfig.VHT_CHANNEL_WIDTH_80: (0, 0)
                },
                hostap_config.HostapConfig.MODE_11AC_PURE: {
                        hostap_config.HostapConfig.VHT_CHANNEL_WIDTH_20:
                        (0, 0),
                        hostap_config.HostapConfig.VHT_CHANNEL_WIDTH_40: (0, 0)
                }
        },
        test_types.TEST_TYPE_TCP_RX: {
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
        test_types.TEST_TYPE_TCP_TX: {
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
        test_types.TEST_TYPE_UDP_RX: {
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
        test_types.TEST_TYPE_UDP_TX: {
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


def get_expected_throughput_wifi(test_type, mode, channel_width):
    """returns the expected throughput for WiFi only performance tests.

    @param test_type: the performance_test_types test type.

    @param mode: the WiFi mode such as 80211n.

    @param channel_width: the channel width used in the test.

    @return a tuple of two integers (must,should) of the expected throughputs in Mbps.

    """
    if test_type in Expected_Throughput_WiFi:
        if mode in Expected_Throughput_WiFi[test_type]:
            if channel_width in Expected_Throughput_WiFi[test_type][mode]:
                return Expected_Throughput_WiFi[test_type][mode][channel_width]
    ret_mode = hostap_config.HostapConfig.VHT_NAMES[channel_width]
    if ret_mode is None:
        ret_mode = hostap_config.HostapConfig.HT_NAMES[channel_width]
    raise error.TestFail(
            'Failed to find the expected throughput from the key values, test type = %s, mode = %s, channel width = %s'
            % (test_type, mode, ret_mode))
