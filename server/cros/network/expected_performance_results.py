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
3- The channel width:
    a) 20 MHz
    b) 40 MHz
    c) 80 MHz
"""

expected_throughput_wifi = {
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


def get_expected_throughput_wifi(test_type, mode, channel_width):
    """returns the expected throughput for WiFi only performance tests.

    @param test_type: the PerfTestTypes test type.

    @param mode: the WiFi mode such as 80211n.

    @param channel_width: the channel width used in the test.

    @return a tuple of two integers (must,should) of the expected throughputs in Mbps.

    """
    if test_type in expected_throughput_wifi:
        if mode in expected_throughput_wifi[test_type]:
            if channel_width in expected_throughput_wifi[test_type][mode]:
                return expected_throughput_wifi[test_type][mode][channel_width]
    ret_mode = hostap_config.HostapConfig.VHT_NAMES[channel_width]
    if ret_mode is None:
        ret_mode = hostap_config.HostapConfig.HT_NAMES[channel_width]
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
                perf_manager.PerfTestTypes.TEST_TYPE_UDP_TX: 200,
                perf_manager.PerfTestTypes.TEST_TYPE_UDP_RX: 300
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
