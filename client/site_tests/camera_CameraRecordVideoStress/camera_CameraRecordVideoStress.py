# Copyright 2021 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import logging
import os
import time

from autotest_lib.client.bin import utils
from autotest_lib.client.common_lib import error
from autotest_lib.client.common_lib import ui_utils
from autotest_lib.client.common_lib.cros import chrome
from autotest_lib.client.cros.graphics import graphics_utils
from autotest_lib.client.cros.multimedia import facade_resource
from autotest_lib.client.cros.power import power_test


class camera_CameraRecordVideoStress(power_test.power_Test):
    """Record Videos for long duration"""
    version = 1
    _VIDEO_LOCATION = '/home/chronos/user/MyFiles/Camera'

    # Timeout delay  in seconds for recorded video to save
    _TIME_DELAY = 3

    # Record the video for 10 seconds
    _CAPTURE_DELAY = 10

    # Names
    _CAMERA_APP_NAME = 'camera'
    _CAMERA_MIRROR = '/^Mirroring$/i'
    _SWITCH_TO_RECORD_VIDEO = '/^Switch to record video$/i'
    _START_RECORDING = '/^Start recording$/i'
    _STOP_RECORDING = '/^Stop recording$/i'

    # Roles
    _BUTTON = 'button'
    _CHECK_BOX = 'checkBox'
    _RADIO_BUTTON = 'radioButton'

    # Threshold video count to clear the videos after specific count
    THRESHOLD_VIDEO_COUNT = 10

    def cleanup(self):
        if self.ui:
            logging.info(self.ui.get_name_role_list())
        if not self.success:
            graphics_utils.take_screenshot(os.path.join(self.debugdir),
                                           'chrome')
        if self.app:
            self.app.close_app(self._CAMERA_APP_NAME)
        if self.cr:
            self.cr.close()
        super(camera_CameraRecordVideoStress, self).cleanup()

    def initialize_test(self):
        """Initializes the test and launches the Camera app """
        self.success = False
        self.videos_not_saved = 0
        self.previous_video_count = 0
        extra_browser_args = self.get_extra_browser_args_for_camera_test()
        self.cr = chrome.Chrome(autotest_ext=True, disable_default_apps=False,
                                extra_browser_args=extra_browser_args)
        self.ui = ui_utils.UI_Handler()
        self.ui.start_ui_root(self.cr)
        logging.info("Deleting all files in %s directory" % self._VIDEO_LOCATION)
        utils.system('rm -rf %s' % os.path.join(self._VIDEO_LOCATION,'*'))
        self.app = facade_resource.Application(self.cr)
        self.app.launch_app(self._CAMERA_APP_NAME)
        self.ui.wait_for_ui_obj(self._CAMERA_MIRROR, isRegex=True,
                           role=self._CHECK_BOX)
        logging.info("Switching to video mode")
        self.app.click_on(self.ui, self._SWITCH_TO_RECORD_VIDEO, isRegex=True,
                      role=self._RADIO_BUTTON)
        self.ui.wait_for_ui_obj(self._START_RECORDING, isRegex=True,
                           role=self._BUTTON)

    def take_video(self, video):
        """
        This function helps in recording the videos using camera app
        and helps in verifying if the recorded video got saved or not

        @param video: video number which is going to be recorded

        The new camera location "/home/chronos/user/MyFiles/Camera" will get
        created only when the first video is saved. Hence we are skipping
        this step of listing the count of files present in the camera location
        for the first video

        """

        if video != 1:
            self.previous_video_count = len(os.listdir(self._VIDEO_LOCATION))
            logging.info("Previous video count: %d", self.previous_video_count)
        logging.info("Recording video %d", video)
        if self.ui.item_present(self._START_RECORDING, isRegex=True,
                           flip=True, role=self._BUTTON):
            raise error.TestFail("Camera is not on video mode")
        self.ui.click_and_wait_for_item_with_retries(
                item_to_click=self._START_RECORDING,
                item_to_wait_for=self._STOP_RECORDING, isRegex_click=True,
                isRegex_wait=True, click_role=self._BUTTON,
                wait_role=self._BUTTON)
        # Time delay for recording the video
        time.sleep(self._CAPTURE_DELAY)
        if self.ui.item_present(self._STOP_RECORDING, isRegex=True,
                           flip=True, role=self._BUTTON):
            raise error.TestFail("Video is not recording to stop it")
        self.app.click_on(self.ui, self._STOP_RECORDING, isRegex=True,
                          role=self._BUTTON)
        # Time delay for the recorded video to save
        time.sleep(self._TIME_DELAY)
        current_video_count = len(os.listdir(self._VIDEO_LOCATION))
        logging.info("Current video count: %d", current_video_count)
        if current_video_count <= self.previous_video_count:
            self.videos_not_saved += 1
            logging.info("video %d is not saved" % video)

    def run_once(self, videos=1):
        self.initialize_test()
        self.start_measurements()
        for video in range(1, videos + 1):
            # Removing video per every 10 recorded videos to get rid of Out
            # of Memory issue
            if not (video % self.THRESHOLD_VIDEO_COUNT):
                utils.system('rm -rf %s' % os.path.join(self._VIDEO_LOCATION,
                                                        '*'))
            self.take_video(video)

        # Check if any video(s) were not saved during this stress testing
        if self.videos_not_saved != 0:
            raise error.TestFail("%d video(s) failed to save during execution"
                                  % self.videos_not_saved)
        self.success = True
