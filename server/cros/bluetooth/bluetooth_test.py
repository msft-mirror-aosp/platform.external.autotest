# Copyright (c) 2013 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from autotest_lib.server import test
from autotest_lib.server.cros import interactive_client
from autotest_lib.server.cros.bluetooth import bluetooth_device


class BluetoothTest(test.test):
    """Base class for Bluetooth tests.

    BluetoothTest provides a common warmup() and cleanup() function for the
    collection of Bluetooth tests that sets the following properties, depending
    on the arguments to the test and properties of the test object:

      self.device - BluetoothDevice object for the device being tested
      self.interactive - InteractiveClient object for the device

    self.interactive may be None if the test is initialized from the control
    file with  the interactive argument as False.

    It is not mandatory to use this base class for Bluetooth tests, it is for
    convenience only. A test with special requirements, or a need to derive
    from a different base class, may instantiate and clean-up the associated
    objects on its own.

    """

    def warmup(self, device_host, interactive=False):
        """Initialize the test member objects based on its arguments."""
        if interactive:
            self.interactive = interactive_client.InteractiveClient(device_host)
        else:
            self.interactive = None

        self.device = bluetooth_device.BluetoothDevice(device_host)


    def cleanup(self):
        """Close the test member objects."""
        if self.interactive:
            self.interactive.close()
        self.device.copy_logs(self.outputdir)
        self.device.close()

        super(BluetoothTest, self).cleanup()
