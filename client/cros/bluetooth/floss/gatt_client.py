# Lint as:python3
# Copyright 2023 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Client Class to access the Floss GATT client interface."""

import logging

from autotest_lib.client.bin import utils
from autotest_lib.client.cros.bluetooth.floss.floss_enums import (BtTransport,
                                                                  LePhy,
                                                                  GattStatus)
from autotest_lib.client.cros.bluetooth.floss.observer_base import ObserverBase
from autotest_lib.client.cros.bluetooth.floss.utils import (
        generate_dbus_cb_objpath, glib_call, glib_callback)


class GattClientCallbacks:
    """Callbacks for the GATT client interface.

    Implement this to observe these callbacks when exporting callbacks via
    register_client.
    """
    def on_client_registered(self, status, scanner_id):
        """Called when GATT client registered.

        @param status: Bluetooth GATT status.
        @param scanner_id: Bluetooth GATT scanner id.
        """
        pass

    def on_client_connection_state(self, status, client_id, connected, addr):
        """Called when GATT client connection state changed.

        @param status: Bluetooth GATT status.
        @param client_id: Bluetooth GATT client id.
        @param connected: A boolean value representing whether the device is
                          connected.
        @param addr: Remote device MAC address.
        """
        pass

    def on_phy_update(self, addr, tx_phy, rx_phy, status):
        """Called when GATT physical type is updated.

        @param addr: Remote device MAC address.
        @param tx_phy: Transmit physical type.
        @param rx_phy: Receive physical type.
        @param status: Bluetooth GATT status.
        """
        pass

    def on_phy_read(self, addr, tx_phy, rx_phy, status):
        """Called when GATT physical type is read.

        @param addr: Remote device MAC address.
        @param tx_phy: Transmit physical type.
        @param rx_phy: Receive physical type.
        @param status: Bluetooth GATT status.
        """
        pass

    def on_search_complete(self, addr, services, status):
        """Called when search completed.

        @param addr: Remote device MAC address.
        @param services: Bluetooth GATT services as list.
        @param status: Bluetooth GATT status.
        """
        pass

    def on_characteristic_read(self, addr, status, handle, value):
        """Called when characteristic is read.

        @param addr: Remote device MAC address.
        @param status: Bluetooth GATT status.
        @param handle: Characteristic handle id.
        @param value: Characteristic value.
        """
        pass

    def on_characteristic_write(self, addr, status, handle):
        """Called when characteristic is written.

        @param addr: Remote device MAC address.
        @param status: Bluetooth GATT status.
        @param handle: Characteristic handle id.
        """
        pass

    def on_execute_write(self, addr, status):
        """Called when execute write.

        @param addr: Remote device MAC address.
        @param status: Bluetooth GATT status.
        """
        pass

    def on_descriptor_read(self, addr, status, handle, value):
        """Called when descriptor is read.

        @param addr: Remote device MAC address.
        @param status: Bluetooth GATT status.
        @param handle: Descriptor handle id.
        @param value: Descriptor value.
        """
        pass

    def on_descriptor_write(self, addr, status, handle):
        """Called when descriptor is written.

        @param addr: Remote device MAC address.
        @param status: Bluetooth GATT status.
        @param handle: Descriptor handle id.
        """
        pass

    def on_notify(self, addr, handle, value):
        """Called when notified.

        @param addr: Remote device MAC address.
        @param handle: Characteristic handle id.
        @param value: Characteristic value.
        """
        pass

    def on_read_remote_rssi(self, addr, rssi, status):
        """Called when remote RSSI is read.

        @param addr: Remote device MAC address.
        @param rssi: RSSI value.
        @param status: Bluetooth GATT status.
        """
        pass

    def on_configure_mtu(self, addr, mtu, status):
        """Called when MTU is configured.

        @param addr: Remote device MAC address.
        @param mtu: MTU value.
        @param status: Bluetooth GATT status.
        """
        pass

    def on_connection_updated(self, addr, interval, latency, timeout, status):
        """Called when connection updated.

        @param addr: Remote device MAC address.
        @param interval: Interval in ms.
        @param latency: Latency in ms.
        @param timeout: Timeout in ms.
        @param status: Bluetooth GATT status.
        """
        pass

    def on_service_changed(self, addr):
        """Called when service changed.

        @param addr: Remote device MAC address.
        """
        pass


