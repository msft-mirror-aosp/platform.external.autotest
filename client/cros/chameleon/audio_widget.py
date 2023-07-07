# Lint as: python2, python3
# Copyright 2014 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""This module provides the audio widgets used in audio tests."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import abc
import copy
import logging
import os
import tempfile

from autotest_lib.client.cros.audio import audio_data
from autotest_lib.client.cros.audio import audio_test_data
from autotest_lib.client.cros.audio import sox_utils
from autotest_lib.client.cros.chameleon import audio_test_utils
from autotest_lib.client.cros.chameleon import chameleon_audio_ids as ids
from autotest_lib.client.cros.chameleon import chameleon_port_finder
import six

_CHAMELEON_FILE_PATH = os.path.join(os.path.dirname(__file__))

class AudioWidget(object):
    """
    This class abstracts an audio widget in audio test framework. A widget
    is identified by its audio port. The handler passed in at __init__ will
    handle action on the audio widget.

    Properties:
        audio_port: The AudioPort this AudioWidget resides in.
        handler: The handler that handles audio action on the widget. It is
                  actually a (Chameleon/Cros)(Input/Output)WidgetHandler object.

    """
    def __init__(self, audio_port, handler):
        """Initializes an AudioWidget on a AudioPort.

        @param audio_port: An AudioPort object.
        @param handler: A WidgetHandler object which handles action on the widget.

        """
        self.audio_port = audio_port
        self.handler = handler


    @property
    def port_id(self):
        """Port id of this audio widget.

        @returns: A string. The port id defined in chameleon_audio_ids for this
                  audio widget.
        """
        return self.audio_port.port_id


