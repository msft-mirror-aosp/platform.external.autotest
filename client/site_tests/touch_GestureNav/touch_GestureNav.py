# Lint as: python2, python3
# Copyright 2018 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import os
import logging

from autotest_lib.client.bin import utils
from autotest_lib.client.common_lib import error
from autotest_lib.client.common_lib.cros import chrome
from autotest_lib.client.cros import touch_playback_test_base


class touch_GestureNav(touch_playback_test_base.touch_playback_test_base):
    """Test to verify the three finger tab switching touchpad gesture."""
    version = 1

    _WAIT_FOR_COMPLETE_NAV = 5
    _PAGE_BACK = 'test_page_back.html'
    _PAGE_FWD = 'test_page_fwd.html'

    def _is_testable(self):
        """Returns True if the test can run on this device, else False."""
        if not self._has_touchpad:
            raise error.TestError('No touchpad found on this device!')

        # Check if playback files are available on DUT to run test.
        self._filepaths = self._find_test_files_from_directions('touchpad',
                'two-finger-longswipe-%s', ['back', 'fwd'])
        if not self._filepaths:
            logging.info('Missing gesture files. Aborting test.')
            return False

        return True


    def _check_tab_navigate(self, to_url, direction=''):
        """
        Verify tab navigation behavior. Moving two fingers one or
        another direction will navigate back or forward in the tab.

        @param direction: the swipe direction and the input file suffix.
        @param to_url: url to verify the swipe navigated to.

        """
        self.tab.WaitForDocumentReadyStateToBeComplete()
        fail_msg = 'Incorrect tab navigating %s to %s' % (direction, to_url)
        utils.poll_for_condition(
                lambda: self.tab.url.encode('utf8')
                    .decode().rstrip('/') == to_url,
                exception=error.TestFail(fail_msg),
                timeout=self._WAIT_FOR_COMPLETE_NAV)

    def _get_navigate_url(self, file_name):
        """
        Copy source html page file to tmp folder and return navigation path.

        @param file_name: used to store the test html file names

        """
        source_file_path = os.path.join(self.bindir, file_name)
        cp_cmd = ('cp %s /tmp/%s' %(source_file_path, file_name))
        os.system(cp_cmd)
        navigate_url = ('file:///tmp/%s' %file_name)
        return navigate_url

    def run_once(self):
        """Entry point of this test."""
        if not self._is_testable():
            raise error.TestNAError('Missing input data for this board name.')

        # Log in and start test.
        with chrome.Chrome(autotest_ext=True,
                           init_network_controller=True,
                           # b/330347607: Enable PrivacySandboxSettings4
                           # to avoid the Privacy Sandbox settings page popup
                           # from being shown.
                           enable_features="PrivacySandboxSettings4") as cr:
            self.tab = cr.browser.tabs[0]

            url_back = self._get_navigate_url(self._PAGE_BACK)
            url_fwd = self._get_navigate_url(self._PAGE_FWD)

            # Navigate to two urls in the same tab
            self.tab.Navigate(url_back)
            self._check_tab_navigate(url_back)
            self.tab.Navigate(url_fwd)
            self._check_tab_navigate(url_fwd)

            # Swipe to navigate back
            self._blocking_playback(touch_type='touchpad',
                        filepath=self._filepaths['back'])
            self._check_tab_navigate(url_back, 'back')

            # Swipe to navigate forward
            self._blocking_playback(touch_type='touchpad',
                        filepath=self._filepaths['fwd'])
            self._check_tab_navigate(url_fwd, 'fwd')
