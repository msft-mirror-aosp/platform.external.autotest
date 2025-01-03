# Copyright 2022 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import logging

from autotest_lib.client.common_lib.cros import kernel_utils
from autotest_lib.client.common_lib import error
from autotest_lib.server.cros.minios import minios_test
from autotest_lib.client.common_lib.cros.network import ping_runner


class nbr_EndToEndTest(minios_test.MiniOsTest):
    """Test network based recovery of a DUT."""
    version = 1
    _TEST_USERNAME = 'test@chromium.org'
    _UI_UPSTART_JOB_NAME = 'ui'
    _KERNEL_B_PARTITION = 4
    _RESOLVE_HOST_NAME = "google.com"

    def _verify_installed_build(self, build):
        """
        Verify that the build on the DUT is the build we expect.

        @param build: Expected build.

        """
        installed_build = self._get_release_builder_path()
        if installed_build != build:
            raise error.TestFail(
                    'Unexpected build installed, expected=%s, actual=%s.' %
                    (build, installed_build))

    def _mark_kernel_bootable(self, partition):
        """
        Helper function to mark the given kernel slot as priority and set the
        success flag.

        @param partition: The kernel partition we want to set as priority.

        """
        rootdev = self._host.run_output(['rootdev', '-s', '-d']).strip()
        self._host.run(['cgpt', 'add', '-i%s' % partition, '-S1', rootdev])
        self._host.run(['cgpt', 'prioritize', '-i%s' % partition, rootdev])

    def cleanup(self):
        active, inactive = kernel_utils.get_kernel_state(self._host)
        if self._n2m and active == kernel_utils._KERNEL_A and not self._is_running_minios(
        ):
            self._mark_kernel_bootable(self._KERNEL_B_PARTITION)
            self._host.reboot()
            kernel_utils.verify_boot_expectations(expected_kernel=inactive,
                                                  host=self._host)
        try:
            self._verify_installed_build(self._n_build)
        except Exception as e:
            raise
        finally:
            self._build = self._get_release_builder_path()
            super(nbr_EndToEndTest, self).cleanup()

    def run_once(self, build=None, n2m=True):
        """
        Validates the network based recovery flow.

        @param build: An optional parameter to specify the target build for the
            update when running locally. job_repo_url will override this value.
        @param n2m: Perform recovery from ToT to current stable version.

        """
        # Configure and get the network credentials to use for recovery.
        network_name, network_password = self._configure_network_for_test()
        self._n2m = n2m
        self._n_build = self._build

        if self._n2m:
            active, inactive = kernel_utils.get_kernel_state(self._host)
            # MiniOS recovers Slot A. Copy Slot A of kernel and root to Slot B
            # so we have a clean copy to boot to after test completion.
            if active == kernel_utils._KERNEL_A:
                kernel_utils.copy_kernel(self._host)
            build = self._get_serving_stable_build(release_archive_path=False)
            logging.debug('stable build name is %s', build)

        payload_url = self.get_payload_for_nebraska(
                build=build,
                full_payload=True,
                public_bucket=self._use_public_bucket)
        target_build = self._build

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

        ping_helper = ping_runner.PingRunner(host=self._host)
        ping_config = ping_runner.PingConfig(self._RESOLVE_HOST_NAME,
                                             count=5,
                                             interval=1,
                                             ignore_status=False,
                                             ignore_result=False)
        ping_helper.ping(ping_config)

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
        # Ensure that the installed build is what we expect.
        self._verify_installed_build(target_build)
        # Verify the update engine events that happened during the recovery.
        self.verify_update_events(self._RECOVERY_VERSION, minios_hostlog)
        # Verify device is no longer owned.
        self._verify_device_ownership(False)
        logging.info('Verification complete.')
