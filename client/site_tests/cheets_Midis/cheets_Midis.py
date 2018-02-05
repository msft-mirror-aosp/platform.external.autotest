# Copyright 2018 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import logging

from autotest_lib.client.common_lib import error
from autotest_lib.client.common_lib.cros import arc
from autotest_lib.client.common_lib.cros import chrome
from autotest_lib.client.bin import test
from autotest_lib.client.bin import utils
from autotest_lib.client.cros import cros_ui


# TODO(pmalani): Change this to actually talk to midis and make
# sure basic functionality works.
class cheets_Midis(test.test):
    """ Test to verify midis daemon starts correctly.

    A simple test which verifies whether:
    - midis starts up correctly on ARC container start-up.
    - midis restarts correctly on logging-out.
    """
    version = 1

    def _get_midis_pid(self):
        """ Get the midis daemon pid using pgrep. """
        cmd = 'pgrep midis'
        result = utils.run(cmd, ignore_status=True).stdout
        ret_val = -1;
        try:
            ret_val = int(result)
        except ValueError:
            logging.error('Error parsing pgrep result: %s', result)
        return ret_val

    def run_once(self):
        """ Restart Chrome with ARC and check that midis also restarts. """

        old_midis_pid = None
        session = None
        with chrome.Chrome(
            arc_mode=arc.arc_common.ARC_MODE_ENABLED,
            dont_override_profile=False) as cr:
            session = cros_ui.get_chrome_session_ident()
            old_midis_pid = self._get_midis_pid()

        if old_midis_pid == -1:
            raise error.TestFail('midis not running in Chrome OS.')

        cros_ui.wait_for_chrome_ready(session)
        new_midis_pid = self._get_midis_pid()
        if new_midis_pid == -1:
            raise error.TestFail('midis not running after Chrome shut down.')

        if new_midis_pid == old_midis_pid:
            raise error.TestFail('midis didn\'t restart.')
        logging.info('Restarted midis with pid %d.', new_midis_pid)
