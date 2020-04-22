# Copyright 2018 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from autotest_lib.client.common_lib import error
from autotest_lib.client.common_lib.cros import chrome
from autotest_lib.client.cros.update_engine import update_engine_test

class autoupdate_LoginStartUpdateLogout(update_engine_test.UpdateEngineTest):
    """
    Logs in, starts an update, waits for a while, then logs out.

    This test is used as part of the server test autoupdate_Interruptions.

    """
    version = 1

    def run_once(self, update_url, progress_to_complete, full_payload=True,
                 interrupt_network=False):
        """
        Login, start an update, wait for the update progress to reach the
        given progress, and logout. If specified, this test will also
        disconnect the internet upon reaching the target update progress,
        wait a while, and reconnect the internet before logging out.

        @param update_url: The omaha url to call.
        @param progress_to_complete: The update progress to wait for before
                                     logging out. If interrupt_network is
                                     True, the internet will be disconnected
                                     when the update reaches this progress.
                                     This should be a number between 0 and 1.
        @param full_payload: True for a full payload. False for delta.
        @param interrupt_network: True to cause a network interruption when
                                  update progress reaches
                                  progress_to_complete. False to logout
                                  normally after reaching that progress.

        """
        # Login as regular user. Start an update. Then Logout
        with chrome.Chrome(logged_in=True):
            self._check_for_update(update_url, critical_update=True,
                                   full_payload=full_payload)
            if interrupt_network:
                self._wait_for_progress(progress_to_complete)
                completed = self._get_update_progress()
                self._disconnect_reconnect_network_test(update_url)

                if self._is_update_engine_idle():
                    raise error.TestFail(
                        'The update was IDLE after interrupt.')
                if not self._update_continued_where_it_left_off(completed):
                    raise error.TestFail('The update did not continue where '
                                         'it left off after interruption.')
            else:
                self._wait_for_progress(progress_to_complete)
