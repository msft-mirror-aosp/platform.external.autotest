# Lint as: python3
# Copyright 2023 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""firmware_GSCSetup test"""

import logging
import os

from autotest_lib.client.common_lib import error
from autotest_lib.client.common_lib.cros import cr50_utils
from autotest_lib.server.cros.faft.cr50_test import Cr50Test


class firmware_GSCSetup(Cr50Test):
    """Basic test to verify DUT is ready for FAFT GSC testing.

    This test checks the following FAFT GSC hardware requirements
    Universal:
      - Servo v4 connected
      - Cr50 console is accessible

    Servo Micro / C2D2:
      - EFI image is google storage
      - Dev image is google storage

    CCD:
      - Testlab mode is enabled
    """
    version = 1

    TMP_PATH = '/tmp/test.gsc.bin'

    def validate_image_devid(self, image):
        """Verify the image is signed with the right devid."""
        devid = self.gsc.get_devid()
        image_name = os.path.basename(image)
        logging.info('Check %s is signed with the devid %s', image_name, devid)
        dest = cr50_utils.InstallImage(self.host, image, self.TMP_PATH)[0]
        output = cr50_utils.GSCTool(self.host, ['-b', dest]).stdout
        if devid not in output:
            raise error.TestFail('Sign %s with the devid %s' %
                                 (image_name, devid))
        logging.info('%s is signed with the devid %s', image_name, devid)

    def validate_efi_image(self):
        """Verify the EFI image exists."""
        logging.info('Check EFI image exists on google storage')
        efi_image = self.download_cr50_eraseflashinfo_image()[0]
        self.validate_image_devid(efi_image)
        logging.info('EFI image ok')

    def validate_dbg_image(self):
        """Verify the DBG image exists and has an ok version."""
        logging.info('Check DBG image')
        dbg_image, dbg_version = self.download_cr50_debug_image()
        logging.info('Found DBG image with version %s', dbg_version)
        if dbg_version[1].startswith('0.'):
            raise error.TestFail('Sign DBG image with a epoch greater than 0')
        self.validate_image_devid(dbg_image)
        logging.info('DBG image ok')

    def check_flex_setup(self):
        """Verify testlab mode is enabled."""
        logging.info('Verify flex setup')
        self.validate_efi_image()
        self.validate_dbg_image()
        logging.info('flex setup is ok')

    def check_testlab_enabled(self):
        """Verify testlab mode is enabled."""
        logging.info('Check testlab mode')
        if not self.gsc.testlab_is_on():
            raise error.TestFail('Enable testlab mode for ccd setups')
        logging.info('Testlab mode enabled')

    def check_ccd_setup(self):
        """Verify testlab mode is enabled."""
        logging.info('Verify ccd setup')
        self.check_testlab_enabled()
        logging.info('ccd setup is ok')

    def run_once(self):
        """Main test logic"""

        logging.info('Check GSC console works')
        if not self.gsc:
            raise error.TestFail('GSC console does not work')
        logging.info('Check Servo V4 is connected')
        if 'servo_v4' not in self.servo.get_servo_version():
            raise error.TestFail('Run with servo v4')

        if self.servo.main_device_is_ccd():
            # Running with ccd_cr50 or ccd_gsc.
            self.check_ccd_setup()
        elif self.servo.main_device_is_flex():
            # Running with c2d2 or servo micro.
            self.check_flex_setup()
        else:
            raise error.TestFail('Use servo micro, c2d2, or ccd with servo v4')
