# Copyright 2012 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# TODO(b/290823172) Remove this file when the test is no longer in any PVS plan

import logging
import time

from autotest_lib.client.common_lib import error
from autotest_lib.server.cros.faft.firmware_test import FirmwareTest

class firmware_ECWatchdog(FirmwareTest):
    """
    Servo based EC watchdog test.
    """
    version = 1


    # Delay of spin-wait in ms. Nuvoton boards set the hardware watchdog to
    # 3187.5ms and also sets a timer to 2200ms. Set the timeout long enough to
    # exceed the hardware watchdog timer because the timer isn't 100% reliable.
    # If there are other platforms that use a longer watchdog timeout, this
    # may need to be adjusted.
    WATCHDOG_DELAY = 3700  # 3187.5ms + 500ms safety margin, rounded up.

    # Delay of EC power on.
    EC_BOOT_DELAY = 1000


    def initialize(self, host, cmdline_args):
        super(firmware_ECWatchdog, self).initialize(host, cmdline_args)
        # Only run in normal mode
        self.switcher.setup_mode('normal')


    def reboot_by_watchdog(self):
        """
        Trigger a watchdog reset.
        """
        self.faft_client.system.run_shell_command("sync")
        self.ec.send_command("waitms %d" % self.WATCHDOG_DELAY)
        time.sleep((self.WATCHDOG_DELAY + self.EC_BOOT_DELAY) / 1000.0)
        self.check_lid_and_power_on()


    def run_once(self):
        """Runs a single iteration of the test."""
        if not self.check_ec_capability():
            raise error.TestNAError("Nothing needs to be tested on this device")

        logging.info("Trigger a watchdog reset and power on system again.")
        self.switcher.mode_aware_reboot('custom', self.reboot_by_watchdog)
