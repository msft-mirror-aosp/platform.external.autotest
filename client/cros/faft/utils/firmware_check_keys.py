# Copyright 2015 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import print_function

import glob
import logging
import pprint
from threading import Timer

from autotest_lib.client.bin.input.input_device import *


class firmwareCheckKeys(object):
    """An abstraction to deal with checking firmware keys."""
    # pylint: disable=undefined-variable
    version = 1
    actual_output = []
    device = None
    power_key_device = None
    ev = None

    def __init__(self):
        for evdev in glob.glob("/dev/input/event*"):
            device = InputDevice(evdev)
            if device.is_keyboard():
                print('keyboard device %s' % evdev)
                self.device = device
            if 'cros_ec_buttons' in str(device.name):
                self.power_key_device = device
        # If no cros_ec_buttons device, use regular kb for power key keycode.
        if not self.power_key_device:
            self.power_key_device = self.device

    def _keyboard_input(self, device):
        """Read key presses."""
        index = 0
        while True:
            self.ev.read(device.f)
            if self.ev.code != KEY_RESERVED:
                print("EventCode is %d value is %d" %
                      (self.ev.code, self.ev.value))
                if self.ev.type == 0 or self.ev.type == 1:
                    self.actual_output.append(self.ev.code)
                    index = index + 1

    def _compare_unique_output_to_sequence(self, expected_sequence):
        """Compare unique output from _keyboard_input to expected sequence.
        Keypresses will have a tendency to repeat as there is delay between
        the down and up events.  We're not interested in precisely how many
        repeats of the key there is, just what is the sequence of keys,
        so, we will make the list unique.

        @param expected_sequence: A list of expected key sequences.
        """
        uniq_actual_output = []
        for i, key in enumerate(self.actual_output):
            if key not in self.actual_output[:i]:
                uniq_actual_output.append(key)

        if uniq_actual_output != expected_sequence:
            print('Keys mismatched %s' % pprint.pformat(uniq_actual_output))
            return -1
        print('Key match expected: %s' % pprint.pformat(uniq_actual_output))
        return len(uniq_actual_output)

    def check_keys(self, expected_sequence):
        """Wait for key press for 10 seconds.

        @return number of input keys captured, -1 for error.
        """
        if not self.device:
            logging.error("Could not find a keyboard device")
            return -1

        self.ev = InputEvent()
        Timer(0, self._keyboard_input, args=(self.device, )).start()

        time.sleep(10)
        return self._compare_unique_output_to_sequence(expected_sequence)

    def check_power_key(self):
        """Wait for power key press for 10 seconds.

        @return number of input presses captured, -1 for error.
        """
        if not self.power_key_device:
            logging.error("Could not find a power key device")
            return -1

        self.ev = InputEvent()
        Timer(0, self._keyboard_input, args=(self.power_key_device, )).start()

        time.sleep(10)
        power_key_seq = [116]
        return self._compare_unique_output_to_sequence(power_key_seq)
