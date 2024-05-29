# Copyright 2018 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import logging

from autotest_lib.client.common_lib import error
from autotest_lib.client.common_lib.cros import cr50_utils
from autotest_lib.server.cros.faft.cr50_test import Cr50Test


class firmware_Cr50RejectUpdate(Cr50Test):
    """Verify cr50 rejects certain updates."""
    version = 1
    # Old version that exists for Cr50 and Ti50
    OLD_IMAGE_VER = '0.0.16'
    # No boards use the bid TEST. Use this image to verify cr50 rejects images
    # with the wrong board id.
    TEST_BID_TYPE = 'TEST:ffffffff:0'
    TEST_BID_FLAGS = 'TEST:0:000fffff'
    TEST_PATH = '/tmp/test_image.bin'
    WAIT_FOR_DUT_SSH_S = 40
    DELAY_SSH_CHECK_S = 5


    def initialize(self, host, cmdline_args, full_args):
        """Initialize servo and download images"""
        super(firmware_Cr50RejectUpdate, self).initialize(host, cmdline_args,
                full_args, restore_cr50_image=True)

        if not hasattr(self, 'gsc'):
            raise error.TestNAError('Test can only be run on devices with '
                                    'access to the GSC console')

        if 'DBG' in self.gsc.get_version():
            raise error.TestNAError('Update rules are wonky on DBG images')

        if cr50_utils.GetChipBoardId(host) == cr50_utils.ERASED_CHIP_BID:
            raise error.TestNAError('Set Cr50 board id to run test')

        # These images are unsigned. They should get rejected for their board
        # id.
        self.bid_type_path = self.download_cr50_debug_image('no_devid',
                self.TEST_BID_TYPE)[0]
        self.bid_flags_path = self.download_cr50_debug_image('no_devid',
                self.TEST_BID_FLAGS)[0]
        self.old_path = self.download_cr50_release_image(self.OLD_IMAGE_VER)[0]
        self.original_path = self.get_saved_cr50_original_path()
        self.host = host
        # Wait until cr50 can accept an update, so cr50 update rate limiting
        # won't interfere with the test.
        self.gsc.wait_until_update_is_allowed()


    def try_update(self, arg, path, err=0, stdout='', wait=True):
        """Run gsctool with the given image and args. Verify the result

        Args:
            arg: strings with the gsctool args
            path: local path to the test image
            err: The error number
            stdout: a string that must be included in the cmd stdout
            wait: Wait for cr50 to have been up for 60 seconds before attempting
                  the update.

        Raises:
            TestFail if there is an unexpected result.
        """
        # Copy the image to the DUT
        self.host.send_file(path, self.TEST_PATH)

        # Wait for cr50 to have been up for 60 seconds, so it won't
        # automatically reject the image.
        if wait:
            self.gsc.wait_until_update_is_allowed()

        # Try to update
        result = self.host.run('gsctool -a %s %s' % (arg, self.TEST_PATH),
                ignore_status=True, ignore_timeout=True, timeout=60)

        logging.info('Update %s result (exp %d): %s', path, err, result)
        # Check the result
        stderr = 'Error %d' % err
        if err and stderr not in result.stderr:
            raise error.TestFail('"%s" not in "%s"' % (stderr, result.stderr))
        if stdout and stdout not in result.stdout:
            raise error.TestFail('"%s" not in "%s"' % (stdout, result.stdout))


    def run_once(self):
        """Verify cr50 rejects certain updates"""
        # GSC rejects a mismatched board id no matter what
        # Verify the bid type check.
        self.try_update('-u', self.bid_type_path, err=12)
        self.try_update('', self.bid_type_path, err=12)
        bid_flag_err = 12 if self.gsc.NAME == 'cr50' else 13
        # Verify the bid flags check.
        self.try_update('-u', self.bid_flags_path, err=bid_flag_err)
        self.try_update('', self.bid_flags_path, err=bid_flag_err)

        # With the '-u' option cr50 rejects any images with old/same header
        # with 'nothing to do'
        self.try_update('-u', self.old_path, stdout='nothing to do')
        self.try_update('-u', self.original_path, stdout='nothing to do')

        # Without '-u' cr50 rejects old headers
        self.try_update('', self.old_path, err=8)

        # Cr50 will accept images with the same header version if -u is omitted.
        # original_path is the image already on cr50, so this won't have any
        # real effect. It will just reboot Cr50.
        self.try_update('', self.original_path, stdout='image updated')
