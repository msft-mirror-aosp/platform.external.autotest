# Copyright 2014 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Facade to access the audio-related functionality."""

import glob
import logging
import multiprocessing
import os
import tempfile

from autotest_lib.client.cros.audio import audio_helper
from autotest_lib.client.cros.audio import cmd_utils
from autotest_lib.client.cros.audio import cras_utils


class AudioFacadeNativeError(Exception):
    """Error in AudioFacadeNative."""
    pass


class AudioFacadeNative(object):
    """Facede to access the audio-related functionality.

    The methods inside this class only accept Python native types.

    """
    _CAPTURE_DATA_FORMATS = [
            dict(file_type='raw', sample_format='S16_LE',
                 channel=1, rate=48000),
            dict(file_type='raw', sample_format='S16_LE',
                 channel=2, rate=48000)]

    _PLAYBACK_DATA_FORMAT = dict(
            file_type='raw', sample_format='S16_LE', channel=2, rate=48000)

    def __init__(self, chrome):
        self._chrome = chrome
        self._browser = chrome.browser
        self._recorder = None


    def cleanup(self):
        """Clean up the temporary files."""
        for path in glob.glob('/tmp/playback_*'):
            os.unlink(path)

        for path in glob.glob('/tmp/capture_*'):
            os.unlink(path)


    def playback(self, file_path, data_format, blocking=False):
        """Playback a file.

        @param file_path: The path to the file.
        @param data_format: A dict containing data format including
                            file_type, sample_format, channel, and rate.
                            file_type: file type e.g. 'raw' or 'wav'.
                            sample_format: One of the keys in
                                           audio_data.SAMPLE_FORMAT.
                            channel: number of channels.
                            rate: sampling rate.
        @param blocking: Blocks this call until playback finishes.

        @returns: True.

        @raises: AudioFacadeNativeError if data format is not supported.

        """
        logging.info('AudioFacadeNative playback file: %r. format: %r',
                     file_path, data_format)

        if data_format != self._PLAYBACK_DATA_FORMAT:
            raise AudioFacadeNativeError(
                    'data format %r is not supported' % data_format)

        def _playback():
            """Playback using cras utility."""
            cras_utils.playback(playback_file=file_path)

        if blocking:
            _playback()
        else:
            p = multiprocessing.Process(target=_playback)
            p.daemon = True
            p.start()

        return True


    def start_recording(self, data_format):
        """Starts recording an audio file.

        Currently the format specified in _CAPTURE_DATA_FORMATS is the only
        formats.

        @param data_format: A dict containing:
                            file_type: 'raw'.
                            sample_format: 'S16_LE' for 16-bit signed integer in
                                           little-endian.
                            channel: channel number.
                            rate: sampling rate.


        @returns: True

        @raises: AudioFacadeNativeError if data format is not supported.

        """
        logging.info('AudioFacadeNative record format: %r', data_format)

        if data_format not in self._CAPTURE_DATA_FORMATS:
            raise AudioFacadeNativeError(
                    'data format %r is not supported' % data_format)

        self._recorder = Recorder()
        self._recorder.start(data_format)

        return True


    def stop_recording(self):
        """Stops recording an audio file.

        @returns: The path to the recorded file.

        """
        self._recorder.stop()
        return self._recorder.file_path


    def set_selected_output_volume(self, volume):
        """Sets the selected output volume.

        @param volume: the volume to be set(0-100).

        """
        cras_utils.set_selected_output_node_volume(volume)


    def set_selected_node_types(self, output_node_types, input_node_types):
        """Set selected node types.

        The node types are defined in cras_utils.CRAS_NODE_TYPES.

        @param output_node_types: A list of output node types.
                                  None to skip setting.
        @param input_node_types: A list of input node types.
                                 None to skip setting.

        """
        cras_utils.set_selected_node_types(output_node_types, input_node_types)


    def get_selected_node_types(self):
        """Gets the selected output and input node types.

        @returns: A tuple (output_node_types, input_node_types) where each
                  field is a list of selected node types defined in
                  cras_utils.CRAS_NODE_TYPES.

        """
        return cras_utils.get_selected_node_types()


    def get_plugged_node_types(self):
        """Gets the plugged output and input node types.

        @returns: A tuple (output_node_types, input_node_types) where each
                  field is a list of plugged node types defined in
                  cras_utils.CRAS_NODE_TYPES.

        """
        return cras_utils.get_plugged_node_types()


    def dump_diagnostics(self, file_path):
        """Dumps audio diagnostics results to a file.

        @param file_path: The path to dump results.

        @returns: True

        """
        with open(file_path, 'w') as f:
            f.write(audio_helper.get_audio_diagnostics())
        return True


class RecorderError(Exception):
    """Error in Recorder."""
    pass


class Recorder(object):
    """The class to control recording subprocess.

    Properties:
        file_path: The path to recorded file. It should be accessed after
                   stop() is called.

    """
    def __init__(self):
        """Initializes a Recorder."""
        _, self.file_path = tempfile.mkstemp(prefix='capture_', suffix='.raw')
        self._capture_subprocess = None


    def start(self, data_format):
        """Starts recording.

        Starts recording subprocess. It can be stopped by calling stop().

        @param data_format: A dict containing:
                            file_type: 'raw'.
                            sample_format: 'S16_LE' for 16-bit signed integer in
                                           little-endian.
                            channel: channel number.
                            rate: sampling rate.

        @raises: RecorderError: If recording subprocess is terminated
                 unexpectedly.

        """
        self._capture_subprocess = cmd_utils.popen(
                cras_utils.capture_cmd(
                        capture_file=self.file_path, duration=None,
                        channels=data_format['channel'],
                        rate=data_format['rate']))


    def stop(self):
        """Stops recording subprocess."""
        if self._capture_subprocess.poll() is None:
            self._capture_subprocess.terminate()
        else:
            raise RecorderError(
                    'Recording process was terminated unexpectedly.')