class AudioInputWidget(AudioWidget):
    """
    This class abstracts an audio input widget. This class provides the audio
    action that is available on an input audio port.

    Properties:
        _remote_rec_path: The path to the recorded file on the remote host.
        _rec_binary: The recorded binary data.
        _rec_format: The recorded data format. A dict containing
                     file_type: 'raw' or 'wav'.
                     sample_format: 'S32_LE' for 32-bit signed integer in
                                    little-endian. Refer to aplay manpage for
                                    other formats.
                     channel: channel number.
                     rate: sampling rate.

        _channel_map: A list containing current channel map. Checks docstring
                      of channel_map method for details.

    """
    def __init__(self, *args, **kwargs):
        """Initializes an AudioInputWidget."""
        super(AudioInputWidget, self).__init__(*args, **kwargs)
        self._remote_rec_path = None
        self._rec_binary = None
        self._rec_format = None
        self._channel_map = None
        self._init_channel_map_without_link()


    def start_recording(self, pinned=False, block_size=None):
        """Starts recording.

        @param pinned: Pins the audio to the input device.
        @param block_size: The number for frames per callback.

        """
        self._remote_rec_path = None
        self._rec_binary = None
        self._rec_format = None
        node_type = None
        if pinned:
            node_type = audio_test_utils.cros_port_id_to_cras_node_type(
                    self.port_id)

        self.handler.start_recording(node_type=node_type, block_size=block_size)


    def stop_recording(self, pinned=False):
        """Stops recording.

        @param pinned: Stop the recording on the pinned input device.
                       False means to stop the active selected one.

        """
        node_type = None
        if pinned:
            node_type = audio_test_utils.cros_port_id_to_cras_node_type(
                    self.port_id)

        self._remote_rec_path, self._rec_format = self.handler.stop_recording(
                node_type=node_type)


    def start_listening(self):
        """Starts listening."""
        self._remote_rec_path = None
        self._rec_binary = None
        self._rec_format = None
        self.handler.start_listening()


    def stop_listening(self):
        """Stops listening."""
        self._remote_rec_path, self._rec_format = self.handler.stop_listening()


    def read_recorded_binary(self):
        """Gets recorded file from handler and fills _rec_binary."""
        self._rec_binary = self.handler.get_recorded_binary(
                self._remote_rec_path, self._rec_format)


    def save_file(self, file_path):
        """Saves recorded data to a file.

        @param file_path: The path to save the file.

        """
        with open(file_path, 'wb') as f:
            logging.debug('Saving recorded raw file to %s', file_path)
            f.write(self._rec_binary)

        wav_file_path = file_path + '.wav'
        logging.debug('Saving recorded wav file to %s', wav_file_path)
        sox_utils.convert_raw_file(
                path_src=file_path,
                channels_src=self._channel,
                rate_src=self._sampling_rate,
                bits_src=self._sample_size_bits,
                path_dst=wav_file_path)


    def get_binary(self):
        """Gets recorded binary data.

        @returns: The recorded binary data.

        """
        return self._rec_binary


    @property
    def data_format(self):
        """The recorded data format.

        @returns: The recorded data format.

        """
        return self._rec_format


    @property
    def channel_map(self):
        """The recorded data channel map.

        @returns: The recorded channel map. A list containing channel mapping.
                  E.g. [1, 0, None, None, None, None, None, None] means
                  channel 0 of recorded data should be mapped to channel 1 of
                  data played to the recorder. Channel 1 of recorded data should
                  be mapped to channel 0 of data played to recorder.
                  Channel 2 to 7 of recorded data should be ignored.

        """
        return self._channel_map


    @channel_map.setter
    def channel_map(self, new_channel_map):
        """Sets channel map.

        @param new_channel_map: A list containing new channel map.

        """
        self._channel_map = copy.deepcopy(new_channel_map)


    def _init_channel_map_without_link(self):
        """Initializes channel map without WidgetLink.

        WidgetLink sets channel map to a sink widget when the link combines
        a source widget to a sink widget. For simple cases like internal
        microphone on Cros device, or Mic port on Chameleon, the audio signal
        is over the air, so we do not use link to combine the source to
        the sink. We just set a default channel map in this case.

        """
        if self.port_id in [ids.ChameleonIds.MIC, ids.CrosIds.INTERNAL_MIC]:
            self._channel_map = [0]


    @property
    def _sample_size_bytes(self):
        """Gets sample size in bytes of recorded data."""
        return audio_data.SAMPLE_FORMATS[
                self._rec_format['sample_format']]['size_bytes']


    @property
    def _sample_size_bits(self):
        """Gets sample size in bits of recorded data."""
        return self._sample_size_bytes * 8


    @property
    def _channel(self):
        """Gets number of channels of recorded data."""
        return self._rec_format['channel']


    @property
    def _sampling_rate(self):
        """Gets sampling rate of recorded data."""
        return self._rec_format['rate']


    def remove_head(self, duration_secs):
        """Removes a duration of recorded data from head.

        @param duration_secs: The duration in seconds to be removed from head.

        """
        offset = int(self._sampling_rate * duration_secs *
                     self._sample_size_bytes * self._channel)
        self._rec_binary = self._rec_binary[offset:]


    def lowpass_filter(self, frequency):
        """Passes the recorded data to a lowpass filter.

        @param frequency: The 3dB frequency of lowpass filter.

        """
        with tempfile.NamedTemporaryFile(
                prefix='original_') as original_file:
            with tempfile.NamedTemporaryFile(
                    prefix='filtered_') as filtered_file:

                original_file.write(self._rec_binary)
                original_file.flush()

                sox_utils.lowpass_filter(
                        original_file.name, self._channel,
                        self._sample_size_bits, self._sampling_rate,
                        filtered_file.name, frequency)

                self._rec_binary = filtered_file.read()


class AudioOutputWidget(AudioWidget):
    """
    This class abstracts an audio output widget. This class provides the audio
    action that is available on an output audio port.

    """
    def __init__(self, *args, **kwargs):
        """Initializes an AudioOutputWidget."""
        super(AudioOutputWidget, self).__init__(*args, **kwargs)
        self._remote_playback_path = None


    def set_playback_data(self, test_data):
        """Sets data to play.

        Sets the data to play in the handler and gets the remote file path.

        @param test_data: An AudioTestData object.

        @returns: path to the remote playback data

        """
        self._remote_playback_path = self.handler.set_playback_data(test_data)

        return self._remote_playback_path

    def start_playback(self, blocking=False, pinned=False, block_size=None):
        """Starts playing audio specified in previous set_playback_data call.

        @param blocking: Blocks this call until playback finishes.
        @param pinned: Pins the audio to the active output device.
        @param block_size: The number for frames per callback.

        """
        node_type = None
        if pinned:
            node_type = audio_test_utils.cros_port_id_to_cras_node_type(
                    self.port_id)

        self.handler.start_playback(
                self._remote_playback_path, blocking, node_type=node_type,
                block_size=block_size)

    def start_playback_with_path(self, remote_playback_path, blocking=False):
        """Starts playing audio specified in previous set_playback_data call
           and the remote_playback_path returned by set_playback_data function.

        @param remote_playback_path: Path returned by set_playback_data.
        @param blocking: Blocks this call until playback finishes.

        """
        self.handler.start_playback(remote_playback_path, blocking)


    def stop_playback(self):
        """Stops playing audio."""
        self.handler.stop_playback()


