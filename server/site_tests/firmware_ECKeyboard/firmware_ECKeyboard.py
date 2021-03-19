# Copyright (c) 2012 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from threading import Timer

from autotest_lib.client.bin.input import linux_input
from autotest_lib.client.common_lib import error
from autotest_lib.server.cros.faft.firmware_test import FirmwareTest


class firmware_ECKeyboard(FirmwareTest):
    """
    Servo based EC keyboard test.
    """
    version = 1

    # Delay to ensure client is ready to read the key press.
    KEY_PRESS_DELAY = 2

    # Map the to-be-tested keys to the expected linux keycodes.
    TEST_KEY_MAP = {
            '0': linux_input.KEY_0,
            'b': linux_input.KEY_B,
            'e': linux_input.KEY_E,
            'o': linux_input.KEY_O,
            'r': linux_input.KEY_R,
            's': linux_input.KEY_S,
            't': linux_input.KEY_T,
            '<enter>': linux_input.KEY_ENTER,
            '<ctrl_l>': linux_input.KEY_LEFTCTRL,
            '<alt_l>': linux_input.KEY_LEFTALT
    }

    def initialize(self, host, cmdline_args):
        super(firmware_ECKeyboard, self).initialize(host, cmdline_args)
        # Only run in normal mode
        self.switcher.setup_mode('normal')

    def cleanup(self):
        self.faft_client.system.run_shell_command('start ui')
        super(firmware_ECKeyboard, self).cleanup()

    def run_once(self):
        """Runs a single iteration of the test."""
        if not self.check_ec_capability(['keyboard']):
            raise error.TestNAError("Nothing needs to be tested on this device")

        test_keys = ""
        expected_keycodes = []

        for key in self.TEST_KEY_MAP:
            test_keys = test_keys + key
            expected_keycodes.append(self.TEST_KEY_MAP[key])

        # Stop UI so that key presses don't go to Chrome.
        self.faft_client.system.run_shell_command('stop ui')

        Timer(self.KEY_PRESS_DELAY, self.ec.send_key_string(test_keys)).start()
        if (self.faft_client.system.check_keys(expected_keycodes) < 0):
            raise error.TestFail("Some test keys are not captured.")
