# Lint as: python3
# Copyright 2022 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from autotest_lib.client.cros.bluetooth.bluetooth_avl_driver_tests import (
        BluetoothAVLDriverTests)


class bluetooth_AVLDriver(BluetoothAVLDriverTests):
    """Test bluetooth AVL driver requirements.

    The real implementations are in
    client/cros/bluetooth/bluetooth_avl_driver_tests.py
    """

    def run_once(self, num_iterations=1, test_name=None):
        """Runs bluetooth_AVLDriver.

        @param num_iterations: Number of times to repeat run.
        @param test_name: test name as string from control file.
        """
        self.quick_test_init(flag='Quick Health')
        self.avl_driver_batch_run(num_iterations, test_name)
