# Copyright 2020 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Server side Bluetooth audio tests."""

import logging
import time

from autotest_lib.client.bin import utils
from autotest_lib.client.common_lib import error
from autotest_lib.client.cros.bluetooth.bluetooth_audio_test_data import (
        A2DP, HFP_WBS, HFP_NBS, audio_test_data)
from autotest_lib.server.cros.bluetooth.bluetooth_adapter_tests import (
        BluetoothAdapterTests, test_retry_and_log)


class BluetoothAdapterAudioTests(BluetoothAdapterTests):
    """Server side Bluetooth adapter audio test class."""

    DEVICE_TYPE = 'BLUETOOTH_AUDIO'
    FREQUENCY_TOLERANCE_RATIO = 0.01
    WAIT_DAEMONS_READY_SECS = 1

    def _get_pulseaudio_bluez_source(self, get_source_method, device):
        """Get the specified bluez device number in the pulseaudio source list.

        @param get_source_method: the method to get distinct bluez source
        @param device: the bluetooth peer device

        @returns: True if the specified bluez source is derived
        """
        sources = device.ListSources()
        logging.debug('ListSources()\n%s', sources)
        self.bluez_source = get_source_method()
        result = bool(self.bluez_source)
        if result:
            logging.debug('bluez_source device number: %s', self.bluez_source)
        else:
            logging.debug('waiting for bluez_source ready in pulseaudio...')
        return result


    def _get_pulseaudio_bluez_sink(self, get_sink_method, device):
        """Get the specified bluez device number in the pulseaudio sink list.

        @param get_sink_method: the method to get distinct bluez sink
        @param device: the bluetooth peer device

        @returns: True if the specified bluez sink is derived
        """
        sinks = device.ListSinks()
        logging.debug('ListSinks()\n%s', sinks)
        self.bluez_sink = get_sink_method()
        result = bool(self.bluez_sink)
        if result:
            logging.debug('bluez_sink device number: %s', self.bluez_sink)
        else:
            logging.debug('waiting for bluez_sink ready in pulseaudio...')
        return result


    def _get_pulseaudio_bluez_source_a2dp(self, device):
        """Get the a2dp bluez source device number.

        @param device: the bluetooth peer device

        @returns: True if the specified a2dp bluez source is derived
        """
        return self._get_pulseaudio_bluez_source(
                device.GetBluezSourceA2DPDevice, device)


    def _get_pulseaudio_bluez_source_hfp(self, device):
        """Get the hfp bluez source device number.

        @param device: the bluetooth peer device

        @returns: True if the specified hfp bluez source is derived
        """
        return self._get_pulseaudio_bluez_source(
                device.GetBluezSourceHFPDevice, device)


    def _get_pulseaudio_bluez_sink_hfp(self, device):
        """Get the hfp bluez sink device number.

        @param device: the bluetooth peer device

        @returns: True if the specified hfp bluez sink is derived
        """
        return self._get_pulseaudio_bluez_sink(
                device.GetBluezSinkHFPDevice, device)


    def _check_audio_frames_legitimacy(self, audio_test_data, recording_device):
        """Check if audio frames in the recorded file are legitimate.

        For a wav file, a simple check is to make sure the recorded audio file
        is not empty.

        For a raw file, a simple check is to make sure the recorded audio file
        are not all zeros.

        @param audio_test_data: a dictionary about the audio test data
                defined in client/cros/bluetooth/bluetooth_audio_test_data.py
        @param recording_device: which device recorded the audio,
                possible values are 'recorded_by_dut' or 'recorded_by_peer'

        @returns: True if audio frames are legitimate.
        """
        result = self.bluetooth_facade.check_audio_frames_legitimacy(
                audio_test_data, recording_device)
        if not result:
            self.results = {'audio_frames_legitimacy': 'empty or all zeros'}
            logging.error('The recorded audio file is empty or all zeros.')
        return result


    def _check_frequency(self, recorded_freq, expected_freq):
        """Check if the recorded frequency is within tolerance.

        @param recorded_freq: the frequency of recorded audio
        @param expected_freq: the expected frequency

        @returns: True if the recoreded frequency falls within the tolerance of
                  the expected frequency
        """
        tolerance = expected_freq * self.FREQUENCY_TOLERANCE_RATIO
        return abs(expected_freq - recorded_freq) <= tolerance


    def _check_primary_frequencies(self, audio_test_data, recording_device):
        """Check if the recorded frequencies meet expectation.

        @param audio_test_data: a dictionary about the audio test data
                defined in client/cros/bluetooth/bluetooth_audio_test_data.py
        @param recording_device: which device recorded the audio,
                possible values are 'recorded_by_dut' or 'recorded_by_peer'

        @returns: True if the recorded frequencies of all channels fall within
                the tolerance of expected frequencies
        """
        recorded_frequencies = self.bluetooth_facade.get_primary_frequencies(
                audio_test_data, recording_device)
        expected_frequencies = audio_test_data['frequencies']
        final_result = True
        self.results = dict()

        if len(recorded_frequencies) < len(expected_frequencies):
            logging.error('recorded_frequencies: %s, expected_frequencies: %s',
                          str(recorded_frequencies), str(expected_frequencies))
            final_result = False
        else:
            for channel, expected_freq in enumerate(expected_frequencies):
                recorded_freq = recorded_frequencies[channel]
                ret_val = self._check_frequency(recorded_freq, expected_freq)
                pass_fail_str = 'pass' if ret_val else 'fail'
                result = ('primary frequency %d (expected %d): %s' %
                          (recorded_freq, expected_freq, pass_fail_str))
                self.results['Channel %d' % channel] = result
                logging.info('Channel %d: %s', channel, result)

                if not ret_val:
                    final_result = False

        logging.debug(str(self.results))
        if not final_result:
            logging.error('Failure at checking primary frequencies')
        return final_result


    def _poll_for_condition(self, condition, timeout=20, sleep_interval=1,
                            desc='waiting for condition'):
        try:
            utils.poll_for_condition(condition=condition,
                                     timeout=timeout,
                                     sleep_interval=sleep_interval,
                                     desc=desc)
        except Exception as e:
            raise error.TestError('Exception occurred when %s' % desc)


    def initialize_bluetooth_audio(self, device, test_profile):
        """Initialize the Bluetooth audio task.

        Note: pulseaudio is not stable. Need to restart it in the beginning.

        @param device: the bluetooth peer device

        """
        if not device.StartPulseaudio():
            raise error.TestError('Failed to start pulseaudio.')
        logging.debug('pulseaudio is started.')

        if test_profile in (HFP_WBS, HFP_NBS):
            if device.StartOfono():
                logging.debug('ofono is started.')
            else:
                raise error.TestError('Failed to start ofono.')
        elif device.StopOfono():
            logging.debug('ofono is stopped.')
        else:
            logging.warn('Failed to stop ofono. Ignored.')

        # Need time to complete starting services.
        time.sleep(self.WAIT_DAEMONS_READY_SECS)


    def cleanup_bluetooth_audio(self, device, test_profile):
        """Cleanup for Bluetooth audio.

        @param device: the bluetooth peer device

        """
        if device.StopPulseaudio():
            logging.debug('pulseaudio is stopped.')
        else:
            logging.warn('Failed to stop pulseaudio. Ignored.')

        if device.StopOfono():
            logging.debug('ofono is stopped.')
        else:
            logging.warn('Failed to stop ofono. Ignored.')


    # ---------------------------------------------------------------
    # Definitions of all bluetooth audio test cases
    # ---------------------------------------------------------------


    @test_retry_and_log(False)
    def test_a2dp_sinewaves(self, device):
        """Test Case: a2dp sinewaves

        @param device: the bluetooth peer device

        @returns: True if the recorded primary frequency is within the
                  tolerance of the playback sine wave frequency.

        """
        a2dp_test_data = audio_test_data[A2DP]

        # Wait for pulseaudio bluez hfp source
        desc='waiting for pulseaudio a2dp bluez source'
        logging.debug(desc)
        self._poll_for_condition(
                lambda: self._get_pulseaudio_bluez_source_a2dp(device),
                desc=desc)

        # Start recording audio on the peer Bluetooth audio device.
        logging.debug('Start recording a2dp')
        if not device.StartRecordingAudioSubprocess('a2dp'):
            raise error.TestError(
                    'Failed to record on the peer Bluetooth audio device.')

        # Play stereo audio on the DUT.
        logging.debug('Play audio')
        if not self.bluetooth_facade.play_audio(a2dp_test_data):
            raise error.TestError('DUT failed to play audio.')

        # Stop recording audio on the peer Bluetooth audio device.
        logging.debug('Stop recording a2dp')
        if not device.StopRecordingingAudioSubprocess():
            msg = 'Failed to stop recording on the peer Bluetooth audio device'
            logging.error(msg)

        # Copy the recorded audio file to the DUT for spectrum analysis.
        logging.debug('Scp recorded file')
        recorded_file = a2dp_test_data['recorded_by_peer']
        device.ScpToDut(recorded_file, recorded_file, self.host.ip)

        # Check if the audio frames in the recorded file are legitimate.
        if not self._check_audio_frames_legitimacy(a2dp_test_data,
                                                   'recorded_by_peer'):
            return False

        # Check if the primary frequencies of recorded file meet expectation.
        check_freq_result = self._check_primary_frequencies(a2dp_test_data,
                                                            'recorded_by_peer')
        return check_freq_result


    @test_retry_and_log(False)
    def test_hfp_dut_as_source(self, device, test_profile):
        """Test Case: hfp sinewave streaming from dut to peer device

        @param device: the bluetooth peer device
        @param test_profile: which test profile is used, HFP_WBS or HFP_NBS

        @returns: True if the recorded primary frequency is within the
                  tolerance of the playback sine wave frequency.

        """
        hfp_test_data = audio_test_data[test_profile]

        # Select audio input device.
        desc='waiting for cras to select audio input device'
        logging.debug(desc)
        self._poll_for_condition(
                lambda: self.bluetooth_facade.select_input_device(device.name),
                desc=desc)

        # Enable HFP profile.
        logging.debug('Start recording audio on DUT')
        if not self.bluetooth_facade.start_capturing_audio_subprocess(
                hfp_test_data, 'recorded_by_peer'):
            raise error.TestError('Peer failed to start capturing audio.')

        # Wait for pulseaudio bluez hfp source
        desc='waiting for pulseaudio bluez hfp source'
        logging.debug(desc)
        self._poll_for_condition(
                lambda: self._get_pulseaudio_bluez_source_hfp(device),
                desc=desc)

        logging.debug('Start recording audio on Pi')
        # Start recording audio on the peer Bluetooth audio device.
        if not device.StartRecordingAudioSubprocess(test_profile):
            raise error.TestError(
                    'Failed to record on the peer Bluetooth audio device.')

        # Play audio on the DUT in a non-blocked way.
        # If there are issues, cras_test_client playing back might be blocked
        # forever. We would like to avoid the testing procedure from that.
        logging.debug('Start playing audio')
        if not self.bluetooth_facade.start_playing_audio_subprocess(
                hfp_test_data):
            raise error.TestError('DUT failed to play audio.')

        time.sleep(hfp_test_data['duration'])

        logging.debug('Stop recording audio on Pi')
        # Stop recording audio on the peer Bluetooth audio device.
        if not device.StopRecordingingAudioSubprocess():
            msg = 'Failed to stop recording on the peer Bluetooth audio device'
            logging.error(msg)

        # Disable HFP profile.
        logging.debug('Stop recording audio on DUT')
        if not self.bluetooth_facade.stop_capturing_audio_subprocess():
            raise error.TestError('DUT failed to stop capturing audio.')

        # Stop playing audio on DUT.
        logging.debug('Stop playing audio on DUT')
        if not self.bluetooth_facade.stop_playing_audio_subprocess():
            raise error.TestError('DUT failed to stop playing audio.')

        # Copy the recorded audio file to the DUT for spectrum analysis.
        logging.debug('Scp to DUT')
        recorded_file = hfp_test_data['recorded_by_peer']
        device.ScpToDut(recorded_file, recorded_file, self.host.ip)

        # Check if the audio frames in the recorded file are legitimate.
        if not self._check_audio_frames_legitimacy(hfp_test_data,
                                                   'recorded_by_peer'):
            return False

        # Check if the primary frequencies of recorded file meet expectation.
        check_freq_result = self._check_primary_frequencies(hfp_test_data,
                                                            'recorded_by_peer')
        return check_freq_result


    @test_retry_and_log(False)
    def test_hfp_dut_as_sink(self, device, test_profile):
        """Test Case: hfp sinewave streaming from peer device to dut

        @param device: the bluetooth peer device
        @param test_profile: which test profile is used, HFP_WBS or HFP_NBS

        @returns: True if the recorded primary frequency is within the
                  tolerance of the playback sine wave frequency.

        """
        hfp_test_data = audio_test_data[test_profile]

        # Select audio input device.
        desc='waiting for cras to select audio input device'
        logging.debug(desc)
        self._poll_for_condition(
                lambda: self.bluetooth_facade.select_input_device(device.name),
                desc=desc)

        # Enable HFP profile.
        logging.debug('Start recording audio on DUT')
        if not self.bluetooth_facade.start_capturing_audio_subprocess(
                hfp_test_data, 'recorded_by_dut'):
            raise error.TestError('DUT failed to start capturing audio.')

        # Wait for pulseaudio bluez hfp source
        desc='waiting for pulseaudio bluez hfp sink'
        logging.debug(desc)
        self._poll_for_condition(
                lambda: self._get_pulseaudio_bluez_sink_hfp(device), desc=desc)

        # Select audio input device.
        logging.debug('Select input device')
        if not self.bluetooth_facade.select_input_device(device.name):
            raise error.TestError('DUT failed to select audio input device.')

        # Start playing audio on chameleon.
        logging.debug('Start playing audio on Pi')
        if not device.StartPlayingAudioSubprocess(test_profile):
            err = 'Failed to start playing audio file on the peer device'
            raise error.TestError(err)

        time.sleep(hfp_test_data['duration'])

        # Stop playing audio on chameleon.
        logging.debug('Stop playing audio on Pi')
        if not device.StopPlayingAudioSubprocess():
            err = 'Failed to stop playing audio on the peer device'
            raise error.TestError(err)

        # Disable HFP profile.
        logging.debug('Stop recording audio on DUT')
        if not self.bluetooth_facade.stop_capturing_audio_subprocess():
            raise error.TestError('DUT failed to stop capturing audio.')

        # Check if the audio frames in the recorded file are legitimate.
        if not self._check_audio_frames_legitimacy(hfp_test_data,
                                                   'recorded_by_dut'):
            return False

        # Check if the primary frequencies of recorded file meet expectation.
        check_freq_result = self._check_primary_frequencies(hfp_test_data,
                                                            'recorded_by_dut')
        return check_freq_result