class FlossGattClient(GattClientCallbacks):
    """Handles method calls and callbacks from the GATT client interface."""

    ADAPTER_SERVICE = 'org.chromium.bluetooth'
    GATT_CLIENT_INTERFACE = 'org.chromium.bluetooth.BluetoothGatt'
    GATT_OBJECT_PATTERN = '/org/chromium/bluetooth/hci{}/gatt'
    GATT_CB_OBJ_NAME = 'test_gatt_client'
    CB_EXPORTED_INTF = 'org.chromium.bluetooth.BluetoothGattCallback'
    FLOSS_RESPONSE_LATENCY_SECS = 3

    class ExportedGattClientCallbacks(ObserverBase):
        """
        <node>
            <interface name="org.chromium.bluetooth.BluetoothGattCallback">
                <method name="OnClientRegistered">
                    <arg type="u" name="status" direction="in" />
                    <arg type="i" name="scanner_id" direction="in" />
                </method>
                <method name="OnClientConnectionState">
                    <arg type="u" name="status" direction="in" />
                    <arg type="i" name="client_id" direction="in" />
                    <arg type="b" name="connected" direction="in" />
                    <arg type="s" name="addr" direction="in" />
                </method>
                <method name="OnPhyUpdate">
                    <arg type="s" name="addr" direction="in" />
                    <arg type="u" name="tx_phy" direction="in" />
                    <arg type="u" name="rx_phy" direction="in" />
                    <arg type="u" name="status" direction="in" />
                </method>
                <method name="OnPhyRead">
                    <arg type="s" name="addr" direction="in" />
                    <arg type="u" name="tx_phy" direction="in" />
                    <arg type="u" name="rx_phy" direction="in" />
                    <arg type="u" name="status" direction="in" />
                </method>
                <method name="OnSearchComplete">
                    <arg type="s" name="addr" direction="in" />
                    <arg type="aa{sv}" name="services" direction="in" />
                    <arg type="u" name="status" direction="in" />
                </method>
                <method name="OnCharacteristicRead">
                    <arg type="s" name="addr" direction="in" />
                    <arg type="u" name="status" direction="in" />
                    <arg type="i" name="handle" direction="in" />
                    <arg type="ay" name="value" direction="in" />
                </method>
                <method name="OnCharacteristicWrite">
                    <arg type="s" name="addr" direction="in" />
                    <arg type="u" name="status" direction="in" />
                    <arg type="i" name="handle" direction="in" />
                </method>
                <method name="OnExecuteWrite">
                    <arg type="s" name="addr" direction="in" />
                    <arg type="u" name="status" direction="in" />
                </method>
                <method name="OnDescriptorRead">
                    <arg type="s" name="addr" direction="in" />
                    <arg type="u" name="status" direction="in" />
                    <arg type="i" name="handle" direction="in" />
                    <arg type="ay" name="value" direction="in" />
                </method>
                <method name="OnDescriptorWrite">
                    <arg type="s" name="addr" direction="in" />
                    <arg type="u" name="status" direction="in" />
                    <arg type="i" name="handle" direction="in" />
                </method>
                <method name="OnNotify">
                    <arg type="s" name="addr" direction="in" />
                    <arg type="i" name="handle" direction="in" />
                    <arg type="ay" name="value" direction="in" />
                </method>
                <method name="OnReadRemoteRssi">
                    <arg type="s" name="addr" direction="in" />
                    <arg type="i" name="rssi" direction="in" />
                    <arg type="u" name="status" direction="in" />
                </method>
                <method name="OnConfigureMtu">
                    <arg type="s" name="addr" direction="in" />
                    <arg type="i" name="mtu" direction="in" />
                    <arg type="u" name="status" direction="in" />
                </method>
                <method name="OnConnectionUpdated">
                    <arg type="s" name="addr" direction="in" />
                    <arg type="i" name="interval" direction="in" />
                    <arg type="i" name="latency" direction="in" />
                    <arg type="i" name="timeout" direction="in" />
                    <arg type="u" name="status" direction="in" />
                </method>
                <method name="OnServiceChanged">
                    <arg type="s" name="addr" direction="in" />
                </method>

            </interface>
        </node>
        """
        def __init__(self):
            """Constructs exported callbacks object."""
            ObserverBase.__init__(self)

        def OnClientRegistered(self, status, scanner_id):
            """Handles client registration callback.

            @param status: Bluetooth GATT status.
            @param scanner_id: Bluetooth GATT scanner id.
            """
            for observer in self.observers.values():
                observer.on_client_registered(status, scanner_id)

        def OnClientConnectionState(self, status, client_id, connected, addr):
            """Handles client connection state callback.

            @param status: Bluetooth GATT status.
            @param client_id: Bluetooth GATT client id.
            @param connected: A boolean value representing whether the device is
                              connected.
            @param addr: Remote device MAC address.
            """
            for observer in self.observers.values():
                observer.on_client_connection_state(status, client_id,
                                                    connected, addr)

        def OnPhyUpdate(self, addr, tx_phy, rx_phy, status):
            """Handles GATT physical type update callback.

            @param addr: Remote device MAC address.
            @param tx_phy: Transmit physical type.
            @param rx_phy: Receive physical type.
            @param status: Bluetooth GATT status.
            """
            for observer in self.observers.values():
                observer.on_phy_update(addr, tx_phy, rx_phy, status)

        def OnPhyRead(self, addr, tx_phy, rx_phy, status):
            """Handles GATT physical type read callback.

            @param addr: Remote device MAC address.
            @param tx_phy: Transmit physical type.
            @param rx_phy: Receive physical type.
            @param status: Bluetooth GATT status.
            """
            for observer in self.observers.values():
                observer.on_phy_read(addr, tx_phy, rx_phy, status)

        def OnSearchComplete(self, addr, services, status):
            """Handles search complete callback.

            @param addr: Remote device MAC address.
            @param services: Bluetooth GATT services as list.
            @param status: Bluetooth GATT status.
            """
            for observer in self.observers.values():
                observer.on_search_complete(addr, services, status)

        def OnCharacteristicRead(self, addr, status, handle, value):
            """Handles characteristic read callback.

            @param addr: Remote device MAC address.
            @param status: Bluetooth GATT status.
            @param handle: Characteristic handle id.
            @param value: Characteristic value.
            """
            for observer in self.observers.values():
                observer.on_characteristic_read(addr, status, handle, value)

        def OnCharacteristicWrite(self, addr, status, handle):
            """Handles characteristic write callback.

            @param addr: Remote device MAC address.
            @param status: Bluetooth GATT status.
            @param handle: Characteristic handle id.
            """
            for observer in self.observers.values():
                observer.on_characteristic_write(addr, status, handle)

        def OnExecuteWrite(self, addr, status):
            """Handles write execution callbacks.

            @param addr: Remote device MAC address.
            @param status: Bluetooth GATT status.
            """
            for observer in self.observers.values():
                observer.on_execute_write(addr, status)

        def OnDescriptorRead(self, addr, status, handle, value):
            """Handles descriptor read callback.

            @param addr: Remote device MAC address.
            @param status: Bluetooth GATT status.
            @param handle: Descriptor handle id.
            @param value: Descriptor value.
            """
            for observer in self.observers.values():
                observer.on_descriptor_read(addr, status, handle, value)

        def OnDescriptorWrite(self, addr, status, handle):
            """Handles descriptor write callback.

            @param addr: Remote device MAC address.
            @param status: Bluetooth GATT status.
            @param handle: Descriptor handle id.
            """
            for observer in self.observers.values():
                observer.on_descriptor_write(addr, status, handle)

        def OnNotify(self, addr, handle, value):
            """Handles notification callback.

            @param addr: Remote device MAC address.
            @param handle: Characteristic handle id.
            @param value: Characteristic value.
            """
            for observer in self.observers.values():
                observer.on_notify(addr, handle, value)

        def OnReadRemoteRssi(self, addr, rssi, status):
            """Handles remote RSSI value read callback.

            @param addr: Remote device MAC address.
            @param rssi: RSSI value.
            @param status: Bluetooth GATT status.
            """
            for observer in self.observers.values():
                observer.on_read_remote_rssi(addr, rssi, status)

        def OnConfigureMtu(self, addr, mtu, status):
            """Handles MTU configuration callback.

            @param addr: Remote device MAC address.
            @param mtu: MTU value.
            @param status: Bluetooth GATT status.
            """
            for observer in self.observers.values():
                observer.on_configure_mtu(addr, mtu, status)

        def OnConnectionUpdated(self, addr, interval, latency, timeout,
                                status):
            """Handles connection update callback.

            @param addr: Remote device MAC address.
            @param interval: Interval in ms.
            @param latency: Latency in ms.
            @param timeout: Timeout in ms.
            @param status: Bluetooth GATT status.
            """
            for observer in self.observers.values():
                observer.on_connection_updated(addr, interval, latency,
                                               timeout, status)

        def OnServiceChanged(self, addr):
            """Handles service changed callback.

            @param addr: Remote device MAC address.
            """
            for observer in self.observers.values():
                observer.on_service_changed(addr)

    def __init__(self, bus, hci, api_version):
        """Constructs the client.

        @param bus: D-Bus bus over which we'll establish connections.
        @param hci: HCI adapter index. Get this value from `get_default_adapter`
                    on FlossManagerClient.
        @param api_version: The Floss API version.
        """

        self.bus = bus
        self.hci = hci
        self.callbacks = None
        self.callback_id = None
        self.objpath = self.GATT_OBJECT_PATTERN.format(hci)
        self.client_id = None
        self.gatt_services = {}
        self.connected_clients = {}
        self.api_version = api_version

    def __del__(self):
        """Destructor"""
        del self.callbacks

    @glib_callback()
    def on_client_registered(self, status, scanner_id):
        """Handles client registration callback.

        @param status: Bluetooth GATT status.
        @param scanner_id: Bluetooth GATT scanner id.
        """
        logging.debug('on_client_registered: status: %s, scanner_id: %s',
                      status, scanner_id)

        if status != GattStatus.SUCCESS:
            logging.error('Failed to register client with id: %s, status = %s',
                          scanner_id, status)
            return
        self.client_id = scanner_id

    @glib_callback()
    def on_client_connection_state(self, status, client_id, connected, addr):
        """Handles client connection state callback.

        @param status: Bluetooth GATT status.
        @param client_id: Bluetooth GATT client id.
        @param connected: A boolean value representing whether the device is
                          connected.
        @param addr: Remote device MAC address.
        """
        logging.debug(
                'on_client_connection_state: status: %s, client_id: %s, '
                'connected: %s, addr: %s', status, client_id, connected, addr)
        if status != GattStatus.SUCCESS:
            return
        self.connected_clients[addr] = connected

    @glib_callback()
    def on_phy_update(self, addr, tx_phy, rx_phy, status):
        """Handles physical type update callback.

        @param addr: Remote device MAC address.
        @param tx_phy: Transmit physical type.
        @param rx_phy: Receive physical type.
        @param status: Bluetooth GATT status.
        """
        logging.debug(
                'on_phy_update: addr: %s, tx_phy: %s, rx_phy: %s, status: %s',
                addr, tx_phy, rx_phy, status)

    @glib_callback()
    def on_phy_read(self, addr, tx_phy, rx_phy, status):
        """Handles physical type read callback.

        @param addr: Remote device MAC address.
        @param tx_phy: Transmit physical type.
        @param rx_phy: Receive physical type.
        @param status: Bluetooth GATT status.
        """
        logging.debug(
                'on_phy_read: addr: %s, tx_phy: %s, rx_phy: %s, status: %s',
                addr, tx_phy, rx_phy, status)

    @glib_callback()
    def on_search_complete(self, addr, services, status):
        """Handles search complete callback.

        @param addr: Remote device MAC address.
        @param services: Bluetooth GATT services as list.
        @param status: Bluetooth GATT status.
        """
        logging.debug('on_search_complete: addr: %s, services: %s, status: %s',
                      addr, services, status)
        if status != GattStatus.SUCCESS:
            logging.error('Failed to complete search')
            return
        self.gatt_services[addr] = services

    @glib_callback()
    def on_characteristic_read(self, addr, status, handle, value):
        """Handles characteristic read callback.

        @param addr: Remote device MAC address.
        @param status: Bluetooth GATT status.
        @param handle: Characteristic handle id.
        @param value: Characteristic value.
        """
        logging.debug(
                'on_characteristic_read: addr: %s, status: %s, handle: %s, '
                'value: %s', addr, status, handle, value)

    @glib_callback()
    def on_characteristic_write(self, addr, status, handle):
        """Handles characteristic write callback.

        @param addr: Remote device MAC address.
        @param status: Bluetooth GATT status.
        @param handle: Characteristic handle id.
        """
        logging.debug(
                'on_characteristic_write: addr: %s, status: %s, handle: %s',
                addr, status, handle)

    @glib_callback()
    def on_execute_write(self, addr, status):
        """Handles write execution callbacks.

        @param addr: Remote device MAC address.
        @param status: Bluetooth GATT status.
        """
        logging.debug('on_execute_write: addr: %s, status: %s', addr, status)

    @glib_callback()
    def on_descriptor_read(self, addr, status, handle, value):
        """Handles descriptor read callback.

        @param addr: Remote device MAC address.
        @param status: Bluetooth GATT status.
        @param handle: Descriptor handle id.
        @param value: Descriptor value.
        """
        logging.debug(
                'on_descriptor_read: addr: %s, status: %s, handle: %s, value: '
                '%s', addr, status, handle, value)

    @glib_callback()
    def on_descriptor_write(self, addr, status, handle):
        """Handles descriptor write callback.

        @param addr: Remote device MAC address.
        @param status: Bluetooth GATT status.
        @param handle: Descriptor handle id.
        """
        logging.debug('on_descriptor_write: addr: %s, status: %s, handle: %s',
                      addr, status, handle)

    @glib_callback()
    def on_notify(self, addr, handle, value):
        """Handles notification callback.

        @param addr: Remote device MAC address.
        @param handle: Characteristic handle id.
        @param value: Characteristic value.
        """
        logging.debug('on_notify: addr: %s, handle: %s, value: %s', addr,
                      handle, value)

    @glib_callback()
    def on_read_remote_rssi(self, addr, rssi, status):
        """Handles remote RSSI value read callback.

        @param addr: Remote device MAC address.
        @param rssi: RSSI value.
        @param status: Bluetooth GATT status.
        """
        logging.debug('on_read_remote_rssi: addr: %s, rssi: %s, status: %s',
                      addr, rssi, status)

    @glib_callback()
    def on_configure_mtu(self, addr, mtu, status):
        """Handles MTU configuration callback.

        @param addr: Remote device MAC address.
        @param mtu: MTU value.
        @param status: Bluetooth GATT status.
        """
        logging.debug('on_configure_mtu: addr: %s, mtu: %s, status: %s', addr,
                      mtu, status)

    @glib_callback()
    def on_connection_updated(self, addr, interval, latency, timeout, status):
        """Handles connection update callback.

        @param addr: Remote device MAC address.
        @param interval: Interval in ms.
        @param latency: Latency in ms.
        @param timeout: Timeout in ms.
        @param status: Bluetooth GATT status.
        """
        logging.debug(
                'on_connection_updated: addr: %s, interval: %s, latency: %s, '
                'timeout: %s, status: %s', addr, interval, latency, timeout,
                status)

    @glib_callback()
    def on_service_changed(self, addr):
        """Handles service changed callback.

        @param addr: Remote device MAC address.
        """
        logging.debug('on_service_changed: addr: %s', addr)

    @glib_call(False)
    def has_proxy(self):
        """Checks whether GATT Client can be acquired."""
        return bool(self.proxy())

    def proxy(self):
        """Gets proxy object to GATT Client interface for method calls."""
        return self.bus.get(self.ADAPTER_SERVICE,
                            self.objpath)[self.GATT_CLIENT_INTERFACE]

    @glib_call(False)
    def register_client(self, app_uuid, eatt_support):
        """Registers GATT client callbacks if one doesn't already exist.

        @param app_uuid: GATT application uuid.
        @param eatt_support: A boolean value that indicates whether eatt is
                             supported.
        """
        # Callbacks already registered
        if self.callbacks:
            return True
        # Create and publish callbacks
        self.callbacks = self.ExportedGattClientCallbacks()
        self.callbacks.add_observer('gatt_testing_client', self)
        objpath = generate_dbus_cb_objpath(self.GATT_CB_OBJ_NAME, self.hci)
        self.bus.register_object(objpath, self.callbacks, None)
        # Register published callbacks with adapter daemon
        self.callback_id = self.proxy().RegisterClient(app_uuid, objpath,
                                                       eatt_support)
        return True

    @glib_call(False)
    def unregister_client(self):
        """Unregisters GATT client.

        @return: True on success, False otherwise.
        """
        self.proxy().UnregisterClient(self.client_id)
        return True

    @glib_call(False)
    def connect_client(self,
                       address,
                       is_direct=False,
                       transport=BtTransport.LE,
                       opportunistic=False,
                       phy=LePhy.PHY1M):
        """Connects GATT client.

        @param address: Remote device MAC address.
        @param is_direct: A boolean value represent direct status.
        @param transport: BtTransport type.
        @param opportunistic: A boolean value represent opportunistic status.
        @param phy: LePhy type.

        @return: True on success, False otherwise.
        """
        self.proxy().ClientConnect(self.client_id, address, is_direct,
                                   transport, opportunistic, phy)
        return True

    @glib_call(False)
    def disconnect_client(self, address):
        """Disconnects GATT client.

        @param address: Remote device MAC address.

        @return: True on success, False otherwise.
        """
        self.proxy().ClientDisconnect(self.client_id, address)
        return True

    @glib_call(False)
    def refresh_device(self, address):
        """Refreshes device.

        @param address: Remote device MAC address.

        @return: True on success, False otherwise.
        """
        self.proxy().RefreshDevice(self.client_id, address)
        return True

    @glib_call(False)
    def discover_services(self, address):
        """Discovers remote device GATT services.

        @param address: Remote device MAC address.

        @return: True on success, False otherwise.
        """
        self.proxy().DiscoverServices(self.client_id, address)
        return True

    @glib_call(False)
    def discover_service_by_uuid(self, address, uuid):
        """Discovers remote device GATT services by UUID.

        @param address: Remote device MAC address.
        @param uuid: The service UUID as a string.

        @return: True on success, False otherwise.
        """
        self.proxy().DiscoverServiceByUuid(self.client_id, address, uuid)
        return True

    @glib_call(False)
    def btif_gattc_discover_service_by_uuid(self, address, uuid):
        """Discovers remote device GATT services by UUID from btif layer.

        @param address: Remote device MAC address.
        @param uuid: The service UUID as a string.

        @return: True on success, False otherwise.
        """
        self.proxy().BtifGattcDiscoverServiceByUuid(self.client_id, address,
                                                    uuid)
        return True

    @glib_call(False)
    def read_characteristic(self, address, handle, auth_req):
        """Reads GATT characteristic.

        @param address: Remote device MAC address.
        @param handle: Characteristic handle id.
        @param auth_req: Authentication requirements value.

        @return: True on success, False otherwise.
        """
        self.proxy().ReadCharacteristic(self.client_id, address, handle,
                                        auth_req)
        return True

    @glib_call(False)
    def read_using_characteristic_uuid(self, address, uuid, start_handle,
                                       end_handle, auth_req):
        """Reads remote device GATT characteristic by UUID.

        @param address: Remote device MAC address.
        @param uuid: The characteristic UUID as a string.
        @param start_handle: Characteristic start handle id.
        @param end_handle: Characteristic end handle id.
        @param auth_req: Authentication requirements value.

        @return: True on success, False otherwise.
        """
        self.proxy().ReadUsingCharacteristicUuid(self.client_id, address, uuid,
                                                 start_handle, end_handle,
                                                 auth_req)
        return True

    @glib_call(None)
    def write_characteristic(self, address, uuid, handle, write_type, auth_req,
                             value):
        """Writes remote device GATT characteristic.

        @param address: Remote device MAC address.
        @param uuid: The characteristic UUID as a string.
        @param handle: Characteristic handle id.
        @param write_type: Characteristic write type.
        @param auth_req: Authentication requirements value.
        @param value: Characteristic value to write.

        @return: GattWriteRequestStatus on success, None otherwise.
        """
        return self.proxy().write_characteristic(self.client_id, address, uuid,
                                                 handle, write_type, auth_req,
                                                 value)

    @glib_call(False)
    def register_for_notification(self, address, handle, enable):
        """Registers for notification.

        @param address: Remote device MAC address.
        @param handle: Characteristic handle id.
        @param enable: Boolean value represents enabling or disabling notify.

        @return: True on success, False otherwise.
        """
        self.proxy().RegisterForNotification(self.client_id, address, handle,
                                             enable)
        return True

    @glib_call(False)
    def begin_reliable_write(self, address):
        """Begins a reliable write transaction.

        @param address: Remote device MAC address.

        @return: True on success, False otherwise.
        """
        self.proxy().BeginReliableWrite(self.client_id, address)
        return True

    @glib_call(False)
    def end_reliable_write(self, address, execute):
        """Ends the reliable write transaction.

        @param address: Remote device MAC address.
        @param execute: Boolean to execute or not.

        @return: True on success, False otherwise.
        """
        self.proxy().EndReliableWrite(self.client_id, address, execute)
        return True

    @glib_call(False)
    def read_remote_rssi(self, address):
        """Reads remote device RSSI.

        @param address: Remote device MAC address.

        @return: True on success, False otherwise.
        """
        self.proxy().ReadRemoteRssi(self.client_id, address)
        return True

    @glib_call(False)
    def configure_mtu(self, address, mtu):
        """Configures MTU value.

        @param address: Remote device MAC address.
        @param mtu: MTU value.

        @return: True on success, False otherwise.
        """
        self.proxy().ConfigureMtu(self.client_id, address, mtu)
        return True

    @glib_call(False)
    def update_connection_parameter(self, address, min_interval, max_interval,
                                    latency, timeout, min_ce_len, max_ce_len):
        """Updates connection parameters.

        @param address: Remote device MAC address.
        @param min_interval: Minimum interval in ms.
        @param max_interval: Maximum interval in ms.
        @param latency: Latency interval in ms.
        @param timeout: Timeout interval in ms.
        @param min_ce_len: Connection event minimum length in ms.
        @param max_ce_len: Connection event maximum length in ms.

        @return: True on success, False otherwise.
        """
        self.proxy().ConnectionParameterUpdate(self.client_id, address,
                                               min_interval, max_interval,
                                               latency, timeout, min_ce_len,
                                               max_ce_len)
        return True

    @glib_call(False)
    def set_preferred_phy(self, address, tx_phy, rx_phy, phy_options):
        """Sets remote device preferred physical options.

        @param address: Remote device MAC address.
        @param tx_phy: Transmit physical type.
        @param rx_phy: Receive physical type.
        @param phy_options: Physical options to use for connection.

        @return: True on success, False otherwise.
        """
        self.proxy().ClientSetPreferredPhy(self.client_id, address, tx_phy,
                                           rx_phy, phy_options)
        return True

    @glib_call(False)
    def read_phy(self, address):
        """Reads remote device physical setting.

        @param address: Remote device MAC address.

        @return: True on success, False otherwise.
        """
        self.proxy().ClientReadPhy(self.client_id, address)
        return True

    def wait_for_client_connected(self, address):
        """Waits for GATT client to be connected.

        @param address: Remote device MAC address.

        @return: True on success, False otherwise.
        """
        try:
            utils.poll_for_condition(
                    condition=lambda: self.connected_clients.get(address),
                    timeout=self.FLOSS_RESPONSE_LATENCY_SECS)
            return True

        except utils.TimeoutError:
            logging.error('on_client_connection_state not called')
            return False

    def wait_for_search_complete(self, address):
        """Waits for GATT search to be completed.

        @param address: Remote device MAC address.

        @return: True on success, False otherwise.
        """
        try:
            utils.poll_for_condition(
                    condition=lambda: address in self.gatt_services,
                    timeout=self.FLOSS_RESPONSE_LATENCY_SECS)
            return True

        except utils.TimeoutError:
            logging.error('on_search_complete not called')
            return False

    def connect_client_sync(self, address):
        """Connects GATT client.

        @param address: Remote device MAC address.

        @return: Client id on success, None otherwise.
        """
        self.connect_client(address=address)
        if not self.wait_for_client_connected(address):
            return None
        return self.connected_clients[address]

    def discover_services_sync(self, address):
        """Discovers remote device GATT services.

        @param address: Remote device MAC address.

        @return: Remote device GATT services as a list on success,
                 None otherwise.
        """
        self.discover_services(address)
        if not self.wait_for_search_complete(address):
            return None
        return self.gatt_services[address]
