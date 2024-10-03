# Lint as: python2, python3
# Copyright 2020 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""A Batch of Bluetooth AUdio Health tests"""

import logging
import time

from autotest_lib.client.common_lib import error
from autotest_lib.client.cros.bluetooth.bluetooth_audio_test_data import (
        A2DP, A2DP_MEDIUM, A2DP_LONG, A2DP_RATE_44100, AVRCP, HFP_WBS, HFP_NBS,
        HFP_WBS_MEDIUM, HFP_NBS_MEDIUM, A2DP_CODEC, AAC, CAP_PIPEWIRE,
        HFP_CODEC, HFP_SWB, HFP_TELEPHONY, LC3, AUDIO_RECORD_DIR)
from autotest_lib.server.cros.bluetooth.bluetooth_adapter_audio_tests import (
        BluetoothAdapterAudioTests)
from autotest_lib.server.cros.bluetooth.bluetooth_adapter_quick_tests import (
        BluetoothAdapterQuickTests)
from autotest_lib.client.cros.chameleon.audio_test_utils import (
        has_internal_speaker)


class bluetooth_AdapterAUHealth(BluetoothAdapterQuickTests,
                                BluetoothAdapterAudioTests):
    """A Batch of Bluetooth audio health tests."""

    batch_wrapper = BluetoothAdapterQuickTests.quick_test_batch_decorator

    def __init__(self, job, bindir, outputdir):
        super().__init__(job, bindir, outputdir)
        self.dut_atlog_path = None

    def hfp_test_pretest(self, device, test_profile, audio_config={}):
        """Common procedure before running a HFP test.

        @param device: the bt peer device
        @param test_profile: which test profile is used, HFP_SWB, HFP_WBS, or
                             HFP_NBS
        @param audio_config: the test specific audio config
        """
        apply_offload = self.will_apply_hfp_offload_path(
                self.hfp_force_offload)
        if self.hfp_force_offload and not apply_offload:
            raise error.TestNAError(
                    'The DUT does not support offload path. Skip the test.')

        logging.info('Test is running with {} path in use.'.format(
                'offload' if apply_offload else 'non-offload'))

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

        if self.hfp_force_offload:
            self.set_force_hfp_offload_on_support(True)

    def hfp_test_posttest(self):
        """Common procedure after running a HFP test."""
        # unset flags for testing purposes by finally clause to ensure they
        # will be executed under all circumstances.
        if self.hfp_force_offload:
            self.set_force_hfp_offload_on_support(False)

        # remove this flag toggle once it is enabled by default (b/308859926)
        # the DUT should always choose the best codec reported by the peer
        self.test_set_force_hfp_swb_enabled(False)

    def avrcp_test_pretest(self, device):
        """Common procedure before running an AVRCP test.

        @param device: the bt peer device.
        """
        self.initialize_bluetooth_player(device)
        self.enable_audio_stream_for_avrcp(device)

    def avrcp_test_posttest(self, device):
        """Common procedure before running an AVRCP test.

        @param device: the bt peer device.
        """
        self.stop_audio_stream_for_avrcp()
        self.cleanup_bluetooth_player(device)

    def audio_test_pretest(self,
                           test_profile,
                           test_name=None,
                           device_configs={},
                           use_all_peers=False,
                           supports_floss=False,
                           pair_device=False,
                           audio_config=None):
        """Common procedure before running a Bluetooth audio test.

        @param test_profile: which test profile is used,
                             A2DP, HFP_SWB, HFP_WBS or HFP_NBS
        @param test_name: the name of the test to log.
        @param device_configs: map of the device types and values
                               There are two possibilities of the values:
                               (1) the quantities needed for the test. For
                                   example, {'BLE_KEYBOARD':1,'BLE_MOUSE':1}.
                               (2) a tuple of tuples of required capabilities,
                                   e.g., devices={'BLUETOOTH_AUDIO':
                                                    (('PIPEWIRE', 'LE_AUDIO'),)}
                                   which requires a BLUETOOTH_AUDIO device with
                                   the capabilities of support PIPEWIRE and
                                   LE_AUDIO adapter.
        @param use_all_peers: Set number of devices to be used to the
                              maximum available. This is used for tests
                              like bluetooth_PeerVerify which uses all
                              available peers. Specify only one device type
                              if this is set to true.
        @param supports_floss: Does this test support running on Floss?
        @param pair_device: True to pair with and connect to the peer device,
                            False otherwise.
        @param audio_config: the test specific audio config.
        """
        self.audio_test_started = False
        self.quick_test_test_pretest(test_name, device_configs, use_all_peers,
                                     supports_floss)

        self.audio_test_started = True
        logging.debug('Running audio_test_pretest...')

        device = self.devices['BLUETOOTH_AUDIO'][0]

        if self.is_hfp_profile(test_profile):
            self.hfp_test_pretest(device, test_profile, audio_config)

        self.test_reset_on_adapter()
        self.test_bluetoothd_running()
        # This is necessary for OFONO to find the correct modem when querying
        # the bt peer call's state.
        device.SetRemoteAddress(self.bluetooth_facade.address)
        # TODO: b/277702522 remove this after bluetooth telephony launch.
        if self.floss:
            self.test_set_bluetooth_telephony(True)
        self.initialize_bluetooth_audio(device,
                                        test_profile,
                                        audio_config=audio_config)

        # Capture the btmon log to determine the codec used.
        # This is performed for the A2DP profile for now.
        # The HFP profile will be covered later.
        if self.is_a2dp_profile(test_profile):
            self.bluetooth_facade.btmon_start()

        self.dut_atlog_path = self.start_recording_atlog()

        if pair_device:
            self.test_device_set_discoverable(device, True)
            self.test_discover_device(device.address)

            self.test_pairing(device.address, device.pin, trusted=True)
            self.test_connection_by_adapter(device.address)

        if self.is_avrcp_profile(test_profile):
            self.avrcp_test_pretest(device)

    def audio_test_posttest(self, test_profile, disconnect_device=False):
        """Common procedure after running a Bluetooth audio test.

        @param test_profile: which test profile is used,
                             A2DP, HFP_SWB, HFP_WBS or HFP_NBS
        @param disconnect_device: True to disconnect device, False otherwise.
        """
        if self.audio_test_started:
            logging.debug('Running audio_test_posttest...')

            if not self.devices['BLUETOOTH_AUDIO']:
                logging.debug('No audio device was initialized, '
                              'skipping audio_test_posttest.')
                return

            device = self.devices['BLUETOOTH_AUDIO'][0]

            if self.is_avrcp_profile(test_profile):
                self.avrcp_test_posttest(device)

            if disconnect_device:
                self.test_disconnection_by_adapter(device.address)

            # Stop the btmon log and verify the codec.
            if self.is_a2dp_profile(test_profile):
                self.bluetooth_facade.btmon_stop()
                self.test_audio_codec()

            self.collect_audio_diagnostics()
            self.compress_and_collect_file(AUDIO_RECORD_DIR)

            if self.dut_atlog_path is not None:
                self.compress_and_collect_file(self.dut_atlog_path)

            self.host.run(f'pkill -f {self.CRAS_TEST_CLIENT}',
                          ignore_status=True)
            self.cleanup_bluetooth_audio(device, test_profile)

            if self.is_hfp_profile(test_profile):
                self.hfp_test_posttest()

        self.quick_test_test_posttest()

    def audio_test(
            test_name,
            test_profile,
            device_configs={},
            flags=['All'],
            allowed_boards=None,
            model_testNA=[],
            model_testWarn=[],
            skip_models=[],
            skip_chipsets=[],
            skip_common_errors=False,
            supports_floss=False,
            use_all_peers=False,
            minimum_kernel_version='',
            audio_config=None,
            pair_device=False,
    ):
        """A decorator providing a wrapper to an audio test.
           Using the decorator a test method can implement only the core
           test and let the decorator handle the audio test wrapper methods
           (reset/cleanup/logging).

        @param test_name: the name of the test to log.
        @param test_profile: Which test profile is used,
                             A2DP, A2DP_MEDIUM, HFP_WBS or HFP_NBS.
        @param device_configs: map of the device types and the quantities
                               needed for the test. For example,
                               {'BLE_KEYBOARD':1, 'BLE_MOUSE':1}.
        @param flags: list of string to describe who should run the
                      test. The string could be one of the following:
                      ['AVL', 'Quick Health', 'All'].
        @param allowed_boards: If not None, raises TestNA on boards that are
                               not in this set.
        @param model_testNA: If the current platform is in this list,
                             failures are emitted as TestNAError.
        @param model_testWarn: If the current platform is in this list,
                               failures are emitted as TestWarn.
        @param skip_models: Raises TestNA on these models and doesn't attempt
                            to run the tests.
        @param skip_chipsets: Raises TestNA on these chipset and doesn't
                              attempt to run the tests.
        @param skip_common_errors: If the test encounters a common error
                                   (such as USB disconnect or daemon crash),
                                   mark the test as TESTNA instead.
                                   USE THIS SPARINGLY, it may mask bugs. This
                                   is available for tests that require state
                                   to be properly retained throughout the
                                   whole test (i.e. advertising) and any
                                   outside failure will cause the test to
                                   fail.
        @param supports_floss: Does this test support running on Floss?
        @param use_all_peers: Set number of devices to be used to the
                              maximum available. This is used for tests
                              like bluetooth_PeerVerify which uses all
                              available peers. Specify only one device type
                              if this is set to true
        @param minimum_kernel_version: Raises TestNA on less than this
                                       kernel's version and doesn't attempt
                                       to run the tests.

        @param audio_config: the test specific audio config
        @param pair_device: True to pair with and connect to the peer device in
                            pretest, False otherwise.
        """
        return BluetoothAdapterQuickTests.quick_test_test_decorator(
                test_name,
                devices=device_configs,
                flags=flags,
                pretest_func=lambda self: self.audio_test_pretest(
                        test_profile=test_profile,
                        test_name=test_name,
                        device_configs=device_configs,
                        use_all_peers=use_all_peers,
                        supports_floss=supports_floss,
                        pair_device=pair_device,
                        audio_config=audio_config,
                ),
                posttest_func=lambda self: self.audio_test_posttest(
                        test_profile=test_profile,
                        disconnect_device=pair_device),
                allowed_boards=allowed_boards,
                model_testNA=model_testNA,
                model_testWarn=model_testWarn,
                skip_models=skip_models,
                skip_chipsets=skip_chipsets,
                skip_common_errors=skip_common_errors,
                supports_floss=supports_floss,
                use_all_peers=use_all_peers,
                minimum_kernel_version=minimum_kernel_version)

    @audio_test(test_name='A2DP sinewave test',
                test_profile=A2DP,
                device_configs={'BLUETOOTH_AUDIO': 1},
                supports_floss=True,
                pair_device=True)
    def au_a2dp_test(self):
        """A2DP test with sinewaves on the two channels."""
        device = self.devices['BLUETOOTH_AUDIO'][0]
        self.test_a2dp_sinewaves(device, A2DP)

    @audio_test(test_name='A2DP sinewave test with the AAC codec',
                test_profile=A2DP,
                device_configs={'BLUETOOTH_AUDIO': ((CAP_PIPEWIRE), )},
                supports_floss=True,
                audio_config={A2DP_CODEC: AAC},
                pair_device=True)
    def au_a2dp_aac_test(self):
        """A2DP test with sinewaves with the AAC codec."""
        device = self.devices['BLUETOOTH_AUDIO'][0]

        # TODO(b/308882924): remove this once it is enabled by default
        self.test_set_force_a2dp_advanced_codecs_enabled(True)
        self.test_a2dp_sinewaves(device, A2DP)
        self.test_set_force_a2dp_advanced_codecs_enabled(False)

    # The A2DP long test is a stress test. Exclude it from the AVL.
    @audio_test(test_name='A2DP sinewave long test',
                test_profile=A2DP_LONG,
                device_configs={'BLUETOOTH_AUDIO': 1},
                flags=['Quick Health'],
                supports_floss=True,
                pair_device=True)
    def au_a2dp_long_test(self, duration=600):
        """A2DP long test with sinewaves on the two channels.

        @param duration: the duration to test a2dp. The unit is in seconds.
        """
        device = self.devices['BLUETOOTH_AUDIO'][0]
        self.test_a2dp_sinewaves(device, A2DP_LONG, duration)


    # Remove flags=['Quick Health'] when this test is migrated to stable suite.
    @audio_test(test_name='A2DP rate 44100 sinewave test',
                test_profile=A2DP_RATE_44100,
                device_configs={'BLUETOOTH_AUDIO': 1},
                flags=['Quick Health'],
                supports_floss=True,
                pair_device=True)
    def au_a2dp_rate_44100_test(self):
        """A2DP test with sampling rate 44100 to emulate Intel THD+N tests."""
        device = self.devices['BLUETOOTH_AUDIO'][0]
        self.test_a2dp_sinewaves(device, A2DP_RATE_44100)

    @audio_test(test_name='A2DP playback and connect test',
                test_profile=A2DP_MEDIUM,
                device_configs={'BLUETOOTH_AUDIO': 1},
                supports_floss=True)
    def au_a2dp_playback_and_connect_test(self):
        """Connect then disconnect an A2DP device while playing stream."""
        if not has_internal_speaker(self.host):
            logging.info('SKIPPING TEST A2DP playback and connect test')
            raise error.TestNAError(
                    'The DUT does not have an internal speaker')

        device = self.devices['BLUETOOTH_AUDIO'][0]
        self.playback_and_connect(device, A2DP_MEDIUM)

    @audio_test(test_name='A2DP playback and disconnect test',
                test_profile=A2DP_MEDIUM,
                device_configs={'BLUETOOTH_AUDIO': 1},
                supports_floss=True)
    def au_a2dp_playback_and_disconnect_test(self):
        """Check the playback stream is still alive after BT disconnected."""
        device = self.devices['BLUETOOTH_AUDIO'][0]
        self.playback_and_disconnect(device, A2DP_MEDIUM)

    @audio_test(test_name='A2DP playback back2back test',
                test_profile=A2DP_MEDIUM,
                device_configs={'BLUETOOTH_AUDIO': 1},
                supports_floss=True)
    def au_a2dp_playback_back2back_test(self):
        """A2DP playback stream back to back test."""
        device = self.devices['BLUETOOTH_AUDIO'][0]
        self.playback_back2back(device, A2DP_MEDIUM)

    @audio_test(test_name='A2DP pinned playback test',
                test_profile=A2DP,
                device_configs={'BLUETOOTH_AUDIO': 1},
                supports_floss=True)
    def au_a2dp_pinned_playback_test(self):
        """Pinned playback stream test."""
        device = self.devices['BLUETOOTH_AUDIO'][0]
        self.pinned_playback(device, A2DP)

    @audio_test(test_name='HFP SWB sinewave test with dut as source',
                test_profile=HFP_SWB,
                device_configs={'BLUETOOTH_AUDIO': ((CAP_PIPEWIRE), )},
                supports_floss=True,
                audio_config={HFP_CODEC: LC3},
                pair_device=True)
    def au_hfp_swb_dut_as_source_test(self):
        """HFP SWB test with sinewave streaming from dut to peer."""
        device = self.devices['BLUETOOTH_AUDIO'][0]
        self.hfp_dut_as_source(device, HFP_SWB)

    @audio_test(test_name='HFP SWB sinewave test with dut as sink',
                test_profile=HFP_SWB,
                device_configs={'BLUETOOTH_AUDIO': ((CAP_PIPEWIRE), )},
                supports_floss=True,
                audio_config={HFP_CODEC: LC3},
                pair_device=True)
    def au_hfp_swb_dut_as_sink_test(self):
        """HFP SWB test with sinewave streaming from peer to dut."""
        device = self.devices['BLUETOOTH_AUDIO'][0]
        self.hfp_dut_as_sink(device,
                             HFP_SWB,
                             check_input_device_sample_rate=32000),

    @audio_test(test_name='HFP WBS sinewave test with dut as source',
                test_profile=HFP_WBS,
                device_configs={'BLUETOOTH_AUDIO': 1},
                supports_floss=True,
                pair_device=True)
    def au_hfp_wbs_dut_as_source_test(self):
        """HFP WBS test with sinewave streaming from dut to peer."""
        device = self.devices['BLUETOOTH_AUDIO'][0]
        self.hfp_dut_as_source(device, HFP_WBS)

    @audio_test(test_name='HFP WBS sinewave test with dut as sink',
                test_profile=HFP_WBS,
                device_configs={'BLUETOOTH_AUDIO': 1},
                supports_floss=True,
                pair_device=True)
    def au_hfp_wbs_dut_as_sink_test(self):
        """HFP WBS test with sinewave streaming from peer to dut."""
        device = self.devices['BLUETOOTH_AUDIO'][0]
        self.hfp_dut_as_sink(device,
                             HFP_WBS,
                             check_input_device_sample_rate=16000)

    @audio_test(test_name='HFP NBS sinewave test with dut as source',
                test_profile=HFP_NBS,
                device_configs={'BLUETOOTH_AUDIO': 1},
                supports_floss=True,
                pair_device=True)
    def au_hfp_nbs_dut_as_source_test(self):
        """HFP NBS test with sinewave streaming from dut to peer."""
        device = self.devices['BLUETOOTH_AUDIO'][0]
        self.hfp_dut_as_source(device, HFP_NBS)

    @audio_test(test_name='HFP NBS sinewave test with dut as sink',
                test_profile=HFP_NBS,
                device_configs={'BLUETOOTH_AUDIO': 1},
                supports_floss=True,
                pair_device=True)
    def au_hfp_nbs_dut_as_sink_test(self):
        """HFP NBS test with sinewave streaming from peer to dut."""
        device = self.devices['BLUETOOTH_AUDIO'][0]
        self.hfp_dut_as_sink(device,
                             HFP_NBS,
                             check_input_device_sample_rate=8000)

    @audio_test(test_name=
                'HFP NBS sinewave test with dut as sink with super resolution',
                test_profile=HFP_NBS,
                device_configs={'BLUETOOTH_AUDIO': 1},
                allowed_boards={
                        'eve',
                        'soraka',
                        'nautilus',
                        'nami',
                        'nocturne',
                        'rammus',
                        'fizz',
                },
                supports_floss=True,
                pair_device=True)
    def au_hfp_nbs_dut_as_sink_with_super_resolution_test(self):
        """HFP NBS test with sinewave and super_resolution streaming from peer to dut."""
        device = self.devices['BLUETOOTH_AUDIO'][0]
        # Enabling ui is needed, or the downloading in dlc service won't work.
        self.hfp_dut_as_sink_with_super_resolution(device, HFP_NBS)

    @audio_test(test_name='HFP WBS VISQOL test with dut as sink',
                test_profile=HFP_WBS,
                device_configs={'BLUETOOTH_AUDIO': 1},
                supports_floss=True,
                pair_device=True)
    def au_hfp_wbs_dut_as_sink_visqol_test(self):
        """HFP WBS VISQOL test with audio streaming from peer to dut"""
        device = self.devices['BLUETOOTH_AUDIO'][0]
        self.hfp_dut_as_sink_visqol_score(device, HFP_WBS)

    @audio_test(test_name='HFP WBS VISQOL test with dut as source',
                test_profile=HFP_WBS,
                device_configs={'BLUETOOTH_AUDIO': 1},
                supports_floss=True,
                pair_device=True)
    def au_hfp_wbs_dut_as_source_visqol_test(self):
        """HFP WBS VISQOL test with audio streaming from dut to peer"""
        device = self.devices['BLUETOOTH_AUDIO'][0]
        self.hfp_dut_as_source_visqol_score(device, HFP_WBS)

    @audio_test(test_name='HFP NBS VISQOL test with dut as sink',
                test_profile=HFP_NBS,
                device_configs={'BLUETOOTH_AUDIO': 1},
                supports_floss=True,
                pair_device=True)
    def au_hfp_nbs_dut_as_sink_visqol_test(self):
        """HFP NBS VISQOL test with audio streaming from peer to dut"""
        device = self.devices['BLUETOOTH_AUDIO'][0]
        self.hfp_dut_as_sink_visqol_score(device, HFP_NBS)

    @audio_test(test_name='HFP NBS VISQOL test with dut as source',
                test_profile=HFP_NBS,
                device_configs={'BLUETOOTH_AUDIO': 1},
                supports_floss=True,
                pair_device=True)
    def au_hfp_nbs_dut_as_source_visqol_test(self):
        """HFP NBS VISQOL test with audio streaming from dut to peer"""
        device = self.devices['BLUETOOTH_AUDIO'][0]
        self.hfp_dut_as_source_visqol_score(device, HFP_NBS)

    @audio_test(test_name='HFP NBS back2back test with dut as source',
                test_profile=HFP_NBS,
                device_configs={'BLUETOOTH_AUDIO': 1},
                supports_floss=True,
                pair_device=True)
    def au_hfp_nbs_dut_as_source_back2back_test(self):
        """HFP NBS back2back test from dut to peer"""
        device = self.devices['BLUETOOTH_AUDIO'][0]
        self.hfp_dut_as_source_back2back(device, HFP_NBS)

    @audio_test(test_name='HFP WBS back2back test with dut as source',
                test_profile=HFP_WBS,
                device_configs={'BLUETOOTH_AUDIO': 1},
                supports_floss=True,
                pair_device=True)
    def au_hfp_wbs_dut_as_source_back2back_test(self):
        """HFP WBS back2back test from dut to peer"""
        device = self.devices['BLUETOOTH_AUDIO'][0]
        self.hfp_dut_as_source_back2back(device, HFP_WBS)

    @audio_test(test_name='Switch A2DP to HFP NBS test with dut as source',
                test_profile=HFP_NBS_MEDIUM,
                device_configs={'BLUETOOTH_AUDIO': 1},
                supports_floss=True,
                pair_device=True)
    def au_a2dp_to_hfp_nbs_dut_as_source_test(self):
        """Switch A2DP to HFP NBS test with dut as source."""
        device = self.devices['BLUETOOTH_AUDIO'][0]
        self.a2dp_to_hfp_dut_as_source(device, HFP_NBS_MEDIUM)

    @audio_test(test_name='Switch A2DP to HFP WBS test with dut as source',
                test_profile=HFP_WBS_MEDIUM,
                device_configs={'BLUETOOTH_AUDIO': 1},
                supports_floss=True,
                pair_device=True)
    def au_a2dp_to_hfp_wbs_dut_as_source_test(self):
        """Switch A2DP to HFP WBS test with dut as source."""
        device = self.devices['BLUETOOTH_AUDIO'][0]
        self.a2dp_to_hfp_dut_as_source(device, HFP_WBS_MEDIUM)

    @audio_test(test_name='Switch HFP NBS to A2DP test with dut as source',
                test_profile=HFP_NBS_MEDIUM,
                device_configs={'BLUETOOTH_AUDIO': 1},
                supports_floss=True,
                pair_device=True)
    def au_hfp_nbs_to_a2dp_dut_as_source_test(self):
        """Switch HFP NBS to A2DP test with dut as source."""
        device = self.devices['BLUETOOTH_AUDIO'][0]
        self.hfp_to_a2dp_dut_as_source(device, HFP_NBS_MEDIUM)

    @audio_test(test_name='Switch HFP WBS to A2DP test with dut as source',
                test_profile=HFP_WBS_MEDIUM,
                device_configs={'BLUETOOTH_AUDIO': 1},
                supports_floss=True,
                pair_device=True)
    def au_hfp_wbs_to_a2dp_dut_as_source_test(self):
        """Switch HFP WBS to A2DP test with dut as source."""
        device = self.devices['BLUETOOTH_AUDIO'][0]
        self.hfp_to_a2dp_dut_as_source(device, HFP_WBS_MEDIUM)

    @audio_test(test_name='Trigger incoming call on dut and answer call',
                test_profile=HFP_TELEPHONY,
                device_configs={'BLUETOOTH_AUDIO': 1},
                supports_floss=True,
                pair_device=True)
    def au_hfp_telephony_incoming_call_answer_call_test(self):
        """Trigger incoming call on dut and answer call."""
        device = self.devices['BLUETOOTH_AUDIO'][0]
        self.hfp_telephony_incoming_call_answer_call(device)

    @audio_test(test_name='Trigger incoming call on dut and reject call',
                test_profile=HFP_TELEPHONY,
                device_configs={'BLUETOOTH_AUDIO': 1},
                supports_floss=True,
                pair_device=True)
    def au_hfp_telephony_incoming_call_reject_call_test(self):
        """Trigger incoming call on dut and reject call."""
        device = self.devices['BLUETOOTH_AUDIO'][0]
        self.hfp_telephony_incoming_call_reject_call(device)

    @audio_test(test_name='Place an active call on dut and hangup call',
                test_profile=HFP_TELEPHONY,
                device_configs={'BLUETOOTH_AUDIO': 1},
                supports_floss=True,
                pair_device=True)
    def au_hfp_telephony_active_call_hangup_call_test(self):
        """Place an active call on dut and hangup call."""
        device = self.devices['BLUETOOTH_AUDIO'][0]
        self.hfp_telephony_active_call_hangup_call(device)

    @audio_test(test_name='Trigger microphone mute and unmute',
                test_profile=HFP_TELEPHONY,
                device_configs={'BLUETOOTH_AUDIO': 1},
                supports_floss=True,
                pair_device=True)
    def au_hfp_telephony_micmute_test(self):
        """Trigger microphone mute and unmute"""
        device = self.devices['BLUETOOTH_AUDIO'][0]
        self.hfp_telephony_micmute(device)

    @audio_test(test_name='avrcp command test',
                test_profile=AVRCP,
                device_configs={'BLUETOOTH_AUDIO': 1},
                supports_floss=True,
                pair_device=True)
    def au_avrcp_command_test(self):
        """AVRCP test to examine commands reception."""
        device = self.devices['BLUETOOTH_AUDIO'][0]
        self.test_avrcp_commands(device)

    @audio_test(test_name='avrcp media info test',
                test_profile=AVRCP,
                device_configs={'BLUETOOTH_AUDIO': 1},
                supports_floss=True,
                pair_device=True)
    def au_avrcp_media_info_test(self):
        """AVRCP test to examine metadata propgation."""
        device = self.devices['BLUETOOTH_AUDIO'][0]
        self.test_avrcp_media_info(device)


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
                 enable_ui=False,
                 hfp_force_offload=False):
        """Run the batch of Bluetooth stand health tests

        @param host: the DUT, usually a chromebook
        @param num_iterations: the number of rounds to execute the test
        @param test_name: the test to run, or None for all tests
        """

        self.quick_test_init(host,
                             use_btpeer=True,
                             flag=flag,
                             args_dict=args_dict,
                             floss=floss,
                             enable_cellular=enable_cellular,
                             enable_ui=enable_ui,
                             hfp_force_offload=hfp_force_offload)
        self.au_health_batch_run(num_iterations, test_name)
        self.quick_test_cleanup()
