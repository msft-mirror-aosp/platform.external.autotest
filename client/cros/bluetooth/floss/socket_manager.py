# Lint as:python3
# Copyright 2022 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Client class to access the Floss socket manager interface."""

from enum import IntEnum
from gi.repository import GLib
import logging
import math
import random

from autotest_lib.client.bin import utils
from autotest_lib.client.cros.bluetooth.floss.observer_base import ObserverBase
from autotest_lib.client.cros.bluetooth.floss.utils import (glib_call,
                                                            glib_callback)


class BtStatus(IntEnum):
    """Bluetooth return status."""
    SUCCESS = 0
    FAIL = 1
    NOT_READY = 2
    NO_MEMORY = 3
    BUSY = 4
    DONE = 5
    UNSUPPORTED = 6
    INVALID_PARAM = 7
    UNHANDLED = 8
    AUTH_FAILURE = 9
    REMOTE_DEVICE_DOWN = 10
    AUTH_REJECTED = 11
    JNI_ENVIRONMENT_ERROR = 12
    JNI_THREAD_ATTACH_ERROR = 13
    WAKE_LOCK_ERROR = 14


class SocketType(IntEnum):
    """Socket types."""
    GT_SOCK_ANY = 0
    GT_SOCK_STREAM = 1
    GT_SOCK_DGRAM = 2
    GT_SOCK_RAW = 3
    GT_SOCK_RDM = 4
    GT_SOCK_SEQPACKET = 5
    GT_SOCK_DCCP = 6
    GT_SOCK_PACKET = 10


class SocketManagerCallbacks:
    """Callbacks for the socket manager interface.

    Implement this to observe these callbacks when exporting callbacks via
    register_callback.
    """

    def on_incoming_socket_ready(self, socket, status):
        """Called when incoming socket is ready.

        @param socket: BluetoothServerSocket.
        @param status: BtStatus.
        """
        pass

    def on_incoming_socket_closed(self, listener_id, reason):
        """Called when incoming socket is closed.

        @param listener_id: SocketId.
        @param reason: BtStatus.
        """
        pass

    def on_handle_incoming_connection(self, listener_id, connection):
        """Called when incoming connection is handled.

        @param listener_id: SocketId.
        @param connection: BluetoothSocket.
        """
        pass

    def on_outgoing_connection_result(self, connecting_id, result, socket):
        """Called when outgoing connection is handled.

        @param connecting_id: SocketId.
        @param result: BtStatus.
        @param socket: BluetoothSocket.
        """
        pass


