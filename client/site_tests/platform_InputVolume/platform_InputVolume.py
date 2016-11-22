# Copyright 2016 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import logging
import re
import time

from autotest_lib.client.bin import test
from autotest_lib.client.bin import utils
from autotest_lib.client.common_lib import error
from autotest_lib.client.common_lib.cros import chrome
from autotest_lib.client.cros.input_playback import input_playback
from telemetry.core import exceptions


class platform_InputVolume(test.test):
    """Tests if device suspends using shortcut keys."""
    version = 1
    _WAIT = 15
    MUTE_CMD = "cras_test_client --dump_server_info|grep muted"
    VOLUME_CMD = "cras_test_client --dump_server_info|grep INTERNAL_SPEAKER"
    MUTE_STATUS = 'Muted'

    def warmup(self):
        """Test setup."""
        # Emulate keyboard.
        # See input_playback. The keyboard is used to play back shortcuts.
        self._player = input_playback.InputPlayback()
        self._player.emulate(input_type='keyboard')
        self._player.find_connected_inputs()

    def test_volume_down(self, volume):
        """
        Use keyboard shortcut to test Volume Down (F9) key.

        @param volume: expected volume.

        @raises: error.TestFail if system volume did not decrease or is muted.

        """
        self._player.blocking_playback_of_default_file(
            input_type='keyboard', filename='keyboard_f9')
        # If expected volume is 0, we should be muted.
        if volume == 0 and not self.is_muted():
            raise error.TestFail("Volume should be muted.")
        sys_volume = self.get_system_volume()
        if sys_volume != volume:
            raise error.TestFail("Volume did not decrease: %s" % sys_volume)

    def test_volume_up(self, volume):
        """
        Use keyboard shortcut to test Volume Up (F10) key.

        @param volume: expected volume

        @raises: error.TestFail if system volume muted or did not increase.

        """
        self._player.blocking_playback_of_default_file(
            input_type='keyboard', filename='keyboard_f10')
        if self.is_muted():
            raise error.TestFail("Volume is muted when it shouldn't be.")
        sys_volume = self.get_system_volume()
        if sys_volume != volume:
            raise error.TestFail("Volume did not increase: %s" % sys_volume)

    def test_mute(self, volume):
        """Use keyboard shortcut to test Mute (F8) key.

        @param volume: expected volume

        @raises: error.TestFail if system volume not muted.

        """
        sys_volume = self.get_system_volume()
        self._player.blocking_playback_of_default_file(
            input_type='keyboard', filename='keyboard_f8')
        if not self.is_muted():
            raise error.TestFail("Volume not muted.")
        if sys_volume != volume:
            raise error.TestFail("Volume changed while mute: %s" % sys_volume)

    def get_system_volume(self):
        """
        Get current system volume (0-100).

        @returns: current system volume.
        """
        volume_output = utils.system_output(self.VOLUME_CMD)
        sys_volume = re.split('\s+', volume_output)[3]
        return int(sys_volume)

    def is_muted(self):
        """
        Returns mute status of system.

        @returns: True if system muted, False if not

        """
        output = utils.system_output(self.MUTE_CMD)
        muted = output.split(':')[-1].strip()
        return muted == self.MUTE_STATUS

    def run_once(self):
        """
        Open browser, and affect volume using mute, up, and down functions.

        """
        with chrome.Chrome():
            current_volume = self.get_system_volume()
            self.test_volume_up(current_volume + 4)
            self.test_volume_down(current_volume)
            self.test_mute(current_volume)
            self.test_volume_up(current_volume)

    def cleanup(self):
        """Test cleanup."""
        self._player.close()
