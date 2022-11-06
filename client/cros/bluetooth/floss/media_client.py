# Lint as:python3
# Copyright 2022 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Client class to access the Floss media interface."""

from enum import Enum
from gi.repository import GLib
import logging
import math
import random

from autotest_lib.client.cros.bluetooth.floss.observer_base import ObserverBase
from autotest_lib.client.cros.bluetooth.floss.utils import (glib_call,
                                                            glib_callback)

class BluetoothMediaCallbacks:
    """Callbacks for the media interface.

    Implement this to observe these callbacks when exporting callbacks via
    register_callback.
    """

    def on_bluetooth_audio_device_added(self, device):
        """Called when a Bluetooth audio device is added.

        @param device: The struct of BluetoothAudioDevice.
        """
        pass

    def on_bluetooth_audio_device_removed(self, addr):
        """Called when a Bluetooth audio device is removed.

        @param addr: Address of device to be removed.
        """
        pass

    def on_absolute_volume_supported_changed(self, supported):
        """Called when the support of using absolute volume is changed.

        @param supported: The boolean value indicates whether the supported
                          volume has changed.
        """
        pass

    def on_absolute_volume_changed(self, volume):
        """Called when the absolute volume is changed.

        @param volume: The value of volume.
        """
        pass

    def on_hfp_volume_changed(self, volume, addr):
        """Called when the HFP volume is changed.

        @param volume: The value of volume.
        @param addr: Device address to get the HFP volume.
        """
        pass

    def on_hfp_audio_disconnected(self, addr):
        """Called when the HFP audio is disconnected.

        @param addr: Device address to get the HFP state.
        """
        pass