class FlossSocketManagerClient(SocketManagerCallbacks):
    """Handles method calls and callbacks from the socket manager interface."""

    ADAPTER_SERVICE = 'org.chromium.bluetooth'
    SOCKET_MANAGER_INTERFACE = 'org.chromium.bluetooth.SocketManager'
    ADAPTER_OBJECT_PATTERN = '/org/chromium/bluetooth/hci{}/adapter'
    SOCKET_CB_OBJ_PATTERN = '/org/chromium/bluetooth/hci{}/test_socket_client{}'
    CB_EXPORTED_INTF = 'org.chromium.bluetooth.SocketManagerCallback'
    FLOSS_RESPONSE_LATENCY_SECS = 3

    class ExportedSocketManagerCallbacks(ObserverBase):
        """
        <node>
            <interface name="org.chromium.bluetooth.SocketManagerCallback">
                <method name="OnIncomingSocketReady">
                    <arg type="a{sv}" name="socket" direction="in" />
                    <arg type="u" name="status" direction="in" />
                </method>
                <method name="OnIncomingSocketClosed">
                    <arg type="t" name="listener_id" direction="in" />
                    <arg type="u" name="reason" direction="in" />
                </method>
                <method name="OnHandleIncomingConnection">
                    <arg type="t" name="listener_id" direction="in" />
                    <arg type="a{sv}" name="connection" direction="in" />
                </method>
                <method name="OnOutgoingConnectionResult">
                    <arg type="t" name="connecting_id" direction="in" />
                    <arg type="u" name="result" direction="in" />
                    <arg type="a{sv}" name="socket" direction="in" />
                </method>
            </interface>
        </node>
        """

        def __init__(self):
            """Construct exported callbacks object."""
            ObserverBase.__init__(self)

        def OnIncomingSocketReady(self, socket, status):
            """Handle incoming socket ready callback."""
            for observer in self.observers.values():
                observer.on_incoming_socket_ready(socket, status)

        def OnIncomingSocketClosed(self, listener_id, reason):
            """Handle incoming socket closed callback."""
            for observer in self.observers.values():
                observer.on_incoming_socket_closed(listener_id, reason)

        def OnHandleIncomingConnection(self, listener_id, connection):
            """Handle incoming socket connection callback."""
            for observer in self.observers.values():
                observer.on_handle_incoming_connection(listener_id, connection)

        def OnOutgoingConnectionResult(self, connecting_id, result, socket):
            """Handle outgoing socket connection callback."""
            for observer in self.observers.values():
                observer.on_outgoing_connection_result(connecting_id, result,
                                                       socket)

    def __init__(self, bus, hci):
        self.bus = bus
        self.hci = hci
        self.callbacks = None
        self.callback_id = None
        self.objpath = self.ADAPTER_OBJECT_PATTERN.format(hci)
        self.ready_sockets = {}

    def __del__(self):
        """Destructor"""
        del self.callbacks

    @glib_callback()
    def on_incoming_socket_ready(self, socket, status):
        """Handle incoming socket ready callback."""
        logging.debug('on_incoming_socket_ready: socket: %s, status: %s',
                      socket, status)
        if BtStatus(status) != BtStatus.SUCCESS:
            return
        socket_id = socket['id']
        self.ready_sockets[socket_id] = (socket, status)

    @glib_callback()
    def on_incoming_socket_closed(self, listener_id, reason):
        """Handle incoming socket closed callback."""
        logging.debug('on_incoming_socket_closed: listener_id: %s, reason: %s',
                      listener_id, reason)

    @glib_callback()
    def on_handle_incoming_connection(self, listener_id, connection):
        """Handle incoming socket connection callback."""
        logging.debug(
                'on_handle_incoming_connection: listener_id: %s,'
                ' connection: %s', listener_id, connection)

    @glib_callback()
    def on_outgoing_connection_result(self, connecting_id, result, socket):
        """Handle outgoing socket connection callback."""
        logging.debug(
                'on_outgoing_connection_result: connecting_id: %s, '
                'result: %s, socket: %s', connecting_id, result, socket)

    def _make_dbus_device(self, address, name):
        return {
                'address': GLib.Variant('s', address),
                'name': GLib.Variant('s', name)
        }

    def _make_dbus_timeout(self, timeout):
        return {'timeout_ms': GLib.Variant('i', timeout)}

    @glib_call(False)
    def has_proxy(self):
        """Checks whether manager proxy can be acquired."""
        return bool(self.proxy())

    def proxy(self):
        """Gets proxy object to socket manager interface for method calls."""
        return self.bus.get(self.ADAPTER_SERVICE,
                            self.objpath)[self.SOCKET_MANAGER_INTERFACE]

    @glib_call(False)
    def register_callbacks(self):
        """Registers socket manager callbacks if one doesn't already exist."""
        # Callbacks already registered
        if self.callbacks:
            return True

        # Generate a random number between 1-1000
        rnumber = math.floor(random.random() * 1000 + 1)

        # Create and publish callbacks
        self.callbacks = self.ExportedSocketManagerCallbacks()
        self.callbacks.add_observer('socket_client', self)
        objpath = self.SOCKET_CB_OBJ_PATTERN.format(self.hci, rnumber)

        self.bus.register_object(objpath, self.callbacks, None)

        # Register published callbacks with adapter daemon
        self.callback_id = self.proxy().RegisterCallback(objpath)
        return True

    def wait_for_incoming_socket_ready(self, socket_id):
        """Waits for incoming socket ready.

        @param socket_id: Socket id.

        @return: Socket, status for specific socket_id on success,
                (None, None) otherwise.
        """
        try:
            utils.poll_for_condition(
                    condition=(lambda: socket_id in self.ready_sockets),
                    timeout=self.FLOSS_RESPONSE_LATENCY_SECS)
        except TimeoutError:
            logging.error('on_incoming_socket_ready not called')
            return None, None
        socket, status = self.ready_sockets[socket_id]

        return socket, status

    @glib_call(None)
    def listen_using_l2cap_channel(self):
        """Listens using L2CAP channel.

        @return: SocketResult as {status:BtStatus, id:int} on success,
                 None otherwise.
        """
        return self.proxy().ListenUsingL2capChannel(self.callback_id)

    @glib_call(None)
    def listen_using_insecure_l2cap_channel(self):
        """Listens using insecure L2CAP channel.

        @return: SocketResult as {status:BtStatus, id:int} on success,
                 None otherwise.
        """

        return self.proxy().ListenUsingInsecureL2capChannel(self.callback_id)

    @glib_call(None)
    def listen_using_insecure_rfcomm_with_service_record(self, name, uuid):
        """Listens using insecure RFCOMM channel with service record.

        @param name: Service name.
        @param uuid: 128-bit service UUID.

        @return: SocketResult as {status:BtStatus, id:int} on success,
                 None otherwise.
        """
        return self.proxy().ListenUsingInsecureRfcommWithServiceRecord(
                self.callback_id, name, uuid)

    @glib_call(None)
    def listen_using_rfcomm_with_service_record(self, name, uuid):
        """Listens using RFCOMM channel with service record.

        @param name: Service name.
        @param uuid: 128-bit service UUID.

        @return: SocketResult as {status:BtStatus, id:int} on success,
                 None otherwise.
        """
        return self.proxy().ListenUsingRfcommWithServiceRecord(
                self.callback_id, name, uuid)

    def listen_using_rfcomm_with_service_record_sync(self, name, uuid):
        """Listens using RFCOMM channel with service record sync.

        @param name: Service name.
        @param uuid: 128-bit service UUID.

        @return: BluetoothServerSocket on success, None otherwise.
        """
        socket_result = self.listen_using_rfcomm_with_service_record(
                name, uuid)
        # Failed if we have issue in D-bus (None) or returned non success
        # status.
        if socket_result is None or socket_result['status'] != BtStatus.SUCCESS:
            logging.error('Failed to listen using rfcomm socket with service '
                          'record')
            return None

        socket_id = socket_result['id']
        server_socket, status = self.wait_for_incoming_socket_ready(socket_id)
        if BtStatus(status) != BtStatus.SUCCESS:
            logging.error('Failed to start socket with id: %s, '
                          'status = %s' % (socket_id, status))
            return None
        return socket_result

    @glib_call(None)
    def create_insecure_l2cap_channel(self, device, psm):
        """Creates insecure L2CAP channel.

        @param device: D-bus device.
        @param psm: Protocol Service Multiplexor.

        @return: SocketResult as {status:BtStatus, id:int} on success,
                 None otherwise.
        """
        return self.proxy().CreateInsecureL2capChannel(self.callback_id,
                                                       device, psm)

    @glib_call(None)
    def create_l2cap_channel(self, device, psm):
        """Creates L2CAP channel.

        @param device: D-bus device.
        @param psm: Protocol Service Multiplexor.

        @return: SocketResult as {status:BtStatus, id:int} on success,
                 None otherwise.
        """

        return self.proxy().CreateL2capChannel(self.callback_id, device, psm)

    @glib_call(None)
    def create_insecure_rfcomm_socket_to_service_record(self, device, uuid):
        """Creates insecure RFCOMM socket to service record.

        @param device: New D-bus device.
        @param uuid: 128-bit service UUID.

        @return: SocketResult as {status:BtStatus, id:int} on success,
                 None otherwise.
        """
        return self.proxy().CreateInsecureRfcommSocketToServiceRecord(
                self.callback_id, device, uuid)

    @glib_call(None)
    def create_rfcomm_socket_to_service_record(self, device, uuid):
        """Creates RFCOMM socket to service record.

        @param device: D-bus device.
        @param uuid: 128-bit service UUID.

        @return: SocketResult as {status:BtStatus, id:int} on success,
                 None otherwise.
        """
        return self.proxy().CreateRfcommSocketToServiceRecord(
                self.callback_id, device, uuid)

    @glib_call(None)
    def accept(self, socket_id, timeout_ms=None):
        """Accepts socket connection.

        @param socket_id: New address of the adapter.
        @param timeout_ms: Timeout in ms.

        @return: BtStatus as int on success, None otherwise.
        """
        timeout_ms = self._make_dbus_timeout(timeout_ms)
        return self.proxy().Accept(self.callback_id, socket_id, timeout_ms)
