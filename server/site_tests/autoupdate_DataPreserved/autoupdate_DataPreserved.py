# Lint as: python2, python3
# Copyright 2018 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from autotest_lib.server.cros.update_engine import update_engine_test


class autoupdate_DataPreserved(update_engine_test.UpdateEngineTest):
    """Ensure user data and preferences are preserved during an update."""

    version = 1
    _USER_DATA_TEST = 'autoupdate_UserData'


    def cleanup(self):
        self._save_extra_update_engine_logs(number_of_logs=2)
        super(autoupdate_DataPreserved, self).cleanup()


    def run_once(self, full_payload=True, running_at_desk=False, build=None):
        """
        Tests that users timezone, input methods, and downloads are preserved
        during an update.

        @param full_payload: True for a full payload. False for delta.
        @param running_at_desk: Indicates test is run locally on a DUT which is
                                not in the lab network.
        @param build: An optional parameter to specify the target build for the
                      update when running locally. If no build is supplied, the
                      current version on the DUT will be used. In the lab, the
                      job_repo_url from the host attributes will override this.

        """
        # Get payload for the update to ToT.
        payload_url = self.get_payload_for_nebraska(
                build=build,
                full_payload=full_payload,
                public_bucket=running_at_desk)

        # Provision latest stable build for the current board.
        self.provision_dut(public_bucket=running_at_desk)

        # Change input method and timezone, create a file, then start update.
        self._run_client_test_and_check_result(self._USER_DATA_TEST,
                                               payload_url=payload_url,
                                               tag='before_update')
        self._host.reboot()

        # Ensure preferences and downloads are the same as before the update.
        self._run_client_test_and_check_result(self._USER_DATA_TEST,
                                               tag='after_update')
