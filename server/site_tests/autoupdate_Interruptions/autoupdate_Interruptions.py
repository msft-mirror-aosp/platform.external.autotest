# Copyright 2018 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import logging
import os
import random

from autotest_lib.client.common_lib import error
from autotest_lib.client.common_lib import utils
from autotest_lib.client.common_lib.cros import kernel_utils
from autotest_lib.server.cros.update_engine import update_engine_test

class autoupdate_Interruptions(update_engine_test.UpdateEngineTest):
    """Ensures an update completes with multiple user interruptions."""
    version = 1

    def cleanup(self):
        self._save_extra_update_engine_logs(number_of_logs=2)
        super(autoupdate_Interruptions, self).cleanup()


    def run_once(self, full_payload=True, interrupt=None, job_repo_url=None):
        """
        Runs an update with interruptions from the user.

        @param full_payload: True for a full payload. False for delta.
        @param interrupt: The interrupt to perform: [reboot, network, suspend].
        @param job_repo_url: Used for debugging locally. This is used to figure
                             out the current build and the devserver to use.
                             The test will read this from a host argument
                             when run in the lab.

        """
        # Clear any previously started updates.
        pref_file = os.path.join(self._UPDATE_ENGINE_PREFS_DIR,
                                 self._UPDATE_CHECK_RESPONSE_HASH)
        self._host.run(['rm', pref_file], ignore_status=True)
        self._restart_update_engine(ignore_status=True)

        update_url = self.get_update_url_for_test(job_repo_url,
                                                  full_payload=full_payload)
        chromeos_version = self._get_chromeos_version()
        active, inactive = kernel_utils.get_kernel_state(self._host)
        # Choose a random downloaded progress to interrupt the update.
        progress = random.uniform(0.1, 0.6)
        logging.info('Progress when we will begin interruptions: %f', progress)

        # Login, start the update, logout
        self._run_client_test_and_check_result(
            'autoupdate_LoginStartUpdateLogout', update_url=update_url,
            progress_to_complete=progress,
            full_payload=full_payload,
            interrupt_network=interrupt is 'network')

        if interrupt in ['reboot', 'suspend']:
            if self._is_update_finished_downloading():
                raise error.TestFail(
                    'Update finished before %s interrupt started. Interrupt '
                    'was supposed to be at %f' % (interrupt, progress))
            self._wait_for_progress(progress)
            completed = self._get_update_progress()
            if interrupt is 'reboot':
                self._host.reboot()
                utils.poll_for_condition(self._get_update_engine_status,
                                         desc='update engine to start')
                self._check_for_update(update_url, critical_update=True,
                                       full_payload=full_payload)
            elif interrupt is 'suspend':
                self._suspend_then_resume()

            if self._is_update_engine_idle():
                raise error.TestFail(
                    'The update was IDLE after interrupt. Last error: %s' %
                    self._get_last_error_string())
            if not self._update_continued_where_it_left_off(
                completed, reboot_interrupt=interrupt is 'reboot'):
                raise error.TestFail('The update did not continue where it '
                                     'left off after interruption.')
        elif interrupt not in ['network', None]:
            raise error.TestFail('Unknown interrupt type: %s' % interrupt)

        # Add a new user and crash browser.
        self._run_client_test_and_check_result(
            'autoupdate_CrashBrowserAfterUpdate')

        # Update is complete. Reboot the device.
        self._host.reboot()
        utils.poll_for_condition(self._get_update_engine_status,
                                 desc='update engine to start')
        # We do check update with no_update=True so it doesn't start the update
        # again.
        self._check_for_update(update_url, no_update=True)

        # Verify that the update completed successfully by checking hostlog.
        rootfs_hostlog, reboot_hostlog = self._create_hostlog_files()
        self.verify_update_events(chromeos_version, rootfs_hostlog)
        self.verify_update_events(chromeos_version, reboot_hostlog,
                                  chromeos_version)
        kernel_utils.verify_boot_expectations(
            inactive,
            'The active image slot did not change after the update.',
            self._host)
