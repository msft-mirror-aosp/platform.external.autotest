# Lint as:python3
# Copyright 2022 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Client class to access the Floss adapter interface."""

from enum import IntEnum
from gi.repository import GLib
import logging
import math
import random

from autotest_lib.client.cros.bluetooth.floss.observer_base import ObserverBase
from autotest_lib.client.cros.bluetooth.floss.utils import (glib_call,
                                                            glib_callback)


class GattStatus(IntEnum):
    """Bluetooth Gatt return status."""
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


class BluetoothAdvertisingCallbacks:
    """Callbacks for the advertising interface.

    Implement this to observe these callbacks when exporting callbacks via
    register_callback.
    """

    def on_advertising_set_started(self, reg_id, advertiser_id, tx_power,
                                   status):
        """Called when advertising set started.

        @param reg_id: Reg_id of advertising set.
        @param advertiser_id: Advertiser id of advertising set.
        @param tx_power: Tx-power value get from advertising set registered.
        @param status: GattStatus.
        """
        pass

    def on_own_address_read(self, advertiser_id, address_type, address):
        """Called when own address read.

        @param advertiser_id: Advertiser id of advertising set.
        @param address_type: Public or private address.
        @param address: Own address.
        """
        pass

    def on_advertising_set_stopped(self, advertiser_id):
        """Called when advertising set stopped.

        @param advertiser_id: Advertiser id of advertising set.
        """
        pass

    def on_advertising_enabled(self, advertiser_id, enable, status):
        """Called when advertising enabled.

        @param advertiser_id: Advertiser id of advertising set.
        @param enable: Enable advertising set flag.
        @param status: GattStatus.
        """
        pass

    def on_advertising_data_set(self, advertiser_id, status):
        """Called when advertising data set.

        @param advertiser_id: Advertiser id of advertising set.
        @param status: GattStatus.
        """
        pass

    def on_scan_response_data_set(self, advertiser_id, status):
        """Called when scan response data set.

        @param advertiser_id: Advertiser id of advertising set.
        @param status: GattStatus.
        """
        pass

    def on_advertising_parameters_updated(self, advertiser_id, tx_power,
                                          status):
        """Called when advertising parameters updated.

        @param advertiser_id: Advertiser id of advertising set.
        @param tx_power: Tx-power value get from advertising set registered.
        @param status: GattStatus.
        """
        pass

    def on_periodic_advertising_parameters_updated(self, advertiser_id,
                                                   status):
        """Called when periodic advertising parameters updated.

        @param advertiser_id: Advertiser id of advertising set.
        @param status: GattStatus.
        """
        pass

    def on_periodic_advertising_data_set(self, advertiser_id, status):
        """Called when periodic advertising data set.

        @param advertiser_id: Advertiser id of advertising set.
        @param status: GattStatus.
        """
        pass

    def on_periodic_advertising_enabled(self, advertiser_id, enable, status):
        """Called when periodic advertising parameters enabled.

        @param advertiser_id: Advertiser id of advertising set.
        @param enable: Enable advertising set flag.
        @param status: GattStatus.
        """
        pass