class WidgetHandler(six.with_metaclass(abc.ABCMeta, object)):
    """This class abstracts handler for basic actions on widget."""

    @abc.abstractmethod
    def plug(self):
        """Plug this widget."""
        pass


    @abc.abstractmethod
    def unplug(self):
        """Unplug this widget."""
        pass


class ChameleonWidgetHandler(WidgetHandler):
    """
    This class abstracts a Chameleon audio widget handler.

    Properties:
        interface: A string that represents the interface name on
                   Chameleon, e.g. 'HDMI', 'LineIn', 'LineOut'.
        scale: The scale is the scaling factor to be applied on the data of the
               widget before playing or after recording.
        _chameleon_board: A ChameleonBoard object to control Chameleon.
        _port: A ChameleonPort object to control port on Chameleon.

    """
    # The mic port on chameleon has a small gain. We need to scale
    # the recorded value up, otherwise, the recorded value will be
    # too small and will be falsely judged as not meaningful in the
    # processing, even when the recorded audio is clear.
    _DEFAULT_MIC_SCALE = 50.0

    def __init__(self, chameleon_board, interface):
        """Initializes a ChameleonWidgetHandler.

        @param chameleon_board: A ChameleonBoard object.
        @param interface: A string that represents the interface name on
                          Chameleon, e.g. 'HDMI', 'LineIn', 'LineOut'.

        """
        self.interface = interface
        self._chameleon_board = chameleon_board
        self._port = self._find_port(interface)
        self.scale = None
        self._init_scale_without_link()


    @abc.abstractmethod
    def _find_port(self, interface):
        """Finds the port by interface."""
        pass


    def plug(self):
        """Plugs this widget."""
        self._port.plug()


    def unplug(self):
        """Unplugs this widget."""
        self._port.unplug()


    def _init_scale_without_link(self):
        """Initializes scale for widget handler not used with link.

        Audio widget link sets scale when it connects two audio widgets.
        For audio widget not used with link, e.g. Mic on Chameleon, we set
        a default scale here.

        """
        if self.interface == 'Mic':
            self.scale = self._DEFAULT_MIC_SCALE


class ChameleonInputWidgetHandler(ChameleonWidgetHandler):
    """
    This class abstracts a Chameleon audio input widget handler.

    """
    def start_recording(self, **kargs):
        """Starts recording.

        @param kargs: Other arguments that Chameleon doesn't support.

        """
        self._port.start_capturing_audio()


    def stop_recording(self, **kargs):
        """Stops recording.

        Gets remote recorded path and format from Chameleon. The format can
        then be used in get_recorded_binary()

        @param kargs: Other arguments that Chameleon doesn't support.

        @returns: A tuple (remote_path, data_format) for recorded data.
                  Refer to stop_capturing_audio call of ChameleonAudioInput.

        """
        return self._port.stop_capturing_audio()


    def get_recorded_binary(self, remote_path, record_format):
        """Gets remote recorded file binary.

        Reads file from Chameleon host and handles scale if needed.

        @param remote_path: The path to the recorded file on Chameleon.
        @param record_format: The recorded data format. A dict containing
                     file_type: 'raw' or 'wav'.
                     sample_format: 'S32_LE' for 32-bit signed integer in
                                    little-endian. Refer to aplay manpage for
                                    other formats.
                     channel: channel number.
                     rate: sampling rate.

        @returns: The recorded binary.

        """
        with tempfile.NamedTemporaryFile(prefix='recorded_') as f:
            self._chameleon_board.host.get_file(remote_path, f.name)

            # Handles scaling using audio_test_data.
            test_data = audio_test_data.AudioTestData(record_format, f.name)
            converted_test_data = test_data.convert(record_format, self.scale)
            try:
                return converted_test_data.get_binary()
            finally:
                converted_test_data.delete()


    def _find_port(self, interface):
        """Finds a Chameleon audio port by interface(port name).

        @param interface: string, the interface. e.g: HDMI.

        @returns: A ChameleonPort object.

        @raises: ValueError if port is not connected.

        """
        finder = chameleon_port_finder.ChameleonAudioInputFinder(
                self._chameleon_board)
        chameleon_port = finder.find_port(interface)
        if not chameleon_port:
            raise ValueError(
                    'Port %s is not connected to Chameleon' % interface)
        return chameleon_port


