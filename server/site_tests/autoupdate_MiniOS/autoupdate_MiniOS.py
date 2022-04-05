# Lint as: python3
# Copyright 2022 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import logging

from autotest_lib.client.common_lib import error
from autotest_lib.client.common_lib.cros import kernel_utils
from autotest_lib.server.cros.minios import minios_test


class autoupdate_MiniOS(minios_test.MiniOsTest):
    """Tests MiniOS update. """

    version = 1

    def cleanup(self):
        self._save_extra_update_engine_logs(number_of_logs=2)
        super(autoupdate_MiniOS, self).cleanup()

    def run_once(self,
                 full_payload=True,
                 job_repo_url=None,
                 with_os=False,
                 with_dlc=False,
                 running_at_desk=False):
        """
        Tests that we can successfully update MiniOS along with the OS.

        @param full_payload: True for full OS and DLC payloads. False for delta.
        @param job_repo_url: This is used to figure out the current build and
                             the devserver to use. The test will read this
                             from a host argument when run in the lab.
        @param with_os: True for MiniOS update along with Platform (OS)
                             update. False for MiniOS only update.
        @param with_dlc: True for MiniOS update with Platform (OS) and DLC.
                             False for turning off DLC update.
        @param running_at_desk: Indicates test is run locally from a
                                workstation.

        """
        if not with_os and with_dlc:
            logging.info("DLC only updates with the platform (OS), "
                         "automatically set with_os to True.")
            with_os = True

        payload_urls = []
        # Payload URL for the MiniOS update.
        # We'll always need a full payload for MiniOS update.
        payload_urls.append(
                self.get_payload_for_nebraska(
                        job_repo_url=job_repo_url,
                        full_payload=True,
                        payload_type=self._PAYLOAD_TYPE.MINIOS,
                        public_bucket=running_at_desk))
        if with_os:
            # Payload URL for the platform (OS) update.
            payload_urls.append(
                    self.get_payload_for_nebraska(
                            job_repo_url=job_repo_url,
                            full_payload=full_payload,
                            public_bucket=running_at_desk))
        if with_dlc:
            # Payload URLs for sample-dlc, a test DLC package.
            # We'll always need a full payload for DLC installation,
            # and optionally a delta payload if required by the test.
            payload_urls.append(
                    self.get_payload_for_nebraska(
                            job_repo_url=job_repo_url,
                            full_payload=True,
                            payload_type=self._PAYLOAD_TYPE.DLC,
                            public_bucket=running_at_desk))
            if not full_payload:
                payload_urls.append(
                        self.get_payload_for_nebraska(
                                job_repo_url=job_repo_url,
                                full_payload=False,
                                payload_type=self._PAYLOAD_TYPE.DLC,
                                public_bucket=running_at_desk))

        # Record DUT state before the update.
        active_cros, inactive_cros = kernel_utils.get_kernel_state(self._host)
        active_minios, inactive_minios = kernel_utils.get_minios_priority(
                self._host)

        # Update MiniOS.
        if with_dlc:
            self._run_client_test_and_check_result(
                    'autoupdate_InstallAndUpdateDLC',
                    payload_urls=payload_urls,
                    allow_failure=not with_os)
        else:
            self._run_client_test_and_check_result(
                    'autoupdate_CannedOmahaUpdate',
                    payload_url=payload_urls,
                    allow_failure=not with_os)

        # MiniOS only updates with platform (OS) update.
        if with_os:
            # Verify the MiniOS update completed successfully.
            kernel_utils.verify_minios_priority_after_update(
                    self._host, expected=inactive_minios)

            # Verify the platform (OS) update completed successfully.
            self._host.reboot()
            kernel_utils.verify_boot_expectations(inactive_cros,
                                                  host=self._host)
            rootfs_hostlog, _ = self._create_hostlog_files()
            self.verify_update_events(self._FORCED_UPDATE, rootfs_hostlog)

            if with_dlc:
                # Verify the DLC update completed successfully.
                dlc_rootfs_hostlog, _ = self._create_dlc_hostlog_files()
                logging.info('Checking DLC update events')
                self.verify_update_events(
                        self._FORCED_UPDATE,
                        dlc_rootfs_hostlog[self._dlc_util._SAMPLE_DLC_ID])
                # Verify the DLC was successfully installed.
                self._dlc_util.remove_preloaded(self._dlc_util._SAMPLE_DLC_ID)
                self._dlc_util.install(self._dlc_util._SAMPLE_DLC_ID,
                                       omaha_url='fake_url')
                if not self._dlc_util.is_installed(
                        self._dlc_util._SAMPLE_DLC_ID):
                    raise error.TestFail('Test DLC was not installed.')

            # Verify booting into the MiniOS.
            logging.info("Booting into MiniOS")
            self._boot_minios()
        else:
            # Expecting no update happened.
            # Verify the MiniOS priority unchanged.
            kernel_utils.verify_minios_priority_after_update(
                    self._host, expected=active_minios)
            # Verify the Platform (OS) boot expectation unchanged.
            kernel_utils.verify_boot_expectations(active_cros, host=self._host)
