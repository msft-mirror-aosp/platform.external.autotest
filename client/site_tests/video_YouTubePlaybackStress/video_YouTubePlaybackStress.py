# Copyright 2021 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import logging
import time
import os

from autotest_lib.client.bin import utils
from autotest_lib.client.common_lib import error
from autotest_lib.client.common_lib.cros import chrome
from autotest_lib.client.cros.audio import alsa_utils
from autotest_lib.client.cros.audio import cras_utils
from autotest_lib.client.cros.graphics import graphics_utils
from autotest_lib.client.cros.power import power_test
from autotest_lib.client.cros.video import helper_logger

URL = "https://www.youtube.com/watch?v=zqLEO5tIuYs"


class video_YouTubePlaybackStress(power_test.power_Test):
    version = 1

    PLAYING_STATE = 'playing'
    # Time in seconds to sample for frame drops
    _SAMPLE_TIME = 10
    DROPPED_FRAMES_PERCENT_THRESHOLD = 10

    def cleanup(self):
        if not self.success:
            graphics_utils.take_screenshot(os.path.join(self.debugdir),
                                           'chrome')
        if self.cr:
            self.cr.close()
        super(video_YouTubePlaybackStress, self).cleanup()

    def initialize_test(self, player_page):
        """Initializes the test.

        @param player_page: The URL (string) of the YouTube player page to test.

        """
        self.tab = self.cr.browser.tabs[0]

        self.tab.Navigate(player_page)
        self.tab.WaitForDocumentReadyStateToBeComplete()

        utils.poll_for_condition(
            condition=self.player_is_ready,
            exception=error.TestError('Failed to load the Youtube player'))

        with open(
                os.path.join(os.path.dirname(__file__),
                'files/video_YouTubePageCommon.js')) as f:
            js = f.read()
            if not self.tab.EvaluateJavaScript(js):
                raise error.TestError('YouTube page failed to load.')
            logging.info('Loaded accompanying .js script.')

    def player_is_ready(self):
        """Simple wrapper to check if the player is ready

        @returns: Returns whether the player is ready."""
        return self.tab.EvaluateJavaScript('typeof player != "undefined"')

    def get_player_state(self):
        """Simple wrapper to get the JS player state.

        @returns: The state of the player (string).

        """
        return self.tab.EvaluateJavaScript('window.__getVideoState();')

    def get_current_time(self):
        """
        Simple wrapper to get the JS player current time

        @returns: Returns current time.
        """
        return self.tab.EvaluateJavaScript('window.__getCurrentTime();')

    def get_frames_statistics(self):
        """Simple wrapper to get a dictionary of raw video frame states

        @returns: Dict of droppedFrameCount (int), decodedFrameCount (int), and
                  droppedFramesPercentage (float).

        """
        return self.tab.EvaluateJavaScript('window.__getFramesStatistics();')

    def get_dropped_frames_percentage(self):
        """Simple wrapper to get the percentage of dropped frames.

        @returns: Drop frame percentage (float).

        """
        return self.get_frames_statistics()['droppedFramesPercentage']

    def perform_frame_drop_test(self):
        """Test to check if there are too many dropped frames.

        """
        utils.poll_for_condition(
            condition=lambda: self.get_player_state() == self.PLAYING_STATE,
            exception=error.TestError('Current player state is %s. Expected '
                                      'player state is %s' % (
                                      self.get_player_state(),
                                      self.PLAYING_STATE)))
        old_time = self.get_current_time()
        utils.poll_for_condition(
            condition=lambda: self.get_current_time() > old_time,
            exception=error.TestError('Video is not played until timeout'))
        dropped_frames_percentage = self.get_dropped_frames_percentage()
        if dropped_frames_percentage > self.DROPPED_FRAMES_PERCENT_THRESHOLD:
            raise error.TestError(
                    'perform_frame_drop_test failed due to too many dropped '
                    'frames (%f%%)' % (dropped_frames_percentage))

    @helper_logger.video_log_wrapper
    def run_once(self, test_duration=10,
                 output_node="INTERNAL_SPEAKER"):
        self.cr = chrome.Chrome(
            extra_browser_args=helper_logger.chrome_vmodule_flag())
        self.initialize_test(URL)
        device_name = cras_utils.get_selected_output_device_name()
        device_type = cras_utils.get_selected_output_device_type()
        self.start_measurements()
        start_time = time.time()
        logging.info("Playing and verifying youtube audio")
        while (time.time() - start_time) <= test_duration:
            logging.info("Peform framedrop test")
            self.perform_frame_drop_test()
            alsa_utils.check_audio_stream_at_selected_device(device_name,
                                                             device_type)
            time.sleep(self._SAMPLE_TIME)