class FlossAdvertisingClient(BluetoothAdvertisingCallbacks):
    """Handles method calls to and callbacks from the advertising interface."""

    ADAPTER_SERVICE = 'org.chromium.bluetooth'
    ADVERTISING_INTERFACE = 'org.chromium.bluetooth.BluetoothGatt'
    ADVERTISING_OBJECT_PATTERN = '/org/chromium/bluetooth/hci{}/gatt'

    ADVERTISING_CB_INTF = 'org.chromium.bluetooth.AdvertisingSetCallback'
    ADVERTISING_CB_OBJ_PATTERN = '/org/chromium/bluetooth/hci{}/test_advertising_client{}'

    class ExportedAdvertisingCallbacks(ObserverBase):
        """
        <node>
            <interface name="org.chromium.bluetooth.AdvertisingSetCallback">
                <method name="OnAdvertisingSetStarted">
                    <arg type="i" name="reg_id" direction="in" />
                    <arg type="i" name="advertiser_id" direction="in" />
                    <arg type="i" name="tx_power" direction="in" />
                    <arg type="u" name="status" direction="in" />
                </method>
                <method name="OnOwnAddressRead">
                    <arg type="i" name="advertiser_id" direction="in" />
                    <arg type="i" name="address_type" direction="in" />
                    <arg type="s" name="address" direction="in" />
                </method>
                <method name="OnAdvertisingSetStopped">
                    <arg type="i" name="advertiser_id" direction="in" />
                </method>
                <method name="OnAdvertisingEnabled">
                    <arg type="i" name="advertiser_id" direction="in" />
                    <arg type="b" name="enable" direction="in" />
                    <arg type="u" name="status" direction="in" />
                </method>
                <method name="OnAdvertisingDataSet">
                    <arg type="i" name="advertiser_id" direction="in" />
                    <arg type="u" name="status" direction="in" />
                </method>
                <method name="OnScanResponseDataSet">
                    <arg type="i" name="advertiser_id" direction="in" />
                    <arg type="u" name="status" direction="in" />
                </method>
                <method name="OnAdvertisingParametersUpdated">
                    <arg type="i" name="advertiser_id" direction="in" />
                    <arg type="i" name="tx_power" direction="in" />
                    <arg type="u" name="status" direction="in" />
                </method>
                <method name="OnPeriodicAdvertisingParametersUpdated">
                    <arg type="i" name="advertiser_id" direction="in" />
                    <arg type="u" name="status" direction="in" />
                </method>
                <method name="OnPeriodicAdvertisingDataSet">
                    <arg type="i" name="advertiser_id" direction="in" />
                    <arg type="u" name="status" direction="in" />
                </method>
                <method name="OnPeriodicAdvertisingEnabled">
                    <arg type="i" name="advertiser_id" direction="in" />
                    <arg type="b" name="enable" direction="in" />
                    <arg type="u" name="status" direction="in" />
                </method>
            </interface>
        </node>
        """

        def __init__(self):
            """Construct exported callbacks object."""
            ObserverBase.__init__(self)

        def OnAdvertisingSetStarted(self, reg_id, advertiser_id, tx_power,
                                    status):
            """Handle advertising set started callback."""
            for observer in self.observers.values():
                observer.on_advertising_set_started(reg_id, advertiser_id,
                                                    tx_power, status)

        def OnOwnAddressRead(self, advertiser_id, address_type, address):
            """Handle own address read callback."""
            for observer in self.observers.values():
                observer.on_own_address_read(advertiser_id, address_type,
                                             address)

        def OnAdvertisingSetStopped(self, advertiser_id):
            """Handle advertising set stopped callback."""
            for observer in self.observers.values():
                observer.on_advertising_set_stopped(advertiser_id)

        def OnAdvertisingEnabled(self, advertiser_id, enable, status):
            """Handle advertising enabled callback."""
            for observer in self.observers.values():
                observer.on_advertising_enabled(advertiser_id, enable, status)

        def OnAdvertisingDataSet(self, advertiser_id, status):
            """Handle advertising data set callback."""
            for observer in self.observers.values():
                observer.on_advertising_data_set(advertiser_id, status)

        def OnScanResponseDataSet(self, advertiser_id, status):
            """Handle scan response data set callback."""
            for observer in self.observers.values():
                observer.on_scan_response_data_set(advertiser_id, status)

        def OnAdvertisingParametersUpdated(self, advertiser_id, tx_power,
                                           status):
            """Handle advertising parameters updated callback."""
            for observer in self.observers.values():
                observer.on_advertising_parameters_updated(
                        advertiser_id, tx_power, status)

        def OnPeriodicAdvertisingParametersUpdated(self, advertiser_id,
                                                   status):
            """Handle periodic advertising parameters updated callback."""
            for observer in self.observers.values():
                observer.on_periodic_advertising_parameters_updated(
                        advertiser_id, status)

        def OnPeriodicAdvertisingDataSet(self, advertiser_id, status):
            """Handle periodic advertising data set callback."""
            for observer in self.observers.values():
                observer.on_periodic_advertising_data_set(
                        advertiser_id, status)

        def OnPeriodicAdvertisingEnabled(self, advertiser_id, enable, status):
            """Handle periodic advertising enabled callback."""
            for observer in self.observers.values():
                observer.on_periodic_advertising_enabled(
                        advertiser_id, enable, status)

    def __init__(self, bus, hci):
        """Construct the client.

        @param bus: DBus bus over which we'll establish connections.
        @param hci: HCI adapter index. Get this value from `get_default_adapter`
                    on FlossAdvertisingClient.
        """
        self.bus = bus
        self.hci = hci
        self.objpath = self.ADVERTISING_OBJECT_PATTERN.format(hci)

        # We don't register callbacks by default.
        self.callbacks = None
        self.callback_id = None

    def __del__(self):
        """Destructor"""
        del self.callbacks

    @glib_callback()
    def on_advertising_set_started(self, reg_id, advertiser_id, tx_power,
                                   status):
        """Handle advertising set started callback."""
        logging.debug(
                'on_advertising_set_started: reg_id: %s, advertiser_id: %s, '
                'tx_power: %s, status: %s', reg_id, advertiser_id, tx_power,
                status)

    @glib_callback()
    def on_own_address_read(self, advertiser_id, address_type, address):
        """Handle own address read callback."""
        logging.debug(
                'on_own_address_read: advertiser_id: %s, address_type: %s, '
                'address: %s', advertiser_id, address_type, address)

    @glib_callback()
    def on_advertising_set_stopped(self, advertiser_id):
        """Handle advertising set stopped callback."""
        logging.debug('on_advertising_set_stopped: advertiser_id: %s',
                      advertiser_id)

    @glib_callback()
    def on_advertising_enabled(self, advertiser_id, enable, status):
        """Handle advertising enable callback."""
        logging.debug(
                'on_advertising_enabled: advertiser_id: %s, enable: %s, '
                'status: %s', advertiser_id, enable, status)

    @glib_callback()
    def on_advertising_data_set(self, advertiser_id, status):
        """Handle advertising data set callback."""
        logging.debug('on_advertising_data_set: advertiser_id: %s, status: %s',
                      advertiser_id, status)

    @glib_callback()
    def on_scan_response_data_set(self, advertiser_id, status):
        """Handle scan response data set callback."""
        logging.debug(
                'on_scan_response_data_set: advertiser_id: %s, status: '
                '%s', advertiser_id, status)

    @glib_callback()
    def on_advertising_parameters_updated(self, advertiser_id, tx_power,
                                          status):
        """Handle advertising parameters update callback."""
        logging.debug(
                'on_advertising_parameters_updated: advertiser_id: %s, '
                'tx_power: %s, status: %s', advertiser_id, tx_power, status)

    @glib_callback()
    def on_periodic_advertising_parameters_updated(self, advertiser_id,
                                                   status):
        """Handle periodic advertising parameters updated callback."""
        logging.debug(
                'on_periodic_advertising_parameters_updated: advertiser_id: '
                '%s, status: %s', advertiser_id, status)

    @glib_callback()
    def on_periodic_advertising_data_set(self, advertiser_id, status):
        """Handle periodic advertising data set callback."""
        logging.debug(
                'on_periodic_advertising_data_set: advertiser_id: %s, status: '
                '%s', advertiser_id, status)

    @glib_callback()
    def on_periodic_advertising_enabled(self, advertiser_id, enable, status):
        """Handle on periodic advertising enabled callback."""
        logging.debug(
                'on_periodic_advertising_enabled: advertiser_id: %s, enable: '
                '%s, status: %s', advertiser_id, enable, status)

    def make_dbus_periodic_advertising_parameters(self, include_tx_power,
                                                  interval):
        """Makes struct for periodic advertising parameters D-Bus."""
        return {
                'include_tx_power': GLib.Variant('b', include_tx_power),
                'interval': GLib.Variant('i', interval)
        }

    def make_dbus_advertising_set_parameters(self, connectable, scannable,
                                             is_legacy, is_anonymous,
                                             include_tx_power, primary_phy,
                                             secondary_phy, interval,
                                             tx_power_level, own_address_type):
        """Makes struct for advertising set parameters D-Bus."""
        return {
                'connectable': GLib.Variant('b', connectable),
                'scannable': GLib.Variant('b', scannable),
                'is_legacy': GLib.Variant('b', is_legacy),
                'is_anonymous': GLib.Variant('b', is_anonymous),
                'include_tx_power': GLib.Variant('b', include_tx_power),
                'primary_phy': GLib.Variant('u', primary_phy),
                'secondary_phy': GLib.Variant('u', secondary_phy),
                'interval': GLib.Variant('i', interval),
                'tx_power_level': GLib.Variant('i', tx_power_level),
                'own_address_type': GLib.Variant('i', own_address_type)
        }

    def make_dbus_advertise_data(self, service_uuids, solicit_uuids,
                                 transport_discovery_data, manufacturer_data,
                                 service_data, include_tx_power_level,
                                 include_device_name):
        """Makes struct for advertising data D-Bus."""
        return {
                'service_uuids':
                GLib.Variant('as', service_uuids),
                'solicit_uuids':
                GLib.Variant('as', solicit_uuids),
                'transport_discovery_data':
                GLib.Variant('aay', transport_discovery_data),
                'manufacturer_data':
                GLib.Variant('a{iay}', manufacturer_data),
                'service_data':
                GLib.Variant('a{say}', service_data),
                'include_tx_power_level':
                GLib.Variant('b', include_tx_power_level),
                'include_device_name':
                GLib.Variant('b', include_device_name),
        }

    @glib_call(False)
    def has_proxy(self):
        """Checks whether Gatt proxy can be acquired."""
        return bool(self.proxy())

    def proxy(self):
        """Gets proxy object to Gatt interface for method calls."""
        return self.bus.get(self.ADAPTER_SERVICE,
                            self.objpath)[self.ADVERTISING_INTERFACE]

    @glib_call(False)
    def register_advertiser_callback(self):
        """Registers advertising callbacks for this client if one doesn't
        already exist.
        """

        if self.callbacks:
            return True

        # Generate a random number between 1-1000
        rnumber = math.floor(random.random() * 1000 + 1)

        # Create and publish callbacks
        self.callbacks = self.ExportedAdvertisingCallbacks()

        self.callbacks.add_observer('advertising_client', self)
        objpath = self.ADVERTISING_CB_OBJ_PATTERN.format(self.hci, rnumber)
        self.bus.register_object(objpath, self.callbacks, None)

        # Register published callbacks with manager daemon
        self.callback_id = self.proxy().RegisterAdvertiserCallback(objpath)
        return True

    @glib_call(False)
    def unregister_advertiser_callback(self):
        """Unregisters advertising callbacks for this client.

        @return: True on success, False otherwise.
        """
        self.proxy().UnregisterAdvertiserCallback(self.callback_id)
        return True

    @glib_call(None)
    def start_advertising_set(self, parameters, advertise_data, scan_response,
                              periodic_parameters, periodic_data, duration,
                              max_ext_adv_events, callback_id):
        """Starts advertising set.

        @param parameters: AdvertisingSetParameters structure.
        @param advertise_data: AdvertiseData structure.
        @param scan_response: Scan response data(optional).
        @param periodic_parameters: PeriodicAdvertisingParameters structure
                                    (optional).
        @param periodic_data: AdvertiseData structure(optional).
        @param duration: Time to start advertising set.
        @param max_ext_adv_events: Maximum of extended advertising events.
        @param callback_id: Callback id from register advertiser callback.

        @return: Returns the reg_id for the advertising set on success,
                 None otherwise.
        """
        return self.proxy().StartAdvertisingSet(
                parameters, advertise_data, scan_response, periodic_parameters,
                periodic_data, duration, max_ext_adv_events, callback_id)

    @glib_call(False)
    def stop_advertising_set(self, advertiser_id):
        """Stops advertising set using advertiser id of set.

        @param advertiser_id: Advertiser id of set advertising.

        @return: True on success, False otherwise.
        """
        self.proxy().StopAdvertisingSet(advertiser_id)
        return True

    @glib_call(False)
    def enable_advertising_set(self, advertiser_id, enable, duration,
                               max_ext_adv_events):
        """Enables advertising set using advertiser_id.

        @param advertiser_id: Advertiser id of set advertising.
        @param enable: Enable advertising set flag.
        @param duration: Time to send the advertising set.
        @param max_ext_adv_events: Number of max extend adv events.

        @return: True on success, False otherwise.
        """
        self.proxy().EnableAdvertisingSet(advertiser_id, enable, duration,
                                          max_ext_adv_events)
        return True

    @glib_call(False)
    def set_advertising_data(self, advertiser_id, data):
        """Sets advertising data using advertiser_id.

        @param advertiser_id: Advertiser id of set advertising.
        @param data: AdvertiseData structure.

        @return: True on success, False otherwise.
        """
        self.proxy().SetAdvertisingData(advertiser_id, data)
        return True

    @glib_call(False)
    def set_scan_response_data(self, advertiser_id, data):
        """Sets scan response data using advertiser id.

        @param advertiser_id: Advertiser id of set advertising.
        @param data: AdvertiseData structure.

        @return: True on success, False otherwise.
        """
        self.proxy().SetScanResponseData(advertiser_id, data)
        return True

    @glib_call(False)
    def set_advertising_parameters(self, advertiser_id, parameters):
        """Sets advertising parameters using advertiser_id.

        @param advertiser_id: Advertiser id of set advertising.
        @param parameters: AdvertisingSetParameters structure.

        @return: True on success, False otherwise.
        """
        self.proxy().SetAdvertisingParameters(advertiser_id, parameters)
        return True

    @glib_call(False)
    def set_periodic_advertising_parameters(self, advertiser_id, parameters):
        """Sets periodic advertising parameters using advertiser_id.

        @param advertiser_id: Advertiser id of set advertising.
        @param parameters: AdvertisingSetParameters structure.

        @return: True on success, False otherwise.
        """
        self.proxy().SetPeriodicAdvertisingParameters(advertiser_id, parameters)
        return True

    @glib_call(False)
    def set_periodic_advertising_data(self, advertiser_id, data):
        """Sets periodic advertising data using advertiser_id.

        @param advertiser_id: Advertiser id of set advertising.
        @param data: AdvertiseData structure.

        @return: True on success, False otherwise.
        """
        self.proxy().SetPeriodicAdvertisingData(advertiser_id, data)
        return True

    @glib_call(False)
    def set_periodic_advertising_enable(self, advertiser_id, enable):
        """Sets periodic advertising enable using advertiser_id.

        @param advertiser_id: Advertiser id of set advertising.
        @param enable: Enable advertising set flag.

        @return: True on success, False otherwise.
        """
        self.proxy().SetPeriodicAdvertisingEnable(advertiser_id, enable)
        return True

    @glib_call(False)
    def get_own_address(self, advertiser_id):
        """Gets own address using advertiser_id.

        @param advertiser_id: Advertiser id of set advertising.

        @return: True on success, False otherwise.
        """
        self.proxy().GetOwnAddress(advertiser_id)
        return True
