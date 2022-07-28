# Lint as: python3
# Copyright 2022 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""This class implements a Bluetooth quick health package"""

from autotest_lib.client.cros.bluetooth import (bluetooth_avl_driver_tests,
                                                bluetooth_avl_hci_tests)


class bluetooth_AdapterQuickHealthClient(
        bluetooth_avl_driver_tests.BluetoothAVLDriverTests,
        bluetooth_avl_hci_tests.BluetoothAVLHCITests):
    """This class implements a client side Bluetooth quick health package.

    The package is running several sub batches of tests.
    A batch is defined as a set of tests, preferably with a common subject, e.g
    'AVLHCI' batch, or the 'AVLDriver' batch.
    The quick health test package is improving test time by doing the minimal
    cleanups between each test and test batches, saving the auto-test ramp up
    time of about 90-120 second per test.
    """

    def run_once(self, num_iterations=1, flag='Quick Health'):
        """Runs the package of Bluetooth Quick Health client side tests.

        @param num_iterations: The number of rounds to execute the test.
        @param flag: List of string to describe who should run the test.
                     The string could be one of the following:
                         ['AVL', 'Quick Health', 'All']
        """

        self.quick_test_init(flag=flag)
        self.quick_test_package_start('BT Quick Health Client')

        for iter in range(1, num_iterations + 1):
            self.quick_test_package_update_iteration(iter)

            self.avl_hci_batch_run()
            self.avl_driver_batch_run()

            self.quick_test_print_summary()

        self.quick_test_package_end()
