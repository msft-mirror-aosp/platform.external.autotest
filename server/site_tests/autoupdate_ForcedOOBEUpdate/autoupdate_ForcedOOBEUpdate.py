# Copyright 2017 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import logging
import random
import time

from autotest_lib.client.common_lib import error
from autotest_lib.client.common_lib.cros import tpm_utils
from autotest_lib.server.cros.update_engine import update_engine_test

class autoupdate_ForcedOOBEUpdate(update_engine_test.UpdateEngineTest):
    """Runs a forced autoupdate during OOBE."""
    version = 1


    def cleanup(self):
        self._host.run('rm %s' % self._CUSTOM_LSB_RELEASE, ignore_status=True)

        # Get the last two update_engine logs: before and after reboot.
        self._save_extra_update_engine_logs()
        self._change_cellular_setting_in_update_engine(False)

        # Cancel any update still in progress.
        if not self._is_update_engine_idle():
            logging.debug('Canceling the in-progress update.')
            self._host.run('restart update-engine')
        super(autoupdate_ForcedOOBEUpdate, self).cleanup()


    def _wait_for_oobe_update_to_complete(self):
        """Wait for the update that started to complete.

        Repeated check status of update. It should move from DOWNLOADING to
        FINALIZING to COMPLETE (then reboot) to IDLE.
        """
        timeout_minutes = 10
        timeout = time.time() + 60 * timeout_minutes
        boot_id = self._host.get_boot_id()
        seen_reboot = False

        while True:
            if not seen_reboot:
                try:
                    self._get_update_engine_status(timeout=10,
                                                   ignore_timeout=False)
                except error.AutoservRunError as e:
                    # Check if command timed out because update-engine was
                    # taking a while or if the command didn't even start.
                    query = 'Querying Update Engine status...'
                    if query not in e.result_obj.stderr:
                        # Command did not start. DUT rebooted at end of update.
                        self._host.test_wait_for_boot(boot_id)
                        seen_reboot = True
            else:
                # Now that the device is rebooted, we have to make sure the
                # update_engine is up and running and new update check has been
                # perfromed.
                try:
                    self._get_update_engine_status(timeout=10,
                                                   ignore_timeout=False)
                    self._check_update_engine_log_for_entry(
                        "Omaha request response:")
                    break;
                except (error.TestFail, error.AutoservRunError):
                    pass

            time.sleep(1)
            if time.time() > timeout:
                raise error.TestFail('OOBE update did not finish in %d '
                                     'minutes.' % timeout_minutes)


    def run_once(self, full_payload=True, cellular=False,
                 interrupt=None, job_repo_url=None, moblab=False):
        """
        Runs a forced autoupdate during ChromeOS OOBE.

        @param full_payload: True for a full payload. False for delta.
        @param cellular: True to do the update over a cellualar connection.
                         Requires that the DUT have a sim card slot.
        @param interrupt: Type of interrupt to try: [reboot, network, suspend]
        @param job_repo_url: Used for debugging locally. This is used to figure
                             out the current build and the devserver to use.
                             The test will read this from a host argument
                             when run in the lab.
        @param moblab: True if we are running on moblab.

        """
        # veyron_rialto is a medical device with a different OOBE that auto
        # completes so this test is not valid on that device.
        if 'veyron_rialto' in self._host.get_board():
            raise error.TestNAError('Rialto has a custom OOBE. Skipping test.')

        tpm_utils.ClearTPMOwnerRequest(self._host)
        update_url = self.get_update_url_for_test(job_repo_url,
                                                  full_payload=full_payload,
                                                  public=cellular,
                                                  moblab=moblab)
        before = self._get_chromeos_version()
        payload_info = None
        if cellular:
            self._change_cellular_setting_in_update_engine(True)

        progress = None
        if interrupt is not None:
            # Choose a random downloaded progress to interrupt the update.
            # Moblab may have higher download speeds and take longer to return
            # from the client test, so we'll use a reduced progress range if
            # we're interrupting the update on moblab.
            progress_limit = 0.3 if moblab else 0.6
            progress = random.uniform(0.1, progress_limit)
            logging.info('Progress when we will interrupt: %f', progress)

        # Call client test to start the forced OOBE update.
        self._run_client_test_and_check_result(
            'autoupdate_StartOOBEUpdate', image_url=update_url,
            full_payload=full_payload, cellular=cellular,
            critical_update=True, interrupt_network=interrupt is 'network',
            interrupt_progress=progress)

        if interrupt in ['reboot', 'suspend']:
            logging.info('Waiting to interrupt update.')
            self._wait_for_progress(progress)
            logging.info('We will now start interrupting the update.')
            self._take_screenshot('before_interrupt.png')
            completed = self._get_update_progress()

            if interrupt is 'reboot':
                self._host.reboot()
            elif interrupt is 'suspend':
                self._suspend_then_resume()
            # Screenshot to check that OOBE was not skipped by interruption.
            self._take_screenshot('after_interrupt.png')

            if self._is_update_engine_idle():
                raise error.TestFail('The update was IDLE after interrupt.')
            if not self._update_continued_where_it_left_off(completed):
                raise error.TestFail('The update did not continue where it '
                                     'left off after interruption.')
        elif interrupt not in ['network', None]:
            raise error.TestFail('Unknown interrupt type: %s' % interrupt)

        # We create a new lsb-release file with no_update=True so there won't be
        # any more actual updates happen.
        self._create_custom_lsb_release(update_url, no_update=True)

        self._wait_for_oobe_update_to_complete()

        # Verify that the update completed successfully by checking hostlog.
        rootfs_hostlog, reboot_hostlog = self._create_hostlog_files()
        self.verify_update_events(self._CUSTOM_LSB_VERSION, rootfs_hostlog)
        self.verify_update_events(self._CUSTOM_LSB_VERSION, reboot_hostlog,
                                  self._CUSTOM_LSB_VERSION)

        after = self._get_chromeos_version()
        logging.info('Successfully force updated from %s to %s.', before, after)