class ChameleonHDMIInputWidgetHandlerError(Exception):
    """Error in ChameleonHDMIInputWidgetHandler."""


class ChameleonHDMIInputWidgetHandler(ChameleonInputWidgetHandler):
    """This class abstracts a Chameleon HDMI audio input widget handler."""
    _EDID_FILE_PATH = os.path.join(
        _CHAMELEON_FILE_PATH, 'test_data/edids/HDMI_DELL_U2410.txt')

    def __init__(self, chameleon_board, interface, display_facade):
        """Initializes a ChameleonHDMIInputWidgetHandler.

        @param chameleon_board: Pass to ChameleonInputWidgetHandler.
        @param interface: Pass to ChameleonInputWidgetHandler.
        @param display_facade: A DisplayFacadeRemoteAdapter to access
                               Cros device display functionality.

        """
        super(ChameleonHDMIInputWidgetHandler, self).__init__(
              chameleon_board, interface)
        self._display_facade = display_facade
        self._hdmi_video_port = None

        self._find_video_port()


    def _find_video_port(self):
        """Finds HDMI as a video port."""
        finder = chameleon_port_finder.ChameleonVideoInputFinder(
                self._chameleon_board, self._display_facade)
        self._hdmi_video_port = finder.find_port(self.interface)
        if not self._hdmi_video_port:
            raise ChameleonHDMIInputWidgetHandlerError(
                    'Can not find HDMI port, perhaps HDMI is not connected?')


    def set_edid_for_audio(self):
        """Sets the EDID suitable for audio test."""
        self._hdmi_video_port.set_edid_from_file(self._EDID_FILE_PATH)


    def restore_edid(self):
        """Restores the original EDID."""
        self._hdmi_video_port.restore_edid()


class ChameleonOutputWidgetHandler(ChameleonWidgetHandler):
    """
    This class abstracts a Chameleon audio output widget handler.

    """
    def __init__(self, *args, **kwargs):
        """Initializes an ChameleonOutputWidgetHandler."""
        super(ChameleonOutputWidgetHandler, self).__init__(*args, **kwargs)
        self._test_data_for_chameleon_format = None


    def set_playback_data(self, test_data):
        """Sets data to play.

        Handles scale if needed. Creates a path and sends the scaled data to
        Chameleon at that path.

        @param test_data: An AudioTestData object.

        @return: The remote data path on Chameleon.

        """
        self._test_data_for_chameleon_format = test_data.data_format
        return self._scale_and_send_playback_data(test_data)


    def _scale_and_send_playback_data(self, test_data):
        """Sets data to play on Chameleon.

        Creates a path and sends the scaled test data to Chameleon at that path.

        @param test_data: An AudioTestData object.

        @return: The remote data path on Chameleon.

        """
        test_data_for_chameleon = test_data.convert(
                self._test_data_for_chameleon_format, self.scale)

        try:
            with tempfile.NamedTemporaryFile(prefix='audio_') as f:
                self._chameleon_board.host.send_file(
                        test_data_for_chameleon.path, f.name)
            return f.name
        finally:
            test_data_for_chameleon.delete()


    def start_playback(self, path, blocking=False, **kargs):
        """Starts playback.

        @param path: The path to the file to play on Chameleon.
        @param blocking: Blocks this call until playback finishes.
        @param kargs: Other arguments that Chameleon doesn't support.

        @raises: NotImplementedError if blocking is True.
        """
        if blocking:
            raise NotImplementedError(
                    'Blocking playback on chameleon is not supported')

        self._port.start_playing_audio(
                path, self._test_data_for_chameleon_format)


    def stop_playback(self):
        """Stops playback."""
        self._port.stop_playing_audio()


    def _find_port(self, interface):
        """Finds a Chameleon audio port by interface(port name).

        @param interface: string, the interface. e.g: LineOut.

        @returns: A ChameleonPort object.

        @raises: ValueError if port is not connected.

        """
        finder = chameleon_port_finder.ChameleonAudioOutputFinder(
                self._chameleon_board)
        chameleon_port = finder.find_port(interface)
        if not chameleon_port:
            raise ValueError(
                    'Port %s is not connected to Chameleon' % interface)
        return chameleon_port


