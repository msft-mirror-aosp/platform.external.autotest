# Lint as: python2, python3
# Copyright 2020 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Server side Bluetooth audio tests."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import logging
import os
import re
import subprocess
import time

import common
from autotest_lib.client.bin import utils
from autotest_lib.client.common_lib import error
from autotest_lib.client.common_lib.cros.network import interface
from autotest_lib.client.cros.bluetooth.bluetooth_audio_test_data import (
        A2DP, HFP_NBS, HFP_NBS_MEDIUM, HFP_WBS, HFP_WBS_MEDIUM, HFP_TELEPHONY,
        AUDIO_DATA_TARBALL_PATH, VISQOL_BUFFER_LENGTH, DATA_DIR, VISQOL_PATH,
        VISQOL_SIMILARITY_MODEL, VISQOL_TEST_DIR, AUDIO_RECORD_DIR,
        AUDIO_SERVER, PULSEAUDIO, PIPEWIRE, A2DP_CODEC, SBC, AAC, HFP_CODEC,
        LC3, audio_test_data, get_audio_test_data, get_visqol_binary)
from autotest_lib.server.cros.bluetooth.bluetooth_adapter_tests import (
        FLOSS_NO_WBS_CHIPSETS, BluetoothAdapterTests, test_retry_and_log)
from six.moves import range


