# Lint as: python2, python3
# Copyright 2021 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Client class to access the Floss adapter interface."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from gi.repository import GLib
from uuid import UUID
import logging

from autotest_lib.client.bin import utils
from autotest_lib.client.cros.bluetooth.floss.floss_enums import (BondState,
                                                                  SdpType)
from autotest_lib.client.cros.bluetooth.floss.observer_base import ObserverBase
from autotest_lib.client.cros.bluetooth.floss.utils import (
        generate_dbus_cb_objpath, glib_call, glib_callback, PropertySet)


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

    def on_sdp_record_created(self, record, handle):
        """SDP record is created successfully with a handle.

        @param record: The record that is created.
        @param handle: The handle for removing the record.
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
    ADAPTER_CB_OBJ_NAME = 'test_adapter_client'
    ADAPTER_CONN_CB_INTF = 'org.chromium.bluetooth.BluetoothConnectionCallback'
    ADAPTER_CONN_CB_OBJ_NAME = 'test_connection_client'
    QA_INTERFACE = 'org.chromium.bluetooth.BluetoothQA'
    QA_LEGACY_INTERFACE = 'org.chromium.bluetooth.BluetoothQALegacy'

    DISCONNECTION_TIMEOUT = 5
    SDP_CREATE_TIMEOUT = 2
    SDP_RECORD_HEADER_FIELDS = {
            'sdp_type',
            'uuid',
            'service_name_length',
            'service_name',
            'rfcomm_channel_number',
            'l2cap_psm',
            'profile_version',
            'user1_len',
            'user1_data',
            'user2_len',
            'user2_data',
    }

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

    @staticmethod
    def check_sdp_record_header_fields(header):
        """Returns whether the header fields exactly match the API.

        @param header: The SDP record header dict. Only the keys will be used.
        """
        missing_fields = FlossAdapterClient.SDP_RECORD_HEADER_FIELDS - set(
                header.keys())
        redundant_fields = set(
                header.keys()) - FlossAdapterClient.SDP_RECORD_HEADER_FIELDS
        if missing_fields or redundant_fields:
            logging.error(
                    'SDP header fields mismatch: missing=%s, redundant=%s',
                    missing_fields, redundant_fields)
            return False
        return True

    @staticmethod
    def parse_dbus_sdp_record(sdp_record_dbus):
        """Parses and converts specific fields to the preferred types.

        @param sdp_record_dbus: Variant dict with signature a{sv}.

        @return: Parsed SDP record dict; None if failed.
        """
        if '0' not in sdp_record_dbus:
            logging.error('Invalid record received from DBus')
            return None

        record = {k: v for k, v in sdp_record_dbus['0'].items()}
        hdr = None
        sdp_type = None
        if 'hdr' in record:
            hdr = record['hdr']
            sdp_type = record['hdr'].get('sdp_type')
            if sdp_type == SdpType.RAW:
                logging.error('Invalid SDP record: Raw header is wrapped')
                return None
            # So far we only support RAW record in the test.
            logging.error('Unsupported SDP type: %s', sdp_type)
            return None
        else:
            # If no 'hdr' field, assume it's a raw header.
            hdr = record
            sdp_type = record.get('sdp_type')
            if sdp_type != SdpType.RAW:
                logging.error(
                        'Invalid SDP record: '
                        'Unwrapped record but sdp_type is %s', sdp_type)
                return None

        if not FlossAdapterClient.check_sdp_record_header_fields(hdr):
            return None
        hdr = {k: v for k, v in hdr.items()}
        hdr['sdp_type'] = SdpType(hdr['sdp_type'])
        hdr['uuid'] = UUID(bytes=bytes(hdr['uuid']))
        hdr['user1_data'] = bytes(hdr['user1_data'])
        hdr['user2_data'] = bytes(hdr['user2_data'])
        return hdr

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
                <method name="OnBondStateChanged">
                    <arg type="u" name="status" direction="in" />
                    <arg type="s" name="address" direction="in" />
                    <arg type="u" name="state" direction="in" />
                </method>
                <method name="OnSdpRecordCreated">
                    <arg type="a{sv}" name="record" direction="in" />
                    <arg type="i" name="handle" direction="in" />
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

        def OnBondStateChanged(self, status, address, state):
            """Handle bond state changed callbacks."""
            for observer in self.observers.values():
                observer.on_bond_state_changed(status, address, state)

        def OnSdpRecordCreated(self, record, handle):
            """Handle SDP record created callbacks."""
            record = FlossAdapterClient.parse_dbus_sdp_record(record)
            if record is None:
                return
            for observer in self.observers.values():
                observer.on_sdp_record_created(record, handle)

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
        self.remote_properties = None

        # The created SDP (record, handle) tuples, which are inserted by
        # on_sdp_record_created and consumed by wait_for_sdp_record_created.
        # Note that the callers are ALLOWED to register the same records
        # multiple times. Due to the Floss API restriction we are not able to
        # distinguish them in on_sdp_record_created.
        self.created_sdp_records = []
        # The created SDP handles. Used by remove_all_sdp_record.
        self.sdp_handles = set()

    def __del__(self):
        """Destructor"""
        del self.callbacks
        del self.connection_callbacks

    def _make_device(self, address, name, bond_state=None, connected=None):
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
                    for key, value in self.known_devices.items()
                    if value.get('bond_state', 0)
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

    @glib_callback()
    def on_sdp_record_created(self, record, handle):
        """SDP record is created successfully."""
        logging.debug('SDP record created: handle=%d record=%s', handle,
                      record)
        self.created_sdp_records.append((record, handle))
        self.sdp_handles.add(handle)

    def _make_dbus_device(self, address, name):
        return {
                'address': GLib.Variant('s', address),
                'name': GLib.Variant('s', name)
        }

    @glib_call(False)
    def has_proxy(self):
        """Checks whether adapter proxy can be acquired."""
        return bool(self.proxy())

    def proxy(self):
        """Gets proxy object to adapter interface for method calls."""
        return self.bus.get(self.ADAPTER_SERVICE,
                            self.objpath)[self.ADAPTER_INTERFACE]

    def qa_proxy(self):
        """Gets proxy object to QA interface for method calls."""
        return self.bus.get(self.ADAPTER_SERVICE,
                            self.objpath)[self.QA_INTERFACE]

    def qa_legacy_proxy(self):
        """Gets proxy object to QA Legacy interface for method calls."""
        return self.bus.get(self.ADAPTER_SERVICE,
                            self.objpath)[self.QA_LEGACY_INTERFACE]


    # TODO(b/227405934): Not sure we want GetRemoteRssi on adapter api since
    #                    it's unlikely to be accurate over time. Use a mock for
    #                    testing for now.
    def get_mock_remote_rssi(self, device):
        """Gets mock value for remote device rssi."""
        return -50

    def register_properties(self):
        """Registers a property set for this client."""
        self.properties = PropertySet({
                'Address': (self.proxy().GetAddress, None),
                'Name': (self.proxy().GetName, self.proxy().SetName),
                'Alias': (self._get_alias, None),
                'Modalias': (self._get_modalias, None),
                'Class': (self.proxy().GetBluetoothClass,
                          self.proxy().SetBluetoothClass),
                'Uuids': (self._get_uuids, None),
                'Discoverable':
                (self.proxy().GetDiscoverable, self.proxy().SetDiscoverable),
                'DiscoverableTimeout':
                (self.proxy().GetDiscoverableTimeout, None),
                'IsMultiAdvertisementSupported':
                (self.proxy().IsMultiAdvertisementSupported, None),
                'IsLeExtendedAdvertisingSupported':
                (self.proxy().IsLeExtendedAdvertisingSupported, None)
        })

        self.remote_properties = PropertySet({
                'Name': (self.proxy().GetRemoteName, None),
                'Type': (self.proxy().GetRemoteType, None),
                'Alias': (self.proxy().GetRemoteAlias, None),
                'Class': (self.proxy().GetRemoteClass, None),
                'WakeAllowed': (self.proxy().GetRemoteWakeAllowed, None),
                'Uuids': (self.proxy().GetRemoteUuids, None),
                'RSSI': (self.get_mock_remote_rssi, None),
        })

    def _get_alias(self):
        """Gets the adapter's alias name.

        It tries BluetoothQA interface first. In case it fails, use
        BluetoothQALegacy interface instead.
        """
        try:
            return self.qa_proxy().GetAlias()
        except:
            return self.qa_legacy_proxy().GetAlias()

    def _get_modalias(self):
        """Gets the adapter modalias name.

        It tries BluetoothQA interface first. In case it fails, use
        BluetoothQALegacy interface instead.
        """
        try:
            return self.qa_proxy().GetModalias()
        except:
            return self.qa_legacy_proxy().GetModalias()

    def _get_uuids(self):
        """Gets the UUIDs from the D-Bus.

        If D-Bus returns UUID as list of integers, converts the value to UUID
        string.

        @return: List of UUIDs in string representation.
        """

        uuids = self.proxy().GetUuids()

        # Type check: uuids should be subscriptable.
        try:
            first_uuid = uuids[0]
        except TypeError:
            return []

        if type(first_uuid) == str:
            return uuids

        uuid_list = []
        for uuid in uuids:
            uuid_hex = ''.join('{:02x}'.format(m) for m in uuid)
            uuid_list.append(str(UUID(uuid_hex)))
        return uuid_list

    @glib_call(False)
    def register_callbacks(self):
        """Registers callbacks for this client.

        This will also initialize properties and populate the list of bonded
        devices since this should be the first thing that gets called after we
        know that the adapter client has a valid proxy object.
        """
        # Make sure properties are registered
        if not self.properties:
            self.register_properties()

        # Prevent callback registration multiple times
        if self.callbacks and self.connection_callbacks:
            return True

        # Reset known devices
        self.known_devices.clear()

        if not self.callbacks:
            # Create and publish callbacks
            self.callbacks = self.ExportedAdapterCallbacks()
            self.callbacks.add_observer('adapter_client', self)
            objpath = generate_dbus_cb_objpath(self.ADAPTER_CB_OBJ_NAME,
                                               self.hci)
            self.bus.register_object(objpath, self.callbacks, None)

            # Register published callback with adapter daemon
            self.proxy().RegisterCallback(objpath)

        if not self.connection_callbacks:
            self.connection_callbacks = self.ExportedConnectionCallbacks(
                    self.bus, objpath)
            self.connection_callbacks.add_observer('adapter_client', self)
            objpath = generate_dbus_cb_objpath(self.ADAPTER_CONN_CB_OBJ_NAME,
                                               self.hci)
            self.bus.register_object(objpath, self.connection_callbacks, None)

            self.proxy().RegisterConnectionCallback(objpath)

        # Add bonded devices as known devices and set their initial connection
        # state
        bonded_devices = self.proxy().GetBondedDevices()
        for device in bonded_devices:
            (success, devtuple) = FlossAdapterClient.parse_dbus_device(device)
            if success:
                (address, name) = devtuple
                dev = self.known_devices.get(
                        address,
                        self._make_device(address,
                                          name,
                                          bond_state=BondState.BONDED))
                if dev['bond_state'] is None:
                    dev['bond_state'] = BondState.BONDED
                    logging.info('[%s:%s] initially bonded.', address, name)

                if dev['connected'] is None:
                    cstate = self.proxy().GetConnectionState(
                            self._make_dbus_device(address, name))
                    dev['connected'] = bool(cstate > 0)
                    logging.info('[%s:%s] initially connection state: %d.',
                                 address, name, cstate)

                self.known_devices[address] = dev

        return True

    def register_callback_observer(self, name, observer):
        """Add an observer for all callbacks.

        @param name: Name of the observer.
        @param observer: Observer that implements all callback classes.
        """
        if isinstance(observer, BluetoothCallbacks):
            self.callbacks.add_observer(name, observer)

        if isinstance(observer, BluetoothConnectionCallbacks):
            self.connection_callbacks.add_observer(name, observer)

    def unregister_callback_observer(self, name, observer):
        """Remove an observer for all callbacks.

        @param name: Name of the observer.
        @param observer: Observer that implements all callback classes.
        """
        if isinstance(observer, BluetoothCallbacks):
            self.callbacks.remove_observer(name, observer)

        if isinstance(observer, BluetoothConnectionCallbacks):
            self.connection_callbacks.remove_observer(name, observer)

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

    def get_properties(self):
        """Gets all adapter properties.

        @return A dict of adapter's property names and properties.
        """
        return {p: self.get_property(p) for p in
                self.properties.get_property_names()}

    def get_discoverable_timeout(self):
        """Gets the adapter's discoverable timeout."""
        return self.proxy().GetDiscoverableTimeout()

    @glib_call(None)
    def get_remote_property(self, address, prop_name):
        """Gets remote device property by name."""
        name = 'Test device'
        if address in self.known_devices:
            name = self.known_devices[address]['name']

        remote_device = self._make_dbus_device(address, name)
        return self.remote_properties.get(prop_name, remote_device)

    @glib_call(None)
    def set_property(self, prop_name, *args):
        """Sets property by name."""
        return self.properties.set(prop_name, *args)

    @glib_call(None)
    def set_remote_property(self, address, prop_name, *args):
        """Sets remote property by name."""
        name = 'Test device'
        if address in self.known_devices:
            name = self.known_devices[address]['name']

        remote_device = self._make_dbus_device(address, name)
        return self.properties.set(prop_name, remote_device, *args)

    @glib_call(None)
    def is_le_extended_advertising_supported(self):
        """Is LE extended advertising supported?"""
        return bool(self.proxy().IsLeExtendedAdvertisingSupported())

    @glib_call(None)
    def is_multi_advertisement_supported(self):
        """Checks if multiple advertisements are supported.

        @return: True on success, False on failure, None on DBus error.
        """
        return bool(self.proxy().IsMultiAdvertisementSupported())

    @glib_call(False)
    def start_discovery(self):
        """Starts discovery session."""
        return bool(self.proxy().StartDiscovery())

    @glib_call(False)
    def stop_discovery(self):
        """Stops discovery session."""
        return bool(self.proxy().CancelDiscovery())

    @glib_call(False)
    def is_wbs_supported(self):
        """Is WBS supported?"""
        return bool(self.proxy().IsWbsSupported())

    @glib_call(False)
    def is_discovering(self):
        """Is adapter discovering?"""
        return bool(self.discovering)

    @glib_call(False)
    def has_device(self, address):
        """Checks to see if device with address is known."""
        return address in self.known_devices

    def is_bonded(self, address):
        """Checks if the given address is currently fully bonded."""
        return address in self.known_devices and self.known_devices[
                address].get('bond_state',
                             BondState.NOT_BONDED) == BondState.BONDED

    @glib_call(False)
    def create_bond(self, address, transport):
        """Creates bond with target address.
        """
        name = 'Test bond'
        if address in self.known_devices:
            name = self.known_devices[address]['name']

        remote_device = self._make_dbus_device(address, name)
        return bool(self.proxy().CreateBond(remote_device, int(transport)))

    @glib_call(False)
    def cancel_bond(self, address):
        """Call cancel bond with no additional checks. Prefer |forget_device|.

        @param address: Device to cancel bond.
        @returns Result of |CancelBondProcess|.
        """
        name = 'Test bond'
        if address in self.known_devices:
            name = self.known_devices[address]['name']

        remote_device = self._make_dbus_device(address, name)
        return bool(self.proxy().CancelBond(remote_device))

    @glib_call(False)
    def remove_bond(self, address):
        """Call remove bond with no additional checks. Prefer |forget_device|.

        @param address: Device to remove bond.
        @returns Result of |RemoveBond|.
        """
        name = 'Test bond'
        if address in self.known_devices:
            name = self.known_devices[address]['name']

        remote_device = self._make_dbus_device(address, name)
        return bool(self.proxy().RemoveBond(remote_device))

    @glib_call(False)
    def forget_device(self, address):
        """Forgets device from local cache and removes bonding.

        If a device is currently bonding or bonded, it will cancel or remove the
        bond to totally remove this device.

        @return
            True if device was known and was removed.
            False if device was unknown or removal failed.
        """
        if address not in self.known_devices:
            return False

        # Remove the device from known devices first
        device = self.known_devices[address]
        del self.known_devices[address]

        remote_device = self._make_dbus_device(device['address'],
                                               device['name'])

        # Extra actions if bond state is not NOT_BONDED
        if device['bond_state'] == BondState.BONDING:
            return bool(self.proxy().CancelBondProcess(remote_device))
        elif device['bond_state'] == BondState.BONDED:
            return bool(self.proxy().RemoveBond(remote_device))

        return True

    @glib_call(False)
    def set_pairing_confirmation(self, address, accept):
        """Confirm that a pairing should be completed on a bonding device."""
        # Device should be known or already `Bonding`
        if address not in self.known_devices:
            logging.debug('[%s] Unknown device in set_pairing_confirmation',
                          address)
            return False

        device = self.known_devices[address]
        remote_device = self._make_dbus_device(address, device['name'])

        return bool(self.proxy().SetPairingConfirmation(remote_device, accept))

    def get_connected_devices_count(self):
        """Gets the number of known, connected devices."""
        return sum([
                1 for x in self.known_devices.values()
                if x.get('connected', False)
        ])

    def is_connected(self, address):
        """Checks whether a device is connected."""
        return address in self.known_devices and self.known_devices[
                address].get('connected', False)

    @glib_call(False)
    def connect_all_enabled_profiles(self, address):
        """Connect all enabled profiles for target address."""
        device = self._make_dbus_device(
                address,
                self.known_devices.get(address, {}).get('name', 'Test device'))
        return bool(self.proxy().ConnectAllEnabledProfiles(device))

    @glib_call(False)
    def disconnect_all_enabled_profiles(self, address):
        """Disconnect all enabled profiles for target address."""
        device = self._make_dbus_device(
                address,
                self.known_devices.get(address, {}).get('name', 'Test device'))
        return bool(self.proxy().DisconnectAllEnabledProfiles(device))

    def wait_for_device_disconnected(self, address):
        """Waits for the device become disconnected."""
        def device_disconnected(self):
            return not self.known_devices.get(address, {}).get(
                    'connected', True)

        try:
            utils.poll_for_condition(
                    condition=(lambda: device_disconnected(self)),
                    timeout=self.DISCONNECTION_TIMEOUT)
            return True
        except utils.TimeoutError:
            logging.error('on_device_disconnected not called')
            return False

    def disconnect_device(self, address):
        """Disconnect a specific address."""
        return self.disconnect_all_enabled_profiles(
                address) and self.wait_for_device_disconnected(address)

    def make_default_sdp_record_header_dict(self):
        """Returns the default SDP record header with all required fields."""
        return {
                'sdp_type': 0,
                'uuid': UUID(bytes=bytes([0x00] * 16)),
                'service_name_length': 0,
                'service_name': '',
                'rfcomm_channel_number': 0,
                'l2cap_psm': 0,
                'profile_version': 0,
                'user1_len': 0,
                'user1_data': bytes(),
                'user2_len': 0,
                'user2_data': bytes(),
        }

    def _make_dbus_sdp_record(self, record):
        """Converts SDP record into DBus variant dict."""
        sdp_type = None
        hdr = None
        if 'hdr' in record:
            hdr = record['hdr']
            sdp_type = record['hdr'].get('sdp_type')
            if sdp_type == SdpType.RAW:
                logging.error('Invalid SDP record: Raw header is wrapped')
                return None
            # So far we only support RAW record in the test.
            logging.error('Unsupported SDP type: %s', sdp_type)
            return None
        else:
            # If no 'hdr' field, assume it's a raw header.
            hdr = record
            sdp_type = record.get('sdp_type')
            if sdp_type != SdpType.RAW:
                logging.error(
                        'Invalid SDP record: '
                        'Unwrapped record but sdp_type is %s', sdp_type)
                return None

        # Build header
        if not FlossAdapterClient.check_sdp_record_header_fields(hdr):
            return None
        hdr_dbus = {
                'sdp_type':
                GLib.Variant('u', hdr['sdp_type']),
                'uuid':
                GLib.Variant('ay', hdr['uuid'].bytes),
                'service_name_length':
                GLib.Variant('u', hdr['service_name_length']),
                'service_name':
                GLib.Variant('s', hdr['service_name']),
                'rfcomm_channel_number':
                GLib.Variant('i', hdr['rfcomm_channel_number']),
                'l2cap_psm':
                GLib.Variant('i', hdr['l2cap_psm']),
                'profile_version':
                GLib.Variant('i', hdr['profile_version']),
                'user1_len':
                GLib.Variant('i', hdr['user1_len']),
                'user1_data':
                GLib.Variant('ay', hdr['user1_data']),
                'user2_len':
                GLib.Variant('i', hdr['user2_len']),
                'user2_data':
                GLib.Variant('ay', hdr['user2_data']),
        }
        return {
                'type': GLib.Variant('u', sdp_type),
                '0': GLib.Variant('a{sv}', hdr_dbus),
        }

    @glib_call(False)
    def create_sdp_record(self, record):
        """Registers an SDP record to Floss.

        @param record: The record dict with all required fields.
                       Header field specification:
                           'sdp_type': SdpType
                           'uuid': UUID
                           'service_name': str
                           'user1_data': bytes
                           'user2_data': bytes
                           others: int

        @returns: True on success; False otherwise
        """
        record = self._make_dbus_sdp_record(record)
        if record is None:
            return False
        return bool(self.proxy().CreateSdpRecord(record))

    def wait_for_sdp_record_created(self, record):
        """Waits for the record to be created and returns the handle.

        @param record: Same param format as create_sdp_record

        @returns: The SDP record handle
        """
        logging.debug('Waiting for record to be created: %s', record)
        poll_result = [None]

        def is_record_created():
            for idx, (r, _) in enumerate(self.created_sdp_records):
                if r == record:
                    poll_result[0] = idx
                    return True
            return False

        try:
            utils.poll_for_condition(condition=is_record_created,
                                     timeout=self.SDP_CREATE_TIMEOUT)
            idx = poll_result[0]
            _, h = self.created_sdp_records.pop(idx)
            return h
        except utils.TimeoutError:
            logging.error('on_device_disconnected not called')
            return None

    def create_sdp_record_sync(self, record):
        """Registers and waits until the SDP record is created.

        @param record: Same param format as create_sdp_record

        @returns: The SDP record handle
        """
        success = self.create_sdp_record(record)
        if not success:
            logging.error('Failed to create SDP record')
            return None
        return self.wait_for_sdp_record_created(record)

    @glib_call(False)
    def remove_sdp_record(self, handle):
        """Removes the SDP record with the handle.

        @param handle: The SDP handle

        @returns: True on success; False otherwise
        """
        if handle not in self.sdp_handles:
            logging.error('Removing unknown SDP handle')
            return False
        self.sdp_handles.remove(handle)
        return bool(self.proxy().RemoveSdpRecord(handle))

    def remove_all_sdp_record(self):
        """Removes all SDP records.

        @returns: True if all removal succeeded; False otherwise
        """
        success = True
        for h in self.sdp_handles:
            if not self.remove_sdp_record(h):
                logging.error('Failed to remove SDP handle=%d', h)
                success = False
        self.sdp_handles.clear()
        return success
