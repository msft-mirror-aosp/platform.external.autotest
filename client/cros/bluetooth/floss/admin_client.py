# Lint as:python3
# Copyright 2022 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Client class to access the Floss admin interface."""

from gi.repository import GLib
from uuid import UUID
import logging
import math
import random

from autotest_lib.client.cros.bluetooth.floss.observer_base import ObserverBase
from autotest_lib.client.cros.bluetooth.floss.utils import (glib_call,
                                                            glib_callback)


class BluetoothAdminPolicyCallbacks:
    """Callbacks for the Admin Interface.

    Implement this to observe these callbacks when exporting callbacks via
    register_callback.
    """

    def on_service_allowlist_changed(self, allowlist):
        """Called when service allow list changed.

        @param allowlist: List of uuid services.
        """
        pass

    def on_device_policy_effect_changed(self, device, new_policy_effect):
        """Called when device policy effect changed.

        @param device: Remote device that is affected by the policy.
        @param new_policy_effect: The Policy that affects services and devices.
        """
        pass


class FlossAdminClient(BluetoothAdminPolicyCallbacks):
    """Handles method calls to and callbacks from the admin interface."""

    ADMIN_SERVICE = 'org.chromium.bluetooth'
    ADMIN_INTERFACE = 'org.chromium.bluetooth.BluetoothAdmin'
    ADMIN_OBJECT_PATTERN = '/org/chromium/bluetooth/hci{}/admin'
    ADMIN_CB_INTF = 'org.chromium.bluetooth.AdminPolicyCallback'
    ADMIN_CB_OBJ_PATTERN = '/org/chromium/bluetooth/hci{}/test_admin_client{}'

    @staticmethod
    def parse_dbus_device(device_dbus):
        """Parses a D-Bus variant dict as a remote device.

        @param device_dbus: Variant dict with signature a{sv}.

        @return: True and BluetoothDevice tuple on success parsing,
                 otherwise False and None.
        """
        if 'address' in device_dbus and 'name' in device_dbus:
            return True, (str(device_dbus['address']),
                          str(device_dbus['name']))
        return False, None

    @staticmethod
    def parse_dbus_policy_effect(new_policy_effect_dbus):
        """Parses a D-Bus variant dict as a remote policy effect.

        @param new_policy_effect_dbus: Variant dict with signature a{sv}.

        @return: True and PolicyEffect tuple on success parsing,
                 otherwise False and None.
        """
        if ('service_blocked' in new_policy_effect_dbus
                    and 'affected' in new_policy_effect_dbus):
            try:
                uuids = [
                        UUID(u)
                        for u in new_policy_effect_dbus['service_blocked']
                ]
            except ValueError:
                logging.exception("Failed to create UUID with values: %s",
                                  uuids)
                return False, None

            return True, (uuids, bool(new_policy_effect_dbus['affected']))
        return False, None

    class ExportedAdminPolicyCallbacks(ObserverBase):
        """
        <node>
            <interface name="org.chromium.bluetooth.AdminPolicyCallback">
                <method name="OnServiceAllowlistChanged">
                    <arg type="aay" name="allowlist" direction="in" />
                </method>
                <method name="OnDevicePolicyEffectChanged">
                    <arg type="a{sv}" name="device" direction="in" />
                    <arg type="a{sv}" name="new_policy_effect" direction="in" />
                </method>
            </interface>
        </node>
        """

        def __init__(self):
            """Constructs exported callbacks object."""
            ObserverBase.__init__(self)

        def OnServiceAllowlistChanged(self, allowlist):
            """Handles service allow list changed callback.

            @param allowlist: List of uuid services.
            """
            for observer in self.observers.values():
                observer.on_service_allowlist_changed(allowlist)

        def OnDevicePolicyEffectChanged(self, device, new_policy_effect):
            """Handles device policy effect Changed callback.

            @param device: Remote device that is affected by the policy.
            @param new_policy_effect: The Policy that affects services and
                                      devices.
            """
            parsed_device, remote_device = FlossAdminClient.parse_dbus_device(
                    device)
            if not parsed_device:
                logging.debug(
                        'OnDevicePolicyEffectChanged parse error: {}'.format(
                                device))
                return

            parsed_policy, remote_policy_effect = (
                    FlossAdminClient.parse_dbus_policy_effect(
                            new_policy_effect))
            if not parsed_policy:
                logging.debug('OnDevicePolicyEffectChanged: {}'.format(
                        new_policy_effect))
                return

            for observer in self.observers.values():
                observer.on_device_policy_effect_changed(
                        remote_device, remote_policy_effect)

    def __init__(self, bus, hci):
        """Constructs the client.

        @param bus: D-Bus bus over which we'll establish connections.
        @param hci: HCI adapter index. Get this value from `get_default_adapter`
                    on FlossManagerClient.
        """
        self.bus = bus
        self.hci = hci
        self.objpath = self.ADMIN_OBJECT_PATTERN.format(hci)

        # We don't register callbacks by default.
        self.callbacks = None
        self.callback_id = None

        self.known_devices = {}
        self.allowlist = []

    def __del__(self):
        """Destructor"""
        del self.callbacks

    @glib_callback()
    def on_service_allowlist_changed(self, allowlist):
        """Handles service allow list changed callback.

        @param allowlist: List of uuid services.
        """
        logging.debug('on_service_allowlist_changed: allowlist: %s', allowlist)
        self.allowlist = allowlist

    @glib_callback()
    def on_device_policy_effect_changed(self, device, new_policy_effect):
        """Handles device policy effect changed callback.

        @param device: Remote device that is affected by the policy.
        @param new_policy_effect: The Policy that affects services and devices.
        """
        logging.debug(
                'on_device_policy_effect_changed: device: %s, '
                'new_policy_effect: %s, ', device, new_policy_effect)

        address, name = device
        if address not in self.known_devices:
            self.known_devices[address] = {
                    'address': address,
                    'name': name,
                    'new_policy_effect': new_policy_effect
            }
        else:
            self.known_devices[address]['name'] = name
            self.known_devices[address]['new_policy_effect'] = new_policy_effect

    @glib_call(False)
    def has_proxy(self):
        """Checks whether Admin proxy can be acquired."""
        return bool(self.proxy())

    def proxy(self):
        """Gets proxy object to admin interface for method calls."""
        return self.bus.get(self.ADMIN_SERVICE,
                            self.objpath)[self.ADMIN_INTERFACE]

    @glib_call(False)
    def register_admin_policy_callback(self):
        """Registers admin callbacks if it doesn't exist."""

        if self.callbacks:
            return True

        # Generate a random number between 1-1000
        rnumber = math.floor(random.random() * 1000 + 1)

        # Create and publish callbacks
        self.callbacks = self.ExportedAdminPolicyCallbacks()

        self.callbacks.add_observer('admin_client', self)
        objpath = self.ADMIN_CB_OBJ_PATTERN.format(self.hci, rnumber)
        self.bus.register_object(objpath, self.callbacks, None)

        # Register published callbacks with admin daemon
        self.callback_id = self.proxy().RegisterAdminPolicyCallback(objpath)
        return True

    @glib_call(False)
    def unregister_admin_policy_callback(self):
        """Unregisters admin policy callbacks for this client.

        @return: True on success, False otherwise.
        """
        return self.proxy().UnregisterAdminPolicyCallback(self.callback_id)

    @glib_call(None)
    def get_device_policy_effect(self, address):
        """Gets device policy effect.

        @param address: Address of device containing policy effect.

        @return: PolicyEffect as {service_blocked: list[Uuid128Bit],
                 affected: bool} on success, None otherwise.
        """
        name = 'Test policy'
        if address in self.known_devices:
            name = self.known_devices[address]['name']

        device = {
                'address': GLib.Variant('s', address),
                'name': GLib.Variant('s', name)
        }
        return self.proxy().GetDevicePolicyEffect(device)

    @glib_call(None)
    def get_allowed_services(self):
        """Gets allowed services.

        @return: List of allowed services on success, None otherwise.
        """
        return self.proxy().GetAllowedServices()

    @glib_call(False)
    def set_allowed_services(self, services):
        """Sets allowed services.

        @param services: List of 128-bit service UUID.

        @return: True on success, False otherwise.
        """
        return self.proxy().SetAllowedServices(services)

    @glib_call(None)
    def is_service_allowed(self, uuid):
        """Checks if the service is allowed.

        @param uuid: 128-bit service UUID.

        @return: Service allowed as boolean on success, None otherwise.
        """
        return self.proxy().IsServiceAllowed(uuid)
