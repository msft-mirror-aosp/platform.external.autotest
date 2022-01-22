# Lint as: python2, python3
# Copyright 2021 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Client class to access the Floss adapter interface."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from enum import Enum
import logging
import math
import random

from autotest_lib.client.cros.bluetooth.floss.observer_base import ObserverBase
from autotest_lib.client.cros.bluetooth.floss.utils import (glib_call,
                                                            glib_callback,
                                                            PropertySet)

class BondState(Enum):
    """Bluetooth bonding state."""
    NOT_BONDED = 0
    BONDING = 1
    BONDED = 2


class BluetoothCallbacks:
    """Callbacks for the Adapter Interface.

    Implement this to observe these callbacks when exporting callbacks via
    register_callback.
    """
    def on_address_changed(self, addr):
        """Adapter address changed.

        @param addr: New address of the adapter.
        """
        pass

    def on_device_found(self, remote_device):
        """Device found via discovery.

        @param remote_device: Remove device found during discovery session.
        """
        pass

    def on_discovering_changed(self, discovering):
        """Discovering state has changed.

        @param discovering: Whether discovery enabled or disabled.
        """
        pass

    def on_ssp_request(self, remote_device, class_of_device, variant, passkey):
        """Simple secure pairing request for agent to reply.

        @param remote_device: Remote device that is being paired.
        @param class_of_device: Class of device as described in HCI spec.
        @param variant: SSP variant (0-3). [Confirmation, Entry, Consent, Notification]
        @param passkey: Passkey to display (so user can confirm or type it).
        """
        pass

    def on_bond_state_changed(self, status, device_address, state):
        """Bonding/Pairing state has changed for a device.

        @param status: Success (0) or failure reason for bonding.
        @param device_address: This notification is for this BDADDR.
        @param state: Bonding state. 0 = Not bonded, 1 = Bonding, 2 = Bonded.
        """
        pass


class BluetoothConnectionCallbacks:
    """Callbacks for the Device Connection interface.

    Implement this to observe these callbacks when exporting callbacks via
    register_connection_callback
    """
    def on_device_connected(self, remote_device):
        """Notification that a device has completed HCI connection.

        @param remote_device: Remote device that completed HCI connection.
        """
        pass

    def on_device_disconnected(self, remote_device):
        """Notification that a device has completed HCI disconnection.

        @param remote_device: Remote device that completed HCI disconnection.
        """
        pass


