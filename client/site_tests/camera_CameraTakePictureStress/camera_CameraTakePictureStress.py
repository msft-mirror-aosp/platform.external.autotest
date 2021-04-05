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


class camera_CameraTakePictureStress(power_test.power_Test):
    """Take pictures for long duration"""
    version = 1
    _IMAGE_LOCATION = '/home/chronos/user/MyFiles/Camera'
    # Timeout delay in seconds for capturing the image
    _CAPTURE_DELAY = 3

    # Names
    _CAMERA_APP_NAME = 'camera'
    _TAKE_PICTURE = '/^take photo/i'
    _CAMERA_MIRROR = '/^Mirroring$/i'

    # Roles
    _BUTTON = 'button'
    _CHECK_BOX = 'checkBox'

    # Threshold image count to clear the images after specific count
    THRESHOLD_IMAGE_COUNT = 10

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
        super(camera_CameraTakePictureStress, self).cleanup()

    def initialize_test(self):
        """Initializes the test and launches the Camera app"""
        self.success = False
        self.snaps_not_saved = 0
        self.previous_image_count = 0
        extra_browser_args = self.get_extra_browser_args_for_camera_test()
        self.cr = chrome.Chrome(autotest_ext=True, disable_default_apps=False,
                                extra_browser_args=extra_browser_args)
        self.ui = ui_utils.UI_Handler()
        self.ui.start_ui_root(self.cr)
        logging.info("Deleting all files in %s directory" % self._IMAGE_LOCATION)
        utils.system('rm -rf %s' % os.path.join(self._IMAGE_LOCATION,'*'))
        self.app = facade_resource.Application(self.cr)
        self.app.launch_app(self._CAMERA_APP_NAME)
        self.ui.wait_for_ui_obj(self._CAMERA_MIRROR, isRegex=True,
                           role=self._CHECK_BOX)

    def verify_captured_image(self, snap):
        """ Check the camera image location if the newly captured image is
        getting saved or not

        @param snap: image number which is going to be captured
        """
        def isdir():
            return os.path.isdir(self._IMAGE_LOCATION)

        # The image location will be created only when the first image is saved
        utils.poll_for_condition(condition=isdir, timeout=self._CAPTURE_DELAY)

        # Once the image is captured, verify whether the image got saved
        # in the image location
        def check_image_location():
            current_image_count = len(os.listdir(self._IMAGE_LOCATION))
            if current_image_count <= self.previous_image_count:
                return False
            else:
                return True
        try:
            utils.poll_for_condition(condition=check_image_location,
                    desc="photo %d is not saved" % snap,
                    timeout=self._CAPTURE_DELAY)
        except Exception as e:
            logging.warning(e)
            self.snaps_not_saved += 1

    def take_pictures(self, snap):
        """
        This function helps in capturing the snaps using camera app
        and helps in verifying if the captured snap got saved or not

        @param snap: image number which is going to be captured
        """
        # The new image location "/home/chronos/user/MyFiles/Camera" will get
        # created only when the first image is saved. Hence we are skipping
        # this step of listing the count of files present in the image location
        # for the first image
        if snap != 1:
            self.previous_image_count = len(os.listdir(self._IMAGE_LOCATION))
            logging.info("Previous image count: %d", self.previous_image_count)

        logging.info("Taking picture %d", snap)
        self.app.click_on(self.ui, self._TAKE_PICTURE, isRegex=True,
                          role=self._BUTTON)
        self.verify_captured_image(snap)

    def run_once(self, snaps=1):
        self.initialize_test()
        self.start_measurements()

        for snap in range(1, snaps + 1):
            # Removing images per every 10 captured images to get rid of Out
            # of Memory issue
            if not (snap % self.THRESHOLD_IMAGE_COUNT):
                utils.system('rm -rf %s' % os.path.join(self._IMAGE_LOCATION,
                                                        '*'))
            self.take_pictures(snap)

        # Check if any image(s) were not saved during this stress testing
        if self.snaps_not_saved != 0:
            raise error.TestFail("%d image(s) failed to save during execution"
                                  % self.snaps_not_saved)
        self.success = True
