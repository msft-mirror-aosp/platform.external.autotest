# Copyright 2022 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import logging

from autotest_lib.client.common_lib.cros import kernel_utils
from autotest_lib.server.cros.minios import minios_test


class nbr_EndToEndTest(minios_test.MiniOsTest):
    """Test network based recovery of a DUT."""
    version = 1
    _TEST_USERNAME = 'test@chromium.org'
    _UI_UPSTART_JOB_NAME = 'ui'

    def run_once(self,
                 build=None,
                 n2m=True):
        """
        Validates the network based recovery flow.

        @param build: An optional parameter to specify the target build for the
            update when running locally. job_repo_url will override this value.
        @param n2m: Perform recovery from ToT to current stable version.

        """
        # Configure and get the network credentials to use for recovery.
        network_name, network_password = self._configure_network_for_test()

        if n2m:
            build = self._get_serving_stable_build(
                    release_archive_path=False)
            logging.debug('stable build name is %s', build)

        payload_url = self.get_payload_for_nebraska(
                build=build,
                full_payload=True,
                public_bucket=self._use_public_bucket)

        logging.info('Performing recovery with payload url: %s', payload_url)

        # Wifi setup stops UI task, but UI service is required for login and
        # device ownership tests. Restart UI and wait before proceeding.
        if self._wifi_configs is not None:
            self._host.upstart_restart(self._UI_UPSTART_JOB_NAME)
            self._host.wait_for_service(self._UI_UPSTART_JOB_NAME)

        # Login and verify that the device is now owned.
        self._run_client_test_and_check_result(
                self._LOGIN_TEST,
                username=self._TEST_USERNAME,
                password=self._LOGIN_TEST_PASSWORD,
                dont_override_profile=True,
                session_start_timeout=30)
        self._verify_device_ownership(True)

        logging.info("Booting into MiniOS")
        self._boot_minios()

        # Install testing dependencies into MiniOS.
        logging.info("Successfully booted into MiniOS.")
        self._install_test_dependencies(public_bucket=self._use_public_bucket)

        old_boot_id = self._host.get_boot_id()
        self._start_nebraska(payload_url=payload_url)
        cmd = [
                self._MINIOS_CLIENT_CMD, '--start_recovery',
                f'--network_name={network_name}', '--watch'
        ]
        if network_password:
            cmd += [f'--network_password={network_password}']
        logging.info(f'Performing network based recovery with cmd: {cmd}.')
        self._run(cmd)
        logging.info('Recovery complete. Grabbing logs.')
        self._minios_cleanup()

        # Generate host log.
        minios_hostlog = self._create_minios_hostlog()
        self._verify_reboot(old_boot_id)

        # NBR always recovers into partition A.
        kernel_utils.verify_boot_expectations(kernel_utils._KERNEL_A,
                                              host=self._host)
        # Verify the update engine events that happened during the recovery.
        self.verify_update_events(self._RECOVERY_VERSION, minios_hostlog)
        # Verify device is no longer owned.
        self._verify_device_ownership(False)
        logging.info('Verification complete.')
