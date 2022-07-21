# Lint as: python2, python3
# Copyright 2021 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import logging

from autotest_lib.client.common_lib.cros import kernel_utils
from autotest_lib.server.cros.update_engine import update_engine_test


class autoupdate_Lacros(update_engine_test.UpdateEngineTest):
    """Performs a simple AU test and checks lacros."""
    version = 1

    def cleanup(self):
        super(autoupdate_Lacros, self).cleanup()

    def run_once(self,
                 full_payload,
                 m2n=False,
                 running_at_desk=False,
                 build=None):
        """
        Performs autoupdate with Nebraska and checks rootfs-lacros.

        @param full_payload: True for full payload, False for delta
        @param running_at_desk: Indicates test is run locally from workstation.
                                Flag does not work with M2N tests.
        @param build: An optional parameter to specify the target build for the
                      update when running locally. If no build is supplied, the
                      current version on the DUT will be used.

        """
        # Get a payload to use for the test.
        payload_url = self.get_payload_for_nebraska(
                full_payload=full_payload,
                public_bucket=running_at_desk,
                build=build)

        if m2n:
            # Provision latest stable build for the current board.
            self.provision_dut(public_bucket=running_at_desk)

        # Login and check rootfs-lacros version
        self._run_client_test_and_check_result('desktopui_RootfsLacros',
                                               tag='before')
        before_version = self._host.run(['cat',
                                         '/tmp/lacros_version.txt']).stdout
        logging.info('rootfs-lacros version before update: %s', before_version)

        # Record DUT state before the update.
        active, inactive = kernel_utils.get_kernel_state(self._host)

        # Perform the update.
        self._run_client_test_and_check_result('autoupdate_CannedOmahaUpdate',
                                               payload_url=payload_url)

        # Verify the update completed successfully.
        self._host.reboot()
        kernel_utils.verify_boot_expectations(inactive, host=self._host)
        rootfs_hostlog, _ = self._create_hostlog_files()
        self.verify_update_events(self._FORCED_UPDATE, rootfs_hostlog)

        # Check the rootfs-lacros version again.
        self._run_client_test_and_check_result('desktopui_RootfsLacros',
                                               tag='after',
                                               dont_override_profile=True)
        after_version = self._host.run(['cat',
                                        '/tmp/lacros_version.txt']).stdout
        logging.info('rootfs-lacros version after update: %s', after_version)
