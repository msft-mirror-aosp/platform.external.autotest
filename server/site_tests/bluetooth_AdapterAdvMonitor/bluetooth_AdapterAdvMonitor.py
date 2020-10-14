# Copyright 2020 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""A Batch of of Bluetooth Advertisement Monitor API tests"""

from autotest_lib.server.cros.bluetooth.bluetooth_adapter_quick_tests \
     import BluetoothAdapterQuickTests
from autotest_lib.server.cros.bluetooth.bluetooth_adapter_adv_monitor_tests \
     import BluetoothAdapterAdvMonitorTests


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


    @test_wrapper('Monitor Object Sanity Tests')
    def advmon_monitor_sanity_tests(self):
        """Tests advertisement monitor object sanity."""
        self.advmon_test_monitor_creation()
        self.advmon_test_monitor_validity()


    @test_wrapper('Single Client Tests',
                  devices={'BLE_KEYBOARD':1, 'BLE_MOUSE':1})
    def advmon_single_client_tests(self):
        """Tests monitor functionality for single client."""
        self.advmon_test_pattern_filter_1()
        self.advmon_test_rssi_filter_1()
        self.advmon_test_rssi_filter_2()
        self.advmon_test_rssi_filter_3()


    @test_wrapper('Foreground Background Combination Tests',
                  devices={'BLE_KEYBOARD':1, 'BLE_MOUSE':1})
    def advmon_fg_bg_combination_tests(self):
        """Tests foreground and background scanning working together."""
        self.advmon_test_fg_bg_combination()


    @batch_wrapper('Advertisement Monitor API')
    def advmon_batch_run(self, num_iterations=1, test_name=None):
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
        self.advmon_monitor_sanity_tests()
        self.advmon_single_client_tests()
        self.advmon_fg_bg_combination_tests()


    def run_once(self,
                 host,
                 num_iterations=1,
                 btpeer_args=[],
                 test_name=None,
                 flag='Quick Sanity'):
        """Run the batch of Bluetooth Advertisement Monitor API tests.

        @param host: the DUT, usually a chromebook.
        @param num_iterations: the number of rounds to execute the test.
        @param test_name: the test to run, or None for all tests.

        """

        # Initialize and run the test batch or the requested specific test.
        self.quick_test_init(host,
                             use_btpeer=True,
                             flag=flag,
                             btpeer_args=btpeer_args)
        self.advmon_batch_run(num_iterations, test_name)
        self.quick_test_cleanup()