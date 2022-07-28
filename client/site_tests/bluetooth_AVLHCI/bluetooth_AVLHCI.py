# Lint as: python3
# Copyright 2022 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from autotest_lib.client.cros.bluetooth.bluetooth_avl_hci_tests import (
        BluetoothAVLHCITests)


class bluetooth_AVLHCI(BluetoothAVLHCITests):
    """Test bluetooth avl HCI requirements.

    The real implementations are in
    client/cros/bluetooth/bluetooth_avl_hci_tests.py
    """

    def run_once(self, num_iterations=1, test_name=None):
        """Runs bluetooth_AVLHCI.

        @param num_iterations: Number of times to repeat run.
        @param test_name: test name as string from control file.
        """
        self.quick_test_init(flag='Quick Health')
        self.avl_hci_batch_run(num_iterations, test_name)