class FlossAdapterClient(BluetoothCallbacks, BluetoothConnectionCallbacks):
    """Handles method calls to and callbacks from the Adapter interface."""

    ADAPTER_SERVICE = 'org.chromium.bluetooth'
    ADAPTER_INTERFACE = 'org.chromium.bluetooth.Bluetooth'
    ADAPTER_OBJECT_PATTERN = '/org/chromium/bluetooth/hci{}/adapter'
    ADAPTER_CB_INTF = 'org.chromium.bluetooth.BluetoothCallback'
    ADAPTER_CB_OBJ_PATTERN = '/org/chromium/bluetooth/hci{}/test_adapter_client{}'
    ADAPTER_CONN_CB_INTF = 'org.chromium.bluetooth.BluetoothConnectionCallback'
    ADAPTER_CONN_CB_OBJ_PATTERN = '/org/chromium/bluetooth/hci{}/test_connection_client{}'

    @staticmethod
    def parse_dbus_device(remote_device_dbus):
        """Parse a dbus variant dict as a remote device.

        @param remote_device_dbus: Variant dict with signature a{sv}.

        @return Parsing success, BluetoothDevice tuple
        """
        if 'address' in remote_device_dbus and 'name' in remote_device_dbus:
            return True, (str(remote_device_dbus['address']),
                          str(remote_device_dbus['name']))

        return False, None

    class ExportedAdapterCallbacks(ObserverBase):
        """
        <node>
            <interface name="org.chromium.bluetooth.BluetoothCallback">
                <method name="OnAddressChanged">
                    <arg type="s" name="addr" direction="in" />
                </method>
                <method name="OnDeviceFound">
                    <arg type="a{sv}" name="remote_device_dbus" direction="in" />
                </method>
                <method name="OnDiscoveringChanged">
                    <arg type="b" name="discovering" direction="in" />
                </method>
                <method name="OnSspRequest">
                    <arg type="a{sv}" name="remote_device_dbus" direction="in" />
                    <arg type="u" name="class_of_device" direction="in" />
                    <arg type="u" name="variant" direction="in" />
                    <arg type="u" name="passkey" direction="in" />
                </method>
            </interface>
        </node>
        """
        def __init__(self):
            """Construct exported callbacks object.
            """
            ObserverBase.__init__(self)

        def OnAddressChanged(self, addr):
            """Handle address changed callbacks."""
            for observer in self.observers.values():
                observer.on_address_changed(addr)

        def OnDeviceFound(self, remote_device_dbus):
            """Handle device found from discovery."""
            parsed, remote_device = FlossAdapterClient.parse_dbus_device(
                    remote_device_dbus)
            if not parsed:
                logging.debug('OnDeviceFound parse error: {}'.format(
                        remote_device_dbus))
                return

            for observer in self.observers.values():
                observer.on_device_found(remote_device)

        def OnDiscoveringChanged(self, discovering):
            """Handle discovering state changed."""
            for observer in self.observers.values():
                observer.on_discovering_changed(bool(discovering))

        def OnSspRequest(self, remote_device_dbus, class_of_device, variant,
                         passkey):
            """Handle pairing/bonding request to agent."""
            parsed, remote_device = FlossAdapterClient.parse_dbus_device(
                    remote_device_dbus)
            if not parsed:
                logging.debug('OnSspRequest parse error: {}'.format(
                        remote_device_dbus))
                return

            for observer in self.observers.values():
                observer.on_ssp_request(remote_device, class_of_device,
                                        variant, passkey)

    class ExportedConnectionCallbacks(ObserverBase):
        """
        <node>
            <interface name="org.chromium.bluetooth.BluetoothConnectionCallback">
                <method name="OnDeviceConnected">
                    <arg type="a{sv}" name="remote_device_dbus" direction="in" />
                </method>
                <method name="OnDeviceDisconnected">
                    <arg type="a{sv}" name="remote_device_dbus" direction="in" />
                </method>
            </interface>
        </node>
        """
        def __init__(self, bus, object_path):
            """Construct exported connection callbacks object.
            """
            ObserverBase.__init__(self)

        def OnDeviceConnected(self, remote_device_dbus):
            """Handle device connected."""
            parsed, remote_device = FlossAdapterClient.parse_dbus_device(
                    remote_device_dbus)
            if not parsed:
                logging.debug('OnDeviceConnected parse error: {}'.format(
                        remote_device_dbus))
                return

            for observer in self.observers.values():
                observer.on_device_connected(remote_device)

        def OnDeviceDisconnected(self, remote_device_dbus):
            """Handle device disconnected."""
            parsed, remote_device = FlossAdapterClient.parse_dbus_device(
                    remote_device_dbus)
            if not parsed:
                logging.debug('OnDeviceDisconnected parse error: {}'.format(
                        remote_device_dbus))
                return

            for observer in self.observers.values():
                observer.on_device_disconnected(remote_device)

    def __init__(self, bus, hci):
        """Construct the client.

        @param bus: DBus bus over which we'll establish connections.
        @param hci: HCI adapter index. Get this value from `get_default_adapter`
                    on FlossManagerClient.
        """
        self.bus = bus
        self.hci = hci
        self.objpath = self.ADAPTER_OBJECT_PATTERN.format(hci)

        # We don't register callbacks by default.
        self.callbacks = None
        self.connection_callbacks = None

        # Locally cached values
        self.known_devices = {}
        self.discovering = False

        # Initialize properties when registering callbacks (we know proxy is
        # valid at this point).
        self.properties = None

    def __del__(self):
        """Destructor"""
        del self.callbacks
        del self.connection_callbacks

    def _make_device(self,
                     address,
                     name,
                     bond_state=BondState.NOT_BONDED,
                     connected=False):
        """Make a device dict."""
        return {
                'address': address,
                'name': name,
                'bond_state': bond_state,
                'connected': connected,
        }

    @glib_callback()
    def on_device_found(self, remote_device):
        """Remote device was found as part of discovery."""
        address, name = remote_device

        # Update a new device
        if not address in self.known_devices:
            self.known_devices[address] = self._make_device(address, name)
        # Update name if previous cached value didn't have a name
        elif not self.known_devices[address]:
            self.known_devices[address]['name'] = name

    @glib_callback()
    def on_discovering_changed(self, discovering):
        """Discovering state has changed."""
        # Ignore a no-op
        if self.discovering == discovering:
            return

        # Cache the value
        self.discovering = discovering

        # If we are freshly starting discoveyr, clear all locally cached known
        # devices (that are not bonded or connected)
        if discovering:
            # Filter known devices to currently bonded or connected devices
            self.known_devices = {
                    key: value
                    for key, value in self.known_devices
                    if value.get('bond_state', 0) > 0
                    or value.get('connected', False)
            }

    @glib_callback()
    def on_bond_state_changed(self, status, address, state):
        """Bond state has changed."""
        # You can bond unknown devices if it was previously bonded
        if not address in self.known_devices:
            self.known_devices[address] = self._make_device(
                    address,
                    '',
                    bond_state=state,
            )
        else:
            self.known_devices[address]['bond_state'] = state

    @glib_callback()
    def on_device_connected(self, remote_device):
        """Remote device connected hci."""
        address, name = remote_device
        if not address in self.known_devices:
            self.known_devices[address] = self._make_device(address,
                                                            name,
                                                            connected=True)
        else:
            self.known_devices[address]['connected'] = True

    @glib_callback()
    def on_device_disconnected(self, remote_device):
        """Remote device disconnected hci."""
        address, name = remote_device
        if not address in self.known_devices:
            self.known_devices[address] = self._make_device(address,
                                                            name,
                                                            connected=False)
        else:
            self.known_devices[address]['connected'] = False

    @glib_call(False)
    def has_proxy(self):
        """Checks whether adapter proxy can be acquired."""
        return bool(self.proxy())

    def proxy(self):
        """Gets proxy object to adapter interface for method calls."""
        return self.bus.get(self.ADAPTER_SERVICE,
                            self.objpath)[self.ADAPTER_INTERFACE]

    def register_properties(self):
        """Registers a property set for this client."""
        self.properties = PropertySet({
                'Address': {(self.proxy().GetAddress, None)},
                'Name': {(self.proxy().GetName, self.proxy().SetName)},
                'Class': {(self.proxy().GetBluetoothClass,
                           self.proxy().SetBluetoothClass)},
                'Uuids': {(self.proxy().GetUuids, None)},
        })

    @glib_call(False)
    def register_callbacks(self):
        # Make sure properties are registered
        if not self.properties:
            self.register_properties()

        if self.callbacks and self.connection_callbacks:
            return True

        # Generate a random number between 1-1000
        rnumber = math.floor(random.random() * 1000 + 1)

        if not self.callbacks:
            # Create and publish callbacks
            self.callbacks = self.ExportedAdapterCallbacks()
            self.callbacks.add_observer('adapter_client', self)
            objpath = self.ADAPTER_CB_OBJ_PATTERN.format(self.hci, rnumber)
            self.bus.register_object(objpath, self.callbacks, None)

            # Register published callback with adapter daemon
            self.proxy().RegisterCallback(objpath)

        if not self.connection_callbacks:
            self.connection_callbacks = self.ExportedConnectionCallbacks(
                    self.bus, objpath)
            self.connection_callbacks.add_observer('adapter_client', self)
            objpath = self.ADAPTER_CONN_CB_OBJ_PATTERN.format(
                    self.hci, rnumber)
            self.bus.register_object(objpath, self.connection_callbacks, None)

            self.proxy().RegisterConnectionCallback(objpath)

        return True

    @glib_call('')
    def get_address(self):
        """Gets the adapter's current address."""
        return str(self.proxy().GetAddress())

    @glib_call('')
    def get_name(self):
        """Gets the adapter's name."""
        return str(self.proxy().GetName())

    @glib_call(None)
    def get_property(self, prop_name):
        """Gets property by name."""
        return self.properties.get(prop_name)

    @glib_call(False)
    def start_discovery(self):
        """Starts discovery session."""
        return bool(self.proxy().StartDiscovery())

    @glib_call(False)
    def stop_discovery(self):
        """Stops discovery session."""
        return bool(self.proxy().CancelDiscovery())

    @glib_call(False)
    def is_discovering(self):
        """Is adapter discovering?"""
        return bool(self.discovering)

    @glib_call(False)
    def has_device(self, address):
        """Checks to see if device with address is known."""
        return address in self.known_devices

    @glib_call(False)
    def forget_device(self, address):
        """Forgets device from local cache and removes bonding.

        If a device is currently bonding or bonded, it will cancel or remove the
        bond to totally remove this device.

        Returns:
            True if device was known and was removed.
            False if device was unknown or removal failed.
        """
        if address not in self.known_devices:
            return False

        # Remove the device from known devices first
        device = self.known_devices[address]
        del self.known_devices[address]

        remote_device = {'address': device['address'], 'name': device['name']}

        # Extra actions if bond state is not NOT_BONDED
        if device['bond_state'] == BondState.BONDING:
            return bool(self.proxy().CancelBondProcess(remote_device))
        elif device['bond_state'] == BondState.BONDED:
            return bool(self.proxy().RemoveBond(remote_device))

        return True

    @glib_call(False)
    def connect_all_enabled_profiles(self, address):
        """Connect all enabled profiles for target address."""
        device = {
                'address': address,
                'name': self.known_devices.get(address,
                                               {}).get('name', 'Test device')
        }
        return bool(self.proxy().ConnectAllEnabledProfiles(device))

    @glib_call(False)
    def disconnect_all_enabled_profiles(self, address):
        """Disconnect all enabled profiles for target address."""
        device = {
                'address': address,
                'name': self.known_devices.get(address,
                                               {}).get('name', 'Test device')
        }
        return bool(self.proxy().DisconnectAllEnabledProfiles(device))
