# Lint as: python2, python3
# Copyright 2015 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""This is a server side audio nodes s test using the Chameleon board."""

import os
import time

from autotest_lib.client.common_lib import error
from autotest_lib.client.cros.chameleon import audio_test_utils
from autotest_lib.client.cros.chameleon import chameleon_audio_ids
from autotest_lib.client.cros.chameleon import chameleon_audio_helper
from autotest_lib.client.cros.chameleon import chameleon_port_finder

from autotest_lib.client.cros.chameleon import edid as edid_lib
from autotest_lib.server.cros.audio import audio_test

URL = 'https://www.youtube.com/watch?v=aqz-KE-bpKQ'


class audio_AudioNodeSwitch(audio_test.AudioTest):
    """Server side audio test.

    This test talks to a Chameleon board and a Cros device to verify
    audio nodes switch correctly.

    """
    version = 1
    _APPLY_EDID_DELAY = 5
    _PLUG_DELAY = 5
    _WAIT_TO_LOAD_VIDEO = 5
    _VOLUMES = {'INTERNAL_SPEAKER': 100,
                'HEADPHONE': 80,
                'LINEOUT': 80,
                'HDMI': 60,
                'USB': 40,}

    def check_default_nodes(self):
        """Checks default audio nodes for devices with onboard audio support."""
        if self.host.get_board().split(':')[1] in blocked_boards:
            raise error.TestNAError('Board not applicable to test!')
        if audio_test_utils.has_internal_microphone(self.host):
            audio_test_utils.check_audio_nodes(self.facade,
                                               (None, ['INTERNAL_MIC']))
        if audio_test_utils.has_internal_speaker(self.host):
            audio_test_utils.check_audio_nodes(self.facade,
                                               (['INTERNAL_SPEAKER'], None))


    def set_active_volume_to_node_volume(self, node):
        """Sets Chrome volume to the specified volume of node.

        @param node: One of node type in self._VOLUMES.

        """
        self.facade.set_chrome_active_volume(self._VOLUMES[node])


    def check_active_node_volume(self, node):
        """Checks the active node type and checks if its volume is as expected.

        @param node: The expected node.

        @raises: TestFail if node volume is not as expected.

        """
        # Checks the node type is the active node type.
        audio_test_utils.check_audio_nodes(self.facade, ([node], None))
        # Checks if active volume is the node volume.
        volume, mute = self.facade.get_chrome_active_volume_mute()
        expected_volume = self._VOLUMES[node]
        if volume != expected_volume:
            raise error.TestFail(
                    'Node %s volume %d != %d' % (node, volume, expected_volume))


    def switch_nodes_and_check_volume(self, nodes):
        """Switches between nodes and check the node volumes.

        @param nodes: A list of node types to check.

        """
        if len(nodes) == 1:
            self.check_active_node_volume(nodes[0])
        for node in nodes:
            # Switch nodes and check their volume.
            self.facade.set_chrome_active_node_type(node, None)
            self.check_active_node_volume(node)


    def run_once(self, jack_node=False, hdmi_node=False,
                 usb_node=False, play_audio=False):
        """Runs AudioNodeSwitch test."""
        self.display_facade = self.factory.create_display_facade()

        self.check_default_nodes()
        nodes = []
        if audio_test_utils.has_internal_speaker(self.host):
            self.set_active_volume_to_node_volume('INTERNAL_SPEAKER')
            nodes.append('INTERNAL_SPEAKER')
            self.switch_nodes_and_check_volume(nodes)

        if play_audio:
            self.browser_facade = self.factory.create_browser_facade()
            self.browser_facade.new_tab(URL)
            time.sleep(self._WAIT_TO_LOAD_VIDEO)
        if hdmi_node:
            edid_path = os.path.join(self.bindir,
                                     'test_data/edids/HDMI_DELL_U2410.txt')
            finder = chameleon_port_finder.ChameleonVideoInputFinder(
                self.host.chameleon, self.display_facade)
            hdmi_port = finder.find_port('HDMI')
            hdmi_port.apply_edid(edid_lib.Edid.from_file(edid_path))
            time.sleep(self._APPLY_EDID_DELAY)
            hdmi_port.set_plug(True)
            time.sleep(self._PLUG_DELAY * 2)

            audio_test_utils.check_audio_nodes(self.facade,
                                               (['HDMI'], None))
            if play_audio:
                self.facade.check_audio_stream_at_selected_device()
            self.set_active_volume_to_node_volume('HDMI')
            nodes.append('HDMI')
            self.switch_nodes_and_check_volume(nodes)

        if jack_node:
            jack_plugger = self.host.chameleon.get_audio_board(
                ).get_jack_plugger()
            jack_plugger.plug()
            time.sleep(self._PLUG_DELAY)
            audio_test_utils.dump_cros_audio_logs(self.host, self.facade,
                                                  self.resultsdir)

            # Checks whether line-out or headphone is detected.
            hp_jack_node_type = audio_test_utils.check_hp_or_lineout_plugged(
                    self.facade)

            audio_test_utils.check_audio_nodes(self.facade,
                                               (None, ['MIC']))

            self.set_active_volume_to_node_volume(hp_jack_node_type)

            nodes.append(hp_jack_node_type)
            self.switch_nodes_and_check_volume(nodes)

        if usb_node:
            source = self.widget_factory.create_widget(
                chameleon_audio_ids.CrosIds.USBOUT)
            recorder = self.widget_factory.create_widget(
                chameleon_audio_ids.ChameleonIds.USBIN)
            binder = self.widget_factory.create_binder(source, recorder)

            with chameleon_audio_helper.bind_widgets(binder):
                time.sleep(self._PLUG_DELAY)
                audio_test_utils.check_audio_nodes(self.facade,
                                                   (['USB'], ['USB']))
                self.set_active_volume_to_node_volume('USB')
                nodes.append('USB')
                self.switch_nodes_and_check_volume(nodes)
            time.sleep(self._PLUG_DELAY)
            nodes.remove('USB')
            self.switch_nodes_and_check_volume(nodes)

        if jack_node:
            if usb_node:
                audio_test_utils.check_audio_nodes(
                        self.facade, ([hp_jack_node_type], ['MIC']))
            jack_plugger.unplug()
            time.sleep(self._PLUG_DELAY)
            nodes.remove(hp_jack_node_type)
            self.switch_nodes_and_check_volume(nodes)

        if hdmi_node:
            if usb_node or jack_node :
                audio_test_utils.check_audio_nodes(self.facade,
                                                   (['HDMI'], None))
            hdmi_port.set_plug(False)
            time.sleep(self._PLUG_DELAY)
            nodes.remove('HDMI')
            self.switch_nodes_and_check_volume(nodes)

        self.check_default_nodes()
