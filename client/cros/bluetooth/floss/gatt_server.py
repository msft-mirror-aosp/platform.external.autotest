# Lint as:python3
# Copyright 2023 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Client Class to access the Floss GATT server interface."""

import logging

from autotest_lib.client.cros.bluetooth.floss.floss_enums import GattStatus
from autotest_lib.client.cros.bluetooth.floss.observer_base import ObserverBase
from autotest_lib.client.cros.bluetooth.floss.utils import (
        generate_dbus_cb_objpath, glib_call, glib_callback)


class GattServerCallbacks:
    """Callbacks for the GATT server interface.

    Implement this to observe these callbacks when exporting callbacks via
    register_server.
    """

    def on_server_registered(self, status, server_id):
        """Called when GATT server registered.

        @param status: Bluetooth GATT status.
        @param server_id: Bluetooth GATT server id.
        """
        pass

    def on_server_connection_state(self, server_id, connected, addr):
        """Called when GATT server connection state changed.

        @param server_id: Bluetooth GATT server id.
        @param connected: A boolean value that indicates whether the GATT server
                          is connected.
        @param addr: Remote device MAC address.
        """
        pass

    def on_service_added(self, status, service):
        """Called when service added.

        @param status: Bluetooth GATT status.
        @param service: BluetoothGattService.
        """
        pass

    def on_service_removed(self, status, handle):
        """Called when service removed.

        @param status: Bluetooth GATT status.
        @param handle: Service record handle.
        """
        pass

    def on_characteristic_read_request(self, addr, trans_id, offset, is_long,
                                       handle):
        """Called when there is a request to read a characteristic.

        @param addr: Remote device MAC address.
        @param trans_id: Transaction id.
        @param offset: Represents the offset from which the attribute value
                       should be read.
        @param is_long: A boolean value representing whether the characteristic
                        size is longer than what we can put in the ATT PDU.
        @param handle: The characteristic handle.
        """
        pass

    def on_descriptor_read_request(self, addr, trans_id, offset, is_long,
                                   handle):
        """Called when there is a request to read a descriptor.

        @param addr: Remote device MAC address.
        @param trans_id: Transaction id.
        @param offset: Represents the offset from which the descriptor value
                       should be read.
        @param is_long: A boolean value representing whether the descriptor size
                        is longer than what we can put in the ATT PDU.
        @param handle: The descriptor handle.
        """
        pass

    def on_characteristic_write_request(self, addr, trans_id, offset, len,
                                        is_prep, need_rsp, handle, value):
        """Called when there is a request to write a characteristic.

        @param addr: Remote device MAC address.
        @param trans_id: Transaction id.
        @param offset: Represents the offset at which the attribute value should
                       be written.
        @param len: The length of the attribute value that should be written.
        @param is_prep: A boolean value representing whether it's a "prepare
                        write" command.
        @param need_rsp: A boolean value representing whether it's a "write no
                         response" command.
        @param handle: The characteristic handle.
        @param value: The value that should be written to the attribute.
        """
        pass

    def on_descriptor_write_request(self, addr, trans_id, offset, len, is_prep,
                                    need_rsp, handle, value):
        """Called when there is a request to write a descriptor.

        @param addr: Remote device MAC address.
        @param trans_id: Transaction id.
        @param offset: The offset value at which the value should be written.
        @param len: The length of the value that should be written.
        @param is_prep: A boolean value representing whether it's a "prepare
                        write" command.
        @param need_rsp: A boolean value representing whether it's a "write no
                         response" command.
        @param handle: The descriptor handle.
        @param value: The value that should be written to the descriptor.
        """
        pass

    def on_execute_write(self, addr, trans_id, exec_write):
        """Called when execute write.

        @param addr: Remote device MAC address.
        @param trans_id: Transaction id.
        @param exec_write: A boolean value that indicates whether the write
                           operation should be executed or canceled.
        """
        pass

    def on_notification_sent(self, addr, status):
        """Called when notification sent.

        @param addr: Remote device MAC address.
        @param status: Bluetooth GATT status.
        """
        pass

    def on_mtu_changed(self, addr, mtu):
        """Called when the MTU changed.

        @param addr: Remote device MAC address.
        @param mtu: Maximum transmission unit.
        """
        pass

    def on_phy_update(self, addr, tx_phy, rx_phy, status):
        """Called when physical update.

        @param addr: Remote device MAC address.
        @param tx_phy: The new TX PHY for the connection.
        @param rx_phy: The new RX PHY for the connection.
        @param status: Bluetooth GATT status.
        """
        pass

    def on_phy_read(self, addr, tx_phy, rx_phy, status):
        """Called when physical read.

        @param addr: Remote device MAC address.
        @param tx_phy: The current transmit PHY for the connection.
        @param rx_phy: The current receive PHY for the connection.
        @param status: Bluetooth GATT status.
        """
        pass

    def on_connection_updated(self, addr, interval, latency, timeout, status):
        """Called when connection updated.

        @param addr: Remote device MAC address.
        @param interval: Connection interval value.
        @param latency: The number of consecutive connection events during which
                        the device doesn't have to be listening.
        @param timeout: Supervision timeout for this connection in milliseconds.
        @param status: Bluetooth GATT status.
        """
        pass

    def on_subrate_change(self, addr, subrate_factor, latency, cont_num,
                          timeout, status):
        """Called when subrate changed.

        @param addr: Remote device MAC address.
        @param subrate_factor: Subrate factor value.
        @param latency: The number of consecutive connection events during which
                        the device doesn't have to be listening.
        @param cont_num: Continuation number.
        @param timeout: Supervision timeout for this connection in milliseconds.
        @param status: Bluetooth GATT status.
        """
        pass


