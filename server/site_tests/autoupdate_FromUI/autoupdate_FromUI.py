# Lint as: python2, python3
# Copyright 2020 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from autotest_lib.client.common_lib.cros import kernel_utils
from autotest_lib.server.cros.update_engine import update_engine_test


class autoupdate_FromUI(update_engine_test.UpdateEngineTest):
    """Trigger an update from the UI.

    Start an update by clicking on the 'Check for update' button in the
    ChromeOS settings menu, instead of calling to update_engine_client
    directly.

    """
    version = 1
    _UI_TEST = 'autoupdate_UpdateFromUI'


    def run_once(self, full_payload=True, running_at_desk=False, build=None):
        """
        Tests that we can successfully perform an update via the UI.

        @param full_payload: True for a full payload. False for delta.
        @param running_at_desk: True if the test is being run locally.
        @param build: An optional parameter to specify the target build for the
                      update when running locally. If no build is supplied, the
                      current version on the DUT will be used.

        """
        payload_url = self.get_payload_for_nebraska(
                full_payload=full_payload,
                public_bucket=running_at_desk,
                build=build)

        active, inactive = kernel_utils.get_kernel_state(self._host)
        # Login and click 'Check for update' in the Settings app.
        self._run_client_test_and_check_result(self._UI_TEST,
                                               payload_url=payload_url)

        self._host.reboot()

        # Check that the update completed successfully
        rootfs_hostlog, _ = self._create_hostlog_files()
        self.verify_update_events(self._CUSTOM_LSB_VERSION, rootfs_hostlog)
        kernel_utils.verify_boot_expectations(inactive, host=self._host)
