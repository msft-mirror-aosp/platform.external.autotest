# Lint as: python2, python3
# Copyright 2022 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Server side bluetooth tests on LL Privacy"""

from autotest_lib.server.cros.bluetooth import bluetooth_adapter_tests

# List of the controllers that does not support LL privacy.
LL_PRIVACY_UNSUPPORTED_CHIPSETS = [
        'Realtek-RTL8852A-USB',
        'Realtek-RTL8852C-USB',
        'Realtek-RTL8822C-UART',
        'Realtek-RTL8822C-USB',
]


class BluetoothAdapterLLPrivacyTests(
        bluetooth_adapter_tests.BluetoothAdapterTests):
    """Server side bluetooth adapter ll privacy Test.

    This class comprises a number of test cases to verify bluetooth
    LL privacy.
    """

    test_case_log = bluetooth_adapter_tests.test_case_log
    test_retry_and_log = bluetooth_adapter_tests.test_retry_and_log
