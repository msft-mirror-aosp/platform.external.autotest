# Lint as:python3
# Copyright 2023 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Client Class to access the Floss GATT client interface."""

from enum import IntEnum
import logging

from autotest_lib.client.bin import utils
from autotest_lib.client.cros.bluetooth.floss.observer_base import ObserverBase
from autotest_lib.client.cros.bluetooth.floss.utils import (
        generate_dbus_cb_objpath, glib_call, glib_callback)


class BtTransport(IntEnum):
    """Bluetooth transport type."""
    AUTO = 0
    BR_EDR = 1
    LE = 2


class GattWriteType(IntEnum):
    """GATT write type."""
    INVALID = 0
    WRITE_NO_RSP = 1
    WRITE = 2
    WRITE_PREPARE = 3


class LePhy(IntEnum):
    """Bluetooth LE physical type."""
    INVALID = 0
    PHY1M = 1
    PHY2M = 2
    PHY_CODED = 3


class GattStatus(IntEnum):
    """Bluetooth GATT return status."""
    SUCCESS = 0x00
    INVALID_HANDLE = 0x01
    READ_NOT_PERMIT = 0x02
    WRITE_NOT_PERMIT = 0x03
    INVALID_PDU = 0x04
    INSUF_AUTHENTICATION = 0x05
    REQ_NOT_SUPPORTED = 0x06
    INVALID_OFFSET = 0x07
    INSUF_AUTHORIZATION = 0x08
    PREPARE_Q_FULL = 0x09
    NOT_FOUND = 0x0A
    NOT_LONG = 0x0B
    INSUF_KEY_SIZE = 0x0C
    INVALID_ATTRLEN = 0x0D
    ERR_UNLIKELY = 0x0E
    INSUF_ENCRYPTION = 0x0F
    UNSUPPORT_GRP_TYPE = 0x10
    INSUF_RESOURCE = 0x11
    DATABASE_OUT_OF_SYNC = 0x12
    VALUE_NOT_ALLOWED = 0x13
    ILLEGAL_PARAMETER = 0x87
    TOO_SHORT = 0x7F
    NO_RESOURCES = 0x80
    INTERNAL_ERROR = 0x81
    WRONG_STATE = 0x82
    DB_FULL = 0x83
    BUSY = 0x84
    ERROR = 0x85
    CMD_STARTED = 0x86
    PENDING = 0x88
    AUTH_FAIL = 0x89
    MORE = 0x8A
    INVALID_CFG = 0x8B
    SERVICE_STARTED = 0x8C
    ENCRYPTED_NO_MITM = 0x8D
    NOT_ENCRYPTED = 0x8E
    CONGESTED = 0x8F
    DUP_REG = 0x90
    ALREADY_OPEN = 0x91
    CANCEL = 0x92


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

    def on_search_complete(self, addr, services, status):
        """Called when search completed.

        @param addr: Remote device MAC address.
        @param services: Bluetooth GATT services as list.
        @param status: Bluetooth GATT status.
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
                <method name="OnSearchComplete">
                    <arg type="s" name="addr" direction="in" />
                    <arg type="aa{sv}" name="services" direction="in" />
                    <arg type="u" name="status" direction="in" />
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

        def OnSearchComplete(self, addr, services, status):
            """Handles search complete callback.

            @param addr: Remote device MAC address.
            @param services: Bluetooth GATT services as list.
            @param status: Bluetooth GATT status.
            """
            for observer in self.observers.values():
                observer.on_search_complete(addr, services, status)

    def __init__(self, bus, hci):
        """Constructs the client.

        @param bus: D-Bus bus over which we'll establish connections.
        @param hci: HCI adapter index. Get this value from `get_default_adapter`
                    on FlossManagerClient.
        """

        self.bus = bus
        self.hci = hci
        self.callbacks = None
        self.callback_id = None
        self.objpath = self.GATT_OBJECT_PATTERN.format(hci)
        self.client_id = None
        self.gatt_services = {}
        self.connected_clients = {}

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

    @glib_call(False)
    def has_proxy(self):
        """Checks whether manager proxy can be acquired."""
        return bool(self.proxy())

    def proxy(self):
        """Gets proxy object to socket manager interface for method calls."""
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
    def discover_services(self, address):
        """Discovers remote device GATT services.

        @param address: Remote device MAC address.

        @return: True on success, False otherwise.
        """
        self.proxy().DiscoverServices(self.client_id, address)
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
        except TimeoutError:
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
        except TimeoutError:
            logging.error('on_search_complete not called')
            return False

    def connect_client_sync(self, address):
        """Connects GATT client.

        @param address: Remote device MAC address.

        @return: Client id.
        """
        self.connect_client(address=address)
        self.wait_for_client_connected(address)
        return self.connected_clients[address]

    def discover_services_sync(self, address):
        """Discovers remote device GATT services.

        @param address: Remote device MAC address.

        @return: Remote device GATT services as a list.
        """
        self.discover_services(address)
        self.wait_for_search_complete(address)
        return self.gatt_services[address]
