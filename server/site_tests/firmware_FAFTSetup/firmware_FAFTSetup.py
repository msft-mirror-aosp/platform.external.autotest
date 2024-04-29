# Lint as: python3
# Copyright 2012 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""firmware_FAFTSetup test"""

import io
import logging

# pylint:disable=import-error
from autotest_lib.client.common_lib import error
from autotest_lib.server.cros.faft.firmware_test import FirmwareTest


class firmware_FAFTSetup(FirmwareTest):
    """Basic test to verify DUT is ready for FAFT testing.

    This test checks the following FAFT hardware requirement:
      - Warm reset
      - Cold reset
      - Recovery boot with USB stick
      - USB stick is plugged into Servo board, not DUT
      - Keyboard simulation
      - No terminal opened on EC console
    """
    version = 1
    NEEDS_SERVO_USB = True

    # Delay to ensure client is ready to read the key press.
    KEY_PRESS_DELAY = 2

    def console_checker(self):
        """Verify EC console is available if using Chrome EC."""
        if not self.check_ec_capability(suppress_warning=True):
            # Not Chrome EC. Nothing to check.
            return True
        try:
            if self.ec.get_version():
                return True
        except:  # pylint: disable=W0702
            pass

        logging.error("Cannot talk to EC console.")
        logging.error(
                "Please check there is no terminal opened on EC console.")
        raise error.TestFail("Failed EC console check.")

    def run_once(self):
        """Main test logic"""

        logging.info("Check EC console is available and test warm reboot")
        self.console_checker()
        self.switcher.mode_aware_reboot()

        logging.info("Check test image is on USB stick and run recovery boot")
        self.setup_usbkey(usbkey=True, host=False)
        self.switcher.reboot_to_mode(to_mode='rec')

        stdout = io.StringIO()
        self._client.run(['crossystem', 'mainfw_type'], stdout_tee=stdout)
        if stdout.getvalue() != 'recovery':
            raise error.TestError(
                    'Reboot to rec - expected fw type recovery, got %s.' %
                    stdout.getvalue())

        logging.info("Check cold boot")
        self.run_shutdown_cmd()
        self.switcher.mode_aware_reboot(reboot_type='cold',
                                        sync_before_boot=False)
