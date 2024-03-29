# Lint as: python2, python3
# Copyright 2020 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""A Batch of Bluetooth AUdio Health tests"""

import functools
import time
import logging

from autotest_lib.client.common_lib import error
from autotest_lib.client.cros.bluetooth.bluetooth_audio_test_data import (
        A2DP, A2DP_MEDIUM, A2DP_LONG, A2DP_RATE_44100, AVRCP, HFP_WBS, HFP_NBS,
        HFP_WBS_MEDIUM, HFP_NBS_MEDIUM, A2DP_CODEC, AAC, CAP_PIPEWIRE,
        HFP_CODEC, HFP_SWB, LC3)
from autotest_lib.server.cros.bluetooth.bluetooth_adapter_audio_tests import (
        BluetoothAdapterAudioTests)
from autotest_lib.server.cros.bluetooth.bluetooth_adapter_quick_tests import (
        BluetoothAdapterQuickTests)
from autotest_lib.client.cros.chameleon.audio_test_utils import (
        has_internal_speaker)


class bluetooth_AdapterAUHealth(BluetoothAdapterQuickTests,
                                BluetoothAdapterAudioTests):
    """A Batch of Bluetooth audio health tests."""

    test_wrapper = BluetoothAdapterQuickTests.quick_test_test_decorator
    batch_wrapper = BluetoothAdapterQuickTests.quick_test_batch_decorator

    def au_run_method(self,
                      device,
                      test_method,
                      test_profile,
                      collect_audio_files=False,
                      audio_config={}):
        """audio procedure of running a specified test method.

        @param device: the bt peer device
        @param test_method: the audio test method to run
        @param test_profile: which test profile is used,
                             A2DP, HFP_SWB, HFP_WBS or HFP_NBS
        @param collect_audio_files: set to True to collect the recorded audio
                                    files.
        @param audio_config: the test specific audio config
        """
        self.test_reset_on_adapter()
        self.test_bluetoothd_running()
        # TODO: b/277702522 remove this after bluetooth telephony launch.
        if self.floss:
            self.test_set_bluetooth_telephony(True)
        self.initialize_bluetooth_audio(device,
                                        test_profile,
                                        audio_config=audio_config)
        self.test_device_set_discoverable(device, True)
        self.test_discover_device(device.address)

        # Capture the btmon log to determine the codec used.
        # This is performed for the A2DP profile for now.
        # The HFP profile will be covered later.
        if self.is_a2dp_profile(test_profile):
            self.bluetooth_facade.btmon_start()

        self.test_pairing(device.address, device.pin, trusted=True)
        self.test_connection_by_adapter(device.address)
        test_method()

        # Stop the btmon log and verify the codec.
        if self.is_a2dp_profile(test_profile):
            self.bluetooth_facade.btmon_stop()
            self.test_audio_codec()

        self.collect_audio_diagnostics()
        if collect_audio_files:
            self.collect_audio_files()
        self.test_disconnection_by_adapter(device.address)
        self.cleanup_bluetooth_audio(device, test_profile)


    def au_run_test_sequence(self,
                             device,
                             test_sequence,
                             test_profile,
                             collect_audio_files=False,
                             audio_config={}):
        """Audio procedure of running a specified test sequence.

        @param device: The Bluetooth peer device.
        @param test_sequence: The audio test sequence to run.
        @param test_profile: Which test profile is used,
                             A2DP, A2DP_MEDIUM, HFP_WBS or HFP_NBS.
        @param collect_audio_files: set to True to collect the recorded audio
                            files.
        @param audio_config: the test specific audio config
        """
        # Setup the Bluetooth device.
        self.test_reset_on_adapter()
        self.test_bluetoothd_running()
        self.initialize_bluetooth_audio(device,
                                        test_profile,
                                        audio_config=audio_config)
        test_sequence()
        self.collect_audio_diagnostics()
        if collect_audio_files:
            self.collect_audio_files()
        self.cleanup_bluetooth_audio(device, test_profile)


    def _au_a2dp_test(self, test_profile, duration=0, audio_config={}):
        """A2DP test with sinewaves on the two channels.

        @param test_profile: which test profile is used, A2DP or A2DP_LONG.
        @param duration: the duration to test a2dp. The unit is in seconds.
                if duration is 0, use the default duration in test_profile.
        @param audio_config: the test specific audio config
        """
        device = self.devices['BLUETOOTH_AUDIO'][0]
        self.au_run_method(device,
                           lambda: self.test_a2dp_sinewaves(
                                   device, test_profile, duration),
                           test_profile,
                           audio_config=audio_config)


    @test_wrapper('A2DP sinewave test',
                  devices={'BLUETOOTH_AUDIO': 1},
                  supports_floss=True)
    def au_a2dp_test(self):
        """A2DP test with sinewaves on the two channels."""
        self._au_a2dp_test(A2DP)


    @test_wrapper('A2DP sinewave test with the AAC codec',
                  devices={'BLUETOOTH_AUDIO': ((CAP_PIPEWIRE), )},
                  supports_floss=True)
    def au_a2dp_aac_test(self):
        """A2DP test with sinewaves with the AAC codec."""
        # TODO(b/308882924): remove this once it is enabled by default
        self.test_set_force_a2dp_advanced_codecs_enabled(True)
        self._au_a2dp_test(A2DP, audio_config={A2DP_CODEC: AAC})
        self.test_set_force_a2dp_advanced_codecs_enabled(False)

    # The A2DP long test is a stress test. Exclude it from the AVL.
    @test_wrapper('A2DP sinewave long test',
                  devices={'BLUETOOTH_AUDIO':1},
                  flags=['Quick Health'],
                  supports_floss=True)
    def au_a2dp_long_test(self, duration=600):
        """A2DP long test with sinewaves on the two channels.

        @param duration: the duration to test a2dp. The unit is in seconds.
        """
        self._au_a2dp_test(A2DP_LONG, duration=duration)


    # Remove flags=['Quick Health'] when this test is migrated to stable suite.
    @test_wrapper('A2DP rate 44100 sinewave test',
                  devices={'BLUETOOTH_AUDIO': 1},
                  supports_floss=True,
                  flags=['Quick Health'])
    def au_a2dp_rate_44100_test(self):
        """A2DP test with sampling rate 44100 to emulate Intel THD+N tests."""
        self._au_a2dp_test(A2DP_RATE_44100)

    @test_wrapper('A2DP playback and connect test',
                  devices={'BLUETOOTH_AUDIO': 1},
                  supports_floss=True)
    def au_a2dp_playback_and_connect_test(self):
        """Connect then disconnect an A2DP device while playing stream."""
        if not has_internal_speaker(self.host):
            logging.info('SKIPPING TEST A2DP playback and connect test')
            raise error.TestNAError(
                    'The DUT does not have an internal speaker')

        device = self.devices['BLUETOOTH_AUDIO'][0]
        test_profile = A2DP_MEDIUM
        test_sequence = lambda: self.playback_and_connect(device, test_profile)
        self.au_run_test_sequence(device, test_sequence, test_profile)


    @test_wrapper('A2DP playback and disconnect test',
                  devices={'BLUETOOTH_AUDIO': 1},
                  supports_floss=True)
    def au_a2dp_playback_and_disconnect_test(self):
        """Check the playback stream is still alive after BT disconnected."""
        device = self.devices['BLUETOOTH_AUDIO'][0]
        test_profile = A2DP_MEDIUM
        test_sequence = lambda: self.playback_and_disconnect(
                device, test_profile)
        self.au_run_test_sequence(device, test_sequence, test_profile)


    @test_wrapper('A2DP playback back2back test',
                  devices={'BLUETOOTH_AUDIO': 1},
                  supports_floss=True)
    def au_a2dp_playback_back2back_test(self):
        """A2DP playback stream back to back test."""
        device = self.devices['BLUETOOTH_AUDIO'][0]
        test_profile = A2DP_MEDIUM
        test_sequence = lambda: self.playback_back2back(device, test_profile)
        self.au_run_test_sequence(device,
                                  test_sequence,
                                  test_profile,
                                  collect_audio_files=True)


    @test_wrapper('A2DP pinned playback test',
                  devices={'BLUETOOTH_AUDIO': 1},
                  supports_floss=True)
    def au_a2dp_pinned_playback_test(self):
        """Pinned playback stream test."""
        device = self.devices['BLUETOOTH_AUDIO'][0]
        test_profile = A2DP
        test_sequence = lambda: self.pinned_playback(device, test_profile)
        self.au_run_test_sequence(device, test_sequence, test_profile)

    def au_hfp_run_method(self,
                          device,
                          test_method,
                          test_profile,
                          audio_config={}):
        """Run an HFP test with the specified test method.

        @param device: the bt peer device
        @param test_method: the specific HFP WBS test method
        @param test_profile: which test profile is used, HFP_SWB, HFP_WBS, or HFP_NBS
        @param audio_config: the test specific audio config
        """
        if self.check_wbs_capability():
            if test_profile in (HFP_WBS, HFP_WBS_MEDIUM, HFP_SWB):
                # Restart cras to ensure that cras goes back to the default
                # selection of the codecs.
                # Any board that supports more than one codec should use the
                # best, unless it's overridden by CRAS' config.
                # Do not enable WBS explicitly in the test so we can catch if
                # the default selection goes wrong.
                self.restart_cras()
                # The audio team suggests a simple 2-second sleep.
                time.sleep(2)
            elif test_profile in (HFP_NBS, HFP_NBS_MEDIUM):
                # Cras may be in either WBS or NBS mode. Disable WBS explicitly.
                if not self.bluetooth_facade.enable_wbs(False):
                    raise error.TestError('failed to disable wbs')
        else:
            if test_profile in (HFP_WBS, HFP_WBS_MEDIUM, HFP_SWB):
                # Skip the WBS test on a board that does not support WBS.
                raise error.TestNAError(
                        'The DUT does not support WBS. Skip the test.')
            elif test_profile in (HFP_NBS, HFP_NBS_MEDIUM):
                # Restart cras to ensure that cras goes back to the default
                # selection of either WBS or NBS.
                # Any board that does not support WBS should use NBS by default.
                # Do not enable NBS explicitly in the test so we can catch if
                # the default selection goes wrong.
                self.restart_cras()
                # The audio team suggests a simple 2-second sleep.
                time.sleep(2)

        if test_profile == HFP_SWB:
            if not self.check_swb_capability():
                raise error.TestNAError(
                        'The DUT does not support SWB. Skip the test.')

            # remove this flag toggle once it is enabled by default (b/308859926)
            # the DUT should always choose the best codec reported by the peer
            self.test_set_force_hfp_swb_enabled(True)

        self.au_run_method(device,
                           lambda: test_method(device, test_profile),
                           test_profile,
                           audio_config=audio_config)

        # remove this flag toggle once it is enabled by default (b/308859926)
        # the DUT should always choose the best codec reported by the peer
        self.test_set_force_hfp_swb_enabled(False)

    @test_wrapper('HFP SWB sinewave test with dut as source',
                  devices={'BLUETOOTH_AUDIO': ((CAP_PIPEWIRE), )},
                  supports_floss=True)
    def au_hfp_swb_dut_as_source_test(self):
        """HFP SWB test with sinewave streaming from dut to peer."""
        device = self.devices['BLUETOOTH_AUDIO'][0]
        self.au_hfp_run_method(device,
                               self.hfp_dut_as_source,
                               HFP_SWB,
                               audio_config={HFP_CODEC: LC3})

    @test_wrapper('HFP SWB sinewave test with dut as sink',
                  devices={'BLUETOOTH_AUDIO': ((CAP_PIPEWIRE), )},
                  supports_floss=True)
    def au_hfp_swb_dut_as_sink_test(self):
        """HFP SWB test with sinewave streaming from peer to dut."""
        device = self.devices['BLUETOOTH_AUDIO'][0]
        self.au_hfp_run_method(device,
                               functools.partial(
                                       self.hfp_dut_as_sink,
                                       check_input_device_sample_rate=32000),
                               HFP_SWB,
                               audio_config={HFP_CODEC: LC3})

    @test_wrapper('HFP WBS sinewave test with dut as source',
                  devices={'BLUETOOTH_AUDIO':1},
                  supports_floss=True)
    def au_hfp_wbs_dut_as_source_test(self):
        """HFP WBS test with sinewave streaming from dut to peer."""
        device = self.devices['BLUETOOTH_AUDIO'][0]
        self.au_hfp_run_method(device, self.hfp_dut_as_source, HFP_WBS)


    @test_wrapper('HFP WBS sinewave test with dut as sink',
                  devices={'BLUETOOTH_AUDIO':1},
                  supports_floss=True)
    def au_hfp_wbs_dut_as_sink_test(self):
        """HFP WBS test with sinewave streaming from peer to dut."""
        device = self.devices['BLUETOOTH_AUDIO'][0]
        self.au_hfp_run_method(
                device,
                functools.partial(self.hfp_dut_as_sink,
                    check_input_device_sample_rate=16000),
                HFP_WBS)


    @test_wrapper('HFP NBS sinewave test with dut as source',
                  devices={'BLUETOOTH_AUDIO': 1},
                  supports_floss=True)
    def au_hfp_nbs_dut_as_source_test(self):
        """HFP NBS test with sinewave streaming from dut to peer."""
        device = self.devices['BLUETOOTH_AUDIO'][0]
        self.au_hfp_run_method(device, self.hfp_dut_as_source, HFP_NBS)


    @test_wrapper('HFP NBS sinewave test with dut as sink',
                  devices={'BLUETOOTH_AUDIO': 1},
                  supports_floss=True)
    def au_hfp_nbs_dut_as_sink_test(self):
        """HFP NBS test with sinewave streaming from peer to dut."""
        device = self.devices['BLUETOOTH_AUDIO'][0]
        self.au_hfp_run_method(
                device,
                functools.partial(self.hfp_dut_as_sink,
                    check_input_device_sample_rate=8000),
                HFP_NBS)


    @test_wrapper(
            'HFP NBS sinewave test with dut as sink with super resolution',
            devices={'BLUETOOTH_AUDIO': 1},
            allowed_boards={
                    'eve',
                    'soraka',
                    'nautilus',
                    'nami',
                    'nocturne',
                    'rammus',
                    'fizz',
            },
            supports_floss=True)
    def au_hfp_nbs_dut_as_sink_with_super_resolution_test(self):
        """HFP NBS test with sinewave and super_resolution streaming from peer to dut."""
        device = self.devices['BLUETOOTH_AUDIO'][0]
        # Enabling ui is needed, or the downloading in dlc service won't work.
        self.au_hfp_run_method(device,
                               self.hfp_dut_as_sink_with_super_resolution,
                               HFP_NBS)


    @test_wrapper('HFP WBS VISQOL test with dut as sink',
                  devices={'BLUETOOTH_AUDIO':1},
                  supports_floss=True)
    def au_hfp_wbs_dut_as_sink_visqol_test(self):
        """HFP WBS VISQOL test with audio streaming from peer to dut"""
        device = self.devices['BLUETOOTH_AUDIO'][0]
        self.au_hfp_run_method(device, self.hfp_dut_as_sink_visqol_score,
                               HFP_WBS)


    @test_wrapper('HFP WBS VISQOL test with dut as source',
                  devices={'BLUETOOTH_AUDIO':1},
                  supports_floss=True)
    def au_hfp_wbs_dut_as_source_visqol_test(self):
        """HFP WBS VISQOL test with audio streaming from dut to peer"""
        device = self.devices['BLUETOOTH_AUDIO'][0]
        self.au_hfp_run_method(device, self.hfp_dut_as_source_visqol_score,
                               HFP_WBS)

    @test_wrapper('HFP NBS VISQOL test with dut as sink',
                  devices={'BLUETOOTH_AUDIO':1},
                  supports_floss=True)
    def au_hfp_nbs_dut_as_sink_visqol_test(self):
        """HFP NBS VISQOL test with audio streaming from peer to dut"""
        device = self.devices['BLUETOOTH_AUDIO'][0]
        self.au_hfp_run_method(device, self.hfp_dut_as_sink_visqol_score,
                               HFP_NBS)


    @test_wrapper('HFP NBS VISQOL test with dut as source',
                  devices={'BLUETOOTH_AUDIO':1},
                  supports_floss=True)
    def au_hfp_nbs_dut_as_source_visqol_test(self):
        """HFP NBS VISQOL test with audio streaming from dut to peer"""
        device = self.devices['BLUETOOTH_AUDIO'][0]
        self.au_hfp_run_method(device, self.hfp_dut_as_source_visqol_score,
                               HFP_NBS)


    @test_wrapper('HFP NBS back2back test with dut as source',
                  devices={'BLUETOOTH_AUDIO': 1},
                  supports_floss=True)
    def au_hfp_nbs_dut_as_source_back2back_test(self):
        """HFP NBS back2back test from dut to peer"""
        device = self.devices['BLUETOOTH_AUDIO'][0]
        self.au_hfp_run_method(device, self.hfp_dut_as_source_back2back,
                               HFP_NBS)


    @test_wrapper('HFP WBS back2back test with dut as source',
                  devices={'BLUETOOTH_AUDIO': 1},
                  supports_floss=True)
    def au_hfp_wbs_dut_as_source_back2back_test(self):
        """HFP WBS back2back test from dut to peer"""
        device = self.devices['BLUETOOTH_AUDIO'][0]
        self.au_hfp_run_method(device, self.hfp_dut_as_source_back2back,
                               HFP_WBS)


    @test_wrapper('Switch A2DP to HFP NBS test with dut as source',
                  devices={'BLUETOOTH_AUDIO': 1},
                  supports_floss=True)
    def au_a2dp_to_hfp_nbs_dut_as_source_test(self):
        """Switch A2DP to HFP NBS test with dut as source."""
        device = self.devices['BLUETOOTH_AUDIO'][0]
        self.au_hfp_run_method(device, self.a2dp_to_hfp_dut_as_source,
                               HFP_NBS_MEDIUM)


    @test_wrapper('Switch A2DP to HFP WBS test with dut as source',
                  devices={'BLUETOOTH_AUDIO': 1},
                  supports_floss=True)
    def au_a2dp_to_hfp_wbs_dut_as_source_test(self):
        """Switch A2DP to HFP WBS test with dut as source."""
        device = self.devices['BLUETOOTH_AUDIO'][0]
        self.au_hfp_run_method(device, self.a2dp_to_hfp_dut_as_source,
                               HFP_WBS_MEDIUM)


    @test_wrapper('Switch HFP NBS to A2DP test with dut as source',
                  devices={'BLUETOOTH_AUDIO': 1},
                  supports_floss=True)
    def au_hfp_nbs_to_a2dp_dut_as_source_test(self):
        """Switch HFP NBS to A2DP test with dut as source."""
        device = self.devices['BLUETOOTH_AUDIO'][0]
        self.au_hfp_run_method(device, self.hfp_to_a2dp_dut_as_source,
                               HFP_NBS_MEDIUM)


    @test_wrapper('Switch HFP WBS to A2DP test with dut as source',
                  devices={'BLUETOOTH_AUDIO': 1},
                  supports_floss=True)
    def au_hfp_wbs_to_a2dp_dut_as_source_test(self):
        """Switch HFP WBS to A2DP test with dut as source."""
        device = self.devices['BLUETOOTH_AUDIO'][0]
        self.au_hfp_run_method(device, self.hfp_to_a2dp_dut_as_source,
                               HFP_WBS_MEDIUM)


    def au_run_avrcp_method(self, device, test_method):
        """avrcp procedure of running a specified test method.

        @param device: the bt peer device
        @param test_method: the avrcp test method to run
        """
        def wrapped_test_method(device):
            """A wrapper method to initialize and cleanup avrcp tests.

            @param device: the bt peer device
            """
            self.initialize_bluetooth_player(device)
            self.enable_audio_stream_for_avrcp(device)
            test_method(device)
            self.stop_audio_stream_for_avrcp()
            self.cleanup_bluetooth_player(device)

        self.au_run_method(
                device, lambda: wrapped_test_method(device), AVRCP)


    @test_wrapper('avrcp command test',
                  devices={'BLUETOOTH_AUDIO': 1},
                  supports_floss=True)
    def au_avrcp_command_test(self):
        """AVRCP test to examine commands reception."""
        device = self.devices['BLUETOOTH_AUDIO'][0]
        self.au_run_avrcp_method(device, self.test_avrcp_commands)


    @test_wrapper('avrcp media info test',
                  devices={'BLUETOOTH_AUDIO': 1},
                  supports_floss=True)
    def au_avrcp_media_info_test(self):
        """AVRCP test to examine metadata propgation."""
        device = self.devices['BLUETOOTH_AUDIO'][0]
        self.au_run_avrcp_method(device, self.test_avrcp_media_info)


    @batch_wrapper('Bluetooth Audio Batch Health Tests')
    def au_health_batch_run(self, num_iterations=1, test_name=None):
        """Run the bluetooth audio health test batch or a specific given test.

        @param num_iterations: how many iterations to run
        @param test_name: specific test to run otherwise None to run the
                whole batch
        """
        self.au_a2dp_test()
        self.au_a2dp_rate_44100_test()
        self.au_a2dp_long_test()
        self.au_hfp_nbs_dut_as_source_test()
        self.au_hfp_nbs_dut_as_sink_test()
        self.au_hfp_wbs_dut_as_source_test()
        self.au_hfp_wbs_dut_as_sink_test()
        self.au_hfp_wbs_dut_as_source_visqol_test()
        self.au_hfp_wbs_dut_as_sink_visqol_test()
        self.au_hfp_nbs_dut_as_source_visqol_test()
        self.au_hfp_nbs_dut_as_sink_visqol_test()
        self.au_avrcp_command_test()
        self.au_avrcp_media_info_test()
        self.au_a2dp_playback_and_connect_test()
        self.au_a2dp_playback_and_disconnect_test()
        self.au_a2dp_playback_back2back_test()
        self.au_a2dp_pinned_playback_test()
        self.au_hfp_nbs_dut_as_source_back2back_test()
        self.au_hfp_wbs_dut_as_source_back2back_test()
        self.au_a2dp_to_hfp_nbs_dut_as_source_test()
        self.au_a2dp_to_hfp_wbs_dut_as_source_test()
        self.au_hfp_nbs_to_a2dp_dut_as_source_test()
        self.au_hfp_wbs_to_a2dp_dut_as_source_test()
        # The following tests will try to enable ui before running the tests
        # and they will also try to disable ui after the test run.
        self.au_hfp_nbs_dut_as_sink_with_super_resolution_test()


    def run_once(self,
                 host,
                 num_iterations=1,
                 args_dict=None,
                 test_name=None,
                 flag='Quick Health',
                 floss=False,
                 enable_cellular=False,
                 enable_ui=False):
        """Run the batch of Bluetooth stand health tests

        @param host: the DUT, usually a chromebook
        @param num_iterations: the number of rounds to execute the test
        @param test_name: the test to run, or None for all tests
        """
        self.host = host
        self.cleanup_audio_config()

        self.quick_test_init(host,
                             use_btpeer=True,
                             flag=flag,
                             args_dict=args_dict,
                             floss=floss,
                             enable_cellular=enable_cellular,
                             enable_ui=enable_ui)
        self.au_health_batch_run(num_iterations, test_name)
        self.quick_test_cleanup()
