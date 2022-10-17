# Lint as:python3
# Copyright 2022 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Client class to access the Floss scanner interface."""

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


class SuspendMode(IntEnum):
    """Bluetooth suspend mode."""
    NORMAL = 0
    SUSPENDING = 1
    SUSPENDED = 2
    RESUMING = 3


class ScanType(IntEnum):
    """Bluetooth scan type."""
    ACTIVE = 0
    PASSIVE = 1


class BluetoothScannerCallbacks:
    """Callbacks for the scanner interface.

    Implement this to observe these callbacks when exporting callbacks via
    register_callback.
    """

    def on_scanner_registered(self, uuid, scanner_id, status):
        """Called when scanner registered.

        @param uuid: The specific uuid to register it.
        @param scanner_id: Scanner id of scanning set.
        @param status: GattStatus.
        """
        pass

    def on_scan_result(self, scan_result):
        """Called when execute start_scan().

        @param scan_result: The struct of ScanResult.
        """
        pass

    def on_suspend_mode_change(self, suspend_mode):
        """Called when suspend mode change.

        @param suspend_mode: The suspend mode of Bluetooth.
        """
        pass


class FlossScannerClient(BluetoothScannerCallbacks):
    """Handles method calls to and callbacks from the scanner interface."""

    SCANNER_SERVICE = 'org.chromium.bluetooth'
    SCANNER_INTERFACE = 'org.chromium.bluetooth.BluetoothGatt'
    SCANNER_OBJECT_PATTERN = '/org/chromium/bluetooth/hci{}/gatt'

    SCANNER_CB_INTF = 'org.chromium.bluetooth.ScannerCallback'
    SCANNER_CB_OBJ_PATTERN = (
        '/org/chromium/bluetooth/hci{}/test_scanner_client{}')

    class ExportedScannerCallbacks(ObserverBase):
        """
        <node>
            <interface name="org.chromium.bluetooth.ScannerCallback">
                <method name="OnScannerRegistered">
                    <arg type="ay" name="uuid" direction="in" />
                    <arg type="y" name="scanner_id" direction="in" />
                    <arg type="u" name="status" direction="in" />
                </method>
                <method name="OnScanResult">
                    <arg type="a{sv}" name="scan_result" direction="in" />
                </method>
                <method name="OnSuspendModeChange">
                    <arg type="u" name="suspend_mode" direction="in" />
                </method>
            </interface>
        </node>
        """

        def __init__(self):
            """Constructs exported callbacks object."""
            ObserverBase.__init__(self)

        def OnScannerRegistered(self, uuid, scanner_id, status):
            """Handles scanner registered callback.

            @param uuid: The specific uuid to register it.
            @param scanner_id: Scanner id of scanning set.
            @param status: GattStatus.
            """
            for observer in self.observers.values():
                observer.on_scanner_registered(uuid, scanner_id, status)

        def OnScanResult(self, scan_result):
            """Handles scan result callback.

            @param scan_result: The struct of ScanResult.
            """
            for observer in self.observers.values():
                observer.on_scan_result(scan_result)

        def OnSuspendModeChange(self, suspend_mode):
            """Handles suspend mode change callback.

            @param suspend_mode: The suspend mode of Bluetooth.
            """
            for observer in self.observers.values():
                observer.on_suspend_mode_change(suspend_mode)

    def __init__(self, bus, hci):
        """Constructs the client.

        @param bus: D-Bus bus over which we'll establish connections.
        @param hci: HCI adapter index. Get this value from `get_default_adapter`
                    on FlossManagerClient.
        """
        self.bus = bus
        self.hci = hci
        self.objpath = self.SCANNER_OBJECT_PATTERN.format(hci)

        # We don't register callbacks by default.
        self.callbacks = None
        self.callback_id = None

    def __del__(self):
        """Destructor"""
        del self.callbacks

    @glib_callback()
    def on_scanner_registered(self, uuid, scanner_id, status):
        """Handles scanner registered callback.

        @param uuid: The specific uuid to register it.
        @param scanner_id: Scanner id of scanning set.
        @param status: GattStatus.
        """
        logging.debug(
                'on_scanner_registered: uuid: %s, scanner_id: %s, '
                'status: %s', uuid, scanner_id, status)

    @glib_callback()
    def on_scan_result(self, scan_result):
        """Handles scan result callback.

        @param scan_result: The struct of ScanResult.
        """
        logging.debug('on_scan_result: scan_result: %s', scan_result)

    @glib_callback()
    def on_suspend_mode_change(self, suspend_mode):
        """Handles suspend mode change callback.

        @param suspend_mode: The suspend mode of Bluetooth.
        """
        logging.debug('on_suspend_mode_change: suspend_mode: %s', suspend_mode)

    def make_dbus_scan_filter_pattern(self, start_position, ad_type, content):
        """Makes struct for scan filter pattern D-Bus.

        @param start_position: The start position of pattern.
        @param ad_type: The type of pattern.
        @param content: The content of pattern.

        @return: Dictionary of scan filter pattern."""
        return {
                'start_position': GLib.Variant('q', start_position),
                'ad_type': GLib.Variant('q', ad_type),
                'content': GLib.Variant('aq', content)
        }

    def make_dbus_scan_filter_condition(self, patterns):
        """Makes struct for scan filter condition D-Bus.

        @param patterns: The list of patterns used for conditions.

        @return: Dictionary of scan filter condition."""
        return {
            'patterns': GLib.Variant('aa{sv}', patterns)
        }

    def make_dbus_scan_filter(self, rssi_high_threshold, rssi_low_threshold,
                              rssi_low_timeout, rssi_sampling_period,
                              condition):
        """Makes struct for scan filter D-Bus.

        @param rssi_high_threshold: RSSI high threshold value.
        @param rssi_low_threshold: RSSI low threshold value.
        @param rssi_low_timeout: RSSI low timeout value.
        @param rssi_sampling_period: The sampling interval in milliseconds.
        @param condition: Struct of ScanFilterCondition.

        @return: Dictionary of scan filter.
         """
        patterns = []
        for c in condition:
            patterns.append(
                    self.make_dbus_scan_filter_pattern(c['start_position'],
                                                       c['ad_type'],
                                                       c['content']))
        return {
                'rssi_high_threshold':
                GLib.Variant('n', rssi_high_threshold),
                'rssi_low_threshold':
                GLib.Variant('n', rssi_low_threshold),
                'rssi_low_timeout':
                GLib.Variant('q', rssi_low_timeout),
                'rssi_sampling_period':
                GLib.Variant('q', rssi_sampling_period),
                'condition':
                GLib.Variant('a{sv}',
                             self.make_dbus_scan_filter_condition(patterns))
        }

    def make_dbus_scan_settings(self, interval, window, scan_type):
        """Makes struct for scan settings D-Bus.

        @param interval: The interval value to setting scan.
        @param window: The window value to setting scan.
        @param scan_type: The type of scan.

        @return: Dictionary of scan settings.
        """
        return {
                'interval': GLib.Variant('i', interval),
                'window': GLib.Variant('i', window),
                'scan_type': GLib.Variant('u', scan_type)
        }

    @glib_call(False)
    def has_proxy(self):
        """Checks whether scanner proxy can be acquired."""
        return bool(self.proxy())

    def proxy(self):
        """Gets proxy object to scanner interface for method calls."""
        return self.bus.get(self.SCANNER_SERVICE,
                            self.objpath)[self.SCANNER_INTERFACE]

    @glib_call(False)
    def register_scanner_callback(self):
        """Registers scanner callbacks if it doesn't exist."""

        if self.callbacks:
            return True

        # Generate a random number between 1-1000
        rnumber = math.floor(random.random() * 1000 + 1)

        # Create and publish callbacks
        self.callbacks = self.ExportedScannerCallbacks()

        self.callbacks.add_observer('scanner_client', self)
        objpath = self.SCANNER_CB_OBJ_PATTERN.format(self.hci, rnumber)
        self.bus.register_object(objpath, self.callbacks, None)

        # Register published callbacks with scanner daemon
        self.callback_id = self.proxy().RegisterScannerCallback(objpath)
        return True

    @glib_call(False)
    def unregister_scanner_callback(self):
        """Unregisters scanner callback for this client.

        @return: True on success, False otherwise.
        """
        return self.proxy().UnregisterScannerCallback(self.callback_id)

    @glib_call(None)
    def register_scanner(self):
        """Registers scanner for the callback id.

        @return: UUID of the registered scanner on success, None otherwise.
        """
        return self.proxy().RegisterScanner(self.callback_id)

    @glib_call(False)
    def unregister_scanner(self, scanner_id):
        """Unregisters scanner set using scanner id of set.

        @param scanner_id: Scanner id of set scanning.

        @return: True on success, False otherwise.
        """
        return self.proxy().UnregisterScanner(scanner_id)

    @glib_call(None)
    def start_scan(self, scanner_id, settings, filter):
        """Starts scan.

        @param scanner_id: Scanner id of set scanning.
        @param settings: ScanSettings structure.
        @param filter: ScanFilter structure.

        @return: BtStatus as int on success, None otherwise.
        """
        return self.proxy().StartScan(scanner_id, settings, filter)

    @glib_call(None)
    def stop_scan(self, scanner_id):
        """Stops scan set using scanner_id.

        @param scanner_id: Scanner id of set scanning.

        @return: BtStatus as int on success, None otherwise.
        """
        return self.proxy().StopScan(scanner_id)

    @glib_call(None)
    def get_scan_suspend_mode(self):
        """Gets scan suspend mode.

        @return: SuspendMode as int on success, None otherwise.
        """
        return self.proxy().GetScanSuspendMode()

    @glib_call(None)
    def is_msft_supported(self):
        """Checks if MSFT supported.

        @return: MSFT capability as boolean on success, None otherwise.
        """
        return self.proxy().IsMsftSupported()
