# Lint as: python2, python3
# Copyright 2022 The ChromiumOS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import logging

# from autotest_lib.client.common_lib import error
from autotest_lib.client.common_lib.cros import kernel_utils
from autotest_lib.client.cros.update_engine import nebraska_wrapper
from autotest_lib.server.cros.update_engine import update_engine_test


class autoupdate_WithFirmware(update_engine_test.UpdateEngineTest):
    """Ensure user data and preferences are preserved during an update."""

    version = 1


    def cleanup(self):
        super(autoupdate_WithFirmware, self).cleanup()


    def run_once(self,
                 full_payload=True,
                 running_at_desk=False,
                 source_build=None,
                 target_build=None):
        """
        Tests that the firmware is also updated along with the OS.

        @param full_payload: True for a full payload. False for delta.
        @param running_at_desk: Indicates test is run locally on a DUT which is
                                not in the lab network.
        @param target_build: An optional parameter to specify the target build
                             for the update when running locally. If no build
                             is supplied, the current version on the DUT will
                             be used. In the lab, the job_repo_url from the
                             host attributes will override this.
        @param source_build: An optional parameter to specify the source build
                             to provision the DUT to.

        """
        # Get payload for the update to ToT.
        payload_url = self.get_payload_for_nebraska(
                build=target_build,
                full_payload=full_payload)

        # Provision the source OS version and firmware for the current board.
        public_bucket = running_at_desk or not self._cache_server_url
        self.provision_dut(with_firmware=True,
                           build_name=source_build,
                           public_bucket=public_bucket)

        # Record DUT state before the update.
        _, inactive = kernel_utils.get_kernel_state(self._host)
        logging.info('Pre-update FW version is %s',
                     self.get_current_fw_version())

        # Perform the update.
        with nebraska_wrapper.NebraskaWrapper(
                host=self._host,
                payload_url=payload_url) as nebraska:
            self._check_for_update(nebraska.get_update_url(),
                                   critical_update=True,
                                   wait_for_completion=True,
                                   update_firmware=True)
            self._wait_for_update_to_complete()
            nebraska.save_log(self.resultsdir)

        self._host.reboot()

        # Wait for the UI to stabilize.
        self._host.wait_for_service('ui')

        # Verify the OS update.
        kernel_utils.verify_boot_expectations(inactive, host=self._host)
        rootfs_hostlog, _ = self._create_hostlog_files()
        self.verify_update_events(self._FORCED_UPDATE, rootfs_hostlog)

        # Verify that the firmware updated.
        actual = self.get_current_fw_version()
        expected = self.get_os_bundled_fw_version()
        logging.info('Expected post-update FW version is %s', expected)
        logging.info('Actual Post-update FW version is %s', actual)
        # TODO(b/228121045): Enable the FW update verification once the client
        # flag is available to trigger the FW update.
        # if actual != expected:
        #     raise error.TestFail('The firmware did not update')
