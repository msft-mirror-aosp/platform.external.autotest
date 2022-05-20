# Copyright 2022 The ChromiumOS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import logging

from autotest_lib.client.common_lib.cros import kernel_utils
from autotest_lib.server.cros.minios import minios_test


class nbr_NetworkInterruptions(minios_test.MiniOsTest):
    """Test network based recovery of a DUT with network interruptions."""
    version = 1

    # The download percentage threshold beyond which we introduce interruptions.
    _DOWNLOAD_PROGRESS_THRESHOLD = 0.1

    # Period to interrupt download traffic in seconds.
    _TRANSIENT_TIMEOUT = 90

    def _perform_network_connection(self, network_name, network_password):
        """
        Connect to the provided network using MiniOS.

        @param network_name: The name of the network to connect to for recovery.
        @param network_password: Optional password for the network.

        """
        # Verify we are on welcome screen.
        self._validate_minios_state(self._MINIOS_STATE_IDLE)
        # Next screen should send you to the network selection screen.
        self._next_screen()
        self._validate_minios_state(self._MINIOS_STATE_NETWORK_SELECTION)
        self._set_network_credentials(network_name, network_password)
        # Select the provided network.
        self._next_screen()
        if network_password:
            # Handle optional password screen if password was provided.
            self._validate_minios_state(self._MINIOS_STATE_NETWORK_CREDENTIALS)
            self._next_screen()
        self._wait_for_minios_state(self._MINIOS_STATE_NETWORK_CONNECTED)

    def _perform_recovery_with_failed_network(self, network_name,
                                              network_password):
        """
        Perform MiniOS recovery with network failure during the download
        phase of the recovery process. Will reset and attempt recovery again
        after failure.

        @param network_name: The name of the network to connect to for recovery.
        @param network_password: Optional password for the network.

        """
        self._perform_network_connection(network_name, network_password)
        logging.info('Starting network based recovery.')
        self._next_screen()
        self._validate_minios_state(self._MINIOS_STATE_RECOVERING)
        self._wait_for_progress(self._DOWNLOAD_PROGRESS_THRESHOLD)
        logging.info('Interrupting network.')
        self._drop_download_traffic()
        self._wait_for_update_to_fail()
        self._validate_minios_state(self._MINIOS_STATE_ERROR)
        # Go back and attempt full recovery again.
        self._prev_screen()
        self._validate_minios_state(self._MINIOS_STATE_IDLE)
        logging.info('Restoring network.')
        self._restore_download_traffic()
        cmd = [
                self._MINIOS_CLIENT_CMD, '--start_recovery',
                f'--network_name={network_name}', '--watch'
        ]
        if network_password:
            cmd += [f'--network_password={network_password}']
        logging.info(f'Performing network based recovery with cmd: {cmd}.')
        self._run(cmd)

    def cleanup(self):
        """Clean up nbr_NetworkInterruptions autotests."""
        self._restore_download_traffic()
        super(nbr_NetworkInterruptions, self).cleanup()

    def run_once(self,
                 job_repo_url=None,
                 network_name=minios_test.MiniOsTest._ETHERNET_LABEL,
                 network_password=None,
                 running_at_desk=False):
        """
        Validates that the Network Based Recovery Flow is resilient to network
        interruptions.

        @param job_repo_url: A url pointing to the devserver where the autotest
            package for this build should be staged.
        @param network_name: The name of the network to connect to for recovery.
        @param network_password: Optional password for the network.
        @param running_at_desk: indicates test is run locally from a
            workstation.

        """
        self._use_public_bucket = running_at_desk
        logging.info('Performing recovery with update url: %s', job_repo_url)
        payload_url = self.get_payload_for_nebraska(
                job_repo_url, full_payload=True, public_bucket=running_at_desk)

        logging.info("Booting into MiniOS")
        self._boot_minios()

        # Install testing dependencies into MiniOS.
        logging.info("Successfully booted into MiniOS.")
        self._install_test_dependencies(public_bucket=running_at_desk)

        old_boot_id = self._host.get_boot_id()
        self._start_nebraska(payload_url=payload_url)
        self._perform_recovery_with_failed_network(network_name,
                                                   network_password)
        logging.info('Recovery complete. Grabbing logs.')

        # Generate host log.
        minios_hostlog = self._create_minios_hostlog()
        self._verify_reboot(old_boot_id)

        # NBR always recovers into partition A.
        kernel_utils.verify_boot_expectations(kernel_utils._KERNEL_A,
                                              host=self._host)
        # Verify the update engine events that happened during the recovery.
        self.verify_update_events(self._RECOVERY_VERSION, minios_hostlog)
        logging.info('Verification complete.')
