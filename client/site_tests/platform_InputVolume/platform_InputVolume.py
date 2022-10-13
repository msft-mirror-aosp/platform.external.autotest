# Lint as: python2, python3
# Copyright 2016 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.


from autotest_lib.client.bin import test
from autotest_lib.client.bin import utils
from autotest_lib.client.common_lib import error
from autotest_lib.client.common_lib.cros import chrome
from autotest_lib.client.cros.input_playback import input_playback
from autotest_lib.client.cros.audio import cras_utils


class platform_InputVolume(test.test):
    """Tests if device suspends using shortcut keys."""
    version = 1
    _WAIT = 15
    MUTE_STATUS = 'Muted'
    CTC_GREP_FOR = "cras_test_client --dump_server_info | grep "

    def warmup(self):
        """Test setup."""
        # Emulate keyboard.
        # See input_playback. The keyboard is used to play back shortcuts.
        self._player = input_playback.InputPlayback()
        self._player.emulate(input_type='keyboard')
        self._player.find_connected_inputs()

    def test_volume_down(self):
        """
        Use keyboard shortcut to test Volume Down (F9) key.

        @raises: error.TestFail if system volume did not decrease or is muted.

        """
        sys_volume_before = self.get_active_volume()
        sys_is_muted_before = self.is_muted()
        self._player.blocking_playback_of_default_file(
            input_type='keyboard', filename='keyboard_f9')
        sys_volume_after = self.get_active_volume()
        sys_is_muted_after = self.is_muted()
        # If expected sys_volume_before is 0, we should be muted.
        if sys_volume_before == 0 and not sys_is_muted_after:
            raise error.TestFail("Volume should be muted.")
        # if already mute, we should decrease volume to zero
        if sys_is_muted_before and sys_volume_after != 0:
            raise error.TestFail("Volume should be zero when system mute.")
        if sys_volume_before <= sys_volume_after:
            raise error.TestFail("Volume did not decrease: before[{}] after[{}]".format(sys_volume_before, sys_volume_after))

    def test_volume_up(self):
        """
        Use keyboard shortcut to test Volume Up (F10) key.

        @raises: error.TestFail if system volume muted or did not increase.

        """
        sys_volume_before = self.get_active_volume()
        sys_is_muted_before = self.is_muted()
        self._player.blocking_playback_of_default_file(
            input_type='keyboard', filename='keyboard_f10')
        sys_volume_after = self.get_active_volume()
        sys_is_muted_after = self.is_muted()
        if sys_is_muted_after:
            raise error.TestFail("Volume is muted when it shouldn't be.")
        # if in mute state, volume up should only change mute state.
        if sys_is_muted_before and sys_volume_before != sys_volume_after:
            raise error.TestFail("Volume changed while volume up from mute: before[{}] after[{}]".format(sys_volume_before, sys_volume_after))
        if (not sys_is_muted_before and not sys_is_muted_after) and sys_volume_before >= sys_volume_after:
            raise error.TestFail("Volume did not increase: before[{}] after[{}]".format(sys_volume_before, sys_volume_after))

    def test_mute(self):
        """Use keyboard shortcut to test Mute (F8) key.

        @raises: error.TestFail if system volume not muted.

        """
        sys_volume_before = self.get_active_volume()
        self._player.blocking_playback_of_default_file(
            input_type='keyboard', filename='keyboard_f8')
        sys_volume_after = self.get_active_volume()
        if not self.is_muted():
            raise error.TestFail("Volume not muted.")
        if sys_volume_before != sys_volume_after:
            raise error.TestFail("Volume changed while mute: before[{}] after[{}]".format(sys_volume_before, sys_volume_after))
    def get_active_volume(self):
        """
        Get current active node volume (0-100).

        @returns: current volume on active node.
        """
        return cras_utils.get_active_node_volume()

    def is_muted(self):
        """
        Returns mute status of system.

        @returns: True if system muted, False if not

        """
        output = utils.system_output(self.CTC_GREP_FOR + 'muted')
        muted = output.split(':')[-1].strip()
        return muted == self.MUTE_STATUS

    def run_once(self):
        """
        Open browser, and affect volume using mute, up, and down functions.

        """
        with chrome.Chrome(disable_default_apps=False):
            self.test_volume_down()
            self.test_volume_up()
            self.test_mute()
            self.test_volume_up()
            self.test_mute()
            self.test_volume_down()

    def cleanup(self):
        """Test cleanup."""
        self._player.close()