class FlossGattServer(GattServerCallbacks):
    """Handles method calls and callbacks from the GATT server interface."""

    ADAPTER_SERVICE = 'org.chromium.bluetooth'
    GATT_SERVER_INTERFACE = 'org.chromium.bluetooth.BluetoothGatt'
    GATT_OBJECT_PATTERN = '/org/chromium/bluetooth/hci{}/gatt'
    GATT_CB_OBJ_NAME = 'test_gatt_server'
    CB_EXPORTED_INTF = 'org.chromium.bluetooth.BluetoothGattServerCallback'

    class ExportedGattServerCallbacks(ObserverBase):
        """
        <node>
            <interface name="org.chromium.bluetooth.BluetoothGattServerCallback">
                <method name="OnServerRegistered">
                    <arg type="u" name="status" direction="in" />
                    <arg type="i" name="server_id" direction="in" />
                </method>
                <method name="OnServerConnectionState">
                    <arg type="i" name="server_id" direction="in" />
                    <arg type="b" name="connected" direction="in" />
                    <arg type="s" name="addr" direction="in" />
                </method>
                <method name="OnServiceAdded">
                    <arg type="u" name="status" direction="in" />
                    <arg type="a{sv}" name="service" direction="in" />
                </method>
                <method name="OnServiceRemoved">
                    <arg type="u" name="status" direction="in" />
                    <arg type="i" name="handle" direction="in" />
                </method>
                <method name="OnCharacteristicReadRequest">
                    <arg type="s" name="addr" direction="in" />
                    <arg type="i" name="trans_id" direction="in" />
                    <arg type="i" name="offset" direction="in" />
                    <arg type="b" name="is_long" direction="in" />
                    <arg type="i" name="handle" direction="in" />
                </method>
                <method name="OnDescriptorReadRequest">
                    <arg type="s" name="addr" direction="in" />
                    <arg type="i" name="trans_id" direction="in" />
                    <arg type="i" name="offset" direction="in" />
                    <arg type="b" name="is_long" direction="in" />
                    <arg type="i" name="handle" direction="in" />
                </method>
                <method name="OnCharacteristicWriteRequest">
                    <arg type="s" name="addr" direction="in" />
                    <arg type="i" name="trans_id" direction="in" />
                    <arg type="i" name="offset" direction="in" />
                    <arg type="i" name="len" direction="in" />
                    <arg type="b" name="is_prep" direction="in" />
                    <arg type="b" name="need_rsp" direction="in" />
                    <arg type="i" name="handle" direction="in" />
                    <arg type="ay" name="value" direction="in" />
                </method>
                <method name="OnDescriptorWriteRequest">
                    <arg type="s" name="addr" direction="in" />
                    <arg type="i" name="trans_id" direction="in" />
                    <arg type="i" name="offset" direction="in" />
                    <arg type="i" name="len" direction="in" />
                    <arg type="b" name="is_prep" direction="in" />
                    <arg type="b" name="need_rsp" direction="in" />
                    <arg type="i" name="handle" direction="in" />
                    <arg type="ay" name="value" direction="in" />
                </method>
                <method name="OnExecuteWrite">
                    <arg type="s" name="addr" direction="in" />
                    <arg type="i" name="trans_id" direction="in" />
                    <arg type="b" name="exec_write" direction="in" />
                </method>
                <method name="OnNotificationSent">
                    <arg type="s" name="addr" direction="in" />
                    <arg type="u" name="status" direction="in" />
                </method>
                <method name="OnMtuChanged">
                    <arg type="s" name="addr" direction="in" />
                    <arg type="i" name="mtu" direction="in" />
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
                <method name="OnConnectionUpdated">
                    <arg type="s" name="addr" direction="in" />
                    <arg type="i" name="interval" direction="in" />
                    <arg type="i" name="latency" direction="in" />
                    <arg type="i" name="timeout" direction="in" />
                    <arg type="u" name="status" direction="in" />
                </method>
                <method name="OnSubrateChange">
                    <arg type="s" name="addr" direction="in" />
                    <arg type="i" name="subrate_factor" direction="in" />
                    <arg type="i" name="latency" direction="in" />
                    <arg type="i" name="cont_num" direction="in" />
                    <arg type="i" name="timeout" direction="in" />
                    <arg type="u" name="status" direction="in" />
                </method>
            </interface>
        </node>
        """

        def __init__(self):
            """Constructs exported callbacks object."""
            ObserverBase.__init__(self)

        def OnServerRegistered(self, status, server_id):
            """Handles server registration callback.

            @param status: Bluetooth GATT status.
            @param server_id: Bluetooth GATT server id.
            """
            for observer in self.observers.values():
                observer.on_server_registered(status, server_id)

        def OnServerConnectionState(self, server_id, connected, addr):
            """Handles server connection state callback.

            @param server_id: Bluetooth GATT server id.
            @param connected: A boolean value that indicates whether the GATT
                              server is connected.
            @param addr: Remote device MAC address.
            """
            for observer in self.observers.values():
                observer.on_server_connection_state(server_id, connected, addr)

        def OnServiceAdded(self, status, service):
            """Handles service added callback.

            @param status: Bluetooth GATT status.
            @param service: BluetoothGattService.
            """
            for observer in self.observers.values():
                observer.on_service_added(status, service)

        def OnServiceRemoved(self, status, handle):
            """Handles service removed callback.

            @param status: Bluetooth GATT status.
            @param handle: Service record handle.
            """
            for observer in self.observers.values():
                observer.on_service_removed(status, handle)

        def OnCharacteristicReadRequest(self, addr, trans_id, offset, is_long,
                                        handle):
            """Handles characteristic read request callback.

            @param addr: Remote device MAC address.
            @param trans_id: Transaction id.
            @param offset: Represents the offset from which the attribute value
                           should be read.
            @param is_long: A boolean value representing whether the attribute
                            size is longer than what we can put in the ATT PDU.
            @param handle: The characteristic handle.
            """
            for observer in self.observers.values():
                observer.on_characteristic_read_request(
                        addr, trans_id, offset, is_long, handle)

        def OnDescriptorReadRequest(self, addr, trans_id, offset, is_long,
                                    handle):
            """Handles descriptor read request callback.

            @param addr: Remote device MAC address.
            @param trans_id: Transaction id.
            @param offset: Represents the offset from which the descriptor value
                           should be read.
            @param is_long: A boolean value representing whether the descriptor
                            size is longer than what we can put in the ATT PDU.
            @param handle: The descriptor handle.
            """
            for observer in self.observers.values():
                observer.on_descriptor_read_request(addr, trans_id, offset,
                                                    is_long, handle)

        def OnCharacteristicWrite(self, addr, trans_id, offset, len, is_prep,
                                  need_rsp, handle, value):
            """Handles characteristic write request callback.

            @param addr: Remote device MAC address.
            @param trans_id: Transaction id.
            @param offset: Represents the offset at which the attribute value
                           should be written.
            @param len: The length of the attribute value that should be
                        written.
            @param is_prep: A boolean value representing whether it's a "prepare
                            write" command.
            @param need_rsp: A boolean value representing whether it's a "write
                             no response" command.
            @param handle: The characteristic handle.
            @param value: The value that should be written to the attribute.
            """
            for observer in self.observers.values():
                observer.on_characteristic_write_request(
                        addr, trans_id, offset, len, is_prep, need_rsp, handle,
                        value)

        def OnDescriptorWriteRequest(self, addr, trans_id, offset, len,
                                     is_prep, need_rsp, handle, value):
            """Handles descriptor write request callback.

            @param addr: Remote device MAC address.
            @param trans_id: Transaction id.
            @param offset: The offset value at which the value should be
                           written.
            @param len: The length of the value that should be written.
            @param is_prep: A boolean value representing whether it's a "prepare
                            write" command.
            @param need_rsp: A boolean value representing whether it's a "write
                             no response" command.
            @param handle: The descriptor handle.
            @param value: The value that should be written to the descriptor.
            """
            for observer in self.observers.values():
                observer.on_descriptor_write_request(addr, trans_id, offset,
                                                     len, is_prep, need_rsp,
                                                     handle, value)

        def OnExecuteWrite(self, addr, trans_id, exec_write):
            """Handles execute write callback.

            @param addr: Remote device MAC address.
            @param trans_id: Transaction id.
            @param exec_write: A boolean value that indicates whether the write
                               operation should be executed or canceled.
            """
            for observer in self.observers.values():
                observer.on_execute_write(addr, trans_id, exec_write)

        def OnNotificationSent(self, addr, status):
            """Handles notification sent callback.

            @param addr: Remote device MAC address.
            @param status: Bluetooth GATT status.
            """
            for observer in self.observers.values():
                observer.on_notification_sent(addr, status)

        def OnMtuChanged(self, addr, mtu):
            """Handles MTU changed callback.

            @param addr: Remote device MAC address.
            @param mtu: Maximum transmission unit.
            """
            for observer in self.observers.values():
                observer.on_mtu_changed(addr, mtu)

        def OnPhyUpdate(self, addr, tx_phy, rx_phy, status):
            """Handles physical update callback.

            @param addr: Remote device MAC address.
            @param tx_phy: The new TX PHY for the connection.
            @param rx_phy: The new RX PHY for the connection.
            @param status: Bluetooth GATT status.
            """
            for observer in self.observers.values():
                observer.on_phy_update(addr, tx_phy, rx_phy, status)

        def OnPhyRead(self, addr, tx_phy, rx_phy, status):
            """Handles physical read callback.

            @param addr: Remote device MAC address.
            @param tx_phy: The current transmit PHY for the connection.
            @param rx_phy: The current receive PHY for the connection.
            @param status: Bluetooth GATT status.
            """
            for observer in self.observers.values():
                observer.on_phy_read(addr, tx_phy, rx_phy, status)

        def OnConnectionUpdated(self, addr, interval, latency, timeout,
                                status):
            """Handles connection updated callback.

            @param addr: Remote device MAC address.
            @param interval: Connection interval value.
            @param latency: The number of consecutive connection events during
                            which the device doesn't have to be listening.
            @param timeout: Supervision timeout for this connection in
                            milliseconds.
            @param status: Bluetooth GATT status.
            """
            for observer in self.observers.values():
                observer.on_connection_updated(addr, interval, latency,
                                               timeout, status)

        def on_subrate_change(self, addr, subrate_factor, latency, cont_num,
                              timeout, status):
            """Handles subrate changed callback.

            @param addr: Remote device MAC address.
            @param subrate_factor: Subrate factor value.
            @param latency: The number of consecutive connection events during
                            which the device doesn't have to be listening.
            @param cont_num: Continuation number.
            @param timeout: Supervision timeout for this connection in
                            milliseconds.
            @param status: Bluetooth GATT status.
            """
            for observer in self.observers.values():
                observer.on_subrate_change(addr, subrate_factor, latency,
                                           cont_num, timeout, status)

    def __init__(self, bus, hci):
        """Constructs the client.

        @param bus: D-Bus bus over which we'll establish connections.
        @param hci: HCI adapter index. Get this value from 'get_default_adapter'
                    on FlossManagerClient.
        """
        self.bus = bus
        self.hci = hci
        self.objpath = self.GATT_OBJECT_PATTERN.format(hci)
        self.cb_dbus_objpath = generate_dbus_cb_objpath(
                self.GATT_CB_OBJ_NAME, self.hci)

        # Create and publish callbacks
        self.callbacks = self.ExportedGattServerCallbacks()
        self.callbacks.add_observer('gatt_testing_server', self)
        self.bus.register_object(self.cb_dbus_objpath, self.callbacks, None)

    def __del__(self):
        """Destructor"""
        del self.callbacks

    @glib_callback()
    def on_server_registered(self, status, server_id):
        """Handles server registration callback.

        @param status: Bluetooth GATT status.
        @param server_id: Bluetooth GATT server id.
        """
        logging.debug('on_server_registered: status: %s, server_id: %s',
                      status, server_id)

        if status != GattStatus.SUCCESS:
            logging.error('Failed to register server with id: %s, status = %s',
                          server_id, status)
            return

    @glib_callback()
    def on_server_connection_state(self, server_id, connected, addr):
        """Handles GATT server connection state callback.

        @param server_id: Bluetooth GATT server id.
        @param connected: A boolean value that indicates whether the GATT server
                          is connected.
        @param addr: Remote device MAC address.
        """
        logging.debug(
                'on_server_connection_state: server_id: %s, '
                'connection_state: %s, device address: %s', server_id,
                connected, addr)

    @glib_callback()
    def on_service_added(self, status, service):
        """Handles service added callback.

        @param status: Bluetooth GATT status.
        @param service: BluetoothGattService.
        """
        logging.debug('on_service_added: status: %s, service: %s', status,
                      service)

    @glib_callback()
    def on_service_removed(self, status, handle):
        """Handles service removed callback.

        @param status: Bluetooth GATT status.
        @param handle: Service record handle.
        """
        logging.debug('on_service_removed: status: %s, handle: %s', status,
                      handle)

    @glib_callback()
    def on_characteristic_read_request(self, addr, trans_id, offset, is_long,
                                       handle):
        """Handles the read request of the characteristic callback.

        @param addr: Remote device MAC address.
        @param trans_id: Transaction id.
        @param offset: Represents the offset from which the attribute value
                       should be read.
        @param is_long: A boolean value representing whether the characteristic
                        size is longer than what we can put in the ATT PDU.
        @param handle: The characteristic handle.
        """
        logging.debug(
                'on_characteristic_read_request: device address: %s, '
                'trans_id: %s, offset: %s, is_long: %s, handle: %s', addr,
                trans_id, offset, is_long, handle)

    @glib_callback()
    def on_descriptor_read_request(self, addr, trans_id, offset, is_long,
                                   handle):
        """Handles the read request of the descriptor callback.

        @param addr: Remote device MAC address.
        @param trans_id: Transaction id.
        @param offset: Represents the offset from which the descriptor value
                       should be read.
        @param is_long: A boolean value representing whether the descriptor size
                        is longer than what we can put in the ATT PDU.
        @param handle: The descriptor handle.
        """
        logging.debug(
                'on_descriptor_read_request: device address: %s, trans_id: %s, '
                'offset: %s, is_long: %s, handle: %s', addr, trans_id, offset,
                is_long, handle)

    @glib_callback()
    def on_characteristic_write_request(self, addr, trans_id, offset, len,
                                        is_prep, need_rsp, handle, value):
        """Handles the write request of the characteristic callback.

        @param addr: Remote device MAC address.
        @param trans_id: Transaction id.
        @param offset: Represents the offset at which the attribute value should
                       be written.
        @param len: The length of the attribute value that should be written.
        @param is_prep: A boolean value representing whether it's a "prepare
                        write" command.
        @param need_rsp: A boolean value representing whether it's a "write no
                         response" command.
        @param handle: The characteristic handle.
        @param value: The value that should be written to the attribute.
        """
        logging.debug(
                'on_characteristic_write_request: device address: %s, '
                'trans_id: %s, offset: %s, length: %s, is_prep: %s, '
                'need_rsp: %s, handle: %s, values: %s', addr, trans_id, offset,
                len, is_prep, need_rsp, handle, value)

    @glib_callback()
    def on_descriptor_write_request(self, addr, trans_id, offset, len, is_prep,
                                    need_rsp, handle, value):
        """Handles the write request of the descriptor callback.

        @param addr: Remote device MAC address.
        @param trans_id: Transaction id.
        @param offset: The offset value at which the value should be written.
        @param len: The length of the value that should be written.
        @param is_prep: A boolean value representing whether it's a "prepare
                        write" command.
        @param need_rsp: A boolean value representing whether it's a "write no
                         response" command.
        @param handle: The descriptor handle.
        @param value: The value that should be written to the descriptor.
        """
        logging.debug(
                'on_descriptor_write_request: device address: %s, '
                'trans_id: %s, offset: %s, length: %s, is_prep: %s, '
                'need_rsp: %s, handle: %s, values: %s', addr, trans_id, offset,
                len, is_prep, need_rsp, handle, value)

    @glib_callback()
    def on_execute_write(self, addr, trans_id, exec_write):
        """Handles execute write callback.

        @param addr: Remote device MAC address.
        @param trans_id: Transaction id.
        @param exec_write: A boolean value that indicates whether the write
                           operation should be executed or canceled.
        """
        logging.debug(
                'on_execute_write: device address: %s, '
                'trans_id: %s, exec_write: %s', addr, trans_id, exec_write)

    @glib_callback()
    def on_notification_sent(self, addr, status):
        """Handles notification sent callback.

        @param addr: Remote device MAC address.
        @param status: Bluetooth GATT status.
        """
        logging.debug('on_notification_sent: device address: %s, status: %s',
                      addr, status)

    @glib_callback()
    def on_mtu_changed(self, addr, mtu):
        """Handles MTU changed callback.

        @param addr: Remote device MAC address.
        @param mtu: Maximum transmission unit.
        """
        logging.debug('on_mtu_changed: device address: %s, mtu : %s', addr,
                      mtu)

    @glib_callback()
    def on_phy_update(self, addr, tx_phy, rx_phy, status):
        """Handles physical update callback.

        @param addr: Remote device MAC address.
        @param tx_phy: The new TX PHY for the connection.
        @param rx_phy: The new RX PHY for the connection.
        @param status: Bluetooth GATT status.
        """
        logging.debug(
                'on_phy_update: device address: %s, tx_phy: %s, '
                'rx_phy: %s, status: %s', addr, tx_phy, rx_phy, status)

    @glib_callback()
    def on_phy_read(self, addr, tx_phy, rx_phy, status):
        """Handles physical read callback.

        @param addr: Remote device MAC address.
        @param tx_phy: The current transmit PHY for the connection.
        @param rx_phy: The current receive PHY for the connection.
        @param status: Bluetooth GATT status.
        """
        logging.debug(
                'on_phy_read: device address: %s, tx_phy: %s, '
                'rx_phy: %s, status: %s', addr, tx_phy, rx_phy, status)

    @glib_callback()
    def on_connection_updated(self, addr, interval, latency, timeout, status):
        """Handles connection updated callback.

        @param addr: Remote device MAC address.
        @param interval: Connection interval value.
        @param latency: The number of consecutive connection events during which
                        the device doesn't have to be listening.
        @param timeout: Supervision timeout for this connection in milliseconds.
        @param status: Bluetooth GATT status.
        """
        logging.debug(
                'on_connection_updated: device address: %s, '
                'interval: %s, latency: %s, timeout: %s, status: %s', addr,
                interval, latency, timeout, status)

    @glib_callback()
    def on_subrate_change(self, addr, subrate_factor, latency, cont_num,
                          timeout, status):
        """Handles subrate changed callback.

        @param addr: Remote device MAC address.
        @param subrate_factor: Subrate factor value.
        @param latency: The number of consecutive connection events during which
                        the device doesn't have to be listening.
        @param cont_num: Continuation number.
        @param timeout: Supervision timeout for this connection in milliseconds.
        @param status: Bluetooth GATT status.
        """
        logging.debug(
                'on_subrate_change: device address: %s, subrate_factor: %s, '
                'latency: %s, cont_num: %s, timeout: %s, status: %s', addr,
                subrate_factor, latency, cont_num, timeout, status)

    @glib_call(False)
    def has_proxy(self):
        """Checks whether GATT server proxy can be acquired."""
        return bool(self.proxy())

    def proxy(self):
        """Gets proxy object to GATT server interface for method calls."""
        return self.bus.get(self.ADAPTER_SERVICE,
                            self.objpath)[self.GATT_SERVER_INTERFACE]

    @glib_call(False)
    def register_server(self, app_uuid, eatt_support):
        """Registers GATT server with provided UUID.

        @param app_uuid: GATT application uuid.
        @param eatt_support: A boolean value that indicates whether EATT is
                             supported.

        @return: True on success, False otherwise.
        """
        self.proxy().RegisterServer(app_uuid, self.cb_dbus_objpath,
                                    eatt_support)
        return True

    @glib_call(False)
    def unregister_server(self, server_id):
        """Unregisters GATT server for this client.

        @param server_id: Bluetooth GATT server id.

        @return: True on success, False otherwise.
        """
        self.proxy().UnregisterServer(server_id)
        return True

    @glib_call(None)
    def server_connect(self, server_id, addr, is_direct, transport):
        """Connects remote device to GATT server.

        @param server_id: Bluetooth GATT server id.
        @param addr: Remote device MAC address.
        @param is_direct: A boolean value that specifies whether the connection
                          should be made using direct connection.
        @param transport: BtTransport type.

        @return: Server connect as boolean on success, None otherwise.
        """
        return self.proxy().ServerConnect(server_id, addr, is_direct,
                                          transport)

    @glib_call(None)
    def server_disconnect(self, server_id, addr):
        """Disconnects remote device from the GATT server.

        @param server_id: Bluetooth GATT server id.
        @param addr: Remote device MAC address.

        @return: Server disconnect as boolean on success, None otherwise.
        """
        return self.proxy().ServerDisconnect(server_id, addr)

    @glib_call(False)
    def add_service(self, server_id, service):
        """Adds GATT service.

        @param server_id: Bluetooth GATT server id.
        @param service: BluetoothGattService.

        @return: True on success, False otherwise.
        """
        self.proxy().AddService(server_id, service)
        return True

    @glib_call(False)
    def remove_service(self, server_id, handle):
        """Removes GATT service.

        @param server_id: Bluetooth GATT server id.
        @param handle: Service record handle.

        @return: True on success, False otherwise.
        """
        self.proxy().RemoveService(server_id, handle)
        return True

    @glib_call(False)
    def clear_services(self, server_id):
        """Clears GATT services.

        @param server_id: Bluetooth GATT server id.

        @return: True on success, False otherwise.
        """
        self.proxy().ClearServices(server_id)
        return True

    @glib_call(None)
    def send_response(self, server_id, addr, request_id, status, offset,
                      value):
        """Sends GATT response.

        @param server_id: Bluetooth GATT server id.
        @param addr: Remote device MAC address.
        @param request_id: Request id.
        @param status: Bluetooth GATT status.
        @param offset: The offset value to be sent in the response.
        @param value: The attribute value to be sent in the response.

        @return: Response send as boolean on success, None otherwise.
        """
        return self.proxy().SendResponse(server_id, addr, request_id, status,
                                         offset, value)

    @glib_call(None)
    def send_notification(self, server_id, addr, handle, confirm, value):
        """Sends GATT notification.

        @param server_id: Bluetooth GATT server id.
        @param addr: Remote device MAC address.
        @param handle: The attribute handle of the attribute to send the
                       notification for.
        @param confirm: A boolean value indicating whether the client should
                        send a confirmation in response to the notification.
        @param value: The notification data to send.

        @return: Notification send as boolean on success, None otherwise.
        """
        return self.proxy().SendNotification(server_id, addr, handle, confirm,
                                             value)

    @glib_call(False)
    def server_set_preferred_phy(self, server_id, addr, tx_phy, rx_phy,
                                 phy_options):
        """Sets preferred phy for server.

        @param server_id: Bluetooth GATT server id.
        @param addr: Remote device MAC address.
        @param tx_phy: Preferred PHY for transmitting data.
        @param rx_phy: Preferred PHY for receiving data.
        @param phy_options: Preferred Phy options.

        @return: True on success, False otherwise.
        """
        self.proxy().ServerSetPreferredPhy(server_id, addr, tx_phy, rx_phy,
                                           phy_options)
        return True

    @glib_call(False)
    def server_read_phy(self, server_id, addr):
        """Reads phy of server.

        @param server_id: Bluetooth GATT server id.
        @param addr: Remote device MAC address.

        @return: True on success, False otherwise.
        """
        self.proxy().ServerReadPhy(server_id, addr)
        return True