class ChameleonLineOutOutputWidgetHandler(ChameleonOutputWidgetHandler):
    """
    This class abstracts a Chameleon usb audio output widget handler.

    """

    _DEFAULT_DATA_FORMAT = dict(file_type='raw',
                                sample_format='S32_LE',
                                channel=8,
                                rate=48000)

    def set_playback_data(self, test_data):
        """Sets data to play.

        Handles scale if needed. Creates a path and sends the scaled data to
        Chameleon at that path.

        @param test_data: An AudioTestData object.

        @return: The remote data path on Chameleon.

        """
        self._test_data_for_chameleon_format = self._DEFAULT_DATA_FORMAT
        return self._scale_and_send_playback_data(test_data)



class CrosWidgetHandler(WidgetHandler):
    """
    This class abstracts a Cros device audio widget handler.

    Properties:
        _audio_facade: An AudioFacadeRemoteAdapter to access Cros device
                       audio functionality.

    """
    def __init__(self, audio_facade):
        """Initializes a CrosWidgetHandler.

        @param audio_facade: An AudioFacadeRemoteAdapter to access Cros device
                             audio functionality.

        """
        self._audio_facade = audio_facade

    def plug(self):
        """Plugs this widget."""
        logging.info('CrosWidgetHandler: plug')

    def unplug(self):
        """Unplugs this widget."""
        logging.info('CrosWidgetHandler: unplug')


class CrosInputWidgetHandlerError(Exception):
    """Error in CrosInputWidgetHandler."""


class CrosInputWidgetHandler(CrosWidgetHandler):
    """
    This class abstracts a Cros device audio input widget handler.

    """
    _DEFAULT_DATA_FORMAT = dict(file_type='raw',
                                sample_format='S16_LE',
                                channel=1,
                                rate=48000)
    _recording_on = None
    _SELECTED = "Selected"

    def start_recording(self, node_type=None, block_size=None):
        """Starts recording audio.

        @param node_type: A Cras node type defined in cras_utils.CRAS_NODE_TYPES
        @param block_size: The number for frames per callback.

        @raises: CrosInputWidgetHandlerError if a recording was already started.
        """
        if self._recording_on:
            raise CrosInputWidgetHandlerError(
                    "A recording was already started on %s." %
                    self._recording_on)

        self._recording_on = node_type if node_type else self._SELECTED
        self._audio_facade.start_recording(self._DEFAULT_DATA_FORMAT, node_type,
                                           block_size)


    def stop_recording(self, node_type=None):
        """Stops recording audio.

        @param node_type: A Cras node type defined in cras_utils.CRAS_NODE_TYPES

        @returns:
            A tuple (remote_path, format).
                remote_path: The path to the recorded file on Cros device.
                format: A dict containing:
                    file_type: 'raw'.
                    sample_format: 'S16_LE' for 16-bit signed integer in
                                   little-endian.
                    channel: channel number.
                    rate: sampling rate.

        @raises: CrosInputWidgetHandlerError if no corresponding responding
        device could be stopped.
        """
        if self._recording_on is None:
            raise CrosInputWidgetHandlerError("No recording was started.")

        if node_type is None and self._recording_on != self._SELECTED:
            raise CrosInputWidgetHandlerError(
                    "No recording on selected device.")

        if node_type and node_type != self._recording_on:
            raise CrosInputWidgetHandlerError(
                    "No recording was started on %s." % node_type)

        self._recording_on = None
        return (self._audio_facade.stop_recording(node_type=node_type),
                self._DEFAULT_DATA_FORMAT)


    def get_recorded_binary(self, remote_path, record_format):
        """Gets remote recorded file binary.

        Gets and reads recorded file from Cros device.

        @param remote_path: The path to the recorded file on Cros device.
        @param record_format: The recorded data format. A dict containing
                     file_type: 'raw' or 'wav'.
                     sample_format: 'S32_LE' for 32-bit signed integer in
                                    little-endian. Refer to aplay manpage for
                                    other formats.
                     channel: channel number.
                     rate: sampling rate.

        @returns: The recorded binary.

        @raises: CrosInputWidgetHandlerError if record_format is not correct.
        """
        if record_format != self._DEFAULT_DATA_FORMAT:
            raise CrosInputWidgetHandlerError(
                    'Record format %r is not valid' % record_format)

        with tempfile.NamedTemporaryFile(prefix='recorded_') as f:
            self._audio_facade.get_recorded_file(remote_path, f.name)
            return open(f.name, "rb").read()


