# Lint as: python2, python3
# Copyright 2022 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
""" Bluetooth test that tests the Fast Pair scenarios."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from base64 import b64decode
import logging

from autotest_lib.client.common_lib import error
from autotest_lib.server.cros.bluetooth.bluetooth_adapter_quick_tests import (
        BluetoothAdapterQuickTests)
from autotest_lib.server.cros.bluetooth.bluetooth_adapter_tests import (
        UNSUPPORTED_BT_HW_FILTERING_CHIPSETS)
from autotest_lib.server import autotest

imported_password_util = True

try:
    # Importing this private util fails on public boards (e.g amd64-generic)
    from autotest_lib.client.common_lib.cros import password_util
except ImportError:
    imported_password_util = False
    logging.error('Failed to import password_util from autotest-private')

test_wrapper = BluetoothAdapterQuickTests.quick_test_test_decorator


class bluetooth_FastPair(BluetoothAdapterQuickTests):
    """Fast Pair tests"""

    UI_TEST = 'bluetooth_FastPairUI'

    KEY_PEM_ARG_KEY = 'fast_pair_antispoofing_key_pem'

    _key_pem = None

    @test_wrapper('Fast Pair Initial Pairing',
                  devices={'BLE_FAST_PAIR': 1},
                  skip_chipsets=UNSUPPORTED_BT_HW_FILTERING_CHIPSETS)
    def fast_pair_initial_pairing_test(self):
        """Test the Fast Pair initial pairing scenario"""
        try:
            # Setup the Fast Pair device.
            device = self.devices['BLE_FAST_PAIR'][0]
            device.SetAntispoofingKeyPem(self._key_pem)

            # Toggling discoverable here ensures the device starts
            # advertising during this test.
            device.SetDiscoverable(False)
            device.SetDiscoverable(True)

            # Run UI test, which clicks through the pairing UI flow.
            client_at = autotest.Autotest(self._host)
            client_at.run_test(self.UI_TEST)
            client_at._check_client_test_result(self._host, self.UI_TEST)

            # Verify device is paired.
            return self.bluetooth_facade.device_is_paired(device.address)
        except Exception as e:
            logging.error('exception in fast_pair_initial_pairing_test %s',
                          str(e))
            return False

    def set_key_pem(self, args_dict):
        if imported_password_util:
            self._key_pem = b64decode(
                    password_util.get_fast_pair_anti_spoofing_key())

        elif args_dict is not None and self.KEY_PEM_ARG_KEY in args_dict:
            self._key_pem = b64decode(args_dict[self.KEY_PEM_ARG_KEY])

        if self._key_pem is None:
            raise error.TestError('Valid %s arg is missing' %
                                  self.KEY_PEM_ARG_KEY)

    def run_once(self, host, args_dict=None):
        """Running Fast Pair tests.

        @param host: the DUT, usually a chromebook
        @param args_dict: dictionary of args to use during test

        """

        # First set required args
        self.set_key_pem(args_dict)

        self._host = host
        self.quick_test_init(host, use_btpeer=True, args_dict=args_dict)
        self.fast_pair_initial_pairing_test()
        self.quick_test_cleanup()
