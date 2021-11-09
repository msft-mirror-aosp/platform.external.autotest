# Copyright (c) 2021 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import logging

from autotest_lib.client.common_lib import error
from autotest_lib.server.cros.faft.firmware_test import FirmwareTest


class firmware_MiniosMenu(FirmwareTest):
    """
    Servo based for MiniOS boot through the UI menu.

    This test requires the device to support MiniOS. This test will boot to the
    manual recovery screen and try to boot MiniOS through the UI menu.
    """
    version = 1

    def initialize(self, host, cmdline_args, older_version):
        super(firmware_MiniosMenu, self).initialize(host, cmdline_args)

        if not self.menu_switcher:
            raise error.TestNAError('Test skipped for menuless UI')
        if not self.faft_config.chrome_ec:
            raise error.TestNAError('Cannot check power state without EC')
        if not self.faft_config.minios_enabled:
            raise error.TestNAError('MiniOS is not enabled for this board')

        self.host = host
        # SSH to MiniOS is only available in developer mode
        self.switcher.setup_mode('dev')
        self.setup_usbkey(usbkey=False)
        self.older_version = older_version

    def cleanup(self):
        try:
            self.switcher.trigger_minios_to_dev()
        except Exception as e:
            logging.error('Caught exception: %s', str(e))
        super(firmware_MiniosMenu, self).cleanup()

    def run_once(self):
        """Run a single iteration of the test."""
        logging.info('Boot into recovery mode, older_version: %s',
                     self.older_version)
        self.switcher.enable_rec_mode_and_reboot(usb_state='host')
        self.wait_for('firmware_screen')
        self.menu_switcher.trigger_rec_to_minios(self.older_version)
        self.check_state(self.checkers.dev_boot_minios_checker)
