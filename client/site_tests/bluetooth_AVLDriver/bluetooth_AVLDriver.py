# Lint as: python3
# Copyright 2022 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import logging
import os

from autotest_lib.client.common_lib import error
from autotest_lib.client.cros.bluetooth.bluetooth_quick_tests import (
        BluetoothQuickTests)


class bluetooth_AVLDriver(BluetoothQuickTests):
    """Test bluetooth AVL driver requirements."""
    test_wrapper = BluetoothQuickTests.quick_test_test_decorator
    batch_wrapper = BluetoothQuickTests.quick_test_batch_decorator
    test_log_result = BluetoothQuickTests.test_log_result

    @test_wrapper('Driver support test', flags=['Quick Health'])
    def driver_support_test(self):
        """Tests - AVL Linux Driver Requirements - Driver Support."""

        transport = self.bluetooth_facade.get_bt_transport()
        if transport is None:
            raise error.TestError('Failed to get BT transport')

        if transport == 'USB':
            self.test_use_usb_driver()
        elif transport == 'UART':
            self.test_use_serial_driver()
        else:
            logging.info('No need to test the used driver, transport is %s',
                         transport)

    def driver_path(self):
        """Returns the path of the first Bluetooth adapter."""
        hci_path = os.path.realpath('/sys/class/bluetooth/hci0')
        return os.path.realpath(hci_path + '/../../driver')

    @test_log_result
    def test_use_usb_driver(self):
        """Verifies a USB controller uses the btusb driver."""
        path = self.driver_path()
        self.results['driver_path'] = path
        return path == '/sys/bus/usb/drivers/btusb'

    @test_log_result
    def test_use_serial_driver(self):
        """Verifies a UART controller uses the serdev interface."""
        path = self.driver_path()
        self.results['driver_path'] = path
        return path.startswith('/sys/bus/serial/drivers/')

    @batch_wrapper('AVLDriver batch')
    def avl_driver_batch_run(self, num_iterations=1, test_name=None):
        """Runs bluetooth_AVLDriver test batch (all test).

        @param num_iterations: Number of times to run batch.
        @param test_name: test name as string from control file.
        """
        self.driver_support_test()

    def run_once(self, num_iterations=1, test_name=None):
        """Runs bluetooth_AVLDriver.

        @param num_iterations: Number of times to repeat run.
        @param test_name: test name as string from control file.
        """
        self.quick_test_init(flag='Quick Health')
        self.avl_driver_batch_run(num_iterations, test_name)
