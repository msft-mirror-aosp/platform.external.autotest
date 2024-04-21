# Lint as: python2, python3
# Copyright 2021 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from autotest_lib.client.common_lib import error
from autotest_lib.server.cros.bluetooth.bluetooth_adapter_audio_tests import \
     BluetoothAdapterAudioTests
from autotest_lib.server.cros.network import hostap_config
from autotest_lib.server.cros.network import perf_test_manager as perf_manager

"""
This file defines the expected throughput values that should be used with the network_WiFi_Perf.*
tests.
For the network_WiFi_BluetoothStreamPerf.* tests, the expected throughput drop levels are defined


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
    c) 80211ax
    Note: gale(legacy) doesn't have expected values for 80211ax
3- The channel width:
    a) 20 MHz
    b) 40 MHz
    c) 80 MHz
"""

expected_throughput_wifi_legacy = {
        perf_manager.PerfTestTypes.TEST_TYPE_TCP_BIDIRECTIONAL: {
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
        perf_manager.PerfTestTypes.TEST_TYPE_UDP_BIDIRECTIONAL: {
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
        perf_manager.PerfTestTypes.TEST_TYPE_TCP_RX: {
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
        perf_manager.PerfTestTypes.TEST_TYPE_TCP_TX: {
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
        perf_manager.PerfTestTypes.TEST_TYPE_UDP_RX: {
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
        perf_manager.PerfTestTypes.TEST_TYPE_UDP_TX: {
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

expected_throughput_wifi_router_arch = {
        'openwrt_ramips-mt7621-ubnt_unifi-6-lite': {
                perf_manager.PerfTestTypes.TEST_TYPE_TCP_BIDIRECTIONAL: {
                        hostap_config.HostapConfig.MODE_11N_PURE: {
                                hostap_config.HostapConfig.HT_CHANNEL_WIDTH_20:
                                (0, 0),
                                hostap_config.HostapConfig.HT_CHANNEL_WIDTH_40_PLUS:
                                (0, 0),
                                hostap_config.HostapConfig.HT_CHANNEL_WIDTH_40_MINUS:
                                (0, 0)
                        },
                        hostap_config.HostapConfig.MODE_11AC_MIXED: {
                                hostap_config.HostapConfig.VHT_CHANNEL_WIDTH_80:
                                (0, 0)
                        },
                        hostap_config.HostapConfig.MODE_11AC_PURE: {
                                hostap_config.HostapConfig.VHT_CHANNEL_WIDTH_20:
                                (0, 0),
                                hostap_config.HostapConfig.VHT_CHANNEL_WIDTH_40:
                                (0, 0)
                        },
                        hostap_config.HostapConfig.MODE_11AX_MIXED: {
                                hostap_config.HostapConfig.HE_CHANNEL_WIDTH_80:
                                (0, 0)
                        },
                        hostap_config.HostapConfig.MODE_11AX_PURE: {
                                hostap_config.HostapConfig.HE_CHANNEL_WIDTH_20:
                                (0, 0),
                                hostap_config.HostapConfig.HE_CHANNEL_WIDTH_40:
                                (0, 0)
                        }
                },
                perf_manager.PerfTestTypes.TEST_TYPE_UDP_BIDIRECTIONAL: {
                        hostap_config.HostapConfig.MODE_11N_PURE: {
                                hostap_config.HostapConfig.HT_CHANNEL_WIDTH_20:
                                (0, 0),
                                hostap_config.HostapConfig.HT_CHANNEL_WIDTH_40_PLUS:
                                (0, 0),
                                hostap_config.HostapConfig.HT_CHANNEL_WIDTH_40_MINUS:
                                (0, 0)
                        },
                        hostap_config.HostapConfig.MODE_11AC_MIXED: {
                                hostap_config.HostapConfig.VHT_CHANNEL_WIDTH_80:
                                (0, 0)
                        },
                        hostap_config.HostapConfig.MODE_11AC_PURE: {
                                hostap_config.HostapConfig.VHT_CHANNEL_WIDTH_20:
                                (0, 0),
                                hostap_config.HostapConfig.VHT_CHANNEL_WIDTH_40:
                                (0, 0)
                        },
                        hostap_config.HostapConfig.MODE_11AX_MIXED: {
                                hostap_config.HostapConfig.HE_CHANNEL_WIDTH_80:
                                (0, 0)
                        },
                        hostap_config.HostapConfig.MODE_11AX_PURE: {
                                hostap_config.HostapConfig.HE_CHANNEL_WIDTH_20:
                                (0, 0),
                                hostap_config.HostapConfig.HE_CHANNEL_WIDTH_40:
                                (0, 0)
                        }
                },
                perf_manager.PerfTestTypes.TEST_TYPE_TCP_RX: {
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
                        },
                        hostap_config.HostapConfig.MODE_11AX_MIXED: {
                                hostap_config.HostapConfig.HE_CHANNEL_WIDTH_80:
                                (200, 400)
                        },
                        hostap_config.HostapConfig.MODE_11AX_PURE: {
                                hostap_config.HostapConfig.HE_CHANNEL_WIDTH_20:
                                (74, 103),
                                hostap_config.HostapConfig.HE_CHANNEL_WIDTH_40:
                                (153, 221)
                        }
                },
                perf_manager.PerfTestTypes.TEST_TYPE_TCP_TX: {
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
                        },
                        hostap_config.HostapConfig.MODE_11AX_MIXED: {
                                hostap_config.HostapConfig.HE_CHANNEL_WIDTH_80:
                                (200, 400)
                        },
                        hostap_config.HostapConfig.MODE_11AX_PURE: {
                                hostap_config.HostapConfig.HE_CHANNEL_WIDTH_20:
                                (74, 103),
                                hostap_config.HostapConfig.HE_CHANNEL_WIDTH_40:
                                (153, 221)
                        }
                },
                perf_manager.PerfTestTypes.TEST_TYPE_UDP_RX: {
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
                        },
                        hostap_config.HostapConfig.MODE_11AX_MIXED: {
                                hostap_config.HostapConfig.HE_CHANNEL_WIDTH_80:
                                (347, 500)
                        },
                        hostap_config.HostapConfig.MODE_11AX_PURE: {
                                hostap_config.HostapConfig.HE_CHANNEL_WIDTH_20:
                                (87, 121),
                                hostap_config.HostapConfig.HE_CHANNEL_WIDTH_40:
                                (180, 260)
                        }
                },
                perf_manager.PerfTestTypes.TEST_TYPE_UDP_TX: {
                        # TODO(b/271490937): wifi_perf_openwrt: UDP TX perf numbers are low
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
                        },
                        hostap_config.HostapConfig.MODE_11AX_MIXED: {
                                hostap_config.HostapConfig.HE_CHANNEL_WIDTH_80:
                                (347, 500)
                        },
                        hostap_config.HostapConfig.MODE_11AX_PURE: {
                                hostap_config.HostapConfig.HE_CHANNEL_WIDTH_20:
                                (87, 121),
                                hostap_config.HostapConfig.HE_CHANNEL_WIDTH_40:
                                (180, 260)
                        }
                }
        }
}


def get_expected_throughput_wifi(test_type,
                                 mode,
                                 channel_width,
                                 router_arch=None):
    """returns the expected throughput for WiFi only performance tests.

    @param test_type: the PerfTestTypes test type.

    @param mode: the WiFi mode such as 80211n.

    @param channel_width: the channel width used in the test.

    @param router_arch: the arch of router's CPU and WiFi chipset

    @return a tuple of two integers (must,should) of the expected throughputs in Mbps.

    """
    expected_tput = expected_throughput_wifi_legacy
    if router_arch:
        expected_tput = expected_throughput_wifi_router_arch[router_arch]

    if test_type in expected_tput:
        if mode in expected_tput[test_type]:
            if channel_width in expected_tput[test_type][mode]:
                return expected_tput[test_type][mode][channel_width]
    ret_mode = hostap_config.HostapConfig.HE_NAMES.get(channel_width)
    if ret_mode is None:
        ret_mode = hostap_config.HostapConfig.VHT_NAMES.get(channel_width)
    if ret_mode is None:
        ret_mode = hostap_config.HostapConfig.HT_NAMES.get(channel_width)
    raise error.TestFail(
            'Failed to find the expected throughput from the key values, test type = %s, mode = %s, channel width = %s'
            % (test_type, mode, ret_mode))


"""These are special exceptions for specific boards that define the maximum
throughput in Mbps that we expect boards to be able to achieve. Generally, these
boards were qualified before the advent of platform throughput requirements, and
therefore are exempted from meeting certain requirements. Each board must be
annotated with a bug which includes the history on why the specific expectations
for that board.
"""
max_throughput_expectation_for_boards = {
        # caroline throughput results tracked in b:188454947.
        "caroline": {
                perf_manager.PerfTestTypes.TEST_TYPE_UDP_RX: 200
        },
        # elm throughput results tracked in b:201806809.
        "elm": {
                perf_manager.PerfTestTypes.TEST_TYPE_UDP_TX:
                200,
                perf_manager.PerfTestTypes.TEST_TYPE_UDP_RX:
                300,
                # The regression on TCP_RX is tracked in b:238853149
                perf_manager.PerfTestTypes.TEST_TYPE_TCP_RX:
                125
        },
        # eve throughput results tracked in b:188454947.
        "eve": {
                perf_manager.PerfTestTypes.TEST_TYPE_UDP_RX: 200
        },
        # kukui throughput results tracked in b:201807413.
        "kukui": {
                perf_manager.PerfTestTypes.TEST_TYPE_UDP_RX: 300
        },
        # nami throughput results tracked in b:188454947.
        "nami": {
                perf_manager.PerfTestTypes.TEST_TYPE_UDP_RX: 200
        },
        # trogdor throughput results tracked in b:201807655.
        "trogdor": {
                perf_manager.PerfTestTypes.TEST_TYPE_UDP_RX: 250
        },
        # kevin throughput results tracked in b:237404049.
        "kevin": {
                perf_manager.PerfTestTypes.TEST_TYPE_TCP_RX: 80
        }
}


def get_board_max_expectation(test_type, board_name):
    """Returns the maximum throughput expectation for a given board in a given
    test type, or None if the board has no exception for that test type.

    @param test_type: the PerfTestTypes test type.
    @param board_name: string name of the board, as defined by
    SiteLinuxSystem.board field.

    @return integer value for maximum throughput expectation (in Mbps) for the
    given boardand test type, or None if the maximum is not defined.
    """

    # Remove the suffix (-kernelnext, -connectivitynext, etc) from the board name.
    if "-" in board_name:
        board_name = board_name.split('-')[0]
    board_maximums = max_throughput_expectation_for_boards.get(board_name)
    if not board_maximums:
        return None
    return board_maximums.get(test_type)


# Constants defining expected throughput drop in percents
NO_EXPECTED_THROUGHPUT_DROP = 0
SCARCELY_EXPECTED_THROUGHPUT_DROP = 5
LIGHT_EXPECTED_THROUGHPUT_DROP = 25
MODERATE_EXPECTED_THROUGHPUT_DROP = 50
SIGNIFICANT_EXPECTED_THROUGHPUT_DROP = 75
HEAVY_EXPECTED_THROUGHPUT_DROP = 90
TOTAL_EXPECTED_THROUGHPUT_DROP = 99


# The tuples defined below (should not exceed, must not exceed) are selected
# based on the statistics from multiple execeutions wifi bt coex tests on
# different boards using OTA setup. The numbers were chosen with rather high
# tolerance.
expected_wifibt_coex_throughput_drop = {
        perf_manager.PerfTestTypes.TEST_TYPE_TCP_BIDIRECTIONAL: {
                hostap_config.HostapConfig.MODE_11AC_MIXED: {
                        hostap_config.HostapConfig.FREQ_BAND_5G: {
                                hostap_config.HostapConfig.VHT_CHANNEL_WIDTH_80: {
                                        BluetoothAdapterAudioTests.CONNECTION_STATE_CONNECTED:
                                                (NO_EXPECTED_THROUGHPUT_DROP, LIGHT_EXPECTED_THROUGHPUT_DROP),
                                        BluetoothAdapterAudioTests.CONNECTION_STATE_STREAMING:
                                                (NO_EXPECTED_THROUGHPUT_DROP, LIGHT_EXPECTED_THROUGHPUT_DROP),
                                        BluetoothAdapterAudioTests.CONNECTION_STATE_DISCONNECTED_AGAIN:
                                                (NO_EXPECTED_THROUGHPUT_DROP, LIGHT_EXPECTED_THROUGHPUT_DROP)
                                }
                        }
                },
                hostap_config.HostapConfig.MODE_11G: {
                        hostap_config.HostapConfig.FREQ_BAND_2_4G: {
                                hostap_config.HostapConfig.CHANNEL_WIDTH_22: {
                                        BluetoothAdapterAudioTests.CONNECTION_STATE_CONNECTED:
                                                (NO_EXPECTED_THROUGHPUT_DROP, MODERATE_EXPECTED_THROUGHPUT_DROP),
                                        BluetoothAdapterAudioTests.CONNECTION_STATE_STREAMING:
                                                (HEAVY_EXPECTED_THROUGHPUT_DROP, TOTAL_EXPECTED_THROUGHPUT_DROP),
                                        BluetoothAdapterAudioTests.CONNECTION_STATE_DISCONNECTED_AGAIN:
                                                (NO_EXPECTED_THROUGHPUT_DROP, LIGHT_EXPECTED_THROUGHPUT_DROP)
                                }
                        }
                },
                hostap_config.HostapConfig.MODE_11N_PURE: {
                        hostap_config.HostapConfig.FREQ_BAND_2_4G: {
                                hostap_config.HostapConfig.HT_CHANNEL_WIDTH_20: {
                                        BluetoothAdapterAudioTests.CONNECTION_STATE_CONNECTED:
                                                (SCARCELY_EXPECTED_THROUGHPUT_DROP, SIGNIFICANT_EXPECTED_THROUGHPUT_DROP),
                                        BluetoothAdapterAudioTests.CONNECTION_STATE_STREAMING:
                                                (HEAVY_EXPECTED_THROUGHPUT_DROP, TOTAL_EXPECTED_THROUGHPUT_DROP),
                                        BluetoothAdapterAudioTests.CONNECTION_STATE_DISCONNECTED_AGAIN:
                                                (NO_EXPECTED_THROUGHPUT_DROP, LIGHT_EXPECTED_THROUGHPUT_DROP)
                                },
                                hostap_config.HostapConfig.HT_CHANNEL_WIDTH_40_PLUS: {
                                        BluetoothAdapterAudioTests.CONNECTION_STATE_CONNECTED:
                                                (LIGHT_EXPECTED_THROUGHPUT_DROP, SIGNIFICANT_EXPECTED_THROUGHPUT_DROP),
                                        BluetoothAdapterAudioTests.CONNECTION_STATE_STREAMING:
                                                (MODERATE_EXPECTED_THROUGHPUT_DROP, SIGNIFICANT_EXPECTED_THROUGHPUT_DROP),
                                        BluetoothAdapterAudioTests.CONNECTION_STATE_DISCONNECTED_AGAIN:
                                                (LIGHT_EXPECTED_THROUGHPUT_DROP, MODERATE_EXPECTED_THROUGHPUT_DROP)
                                }
                        },
                        hostap_config.HostapConfig.FREQ_BAND_5G: {
                                hostap_config.HostapConfig.HT_CHANNEL_WIDTH_20: {
                                        BluetoothAdapterAudioTests.CONNECTION_STATE_CONNECTED:
                                                (NO_EXPECTED_THROUGHPUT_DROP, LIGHT_EXPECTED_THROUGHPUT_DROP),
                                        BluetoothAdapterAudioTests.CONNECTION_STATE_STREAMING:
                                                (NO_EXPECTED_THROUGHPUT_DROP, LIGHT_EXPECTED_THROUGHPUT_DROP),
                                        BluetoothAdapterAudioTests.CONNECTION_STATE_DISCONNECTED_AGAIN:
                                                (NO_EXPECTED_THROUGHPUT_DROP, LIGHT_EXPECTED_THROUGHPUT_DROP)
                                },
                                hostap_config.HostapConfig.HT_CHANNEL_WIDTH_40_PLUS: {
                                        BluetoothAdapterAudioTests.CONNECTION_STATE_CONNECTED:
                                                (NO_EXPECTED_THROUGHPUT_DROP, LIGHT_EXPECTED_THROUGHPUT_DROP),
                                        BluetoothAdapterAudioTests.CONNECTION_STATE_STREAMING:
                                                (NO_EXPECTED_THROUGHPUT_DROP, LIGHT_EXPECTED_THROUGHPUT_DROP),
                                        BluetoothAdapterAudioTests.CONNECTION_STATE_DISCONNECTED_AGAIN:
                                                (NO_EXPECTED_THROUGHPUT_DROP, LIGHT_EXPECTED_THROUGHPUT_DROP)
                                }
                        }
                },
        },
        perf_manager.PerfTestTypes.TEST_TYPE_TCP_RX: {
                hostap_config.HostapConfig.MODE_11AC_MIXED: {
                        hostap_config.HostapConfig.FREQ_BAND_5G: {
                                hostap_config.HostapConfig.VHT_CHANNEL_WIDTH_80: {
                                        BluetoothAdapterAudioTests.CONNECTION_STATE_CONNECTED:
                                                (NO_EXPECTED_THROUGHPUT_DROP, MODERATE_EXPECTED_THROUGHPUT_DROP),
                                        BluetoothAdapterAudioTests.CONNECTION_STATE_STREAMING:
                                                (NO_EXPECTED_THROUGHPUT_DROP, MODERATE_EXPECTED_THROUGHPUT_DROP),
                                        BluetoothAdapterAudioTests.CONNECTION_STATE_DISCONNECTED_AGAIN:
                                                (NO_EXPECTED_THROUGHPUT_DROP, MODERATE_EXPECTED_THROUGHPUT_DROP)
                                }
                        }
                },
                hostap_config.HostapConfig.MODE_11G: {
                        hostap_config.HostapConfig.FREQ_BAND_2_4G: {
                                hostap_config.HostapConfig.CHANNEL_WIDTH_22: {
                                        BluetoothAdapterAudioTests.CONNECTION_STATE_CONNECTED:
                                                (NO_EXPECTED_THROUGHPUT_DROP, MODERATE_EXPECTED_THROUGHPUT_DROP),
                                        BluetoothAdapterAudioTests.CONNECTION_STATE_STREAMING:
                                                (HEAVY_EXPECTED_THROUGHPUT_DROP, TOTAL_EXPECTED_THROUGHPUT_DROP),
                                        BluetoothAdapterAudioTests.CONNECTION_STATE_DISCONNECTED_AGAIN:
                                                (NO_EXPECTED_THROUGHPUT_DROP, LIGHT_EXPECTED_THROUGHPUT_DROP)
                                }
                        }
                },
                hostap_config.HostapConfig.MODE_11N_PURE: {
                        hostap_config.HostapConfig.FREQ_BAND_2_4G: {
                                hostap_config.HostapConfig.HT_CHANNEL_WIDTH_20: {
                                        BluetoothAdapterAudioTests.CONNECTION_STATE_CONNECTED:
                                                (SCARCELY_EXPECTED_THROUGHPUT_DROP, SIGNIFICANT_EXPECTED_THROUGHPUT_DROP),
                                        BluetoothAdapterAudioTests.CONNECTION_STATE_STREAMING:
                                                (HEAVY_EXPECTED_THROUGHPUT_DROP, TOTAL_EXPECTED_THROUGHPUT_DROP),
                                        BluetoothAdapterAudioTests.CONNECTION_STATE_DISCONNECTED_AGAIN:
                                                (NO_EXPECTED_THROUGHPUT_DROP, LIGHT_EXPECTED_THROUGHPUT_DROP)
                                },
                                hostap_config.HostapConfig.HT_CHANNEL_WIDTH_40_PLUS: {
                                        BluetoothAdapterAudioTests.CONNECTION_STATE_CONNECTED:
                                                (LIGHT_EXPECTED_THROUGHPUT_DROP, MODERATE_EXPECTED_THROUGHPUT_DROP),
                                        BluetoothAdapterAudioTests.CONNECTION_STATE_STREAMING:
                                                (MODERATE_EXPECTED_THROUGHPUT_DROP, SIGNIFICANT_EXPECTED_THROUGHPUT_DROP),
                                        BluetoothAdapterAudioTests.CONNECTION_STATE_DISCONNECTED_AGAIN:
                                                (LIGHT_EXPECTED_THROUGHPUT_DROP, MODERATE_EXPECTED_THROUGHPUT_DROP)
                                }
                        },
                        hostap_config.HostapConfig.FREQ_BAND_5G: {
                                hostap_config.HostapConfig.HT_CHANNEL_WIDTH_20: {
                                        BluetoothAdapterAudioTests.CONNECTION_STATE_CONNECTED:
                                                (NO_EXPECTED_THROUGHPUT_DROP, LIGHT_EXPECTED_THROUGHPUT_DROP),
                                        BluetoothAdapterAudioTests.CONNECTION_STATE_STREAMING:
                                                (NO_EXPECTED_THROUGHPUT_DROP, LIGHT_EXPECTED_THROUGHPUT_DROP),
                                        BluetoothAdapterAudioTests.CONNECTION_STATE_DISCONNECTED_AGAIN:
                                                (NO_EXPECTED_THROUGHPUT_DROP, LIGHT_EXPECTED_THROUGHPUT_DROP)
                                },
                                hostap_config.HostapConfig.HT_CHANNEL_WIDTH_40_PLUS: {
                                        BluetoothAdapterAudioTests.CONNECTION_STATE_CONNECTED:
                                                (NO_EXPECTED_THROUGHPUT_DROP, LIGHT_EXPECTED_THROUGHPUT_DROP),
                                        BluetoothAdapterAudioTests.CONNECTION_STATE_STREAMING:
                                                (NO_EXPECTED_THROUGHPUT_DROP, LIGHT_EXPECTED_THROUGHPUT_DROP),
                                        BluetoothAdapterAudioTests.CONNECTION_STATE_DISCONNECTED_AGAIN:
                                                (NO_EXPECTED_THROUGHPUT_DROP, LIGHT_EXPECTED_THROUGHPUT_DROP)
                                }
                        }
                }
        },
        perf_manager.PerfTestTypes.TEST_TYPE_TCP_TX: {
                hostap_config.HostapConfig.MODE_11AC_MIXED: {
                        hostap_config.HostapConfig.FREQ_BAND_5G: {
                                hostap_config.HostapConfig.VHT_CHANNEL_WIDTH_80: {
                                        BluetoothAdapterAudioTests.CONNECTION_STATE_CONNECTED:
                                                (NO_EXPECTED_THROUGHPUT_DROP, LIGHT_EXPECTED_THROUGHPUT_DROP),
                                        BluetoothAdapterAudioTests.CONNECTION_STATE_STREAMING:
                                                (NO_EXPECTED_THROUGHPUT_DROP, LIGHT_EXPECTED_THROUGHPUT_DROP),
                                        BluetoothAdapterAudioTests.CONNECTION_STATE_DISCONNECTED_AGAIN:
                                                (NO_EXPECTED_THROUGHPUT_DROP, LIGHT_EXPECTED_THROUGHPUT_DROP)
                                }
                        }
                },
                hostap_config.HostapConfig.MODE_11G: {
                        hostap_config.HostapConfig.FREQ_BAND_2_4G: {
                                hostap_config.HostapConfig.CHANNEL_WIDTH_22: {
                                        BluetoothAdapterAudioTests.CONNECTION_STATE_CONNECTED:
                                                (NO_EXPECTED_THROUGHPUT_DROP, MODERATE_EXPECTED_THROUGHPUT_DROP), # fixed
                                        BluetoothAdapterAudioTests.CONNECTION_STATE_STREAMING:
                                                (HEAVY_EXPECTED_THROUGHPUT_DROP, TOTAL_EXPECTED_THROUGHPUT_DROP),
                                        BluetoothAdapterAudioTests.CONNECTION_STATE_DISCONNECTED_AGAIN:
                                                (NO_EXPECTED_THROUGHPUT_DROP, LIGHT_EXPECTED_THROUGHPUT_DROP)
                                }
                        }
                },
                hostap_config.HostapConfig.MODE_11N_PURE: {
                        hostap_config.HostapConfig.FREQ_BAND_2_4G: {
                                hostap_config.HostapConfig.HT_CHANNEL_WIDTH_20: {
                                        BluetoothAdapterAudioTests.CONNECTION_STATE_CONNECTED:
                                                (SCARCELY_EXPECTED_THROUGHPUT_DROP, MODERATE_EXPECTED_THROUGHPUT_DROP),
                                        BluetoothAdapterAudioTests.CONNECTION_STATE_STREAMING:
                                                (HEAVY_EXPECTED_THROUGHPUT_DROP, TOTAL_EXPECTED_THROUGHPUT_DROP),
                                        BluetoothAdapterAudioTests.CONNECTION_STATE_DISCONNECTED_AGAIN:
                                                (NO_EXPECTED_THROUGHPUT_DROP, LIGHT_EXPECTED_THROUGHPUT_DROP)
                                },
                                hostap_config.HostapConfig.HT_CHANNEL_WIDTH_40_PLUS: {
                                        BluetoothAdapterAudioTests.CONNECTION_STATE_CONNECTED:
                                                (SCARCELY_EXPECTED_THROUGHPUT_DROP, MODERATE_EXPECTED_THROUGHPUT_DROP),
                                        BluetoothAdapterAudioTests.CONNECTION_STATE_STREAMING:
                                                (MODERATE_EXPECTED_THROUGHPUT_DROP, SIGNIFICANT_EXPECTED_THROUGHPUT_DROP),
                                        BluetoothAdapterAudioTests.CONNECTION_STATE_DISCONNECTED_AGAIN:
                                                (NO_EXPECTED_THROUGHPUT_DROP, LIGHT_EXPECTED_THROUGHPUT_DROP)
                                }
                        },
                        hostap_config.HostapConfig.FREQ_BAND_5G: {
                                hostap_config.HostapConfig.HT_CHANNEL_WIDTH_20: {
                                        BluetoothAdapterAudioTests.CONNECTION_STATE_CONNECTED:
                                                (NO_EXPECTED_THROUGHPUT_DROP, LIGHT_EXPECTED_THROUGHPUT_DROP),
                                        BluetoothAdapterAudioTests.CONNECTION_STATE_STREAMING:
                                                (NO_EXPECTED_THROUGHPUT_DROP, LIGHT_EXPECTED_THROUGHPUT_DROP),
                                        BluetoothAdapterAudioTests.CONNECTION_STATE_DISCONNECTED_AGAIN:
                                                (NO_EXPECTED_THROUGHPUT_DROP, LIGHT_EXPECTED_THROUGHPUT_DROP)
                                },
                                hostap_config.HostapConfig.HT_CHANNEL_WIDTH_40_PLUS: {
                                        BluetoothAdapterAudioTests.CONNECTION_STATE_CONNECTED:
                                                (NO_EXPECTED_THROUGHPUT_DROP, LIGHT_EXPECTED_THROUGHPUT_DROP),
                                        BluetoothAdapterAudioTests.CONNECTION_STATE_STREAMING:
                                                (NO_EXPECTED_THROUGHPUT_DROP, LIGHT_EXPECTED_THROUGHPUT_DROP),
                                        BluetoothAdapterAudioTests.CONNECTION_STATE_DISCONNECTED_AGAIN:
                                                (NO_EXPECTED_THROUGHPUT_DROP, LIGHT_EXPECTED_THROUGHPUT_DROP)
                                }
                        }
                }
        },
        perf_manager.PerfTestTypes.TEST_TYPE_UDP_BIDIRECTIONAL: {
                hostap_config.HostapConfig.MODE_11AC_MIXED: {
                        hostap_config.HostapConfig.FREQ_BAND_5G: {
                                hostap_config.HostapConfig.VHT_CHANNEL_WIDTH_80: {
                                        BluetoothAdapterAudioTests.CONNECTION_STATE_CONNECTED:
                                                (NO_EXPECTED_THROUGHPUT_DROP, LIGHT_EXPECTED_THROUGHPUT_DROP),
                                        BluetoothAdapterAudioTests.CONNECTION_STATE_STREAMING:
                                                (NO_EXPECTED_THROUGHPUT_DROP, LIGHT_EXPECTED_THROUGHPUT_DROP),
                                        BluetoothAdapterAudioTests.CONNECTION_STATE_DISCONNECTED_AGAIN:
                                                (NO_EXPECTED_THROUGHPUT_DROP, MODERATE_EXPECTED_THROUGHPUT_DROP)
                                }
                        }
                },
                hostap_config.HostapConfig.MODE_11G: {
                        hostap_config.HostapConfig.FREQ_BAND_2_4G: {
                                hostap_config.HostapConfig.CHANNEL_WIDTH_22: {
                                        BluetoothAdapterAudioTests.CONNECTION_STATE_CONNECTED:
                                                (NO_EXPECTED_THROUGHPUT_DROP, MODERATE_EXPECTED_THROUGHPUT_DROP),
                                        BluetoothAdapterAudioTests.CONNECTION_STATE_STREAMING:
                                                (HEAVY_EXPECTED_THROUGHPUT_DROP, TOTAL_EXPECTED_THROUGHPUT_DROP),
                                        BluetoothAdapterAudioTests.CONNECTION_STATE_DISCONNECTED_AGAIN:
                                                (NO_EXPECTED_THROUGHPUT_DROP, LIGHT_EXPECTED_THROUGHPUT_DROP)
                                }
                        }
                },
                hostap_config.HostapConfig.MODE_11N_PURE: {
                        hostap_config.HostapConfig.FREQ_BAND_2_4G: {
                                hostap_config.HostapConfig.HT_CHANNEL_WIDTH_20: {
                                        BluetoothAdapterAudioTests.CONNECTION_STATE_CONNECTED:
                                                (LIGHT_EXPECTED_THROUGHPUT_DROP, MODERATE_EXPECTED_THROUGHPUT_DROP),
                                        BluetoothAdapterAudioTests.CONNECTION_STATE_STREAMING:
                                                (HEAVY_EXPECTED_THROUGHPUT_DROP, TOTAL_EXPECTED_THROUGHPUT_DROP),
                                        BluetoothAdapterAudioTests.CONNECTION_STATE_DISCONNECTED_AGAIN:
                                                (NO_EXPECTED_THROUGHPUT_DROP, LIGHT_EXPECTED_THROUGHPUT_DROP)
                                },
                                hostap_config.HostapConfig.HT_CHANNEL_WIDTH_40_PLUS: {
                                        BluetoothAdapterAudioTests.CONNECTION_STATE_CONNECTED:
                                                (SCARCELY_EXPECTED_THROUGHPUT_DROP, MODERATE_EXPECTED_THROUGHPUT_DROP),
                                        BluetoothAdapterAudioTests.CONNECTION_STATE_STREAMING:
                                                (MODERATE_EXPECTED_THROUGHPUT_DROP, SIGNIFICANT_EXPECTED_THROUGHPUT_DROP),
                                        BluetoothAdapterAudioTests.CONNECTION_STATE_DISCONNECTED_AGAIN:
                                                (NO_EXPECTED_THROUGHPUT_DROP, MODERATE_EXPECTED_THROUGHPUT_DROP)
                                }
                        },
                        hostap_config.HostapConfig.FREQ_BAND_5G: {
                                hostap_config.HostapConfig.HT_CHANNEL_WIDTH_20: {
                                        BluetoothAdapterAudioTests.CONNECTION_STATE_CONNECTED:
                                                (NO_EXPECTED_THROUGHPUT_DROP, LIGHT_EXPECTED_THROUGHPUT_DROP),
                                        BluetoothAdapterAudioTests.CONNECTION_STATE_STREAMING:
                                                (NO_EXPECTED_THROUGHPUT_DROP, LIGHT_EXPECTED_THROUGHPUT_DROP),
                                        BluetoothAdapterAudioTests.CONNECTION_STATE_DISCONNECTED_AGAIN:
                                                (NO_EXPECTED_THROUGHPUT_DROP, LIGHT_EXPECTED_THROUGHPUT_DROP)
                                },
                                hostap_config.HostapConfig.HT_CHANNEL_WIDTH_40_PLUS: {
                                        BluetoothAdapterAudioTests.CONNECTION_STATE_CONNECTED:
                                                (NO_EXPECTED_THROUGHPUT_DROP, LIGHT_EXPECTED_THROUGHPUT_DROP),
                                        BluetoothAdapterAudioTests.CONNECTION_STATE_STREAMING:
                                                (NO_EXPECTED_THROUGHPUT_DROP, LIGHT_EXPECTED_THROUGHPUT_DROP),
                                        BluetoothAdapterAudioTests.CONNECTION_STATE_DISCONNECTED_AGAIN:
                                                (NO_EXPECTED_THROUGHPUT_DROP, LIGHT_EXPECTED_THROUGHPUT_DROP)
                                }
                        }
                }
        },
        perf_manager.PerfTestTypes.TEST_TYPE_UDP_RX: {
                hostap_config.HostapConfig.MODE_11AC_MIXED: {
                        hostap_config.HostapConfig.FREQ_BAND_5G: {
                                hostap_config.HostapConfig.VHT_CHANNEL_WIDTH_80: {
                                        BluetoothAdapterAudioTests.CONNECTION_STATE_CONNECTED:
                                                (NO_EXPECTED_THROUGHPUT_DROP, LIGHT_EXPECTED_THROUGHPUT_DROP),
                                        BluetoothAdapterAudioTests.CONNECTION_STATE_STREAMING:
                                                (SCARCELY_EXPECTED_THROUGHPUT_DROP, LIGHT_EXPECTED_THROUGHPUT_DROP),
                                        BluetoothAdapterAudioTests.CONNECTION_STATE_DISCONNECTED_AGAIN:
                                                (NO_EXPECTED_THROUGHPUT_DROP, LIGHT_EXPECTED_THROUGHPUT_DROP)
                                }
                        }
                },
                hostap_config.HostapConfig.MODE_11G: {
                        hostap_config.HostapConfig.FREQ_BAND_2_4G: {
                                hostap_config.HostapConfig.CHANNEL_WIDTH_22: {
                                        BluetoothAdapterAudioTests.CONNECTION_STATE_CONNECTED:
                                                (NO_EXPECTED_THROUGHPUT_DROP, LIGHT_EXPECTED_THROUGHPUT_DROP),
                                        BluetoothAdapterAudioTests.CONNECTION_STATE_STREAMING:
                                                (HEAVY_EXPECTED_THROUGHPUT_DROP, TOTAL_EXPECTED_THROUGHPUT_DROP),
                                        BluetoothAdapterAudioTests.CONNECTION_STATE_DISCONNECTED_AGAIN:
                                                (NO_EXPECTED_THROUGHPUT_DROP, LIGHT_EXPECTED_THROUGHPUT_DROP)
                                }
                        }
                },
                hostap_config.HostapConfig.MODE_11N_PURE: {
                        hostap_config.HostapConfig.FREQ_BAND_2_4G: {
                                hostap_config.HostapConfig.HT_CHANNEL_WIDTH_20: {
                                        BluetoothAdapterAudioTests.CONNECTION_STATE_CONNECTED:
                                                (MODERATE_EXPECTED_THROUGHPUT_DROP, SIGNIFICANT_EXPECTED_THROUGHPUT_DROP),
                                        BluetoothAdapterAudioTests.CONNECTION_STATE_STREAMING:
                                                (HEAVY_EXPECTED_THROUGHPUT_DROP, TOTAL_EXPECTED_THROUGHPUT_DROP),
                                        BluetoothAdapterAudioTests.CONNECTION_STATE_DISCONNECTED_AGAIN:
                                                (NO_EXPECTED_THROUGHPUT_DROP, LIGHT_EXPECTED_THROUGHPUT_DROP)
                                },
                                hostap_config.HostapConfig.HT_CHANNEL_WIDTH_40_PLUS: {
                                        BluetoothAdapterAudioTests.CONNECTION_STATE_CONNECTED:
                                                (SCARCELY_EXPECTED_THROUGHPUT_DROP, LIGHT_EXPECTED_THROUGHPUT_DROP),
                                        BluetoothAdapterAudioTests.CONNECTION_STATE_STREAMING:
                                                (MODERATE_EXPECTED_THROUGHPUT_DROP, SIGNIFICANT_EXPECTED_THROUGHPUT_DROP),
                                        BluetoothAdapterAudioTests.CONNECTION_STATE_DISCONNECTED_AGAIN:
                                                (NO_EXPECTED_THROUGHPUT_DROP, LIGHT_EXPECTED_THROUGHPUT_DROP)
                                }
                        },
                        hostap_config.HostapConfig.FREQ_BAND_5G: {
                                hostap_config.HostapConfig.HT_CHANNEL_WIDTH_20: {
                                        BluetoothAdapterAudioTests.CONNECTION_STATE_CONNECTED:
                                                (NO_EXPECTED_THROUGHPUT_DROP, LIGHT_EXPECTED_THROUGHPUT_DROP),
                                        BluetoothAdapterAudioTests.CONNECTION_STATE_STREAMING:
                                                (NO_EXPECTED_THROUGHPUT_DROP, LIGHT_EXPECTED_THROUGHPUT_DROP),
                                        BluetoothAdapterAudioTests.CONNECTION_STATE_DISCONNECTED_AGAIN:
                                                (NO_EXPECTED_THROUGHPUT_DROP, LIGHT_EXPECTED_THROUGHPUT_DROP)
                                },
                                hostap_config.HostapConfig.HT_CHANNEL_WIDTH_40_PLUS: {
                                        BluetoothAdapterAudioTests.CONNECTION_STATE_CONNECTED:
                                                (NO_EXPECTED_THROUGHPUT_DROP, LIGHT_EXPECTED_THROUGHPUT_DROP),
                                        BluetoothAdapterAudioTests.CONNECTION_STATE_STREAMING:
                                                (NO_EXPECTED_THROUGHPUT_DROP, LIGHT_EXPECTED_THROUGHPUT_DROP),
                                        BluetoothAdapterAudioTests.CONNECTION_STATE_DISCONNECTED_AGAIN:
                                                (NO_EXPECTED_THROUGHPUT_DROP, LIGHT_EXPECTED_THROUGHPUT_DROP)
                                }
                        }
                }
        },
        perf_manager.PerfTestTypes.TEST_TYPE_UDP_TX: {
                hostap_config.HostapConfig.MODE_11AC_MIXED: {
                        hostap_config.HostapConfig.FREQ_BAND_5G: {
                                hostap_config.HostapConfig.VHT_CHANNEL_WIDTH_80: {
                                        BluetoothAdapterAudioTests.CONNECTION_STATE_CONNECTED:
                                                (NO_EXPECTED_THROUGHPUT_DROP, LIGHT_EXPECTED_THROUGHPUT_DROP),
                                        BluetoothAdapterAudioTests.CONNECTION_STATE_STREAMING:
                                                (SCARCELY_EXPECTED_THROUGHPUT_DROP, LIGHT_EXPECTED_THROUGHPUT_DROP),
                                        BluetoothAdapterAudioTests.CONNECTION_STATE_DISCONNECTED_AGAIN:
                                                (NO_EXPECTED_THROUGHPUT_DROP, LIGHT_EXPECTED_THROUGHPUT_DROP)
                                }
                        }
                },
                hostap_config.HostapConfig.MODE_11G: {
                        hostap_config.HostapConfig.FREQ_BAND_2_4G: {
                                hostap_config.HostapConfig.CHANNEL_WIDTH_22: {
                                        BluetoothAdapterAudioTests.CONNECTION_STATE_CONNECTED:
                                                (NO_EXPECTED_THROUGHPUT_DROP, MODERATE_EXPECTED_THROUGHPUT_DROP),
                                        BluetoothAdapterAudioTests.CONNECTION_STATE_STREAMING:
                                                (HEAVY_EXPECTED_THROUGHPUT_DROP, TOTAL_EXPECTED_THROUGHPUT_DROP),
                                        BluetoothAdapterAudioTests.CONNECTION_STATE_DISCONNECTED_AGAIN:
                                                (NO_EXPECTED_THROUGHPUT_DROP, MODERATE_EXPECTED_THROUGHPUT_DROP)
                                }
                        }
                },
                hostap_config.HostapConfig.MODE_11N_PURE: {
                        hostap_config.HostapConfig.FREQ_BAND_2_4G: {
                                hostap_config.HostapConfig.HT_CHANNEL_WIDTH_20: {
                                        BluetoothAdapterAudioTests.CONNECTION_STATE_CONNECTED:
                                                (SCARCELY_EXPECTED_THROUGHPUT_DROP, SIGNIFICANT_EXPECTED_THROUGHPUT_DROP),
                                        BluetoothAdapterAudioTests.CONNECTION_STATE_STREAMING:
                                                (HEAVY_EXPECTED_THROUGHPUT_DROP, TOTAL_EXPECTED_THROUGHPUT_DROP),
                                        BluetoothAdapterAudioTests.CONNECTION_STATE_DISCONNECTED_AGAIN:
                                                (NO_EXPECTED_THROUGHPUT_DROP, LIGHT_EXPECTED_THROUGHPUT_DROP)
                                },
                                hostap_config.HostapConfig.HT_CHANNEL_WIDTH_40_PLUS: {
                                        BluetoothAdapterAudioTests.CONNECTION_STATE_CONNECTED:
                                                (SCARCELY_EXPECTED_THROUGHPUT_DROP, MODERATE_EXPECTED_THROUGHPUT_DROP),
                                        BluetoothAdapterAudioTests.CONNECTION_STATE_STREAMING:
                                                (LIGHT_EXPECTED_THROUGHPUT_DROP, SIGNIFICANT_EXPECTED_THROUGHPUT_DROP),
                                        BluetoothAdapterAudioTests.CONNECTION_STATE_DISCONNECTED_AGAIN:
                                                (NO_EXPECTED_THROUGHPUT_DROP, LIGHT_EXPECTED_THROUGHPUT_DROP)
                                }
                        },
                        hostap_config.HostapConfig.FREQ_BAND_5G: {
                                hostap_config.HostapConfig.HT_CHANNEL_WIDTH_20: {
                                        BluetoothAdapterAudioTests.CONNECTION_STATE_CONNECTED:
                                                (NO_EXPECTED_THROUGHPUT_DROP, LIGHT_EXPECTED_THROUGHPUT_DROP),
                                        BluetoothAdapterAudioTests.CONNECTION_STATE_STREAMING:
                                                (NO_EXPECTED_THROUGHPUT_DROP, LIGHT_EXPECTED_THROUGHPUT_DROP),
                                        BluetoothAdapterAudioTests.CONNECTION_STATE_DISCONNECTED_AGAIN:
                                                (NO_EXPECTED_THROUGHPUT_DROP, LIGHT_EXPECTED_THROUGHPUT_DROP)
                                },
                                hostap_config.HostapConfig.HT_CHANNEL_WIDTH_40_PLUS: {
                                        BluetoothAdapterAudioTests.CONNECTION_STATE_CONNECTED:
                                                (NO_EXPECTED_THROUGHPUT_DROP, LIGHT_EXPECTED_THROUGHPUT_DROP),
                                        BluetoothAdapterAudioTests.CONNECTION_STATE_STREAMING:
                                                (NO_EXPECTED_THROUGHPUT_DROP, LIGHT_EXPECTED_THROUGHPUT_DROP),
                                        BluetoothAdapterAudioTests.CONNECTION_STATE_DISCONNECTED_AGAIN:
                                                (NO_EXPECTED_THROUGHPUT_DROP, LIGHT_EXPECTED_THROUGHPUT_DROP)
                                }
                        }
                }
        }
}

def get_expected_wifibt_coex_throughput_drop(test_type, ap_config, bt_tag):
    """returns the expected throughput drop for WiFI BT coex tests.

    @param test_type: the PerfTestTypes test type.

    @param ap_config: the AP configuration

    @param bt_tag: string for BT operation

    @return a tuple of two integers (should, must) of the expected throughput drop percentage

    """
    mode = ap_config.mode
    channel_width = ap_config.channel_width
    freq_band = ap_config.freq_band
    if test_type in expected_wifibt_coex_throughput_drop:
        if mode in expected_wifibt_coex_throughput_drop[test_type]:
            if freq_band in expected_wifibt_coex_throughput_drop[test_type][mode]:
                if channel_width in expected_wifibt_coex_throughput_drop[test_type][mode][freq_band]:
                    if bt_tag in expected_wifibt_coex_throughput_drop[test_type][mode][freq_band][channel_width]:
                        return expected_wifibt_coex_throughput_drop[test_type][mode][freq_band][channel_width][bt_tag]

    ret_mode = hostap_config.HostapConfig.VHT_NAMES[channel_width]

    if ret_mode is None:
        ret_mode = hostap_config.HostapConfig.HT_NAMES[channel_width]
    raise error.TestFail(
            'Failed to find the expected throughput drop from the key values, test type = %s, freq band = %s, mode = %s, channel width = %s'
            % (test_type, freq_band, mode, ret_mode))


max_wifibt_coex_throughput_drop_expectation_for_boards = {
        "guybrush": {
                perf_manager.PerfTestTypes.TEST_TYPE_UDP_TX: {
                        hostap_config.HostapConfig.MODE_11G: {
                                hostap_config.HostapConfig.FREQ_BAND_2_4G: {
                                        hostap_config.HostapConfig.CHANNEL_WIDTH_22: {
                                                BluetoothAdapterAudioTests.CONNECTION_STATE_CONNECTED: SIGNIFICANT_EXPECTED_THROUGHPUT_DROP
                                        }
                                }
                        }
                },
                perf_manager.PerfTestTypes.TEST_TYPE_TCP_TX: {
                        hostap_config.HostapConfig.MODE_11N_PURE: {
                                hostap_config.HostapConfig.FREQ_BAND_2_4G: {
                                        hostap_config.HostapConfig.HT_CHANNEL_WIDTH_40_PLUS: {
                                                BluetoothAdapterAudioTests.CONNECTION_STATE_STREAMING: HEAVY_EXPECTED_THROUGHPUT_DROP
                                        }
                                },
                                hostap_config.HostapConfig.FREQ_BAND_5G: {
                                        hostap_config.HostapConfig.HT_CHANNEL_WIDTH_20: {
                                                BluetoothAdapterAudioTests.CONNECTION_STATE_DISCONNECTED_AGAIN: MODERATE_EXPECTED_THROUGHPUT_DROP
                                        }
                                }
                        }
                },
                perf_manager.PerfTestTypes.TEST_TYPE_TCP_RX: {
                        hostap_config.HostapConfig.MODE_11N_PURE: {
                                hostap_config.HostapConfig.FREQ_BAND_5G: {
                                        hostap_config.HostapConfig.HT_CHANNEL_WIDTH_20: {
                                                BluetoothAdapterAudioTests.CONNECTION_STATE_DISCONNECTED_AGAIN: MODERATE_EXPECTED_THROUGHPUT_DROP
                                        }
                                },
                                hostap_config.HostapConfig.FREQ_BAND_2_4G: {
                                        hostap_config.HostapConfig.HT_CHANNEL_WIDTH_40_PLUS: {
                                                BluetoothAdapterAudioTests.CONNECTION_STATE_CONNECTED: SIGNIFICANT_EXPECTED_THROUGHPUT_DROP
                                        }
                                }
                        }
                },
                perf_manager.PerfTestTypes.TEST_TYPE_UDP_BIDIRECTIONAL: {
                        hostap_config.HostapConfig.MODE_11AC_MIXED: {
                                hostap_config.HostapConfig.FREQ_BAND_5G: {
                                        hostap_config.HostapConfig.VHT_CHANNEL_WIDTH_80: {
                                                BluetoothAdapterAudioTests.CONNECTION_STATE_CONNECTED: MODERATE_EXPECTED_THROUGHPUT_DROP
                                        }
                                }
                        },
                        hostap_config.HostapConfig.MODE_11N_PURE: {
                                hostap_config.HostapConfig.FREQ_BAND_2_4G: {
                                        hostap_config.HostapConfig.HT_CHANNEL_WIDTH_40_PLUS: {
                                                BluetoothAdapterAudioTests.CONNECTION_STATE_CONNECTED: SIGNIFICANT_EXPECTED_THROUGHPUT_DROP,
                                                BluetoothAdapterAudioTests.CONNECTION_STATE_STREAMING: HEAVY_EXPECTED_THROUGHPUT_DROP
                                        }
                                }
                        },
                        hostap_config.HostapConfig.MODE_11G: {
                                hostap_config.HostapConfig.FREQ_BAND_2_4G: {
                                        hostap_config.HostapConfig.CHANNEL_WIDTH_22: {
                                                BluetoothAdapterAudioTests.CONNECTION_STATE_CONNECTED: SIGNIFICANT_EXPECTED_THROUGHPUT_DROP
                                        }
                                }
                        }
                },
                perf_manager.PerfTestTypes.TEST_TYPE_TCP_BIDIRECTIONAL: {
                        hostap_config.HostapConfig.MODE_11AC_MIXED: {
                                hostap_config.HostapConfig.FREQ_BAND_5G: {
                                        hostap_config.HostapConfig.VHT_CHANNEL_WIDTH_80: {
                                                BluetoothAdapterAudioTests.CONNECTION_STATE_CONNECTED: MODERATE_EXPECTED_THROUGHPUT_DROP,
                                                BluetoothAdapterAudioTests.CONNECTION_STATE_STREAMING: MODERATE_EXPECTED_THROUGHPUT_DROP,
                                                BluetoothAdapterAudioTests.CONNECTION_STATE_DISCONNECTED_AGAIN: MODERATE_EXPECTED_THROUGHPUT_DROP
                                        }
                                }
                        },
                        hostap_config.HostapConfig.MODE_11N_PURE: {
                                hostap_config.HostapConfig.FREQ_BAND_5G: {
                                        hostap_config.HostapConfig.HT_CHANNEL_WIDTH_20: {
                                                BluetoothAdapterAudioTests.CONNECTION_STATE_STREAMING: MODERATE_EXPECTED_THROUGHPUT_DROP
                                        }
                                },
                                hostap_config.HostapConfig.FREQ_BAND_2_4G: {
                                        hostap_config.HostapConfig.HT_CHANNEL_WIDTH_40_PLUS: {
                                                BluetoothAdapterAudioTests.CONNECTION_STATE_STREAMING: SIGNIFICANT_EXPECTED_THROUGHPUT_DROP
                                        }
                                }
                        }
                }
        },
        "nissa": {
                perf_manager.PerfTestTypes.TEST_TYPE_UDP_TX: {
                        hostap_config.HostapConfig.MODE_11G: {
                                hostap_config.HostapConfig.FREQ_BAND_2_4G: {
                                        hostap_config.HostapConfig.CHANNEL_WIDTH_22: {
                                                BluetoothAdapterAudioTests.CONNECTION_STATE_CONNECTED: SIGNIFICANT_EXPECTED_THROUGHPUT_DROP
                                        }
                                },
                                hostap_config.HostapConfig.FREQ_BAND_5G: {
                                        hostap_config.HostapConfig.HT_CHANNEL_WIDTH_20: {
                                                BluetoothAdapterAudioTests.CONNECTION_STATE_STREAMING: MODERATE_EXPECTED_THROUGHPUT_DROP,
                                                BluetoothAdapterAudioTests.CONNECTION_STATE_DISCONNECTED_AGAIN: MODERATE_EXPECTED_THROUGHPUT_DROP
                                        }
                                }
                        }
                },
                perf_manager.PerfTestTypes.TEST_TYPE_TCP_TX: {
                        hostap_config.HostapConfig.MODE_11G: {
                                hostap_config.HostapConfig.FREQ_BAND_2_4G: {
                                        hostap_config.HostapConfig.CHANNEL_WIDTH_22: {
                                                BluetoothAdapterAudioTests.CONNECTION_STATE_DISCONNECTED_AGAIN: MODERATE_EXPECTED_THROUGHPUT_DROP
                                        }
                                }
                        }
                },
                perf_manager.PerfTestTypes.TEST_TYPE_TCP_BIDIRECTIONAL: {
                        hostap_config.HostapConfig.MODE_11AC_MIXED: {
                                hostap_config.HostapConfig.FREQ_BAND_5G: {
                                        hostap_config.HostapConfig.VHT_CHANNEL_WIDTH_80: {
                                                BluetoothAdapterAudioTests.CONNECTION_STATE_STREAMING: MODERATE_EXPECTED_THROUGHPUT_DROP,
                                                BluetoothAdapterAudioTests.CONNECTION_STATE_DISCONNECTED_AGAIN: MODERATE_EXPECTED_THROUGHPUT_DROP
                                        }
                                }
                        }
                }
        },
        "dedede": {
                perf_manager.PerfTestTypes.TEST_TYPE_UDP_TX: {
                        hostap_config.HostapConfig.MODE_11G: {
                                hostap_config.HostapConfig.FREQ_BAND_2_4G: {
                                        hostap_config.HostapConfig.CHANNEL_WIDTH_22: {
                                                BluetoothAdapterAudioTests.CONNECTION_STATE_CONNECTED: SIGNIFICANT_EXPECTED_THROUGHPUT_DROP
                                        }
                                }
                        }
                },
                perf_manager.PerfTestTypes.TEST_TYPE_TCP_TX: {
                        hostap_config.HostapConfig.MODE_11G: {
                                hostap_config.HostapConfig.FREQ_BAND_2_4G: {
                                        hostap_config.HostapConfig.CHANNEL_WIDTH_22: {
                                                BluetoothAdapterAudioTests.CONNECTION_STATE_DISCONNECTED_AGAIN: MODERATE_EXPECTED_THROUGHPUT_DROP
                                        }
                                }
                        }
                },
                perf_manager.PerfTestTypes.TEST_TYPE_TCP_RX: {
                        hostap_config.HostapConfig.MODE_11G: {
                                hostap_config.HostapConfig.FREQ_BAND_2_4G: {
                                        hostap_config.HostapConfig.CHANNEL_WIDTH_22: {
                                                BluetoothAdapterAudioTests.CONNECTION_STATE_CONNECTED: SIGNIFICANT_EXPECTED_THROUGHPUT_DROP
                                        }
                                }
                        }
                },
                perf_manager.PerfTestTypes.TEST_TYPE_TCP_RX: {
                        hostap_config.HostapConfig.MODE_11N_PURE: {
                                hostap_config.HostapConfig.FREQ_BAND_5G: {
                                        hostap_config.HostapConfig.HT_CHANNEL_WIDTH_40_PLUS: {
                                                BluetoothAdapterAudioTests.CONNECTION_STATE_STREAMING: MODERATE_EXPECTED_THROUGHPUT_DROP,
                                                BluetoothAdapterAudioTests.CONNECTION_STATE_DISCONNECTED_AGAIN: MODERATE_EXPECTED_THROUGHPUT_DROP
                                        }
                                },
                                hostap_config.HostapConfig.FREQ_BAND_2_4G: {
                                        hostap_config.HostapConfig.HT_CHANNEL_WIDTH_40_PLUS: {
                                                BluetoothAdapterAudioTests.CONNECTION_STATE_CONNECTED: SIGNIFICANT_EXPECTED_THROUGHPUT_DROP
                                        }
                                }
                        }
                },
                perf_manager.PerfTestTypes.TEST_TYPE_UDP_BIDIRECTIONAL: {
                        hostap_config.HostapConfig.MODE_11AC_MIXED: {
                                hostap_config.HostapConfig.FREQ_BAND_5G: {
                                        hostap_config.HostapConfig.VHT_CHANNEL_WIDTH_80: {
                                                BluetoothAdapterAudioTests.CONNECTION_STATE_STREAMING: MODERATE_EXPECTED_THROUGHPUT_DROP
                                        }
                                }
                        },
                        hostap_config.HostapConfig.MODE_11G: {
                                hostap_config.HostapConfig.FREQ_BAND_2_4G: {
                                        hostap_config.HostapConfig.CHANNEL_WIDTH_22: {
                                                BluetoothAdapterAudioTests.CONNECTION_STATE_CONNECTED: SIGNIFICANT_EXPECTED_THROUGHPUT_DROP
                                        }
                                }
                        }
                },
                perf_manager.PerfTestTypes.TEST_TYPE_TCP_BIDIRECTIONAL: {
                        hostap_config.HostapConfig.MODE_11G: {
                                hostap_config.HostapConfig.FREQ_BAND_2_4G: {
                                        hostap_config.HostapConfig.CHANNEL_WIDTH_22: {
                                                BluetoothAdapterAudioTests.CONNECTION_STATE_CONNECTED: SIGNIFICANT_EXPECTED_THROUGHPUT_DROP
                                        }
                                }
                        }
                }
        },
        "cherry": {
                perf_manager.PerfTestTypes.TEST_TYPE_UDP_BIDIRECTIONAL: {
                        hostap_config.HostapConfig.MODE_11AC_MIXED: {
                                hostap_config.HostapConfig.FREQ_BAND_5G: {
                                        hostap_config.HostapConfig.VHT_CHANNEL_WIDTH_80: {
                                                BluetoothAdapterAudioTests.CONNECTION_STATE_STREAMING: MODERATE_EXPECTED_THROUGHPUT_DROP
                                        }
                                }
                        }
                },
                perf_manager.PerfTestTypes.TEST_TYPE_TCP_BIDIRECTIONAL: {
                        hostap_config.HostapConfig.MODE_11AC_MIXED: {
                                hostap_config.HostapConfig.FREQ_BAND_5G: {
                                        hostap_config.HostapConfig.VHT_CHANNEL_WIDTH_80: {
                                                BluetoothAdapterAudioTests.CONNECTION_STATE_CONNECTED: MODERATE_EXPECTED_THROUGHPUT_DROP
                                        }
                                }
                        }
                }
        },
        "jacuzzi": {
                perf_manager.PerfTestTypes.TEST_TYPE_UDP_TX: {
                        hostap_config.HostapConfig.MODE_11N_PURE: {
                                hostap_config.HostapConfig.FREQ_BAND_2_4G: {
                                        hostap_config.HostapConfig.HT_CHANNEL_WIDTH_20: {
                                                BluetoothAdapterAudioTests.CONNECTION_STATE_CONNECTED: HEAVY_EXPECTED_THROUGHPUT_DROP
                                        }
                                }
                        }
                }
        },
        "brya": {
                perf_manager.PerfTestTypes.TEST_TYPE_UDP_TX: {
                        hostap_config.HostapConfig.MODE_11N_PURE: {
                                hostap_config.HostapConfig.FREQ_BAND_2_4G: {
                                        hostap_config.HostapConfig.HT_CHANNEL_WIDTH_20: {
                                                BluetoothAdapterAudioTests.CONNECTION_STATE_DISCONNECTED_AGAIN: SIGNIFICANT_EXPECTED_THROUGHPUT_DROP
                                        }
                                }
                        }
                },
                perf_manager.PerfTestTypes.TEST_TYPE_TCP_TX: {
                        hostap_config.HostapConfig.MODE_11N_PURE: {
                                hostap_config.HostapConfig.FREQ_BAND_2_4G: {
                                        hostap_config.HostapConfig.HT_CHANNEL_WIDTH_20: {
                                                BluetoothAdapterAudioTests.CONNECTION_STATE_CONNECTED: SIGNIFICANT_EXPECTED_THROUGHPUT_DROP
                                        }
                                }
                        }
                }
        },
        "volteer": {
                perf_manager.PerfTestTypes.TEST_TYPE_UDP_TX: {
                        hostap_config.HostapConfig.MODE_11N_PURE: {
                                hostap_config.HostapConfig.FREQ_BAND_2_4G: {
                                        hostap_config.HostapConfig.HT_CHANNEL_WIDTH_20: {
                                                BluetoothAdapterAudioTests.CONNECTION_STATE_DISCONNECTED_AGAIN: MODERATE_EXPECTED_THROUGHPUT_DROP
                                        }
                                }
                        }
                },
                perf_manager.PerfTestTypes.TEST_TYPE_TCP_TX: {
                        hostap_config.HostapConfig.MODE_11G: {
                                hostap_config.HostapConfig.FREQ_BAND_2_4G: {
                                        hostap_config.HostapConfig.CHANNEL_WIDTH_22: {
                                                BluetoothAdapterAudioTests.CONNECTION_STATE_DISCONNECTED_AGAIN: MODERATE_EXPECTED_THROUGHPUT_DROP
                                        }
                                }
                        },
                        hostap_config.HostapConfig.MODE_11N_PURE: {
                                hostap_config.HostapConfig.FREQ_BAND_2_4G: {
                                        hostap_config.HostapConfig.HT_CHANNEL_WIDTH_20: {
                                                BluetoothAdapterAudioTests.CONNECTION_STATE_DISCONNECTED_AGAIN: MODERATE_EXPECTED_THROUGHPUT_DROP
                                        }
                                }
                        }
                },
                perf_manager.PerfTestTypes.TEST_TYPE_TCP_RX: {
                        hostap_config.HostapConfig.MODE_11G: {
                                hostap_config.HostapConfig.FREQ_BAND_2_4G: {
                                        hostap_config.HostapConfig.CHANNEL_WIDTH_22: {
                                                BluetoothAdapterAudioTests.CONNECTION_STATE_CONNECTED: SIGNIFICANT_EXPECTED_THROUGHPUT_DROP
                                        }
                                }
                        },
                        hostap_config.HostapConfig.MODE_11N_PURE: {
                                hostap_config.HostapConfig.FREQ_BAND_2_4G: {
                                        hostap_config.HostapConfig.HT_CHANNEL_WIDTH_40_PLUS: {
                                                BluetoothAdapterAudioTests.CONNECTION_STATE_CONNECTED: SIGNIFICANT_EXPECTED_THROUGHPUT_DROP
                                        }
                                }
                        }
                }
        },
        "scarlet": {
                perf_manager.PerfTestTypes.TEST_TYPE_UDP_TX: {
                        hostap_config.HostapConfig.MODE_11N_PURE: {
                                hostap_config.HostapConfig.FREQ_BAND_2_4G: {
                                        hostap_config.HostapConfig.HT_CHANNEL_WIDTH_40_PLUS: {
                                                BluetoothAdapterAudioTests.CONNECTION_STATE_CONNECTED: HEAVY_EXPECTED_THROUGHPUT_DROP
                                        }
                                }
                        }
                },
                perf_manager.PerfTestTypes.TEST_TYPE_TCP_TX: {
                        hostap_config.HostapConfig.MODE_11G: {
                                hostap_config.HostapConfig.FREQ_BAND_2_4G: {
                                        hostap_config.HostapConfig.CHANNEL_WIDTH_22: {
                                                BluetoothAdapterAudioTests.CONNECTION_STATE_DISCONNECTED_AGAIN: MODERATE_EXPECTED_THROUGHPUT_DROP
                                        }
                                }
                        }
                }
        },
        "hana": {
                perf_manager.PerfTestTypes.TEST_TYPE_UDP_TX: {
                        hostap_config.HostapConfig.MODE_11N_PURE: {
                                hostap_config.HostapConfig.FREQ_BAND_2_4G: {
                                        hostap_config.HostapConfig.HT_CHANNEL_WIDTH_40_PLUS: {
                                                BluetoothAdapterAudioTests.CONNECTION_STATE_CONNECTED: HEAVY_EXPECTED_THROUGHPUT_DROP,
                                                BluetoothAdapterAudioTests.CONNECTION_STATE_STREAMING: HEAVY_EXPECTED_THROUGHPUT_DROP
                                        }
                                }
                        }
                },
                perf_manager.PerfTestTypes.TEST_TYPE_TCP_TX: {
                        hostap_config.HostapConfig.MODE_11N_PURE: {
                                hostap_config.HostapConfig.FREQ_BAND_2_4G: {
                                        hostap_config.HostapConfig.HT_CHANNEL_WIDTH_20: {
                                                BluetoothAdapterAudioTests.CONNECTION_STATE_CONNECTED: SIGNIFICANT_EXPECTED_THROUGHPUT_DROP
                                        },
                                        hostap_config.HostapConfig.HT_CHANNEL_WIDTH_40_PLUS: {
                                                BluetoothAdapterAudioTests.CONNECTION_STATE_CONNECTED: HEAVY_EXPECTED_THROUGHPUT_DROP,
                                                BluetoothAdapterAudioTests.CONNECTION_STATE_STREAMING: HEAVY_EXPECTED_THROUGHPUT_DROP
                                        }
                                }
                        }
                },
                perf_manager.PerfTestTypes.TEST_TYPE_TCP_RX: {
                        hostap_config.HostapConfig.MODE_11N_PURE: {
                                hostap_config.HostapConfig.FREQ_BAND_2_4G: {
                                        hostap_config.HostapConfig.HT_CHANNEL_WIDTH_40_PLUS: {
                                                BluetoothAdapterAudioTests.CONNECTION_STATE_STREAMING: HEAVY_EXPECTED_THROUGHPUT_DROP
                                        }
                                }
                        }
                },
                perf_manager.PerfTestTypes.TEST_TYPE_UDP_BIDIRECTIONAL: {
                        hostap_config.HostapConfig.MODE_11N_PURE: {
                                hostap_config.HostapConfig.FREQ_BAND_2_4G: {
                                        hostap_config.HostapConfig.HT_CHANNEL_WIDTH_20: {
                                                BluetoothAdapterAudioTests.CONNECTION_STATE_CONNECTED: MODERATE_EXPECTED_THROUGHPUT_DROP
                                        },
                                        hostap_config.HostapConfig.HT_CHANNEL_WIDTH_40_PLUS: {
                                                BluetoothAdapterAudioTests.CONNECTION_STATE_CONNECTED: HEAVY_EXPECTED_THROUGHPUT_DROP,
                                                BluetoothAdapterAudioTests.CONNECTION_STATE_STREAMING: HEAVY_EXPECTED_THROUGHPUT_DROP
                                        }
                                }
                        }
                },
                perf_manager.PerfTestTypes.TEST_TYPE_TCP_BIDIRECTIONAL: {
                        hostap_config.HostapConfig.MODE_11N_PURE: {
                                hostap_config.HostapConfig.FREQ_BAND_2_4G: {
                                        hostap_config.HostapConfig.HT_CHANNEL_WIDTH_40_PLUS: {
                                                BluetoothAdapterAudioTests.CONNECTION_STATE_CONNECTED: HEAVY_EXPECTED_THROUGHPUT_DROP,
                                                BluetoothAdapterAudioTests.CONNECTION_STATE_STREAMING: SIGNIFICANT_EXPECTED_THROUGHPUT_DROP
                                        }
                                }
                        }
                }
        },
        "bob": {
                perf_manager.PerfTestTypes.TEST_TYPE_UDP_TX: {
                        hostap_config.HostapConfig.MODE_11N_PURE: {
                                hostap_config.HostapConfig.FREQ_BAND_2_4G: {
                                        hostap_config.HostapConfig.HT_CHANNEL_WIDTH_40_PLUS: {
                                                BluetoothAdapterAudioTests.CONNECTION_STATE_CONNECTED: HEAVY_EXPECTED_THROUGHPUT_DROP,
                                                BluetoothAdapterAudioTests.CONNECTION_STATE_STREAMING: HEAVY_EXPECTED_THROUGHPUT_DROP
                                        }
                                }
                        }
                },
                perf_manager.PerfTestTypes.TEST_TYPE_TCP_TX: {
                        hostap_config.HostapConfig.MODE_11N_PURE: {
                                hostap_config.HostapConfig.FREQ_BAND_2_4G: {
                                        hostap_config.HostapConfig.HT_CHANNEL_WIDTH_20: {
                                                BluetoothAdapterAudioTests.CONNECTION_STATE_CONNECTED: SIGNIFICANT_EXPECTED_THROUGHPUT_DROP
                                        },
                                        hostap_config.HostapConfig.HT_CHANNEL_WIDTH_40_PLUS: {
                                                BluetoothAdapterAudioTests.CONNECTION_STATE_CONNECTED: SIGNIFICANT_EXPECTED_THROUGHPUT_DROP
                                        }
                                }
                        }
                },
                perf_manager.PerfTestTypes.TEST_TYPE_UDP_BIDIRECTIONAL: {
                        hostap_config.HostapConfig.MODE_11N_PURE: {
                                hostap_config.HostapConfig.FREQ_BAND_2_4G: {
                                        hostap_config.HostapConfig.HT_CHANNEL_WIDTH_40_PLUS: {
                                                BluetoothAdapterAudioTests.CONNECTION_STATE_CONNECTED: SIGNIFICANT_EXPECTED_THROUGHPUT_DROP
                                        }
                                }
                        },
                        hostap_config.HostapConfig.MODE_11G: {
                                hostap_config.HostapConfig.FREQ_BAND_2_4G: {
                                        hostap_config.HostapConfig.CHANNEL_WIDTH_22: {
                                                BluetoothAdapterAudioTests.CONNECTION_STATE_DISCONNECTED_AGAIN: MODERATE_EXPECTED_THROUGHPUT_DROP
                                        }
                                }
                        }
                },
                perf_manager.PerfTestTypes.TEST_TYPE_TCP_BIDIRECTIONAL: {
                        hostap_config.HostapConfig.MODE_11G: {
                                hostap_config.HostapConfig.FREQ_BAND_2_4G: {
                                        hostap_config.HostapConfig.CHANNEL_WIDTH_22: {
                                                BluetoothAdapterAudioTests.CONNECTION_STATE_DISCONNECTED_AGAIN: MODERATE_EXPECTED_THROUGHPUT_DROP
                                        }
                                }
                        }
                }
        },
        "coral": {
                perf_manager.PerfTestTypes.TEST_TYPE_UDP_TX: {
                        hostap_config.HostapConfig.MODE_11N_PURE: {
                                hostap_config.HostapConfig.FREQ_BAND_2_4G: {
                                        hostap_config.HostapConfig.HT_CHANNEL_WIDTH_40_PLUS: {
                                                BluetoothAdapterAudioTests.CONNECTION_STATE_CONNECTED: SIGNIFICANT_EXPECTED_THROUGHPUT_DROP
                                        }
                                },
                                hostap_config.HostapConfig.FREQ_BAND_5G: {
                                        hostap_config.HostapConfig.HT_CHANNEL_WIDTH_40_PLUS: {
                                                BluetoothAdapterAudioTests.CONNECTION_STATE_STREAMING: MODERATE_EXPECTED_THROUGHPUT_DROP,
                                                BluetoothAdapterAudioTests.CONNECTION_STATE_DISCONNECTED_AGAIN: MODERATE_EXPECTED_THROUGHPUT_DROP
                                        }
                                }
                        }
                },
                perf_manager.PerfTestTypes.TEST_TYPE_TCP_TX: {
                        hostap_config.HostapConfig.MODE_11AC_MIXED: {
                                hostap_config.HostapConfig.FREQ_BAND_5G: {
                                        hostap_config.HostapConfig.VHT_CHANNEL_WIDTH_80: {
                                                BluetoothAdapterAudioTests.CONNECTION_STATE_STREAMING: MODERATE_EXPECTED_THROUGHPUT_DROP
                                        }
                                }
                        },
                        hostap_config.HostapConfig.MODE_11N_PURE: {
                                hostap_config.HostapConfig.FREQ_BAND_2_4G: {
                                        hostap_config.HostapConfig.HT_CHANNEL_WIDTH_20: {
                                                BluetoothAdapterAudioTests.CONNECTION_STATE_CONNECTED: SIGNIFICANT_EXPECTED_THROUGHPUT_DROP
                                        }
                                }
                        }
                },
                perf_manager.PerfTestTypes.TEST_TYPE_TCP_RX: {
                        hostap_config.HostapConfig.MODE_11G: {
                                hostap_config.HostapConfig.FREQ_BAND_2_4G: {
                                        hostap_config.HostapConfig.CHANNEL_WIDTH_22: {
                                                BluetoothAdapterAudioTests.CONNECTION_STATE_DISCONNECTED_AGAIN: MODERATE_EXPECTED_THROUGHPUT_DROP
                                        }
                                }
                        },
                        hostap_config.HostapConfig.MODE_11N_PURE: {
                                hostap_config.HostapConfig.FREQ_BAND_2_4G: {
                                        hostap_config.HostapConfig.HT_CHANNEL_WIDTH_40_PLUS: {
                                                BluetoothAdapterAudioTests.CONNECTION_STATE_STREAMING: HEAVY_EXPECTED_THROUGHPUT_DROP
                                        }
                                }
                        }
                },
                perf_manager.PerfTestTypes.TEST_TYPE_UDP_BIDIRECTIONAL: {
                        hostap_config.HostapConfig.MODE_11N_PURE: {
                                hostap_config.HostapConfig.FREQ_BAND_2_4G: {
                                        hostap_config.HostapConfig.HT_CHANNEL_WIDTH_20: {
                                                BluetoothAdapterAudioTests.CONNECTION_STATE_CONNECTED: HEAVY_EXPECTED_THROUGHPUT_DROP
                                        },
                                        hostap_config.HostapConfig.HT_CHANNEL_WIDTH_40_PLUS: {
                                                BluetoothAdapterAudioTests.CONNECTION_STATE_CONNECTED: SIGNIFICANT_EXPECTED_THROUGHPUT_DROP,
                                                BluetoothAdapterAudioTests.CONNECTION_STATE_STREAMING: HEAVY_EXPECTED_THROUGHPUT_DROP
                                        }
                                }
                        }
                },
                perf_manager.PerfTestTypes.TEST_TYPE_TCP_BIDIRECTIONAL: {
                        hostap_config.HostapConfig.MODE_11N_PURE: {
                                hostap_config.HostapConfig.FREQ_BAND_2_4G: {
                                        hostap_config.HostapConfig.HT_CHANNEL_WIDTH_40_PLUS: {
                                                BluetoothAdapterAudioTests.CONNECTION_STATE_STREAMING: SIGNIFICANT_EXPECTED_THROUGHPUT_DROP
                                        }
                                }
                        }
                }
        },
        "nami": {
                perf_manager.PerfTestTypes.TEST_TYPE_UDP_TX: {
                        hostap_config.HostapConfig.MODE_11N_PURE: {
                                hostap_config.HostapConfig.FREQ_BAND_2_4G: {
                                        hostap_config.HostapConfig.HT_CHANNEL_WIDTH_40_PLUS: {
                                                BluetoothAdapterAudioTests.CONNECTION_STATE_STREAMING: HEAVY_EXPECTED_THROUGHPUT_DROP
                                        }
                                }
                        }
                }
        },
        "corsola": {
                perf_manager.PerfTestTypes.TEST_TYPE_UDP_TX: {
                        hostap_config.HostapConfig.MODE_11AC_MIXED: {
                                hostap_config.HostapConfig.FREQ_BAND_5G: {
                                        hostap_config.HostapConfig.VHT_CHANNEL_WIDTH_80: {
                                                BluetoothAdapterAudioTests.CONNECTION_STATE_STREAMING: MODERATE_EXPECTED_THROUGHPUT_DROP
                                        }
                                }
                        }
                },
                perf_manager.PerfTestTypes.TEST_TYPE_TCP_BIDIRECTIONAL: {
                        hostap_config.HostapConfig.MODE_11AC_MIXED: {
                                hostap_config.HostapConfig.FREQ_BAND_5G: {
                                        hostap_config.HostapConfig.VHT_CHANNEL_WIDTH_80: {
                                                BluetoothAdapterAudioTests.CONNECTION_STATE_DISCONNECTED_AGAIN: MODERATE_EXPECTED_THROUGHPUT_DROP
                                        }
                                }
                        },
                        hostap_config.HostapConfig.MODE_11G: {
                                hostap_config.HostapConfig.FREQ_BAND_2_4G: {
                                        hostap_config.HostapConfig.CHANNEL_WIDTH_22: {
                                                BluetoothAdapterAudioTests.CONNECTION_STATE_DISCONNECTED_AGAIN: MODERATE_EXPECTED_THROUGHPUT_DROP
                                        }
                                }
                        }
                }
        },
        "kukui": {
                perf_manager.PerfTestTypes.TEST_TYPE_TCP_TX: {
                        hostap_config.HostapConfig.MODE_11N_PURE: {
                                hostap_config.HostapConfig.FREQ_BAND_2_4G: {
                                        hostap_config.HostapConfig.HT_CHANNEL_WIDTH_20: {
                                                BluetoothAdapterAudioTests.CONNECTION_STATE_DISCONNECTED_AGAIN: MODERATE_EXPECTED_THROUGHPUT_DROP
                                        },
                                        hostap_config.HostapConfig.HT_CHANNEL_WIDTH_40_PLUS: {
                                                BluetoothAdapterAudioTests.CONNECTION_STATE_CONNECTED: HEAVY_EXPECTED_THROUGHPUT_DROP
                                        }
                                }
                        }
                },
                perf_manager.PerfTestTypes.TEST_TYPE_TCP_RX: {
                        hostap_config.HostapConfig.MODE_11N_PURE: {
                                hostap_config.HostapConfig.FREQ_BAND_5G: {
                                        hostap_config.HostapConfig.HT_CHANNEL_WIDTH_20: {
                                                BluetoothAdapterAudioTests.CONNECTION_STATE_CONNECTED: MODERATE_EXPECTED_THROUGHPUT_DROP,
                                                BluetoothAdapterAudioTests.CONNECTION_STATE_STREAMING: MODERATE_EXPECTED_THROUGHPUT_DROP,
                                                BluetoothAdapterAudioTests.CONNECTION_STATE_DISCONNECTED_AGAIN: MODERATE_EXPECTED_THROUGHPUT_DROP
                                        }
                                }
                        }
                },
                perf_manager.PerfTestTypes.TEST_TYPE_UDP_BIDIRECTIONAL: {
                        hostap_config.HostapConfig.MODE_11N_PURE: {
                                hostap_config.HostapConfig.FREQ_BAND_5G: {
                                        hostap_config.HostapConfig.HT_CHANNEL_WIDTH_20: {
                                                BluetoothAdapterAudioTests.CONNECTION_STATE_STREAMING: MODERATE_EXPECTED_THROUGHPUT_DROP
                                        }
                                }
                        }
                }
        },
        "grunt": {
                perf_manager.PerfTestTypes.TEST_TYPE_TCP_TX: {
                        hostap_config.HostapConfig.MODE_11N_PURE: {
                                hostap_config.HostapConfig.FREQ_BAND_2_4G: {
                                        hostap_config.HostapConfig.HT_CHANNEL_WIDTH_20: {
                                                BluetoothAdapterAudioTests.CONNECTION_STATE_CONNECTED: HEAVY_EXPECTED_THROUGHPUT_DROP
                                        }
                                }
                        }
                },
        },
        "octopus": {
                perf_manager.PerfTestTypes.TEST_TYPE_TCP_TX: {
                        hostap_config.HostapConfig.MODE_11N_PURE: {
                                hostap_config.HostapConfig.FREQ_BAND_2_4G: {
                                        hostap_config.HostapConfig.HT_CHANNEL_WIDTH_40_PLUS: {
                                                BluetoothAdapterAudioTests.CONNECTION_STATE_CONNECTED: SIGNIFICANT_EXPECTED_THROUGHPUT_DROP
                                        }
                                }
                        }
                },
                perf_manager.PerfTestTypes.TEST_TYPE_TCP_RX: {
                        hostap_config.HostapConfig.MODE_11G: {
                                hostap_config.HostapConfig.FREQ_BAND_2_4G: {
                                        hostap_config.HostapConfig.CHANNEL_WIDTH_22: {
                                                BluetoothAdapterAudioTests.CONNECTION_STATE_CONNECTED: SIGNIFICANT_EXPECTED_THROUGHPUT_DROP
                                        }
                                }
                        }
                },
                perf_manager.PerfTestTypes.TEST_TYPE_UDP_BIDIRECTIONAL: {
                        hostap_config.HostapConfig.MODE_11AC_MIXED: {
                                hostap_config.HostapConfig.FREQ_BAND_5G: {
                                        hostap_config.HostapConfig.VHT_CHANNEL_WIDTH_80: {
                                                BluetoothAdapterAudioTests.CONNECTION_STATE_STREAMING: MODERATE_EXPECTED_THROUGHPUT_DROP
                                        }
                                }
                        }
                },
                perf_manager.PerfTestTypes.TEST_TYPE_UDP_BIDIRECTIONAL: {
                        hostap_config.HostapConfig.MODE_11N_PURE: {
                                hostap_config.HostapConfig.FREQ_BAND_2_4G: {
                                        hostap_config.HostapConfig.HT_CHANNEL_WIDTH_20: {
                                                BluetoothAdapterAudioTests.CONNECTION_STATE_CONNECTED: MODERATE_EXPECTED_THROUGHPUT_DROP
                                        }
                                }
                        }
                },
                perf_manager.PerfTestTypes.TEST_TYPE_TCP_BIDIRECTIONAL: {
                        hostap_config.HostapConfig.MODE_11G: {
                                hostap_config.HostapConfig.FREQ_BAND_2_4G: {
                                        hostap_config.HostapConfig.CHANNEL_WIDTH_22: {
                                                BluetoothAdapterAudioTests.CONNECTION_STATE_DISCONNECTED_AGAIN: MODERATE_EXPECTED_THROUGHPUT_DROP
                                        }
                                }
                        }
                }
        },
        "fizz": {
                perf_manager.PerfTestTypes.TEST_TYPE_TCP_TX: {
                        hostap_config.HostapConfig.MODE_11N_PURE: {
                                hostap_config.HostapConfig.FREQ_BAND_2_4G: {
                                        hostap_config.HostapConfig.HT_CHANNEL_WIDTH_40_PLUS: {
                                                BluetoothAdapterAudioTests.CONNECTION_STATE_STREAMING: HEAVY_EXPECTED_THROUGHPUT_DROP
                                        }
                                }
                        }
                }
        },
        "asurada": {
                perf_manager.PerfTestTypes.TEST_TYPE_TCP_RX: {
                        hostap_config.HostapConfig.MODE_11G: {
                                hostap_config.HostapConfig.FREQ_BAND_2_4G: {
                                        hostap_config.HostapConfig.CHANNEL_WIDTH_22: {
                                                BluetoothAdapterAudioTests.CONNECTION_STATE_CONNECTED: HEAVY_EXPECTED_THROUGHPUT_DROP
                                        }
                                }
                        }
                },
                perf_manager.PerfTestTypes.TEST_TYPE_UDP_BIDIRECTIONAL: {
                        hostap_config.HostapConfig.MODE_11N_PURE: {
                                hostap_config.HostapConfig.FREQ_BAND_2_4G: {
                                        hostap_config.HostapConfig.HT_CHANNEL_WIDTH_20: {
                                                BluetoothAdapterAudioTests.CONNECTION_STATE_CONNECTED: MODERATE_EXPECTED_THROUGHPUT_DROP
                                        }
                                }
                        }
                },
                perf_manager.PerfTestTypes.TEST_TYPE_TCP_BIDIRECTIONAL: {
                        hostap_config.HostapConfig.MODE_11AC_MIXED: {
                                hostap_config.HostapConfig.FREQ_BAND_5G: {
                                        hostap_config.HostapConfig.VHT_CHANNEL_WIDTH_80: {
                                                BluetoothAdapterAudioTests.CONNECTION_STATE_DISCONNECTED_AGAIN: MODERATE_EXPECTED_THROUGHPUT_DROP
                                        }
                                }
                        }
                }
        },
        "puff": {
                perf_manager.PerfTestTypes.TEST_TYPE_TCP_RX: {
                        hostap_config.HostapConfig.MODE_11G: {
                                hostap_config.HostapConfig.FREQ_BAND_2_4G: {
                                        hostap_config.HostapConfig.CHANNEL_WIDTH_22: {
                                                BluetoothAdapterAudioTests.CONNECTION_STATE_DISCONNECTED_AGAIN: MODERATE_EXPECTED_THROUGHPUT_DROP
                                        }
                                }
                        }
                }
        },
        "ramus": {
                perf_manager.PerfTestTypes.TEST_TYPE_TCP_RX: {
                        hostap_config.HostapConfig.MODE_11AC_MIXED: {
                                hostap_config.HostapConfig.FREQ_BAND_5G: {
                                        hostap_config.HostapConfig.VHT_CHANNEL_WIDTH_80: {
                                                BluetoothAdapterAudioTests.CONNECTION_STATE_DISCONNECTED_AGAIN: HEAVY_EXPECTED_THROUGHPUT_DROP
                                        }
                                }
                        }
                },
                perf_manager.PerfTestTypes.TEST_TYPE_UDP_BIDIRECTIONAL: {
                        hostap_config.HostapConfig.MODE_11AC_MIXED: {
                                hostap_config.HostapConfig.FREQ_BAND_5G: {
                                        hostap_config.HostapConfig.VHT_CHANNEL_WIDTH_80: {
                                                BluetoothAdapterAudioTests.CONNECTION_STATE_DISCONNECTED_AGAIN: HEAVY_EXPECTED_THROUGHPUT_DROP
                                        }
                                }
                        }
                },
                perf_manager.PerfTestTypes.TEST_TYPE_TCP_BIDIRECTIONAL: {
                        hostap_config.HostapConfig.MODE_11AC_MIXED: {
                                hostap_config.HostapConfig.FREQ_BAND_5G: {
                                        hostap_config.HostapConfig.VHT_CHANNEL_WIDTH_80: {
                                                BluetoothAdapterAudioTests.CONNECTION_STATE_DISCONNECTED_AGAIN: SIGNIFICANT_EXPECTED_THROUGHPUT_DROP
                                        }
                                }
                        }
                }
        },
        "kevin": {
                perf_manager.PerfTestTypes.TEST_TYPE_UDP_BIDIRECTIONAL: {
                        hostap_config.HostapConfig.MODE_11G: {
                                hostap_config.HostapConfig.FREQ_BAND_2_4G: {
                                        hostap_config.HostapConfig.CHANNEL_WIDTH_22: {
                                                BluetoothAdapterAudioTests.CONNECTION_STATE_DISCONNECTED_AGAIN: MODERATE_EXPECTED_THROUGHPUT_DROP
                                        }
                                }
                        }
                },
                perf_manager.PerfTestTypes.TEST_TYPE_TCP_BIDIRECTIONAL: {
                        hostap_config.HostapConfig.MODE_11G: {
                                hostap_config.HostapConfig.FREQ_BAND_2_4G: {
                                        hostap_config.HostapConfig.CHANNEL_WIDTH_22: {
                                                BluetoothAdapterAudioTests.CONNECTION_STATE_DISCONNECTED_AGAIN: MODERATE_EXPECTED_THROUGHPUT_DROP
                                        }
                                }
                        }
                }
        }

}

def get_board_max_wifibt_coex_throughput_drop_expectation(test_type, board_name, ap_config, bt_tag):
    """Returns the maximum throughput expectation for a given board in a given
    test type, or None if the board has no exception for that test type.

    @param test_type: the PerfTestTypes test type
    @param board_name: string name of the board, as defined by
                       SiteLinuxSystem.board field
    @param ap_config: the AP configuration
    @param bt_tag: string for BT operation

    @return integer value for maximum throughput expectation (in Mbps) for the
            given boardand test type, or None if the maximum is not defined.
    """
    board_drop_expectations = max_wifibt_coex_throughput_drop_expectation_for_boards.get(board_name)
    if not board_drop_expectations:
        return None

    mode = ap_config.mode
    channel_width = ap_config.channel_width
    freq_band = ap_config.freq_band

    if test_type in board_drop_expectations:
        if mode in board_drop_expectations[test_type]:
            if freq_band in board_drop_expectations[test_type][mode]:
                if channel_width in board_drop_expectations[test_type][mode][freq_band]:
                    if bt_tag in board_drop_expectations[test_type][mode][freq_band][channel_width]:
                        return board_drop_expectations[test_type][mode][freq_band][channel_width][bt_tag]

    return None


def get_expected_result(expected_table, *keys):
    """Retrieves the expected result from nested dict based on keys.

    @param expected_table: The nested dictionary to traverse.
    @param keys: Variable length arguments representing keys to traverse the
                 dictionary.

    @return: The expected result retrieved based on provided keys, or None if
             not found.
    """
    for key in keys:
        expected_table = expected_table.get(key)
        if expected_table is None:
            return None
    return expected_table


def get_expected_value(measurement, expected_dict, test_type, test_name,
                       ap_config, bt_tag):
    """Returns the expected value for a measurement in a Wi-Fi BT load test.

    @param measurement: The name of the measurement.
    @param expected_dict: The nested dictionary containing the expected values.
    @param test_type: The PerfTestTypes test type.
    @param test_name: The test name.
    @param ap_config: The AP configuration.
    @param bt_tag: String for BT operation.

    @return: The expected value retrieved based on the provided keys.
    """
    mode = ap_config.mode
    channel_width = ap_config.channel_width
    freq_band = ap_config.freq_band

    result = get_expected_result(expected_dict, test_name, test_type, mode,
                                 freq_band, channel_width, bt_tag)
    if result is None:
        ret_mode = hostap_config.HostapConfig.get_channel_width_name(
                mode, freq_band, channel_width)
        raise error.TestFail(
                'Failed to find the expected %s value from the key values, '
                'test type = %s, freq band = %s, mode = %s, channel width = %s'
                % (measurement, test_type, freq_band, mode, ret_mode))
    return result


"""The tuples defined below represent thresholds for drop rate values, where
drop rate refers to the decrease in measured throughput during different
BT status: BT_connected, BT_connected_with_load and BT_disconnected_again. The
tuples are structured as (should not exceed, must not exceed). The
'should not exceed' value is set to 0 as a turnaround. For 'mouse_load' test,
the 'must not exceed' value was derived from the highest drop rate observed
during 100 runs of Wi-Fi and Bluetooth load coexistence tests. For other
tests the 'must not exceed' value for these tests is determined based on the
highest observed drop rate across 10 runs. These values may be enhanced later
by running additional tests for 100 runs.
"""
expected_throughput_drop = {
    'coex_test_with_mouse_click_load': {
        perf_manager.PerfTestTypes.TEST_TYPE_UDP_TX: {
            hostap_config.HostapConfig.MODE_11AX_MIXED: {
                hostap_config.HostapConfig.FREQ_BAND_5G: {
                    hostap_config.HostapConfig.HE_CHANNEL_WIDTH_80: {
                        'BT_connected': (0, 18),
                        'BT_connected_with_load': (0, 17),
                        'BT_disconnected_again': (0, 18)
                    }
                }
            },
            hostap_config.HostapConfig.MODE_11G: {
                hostap_config.HostapConfig.FREQ_BAND_2_4G: {
                    hostap_config.HostapConfig.CHANNEL_WIDTH_22: {
                        'BT_connected': (0, 2),
                        'BT_connected_with_load': (0, 7),
                        'BT_disconnected_again': (0, 0)
                    }
                }
            }
        },
        perf_manager.PerfTestTypes.TEST_TYPE_UDP_RX: {
            hostap_config.HostapConfig.MODE_11AX_MIXED: {
                hostap_config.HostapConfig.FREQ_BAND_5G: {
                    hostap_config.HostapConfig.HE_CHANNEL_WIDTH_80: {
                        'BT_connected': (0, 1),
                        'BT_connected_with_load': (0, 1),
                        'BT_disconnected_again': (0, 1)
                    }
                }
            },
            hostap_config.HostapConfig.MODE_11G: {
                hostap_config.HostapConfig.FREQ_BAND_2_4G: {
                    hostap_config.HostapConfig.CHANNEL_WIDTH_22: {
                        'BT_connected': (0, 18),
                        'BT_connected_with_load': (0, 14),
                        'BT_disconnected_again': (0, 16)
                    }
                }
            }
        },
        perf_manager.PerfTestTypes.TEST_TYPE_TCP_TX: {
            hostap_config.HostapConfig.MODE_11AX_MIXED: {
                hostap_config.HostapConfig.FREQ_BAND_5G: {
                    hostap_config.HostapConfig.HE_CHANNEL_WIDTH_80: {
                        'BT_connected': (0, 4),
                        'BT_connected_with_load': (0, 3),
                        'BT_disconnected_again': (0, 4)
                    }
                }
            },
            hostap_config.HostapConfig.MODE_11G: {
                hostap_config.HostapConfig.FREQ_BAND_2_4G: {
                    hostap_config.HostapConfig.CHANNEL_WIDTH_22: {
                        'BT_connected': (0, 3),
                        'BT_connected_with_load': (0, 6),
                        'BT_disconnected_again': (0, 0)
                    }
                }
            }
        },
        perf_manager.PerfTestTypes.TEST_TYPE_TCP_RX: {
            hostap_config.HostapConfig.MODE_11AX_MIXED: {
                hostap_config.HostapConfig.FREQ_BAND_5G: {
                    hostap_config.HostapConfig.HE_CHANNEL_WIDTH_80: {
                            'BT_connected': (0, 14),
                            'BT_connected_with_load': (0, 17),
                            'BT_disconnected_again': (0, 14)
                    }
                }
            },
            hostap_config.HostapConfig.MODE_11G: {
                hostap_config.HostapConfig.FREQ_BAND_2_4G: {
                    hostap_config.HostapConfig.CHANNEL_WIDTH_22: {
                        'BT_connected': (0, 5),
                        'BT_connected_with_load': (0, 8),
                        'BT_disconnected_again': (0, 1)
                    }
                }
            }
        }
    },
    'coex_test_with_ble_keyboard_load': {
        perf_manager.PerfTestTypes.TEST_TYPE_UDP_TX: {
            hostap_config.HostapConfig.MODE_11AX_MIXED: {
                hostap_config.HostapConfig.FREQ_BAND_5G: {
                    hostap_config.HostapConfig.HE_CHANNEL_WIDTH_80: {
                        'BT_connected': (0, 0),
                        'BT_connected_with_load': (0, 0),
                        'BT_disconnected_again': (0, 1)
                    }
                }
            },
            hostap_config.HostapConfig.MODE_11G: {
                hostap_config.HostapConfig.FREQ_BAND_2_4G: {
                    hostap_config.HostapConfig.CHANNEL_WIDTH_22: {
                        'BT_connected': (0, 1),
                        'BT_connected_with_load': (0, 2),
                        'BT_disconnected_again': (0, 0)
                    }
                }
            }
        },
        perf_manager.PerfTestTypes.TEST_TYPE_UDP_RX: {
            hostap_config.HostapConfig.MODE_11AX_MIXED: {
                hostap_config.HostapConfig.FREQ_BAND_5G: {
                    hostap_config.HostapConfig.HE_CHANNEL_WIDTH_80: {
                        'BT_connected': (0, 0),
                        'BT_connected_with_load': (0, 0),
                        'BT_disconnected_again': (0, 0)
                    }
                }
            },
            hostap_config.HostapConfig.MODE_11G: {
                hostap_config.HostapConfig.FREQ_BAND_2_4G: {
                    hostap_config.HostapConfig.CHANNEL_WIDTH_22: {
                        'BT_connected': (0, 2),
                        'BT_connected_with_load': (0, 3),
                        'BT_disconnected_again': (0, 0)
                    }
                }
            }
        },
        perf_manager.PerfTestTypes.TEST_TYPE_TCP_TX: {
            hostap_config.HostapConfig.MODE_11AX_MIXED: {
                hostap_config.HostapConfig.FREQ_BAND_5G: {
                    hostap_config.HostapConfig.HE_CHANNEL_WIDTH_80: {
                        'BT_connected': (0, 1),
                        'BT_connected_with_load': (0, 0),
                        'BT_disconnected_again': (0, 1)
                    }
                }
            },
            hostap_config.HostapConfig.MODE_11G: {
                hostap_config.HostapConfig.FREQ_BAND_2_4G: {
                    hostap_config.HostapConfig.CHANNEL_WIDTH_22: {
                        'BT_connected': (0, 1),
                        'BT_connected_with_load': (0, 2),
                        'BT_disconnected_again': (0, 0)
                    }
                }
            }
        },
        perf_manager.PerfTestTypes.TEST_TYPE_TCP_RX: {
            hostap_config.HostapConfig.MODE_11AX_MIXED: {
                hostap_config.HostapConfig.FREQ_BAND_5G: {
                    hostap_config.HostapConfig.HE_CHANNEL_WIDTH_80: {
                        'BT_connected': (0, 1),
                        'BT_connected_with_load': (0, 0),
                        'BT_disconnected_again': (0, 2)
                    }
                }
            },
            hostap_config.HostapConfig.MODE_11G: {
                hostap_config.HostapConfig.FREQ_BAND_2_4G: {
                    hostap_config.HostapConfig.CHANNEL_WIDTH_22: {
                        'BT_connected': (0, 0),
                        'BT_connected_with_load': (0, 0),
                        'BT_disconnected_again': (0, 0)
                    }
                }
            }
        }
    },
    'coex_test_with_keyboard_load': {
        perf_manager.PerfTestTypes.TEST_TYPE_UDP_TX: {
            hostap_config.HostapConfig.MODE_11AX_MIXED: {
                hostap_config.HostapConfig.FREQ_BAND_5G: {
                    hostap_config.HostapConfig.HE_CHANNEL_WIDTH_80: {
                        'BT_connected': (0, 1),
                        'BT_connected_with_load': (0, 1),
                        'BT_disconnected_again': (0, 2)
                    }
                }
            },
            hostap_config.HostapConfig.MODE_11G: {
                hostap_config.HostapConfig.FREQ_BAND_2_4G: {
                    hostap_config.HostapConfig.CHANNEL_WIDTH_22: {
                        'BT_connected': (0, 2),
                        'BT_connected_with_load': (0, 9),
                        'BT_disconnected_again': (0, 0)
                    }
                }
            }
        },
        perf_manager.PerfTestTypes.TEST_TYPE_UDP_RX: {
            hostap_config.HostapConfig.MODE_11AX_MIXED: {
                hostap_config.HostapConfig.FREQ_BAND_5G: {
                    hostap_config.HostapConfig.HE_CHANNEL_WIDTH_80: {
                        'BT_connected': (0, 0),
                        'BT_connected_with_load': (0, 0),
                        'BT_disconnected_again': (0, 0)
                    }
                }
            },
            hostap_config.HostapConfig.MODE_11G: {
                hostap_config.HostapConfig.FREQ_BAND_2_4G: {
                    hostap_config.HostapConfig.CHANNEL_WIDTH_22: {
                        'BT_connected': (0, 4),
                        'BT_connected_with_load': (0, 6),
                        'BT_disconnected_again': (0, 1),
                    }
                }
            }
        },
        perf_manager.PerfTestTypes.TEST_TYPE_TCP_TX: {
            hostap_config.HostapConfig.MODE_11AX_MIXED: {
                hostap_config.HostapConfig.FREQ_BAND_5G: {
                    hostap_config.HostapConfig.HE_CHANNEL_WIDTH_80: {
                        'BT_connected': (0, 1),
                        'BT_connected_with_load': (0, 1),
                        'BT_disconnected_again': (0, 0)
                    }
                }
            },
            hostap_config.HostapConfig.MODE_11G: {
                hostap_config.HostapConfig.FREQ_BAND_2_4G: {
                    hostap_config.HostapConfig.CHANNEL_WIDTH_22: {
                        'BT_connected': (0, 2),
                        'BT_connected_with_load': (0, 6),
                        'BT_disconnected_again': (0, 0),
                    }
                }
            }
        },
        perf_manager.PerfTestTypes.TEST_TYPE_TCP_RX: {
            hostap_config.HostapConfig.MODE_11AX_MIXED: {
                hostap_config.HostapConfig.FREQ_BAND_5G: {
                    hostap_config.HostapConfig.HE_CHANNEL_WIDTH_80: {
                        'BT_connected': (0, 2),
                        'BT_connected_with_load': (0, 0),
                        'BT_disconnected_again': (0, 0)
                    }
                }
            },
            hostap_config.HostapConfig.MODE_11G: {
                hostap_config.HostapConfig.FREQ_BAND_2_4G: {
                    hostap_config.HostapConfig.CHANNEL_WIDTH_22: {
                        'BT_connected': (0, 4),
                        'BT_connected_with_load': (0, 10),
                        'BT_disconnected_again': (0, 0),
                    }
                }
            }
        }
    },
    'coex_test_with_ble_mouse_click_load': {
        perf_manager.PerfTestTypes.TEST_TYPE_UDP_TX: {
            hostap_config.HostapConfig.MODE_11AX_MIXED: {
                hostap_config.HostapConfig.FREQ_BAND_5G: {
                    hostap_config.HostapConfig.HE_CHANNEL_WIDTH_80: {
                        'BT_connected': (0, 0),
                        'BT_connected_with_load': (0, 0),
                        'BT_disconnected_again': (0, 0)
                    }
                }
            },
            hostap_config.HostapConfig.MODE_11G: {
                hostap_config.HostapConfig.FREQ_BAND_2_4G: {
                    hostap_config.HostapConfig.CHANNEL_WIDTH_22: {
                        'BT_connected': (0, 0),
                        'BT_connected_with_load': (0, 0),
                        'BT_disconnected_again': (0, 0)
                    }
                }
            }
        },
        perf_manager.PerfTestTypes.TEST_TYPE_UDP_RX: {
            hostap_config.HostapConfig.MODE_11AX_MIXED: {
                hostap_config.HostapConfig.FREQ_BAND_5G: {
                    hostap_config.HostapConfig.HE_CHANNEL_WIDTH_80: {
                        'BT_connected': (0, 0),
                        'BT_connected_with_load': (0, 0),
                        'BT_disconnected_again': (0, 0)
                    }
                }
            },
            hostap_config.HostapConfig.MODE_11G: {
                hostap_config.HostapConfig.FREQ_BAND_2_4G: {
                    hostap_config.HostapConfig.CHANNEL_WIDTH_22: {
                        'BT_connected': (0, 0),
                        'BT_connected_with_load': (0, 0),
                        'BT_disconnected_again': (0, 0)
                    }
                }
            }
        },
        perf_manager.PerfTestTypes.TEST_TYPE_TCP_TX: {
            hostap_config.HostapConfig.MODE_11AX_MIXED: {
                hostap_config.HostapConfig.FREQ_BAND_5G: {
                    hostap_config.HostapConfig.HE_CHANNEL_WIDTH_80: {
                        'BT_connected': (0, 0),
                        'BT_connected_with_load': (0, 0),
                        'BT_disconnected_again': (0, 0)
                    }
                }
            },
            hostap_config.HostapConfig.MODE_11G: {
                hostap_config.HostapConfig.FREQ_BAND_2_4G: {
                    hostap_config.HostapConfig.CHANNEL_WIDTH_22: {
                        'BT_connected': (0, 2),
                        'BT_connected_with_load': (0, 2),
                        'BT_disconnected_again': (0, 0)
                    }
                }
            }
        },
        perf_manager.PerfTestTypes.TEST_TYPE_TCP_RX: {
            hostap_config.HostapConfig.MODE_11AX_MIXED: {
                hostap_config.HostapConfig.FREQ_BAND_5G: {
                    hostap_config.HostapConfig.HE_CHANNEL_WIDTH_80: {
                        'BT_connected': (0, 0),
                        'BT_connected_with_load': (0, 2),
                        'BT_disconnected_again': (0, 0)
                    }
                }
            },
            hostap_config.HostapConfig.MODE_11G: {
                hostap_config.HostapConfig.FREQ_BAND_2_4G: {
                    hostap_config.HostapConfig.CHANNEL_WIDTH_22: {
                        'BT_connected': (0, 0),
                        'BT_connected_with_load': (0, 0),
                        'BT_disconnected_again': (0, 0)
                    }
                }
            }
        }
    }
}


def get_expected_wifi_throughput_drop_rate(test_type, test_name, ap_config,
                                           bt_tag):
    """Returns the expected throughput drop rate for Wi-Fi BT load coex tests.

    @param test_type: The PerfTestTypes test type.
    @param test_name: The test name.
    @param ap_config: The AP configuration.
    @param bt_tag: String for BT operation.

    @return: A tuple of two integers (SHOULD, MUST) of the expected throughput
             drop percentage.
    """
    return get_expected_value('throughput drop', expected_throughput_drop,
                              test_type, test_name, ap_config, bt_tag)


"""The tuples defined below represent thresholds for throughput values as
(should not exceed, must not exceed). For 'mouse_load' test, the
'should not exceed' value is derived from the highest throughput observed
during 100 runs of Wi-Fi and Bluetooth load coexistence tests, while the
'must not exceed' value is derived from the lowest throughput observed
during the same tests. For other tests, these thresholds are determined based
on 10 runs. These values may be enhanced later by running additional tests
for 100 runs.
"""
expected_throughput_values = {
    'coex_test_with_mouse_click_load': {
        perf_manager.PerfTestTypes.TEST_TYPE_UDP_TX: {
            hostap_config.HostapConfig.MODE_11AX_MIXED: {
                hostap_config.HostapConfig.FREQ_BAND_5G: {
                    hostap_config.HostapConfig.HE_CHANNEL_WIDTH_80: {
                        'BT_connected': (369.32, 342.55),
                        'BT_connected_with_load': (362.52, 331.14),
                        'BT_disconnected_again': (376.43, 297.24)
                    }
                }
            },
            hostap_config.HostapConfig.MODE_11G: {
                hostap_config.HostapConfig.FREQ_BAND_2_4G: {
                    hostap_config.HostapConfig.CHANNEL_WIDTH_22: {
                        'BT_connected': (27.24, 27.21),
                        'BT_connected_with_load': (25.67, 25.65),
                        'BT_disconnected_again': (27.87, 27.86)
                    }
                }
            }
        },
        perf_manager.PerfTestTypes.TEST_TYPE_UDP_RX: {
            hostap_config.HostapConfig.MODE_11AX_MIXED: {
                hostap_config.HostapConfig.FREQ_BAND_5G: {
                    hostap_config.HostapConfig.HE_CHANNEL_WIDTH_80: {
                        'BT_connected': (389.08, 386.41),
                        'BT_connected_with_load': (386.97, 383.77),
                        'BT_disconnected_again': (387.17, 384.99)
                    }
                }
            },
            hostap_config.HostapConfig.MODE_11G: {
                hostap_config.HostapConfig.FREQ_BAND_2_4G: {
                    hostap_config.HostapConfig.CHANNEL_WIDTH_22: {
                        'BT_connected': (39.08, 38.66),
                        'BT_connected_with_load': (38.53, 38.36),
                        'BT_disconnected_again': (40.66, 40.45),
                    }
                }
            }
        },
        perf_manager.PerfTestTypes.TEST_TYPE_TCP_TX: {
            hostap_config.HostapConfig.MODE_11AX_MIXED: {
                hostap_config.HostapConfig.FREQ_BAND_5G: {
                    hostap_config.HostapConfig.HE_CHANNEL_WIDTH_80: {
                        'BT_connected': (728.72, 722.50),
                        'BT_connected_with_load': (733.23, 727.69),
                        'BT_disconnected_again': (731.66, 726.54)
                    }
                }
            },
            hostap_config.HostapConfig.MODE_11G: {
                hostap_config.HostapConfig.FREQ_BAND_2_4G: {
                    hostap_config.HostapConfig.CHANNEL_WIDTH_22: {
                        'BT_connected': (21.55, 21.11),
                        'BT_connected_with_load': (20.91, 20.68),
                        'BT_disconnected_again': (22.15, 21.86),
                    }
                }
            }
        },
        perf_manager.PerfTestTypes.TEST_TYPE_TCP_RX: {
            hostap_config.HostapConfig.MODE_11AX_MIXED: {
                hostap_config.HostapConfig.FREQ_BAND_5G: {
                    hostap_config.HostapConfig.HE_CHANNEL_WIDTH_80: {
                        'BT_connected': (328.92, 296.43),
                        'BT_connected_with_load': (335.53, 317.38),
                        'BT_disconnected_again': (330.17, 303.26)
                    }
                }
            },
            hostap_config.HostapConfig.MODE_11G: {
                hostap_config.HostapConfig.FREQ_BAND_2_4G: {
                    hostap_config.HostapConfig.CHANNEL_WIDTH_22: {
                        'BT_connected': (21.72, 21.69),
                        'BT_connected_with_load': (20.87, 20.84),
                        'BT_disconnected_again': (22.85, 22.80),
                    }
                }
            }
        }
    },
    'coex_test_with_ble_keyboard_load': {
        perf_manager.PerfTestTypes.TEST_TYPE_UDP_TX: {
            hostap_config.HostapConfig.MODE_11AX_MIXED: {
                hostap_config.HostapConfig.FREQ_BAND_5G: {
                    hostap_config.HostapConfig.HE_CHANNEL_WIDTH_80: {
                        'BT_connected': (423.12, 380.85),
                        'BT_connected_with_load': (342.76, 283.10),
                        'BT_disconnected_again': (397.56, 382.65)
                    }
                }
            },
            hostap_config.HostapConfig.MODE_11G: {
                hostap_config.HostapConfig.FREQ_BAND_2_4G: {
                    hostap_config.HostapConfig.CHANNEL_WIDTH_22: {
                        'BT_connected': (27.48, 27.08),
                        'BT_connected_with_load': (27.04, 26.53),
                        'BT_disconnected_again': (27.60, 27.24)
                    }
                }
            }
        },
        perf_manager.PerfTestTypes.TEST_TYPE_UDP_RX: {
            hostap_config.HostapConfig.MODE_11AX_MIXED: {
                hostap_config.HostapConfig.FREQ_BAND_5G: {
                    hostap_config.HostapConfig.HE_CHANNEL_WIDTH_80: {
                        'BT_connected': (388.07, 387.99),
                        'BT_connected_with_load': (389.52, 389.04),
                        'BT_disconnected_again': (389.12, 388.18)
                    }
                }
            },
            hostap_config.HostapConfig.MODE_11G: {
                hostap_config.HostapConfig.FREQ_BAND_2_4G: {
                    hostap_config.HostapConfig.CHANNEL_WIDTH_22: {
                        'BT_connected': (39.91, 35.42),
                        'BT_connected_with_load': (39.06, 35.02),
                        'BT_disconnected_again': (38.63, 36.59)
                    }
                }
            }
        },
        perf_manager.PerfTestTypes.TEST_TYPE_TCP_TX: {
            hostap_config.HostapConfig.MODE_11AX_MIXED: {
                hostap_config.HostapConfig.FREQ_BAND_5G: {
                    hostap_config.HostapConfig.HE_CHANNEL_WIDTH_80: {
                        'BT_connected': (749.83, 740.26),
                        'BT_connected_with_load': (746.10, 743.25),
                        'BT_disconnected_again': (751.76, 739.01)
                    }
                }
            },
            hostap_config.HostapConfig.MODE_11G: {
                hostap_config.HostapConfig.FREQ_BAND_2_4G: {
                    hostap_config.HostapConfig.CHANNEL_WIDTH_22: {
                        'BT_connected': (21.78, 21.53),
                        'BT_connected_with_load': (21.65, 21.43),
                        'BT_disconnected_again': (22.03, 22)
                    }
                }
            }
        },
        perf_manager.PerfTestTypes.TEST_TYPE_TCP_RX: {
            hostap_config.HostapConfig.MODE_11AX_MIXED: {
                hostap_config.HostapConfig.FREQ_BAND_5G: {
                    hostap_config.HostapConfig.HE_CHANNEL_WIDTH_80: {
                        'BT_connected': (361.10, 353.30),
                        'BT_connected_with_load': (362.81, 361.24),
                        'BT_disconnected_again': (332.64, 327.27)
                    }
                }
            },
            hostap_config.HostapConfig.MODE_11G: {
                hostap_config.HostapConfig.FREQ_BAND_2_4G: {
                    hostap_config.HostapConfig.CHANNEL_WIDTH_22: {
                        'BT_connected': (22.36, 22.07),
                        'BT_connected_with_load': (22.25, 21.82),
                        'BT_disconnected_again': (22.32, 22.06)
                    }
                }
            }
        }
    },
    'coex_test_with_keyboard_load': {
        perf_manager.PerfTestTypes.TEST_TYPE_UDP_TX: {
            hostap_config.HostapConfig.MODE_11AX_MIXED: {
                hostap_config.HostapConfig.FREQ_BAND_5G: {
                    hostap_config.HostapConfig.HE_CHANNEL_WIDTH_80: {
                        'BT_connected': (274.95, 266.54),
                        'BT_connected_with_load': (280.76, 277.82),
                        'BT_disconnected_again': (280.86, 274.47)
                    }
                }
            },
            hostap_config.HostapConfig.MODE_11G: {
                hostap_config.HostapConfig.FREQ_BAND_2_4G: {
                    hostap_config.HostapConfig.CHANNEL_WIDTH_22: {
                        'BT_connected': (26.84, 26.61),
                        'BT_connected_with_load': (24.94, 24.24),
                        'BT_disconnected_again': (27.48, 27.06)
                    }
                }
            }
        },
        perf_manager.PerfTestTypes.TEST_TYPE_UDP_RX: {
            hostap_config.HostapConfig.MODE_11AX_MIXED: {
                hostap_config.HostapConfig.FREQ_BAND_5G: {
                    hostap_config.HostapConfig.HE_CHANNEL_WIDTH_80: {
                        'BT_connected': (390.14, 379.60),
                        'BT_connected_with_load': (389.04, 385.01),
                        'BT_disconnected_again': (389.47, 376.14)
                    }
                }
            },
            hostap_config.HostapConfig.MODE_11G: {
                hostap_config.HostapConfig.FREQ_BAND_2_4G: {
                    hostap_config.HostapConfig.CHANNEL_WIDTH_22: {
                        'BT_connected': (38.12, 36.96),
                        'BT_connected_with_load': (37.25, 35.10),
                        'BT_disconnected_again': (39.45, 38.35)
                    }
                }
            }
        },
        perf_manager.PerfTestTypes.TEST_TYPE_TCP_TX: {
            hostap_config.HostapConfig.MODE_11AX_MIXED: {
                hostap_config.HostapConfig.FREQ_BAND_5G: {
                    hostap_config.HostapConfig.HE_CHANNEL_WIDTH_80: {
                        'BT_connected': (442.60, 387.68),
                        'BT_connected_with_load': (445.01, 416.68),
                        'BT_disconnected_again': (441.80, 409.17)
                    }
                }
            },
            hostap_config.HostapConfig.MODE_11G: {
                hostap_config.HostapConfig.FREQ_BAND_2_4G: {
                    hostap_config.HostapConfig.CHANNEL_WIDTH_22: {
                        'BT_connected': (21.21, 21.02),
                        'BT_connected_with_load': (20.13, 20.04),
                        'BT_disconnected_again': (21.7, 21.44)
                    }
                }
            }
        },
        perf_manager.PerfTestTypes.TEST_TYPE_TCP_RX: {
            hostap_config.HostapConfig.MODE_11AX_MIXED: {
                hostap_config.HostapConfig.FREQ_BAND_5G: {
                    hostap_config.HostapConfig.HE_CHANNEL_WIDTH_80: {
                        'BT_connected': (314.93, 211.57),
                        'BT_connected_with_load': (321.55, 286.19),
                        'BT_disconnected_again': (318.85, 239.74)
                    }
                }
            },
            hostap_config.HostapConfig.MODE_11G: {
                hostap_config.HostapConfig.FREQ_BAND_2_4G: {
                    hostap_config.HostapConfig.CHANNEL_WIDTH_22: {
                        'BT_connected': (21.11, 20.50),
                        'BT_connected_with_load': (19.98, 19.04),
                        'BT_disconnected_again': (22.26, 21.66)
                    }
                }
            }
        }
    },
    'coex_test_with_ble_mouse_click_load': {
        perf_manager.PerfTestTypes.TEST_TYPE_UDP_TX: {
            hostap_config.HostapConfig.MODE_11AX_MIXED: {
                hostap_config.HostapConfig.FREQ_BAND_5G: {
                    hostap_config.HostapConfig.HE_CHANNEL_WIDTH_80: {
                        'BT_connected': (283.10, 278.15),
                        'BT_connected_with_load': (279.69, 279.34),
                        'BT_disconnected_again': (280.30, 274.91)
                    }
                }
            },
            hostap_config.HostapConfig.MODE_11G: {
                hostap_config.HostapConfig.FREQ_BAND_2_4G: {
                    hostap_config.HostapConfig.CHANNEL_WIDTH_22: {
                        'BT_connected': (27.42, 27.12),
                        'BT_connected_with_load': (27.32, 26.55),
                        'BT_disconnected_again': (26.24, 25.34)
                    }
                }
            }
        },
        perf_manager.PerfTestTypes.TEST_TYPE_UDP_RX: {
            hostap_config.HostapConfig.MODE_11AX_MIXED: {
                hostap_config.HostapConfig.FREQ_BAND_5G: {
                    hostap_config.HostapConfig.HE_CHANNEL_WIDTH_80: {
                        'BT_connected': (391.55, 378.68),
                        'BT_connected_with_load': (388.72, 384.03),
                        'BT_disconnected_again': (389.44, 375.16)
                    }
                }
            },
            hostap_config.HostapConfig.MODE_11G: {
                hostap_config.HostapConfig.FREQ_BAND_2_4G: {
                    hostap_config.HostapConfig.CHANNEL_WIDTH_22: {
                        'BT_connected': (38.78, 36.16),
                        'BT_connected_with_load': (38.94, 32.47),
                        'BT_disconnected_again': (38.88, 38.10)
                    }
                }
            }
        },
        perf_manager.PerfTestTypes.TEST_TYPE_TCP_TX: {
            hostap_config.HostapConfig.MODE_11AX_MIXED: {
                hostap_config.HostapConfig.FREQ_BAND_5G: {
                    hostap_config.HostapConfig.HE_CHANNEL_WIDTH_80: {
                        'BT_connected': (447.12, 445.63),
                        'BT_connected_with_load': (442.34, 407.31),
                        'BT_disconnected_again': (445.74, 415.24)
                    }
                }
            },
            hostap_config.HostapConfig.MODE_11G: {
                hostap_config.HostapConfig.FREQ_BAND_2_4G: {
                    hostap_config.HostapConfig.CHANNEL_WIDTH_22: {
                        'BT_connected': (21.86, 21.45),
                        'BT_connected_with_load': (21.62, 21.33),
                        'BT_disconnected_again': (22.06, 21.84)
                    }
                }
            }
        },
        perf_manager.PerfTestTypes.TEST_TYPE_TCP_RX: {
            hostap_config.HostapConfig.MODE_11AX_MIXED: {
                hostap_config.HostapConfig.FREQ_BAND_5G: {
                    hostap_config.HostapConfig.HE_CHANNEL_WIDTH_80: {
                        'BT_connected': (324.96, 247.41),
                        'BT_connected_with_load': (314.27, 232.56),
                        'BT_disconnected_again': (335.73, 226.84)
                    }
                }
            },
            hostap_config.HostapConfig.MODE_11G: {
                hostap_config.HostapConfig.FREQ_BAND_2_4G: {
                    hostap_config.HostapConfig.CHANNEL_WIDTH_22: {
                        'BT_connected': (22.18, 21.85),
                        'BT_connected_with_load': (22.20, 21.58),
                        'BT_disconnected_again': (22.24, 21.55)
                    }
                }
            }
        }
    }
}


def get_expected_wifi_throughput(test_type, test_name, ap_config, bt_tag):
    """Returns the expected throughput for Wi-Fi BT load coex performance tests.

    @param test_type: The PerfTestTypes test type.
    @param test_name: The test name.
    @param ap_config: The AP configuration.
    @param bt_tag: String for BT operation.

    @return: A tuple of two floats (must,should) of the expected throughput's
             in Mbps.
    """
    return get_expected_value('throughput', expected_throughput_values,
                              test_type, test_name, ap_config, bt_tag)


"""The thresholds defined below are for latency measurements. For the
'mouse_load' test, they are determined based on the highest observed latency
across 100 runs of Wi-Fi and Bluetooth load coexistence tests. For other
tests, they are determined based on the highest observed latency across 10
runs. These values may be enhanced later by running additional tests for 100
runs.
"""
expected_latency_values = {
    'coex_test_with_mouse_click_load': {
        perf_manager.PerfTestTypes.TEST_TYPE_UDP_TX: {
            hostap_config.HostapConfig.MODE_11AX_MIXED: {
                hostap_config.HostapConfig.FREQ_BAND_5G: {
                    hostap_config.HostapConfig.HE_CHANNEL_WIDTH_80: {
                        'BT_connected': 3.55,
                        'BT_connected_with_load': 3.24,
                        'BT_disconnected_again': 3.33
                    }
                }
            },
            hostap_config.HostapConfig.MODE_11G: {
                hostap_config.HostapConfig.FREQ_BAND_2_4G: {
                    hostap_config.HostapConfig.CHANNEL_WIDTH_22: {
                        'BT_connected': 3.82,
                        'BT_connected_with_load': 4.74,
                        'BT_disconnected_again': 2.64
                    }
                }
            }
        },
        perf_manager.PerfTestTypes.TEST_TYPE_UDP_RX: {
            hostap_config.HostapConfig.MODE_11AX_MIXED: {
                hostap_config.HostapConfig.FREQ_BAND_5G: {
                    hostap_config.HostapConfig.HE_CHANNEL_WIDTH_80: {
                        'BT_connected': 1.57,
                        'BT_connected_with_load': 1.63,
                        'BT_disconnected_again': 1.58
                    }
                }
            },
            hostap_config.HostapConfig.MODE_11G: {
                hostap_config.HostapConfig.FREQ_BAND_2_4G: {
                    hostap_config.HostapConfig.CHANNEL_WIDTH_22: {
                            'BT_connected': 5.30,
                            'BT_connected_with_load': 4.51,
                            'BT_disconnected_again': 4.63
                    }
                }
            }
        },
        perf_manager.PerfTestTypes.TEST_TYPE_TCP_TX: {
            hostap_config.HostapConfig.MODE_11AX_MIXED: {
                hostap_config.HostapConfig.FREQ_BAND_5G: {
                    hostap_config.HostapConfig.HE_CHANNEL_WIDTH_80: {
                        'BT_connected': 1.62,
                        'BT_connected_with_load': 2.03,
                        'BT_disconnected_again': 1.69
                    }
                }
            },
            hostap_config.HostapConfig.MODE_11G: {
                hostap_config.HostapConfig.FREQ_BAND_2_4G: {
                    hostap_config.HostapConfig.CHANNEL_WIDTH_22: {
                        'BT_connected': 3.95,
                        'BT_connected_with_load': 4.13,
                        'BT_disconnected_again': 5.12
                    }
                }
            }
        },
        perf_manager.PerfTestTypes.TEST_TYPE_TCP_RX: {
            hostap_config.HostapConfig.MODE_11AX_MIXED: {
                hostap_config.HostapConfig.FREQ_BAND_5G: {
                    hostap_config.HostapConfig.HE_CHANNEL_WIDTH_80: {
                        'BT_connected': 1.60,
                        'BT_connected_with_load': 1.46,
                        'BT_disconnected_again': 1.56
                    }
                }
            },
            hostap_config.HostapConfig.MODE_11G: {
                hostap_config.HostapConfig.FREQ_BAND_2_4G: {
                    hostap_config.HostapConfig.CHANNEL_WIDTH_22: {
                        'BT_connected': 3.80,
                        'BT_connected_with_load': 2.96,
                        'BT_disconnected_again': 5.28
                    }
                }
            }
        }
    },
    'coex_test_with_ble_keyboard_load': {
        perf_manager.PerfTestTypes.TEST_TYPE_UDP_TX: {
            hostap_config.HostapConfig.MODE_11AX_MIXED: {
                hostap_config.HostapConfig.FREQ_BAND_5G: {
                    hostap_config.HostapConfig.HE_CHANNEL_WIDTH_80: {
                        'BT_connected': 1.27,
                        'BT_connected_with_load': 1.30,
                        'BT_disconnected_again': 1.58
                    }
                }
            },
            hostap_config.HostapConfig.MODE_11G: {
                hostap_config.HostapConfig.FREQ_BAND_2_4G: {
                    hostap_config.HostapConfig.CHANNEL_WIDTH_22: {
                        'BT_connected': 1.80,
                        'BT_connected_with_load': 1.52,
                        'BT_disconnected_again': 4.85
                    }
                }
            }
        },
        perf_manager.PerfTestTypes.TEST_TYPE_UDP_RX: {
            hostap_config.HostapConfig.MODE_11AX_MIXED: {
                hostap_config.HostapConfig.FREQ_BAND_5G: {
                    hostap_config.HostapConfig.HE_CHANNEL_WIDTH_80: {
                        'BT_connected': 1.36,
                        'BT_connected_with_load': 1.53,
                        'BT_disconnected_again': 1.48
                    }
                }
            },
            hostap_config.HostapConfig.MODE_11G: {
                hostap_config.HostapConfig.FREQ_BAND_2_4G: {
                    hostap_config.HostapConfig.CHANNEL_WIDTH_22: {
                        'BT_connected': 1.48,
                        'BT_connected_with_load': 5.59,
                        'BT_disconnected_again': 1.66
                    }
                }
            }
        },
        perf_manager.PerfTestTypes.TEST_TYPE_TCP_TX: {
            hostap_config.HostapConfig.MODE_11AX_MIXED: {
                hostap_config.HostapConfig.FREQ_BAND_5G: {
                    hostap_config.HostapConfig.HE_CHANNEL_WIDTH_80: {
                        'BT_connected': 1.43,
                        'BT_connected_with_load': 1.32,
                        'BT_disconnected_again': 1.52
                    }
                }
            },
            hostap_config.HostapConfig.MODE_11G: {
                hostap_config.HostapConfig.FREQ_BAND_2_4G: {
                    hostap_config.HostapConfig.CHANNEL_WIDTH_22: {
                        'BT_connected': 2.27,
                        'BT_connected_with_load': 1.38,
                        'BT_disconnected_again': 1.37
                    }
                }
            }
        },
        perf_manager.PerfTestTypes.TEST_TYPE_TCP_RX: {
            hostap_config.HostapConfig.MODE_11AX_MIXED: {
                hostap_config.HostapConfig.FREQ_BAND_5G: {
                    hostap_config.HostapConfig.HE_CHANNEL_WIDTH_80: {
                        'BT_connected': 1.32,
                        'BT_connected_with_load': 1.33,
                        'BT_disconnected_again': 1.57
                    }
                }
            },
            hostap_config.HostapConfig.MODE_11G: {
                hostap_config.HostapConfig.FREQ_BAND_2_4G: {
                    hostap_config.HostapConfig.CHANNEL_WIDTH_22: {
                        'BT_connected': 2.68,
                        'BT_connected_with_load': 1.70,
                        'BT_disconnected_again': 2.31
                    }
                }
            }
        }
    },
    'coex_test_with_keyboard_load': {
        perf_manager.PerfTestTypes.TEST_TYPE_UDP_TX: {
            hostap_config.HostapConfig.MODE_11AX_MIXED: {
                hostap_config.HostapConfig.FREQ_BAND_5G: {
                    hostap_config.HostapConfig.HE_CHANNEL_WIDTH_80: {
                        'BT_connected': 1.56,
                        'BT_connected_with_load': 1.41,
                        'BT_disconnected_again': 1.40
                    }
                }
            },
            hostap_config.HostapConfig.MODE_11G: {
                hostap_config.HostapConfig.FREQ_BAND_2_4G: {
                    hostap_config.HostapConfig.CHANNEL_WIDTH_22: {
                        'BT_connected': 1.72,
                        'BT_connected_with_load': 1.47,
                        'BT_disconnected_again': 1.30
                    }
                }
            }
        },
        perf_manager.PerfTestTypes.TEST_TYPE_UDP_RX: {
            hostap_config.HostapConfig.MODE_11AX_MIXED: {
                hostap_config.HostapConfig.FREQ_BAND_5G: {
                    hostap_config.HostapConfig.HE_CHANNEL_WIDTH_80: {
                        'BT_connected': 1.54,
                        'BT_connected_with_load': 1.46,
                        'BT_disconnected_again': 2.35
                    }
                }
            },
            hostap_config.HostapConfig.MODE_11G: {
                hostap_config.HostapConfig.FREQ_BAND_2_4G: {
                    hostap_config.HostapConfig.CHANNEL_WIDTH_22: {
                        'BT_connected': 1.60,
                        'BT_connected_with_load': 1.46,
                        'BT_disconnected_again': 2.88,
                    }
                }
            }
        },
        perf_manager.PerfTestTypes.TEST_TYPE_TCP_TX: {
            hostap_config.HostapConfig.MODE_11AX_MIXED: {
                hostap_config.HostapConfig.FREQ_BAND_5G: {
                    hostap_config.HostapConfig.HE_CHANNEL_WIDTH_80: {
                        'BT_connected': 1.40,
                        'BT_connected_with_load': 1.45,
                        'BT_disconnected_again': 1.44
                    }
                }
            },
            hostap_config.HostapConfig.MODE_11G: {
                hostap_config.HostapConfig.FREQ_BAND_2_4G: {
                    hostap_config.HostapConfig.CHANNEL_WIDTH_22: {
                        'BT_connected': 3.80,
                        'BT_connected_with_load': 1.90,
                        'BT_disconnected_again': 1.77
                    }
                }
            }
        },
        perf_manager.PerfTestTypes.TEST_TYPE_TCP_RX: {
            hostap_config.HostapConfig.MODE_11AX_MIXED: {
                hostap_config.HostapConfig.FREQ_BAND_5G: {
                    hostap_config.HostapConfig.HE_CHANNEL_WIDTH_80: {
                        'BT_connected': 1.59,
                        'BT_connected_with_load': 1.44,
                        'BT_disconnected_again': 1.46
                    }
                }
            },
            hostap_config.HostapConfig.MODE_11G: {
                hostap_config.HostapConfig.FREQ_BAND_2_4G: {
                    hostap_config.HostapConfig.CHANNEL_WIDTH_22: {
                        'BT_connected': 1.63,
                        'BT_connected_with_load': 1.62,
                        'BT_disconnected_again': 1.61
                    }
                }
            }
        }
    },
    'coex_test_with_ble_mouse_click_load': {
        perf_manager.PerfTestTypes.TEST_TYPE_UDP_TX: {
            hostap_config.HostapConfig.MODE_11AX_MIXED: {
                hostap_config.HostapConfig.FREQ_BAND_5G: {
                    hostap_config.HostapConfig.HE_CHANNEL_WIDTH_80: {
                        'BT_connected': 1.48,
                        'BT_connected_with_load': 1.45,
                        'BT_disconnected_again': 1.36
                    }
                }
            },
            hostap_config.HostapConfig.MODE_11G: {
                hostap_config.HostapConfig.FREQ_BAND_2_4G: {
                    hostap_config.HostapConfig.CHANNEL_WIDTH_22: {
                        'BT_connected': 2.52,
                        'BT_connected_with_load': 1.44,
                        'BT_disconnected_again': 1.52
                    }
                }
            }
        },
        perf_manager.PerfTestTypes.TEST_TYPE_UDP_RX: {
            hostap_config.HostapConfig.MODE_11AX_MIXED: {
                hostap_config.HostapConfig.FREQ_BAND_5G: {
                    hostap_config.HostapConfig.HE_CHANNEL_WIDTH_80: {
                        'BT_connected': 1.57,
                        'BT_connected_with_load': 1.48,
                        'BT_disconnected_again': 2.37
                    }
                }
            },
            hostap_config.HostapConfig.MODE_11G: {
                hostap_config.HostapConfig.FREQ_BAND_2_4G: {
                    hostap_config.HostapConfig.CHANNEL_WIDTH_22: {
                        'BT_connected': 1.37,
                        'BT_connected_with_load': 1.28,
                        'BT_disconnected_again': 2.47
                    }
                }
            }
        },
        perf_manager.PerfTestTypes.TEST_TYPE_TCP_TX: {
            hostap_config.HostapConfig.MODE_11AX_MIXED: {
                hostap_config.HostapConfig.FREQ_BAND_5G: {
                    hostap_config.HostapConfig.HE_CHANNEL_WIDTH_80: {
                        'BT_connected': 1.45,
                        'BT_connected_with_load': 1.56,
                        'BT_disconnected_again': 1.53
                    }
                }
            },
            hostap_config.HostapConfig.MODE_11G: {
                hostap_config.HostapConfig.FREQ_BAND_2_4G: {
                    hostap_config.HostapConfig.CHANNEL_WIDTH_22: {
                        'BT_connected': 2.18,
                        'BT_connected_with_load': 1.67,
                        'BT_disconnected_again': 4.58
                    }
                }
            }
        },
        perf_manager.PerfTestTypes.TEST_TYPE_TCP_RX: {
            hostap_config.HostapConfig.MODE_11AX_MIXED: {
                hostap_config.HostapConfig.FREQ_BAND_5G: {
                    hostap_config.HostapConfig.HE_CHANNEL_WIDTH_80: {
                        'BT_connected': 1.62,
                        'BT_connected_with_load': 1.61,
                        'BT_disconnected_again': 1.60
                    }
                }
            },
            hostap_config.HostapConfig.MODE_11G: {
                hostap_config.HostapConfig.FREQ_BAND_2_4G: {
                    hostap_config.HostapConfig.CHANNEL_WIDTH_22: {
                        'BT_connected': 1.32,
                        'BT_connected_with_load': 1.32,
                        'BT_disconnected_again': 1.52
                    }
                }
            }
        }
    }
}


def get_expected_wifi_latency(test_type, test_name, ap_config, bt_tag):
    """Returns the expected latency for Wi-Fi BT load coex tests.

    @param test_type: The PerfTestTypes test type.
    @param test_name: The test name.
    @param ap_config: The AP configuration.
    @param bt_tag: String for BT operation.

    @return: Float value for the expected latency in milliseconds.
    """
    return get_expected_value('latency', expected_latency_values, test_type,
                              test_name, ap_config, bt_tag)