class FlossMediaClient(BluetoothMediaCallbacks):
    """Handles method calls to and callbacks from the media interface."""

    MEDIA_SERVICE = 'org.chromium.bluetooth'
    MEDIA_INTERFACE = 'org.chromium.bluetooth.BluetoothMedia'
    MEDIA_OBJECT_PATTERN = '/org/chromium/bluetooth/hci{}/media'

    MEDIA_CB_INTF = 'org.chromium.bluetooth.BluetoothMediaCallback'
    MEDIA_CB_OBJ_PATTERN = '/org/chromium/bluetooth/hci{}/test_media_client{}'

    class ExportedMediaCallbacks(ObserverBase):
        """
        <node>
            <interface name="org.chromium.bluetooth.BluetoothMediaCallback">
                <method name="OnBluetoothAudioDeviceAdded">
                    <arg type="a{sv}" name="device" direction="in" />
                </method>
                <method name="OnBluetoothAudioDeviceRemoved">
                    <arg type="s" name="addr" direction="in" />
                </method>
                <method name="OnAbsoluteVolumeSupportedChanged">
                    <arg type="b" name="supported" direction="in" />
                </method>
                <method name="OnAbsoluteVolumeChanged">
                    <arg type="b" name="volume" direction="in" />
                </method>
                <method name="OnHfpVolumeChanged">
                    <arg type="b" name="volume" direction="in" />
                    <arg type="s" name="addr" direction="in" />
                </method>
                <method name="OnHfpAudioDisconnected">
                    <arg type="s" name="addr" direction="in" />
                </method>
            </interface>
        </node>
        """

        def __init__(self):
            """Constructs exported callbacks object."""
            ObserverBase.__init__(self)

        def OnBluetoothAudioDeviceAdded(self, device):
            """Handles Bluetooth audio device added callback.

            @param device: The struct of BluetoothAudioDevice.
            """
            for observer in self.observers.values():
                observer.on_bluetooth_audio_device_added(device)

        def OnBluetoothAudioDeviceRemoved(self, addr):
            """Handles Bluetooth audio device removed callback.

            @param addr: Address of device to be removed.
            """
            for observer in self.observers.values():
                observer.on_bluetooth_audio_device_removed(addr)

        def OnAbsoluteVolumeSupportedChanged(self, supported):
            """Handles absolute volume supported changed callback.

            @param supported: The boolean value indicates whether the supported
                              volume has changed.
            """
            for observer in self.observers.values():
                observer.on_absolute_volume_supported_changed(supported)

        def OnAbsoluteVolumeChanged(self, volume):
            """Handles absolute volume changed callback.

            @param volume: The value of volume.
            """
            for observer in self.observers.values():
                observer.on_absolute_volume_changed(volume)

        def OnHfpVolumeChanged(self, volume, addr):
            """Handles HFP volume changed callback.

            @param volume: The value of volume.
            @param addr: Device address to get the HFP volume.
            """
            for observer in self.observers.values():
                observer.on_hfp_volume_changed(volume, addr)

        def OnHfpAudioDisconnected(self, addr):
            """Handles HFP audio disconnected callback.

            @param addr: Device address to get the HFP state.
            """
            for observer in self.observers.values():
                observer.on_hfp_audio_disconnected(addr)

    def __init__(self, bus, hci):
        """Constructs the client.

        @param bus: D-Bus bus over which we'll establish connections.
        @param hci: HCI adapter index. Get this value from 'get_default_adapter'
                    on FlossManagerClient.
        """
        self.bus = bus
        self.hci = hci
        self.objpath = self.MEDIA_OBJECT_PATTERN.format(hci)

        # We don't register callbacks by default.
        self.callbacks = None

    def __del__(self):
        """Destructor"""
        del self.callbacks

    @glib_callback()
    def on_bluetooth_audio_device_added(self, device):
        """Handles Bluetooth audio device added callback.

        @param device: The struct of BluetoothAudioDevice.
        """
        logging.debug('on_bluetooth_audio_device_added: device: %s', device)

    @glib_callback()
    def on_bluetooth_audio_device_removed(self, addr):
        """Handles Bluetooth audio device removed callback.

        @param addr: Address of device to be removed.
        """
        logging.debug('on_bluetooth_audio_device_removed: address: %s', addr)

    @glib_callback()
    def on_absolute_volume_supported_changed(self, supported):
        """Handles absolute volume supported changed callback.

        @param supported: The boolean value indicates whether the supported
                          volume has changed.
        """
        logging.debug('on_absolute_volume_supported_changed: supported: %s',
                      supported)

    @glib_callback()
    def on_absolute_volume_changed(self, volume):
        """Handles absolute volume changed callback.

        @param volume: The value of volume.
        """
        logging.debug('on_absolute_volume_changed: volume: %s', volume)

    @glib_callback()
    def on_hfp_volume_changed(self, volume, addr):
        """Handles HFP volume changed callback.

        @param volume: The value of volume.
        @param addr: Device address to get the HFP volume.
        """
        logging.debug('on_hfp_volume_changed: volume: %s, address: %s', volume,
                      addr)

    @glib_callback()
    def on_hfp_audio_disconnected(self, addr):
        """Handles HFP audio disconnected callback.

        @param addr: Device address to get the HFP state.
        """
        logging.debug('on_hfp_audio_disconnected: address: %s', addr)

    def make_dbus_player_metadata(self, title, artist, album, length):
        """Makes struct for player metadata D-Bus.

        @param title: The title of player metadata.
        @param artist: The artist of player metadata.
        @param album: The album of player metadata.
        @param length: The value of length metadata.

        @return: Dictionary of player metadata.
        """
        return {
            'title': GLib.Variant('s', title),
            'artist': GLib.Variant('s', artist),
            'album': GLib.Variant('s', album),
            'length': GLib.Variant('x', length)
        }

    @glib_call(False)
    def has_proxy(self):
        """Checks whether the media proxy is present."""
        return bool(self.proxy())

    def proxy(self):
        """Gets a proxy object to media interface for method calls."""
        return self.bus.get(self.MEDIA_SERVICE,
                            self.objpath)[self.MEDIA_INTERFACE]

    @glib_call(None)
    def register_callback(self):
        """Registers a media callback if it doesn't exist."""

        if self.callbacks:
            return True

        # Generate a random number between 1-1000
        rnumber = math.floor(random.random() * 1000 + 1)

        # Create and publish callbacks
        self.callbacks = self.ExportedMediaCallbacks()

        self.callbacks.add_observer('media_client', self)
        objpath = self.MEDIA_CB_OBJ_PATTERN.format(self.hci, rnumber)
        self.bus.register_object(objpath, self.callbacks, None)

        # Register published callbacks with media daemon
        return self.proxy().RegisterCallback(objpath)

    @glib_call(None)
    def initialize(self):
        """Initializes the media (both A2DP and AVRCP) stack.

        @return: True on success, False on failure, None on DBus error.
        """
        return self.proxy().Initialize()

    @glib_call(None)
    def cleanup(self):
        """Cleans up media stack.

        @return: True on success, False on failure, None on DBus error.
        """
        return self.proxy().Cleanup()

    @glib_call(False)
    def connect(self, address):
        """Connects to a Bluetooth media device with the specified address.

        @param address: Device address to connect.

        @return: True on success, False otherwise.
        """
        self.proxy().Connect(address)
        return True

    @glib_call(False)
    def disconnect(self, address):
        """Disconnects the specified Bluetooth media device.

        @param address: Device address to disconnect.

        @return: True on success, False otherwise.
        """
        self.proxy().Disconnect(address)
        return True

    @glib_call(False)
    def set_active_device(self, address):
        """Sets the device as the active A2DP device.

        @param address: Device address to set as an active A2DP device.

        @return: True on success, False otherwise.
        """
        self.proxy().SetActiveDevice(address)
        return True

    @glib_call(False)
    def set_hfp_active_device(self, address):
        """Sets the device as the active HFP device.

        @param address: Device address to set as an active HFP device.

        @return: True on success, False otherwise.
        """
        self.proxy().SetHfpActiveDevice(address)
        return True

    @glib_call(None)
    def set_audio_config(self, sample_rate, bits_per_sample, channel_mode):
        """Sets audio configuration.

        @param sample_rate: Value of sample rate.
        @param bits_per_sample: Number of bits per sample.
        @param channel_mode: Value of channel mode.

        @return: True on success, False on failure, None on DBus error.
        """
        return self.proxy().SetAudioConfig(sample_rate, bits_per_sample,
                                           channel_mode)

    @glib_call(False)
    def set_volume(self, volume):
        """Sets the A2DP/AVRCP volume.

        @param volume: The value of volume to set it.

        @return: True on success, False otherwise.
        """
        self.proxy().SetVolume(volume)
        return True

    @glib_call(False)
    def set_hfp_volume(self, volume, address):
        """Sets the HFP speaker volume.

        @param volume: The value of volume.
        @param address: Device address to set the HFP volume.

        @return: True on success, False otherwise.
        """
        self.proxy().SetHfpVolume(volume, address)
        return True

    @glib_call(False)
    def start_audio_request(self):
        """Starts audio request.

        @return: True on success, False otherwise.
        """
        self.proxy().StartAudioRequest()
        return True

    @glib_call(None)
    def get_a2dp_audio_started(self, address):
        """Gets A2DP audio started.

        @param address: Device address to get the A2DP state.

        @return: Non-zero value iff A2DP audio has started, None on D-Bus error.
        """
        return self.proxy().GetA2dpAudioStarted(address)

    @glib_call(False)
    def stop_audio_request(self):
        """Stops audio request.

        @return: True on success, False otherwise.
        """
        self.proxy().StopAudioRequest()
        return True

    @glib_call(False)
    def start_sco_call(self, address, sco_offload, force_cvsd):
        """Starts the SCO call.

        @param address: Device address to make SCO call.
        @param sco_offload: Whether SCO offload is enabled.
        @param force_cvsd: True to force the stack to use CVSD even if mSBC
                           is supported.

        @return: True on success, False otherwise.
        """
        self.proxy().StartScoCall(address, sco_offload, force_cvsd)
        return True

    @glib_call(None)
    def get_hfp_audio_started(self, address):
        """Gets HFP audio started.

        @param address: Device address to get the HFP state.

        @return: The negotiated codec (CVSD=1, mSBC=2) to use if HFP audio has
                 started; 0 if HFP audio hasn't started. None on DBus error.
        """
        return self.proxy().GetHfpAudioStarted(address)

    @glib_call(False)
    def stop_sco_call(self, address):
        """Stops the SCO call.

        @param address: Device address to stop SCO call.

        @return: True on success, False otherwise.
        """
        self.proxy().StopScoCall(address)
        return True

    @glib_call(None)
    def get_presentation_position(self):
        """Gets presentation position.

        @return: PresentationPosition struct on success, None otherwise.
        """
        return self.proxy().GetPresentationPosition()

    @glib_call(False)
    def set_player_position(self, position_us):
        """Sets player position.

        @param position_us: The player position in microsecond.

        @return: True on success, False otherwise.
        """
        self.proxy().SetPlayerPosition(position_us)
        return True

    @glib_call(False)
    def set_player_playback_status(self, status):
        """Sets player playback status.

        @param status: Playback status such as 'playing', 'paused', 'stopped'
                       as string.

        @return: True on success, False otherwise.
        """
        self.proxy().SetPlayerPlaybackStatus(status)
        return True

    @glib_call(False)
    def set_player_metadata(self, metadata):
        """Sets player metadata.

        @param metadata: The media metadata to set it.

        @return: True on success, False otherwise.
        """
        self.proxy().SetPlayerMetadata(metadata)
        return True
