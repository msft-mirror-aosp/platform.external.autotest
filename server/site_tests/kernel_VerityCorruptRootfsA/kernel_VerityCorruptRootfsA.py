# Copyright 2022 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# TODO(b/290823172) Remove this file when the test is no longer in any
# PVS plan

import logging

from autotest_lib.server.cros.faft.firmware_test import FirmwareTest


class kernel_VerityCorruptRootfsA(FirmwareTest):
    """
    Servo based kernel A corruption test.

    This test corrupts kernel A and checks for kernel B on the next boot.
    It will fail if kernel verification mis-behaved.
    """
    version = 1

    def initialize(self, host, cmdline_args, dev_mode=False):
        super(kernel_VerityCorruptRootfsA, self).initialize(host, cmdline_args)
        self.switcher.setup_mode('dev' if dev_mode else 'normal')
        self.setup_usbkey(usbkey=False)
        self.setup_kernel('a')

    def cleanup(self):
        try:
            self.setup_kernel('a')
        except Exception as e:
            logging.error("Caught exception: %s", str(e))
        super(kernel_VerityCorruptRootfsA, self).cleanup()

    def run_once(self, dev_mode=False):
        """Runs a single iteration of the test."""
        logging.info("Corrupt rootfs A.")
        self.check_state((self.checkers.root_part_checker, 'a'))
        self.faft_client.rootfs.corrupt_rootfs_verity('a')
        self.switcher.mode_aware_reboot()

        logging.info("Expected kernel B boot and restore kernel A.")
        self.check_state((self.checkers.root_part_checker, 'b'))
        self.setup_kernel('a')
        self.switcher.mode_aware_reboot()

        logging.info("Expected kernel A boot.")
        self.check_state((self.checkers.root_part_checker, 'a'))
