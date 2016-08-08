# Copyright 2016 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from autotest_lib.client.common_lib.cros import tpm_utils
from autotest_lib.server import test, autotest


class enterprise_LongevityTrackerServer(test.test):
    """A test that runs enterprise_KioskEnrollment and clears the TPM as
    necessary. After enterprise enrollment is successful, it collects and logs
    cpu, memory and temperature data from the device under test."""
    version = 1


    def run_once(self, host=None, kiosk_app_attributes=None):
        self.client = host

        tpm_utils.ClearTPMOwnerRequest(self.client)
        autotest.Autotest(self.client).run_test('enterprise_KioskEnrollment',
                kiosk_app_attributes=kiosk_app_attributes,
                check_client_result=True)
        for cycle in range(5):
            autotest.Autotest(self.client).run_test('longevity_Tracker',
                    kiosk_app_attributes=kiosk_app_attributes,
                    check_client_result=True)
        tpm_utils.ClearTPMOwnerRequest(self.client)