class CrosUSBInputWidgetHandler(CrosInputWidgetHandler):
    """
    This class abstracts a Cros device audio input widget handler.

    """
    _DEFAULT_DATA_FORMAT = dict(file_type='raw',
                                sample_format='S16_LE',
                                channel=2,
                                rate=48000)


class CrosHotwordingWidgetHandler(CrosInputWidgetHandler):
    """
    This class abstracts a Cros device audio input widget handler on hotwording.

    """
    _DEFAULT_DATA_FORMAT = dict(file_type='raw',
                                sample_format='S16_LE',
                                channel=1,
                                rate=16000)

    def __init__(self, audio_facade, system_facade):
        """Initializes a CrosWidgetHandler.

        @param audio_facade: An AudioFacadeRemoteAdapter to access Cros device
                             audio functionality.
        @param system_facade: A SystemFacadeRemoteAdapter to access Cros device
                             system functionality.

        """
        super(CrosHotwordingWidgetHandler, self).__init__(
                audio_facade)
        self._system_facade = system_facade


    def start_listening(self):
        """Start listening to hotword."""
        self._audio_facade.start_listening(self._DEFAULT_DATA_FORMAT)


    def stop_listening(self):
        """Stops listening to hotword."""
        return self._audio_facade.stop_listening(), self._DEFAULT_DATA_FORMAT


class CrosOutputWidgetHandlerError(Exception):
    """The error in CrosOutputWidgetHandler."""
    pass


class CrosOutputWidgetHandler(CrosWidgetHandler):
    """
    This class abstracts a Cros device audio output widget handler.

    """
    _DEFAULT_DATA_FORMAT = dict(file_type='raw',
                                sample_format='S16_LE',
                                channel=2,
                                rate=48000)

    def set_playback_data(self, test_data):
        """Sets data to play.

        @param test_data: An AudioTestData object.

        @returns: The remote file path on Cros device.

        """
        # TODO(cychiang): Do format conversion on Cros device if this is
        # needed.
        if test_data.data_format != self._DEFAULT_DATA_FORMAT:
            raise CrosOutputWidgetHandlerError(
                    'File format conversion for cros device is not supported.')
        return self._audio_facade.set_playback_file(test_data.path)


    def start_playback(self, path, blocking=False, node_type=None,
                       block_size=None):
        """Starts playing audio.

        @param path: The path to the file to play on Cros device.
        @param blocking: Blocks this call until playback finishes.
        @param node_type: A Cras node type defined in cras_utils.CRAS_NODE_TYPES
        @param block_size: The number for frames per callback.

        """
        self._audio_facade.playback(path, self._DEFAULT_DATA_FORMAT, blocking,
                node_type, block_size)

    def stop_playback(self):
        """Stops playing audio."""
        self._audio_facade.stop_playback()


class PeripheralWidgetHandler(object):
    """
    This class abstracts an action handler on peripheral.
    Currently, as there is no action to take on the peripheral speaker and mic,
    this class serves as a place-holder.

    """
    pass


class PeripheralWidget(AudioWidget):
    """
    This class abstracts a peripheral widget which only acts passively like
    peripheral speaker or microphone, or acts transparently like bluetooth
    module on audio board which relays the audio siganl between Chameleon board
    and Cros device. This widget does not provide playback/record function like
    AudioOutputWidget or AudioInputWidget. The main purpose of this class is
    an identifier to find the correct AudioWidgetLink to do the real work.
    """
    pass