class BluetoothAdapterAudioTests(BluetoothAdapterTests):
    """Server side Bluetooth adapter audio test class."""

    DEVICE_TYPE = 'BLUETOOTH_AUDIO'
    FREQUENCY_TOLERANCE_RATIO = 0.01
    WAIT_DAEMONS_READY_SECS = 1
    DEFAULT_CHUNK_IN_SECS = 1
    IGNORE_LAST_FEW_CHUNKS = 2

    # Useful constant for upsampling NBS files for compatibility with ViSQOL
    MIN_VISQOL_SAMPLE_RATE = 16000

    # The node types of the bluetooth output nodes in cras are the same for both
    # A2DP and HFP.
    CRAS_BLUETOOTH_OUTPUT_NODE_TYPE = 'BLUETOOTH'
    CRAS_INTERNAL_SPEAKER_OUTPUT_NODE_TYPE = 'INTERNAL_SPEAKER'

    # Human readable strings describing the current connection state
    CONNECTION_STATE_DISCONNECTED = 'BT_disconnected'
    CONNECTION_STATE_CONNECTED = 'BT_connected_but_not_streaming'
    CONNECTION_STATE_STREAMING =  'BT_streaming_audiofile'
    CONNECTION_STATE_DISCONNECTED_AGAIN = 'BT_disconnected_again'
    CONNECTION_STATE_QUIET = 'BT_quiet'
    CONNECTION_STATE_SCANNING = 'BT_scanning'
    CONNECTION_STATE_QUIET_AGAIN = 'BT_quiet_again'

    DEFAULT_AUDIO_CONFIG = {AUDIO_SERVER: PULSEAUDIO, A2DP_CODEC: SBC}

    # This is temporary. All codecs will be served by PIPEWIRE eventually.
    AUDIO_SERVER_CHOICE = {SBC: PULSEAUDIO, AAC: PIPEWIRE, LC3: PIPEWIRE}

    # Regex to find ACL data event time for Bluetooth A2DP audio packets in
    # btmon log, e.g.
    # ACL Data RX: Handle 12 flags 0x02 dlen 612
    # #700 [hci0] 2024-02-12 10:57:10.947278
    #   Channel: 64 len 608 [PSM 25 mode Basic (0x00)] {chan 0}
    # PSM with value 25 was taken from this reference:
    # https://btprodspecificationrefs.blob.core.windows.net/assigned-numbers/Assigned%20Number%20Types/Assigned_Numbers.pdf
    A2DP_DUT_NOTIFICATION_REGEX = (r"ACL Data TX: Handle {} .*\[hci\d+\] ("
                                   r"\d+-\d+-\d+ \d+:\d+:\d+\.\d+)\s.*PSM 25")
    # Regex to find ACL data event time for Bluetooth peer A2DP audio packets in
    # btmon log, e.g.
    # ACL Data RX: H.. 12 flags 0x02 dlen 612
    # #700 [hci0] 2024-02-12 10:57:10.947278
    #   Channel: 64 len 608 [PSM 25 mode Basic (0x00)] {chan 0}
    # PSM with value 25 was taken from this reference:
    # https://btprodspecificationrefs.blob.core.windows.net/assigned-numbers/Assigned%20Number%20Types/Assigned_Numbers.pdf
    A2DP_PEER_NOTIFICATION_REGEX = (r"ACL Data RX.*\[hci\d+\] ("
                                    r"\d+-\d+-\d+ \d+:\d+:\d+\.\d+)\s.*PSM 25")

    # Boards which only have the offload path available for BT HFP.
    BOARDS_OFFLOAD_ONLY_FOR_HFP = ['kukui', 'jacuzzi', 'corsola', 'staryu']

    # The real IP replacent when used in ssh tunneling environment
    real_ip = None

    def _get_pulseaudio_bluez_source(self, get_source_method, device,
                                     test_profile):
        """Get the specified bluez device number in the pulseaudio source list.

        @param get_source_method: the method to get distinct bluez source
        @param device: the bluetooth peer device
        @param test_profile: the test profile used, A2DP, HFP_WBS or HFP_NBS

        @returns: True if the specified bluez source is derived
        """
        sources = device.ListSources(test_profile)
        logging.debug('ListSources()\n%s', sources)
        self.bluez_source = get_source_method(test_profile)
        result = bool(self.bluez_source)
        if result:
            logging.debug('bluez_source device number: %s', self.bluez_source)
        else:
            logging.debug('waiting for bluez_source ready in pulseaudio...')
        return result


    def _get_pulseaudio_bluez_sink(self, get_sink_method, device, test_profile):
        """Get the specified bluez device number in the pulseaudio sink list.

        @param get_sink_method: the method to get distinct bluez sink
        @param device: the bluetooth peer device
        @param test_profile: the test profile used, A2DP, HFP_WBS or HFP_NBS

        @returns: True if the specified bluez sink is derived
        """
        sinks = device.ListSinks(test_profile)
        logging.debug('ListSinks()\n%s', sinks)
        self.bluez_sink = get_sink_method(test_profile)
        result = bool(self.bluez_sink)
        if result:
            logging.debug('bluez_sink device number: %s', self.bluez_sink)
        else:
            logging.debug('waiting for bluez_sink ready in pulseaudio...')
        return result


    def _get_pulseaudio_bluez_source_a2dp(self, device, test_profile):
        """Get the a2dp bluez source device number.

        @param device: the bluetooth peer device
        @param test_profile: the test profile used, A2DP, HFP_WBS or HFP_NBS

        @returns: True if the specified a2dp bluez source is derived
        """
        return self._get_pulseaudio_bluez_source(
                device.GetBluezSourceA2DPDevice, device, test_profile)


    def _get_pulseaudio_bluez_source_hfp(self, device, test_profile):
        """Get the hfp bluez source device number.

        @param device: the bluetooth peer device
        @param test_profile: the test profile used, A2DP, HFP_WBS or HFP_NBS

        @returns: True if the specified hfp bluez source is derived
        """
        return self._get_pulseaudio_bluez_source(
                device.GetBluezSourceHFPDevice, device, test_profile)


    def _get_pulseaudio_bluez_sink_hfp(self, device, test_profile):
        """Get the hfp bluez sink device number.

        @param device: the bluetooth peer device
        @param test_profile: the test profile used, A2DP, HFP_WBS or HFP_NBS

        @returns: True if the specified hfp bluez sink is derived
        """
        return self._get_pulseaudio_bluez_sink(
                device.GetBluezSinkHFPDevice, device, test_profile)


    def _check_audio_frames_legitimacy(self, audio_test_data, recording_device,
                                       recorded_file=None):
        """Check if audio frames in the recorded file are legitimate.

        For a wav file, a simple check is to make sure the recorded audio file
        is not empty.

        For a raw file, a simple check is to make sure the recorded audio file
        are not all zeros.

        @param audio_test_data: a dictionary about the audio test data
                defined in client/cros/bluetooth/bluetooth_audio_test_data.py
        @param recording_device: which device recorded the audio,
                possible values are 'recorded_by_dut' or 'recorded_by_peer'
        @param recorded_file: the recorded file name

        @returns: True if audio frames are legitimate.
        """
        result = self.bluetooth_facade.check_audio_frames_legitimacy(
                audio_test_data, recording_device, recorded_file)
        if not result:
            self.results = {'audio_frames_legitimacy': 'empty or all zeros'}
            logging.error('The recorded audio file is empty or all zeros.')
        return result


    def _check_frequency(self, test_profile, recorded_freq, expected_freq):
        """Check if the recorded frequency is within tolerance.

        @param test_profile: the test profile used, A2DP, HFP_WBS or HFP_NBS
        @param recorded_freq: the frequency of recorded audio
        @param expected_freq: the expected frequency

        @returns: True if the recoreded frequency falls within the tolerance of
                  the expected frequency
        """
        tolerance = expected_freq * self.FREQUENCY_TOLERANCE_RATIO
        return abs(expected_freq - recorded_freq) <= tolerance


    def _check_primary_frequencies(self, test_profile, audio_test_data,
                                   recording_device, recorded_file=None):
        """Check if the recorded frequencies meet expectation.

        @param test_profile: the test profile used, A2DP, HFP_WBS or HFP_NBS
        @param audio_test_data: a dictionary about the audio test data
                defined in client/cros/bluetooth/bluetooth_audio_test_data.py
        @param recording_device: which device recorded the audio,
                possible values are 'recorded_by_dut' or 'recorded_by_peer'
        @param recorded_file: the recorded file name

        @returns: True if the recorded frequencies of all channels fall within
                the tolerance of expected frequencies
        """
        recorded_frequencies = self.bluetooth_facade.get_primary_frequencies(
                audio_test_data, recording_device, recorded_file)
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
                ret_val = self._check_frequency(
                        test_profile, recorded_freq, expected_freq)
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

    def _get_real_ip(self):
        # Localhost is unlikely to be the correct ip target so take the local
        # host ip if it exists.
        # When used ssh tunneling i.e. from cloudtop we need to provide
        # DUT ip
        if self.real_ip is None:
            if self.host.ip in ('127.0.0.1', 'localhost', '::1'):
                if self.local_host_ip:
                    self.real_ip = self.local_host_ip
                    logging.info('Using local host ip = %s', self.real_ip)
                else:
                    dut_if = interface.Interface.get_connected_ethernet_interface(
                        host=self.host)
                    self.real_ip = dut_if.ipv4_address
                    logging.info('Using DUT ip = %s', self.real_ip)
            else:
                self.real_ip = self.host.ip


    def _poll_for_condition(self, condition, timeout=20, sleep_interval=1,
                            desc='waiting for condition'):
        try:
            utils.poll_for_condition(condition=condition,
                                     timeout=timeout,
                                     sleep_interval=sleep_interval,
                                     desc=desc)
        except Exception as e:
            raise error.TestError('Exception occurred when %s (%s)' % (desc, e))

    def _scp_to_dut(self, device, src_file, dest_file):
        """SCP file from peer device to DuT."""
        self._get_real_ip()

        device.ScpToDut(src_file, dest_file, self.real_ip)

    def _create_call_state(self,
                           active=0,
                           held=0,
                           dialing=0,
                           alerting=0,
                           incoming=0,
                           waiting=0,
                           disconnected=0):
        """"create call state dictionary"""
        return {
                "active": active,
                "held": held,
                "dialing": dialing,
                "alerting": alerting,
                "incoming": incoming,
                "waiting": waiting,
                "disconnected": disconnected
        }

    def check_wbs_capability(self):
        """Check if the DUT supports WBS capability.

        @raises: TestNAError if the dut does not support wbs.
        """
        # For floss we don't check the supported_capabilities since eventually
        # WBS is determined by CRAS.
        if self.floss:
            chipset = self.bluetooth_facade.get_chipset_name()
            return not chipset in FLOSS_NO_WBS_CHIPSETS

        capabilities, err = self.bluetooth_facade.get_supported_capabilities()
        logging.debug("get_supported_capabilities %s", capabilities)
        return err is None and bool(capabilities.get('wide band speech'))

    def check_swb_capability(self):
        """Check if the DUT supports SWB capability.

        @returns True if supported, False otherwise
        """
        return self.bluetooth_facade.is_swb_supported()

    def collect_audio_diagnostics(self, filename='audio_diagnostics.txt'):
        """Collect the audio_diagnostics file for debugging.

        @param filename: the audio diagnostics filename

        """
        if not self.audio_facade:
            logging.warn('self.audio_facade does not exist.')
            return

        audio_diagnostics_file = os.path.join(self.resultsdir, filename)
        try:
            self.audio_facade.dump_diagnostics(audio_diagnostics_file)
            logging.debug('collected audio_diagnostics file in %s',
                          audio_diagnostics_file)
        except:
            logging.warn('failed to call dump_diagnostics()')

    def collect_audio_files(self):
        """Collect the recoded audio files for debugging. """
        compressed_file_name = 'audio_files.tar.gz'
        remote_result_path = os.path.join(AUDIO_RECORD_DIR,
                                          compressed_file_name)

        if not self.bluetooth_facade.zip_audio_files(AUDIO_RECORD_DIR,
                                                     remote_result_path):
            logging.error('Failed to compress the audio files.')
            return

        try:
            result_path = os.path.join(self.resultsdir, compressed_file_name)
            self.host.get_file(remote_result_path, result_path)
            logging.debug('Collected audio files in %s', result_path)
        except Exception as e:
            logging.error('Failed to collect audio files: %s', e)

    def generate_audio_config(self, test_specific_audio_config):
        """Generate the audio config.

        Generate a default audio config. Update the config with any test
        specific audio config.

        @param test_specific_audio_config: the test specific audio config
                that will be used to update the default one.
        """
        for profile in [A2DP_CODEC, HFP_CODEC]:
            if profile in test_specific_audio_config:
                codec = test_specific_audio_config[profile]
                audio_server = self.AUDIO_SERVER_CHOICE.get(codec)
                if audio_server:
                    test_specific_audio_config[AUDIO_SERVER] = audio_server

        self._audio_config = self.DEFAULT_AUDIO_CONFIG.copy()
        self._audio_config.update(test_specific_audio_config)
        logging.debug("audio_config: %s", self._audio_config)

    def cleanup_audio_config(self):
        """Clean up the audio config.

        Clean up both self._audio_config.
        """
        self._audio_config = {}

    def get_audio_server_name(self):
        """Get the audio server name from the audio config.

        @returns: the audio server name
        """
        return self._audio_config.get(AUDIO_SERVER)

    def get_a2dp_codec_name(self):
        """Get the audio a2dp codec from the audio config.

        @returns: the a2dp codec
        """
        return self._audio_config.get(A2DP_CODEC)

    def is_a2dp_profile(self, test_profile):
        """Is the test_profile an A2DP profile?

        @returns: True if the test_profile is an A2DP profile.
        """
        return test_profile.startswith(A2DP)

    def initialize_bluetooth_audio(self,
                                   device,
                                   test_profile,
                                   audio_config={}):
        """Initialize the Bluetooth audio task.

        Note: pulseaudio is not stable. Need to restart it in the beginning.

        @param device: the bluetooth peer device
        @param test_profile: the test profile used, A2DP, HFP_WBS or HFP_NBS
        @param audio_config: the test specific audio config that will be used
                to update the default one

        """
        self.cleanup_audio_config()
        self.generate_audio_config(audio_config)

        audio_server = self.get_audio_server_name()
        if audio_server != PULSEAUDIO and audio_server != PIPEWIRE:
            raise error.TestError('%s not supported' % audio_server)

        if not self.bluetooth_facade.create_audio_record_directory(
                AUDIO_RECORD_DIR):
            raise error.TestError('Failed to create %s on the DUT' %
                                  AUDIO_RECORD_DIR)

        device.SetAudioConfig(self._audio_config)

        if not device.StartAudioServer(test_profile):
            raise error.TestError('Failed to start %s.' % audio_server)
        logging.info('%s is started.', audio_server)

        if test_profile in (HFP_WBS, HFP_NBS, HFP_NBS_MEDIUM, HFP_WBS_MEDIUM,
                            HFP_TELEPHONY):
            if device.StartOfono():
                logging.debug('ofono is started.')
            else:
                raise error.TestError('Failed to start ofono.')
        elif device.StopOfono():
            logging.debug('ofono is stopped.')
        else:
            logging.warning('Failed to stop ofono. Ignored.')

        # Need time to complete starting services.
        time.sleep(self.WAIT_DAEMONS_READY_SECS)


    def cleanup_bluetooth_audio(self, device, test_profile):
        """Cleanup for Bluetooth audio.

        @param device: the bluetooth peer device
        @param test_profile: the test profile used, A2DP, HFP_WBS or HFP_NBS

        """
        self.cleanup_audio_config()

        if device.StopAudioServer():
            logging.debug('The audio serever is stopped.')
        else:
            logging.warning('Failed to stop the audio server. Ignored.')

        if device.StopOfono():
            logging.debug('ofono is stopped.')
        else:
            logging.warning('Failed to stop ofono. Ignored.')

    def enable_audio_stream_for_avrcp(self, device):
        """Adopt Android behavior, i.e., AVRCP is coupled with A2DP before
        executing any AVRCP tests, and an active audio stream should be enabled.

        @param device: the Bluetooth peer device.

        """
        test_data = audio_test_data['a2dp'].copy()
        duration = test_data['duration']

        test_data['file'] %= duration

        # Wait for pulseaudio a2dp bluez source
        self.test_device_a2dp_connected(device)

        # Select audio output node so that we do not rely on chrome to do it.
        self.test_select_audio_output_node_bluetooth()

        # Start recording audio on the peer Bluetooth audio device.
        self.test_device_to_start_recording_audio_subprocess(
                device, 'a2dp', test_data)

        # Play audio on the DUT in a non-blocked way and check the recorded
        # audio stream in a real-time manner.
        self.test_dut_to_start_playing_audio_subprocess(test_data)

    def stop_audio_stream_for_avrcp(self):
        """Stop playing audio on DUT"""
        self.test_dut_to_stop_playing_audio_subprocess()

    def get_peer_a2dp_notif_timestamps(self, device):
        """Gets peer A2DP notifications timestamp.

        @param device: The Bluetooth device.

        @return: List of peer notifications timestamp.
        """
        return self.get_peer_protocol_notif_timestamps(
                self.A2DP_PEER_NOTIFICATION_REGEX, device)

    def get_dut_a2dp_notif_timestamps(self, device):
        """Gets DUT A2DP notifications timestamp.

        @param device: The Bluetooth device.

        @return: List of DUT notifications timestamp.
        """
        return self.get_dut_protocol_notif_timestamps(
                self.A2DP_DUT_NOTIFICATION_REGEX, device)

    def initialize_bluetooth_player(self, device):
        """Initialize the Bluetooth media player.

        @param device: the Bluetooth peer device.

        """
        if not device.ExportMediaPlayer():
            raise error.TestError('Failed to export media player.')
        logging.debug('mpris-proxy is started.')

        # Wait for player to show up and observed by playerctl.
        desc='waiting for media player'
        self._poll_for_condition(
                lambda: bool(device.GetExportedMediaPlayer()), desc=desc)


    def cleanup_bluetooth_player(self, device):
        """Cleanup for Bluetooth media player.

        @param device: the bluetooth peer device.

        """
        device.UnexportMediaPlayer()


    def parse_visqol_output(self, stdout, stderr):
        """
        Parse stdout and stderr string from VISQOL output and parse into
        a float score.

        On error, stderr will contain the error message, otherwise will be None.
        On success, stdout will be a string, first line will be
        VISQOL version, followed by indication of speech mode. Followed by
        paths to reference and degraded file, and a float MOS-LQO score, which
        is what we're interested in. Followed by more detailed charts about
        specific scoring by segments of the files. Stdout is None on error.

        @param stdout: The stdout bytes from commandline output of VISQOL.
        @param stderr: The stderr bytes from commandline output of VISQOL.

        @returns: A tuple of a float score and string representation of the
                srderr or None if there was no error.
        """
        string_out = stdout.decode('utf-8') or ''
        stderr = stderr.decode('utf-8')

        # Log verbose VISQOL output:
        log_file = os.path.join(VISQOL_TEST_DIR, 'VISQOL_LOG.txt')
        with open(log_file, 'w+') as f:
            f.write('String Error:\n{}\n'.format(stderr))
            f.write('String Out:\n{}\n'.format(string_out))

        # pattern matches first float or int after 'MOS-LQO:' in stdout,
        # e.g. it would match the line 'MOS-LQO       2.3' in the stdout
        score_pattern = re.compile(r'.*MOS-LQO:\s*(\d+.?\d*)')
        score_search = re.search(score_pattern, string_out)

        # re.search returns None if no pattern match found, otherwise the score
        # would be in the match object's group 1 matches just the float score
        score = float(score_search.group(1)) if score_search else -1.0
        return stderr, score


    def get_visqol_score(self, ref_file, deg_file, speech_mode=True,
                         verbose=True):
        """
        Runs VISQOL using the subprocess library on the provided reference file
        and degraded file and returns the VISQOL score.

        @param ref_file: File path to the reference wav file.
        @param deg_file: File path to the degraded wav file.
        @param speech_mode: [Optional] Defaults to True, accepts 16k sample
                rate files and ignores frequencies > 8kHz for scoring.
        @param verbose: [Optional] Defaults to True, outputs more details.

        @returns: A float score for the tested file.
        """
        visqol_cmd = [VISQOL_PATH]
        visqol_cmd += ['--reference_file', ref_file]
        visqol_cmd += ['--degraded_file', deg_file]
        visqol_cmd += ['--similarity_to_quality_model', VISQOL_SIMILARITY_MODEL]

        if speech_mode:
            visqol_cmd.append('--use_speech_mode')
        if verbose:
            visqol_cmd.append('--verbose')

        visqol_process = subprocess.Popen(visqol_cmd, stdout=subprocess.PIPE,
                                          stderr=subprocess.PIPE)
        stdout, stderr = visqol_process.communicate()

        err, score = self.parse_visqol_output(stdout, stderr)

        if err:
            raise error.TestError(err)
        elif score < 0.0:
            raise error.TestError('Failed to parse score, got {}'.format(score))

        return score


    def get_ref_and_deg_files(self, trimmed_file, test_profile, test_data):
        """Return path for reference and degraded files to run visqol on.

        @param trimmed_file: Path to the trimmed audio file on DUT.
        @param test_profile: The test profile used HFP_WBS or HFP_NBS.
        @param test_data: A dictionary about the audio test data defined in
                client/cros/bluetooth/bluetooth_audio_test_data.py.

        @returns: A tuple of path to the reference file and degraded file if
                they exist, otherwise False for the files that aren't available.
        """
        # Path in autotest server in ViSQOL folder to store degraded file from
        # retrieved from the DUT
        deg_file = os.path.join(VISQOL_TEST_DIR, os.path.split(trimmed_file)[1])
        played_file = test_data['file']
        # If profile is WBS, no resampling required
        if test_profile == HFP_WBS:
            self.host.get_file(trimmed_file, deg_file)
            return played_file, deg_file

        # On NBS, degraded and reference files need to be resampled to 16 kHz
        # Build path for the upsampled (us) reference (ref) file on DUT
        ref_file = '{}_us_ref{}'.format(*os.path.splitext(played_file))
        # If resampled ref file already exists, don't need to do it again
        if not os.path.isfile(ref_file):
            if not self.bluetooth_facade.convert_audio_sample_rate(
                    played_file, ref_file, test_data,
                    self.MIN_VISQOL_SAMPLE_RATE):
                return False, False
            # Move upsampled reference file to autotest server
            self.host.get_file(ref_file, ref_file)

        # Build path for resampled degraded file on DUT
        deg_on_dut = '{}_us{}'.format(*os.path.splitext(trimmed_file))
        # Resample degraded file to 16 kHz and move to autotest server
        if not self.bluetooth_facade.convert_audio_sample_rate(
                trimmed_file, deg_on_dut, test_data,
                self.MIN_VISQOL_SAMPLE_RATE):
            return ref_file, False

        self.host.get_file(deg_on_dut, deg_file)

        return ref_file, deg_file


    def format_recorded_file(self, test_data, test_profile, recording_device):
        """Format recorded files to be compatible with ViSQOL.

        Convert raw files to wav if recorded file is a raw file, trim file to
        duration, if required, resample the file, then lastly return the paths
        for the reference file and degraded file on the autotest server.

        @param test_data: A dictionary about the audio test data defined in
                client/cros/bluetooth/bluetooth_audio_test_data.py.
        @param test_profile: The test profile used, HFP_WBS or HFP_NBS.
        @param recording_device: Which device recorded the audio, either
                'recorded_by_dut' or 'recorded_by_peer'.

        @returns: A tuple of path to the reference file and degraded file if
                they exist, otherwise False for the files that aren't available.
        """
        # Path to recorded file either on DUT or BT peer
        recorded_file = test_data[recording_device]
        untrimmed_file = recorded_file
        if recorded_file.endswith('.raw'):
            # build path for file converted from raw to wav, i.e. change the ext
            untrimmed_file = os.path.splitext(recorded_file)[0] + '.wav'
            if not self.bluetooth_facade.convert_raw_to_wav(
                    recorded_file, untrimmed_file, test_data):
                raise error.TestError('Could not convert raw file to wav')

        # Compute the duration of played file without added buffer
        new_duration = (test_data['chunk_checking_duration'] -
                        VISQOL_BUFFER_LENGTH)
        # build path for file resulting from trimming to desired duration
        trimmed_file = '{}_t{}'.format(*os.path.splitext(untrimmed_file))
        if not self.bluetooth_facade.trim_wav_file(
                untrimmed_file, trimmed_file, new_duration, test_data):
            raise error.TestError('Failed to trim recorded file')

        return self.get_ref_and_deg_files(trimmed_file, test_profile, test_data)


    def handle_one_chunk(self, device, chunk_in_secs, index, test_profile):
        """Handle one chunk of audio data by calling chameleon api."""
        self._get_real_ip()

        try:
            recorded_file = device.HandleOneChunk(chunk_in_secs, index,
                                                  self.real_ip)
        except Exception as e:
            raise error.TestError('Failed to handle chunk (%s)', e)

        return recorded_file


    def will_apply_hfp_offload_path(self, force_offload):
        """Whether the DUT is going to apply HFP offload path.

        @param force_offload: A bool for the given flag state.

        @returns: A bool indicating whether to apply HFP offload path.
                True for offload path, False for non-offload path.
        """
        if self.get_board() in self.BOARDS_OFFLOAD_ONLY_FOR_HFP:
            # support offload path only.
            # contain all MT8183/MT8186 devices, e.g. Steelix, Krane, and Kukui.
            return True
        elif self.get_hfp_offload_supported():
            # support both non-offload and offload paths.
            # include some Intel TGL+ devices such as Redrix, Kano, Volmar, etc.
            return force_offload
        else:
            # support non-offload path only.
            # contain the rest does not support HFP offload.
            return False


    # ---------------------------------------------------------------
    # Definitions of all bluetooth audio test cases
    # ---------------------------------------------------------------

    @test_retry_and_log(False)
    def test_set_bluetooth_telephony(self, enable):
        """Enable bluetooth telephony on the DUT."""
        return self.bluetooth_facade.set_phone_ops_enabled(enable)

    @test_retry_and_log(False)
    def test_select_audio_input_device(self, device_name):
        """Select the audio input device for the DUT.

        @param: device_name: the audio input device to be selected.

        @returns: True on success. Raise otherwise.
        """
        desc = 'waiting for cras to select audio input device'
        logging.debug(desc)
        self._poll_for_condition(
                lambda: self.bluetooth_facade.select_input_device(device_name),
                desc=desc)
        return True


    @test_retry_and_log(False)
    def test_select_audio_output_node_bluetooth(self):
        """Select the Bluetooth device as output node.

        @returns: True on success. False otherwise.
        """
        return self._test_select_audio_output_node(
                self.CRAS_BLUETOOTH_OUTPUT_NODE_TYPE)


    @test_retry_and_log(False)
    def test_select_audio_output_node_internal_speaker(self):
        """Select the internal speaker as output node.

        @returns: True on success. False otherwise.
        """
        return self._test_select_audio_output_node(
                self.CRAS_INTERNAL_SPEAKER_OUTPUT_NODE_TYPE)


    def _test_select_audio_output_node(self, node_type=None):
        """Select the audio output node through cras.

        @param node_type: a str representing node type defined in
                          CRAS_NODE_TYPES.
        @raises: error.TestError if failed.

        @return True if select given node success.
        """
        def node_type_selected(node_type):
            """Check if the given node type is selected."""
            selected = self.bluetooth_facade.get_selected_output_device_type()
            logging.debug('active output node type: %s, expected %s', selected,
                          node_type)
            return selected == node_type

        desc = 'waiting for bluetooth_facade.select_output_node()'
        self._poll_for_condition(
                lambda: self.bluetooth_facade.select_output_node(node_type),
                desc=desc)

        desc = 'waiting for %s as active cras audio output node type' % node_type
        logging.debug(desc)
        self._poll_for_condition(lambda: node_type_selected(node_type),
                                 desc=desc)

        return True


    @test_retry_and_log(False)
    def test_audio_is_alive_on_dut(self):
        """Test that if the audio stream is alive on the DUT.

        @returns: True if the audio summary is found on the DUT.
        """
        summary = self.bluetooth_facade.get_audio_thread_summary()
        result = bool(summary)

        # If we can find something starts with summary like: "Summary: Output
        # device [Silent playback device.] 4096 48000 2  Summary: Output stream
        # CRAS_CLIENT_TYPE_TEST CRAS_STREAM_TYPE_DEFAULT 480 240 0x0000 48000
        # 2 0" this means that there's an audio stream alive on the DUT.
        desc = " ".join(str(line) for line in summary)
        logging.debug('find summary: %s', desc)

        self.results = {'test_audio_is_alive_on_dut': result}
        return all(self.results.values())


    @test_retry_and_log(False)
    def test_check_chunks(self,
                          device,
                          test_profile,
                          test_data,
                          duration,
                          check_legitimacy=True,
                          check_frequencies=True,
                          start_index=0):
        """Check chunks of recorded streams and verify the primary frequencies.

        @param device: the bluetooth peer device
        @param test_profile: the a2dp test profile;
                             choices are A2DP and A2DP_LONG
        @param test_data: the test data of the test profile
        @param duration: the duration of the audio file to test
        @param check_legitimacy: specify this to True to run
                                _check_audio_frames_legitimacy test
        @param check_frequencies: specify this to True to run
                                 _check_primary_frequencies test
        @param start_index: The starting index of the audio file. This is used
                            only to prevent audio files from being replaced
                            when this function is called multiple times.

        @returns: True if all chunks pass the frequencies check.
        """
        chunk_in_secs = test_data['chunk_in_secs']
        if not bool(chunk_in_secs):
            chunk_in_secs = self.DEFAULT_CHUNK_IN_SECS
        nchunks = duration // chunk_in_secs
        logging.info('Number of chunks: %d', nchunks)

        check_audio_frames_legitimacy = True
        check_primary_frequencies = True
        for i in range(nchunks):
            logging.debug('Check chunk %d', i)

            recorded_file = self.handle_one_chunk(device, chunk_in_secs,
                                                  start_index + i,
                                                  test_profile)
            if recorded_file is None:
                raise error.TestError('Failed to handle chunk %d' % i)

            if check_legitimacy:
                # Check if the audio frames in the recorded file are legitimate.
                if not self._check_audio_frames_legitimacy(
                        test_data, 'recorded_by_peer', recorded_file=recorded_file):
                    if (i > self.IGNORE_LAST_FEW_CHUNKS and
                            i >= nchunks - self.IGNORE_LAST_FEW_CHUNKS):
                        logging.info('empty chunk %d ignored for last %d chunks',
                                     i, self.IGNORE_LAST_FEW_CHUNKS)
                    else:
                        check_audio_frames_legitimacy = False
                    break

            if check_frequencies:
                # Check if the primary frequencies of the recorded file
                # meet expectation.
                if not self._check_primary_frequencies(
                        test_profile,
                        test_data,
                        'recorded_by_peer',
                        recorded_file=recorded_file):
                    if (i > self.IGNORE_LAST_FEW_CHUNKS and
                            i >= nchunks - self.IGNORE_LAST_FEW_CHUNKS):
                        msg = 'partially filled chunk %d ignored for last %d chunks'
                        logging.info(msg, i, self.IGNORE_LAST_FEW_CHUNKS)
                    else:
                        check_primary_frequencies = False
                    break

        self.results = dict()
        if check_legitimacy:
            self.results['check_audio_frames_legitimacy'] = (
                    check_audio_frames_legitimacy)

        if check_frequencies:
            self.results['check_primary_frequencies'] = (
                    check_primary_frequencies)

        return all(self.results.values())


    @test_retry_and_log(False)
    def test_check_empty_chunks(self,
                                device,
                                test_data,
                                duration,
                                test_profile,
                                start_index=0):
        """Check if all the chunks are empty.

        @param device: The Bluetooth peer device.
        @param test_data: The test data of the test profile.
        @param duration: The duration of the audio file to test.
        @param test_profile: Which audio profile is used. Profiles are defined
                             in bluetooth_audio_test_data.py.
        @param start_index: The starting index of the audio file. This is used
                            only to prevent audio files from being replaced
                            when this function is called multiple times.

        @returns: True if all the chunks are empty.
        """
        chunk_in_secs = test_data['chunk_in_secs']
        if not bool(chunk_in_secs):
            chunk_in_secs = self.DEFAULT_CHUNK_IN_SECS
        nchunks = duration // chunk_in_secs
        logging.info('Number of chunks: %d', nchunks)

        all_chunks_empty = True
        for i in range(nchunks):
            logging.info('Check chunk %d', i)

            recorded_file = self.handle_one_chunk(device, chunk_in_secs,
                                                  start_index + i,
                                                  test_profile)
            if recorded_file is None:
                raise error.TestError('Failed to handle chunk %d' % i)


            # Check if the audio frames in the recorded file are legitimate.
            if self._check_audio_frames_legitimacy(
                    test_data, 'recorded_by_peer', recorded_file):
                if (i > self.IGNORE_LAST_FEW_CHUNKS and
                        i >= nchunks - self.IGNORE_LAST_FEW_CHUNKS):
                    logging.info('empty chunk %d ignored for last %d chunks',
                                 i, self.IGNORE_LAST_FEW_CHUNKS)
                else:
                    all_chunks_empty = False
                break

        self.results = {'all chunks are empty': all_chunks_empty}

        return all(self.results.values())


    @test_retry_and_log(False)
    def test_check_audio_file(self,
                              device,
                              test_profile,
                              test_data,
                              recording_device,
                              check_legitimacy=True,
                              check_frequencies=True):
        """Check the audio file and verify the primary frequencies.

        @param device: the Bluetooth peer device.
        @param test_profile: A2DP or HFP test profile.
        @param test_data: the test data of the test profile.
        @param recording_device: which device recorded the audio,
                possible values are 'recorded_by_dut' or 'recorded_by_peer'.
        @param check_legitimacy: if set this to True, run
                                _check_audio_frames_legitimacy test.
        @param check_frequencies: if set this to True, run
                                 _check_primary_frequencies test.

        @returns: True if audio file passes the frequencies check.
        """
        if recording_device == 'recorded_by_peer':
            logging.debug('Scp to DUT')
            try:
                recorded_file = test_data[recording_device]
                self._scp_to_dut(device, recorded_file, recorded_file)
                logging.debug('Recorded {} successfully'.format(recorded_file))
            except Exception as e:
                raise error.TestError('Exception occurred when (%s)' % (e))

        self.results = dict()
        if check_legitimacy:
            self.results['check_audio_frames_legitimacy'] = (
                    self._check_audio_frames_legitimacy(
                            test_data, recording_device))

        if check_frequencies:
            self.results['check_primary_frequencies'] = (
                    self._check_primary_frequencies(
                            test_profile, test_data, recording_device))

        return all(self.results.values())


    @test_retry_and_log(False)
    def test_dut_to_start_playing_audio_subprocess(self,
                                                   test_data,
                                                   pin_device=None):
        """Start playing audio in a subprocess.

        @param test_data: the audio test data

        @returns: True on success. False otherwise.
        """
        start_playing_audio = self.bluetooth_facade.start_playing_audio_subprocess(
                test_data, pin_device)
        self.results = {
                'dut_to_start_playing_audio_subprocess': start_playing_audio
        }
        return all(self.results.values())

    @test_retry_and_log(False)
    def test_dut_to_stop_playing_audio_subprocess(self):
        """Stop playing audio in the subprocess.

        @returns: True on success. False otherwise.
        """
        stop_playing_audio = (
                self.bluetooth_facade.stop_playing_audio_subprocess())

        self.results = {
                'dut_to_stop_playing_audio_subprocess': stop_playing_audio
        }
        return all(self.results.values())

    @test_retry_and_log(False)
    def test_enable_disable_ui(self, enable):
        """Enables or disables the ui service.

        @param enable: A bool indicating enabling or disabling the ui service.

        @returns: True on success. False otherwise.
        """
        self.results = {
            'enable_disable_ui_success': self.enable_disable_ui(enable)
        }
        return all(self.results.values())

    @test_retry_and_log(False)
    def test_set_force_hfp_swb_enabled(self, enable):
        """Sets the force hfp swb enabled status to `enabled`.

        @param enable: A bool to be set as the force hfp swb enabled status.
        """
        self.audio_facade.set_force_hfp_swb_enabled(enable)
        enabled = self.audio_facade.get_force_hfp_swb_enabled()

        result_key = 'set_force_hfp_swb_enabled_to_%s' % enable
        self.results = {result_key: enable == enabled}
        return all(self.results.values())

    @test_retry_and_log(False)
    def test_set_force_sr_bt_enabled(self, enable):
        """Sets the force sr bt enabled status to `enabled`.

        @param enable: A bool to be set as the force sr bt enabled status.
        """
        self.audio_facade.set_force_sr_bt_enabled(enable)
        enabled = self.audio_facade.get_force_sr_bt_enabled()

        result_key = 'set_force_sr_bt_enabled_to_%s' % enable
        self.results = {result_key: enable == enabled}
        return all(self.results.values())

    @test_retry_and_log(False)
    def test_set_force_a2dp_advanced_codecs_enabled(self, enable):
        """Sets the force a2dp advanced codecs enabled status to `enabled`.

        @param enable: A bool to be set as the force a2dp advanced codecs
                       enabled status.
        """
        self.audio_facade.set_force_a2dp_advanced_codecs_enabled(enable)
        enabled = self.audio_facade.get_force_a2dp_advanced_codecs_enabled()

        result_key = 'set_force_a2dp_advanced_codecs_enabled_to_%s' % enable
        self.results = {result_key: enable == enabled}
        return all(self.results.values())

    @test_retry_and_log(False)
    def test_check_input_device_sample_rate(self, rate):
        """Checks the input device sample rate.

        This method checks if there is exactly one input device whose sample
        rate is the given `rate`.

        @param rate: the expected sample rate of the input device.

        @returns: True on success. False otherwise.
        """
        summaries = self.audio_facade.get_audio_thread_summary()
        # Example summaries when capturing:
        # Summary: Input device [RASPI_AUDIO] 14400 24000 1
        # Summary: Input stream 0x130000 CRAS_CLIENT_TYPE_TEST
        #          CRAS_STREAM_TYPE_DEFAULT 160 80 0x0000 16000 1 0
        pattern = re.compile(
            r'Summary: Input device \[.*?\] (\d+) (?P<rate>\d+) (\d+) ')
        filtered = map(lambda x: pattern.match(x), summaries)
        filtered = filter(lambda x: x and int(x.group('rate')) == rate,
                          filtered)
        result = len(list(filtered)) == 1
        if not result:
            logging.debug("summaries: %s", '\n'.join(summaries))
        self.results = {
            'check_input_device_sample_rate': result
        }
        return all(self.results.values())

    @test_retry_and_log(False)
    def test_dut_to_start_capturing_audio_subprocess(self, audio_data,
                                                     recording_device):
        """Start capturing audio in a subprocess.

        @param audio_data: the audio test data
        @param recording_device: which device recorded the audio,
                possible values are 'recorded_by_dut' or 'recorded_by_peer'

        @returns: True on success. False otherwise.
        """
        # Let the dut capture audio stream until it is stopped explicitly by
        # setting duration to None. This is required on some slower devices.
        audio_data = audio_data.copy()
        audio_data.update({'duration': None})

        start_capturing_audio = self.bluetooth_facade.start_capturing_audio_subprocess(
                audio_data, recording_device)
        self.results = {
                'dut_to_start_capturing_audio_subprocess':
                start_capturing_audio
        }
        return all(self.results.values())

    @test_retry_and_log(False)
    def test_dut_to_stop_capturing_audio_subprocess(self):
        """Stop capturing audio.

        @returns: True on success. False otherwise.
        """
        stop_capturing_audio = (
                self.bluetooth_facade.stop_capturing_audio_subprocess())

        self.results = {
                'dut_to_stop_capturing_audio_subprocess': stop_capturing_audio
        }
        return all(self.results.values())

    @test_retry_and_log(False)
    def test_device_to_start_playing_audio_subprocess(self, device,
                                                      test_profile, test_data):
        """Start playing the audio file in a subprocess.

        @param device: the bluetooth peer device
        @param test_data: the audio file to play and data about the file
        @param audio_profile: the audio profile, either a2dp, hfp_wbs, or hfp_nbs

        @returns: True on success. False otherwise.
        """
        start_playing_audio = device.StartPlayingAudioSubprocess(
                test_profile, test_data)
        self.results = {
                'device_to_start_playing_audio_subprocess': start_playing_audio
        }
        return all(self.results.values())

    @test_retry_and_log(False)
    def test_device_to_stop_playing_audio_subprocess(self, device):
        """Stop playing the audio file in a subprocess.

        @param device: the bluetooth peer device

        @returns: True on success. False otherwise.
        """
        stop_playing_audio = device.StopPlayingAudioSubprocess()
        self.results = {
                'device_to_stop_playing_audio_subprocess': stop_playing_audio
        }
        return all(self.results.values())

    @test_retry_and_log(False)
    def test_device_to_start_recording_audio_subprocess(
            self, device, test_profile, test_data):
        """Start recording audio in a subprocess.

        @param device: the bluetooth peer device
        @param test_profile: the audio profile used to get the recording settings
        @param test_data: the details of the file being recorded

        @returns: True on success. False otherwise.
        """
        start_recording_audio = device.StartRecordingAudioSubprocess(
                test_profile, test_data)
        self.results = {
                'device_to_start_recording_audio_subprocess':
                start_recording_audio
        }
        return all(self.results.values())

    @test_retry_and_log(False)
    def test_device_to_stop_recording_audio_subprocess(self, device):
        """Stop the recording subprocess.

        @returns: True on success. False otherwise.
        """
        stop_recording_audio = device.StopRecordingingAudioSubprocess()
        self.results = {
                'device_to_stop_recording_audio_subprocess':
                stop_recording_audio
        }
        return all(self.results.values())

    @test_retry_and_log(False)
    def test_device_a2dp_connected(self, device, timeout=15):
        """ Tests a2dp profile is connected on device. """
        audio_server = self.get_audio_server_name()
        if audio_server == PULSEAUDIO:
            check_connection = lambda: self._get_pulseaudio_bluez_source_a2dp(
                    device, A2DP)
        elif audio_server == PIPEWIRE:
            check_connection = lambda: device.GetPipewireBluezId() is not None
        else:
            raise error.TestError('%s not supported' % audio_server)

        self.results = {}
        is_connected = self._wait_for_condition(check_connection,
                                                'test_device_a2dp_connected',
                                                timeout=timeout)
        self.results['peer a2dp connected'] = is_connected

        return all(self.results.values())


    @test_retry_and_log(False)
    def test_hfp_connected(self,
                           bluez_function,
                           device,
                           test_profile,
                           timeout=15):
        """Tests HFP profile is connected.

        @param bluez_function: the appropriate bluez HFP function either
                _get_pulseaudio_bluez_source_hfp or
                _get_pulseaudio_bluez_sink_hfp depending on the role of the DUT.
        @param device: the Bluetooth peer device.
        @param test_profile: which test profile is used, HFP_WBS or HFP_NBS.
        @param timeout: number of seconds to wait before giving up connecting
                        to HFP profile.

        @returns: True on success. False otherwise.
        """
        audio_server = self.get_audio_server_name()
        if audio_server == PULSEAUDIO:
            check_connection = lambda: bluez_function(device, test_profile)
        elif audio_server == PIPEWIRE:
            check_connection = lambda: device.GetPipewireBluezId() is not None
        else:
            raise error.TestError('%s not supported' % audio_server)

        is_connected = self._wait_for_condition(check_connection,
                                                'test_hfp_connected',
                                                timeout=timeout)
        self.results = {'peer hfp connected': is_connected}

        return all(self.results.values())


    @test_retry_and_log(False)
    def test_send_audio_to_dut_and_unzip(self):
        """Send the audio file to the DUT and unzip it.

        @returns: True on success. False otherwise.
        """
        try:
            self.host.send_file(AUDIO_DATA_TARBALL_PATH,
                                AUDIO_DATA_TARBALL_PATH)
        except Exception as e:
            raise error.TestError('Fail to send file to the DUT: (%s)', e)

        unzip_success = self.bluetooth_facade.unzip_audio_test_data(
                AUDIO_DATA_TARBALL_PATH, DATA_DIR)

        self.results = {'unzip audio file': unzip_success}

        return all(self.results.values())


    @test_retry_and_log(False)
    def test_get_visqol_score(self, test_file, test_profile, recording_device):
        """Test that if the recorded audio file meets the passing score.

        This function also records the visqol performance.

        @param device: the Bluetooth peer device.
        @param test_profile: which test profile is used, HFP_WBS or HFP_NBS.
        @param recording_device: which device recorded the audio,
                possible values are 'recorded_by_dut' or 'recorded_by_peer'.

        @returns: True if the test files score at or above the
                  source_passing_score value as defined in
                  bluetooth_audio_test_data.py.
        """
        dut_role = 'sink' if recording_device == 'recorded_by_dut' else 'source'
        filename = os.path.split(test_file['file'])[1]

        ref_file, deg_file = self.format_recorded_file(test_file, test_profile,
                                                       recording_device)
        if not ref_file or not deg_file:
            desc = 'Failed to get ref and deg file: ref {}, deg {}'.format(
                    ref_file, deg_file)
            raise error.TestError(desc)

        score = self.get_visqol_score(ref_file,
                                      deg_file,
                                      speech_mode=test_file['speech_mode'])

        key = ''.join((dut_role, '_passing_score'))
        logging.info('{} scored {}, min passing score: {}'.format(
                filename, score, test_file[key]))
        passed = score >= test_file[key]
        self.results = {filename: passed}

        # Track visqol performance
        test_desc = '{}_{}_{}'.format(test_profile, dut_role,
                                      test_file['reporting_type'])
        self.write_perf_keyval({test_desc: score})

        if not passed:
            logging.warning('Failed: {}'.format(filename))

        return all(self.results.values())

    @test_retry_and_log(False)
    def test_check_call_state_on_peer(self, device, expected_call_state):
        """Test that if call state correct on peer

        @param device: the Bluetooth peer device.
        @param expected_call_state: Dictionary of total number of states for all
        current calls.

        @returns: True if the all call states in the Dictionary is same as
        expected.
        """
        call_result = device.GetCurrentCallState()
        self.results = {
                "expected_call_state": call_result == expected_call_state
        }
        return all(self.results.values())

    @test_retry_and_log(False)
    def test_check_mic_volume_on_peer(self, device, expect_mic_volume):
        """Test that if microphone volume is correct on peer

        @param device: the Bluetooth peer device.
        @param expect_mic_volume: volume 0-100

        @returns: True if expect_mic_volume == peer mic volume
        """
        volume = device.GetMicVolume()
        self.results = {
                "test_check_mic_volume_on_peer": volume == expect_mic_volume
        }
        return all(self.results.values())

    @test_retry_and_log(False)
    def test_check_input_event_on_dut(self,
                                      hook_switch=False,
                                      phone_mute=False):
        """Test that if input report result is correct on dut

        @param hook_switch: call is active or not.
        @param phone_mute: mic is mute or not.

        @returns: True if hook_switch and phone_mute result from hid input event
        is correct.
        """
        input_event = self.bluetooth_facade.get_input_event()
        self.results = {
                "expected_hook_switch":
                input_event["hook-switch"] == hook_switch,
                "expected_phone_mute": input_event["phone-mute"] == phone_mute
        }
        return all(self.results.values())

    @test_retry_and_log(False)
    def test_avrcp_commands(self, device):
        """Test Case: Test AVRCP commands issued by peer can be received at DUT

        The very first AVRCP command (Linux evdev event) the DUT receives
        contains extra information than just the AVRCP event, e.g. EV_REP
        report used to specify delay settings. Send the first command before
        the actual test starts to avoid dealing with them during test.

        The peer device name is required to monitor the event reception on the
        DUT. However, as the peer device itself already registered with the
        kernel as an udev input device. The AVRCP profile will register as an
        separate input device with the name pattern: name + (AVRCP), e.g.
        RASPI_AUDIO (AVRCP). Using 'AVRCP' as device name to help search for
        the device.

        @param device: the Bluetooth peer device

        @returns: True if the all AVRCP commands received by DUT, false
                  otherwise

        """
        device.SendMediaPlayerCommand('play')

        name = device.name
        device.name = 'AVRCP'

        result_pause = self.test_avrcp_event(device,
            device.SendMediaPlayerCommand, 'pause')
        result_play = self.test_avrcp_event(device,
            device.SendMediaPlayerCommand, 'play')
        result_stop = self.test_avrcp_event(device,
            device.SendMediaPlayerCommand, 'stop')
        result_next = self.test_avrcp_event(device,
            device.SendMediaPlayerCommand, 'next')
        result_previous = self.test_avrcp_event(device,
            device.SendMediaPlayerCommand, 'previous')

        device.name = name
        self.results = {'pause': result_pause, 'play': result_play,
                        'stop': result_stop, 'next': result_next,
                        'previous': result_previous}
        return all(self.results.values())


    @test_retry_and_log(False)
    def test_avrcp_media_info(self, device):
        """Test Case: Test AVRCP media info sent by DUT can be received by peer

        The test update all media information twice to prevent previous
        leftover data affect the current iteration of test. Then compare the
        expected results against the information received on the peer device.

        This test verifies media information including: playback status,
        length, title, artist, and album. Position of the media is not
        currently support as playerctl on the peer side cannot correctly
        retrieve such information.

        Length and position information are transmitted in the unit of
        microsecond. However, BlueZ process those time data in the resolution
        of millisecond. Discard microsecond detail when comparing those media
        information.

        The Floss player metadata consists of 'album', 'artist', 'title'
        and 'length'. Unlike the Bluez metadata that does not include 'length'

        @param device: the Bluetooth peer device

        @returns: True if the all AVRCP media info received by DUT, false
                  otherwise

        """
        # First round of updating media information to overwrite all leftovers.
        init_status = 'stopped'
        init_length = 20200414
        init_position = 8686868
        init_metadata = {'album': 'metadata_album_init',
                         'artist': 'metadata_artist_init',
                         'title': 'metadata_title_init'}

        if self.floss:
            init_metadata.update({'length': init_length})
        else:
            self.bluetooth_facade.set_player_length(init_length)
        self.bluetooth_facade.set_player_metadata(init_metadata)
        self.bluetooth_facade.set_player_playback_status(init_status)
        self.bluetooth_facade.set_player_position(init_position)

        # Second round of updating for actual testing.
        expected_status = 'playing'
        expected_length = 68686868
        expected_position = 20200414
        expected_metadata = {'album': 'metadata_album_expected',
                             'artist': 'metadata_artist_expected',
                             'title': 'metadata_title_expected'}

        if self.floss:
            expected_metadata.update({'length': expected_length})
        else:
            self.bluetooth_facade.set_player_length(expected_length)
        self.bluetooth_facade.set_player_metadata(expected_metadata)
        self.bluetooth_facade.set_player_playback_status(expected_status)
        self.bluetooth_facade.set_player_position(expected_position)

        # Give the DUT some chance to propagate the media info to the peer.
        # The propagation should be instant, so just have a short sleep.
        time.sleep(1)

        received_media_info = device.GetMediaPlayerMediaInfo()
        logging.debug(received_media_info)

        try:
            actual_length = int(received_media_info.get('length'))
        except:
            actual_length = 0

        result_status = bool(expected_status ==
            received_media_info.get('status').lower())
        result_album = bool(expected_metadata['album'] ==
            received_media_info.get('album'))
        result_artist = bool(expected_metadata['artist'] ==
            received_media_info.get('artist'))
        result_title = bool(expected_metadata['title'] ==
            received_media_info.get('title'))
        # The AVRCP time information is in the unit of microseconds but with
        # milliseconds resolution. Convert both send and received length into
        # milliseconds for comparison.
        result_length = bool(expected_length // 1000 == actual_length // 1000)

        self.results = {'status': result_status, 'album': result_album,
                        'artist': result_artist, 'title': result_title,
                        'length': result_length}
        return all(self.results.values())


    # ---------------------------------------------------------------
    # Definitions of all bluetooth audio test sequences
    # ---------------------------------------------------------------

    def test_a2dp_sinewaves(self,
                            device,
                            test_profile,
                            duration,
                            expected_pass=True):
        """Test Case: A2DP sinewaves.

        If the test is expected to pass, verify A2DP is connected on the peer
        device and it receives the audio stream.
        If the test is expected to fail, verify that A2DP is not connected
        **OR** the DUT doesn't receive the audio stream.

        @param device: The bluetooth peer device.
        @param test_profile: The a2dp test profile;
                             choices are A2DP and A2DP_LONG.
        @param duration: The duration of the audio file to test
                         0 means to use the default value in the test profile.
        @param expected_pass: True if the test is expected to pass, False
                              otherwise.
        """
        # Make a copy since the test_data may be formatted with distinct
        # arguments in the follow-up tests.
        test_data = audio_test_data[test_profile].copy()
        if bool(duration):
            test_data['duration'] = duration
        else:
            duration = test_data['duration']

        test_data['file'] %= duration
        logging.info('%s test for %d seconds.', test_profile, duration)

        # Wait for pulseaudio A2DP source.
        if not expected_pass:
            device_connected = self.ignore_failure(
                    self.test_device_a2dp_connected, device)
        else:
            device_connected = self.test_device_a2dp_connected(device)

        # If expected_test is False and device_connected is False, we don't need
        # to check if the peer receives an audio stream.
        if not device_connected:
            return

        # Select audio output node so that we do not rely on chrome to do it.
        self.test_select_audio_output_node_bluetooth()

        # Start recording audio on the peer Bluetooth audio device.
        self.test_device_to_start_recording_audio_subprocess(
                device, test_profile, test_data)

        # Play audio on the DUT in a non-blocked way and check the recorded
        # audio stream in a real-time manner.
        self.test_dut_to_start_playing_audio_subprocess(test_data)

        # Check chunks of recorded streams and verify the primary frequencies.
        # This is a blocking call until all chunks are completed.
        self.expect_test(expected_pass, self.test_check_chunks, device,
                         test_profile, test_data, duration)

        # Stop recording audio on the peer Bluetooth audio device.
        self.test_device_to_stop_recording_audio_subprocess(device)

        # Stop playing audio on DUT.
        self.test_dut_to_stop_playing_audio_subprocess()


    def playback_and_connect(self, device, test_profile):
        """Connect then disconnect an A2DP device while playing stream.

        This test first plays the audio stream and then selects the BT device
        as output node, checking if the stream has routed to the BT device.
        After that, disconnect the BT device and also check whether the stream
        closes on it gracefully.

        @param device: the Bluetooth peer device.
        @param test_profile: to select which A2DP test profile is used.
        """
        test_data = audio_test_data[test_profile]

        # Set audio output to the internal speaker and set the minimum volume
        # to avoid making noise while testing.
        self.test_select_audio_output_node_internal_speaker()
        self.audio_facade.set_selected_output_volume(1)

        # Start playing audio on the Dut.
        self.test_dut_to_start_playing_audio_subprocess(test_data)

        # Connect the Bluetooth device.
        self.test_device_set_discoverable(device, True)
        self.test_discover_device(device.address)
        self.test_pairing(device.address, device.pin, trusted=True)
        self.test_connection_by_adapter(device.address)
        self.test_device_a2dp_connected(device)

        # Select Bluetooth as output node.
        # Do not set the volume of Bluetooth audio device.
        self.test_select_audio_output_node_bluetooth()

        self.test_device_to_start_recording_audio_subprocess(
                device, test_profile, test_data)

        # Handle chunks of recorded streams and verify the primary frequencies.
        # This is a blocking call until all chunks are completed.
        self.test_check_chunks(device, test_profile, test_data,
                               test_data['chunk_checking_duration'])

        self.test_device_to_stop_recording_audio_subprocess(device)

        # Set audio output to the internal speaker and set the minimum volume
        # to avoid making noise while testing.
        self.test_select_audio_output_node_internal_speaker()
        self.audio_facade.set_selected_output_volume(1)

        # Check if the device disconnects successfully.
        self.expect_test(False, self.test_device_a2dp_connected, device)

        self.test_dut_to_stop_playing_audio_subprocess()

        self.audio_facade.set_selected_output_volume(100)


    def playback_and_disconnect(self, device, test_profile):
        """Disconnect the Bluetooth device while the stream is playing.

        This test will keep the stream playing and then disconnect the
        Bluetooth device. The goal is to check the stream is still alive
        after the Bluetooth device disconnected.

        @param device: the Bluetooth peer device.
        @param test_profile: to select which A2DP test profile is used.
        """
        test_data = audio_test_data[test_profile]

        # Connect the Bluetooth device.
        self.test_device_set_discoverable(device, True)
        self.test_discover_device(device.address)
        self.test_pairing(device.address, device.pin, trusted=True)
        self.test_connection_by_adapter(device.address)
        self.test_device_a2dp_connected(device)

        # Select Bluetooth as output node.
        self.test_select_audio_output_node_bluetooth()

        self.test_device_to_start_recording_audio_subprocess(
                device, test_profile, test_data)

        # Start playing audio on the DUT.
        self.test_dut_to_start_playing_audio_subprocess(test_data)

        # Handle chunks of recorded streams and verify the primary frequencies.
        # This is a blocking call until all chunks are completed.
        self.test_check_chunks(device, test_profile, test_data,
                               test_data['chunk_checking_duration'])

        self.test_device_to_stop_recording_audio_subprocess(device)

        # Disconnect the Bluetooth device.
        self.test_disconnection_by_adapter(device.address)

        # Obtain audio thread summary to check if the audio stream is still
        # alive.
        self.test_audio_is_alive_on_dut()

        # Stop playing audio on the DUT.
        self.test_dut_to_stop_playing_audio_subprocess()


    def playback_back2back(self, device, test_profile):
        """Repeat to start and stop the playback stream several times.

        This test repeats to start and stop the playback stream and verify
        that the Bluetooth device receives the stream correctly.

        @param device: the Bluetooth peer device.
        @param test_profile: to select which A2DP test profile is used.
        """
        test_data = audio_test_data[test_profile]

        self.test_device_set_discoverable(device, True)
        self.test_discover_device(device.address)
        self.test_pairing(device.address, device.pin, trusted=True)
        self.test_connection_by_adapter(device.address)

        self.test_device_a2dp_connected(device)
        self.test_select_audio_output_node_bluetooth()

        nchunks = (test_data['chunk_checking_duration'] //
                   test_data['chunk_in_secs'])

        for i in range(3):
            # TODO(b/208165757): In here if we record the audio stream before
            # playing that will cause an audio blank about 1~2 sec in the
            # beginning of the recorded file and make the chunks checking fail.
            # Need to fix this problem in the future.
            self.test_dut_to_start_playing_audio_subprocess(test_data)
            self.test_device_to_start_recording_audio_subprocess(
                    device, test_profile, test_data)

            self.test_check_chunks(device,
                                   test_profile,
                                   test_data,
                                   test_data['chunk_checking_duration'],
                                   start_index=i * 2 * nchunks)
            self.test_dut_to_stop_playing_audio_subprocess()
            self.test_device_to_stop_recording_audio_subprocess(device)

            self.test_device_to_start_recording_audio_subprocess(
                    device, test_profile, test_data)
            self.test_check_empty_chunks(device,
                                         test_data,
                                         test_data['chunk_checking_duration'],
                                         test_profile,
                                         start_index=(i * 2 + 1) * nchunks)
            self.test_device_to_stop_recording_audio_subprocess(device)

        self.test_disconnection_by_adapter(device.address)


    def pinned_playback(self, device, test_profile):
        """Play an audio stream that is pinned to the Bluetooth device.

        This test does not choose Bluetooth as the output node but directly
        plays the sound that is pinned to the Bluetooth device and check
        whether it receives the audio stream correctly.

        @param device: the Bluetooth peer device.
        @param test_profile: to select which A2DP test profile is used.
        """
        test_data = audio_test_data[test_profile]

        self.test_device_set_discoverable(device, True)
        self.test_discover_device(device.address)
        self.test_pairing(device.address, device.pin, trusted=True)
        self.test_connection_by_adapter(device.address)

        self.test_device_a2dp_connected(device)
        self.test_device_to_start_recording_audio_subprocess(
                device, test_profile, test_data)

        # We do not select Bluetooth as output node but play audio pinned to
        # the Bluetooth device straight forward.
        device_id = self.bluetooth_facade.get_device_id_from_node_type(
                self.CRAS_BLUETOOTH_OUTPUT_NODE_TYPE, False)
        logging.info("Bluetooth device id for audio stream output: %s",
                     device_id)
        self.test_dut_to_start_playing_audio_subprocess(test_data, device_id)
        self.test_check_chunks(device, test_profile, test_data,
                               test_data['duration'])
        self.test_dut_to_stop_playing_audio_subprocess()
        self.test_device_to_stop_recording_audio_subprocess(device)
        self.test_disconnection_by_adapter(device.address)


    def hfp_dut_as_source_visqol_score(self, device, test_profile):
        """Test Case: HFP test files streaming from peer device to the DUT.

        @param device: the Bluetooth peer device.
        @param test_profile: which test profile is used, HFP_WBS or HFP_NBS.
        """
        # list of test wav files
        hfp_test_data = audio_test_data[test_profile]
        test_files = hfp_test_data['visqol_test_files']

        get_visqol_binary()
        get_audio_test_data()

        # Download test data to the DUT.
        self.test_send_audio_to_dut_and_unzip()

        for test_file in test_files:
            filename = os.path.split(test_file['file'])[1]
            logging.debug('Testing file: {}'.format(filename))

            self.test_select_audio_input_device(device.name)
            self.test_select_audio_output_node_bluetooth()

            # Enable HFP profile.
            self.test_dut_to_start_capturing_audio_subprocess(
                    test_file, 'recorded_by_peer')

            # Wait for pulseaudio bluez hfp source/sink
            self.test_hfp_connected(self._get_pulseaudio_bluez_source_hfp,
                                    device, test_profile)

            self.test_device_to_start_recording_audio_subprocess(
                    device, test_profile, test_file)

            # Play audio on the DUT in a non-blocked way.
            # If there are issues, cras_test_client playing back might be blocked
            # forever. We would like to avoid the testing procedure from that.
            self.test_dut_to_start_playing_audio_subprocess(test_file)
            time.sleep(test_file['chunk_checking_duration'])
            self.test_dut_to_stop_playing_audio_subprocess()
            self.test_device_to_stop_recording_audio_subprocess(device)

            # Disable HFP profile.
            self.test_dut_to_stop_capturing_audio_subprocess()

            # Copy the recorded audio file to the DUT for spectrum analysis.
            recorded_file = test_file['recorded_by_peer']
            self._scp_to_dut(device, recorded_file, recorded_file)

            self.test_get_visqol_score(test_file, test_profile,
                                       'recorded_by_peer')


    def hfp_dut_as_sink_visqol_score(self, device, test_profile):
        """Test Case: HFP test files streaming from peer device to the DUT.

        @param device: the Bluetooth peer device.
        @param test_profile: which test profile is used, HFP_WBS or HFP_NBS.
        """
        # list of test wav files
        hfp_test_data = audio_test_data[test_profile]
        test_files = hfp_test_data['visqol_test_files']

        get_visqol_binary()
        get_audio_test_data()

        # Download test data to the DUT.
        self.test_send_audio_to_dut_and_unzip()

        for test_file in test_files:
            filename = os.path.split(test_file['file'])[1]
            logging.debug('Testing file: {}'.format(filename))

            self.test_select_audio_input_device(device.name)
            self.test_select_audio_output_node_bluetooth()

            # Enable HFP profile.
            self.test_dut_to_start_capturing_audio_subprocess(
                    test_file, 'recorded_by_dut')

            # Wait for pulseaudio bluez hfp source/sink.
            self.test_hfp_connected(self._get_pulseaudio_bluez_sink_hfp,
                                    device, test_profile)

            self.test_select_audio_input_device(device.name)

            self.test_device_to_start_playing_audio_subprocess(
                    device, test_profile, test_file)
            time.sleep(test_file['chunk_checking_duration'])
            self.test_device_to_stop_playing_audio_subprocess(device)

            # Disable HFP profile.
            self.test_dut_to_stop_capturing_audio_subprocess()
            logging.debug('Recorded {} successfully'.format(filename))

            self.test_get_visqol_score(test_file, test_profile,
                                       'recorded_by_dut')


    def hfp_dut_as_source(self, device, test_profile):
        """Test Case: HFP sinewave streaming from the DUT to peer device.

        @param device: the Bluetooth peer device.
        @param test_profile: which test profile is used, HFP_WBS or HFP_NBS.
        """
        hfp_test_data = audio_test_data[test_profile]

        self.test_select_audio_input_device(device.name)
        self.test_select_audio_output_node_bluetooth()

        # Enable HFP profile.
        self.test_dut_to_start_capturing_audio_subprocess(
                hfp_test_data, 'recorded_by_peer')

        # Wait for pulseaudio bluez hfp source/sink
        self.test_hfp_connected(self._get_pulseaudio_bluez_source_hfp, device,
                                test_profile)

        self.test_device_to_start_recording_audio_subprocess(
                device, test_profile, hfp_test_data)
        self.test_dut_to_start_playing_audio_subprocess(hfp_test_data)
        time.sleep(hfp_test_data['chunk_checking_duration'])
        self.test_dut_to_stop_playing_audio_subprocess()
        self.test_device_to_stop_recording_audio_subprocess(device)
        self.test_check_audio_file(device, test_profile, hfp_test_data,
                                   'recorded_by_peer')

        # Disable HFP profile.
        self.test_dut_to_stop_capturing_audio_subprocess()


    def hfp_dut_as_sink(self, device, test_profile, *,
                        check_input_device_sample_rate=None):
        """Test Case: HFP sinewave streaming from peer device to the DUT.

        @param device: the Bluetooth peer device.
        @param test_profile: which test profile is used, HFP_WBS or HFP_NBS.
        @param check_input_device_sample_rate: if it's not None, it must be an
                integer specifying the expected sample rate of the input device
                and, during capturing, a test will be run that checks if the
                sample rate is as expected.
        """
        hfp_test_data = audio_test_data[test_profile]

        self.test_select_audio_input_device(device.name)
        self.test_select_audio_output_node_bluetooth()

        # Enable HFP profile.
        self.test_dut_to_start_capturing_audio_subprocess(
                hfp_test_data, 'recorded_by_dut')

        # Wait for pulseaudio bluez hfp source/sink
        self.test_hfp_connected(self._get_pulseaudio_bluez_sink_hfp, device,
                                test_profile)

        self.test_select_audio_input_device(device.name)

        if check_input_device_sample_rate is not None:
            self.test_check_input_device_sample_rate(check_input_device_sample_rate)

        self.test_device_to_start_playing_audio_subprocess(
                device, test_profile, hfp_test_data)
        time.sleep(hfp_test_data['chunk_checking_duration'])
        self.test_device_to_stop_playing_audio_subprocess(device)

        # Disable HFP profile.
        self.test_dut_to_stop_capturing_audio_subprocess()
        self.test_check_audio_file(device, test_profile, hfp_test_data,
                                   'recorded_by_dut')


    def hfp_dut_as_sink_with_super_resolution(self, device, test_profile):
        """HFP sinewave streaming with super_resolution from peer device to DUT.

        @param device: the Bluetooth peer device.
        @param test_profile: which test profile is used, HFP_WBS or HFP_NBS.
        """
        # Sleeping is needed, or the step test_hfp_connected inside the method
        # hfp_dut_as_sink will fail.
        time.sleep(10)
        # Force enabling the sr bt and expect the sample rate to be 24000.
        self.test_set_force_sr_bt_enabled(True)
        self.hfp_dut_as_sink(
                device,
                test_profile,
                check_input_device_sample_rate=24000)
        self.test_set_force_sr_bt_enabled(False)


    def hfp_dut_as_source_back2back(self, device, test_profile):
        """Play and stop the audio stream from DUT to Bluetooth peer device.

        The test starts then stops the stream playback for three times. In each
        iteration, it checks the Bluetooth device can successfully receive the
        stream when it is played; also check the absence of the streama when
        stop playing.

        @param device: the Bluetooth peer device.
        @param test_profile: which test profile is used, HFP_SWB, HFP_WBS or HFP_NBS.
        """
        hfp_test_data = audio_test_data[test_profile]

        # Select audio input device.
        self.test_select_audio_input_device(device.name)

        # Select audio output node so that we do not rely on chrome to do it.
        self.test_select_audio_output_node_bluetooth()

        # Enable HFP profile.
        self.test_dut_to_start_capturing_audio_subprocess(hfp_test_data,
                                                          'recorded_by_peer')

        # Wait for pulseaudio bluez hfp source/sink
        self.test_hfp_connected(
                self._get_pulseaudio_bluez_source_hfp, device, test_profile)

        for _ in range(3):
            # TODO(b/208165757): If we record the audio stream before playing
            # that will cause an audio blank about 1~2 sec in the beginning of
            # the recorded file and make the chunks checking fail. Need to fix
            # this problem in the future.
            self.test_dut_to_start_playing_audio_subprocess(hfp_test_data)
            self.test_device_to_start_recording_audio_subprocess(
                    device, test_profile, hfp_test_data)
            time.sleep(hfp_test_data['chunk_checking_duration'])

            self.test_dut_to_stop_playing_audio_subprocess()
            self.test_device_to_stop_recording_audio_subprocess(device)
            self.test_check_audio_file(device, test_profile, hfp_test_data,
                                       'recorded_by_peer')

            self.test_device_to_start_recording_audio_subprocess(
                    device, test_profile, hfp_test_data)
            time.sleep(hfp_test_data['chunk_checking_duration'])

            self.test_device_to_stop_recording_audio_subprocess(device)
            self.test_check_audio_file(device, test_profile, hfp_test_data,
                                       recording_device='recorded_by_peer',
                                       check_frequencies=False)

        # Disable HFP profile.
        self.test_dut_to_stop_capturing_audio_subprocess()


    def a2dp_to_hfp_dut_as_source(self, device, test_profile):
        """Play the audio from DUT to Bluetooth device and switch the profile.

        This test first uses A2DP profile and plays the audio stream on the
        DUT, checking if the peer receives the audio stream correctly. And
        then switch to the HFP_NBS profile and check the audio stream again.

        @param device: the Bluetooth peer device.
        @param test_profile: which test profile is used, HFP_WBS_MEDIUM or
                             HFP_NBS_MEDIUM.
        """
        hfp_test_data = audio_test_data[test_profile]

        # Wait for pulseaudio a2dp bluez source.
        self.test_device_a2dp_connected(device)

        # Select audio output node so that we do not rely on chrome to do it.
        self.test_select_audio_output_node_bluetooth()

        self.test_device_to_start_recording_audio_subprocess(
                device, test_profile, hfp_test_data)

        # Play audio on the DUT in a non-blocked way and check the recorded
        # audio stream in a real-time manner.
        self.test_dut_to_start_playing_audio_subprocess(hfp_test_data)

        time.sleep(hfp_test_data['chunk_checking_duration'])

        self.test_device_to_stop_recording_audio_subprocess(device)

        self.test_check_audio_file(device, test_profile, hfp_test_data,
                                   'recorded_by_peer')

        self.test_select_audio_input_device(device.name)

        # Enable HFP profile.
        self.test_dut_to_start_capturing_audio_subprocess(hfp_test_data,
                                                          'recorded_by_peer')

        # Wait for pulseaudio bluez hfp source/sink.
        self.test_hfp_connected(
                self._get_pulseaudio_bluez_source_hfp, device, test_profile)

        self.test_device_to_start_recording_audio_subprocess(
                device, test_profile, hfp_test_data)

        time.sleep(hfp_test_data['chunk_checking_duration'])

        self.test_dut_to_stop_playing_audio_subprocess()

        self.test_device_to_stop_recording_audio_subprocess(device)

        self.test_check_audio_file(device, test_profile, hfp_test_data,
                                   'recorded_by_peer')

        # Disable HFP profile.
        self.test_dut_to_stop_capturing_audio_subprocess()


    def hfp_to_a2dp_dut_as_source(self, device, test_profile):
        """Play the audio from DUT to Bluetooth peer in A2DP then switch to HFP.

        This test first uses HFP profile and plays the audio stream on the DUT,
        checking if the peer receives the audio stream correctly. And then
        switch to the A2DP profile and check the audio stream again.

        @param device: the Bluetooth peer device.
        @param test_profile: which test profile is used,
                             HFP_NBS_MEDIUM or HFP_WBS_MEDIUM.
        """
        hfp_test_data = audio_test_data[test_profile]

        self.test_select_audio_input_device(device.name)

        # Select audio output node so that we do not rely on chrome to do it.
        self.test_select_audio_output_node_bluetooth()

        # Enable HFP profile.
        self.test_dut_to_start_capturing_audio_subprocess(hfp_test_data,
                                                          'recorded_by_peer')

        # Wait for pulseaudio bluez hfp source/sink.
        self.test_hfp_connected(
                self._get_pulseaudio_bluez_source_hfp, device, test_profile)

        # Play audio on the DUT in a non-blocked way and check the recorded
        # audio stream in a real-time manner.
        self.test_dut_to_start_playing_audio_subprocess(hfp_test_data)
        self.test_device_to_start_recording_audio_subprocess(
                device, test_profile, hfp_test_data)
        time.sleep(hfp_test_data['chunk_checking_duration'])

        self.test_device_to_stop_recording_audio_subprocess(device)
        self.test_check_audio_file(device, test_profile, hfp_test_data,
                                   'recorded_by_peer')

        # Disable HFP profile.
        self.test_dut_to_stop_capturing_audio_subprocess()

        # Wait for pulseaudio a2dp bluez source.
        self.test_device_a2dp_connected(device)

        self.test_device_to_start_recording_audio_subprocess(
                device, test_profile, hfp_test_data)
        time.sleep(hfp_test_data['chunk_checking_duration'])

        self.test_dut_to_stop_playing_audio_subprocess()
        self.test_check_audio_file(device, test_profile, hfp_test_data,
                                   'recorded_by_peer')
        self.test_device_to_stop_recording_audio_subprocess(device)

    def hfp_telephony_incoming_call_answer_by_peer(self, device):
        """Trigger incoming call on DUT and answer the call by Bluetooth peer.

        The purpose of this test is to assess the functionality of the DUT
        telephony HID device in handling incoming calls via the HFP profile.
        The test begins by sending an incoming call event to the DUT telephony
        HID device check if the incoming call exists on the peer device.
        The test then proceeds to answer the call from the Bluetooth peer device
        and verifies that the DUT telephony HID device sends an off-hook
        (call is active) input report to indicate that the call is active.

        @param device: the Bluetooth peer device.
        """
        hfp_test_data = audio_test_data[HFP_TELEPHONY]
        self.test_select_audio_input_device(device.name)
        self.test_select_audio_output_node_bluetooth()

        self.bluetooth_facade.open_telephony_device(device.name)
        self.bluetooth_facade.send_incoming_call()
        time.sleep(hfp_test_data['telephony_event_propagate_duration'])
        expected_call_state = self._create_call_state(incoming=1)
        self.test_check_call_state_on_peer(device, expected_call_state)

        device.AnswerCall()
        time.sleep(hfp_test_data['telephony_event_propagate_duration'])

        expected_call_state = self._create_call_state(active=1)
        self.test_check_input_event_on_dut(hook_switch=True, phone_mute=False)
        self.test_check_call_state_on_peer(device, expected_call_state)

        self.bluetooth_facade.close_telephony_device()

    def hfp_telephony_incoming_call_answer_by_dut(self, device):
        """Trigger incoming call on DUT and answer the call by DUT.

        The test sends an incoming call event to the DUT telephony HID device
        and checks if the incoming call exists on the peer device.
        The test then sends an off-hook (call is active) event on dut
        to answer the call and verifies that the peer has an active call.

        @param device: the Bluetooth peer device.
        """

        hfp_test_data = audio_test_data[HFP_TELEPHONY]
        self.test_select_audio_input_device(device.name)
        self.test_select_audio_output_node_bluetooth()

        self.bluetooth_facade.open_telephony_device(device.name)
        self.bluetooth_facade.send_incoming_call()
        time.sleep(hfp_test_data['telephony_event_propagate_duration'])

        expected_call_state = self._create_call_state(incoming=1)
        self.test_check_call_state_on_peer(device, expected_call_state)

        self.bluetooth_facade.send_answer_call()
        time.sleep(hfp_test_data['telephony_event_propagate_duration'])

        expected_call_state = self._create_call_state(active=1)
        self.test_check_call_state_on_peer(device, expected_call_state)

        self.bluetooth_facade.close_telephony_device()

    def hfp_telephony_incoming_call_reject_by_peer(self, device):
        """Trigger incoming call on DUT and reject the call by Bluetooth peer.

        The test begins by sending an incoming call event to the DUT telephony
        HID device and checks if the incoming call exists on the peer device.
        The test then proceeds to reject the call from the Bluetooth peer device
        and verifies that the DUT telephony HID device sends an
        off-hook=0 (call is rejected) input report to indicate that the call is
        rejected.

        @param device: the Bluetooth peer device.
        """
        hfp_test_data = audio_test_data[HFP_TELEPHONY]
        self.test_select_audio_input_device(device.name)
        self.test_select_audio_output_node_bluetooth()

        self.bluetooth_facade.open_telephony_device(device.name)
        self.bluetooth_facade.send_incoming_call()
        time.sleep(hfp_test_data['telephony_event_propagate_duration'])

        expected_call_state = self._create_call_state(incoming=1)
        self.test_check_call_state_on_peer(device, expected_call_state)

        device.RejectCall()
        time.sleep(hfp_test_data['telephony_event_propagate_duration'])

        expected_call_state = self._create_call_state(active=0)
        self.test_check_input_event_on_dut(hook_switch=False, phone_mute=False)
        self.test_check_call_state_on_peer(device, expected_call_state)
        self.bluetooth_facade.close_telephony_device()

    def hfp_telephony_incoming_call_reject_by_dut(self, device):
        """Trigger incoming call on DUT and reject the call from DUT.

        The test begins by sending an incoming call event to the DUT telephony
        HID device and checks if the incoming call exists on the peer device.
        The test then proceeds to reject the call from DUT and verifies that the
        call is rejected on peer side.

        @param device: the Bluetooth peer device.
        """
        hfp_test_data = audio_test_data[HFP_TELEPHONY]
        self.test_select_audio_input_device(device.name)
        self.test_select_audio_output_node_bluetooth()

        self.bluetooth_facade.open_telephony_device(device.name)
        self.bluetooth_facade.send_incoming_call()
        time.sleep(hfp_test_data['telephony_event_propagate_duration'])
        expected_call_state = self._create_call_state(incoming=1)

        self.test_check_call_state_on_peer(device, expected_call_state)

        self.bluetooth_facade.send_reject_call()
        time.sleep(hfp_test_data['telephony_event_propagate_duration'])

        expected_call_state = self._create_call_state(active=0)
        self.test_check_call_state_on_peer(device, expected_call_state)
        self.bluetooth_facade.close_telephony_device()

    def hfp_telephony_active_call_hangup_by_dut(self, device):
        """Place an active call on DUT and hangup the call from DUT.

        The test begins by sending an active call event to the DUT telephony HID
        device and checks if an active call exists on the peer device.
        The test then proceeds to hangup the call from DUT and verifies that no
        call exists on peer side.

        @param device: the Bluetooth peer device.
        """
        hfp_test_data = audio_test_data[HFP_TELEPHONY]
        self.test_select_audio_input_device(device.name)
        self.test_select_audio_output_node_bluetooth()

        self.bluetooth_facade.open_telephony_device(device.name)
        self.bluetooth_facade.send_answer_call()
        time.sleep(hfp_test_data['telephony_event_propagate_duration'])

        expected_call_state = self._create_call_state(active=1)
        self.test_check_call_state_on_peer(device, expected_call_state)

        self.bluetooth_facade.send_hangup_call()
        time.sleep(hfp_test_data['telephony_event_propagate_duration'])

        expected_call_state = self._create_call_state(active=0)
        self.test_check_call_state_on_peer(device, expected_call_state)
        self.bluetooth_facade.close_telephony_device()

    def hfp_telephony_active_call_hangup_by_peer(self, device):
        """Place an active call on DUT hangup the call from peer.

        The test begins by sending an active call event to the DUT telephony HID
        device and checks if an active call exists on the peer device.
        The test then proceeds to hangup the call from peer and verifies that
        that the DUT telephony HID device sends an off-hook=0 (call is hanguped)
        input report and no call exists on peer side.

        @param device: the Bluetooth peer device.
        """
        hfp_test_data = audio_test_data[HFP_TELEPHONY]
        self.test_select_audio_input_device(device.name)
        self.test_select_audio_output_node_bluetooth()

        self.bluetooth_facade.open_telephony_device(device.name)
        self.bluetooth_facade.send_answer_call()
        time.sleep(hfp_test_data['telephony_event_propagate_duration'])

        expected_call_state = self._create_call_state(active=1)
        self.test_check_call_state_on_peer(device, expected_call_state)

        device.HangupCall()
        time.sleep(hfp_test_data['telephony_event_propagate_duration'])

        expected_call_state = self._create_call_state(active=0)
        self.test_check_call_state_on_peer(device, expected_call_state)
        self.bluetooth_facade.close_telephony_device()

    def hfp_telephony_micmute_from_peer(self, device):
        """Trigger microphone mute from peer and verify the event sent to DUT.

        Since the HFP does not define a microphone mute event, Floss converts
        volume=0 to a muted event and sends it through the telephony HID input
        report.
        Upon receiving a non-zero volume, Floss converts it to an unmute event
        instead.
        This test sets the peer microphone volume to 0 and verify that the
        microphone mute event is sent from the telephony HID input report.

        @param device: the Bluetooth peer device.
        """
        hfp_test_data = audio_test_data[HFP_TELEPHONY]
        self.test_select_audio_input_device(device.name)
        self.test_select_audio_output_node_bluetooth()
        device.SetMicVolume(100)

        time.sleep(hfp_test_data['telephony_event_propagate_duration'])

        self.bluetooth_facade.open_telephony_device(device.name)
        time.sleep(hfp_test_data['telephony_event_propagate_duration'])
        device.SetMicVolume(0)
        time.sleep(hfp_test_data['telephony_event_propagate_duration'])
        self.test_check_input_event_on_dut(hook_switch=False, phone_mute=True)
        device.SetMicVolume(100)
        time.sleep(hfp_test_data['telephony_event_propagate_duration'])
        self.test_check_input_event_on_dut(hook_switch=False, phone_mute=False)

    def hfp_telephony_micmute_from_dut(self, device):
        """Trigger microphone mute from DUT and verify the mic volume on peer.

        Since the HFP does not define a microphone mute event, Floss stores the
        original volume level and sends out a volume=0 event to the peer on
        muting. On unmuting, the saved volume level is sent to the peer.
        This test send HID mute output report and verify the mic volume is
        changed on peer side.

        @param device: the Bluetooth peer device.
        """
        hfp_test_data = audio_test_data[HFP_TELEPHONY]
        self.test_select_audio_input_device(device.name)
        self.test_select_audio_output_node_bluetooth()
        device.SetMicVolume(100)

        time.sleep(hfp_test_data['telephony_event_propagate_duration'])

        self.bluetooth_facade.open_telephony_device(device.name)
        self.bluetooth_facade.send_mic_mute(True)
        time.sleep(hfp_test_data['telephony_event_propagate_duration'])

        self.test_check_mic_volume_on_peer(device, 0)
        self.bluetooth_facade.send_mic_mute(False)
        time.sleep(hfp_test_data['telephony_event_propagate_duration'])
        self.test_check_mic_volume_on_peer(device, 100)
