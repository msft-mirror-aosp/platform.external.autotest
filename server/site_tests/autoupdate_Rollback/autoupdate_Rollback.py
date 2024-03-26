# Lint as: python2, python3
# Copyright 2013 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import logging
import os
import time

from autotest_lib.client.common_lib import error
from autotest_lib.client.common_lib import utils
from autotest_lib.client.common_lib.cros import kernel_utils
from autotest_lib.server.cros.update_engine import update_engine_test

POWERWASH_COMMAND = 'safe fast keepimg'
POWERWASH_MARKER_FILE = '/mnt/stateful_partition/factory_install_reset'
STATEFUL_MARKER_FILE = '/mnt/stateful_partition/autoupdate_Rollback_flag'

class autoupdate_Rollback(update_engine_test.UpdateEngineTest):
    """Test that updates the machine and performs rollback."""
    version = 1

    def _powerwash(self):
        """Powerwashes DUT."""
        logging.info('Powerwashing device before rollback.')
        self._host.run(['echo', 'car', '>', STATEFUL_MARKER_FILE])
        self._host.run(['echo', "'%s'" % POWERWASH_COMMAND, '>',
                        POWERWASH_MARKER_FILE])
        self._host.reboot()

        marker = self._host.run(['test', '-e', STATEFUL_MARKER_FILE],
                                ignore_status=True, ignore_timeout=True)
        if marker is None or marker.exit_status == 0:
            raise error.TestFail("Powerwash cycle didn't remove the marker "
                                 "file on the stateful partition.")

        # Post powerwashing, we MUST wait for the current boot to be marked
        # as the higher priority again. Otherwise, we will be racing with the
        # asynchronous task of marking the currently updated partition as
        # successful post invocation of a rollback.
        # However, simply check for the higher priority as well as success per
        # kernel boot priority will not work because the currently booted kernel
        # is already the highest priority.
        # Reason for 90 seconds is 150% of actual platform delay in the updater.
        time.sleep(90)


    def cleanup(self):
        """Clean up test state."""
        # Save update_engine logs for the update, rollback, and post-reboot.
        self._save_extra_update_engine_logs(number_of_logs=3)

        # Delete rollback-version and rollback-happened pref which are
        # generated during Rollback and Enterprise Rollback.
        # rollback-version is written when update_engine Rollback D-Bus API is
        # called. The existence of rollback-version prevents update_engine to
        # apply payload whose version is the same as rollback-version.
        # rollback-happened is written when update_engine finished Enterprise
        # Rollback operation.
        preserved_prefs_path = ('/mnt/stateful_partition/unencrypted/preserve'
                                '/update_engine/prefs/')
        self._host.run(
            ['rm', os.path.join(preserved_prefs_path, 'rollback-version'),
             os.path.join(preserved_prefs_path, 'rollback-happened')],
            ignore_status=True)
        # Restart update-engine to pick up new prefs.
        self._restart_update_engine(ignore_status=True)
        super(autoupdate_Rollback, self).cleanup()


    def run_once(self,
                 powerwash_before_rollback=False,
                 running_at_desk=False,
                 build=None):
        """Runs the test.

        @param powerwash_before_rollback: True if we should rollback before
                                          powerwashing.
        @param running_at_desk: True if the test is being run locally.
        @param build: An optional parameter to specify the target build for the
                      update when running locally. If no build is supplied, the
                      current version on the DUT will be used.

        @raise error.TestError if anything went wrong with setting up the test;
               error.TestFail if any part of the test has failed.

        """
        payload_url = self.get_payload_for_nebraska(
                build=build, public_bucket=running_at_desk)
        active, inactive = kernel_utils.get_kernel_state(self._host)
        logging.info('Initial device state: active kernel %s, '
                     'inactive kernel %s.', active, inactive)

        logging.info('Performing an update.')
        self._run_client_test_and_check_result('autoupdate_CannedOmahaUpdate',
                                               payload_url=payload_url)
        self._host.reboot()
        # Ensure the update completed successfully.
        rootfs_hostlog, _ = self._create_hostlog_files()
        self.verify_update_events(self._FORCED_UPDATE, rootfs_hostlog)
        # We should be booting from the new partition.
        error_msg = 'Failed to set up test by updating DUT.'
        kernel_utils.verify_boot_expectations(inactive, error_msg, self._host)

        if powerwash_before_rollback:
            # Restore the stateful partition after the test to ensure the DUT
            # can be used by subsequent tests.
            self._should_restore_stateful = True
            self._powerwash()

        logging.info('Update verified, initiating rollback.')
        # Powerwash is tested separately from rollback.
        # Wait for update_engine to be idle before initiating a rollback,
        # since other operations such as DLC installations could still be
        # happening.
        utils.poll_for_condition(condition=self._is_update_engine_idle,
                                 timeout=300,
                                 desc='Waiting for update engine idle')
        self._rollback(powerwash=False)
        self._host.reboot()

        # We should be back on our initial partition.
        error_msg = ('Autoupdate reported that rollback succeeded but we '
                         'did not boot into the correct partition.')
        kernel_utils.verify_boot_expectations(active, error_msg, self._host)
        logging.info('We successfully rolled back to initial kernel.')
