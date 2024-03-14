# Lint as: python2, python3
# Copyright 2020 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""A Batch of of Bluetooth Advertisement Monitor API tests"""

from autotest_lib.server.cros.bluetooth.bluetooth_adapter_quick_tests \
     import BluetoothAdapterQuickTests
from autotest_lib.server.cros.bluetooth.bluetooth_adapter_adv_monitor_tests \
     import (BluetoothAdapterAdvMonitorTests, ADVMON_UNSUPPORTED_CHIPSETS)
from autotest_lib.server.cros.bluetooth.bluetooth_adapter_tests import (
        SUSPEND_POWER_DOWN_CHIPSETS, SUSPEND_POWER_DOWN_MODELS)


class bluetooth_AdapterAdvMonitor(BluetoothAdapterQuickTests,
                                  BluetoothAdapterAdvMonitorTests):
    """A Batch of Bluetooth Advertisement Monitor tests. This test is written
       as a batch of tests in order to reduce test time, since auto-test ramp
       up time is costly. The batch is using BluetoothAdapterQuickTests wrapper
       methods to start and end a test and a batch of tests.

       This class can be called to run the entire test batch or to run a
       specific test only.

    """

    test_wrapper = BluetoothAdapterQuickTests.quick_test_test_decorator
    batch_wrapper = BluetoothAdapterQuickTests.quick_test_batch_decorator


    @test_wrapper('Monitor Object Health Tests',
                  supports_floss=True)
    def advmon_monitor_health_tests(self):
        """Tests advertisement monitor object health."""
        self.advmon_test_monitor_creation()
        self.advmon_test_monitor_validity()


    @test_wrapper('Single Client Tests - Pattern Filter',
                  devices={
                          'BLE_KEYBOARD': 1,
                          'BLE_MOUSE': 1
                  },
                  skip_chipsets=ADVMON_UNSUPPORTED_CHIPSETS,
                  supports_floss=True)
    def advmon_pattern_filter_tests(self):
        """Tests pattern filter for single client."""
        self.advmon_test_pattern_filter()


    @test_wrapper('Single Client Tests - RSSI Filter Range',
                  devices={
                          'BLE_KEYBOARD': 1,
                          'BLE_MOUSE': 1
                  },
                  supports_floss=True)
    def advmon_rssi_filter_range_tests(self):
        """Tests RSSI filter range for single client."""
        self.advmon_test_rssi_filter_range()


    @test_wrapper('Single Client Tests - RSSI Filter Multi Peers',
                  devices={
                          'BLE_KEYBOARD': 1,
                          'BLE_MOUSE': 1
                  },
                  supports_floss=True)
    def advmon_rssi_filter_multi_peers_tests(self):
        """Tests RSSI filter with multiple peers for single client."""
        self.advmon_test_rssi_filter_multi_peers()


    @test_wrapper('Single Client Tests - RSSI Filter Reset',
                  devices={
                          'BLE_KEYBOARD': 1,
                          'BLE_MOUSE': 1
                  },
                  supports_floss=True)
    def advmon_rssi_filter_reset_tests(self):
        """Tests RSSI filter reset for single client."""
        self.advmon_test_rssi_filter_reset()


    @test_wrapper('Multi Client Tests',
                  devices={
                          'BLE_KEYBOARD': 1,
                          'BLE_MOUSE': 1
                  },
                  supports_floss=False)
    def advmon_multi_client_tests(self):
        """Tests monitor functionality for multiple clients."""
        self.advmon_test_multi_client()


    @test_wrapper('Foreground Background Combination Tests',
                  devices={
                          'BLE_KEYBOARD': 1,
                          'BLE_MOUSE': 1
                  },
                  supports_floss=True)
    def advmon_fg_bg_combination_tests(self):
        """Tests foreground and background scanning working together."""
        self.advmon_test_fg_bg_combination()


    # TODO(b/150897528) - Dru loses firmware around suspend, which causes bluez
    #                     removes all the monitors.
    @test_wrapper('Suspend Resume Tests',
                  devices={
                          'BLE_KEYBOARD': 1,
                          'BLE_MOUSE': 1
                  },
                  skip_models=SUSPEND_POWER_DOWN_MODELS,
                  skip_chipsets=SUSPEND_POWER_DOWN_CHIPSETS,
                  supports_floss=False)
    def advmon_suspend_resume_tests(self):
        """Tests working of background scanning with suspend resume."""
        self.advmon_test_suspend_resume()


    # TODO(b/150897528) - Dru loses firmware around suspend, which causes bluez
    #                     removes all the monitors.
    @test_wrapper('Interleave Scan Tests',
                  devices={'BLE_MOUSE': 1},
                  skip_models=SUSPEND_POWER_DOWN_MODELS,
                  skip_chipsets=SUSPEND_POWER_DOWN_CHIPSETS,
                  supports_floss=False)
    def advmon_interleaved_scan_tests(self):
        """Tests interleave scan."""
        self.advmon_test_interleaved_scan()

    # TODO(b/267641212) - RTL8852 supports (1 + |address|) * |pattern| <= 20,
    #                     but we have 5 addresses and 4 patterns here.
    @test_wrapper('Condition Device Count Tests',
                  devices={'BLE_MOUSE': 1},
                  skip_chipsets=ADVMON_UNSUPPORTED_CHIPSETS +
                  ['Realtek-RTL8852C-USB', 'Realtek-RTL8852A-USB'],
                  supports_floss=True)
    def advmon_condition_device_count_tests(self):
        """Tests minimum supported condition and device count."""
        self.advmon_test_condition_device_count()

    @test_wrapper('HCI events Filtered',
                  devices={
                          'BLE_KEYBOARD': 1,
                          'BLE_MOUSE': 1
                  },
                  skip_chipsets=ADVMON_UNSUPPORTED_CHIPSETS,
                  supports_floss=True,
                  flags=['Quick Health'])
    def advmon_hci_events_filtered_tests(self):
        """Tests HCI events are correctly filtered."""
        self.advmon_test_hci_events_filtered()

    @test_wrapper('Scan performance test',
                  devices={'BLE_MOUSE': 1},
                  supports_floss=True,
                  flags=['Quick Health'])
    def advmon_scanner_performance_tests(self):
        """Tests scanner performance in different params."""
        self.advmon_test_scanner_performance()

    @batch_wrapper('Advertisement Monitor API')
    def advmon_health_batch_run(self, num_iterations=1, test_name=None):
        """Run the Advertisement Monitor test batch or a specific given test.
           The wrapper of this method is implemented in batch_decorator.
           Using the decorator a test batch method can implement the only its
           core tests invocations and let the decorator handle the wrapper,
           which is taking care for whether to run a specific test or the
           batch as a whole, and running the batch in iterations.

           @param num_iterations: how many iterations to run.
           @param test_name: specific test to run otherwise None to run the
                             whole batch.

        """
        self.advmon_monitor_health_tests()
        self.advmon_pattern_filter_tests()
        self.advmon_rssi_filter_range_tests()
        self.advmon_rssi_filter_multi_peers_tests()
        self.advmon_rssi_filter_reset_tests()
        self.advmon_multi_client_tests()
        # TODO(b/252440201) - Disable fg_bg test until fixed. See #comment8.
        # self.advmon_fg_bg_combination_tests()
        self.advmon_suspend_resume_tests()
        self.advmon_interleaved_scan_tests()
        self.advmon_condition_device_count_tests()
        self.advmon_hci_events_filtered_tests()
        self.advmon_scanner_performance_tests()

    def run_once(self,
                 host,
                 num_iterations=1,
                 peer_required=True,
                 args_dict=None,
                 test_name=None,
                 flag='Quick Health',
                 floss=False):
        """Run the batch of Bluetooth Advertisement Monitor API tests.

        @param host: the DUT, usually a chromebook.
        @param num_iterations: the number of rounds to execute the test.
        @param test_name: the test to run, or None for all tests.

        """

        # Initialize and run the test batch or the requested specific test.
        self.quick_test_init(host,
                             use_btpeer=peer_required,
                             flag=flag,
                             args_dict=args_dict,
                             floss=floss)
        self.advmon_health_batch_run(num_iterations, test_name)
        self.quick_test_cleanup()
