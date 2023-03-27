# Lint as:python3
# Copyright 2022 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Client class to access the Floss adapter interface."""

from gi.repository import GLib
import logging
import uuid

from autotest_lib.client.bin import utils
from autotest_lib.client.cros.bluetooth.floss.floss_enums import GattStatus
from autotest_lib.client.cros.bluetooth.floss.observer_base import ObserverBase
from autotest_lib.client.cros.bluetooth.floss.utils import (
        generate_dbus_cb_objpath, glib_call, glib_callback)


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
    ADVERTISING_CB_OBJ_NAME = 'test_advertising_client'

    FLOSS_RESPONSE_LATENCY_SECS = 3

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

        # A dict of advertiser_id as key and tx power as value.
        self.active_advs = {}

        # A dict of reg_id as key and tuple of (advertiser_id, status) as value.
        self.start_adv_results = {}

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
        self.start_adv_results[reg_id] = (advertiser_id, status)
        if GattStatus(status) != GattStatus.SUCCESS:
            return

        if advertiser_id in self.active_advs:
            logging.warn(
                    'The set of advertiser_id: %s, is already registered.',
                    advertiser_id)
        else:
            self.active_advs[advertiser_id] = tx_power

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
        if advertiser_id in self.active_advs:
            self.active_advs.pop(advertiser_id)
        else:
            logging.warn('The set of advertiser_id: %s, not registered yet.',
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

    def make_dbus_periodic_advertising_parameters(self,
                                                  adv_periodic_parameters):
        """Makes a struct for periodic advertising parameters D-Bus.

        @param adv_periodic_parameters: A dictionary of periodic advertising
                                        parameters.

        @return: An empty dictionary if adv_periodic_parameters is None or some
                 periodic parameters are missing from it, else returns a
                 dictionary with periodic advertising parameters.
        """
        if not adv_periodic_parameters:
            return {}

        missing_periodic_parameters = {'include_tx_power', 'interval'} - set(
                adv_periodic_parameters.keys())

        if missing_periodic_parameters:
            logging.error(
                    'Missing periodic advertisement parameters data with '
                    'keys: %s', ','.join(missing_periodic_parameters))
            return {}

        return {
                'include_tx_power':
                GLib.Variant('b', adv_periodic_parameters['include_tx_power']),
                'interval':
                GLib.Variant('i', adv_periodic_parameters['interval'])
        }

    def make_dbus_advertising_set_parameters(self, adv_set_parameters):
        """Makes a struct for advertising set parameters D-Bus.

        @param adv_set_parameters: A dictionary of advertising set parameters.

        @return: An empty dictionary if adv_set_parameters is None or some
                 parameters are missing from it, else returns a dictionary with
                 advertising set parameters.
        """
        if not adv_set_parameters:
            return {}

        missing_parameters = {
                'connectable', 'scannable', 'is_legacy', 'is_anonymous',
                'include_tx_power', 'primary_phy', 'secondary_phy', 'interval',
                'tx_power_level', 'own_address_type'
        } - set(adv_set_parameters.keys())

        if missing_parameters:
            logging.error('Missing advertisement parameters with keys: %s',
                          ','.join(missing_parameters))
            return {}

        return {
                'connectable':
                GLib.Variant('b', adv_set_parameters['connectable']),
                'scannable':
                GLib.Variant('b', adv_set_parameters['scannable']),
                'is_legacy':
                GLib.Variant('b', adv_set_parameters['is_legacy']),
                'is_anonymous':
                GLib.Variant('b', adv_set_parameters['is_anonymous']),
                'include_tx_power':
                GLib.Variant('b', adv_set_parameters['include_tx_power']),
                'primary_phy':
                GLib.Variant('u', adv_set_parameters['primary_phy']),
                'secondary_phy':
                GLib.Variant('u', adv_set_parameters['secondary_phy']),
                'interval':
                GLib.Variant('i', adv_set_parameters['interval']),
                'tx_power_level':
                GLib.Variant('i', adv_set_parameters['tx_power_level']),
                'own_address_type':
                GLib.Variant('i', adv_set_parameters['own_address_type'])
        }

    def make_dbus_advertise_data(self, adv_data):
        """Makes a struct for advertising data D-Bus.

        @param adv_data: A dictionary of advertising data.

        @return: An empty dictionary if adv_data is None or some data are
                 missing from it, else returns a dictionary with advertising
                 data.
        """
        if not adv_data:
            return {}

        missing_data = {
                'service_uuids', 'solicit_uuids', 'transport_discovery_data',
                'manufacturer_data', 'service_data', 'include_tx_power_level',
                'include_device_name'
        } - set(adv_data.keys())

        if missing_data:
            logging.error('Missing advertisement data with keys: %s',
                          ','.join(missing_data))
            return {}

        return {
                'service_uuids':
                GLib.Variant(
                        'aay',
                        self.convert_uuids_to_bytearray(
                                adv_data['service_uuids'])),
                'solicit_uuids':
                GLib.Variant(
                        'aay',
                        self.convert_uuids_to_bytearray(
                                adv_data['solicit_uuids'])),
                'transport_discovery_data':
                GLib.Variant('aay', adv_data['transport_discovery_data']),
                'manufacturer_data':
                GLib.Variant(
                        'a{qay}',
                        self.convert_manufacturer_data_to_bytearray(
                                adv_data['manufacturer_data'])),
                'service_data':
                GLib.Variant(
                        'a{say}',
                        self.convert_service_data_to_bytearray(
                                adv_data['service_data'])),
                'include_tx_power_level':
                GLib.Variant('b', adv_data['include_tx_power_level']),
                'include_device_name':
                GLib.Variant('b', adv_data['include_device_name'])
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

        # Create and publish callbacks
        self.callbacks = self.ExportedAdvertisingCallbacks()
        self.callbacks.add_observer('advertising_client', self)
        objpath = generate_dbus_cb_objpath(self.ADVERTISING_CB_OBJ_NAME,
                                           self.hci)
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
                              max_ext_adv_events):
        """Starts advertising set.

        @param parameters: AdvertisingSetParameters structure.
        @param advertise_data: AdvertiseData structure.
        @param scan_response: Scan response data(optional).
        @param periodic_parameters: PeriodicAdvertisingParameters structure
                                    (optional).
        @param periodic_data: AdvertiseData structure(optional).
        @param duration: Time to start advertising set.
        @param max_ext_adv_events: Maximum of extended advertising events.

        @return: Returns the reg_id for the advertising set on success,
                 None otherwise.
        """
        return self.proxy().StartAdvertisingSet(
                parameters, advertise_data, scan_response, periodic_parameters,
                periodic_data, duration, max_ext_adv_events, self.callback_id)

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

    @staticmethod
    def convert_service_data_to_bytearray(service_data):
        """Converts values in service data dict to bytearray.

        @param service_data: A dict of UUID as key and service data for
                             specific UUID as value.

        @return: Dictionary of the data converted.
        """
        return {k: bytearray(v) for k, v in service_data.items()}

    @staticmethod
    def convert_manufacturer_data_to_bytearray(manufacturer_data):
        """Converts values in manufacturer data dict to bytearray.

        It also converts the hex keys to integers.

        @param manufacturer_data: A dict of manufacturer id as key and
                                  manufacturer data for specific id as value.

        @return: Dictionary of the data converted.
        """
        return {int(k, 16): bytearray(v) for k, v in manufacturer_data.items()}

    @staticmethod
    def convert_uuids_to_bytearray(uuids):
        """Converts values in uuids list to bytearray.

        @param uuids: A list of UUID128bit.

        @return: List of the data converted.
        """
        return [uuid.UUID(i).bytes for i in uuids]

    def wait_for_adv_started(self, reg_id):
        """Waits for advertising started.

        @param reg_id: The reg_id for advertising set.

        @return: Advertiser_id, status for specific reg_id on success,
                (None, None) otherwise.
        """
        try:
            utils.poll_for_condition(
                    condition=(lambda: reg_id in self.start_adv_results),
                    timeout=self.FLOSS_RESPONSE_LATENCY_SECS)

        except TimeoutError:
            logging.error('on_advertising_set_started not called')
            return (None, None)

        advertise_id, status = self.start_adv_results[reg_id]

        # Consume the result here because we have no straightforward timing
        # to drop the info. We can't drop it in wait_for_adv_stopped because
        # if the advertising failed to start then it makes no sense for the
        # user to call wait_for_adv_stopped.
        del self.start_adv_results[reg_id]

        return advertise_id, status

    def wait_for_adv_stopped(self, advertiser_id):
        """Waits for advertising stopped.

        @param advertiser_id: The advertiser_id for advertising set.

        @return: True on success, False otherwise.
        """
        try:
            utils.poll_for_condition(
                    condition=(
                            lambda: advertiser_id not in self.active_advs),
                    timeout=self.FLOSS_RESPONSE_LATENCY_SECS)

            return True
        except TimeoutError:
            logging.error('on_advertising_set_stopped not called')
            return False

    def start_advertising_set_sync(self, parameters, advertise_data,
                                   scan_response, periodic_parameters,
                                   periodic_data, duration,
                                   max_ext_adv_events):
        """Starts advertising set sync.

        @param parameters: AdvertisingSetParameters structure.
        @param advertise_data: AdvertiseData structure.
        @param scan_response: Scan response data(optional).
        @param periodic_parameters: PeriodicAdvertisingParameters structure
                                    (optional).
        @param periodic_data: AdvertiseData structure(optional).
        @param duration: Time to start advertising set.
        @param max_ext_adv_events: Maximum of extended advertising events.

        @return: Advertiser_id for specific reg_id on success, None otherwise.
        """

        reg_id = self.start_advertising_set(parameters, advertise_data,
                                            scan_response, periodic_parameters,
                                            periodic_data, duration,
                                            max_ext_adv_events)
        if reg_id is None:
            logging.error('Failed to start advertisement set')
            return None

        advertise_id, status = self.wait_for_adv_started(reg_id)
        if GattStatus(status) != GattStatus.SUCCESS:
            logging.error(
                    'Failed to start advertisement with id: %s, status = %s',
                    advertise_id, status)
            return None
        return advertise_id

    def stop_advertising_set_sync(self, advertiser_id):
        """Stops advertising set sync.

        @param advertiser_id: Advertiser_id for set of advertising.

        @return: True on success, False otherwise.
        """
        if not self.stop_advertising_set(advertiser_id):
            return False
        return self.wait_for_adv_stopped(advertiser_id)

    def stop_all_advertising_sets(self):
        """Stops all advertising sets.

        @return: True on success, False otherwise.
        """
        failed_adv_ids = []
        adv_ids = [i for i in self.active_advs]
        for i in adv_ids:
            if not self.stop_advertising_set_sync(i):
                failed_adv_ids.append(i)

        if len(failed_adv_ids) > 0:
            logging.error('Failed to reset advertisement sets with ids: %s',
                          ','.join(failed_adv_ids))
            return False
        return True

    def get_tx_power(self, advertiser_id):
        """Gets tx power value for specific advertiser id.

        @param advertiser_id: Advertiser_id for set of advertising.

        @return: Advertiser_id on success, None otherwise.
        """
        return self.active_advs.get(advertiser_id)
