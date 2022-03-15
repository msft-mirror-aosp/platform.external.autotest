# Lint as: python2, python3
# Copyright (c) 2021 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""
This module provides bindings for ModemManager1.

"""

import dbus
import dbus.mainloop.glib
import logging
import time

from autotest_lib.client.bin import utils
from autotest_lib.client.cros.cellular import mm1_constants


def _is_unknown_dbus_binding_exception(e):
    return (isinstance(e, dbus.exceptions.DBusException) and
            e.get_dbus_name() in [mm1_constants.DBUS_SERVICE_UNKNOWN,
                                  mm1_constants.DBUS_UNKNOWN_METHOD,
                                  mm1_constants.DBUS_UNKNOWN_OBJECT,
                                  mm1_constants.DBUS_UNKNOWN_INTERFACE])


class ModemManager1ProxyError(Exception):
    """Exceptions raised by ModemManager1ProxyError and it's children."""
    pass


class ModemManager1Proxy(object):
    """A wrapper around a DBus proxy for ModemManager1."""

    # Amount of time to wait between attempts to connect to ModemManager1.
    CONNECT_WAIT_INTERVAL_SECONDS = 0.2

    @classmethod
    def get_proxy(cls, bus=None, timeout_seconds=10):
        """Connect to ModemManager1 over DBus, retrying if necessary.

        After connecting to ModemManager1, this method will verify that
        ModemManager1 is answering RPCs.

        @param bus: D-Bus bus to use, or specify None and this object will
            create a mainloop and bus.
        @param timeout_seconds: float number of seconds to try connecting
            A value <= 0 will cause the method to return immediately,
            without trying to connect.
        @return a ModemManager1Proxy instance if we connected, or None
            otherwise.
        @raise ModemManager1ProxyError if it fails to connect to
            ModemManager1.

        """
        def _connect_to_mm1(bus):
            try:
                # We create instance of class on which this classmethod was
                # called. This way, calling
                # SubclassOfModemManager1Proxy.get_proxy() will get a proxy of
                # the right type.
                return cls(bus=bus)
            except dbus.exceptions.DBusException as e:
                if _is_unknown_dbus_binding_exception(e):
                    return None
                raise ModemManager1ProxyError(
                    'Error connecting to ModemManager1. DBus error: |%s|',
                    repr(e))

        utils.poll_for_condition(
            lambda: _connect_to_mm1(bus) is not None,
            exception=ModemManager1ProxyError(
                'Timed out connecting to ModemManager1'),
            timeout=timeout_seconds,
            sleep_interval=ModemManager1Proxy.CONNECT_WAIT_INTERVAL_SECONDS)
        connection = _connect_to_mm1(bus)

        # Check to make sure ModemManager1 is responding to DBus requests by
        # setting the logging to debug.
        connection.manager.SetLogging('DEBUG', timeout=timeout_seconds)

        return connection

    def __init__(self, bus=None):
        if bus is None:
            dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
            bus = dbus.SystemBus()
        self._bus = bus
        self._manager = dbus.Interface(
            self._bus.get_object(mm1_constants.I_MODEM_MANAGER,
                                 mm1_constants.MM1),
            mm1_constants.I_MODEM_MANAGER)
        self._device = None

    @property
    def manager(self):
        """@return the DBus ModemManager1 Manager object."""
        return self._manager

    def inhibit_device(self, inhibit):
        """

        Uses Modem Manager InhibitDevice DBus API to inhibit/uninhibit
        @param inhibit: true to inhibit the modem and false to uninhibit it.

        InhibitDevice API:
        @uid: the unique ID of the physical device, given in the
              #org.freedesktop.ModemManager1.Modem:Device property.
        @inhibit: %TRUE to inhibit the modem and %FALSE to uninhibit it.

        Inhibit or uninhibit the device.

        When the modem is inhibited ModemManager will close all its ports and
        unexport it from the bus, so that users of the interface are no longer
        able to operate with it.

        This operation binds the inhibition request to the existence of the
        caller in the DBus bus. If the caller disappears from the bus, the
        inhibition will automatically removed.
        """
        try:
            if not self._manager:
                raise ModemManager1ProxyError(
                    'Failed to obtain dbus manager object.- No manager')
            if not inhibit and not self._device:
                raise ModemManager1ProxyError(
                    'Uninhibit called before inhibit %s' % self._device)

            if inhibit:
                modem = self.get_modem()
                if not modem:
                    raise ModemManager1ProxyError(
                        'Failed to to obtain dbus manager object. - No modem')

                self._device = modem.properties(
                mm1_constants.I_MODEM).get('Device')

            logging.debug('device to be inhibited/uninhibited %s', self._device)
            self._manager.InhibitDevice(dbus.String(self._device), inhibit)

            logging.debug('inhibit=%r done with %s', inhibit, self._device)

            if inhibit:
                time.sleep(mm1_constants.MM_INHIBIT_PROCESSING_TIME)
            else:
                result = self.wait_for_modem(
                    mm1_constants.MM_UNINHIBIT_PROCESSING_TIME)

                time.sleep(mm1_constants.MM_REPROBE_PROCESSING_TIME)
                if result is None:
                    raise ModemManager1ProxyError('No modem after uninhibit')
        except dbus.exceptions.DBusException as e:
            raise ModemManager1ProxyError(
                'Failed to to obtain dbus object for the modem.'
                'DBus error: %s' % repr(e))

    def get_modem(self):
        """
        Return the one and only modem object.

        This method distinguishes between no modem and more than one modem.
        In the former, this could happen if the modem has not yet surfaced and
        is not really considered an error. The caller can wait for the modem
        by repeatedly calling this method. In the latter, it is a clear error
        condition and an exception will be raised.

        Every call to |get_modem| obtains a fresh DBus proxy for the modem. So,
        if the modem DBus object has changed between two calls to this method,
        the proxy returned will be for the currently exported modem.

        @return a ModemProxy object.  Return None if no modem is found.
        @raise ModemManager1ProxyError unless exactly one modem is found.

        """
        try:
            object_manager = dbus.Interface(
                self._bus.get_object(mm1_constants.I_MODEM_MANAGER,
                                     mm1_constants.MM1),
                mm1_constants.I_OBJECT_MANAGER)
            modems = object_manager.GetManagedObjects()
        except dbus.exceptions.DBusException as e:
            raise ModemManager1ProxyError(
                'Failed to list the available modems. DBus error: %s' %
                repr(e))

        if not modems:
            return None
        elif len(modems) > 1:
            raise ModemManager1ProxyError(
                'Expected one modem object, found %d' % len(modems))

        modem_proxy = ModemProxy(self._bus, list(modems.keys())[0])
        # Check that this object is valid
        try:
            modem_proxy.modem.GetAll(mm1_constants.I_MODEM,
                                     dbus_interface=mm1_constants.I_PROPERTIES)
            return modem_proxy
        except dbus.exceptions.DBusException as e:
            if _is_unknown_dbus_binding_exception(e):
                return None
            raise ModemManager1ProxyError(
                'Failed to obtain dbus object for the modem. DBus error: %s' %
                repr(e))

    def wait_for_modem(self, timeout_seconds):
        """
        Wait for the modem to appear.

        @param timeout_seconds: Number of seconds to wait for modem to appear.
        @return a ModemProxy object.
        @raise ModemManager1ProxyError if no modem is found within the timeout
                or if more than one modem is found. NOTE: This method does not
                wait for a second modem. The exception is raised if there is
                more than one modem at the time of polling.

        """
        return utils.poll_for_condition(
            self.get_modem,
            exception=ModemManager1ProxyError('No modem found'),
            timeout=timeout_seconds)


class ModemProxy(object):
    """A wrapper around a DBus proxy for ModemManager1 modem object."""

    # Amount of time to wait for a state transition.
    STATE_TRANSITION_WAIT_SECONDS = 60

    def __init__(self, bus, path):
        self._bus = bus
        self._modem = self._bus.get_object(mm1_constants.I_MODEM_MANAGER, path)

    @property
    def modem(self):
        """@return the DBus modem object."""
        return self._modem

    @property
    def iface_modem(self):
        """@return org.freedesktop.ModemManager1.Modem DBus interface."""
        return dbus.Interface(self._modem, mm1_constants.I_MODEM)

    @property
    def iface_simple_modem(self):
        """@return org.freedesktop.ModemManager1.Simple DBus interface."""
        return dbus.Interface(self._modem, mm1_constants.I_MODEM_SIMPLE)

    @property
    def iface_gsm_modem(self):
        """@return org.freedesktop.ModemManager1.Modem3gpp DBus interface."""
        return dbus.Interface(self._modem, mm1_constants.I_MODEM_3GPP)

    @property
    def iface_cdma_modem(self):
        """@return org.freedesktop.ModemManager1.ModemCdma DBus interface."""
        return dbus.Interface(self._modem, mm1_constants.I_MODEM_CDMA)

    @property
    def iface_properties(self):
        """@return org.freedesktop.DBus.Properties DBus interface."""
        return dbus.Interface(self._modem, dbus.PROPERTIES_IFACE)

    def properties(self, iface):
        """Return the properties associated with the specified interface.

        @param iface: Name of interface to retrieve the properties from.
        @return array of properties.

        """
        return self.iface_properties.GetAll(iface)

    def get_sim(self):
        """
        Return the SIM proxy object associated with this modem.

        @return SimProxy object or None if no SIM exists.

        """
        sim_path = self.properties(mm1_constants.I_MODEM).get('Sim')
        if not sim_path:
            return None
        sim_proxy = SimProxy(self._bus, sim_path)
        # Check that this object is valid
        try:
            sim_proxy.properties(mm1_constants.I_SIM)
            return sim_proxy
        except dbus.exceptions.DBusException as e:
            if _is_unknown_dbus_binding_exception(e):
                return None
            raise ModemManager1ProxyError(
                'Failed to obtain dbus object for the SIM. DBus error: %s' %
                repr(e))

    def get_sim_slots(self):
        """
        The list of SIM slots available in the system, including the SIM object
        paths if the cards are present. If a given SIM slot at a given index
        doesn't have a SIM card available, an empty object path will be given.

        The length of this array of objects will be equal to the amount of
        available SIM slots in the system, and the index in the array is the
        slot index.

        This list includes the SIM object considered as primary active SIM slot
        (#org.freedesktop.ModemManager1.Modem.Sim) at index
        #org.freedesktop.ModemManager1.Modem.ActiveSimSlot.

        @return list of SimSlot paths

        """
        return self.properties(mm1_constants.I_MODEM).get('SimSlots')

    def get_primary_sim_slot(self):
        """
        The index of the primary active SIM slot in the
        #org.freedesktop.ModemManager1.Modem.SimSlots array, given in the [1,N]
        range.

        If multiple SIM slots aren't supported, this property will report None

        In a Multi SIM Single Standby setup, this index identifies the only SIM
        that is currently active. All the remaining slots will be inactive.

        In a Multi SIM Multi Standby setup, this index identifies the active SIM
        that is considered primary, i.e. the one that will be used when a data
        connection is setup.

        @return current primary slot index

        """
        return self.properties(mm1_constants.I_MODEM).get('PrimarySimSlot')

    def set_primary_slot(self, sim_slot):
        """
        Selects which SIM slot to be considered as primary, on devices that
        expose multiple slots in the #org.freedesktop.ModemManager1.Modem
        :SimSlots property.

        When the switch happens the modem may require a full device reprobe,
        so the modem object in DBus will get removed, and recreated once the
        selected SIM slot is in use.

        There is no limitation on which SIM slot to select, so the user may
        also set as primary a slot that doesn't currently have any valid SIM
        card inserted.

        @param: sim_slot: SIM slot number to set as primary.
        @return: success or raise error

        """
        self.iface_modem.SetPrimarySimSlot(dbus.UInt32(sim_slot))

    def wait_for_states(self, states,
                        timeout_seconds=STATE_TRANSITION_WAIT_SECONDS):
        """
        Wait for the modem to transition to a state in |states|.

        This method does not support transitory states (eg. enabling,
        disabling, connecting, disconnecting, etc).

        @param states: List of states the modem can transition to.
        @param timeout_seconds: Max number of seconds to wait.
        @raise ModemManager1ProxyError if the modem does not transition to
            one of the accepted states.

        """
        for state in states:
            if state in [mm1_constants.MM_MODEM_STATE_INITIALIZING,
                         mm1_constants.MM_MODEM_STATE_DISABLING,
                         mm1_constants.MM_MODEM_STATE_ENABLING,
                         mm1_constants.MM_MODEM_STATE_SEARCHING,
                         mm1_constants.MM_MODEM_STATE_DISCONNECTING,
                         mm1_constants.MM_MODEM_STATE_CONNECTING]:
                raise ModemManager1ProxyError(
                    'wait_for_states() does not support transitory states.')

        utils.poll_for_condition(
            lambda: self.properties(mm1_constants.I_MODEM)[
                mm1_constants.MM_MODEM_PROPERTY_NAME_STATE] in states,
            exception=ModemManager1ProxyError(
                'Timed out waiting for modem to enter one of these '
                'states: %s, current state=%s' %
                (states,
                 self.properties(mm1_constants.I_MODEM)[
                     mm1_constants.MM_MODEM_PROPERTY_NAME_STATE])),
            timeout=timeout_seconds)

class SimProxy(object):
    """A wrapper around a DBus proxy for ModemManager1 SIM object."""

    def __init__(self, bus, path):
        self._bus = bus
        self._sim = self._bus.get_object(mm1_constants.I_MODEM_MANAGER, path)

    @property
    def sim(self):
        """@return the DBus SIM object."""
        return self._sim

    @property
    def iface_properties(self):
        """@return org.freedesktop.DBus.Properties DBus interface."""
        return dbus.Interface(self._sim, dbus.PROPERTIES_IFACE)

    @property
    def iface_sim(self):
        """@return org.freedesktop.ModemManager1.Sim DBus interface."""
        return dbus.Interface(self._sim, mm1_constants.I_SIM)

    def properties(self, iface=mm1_constants.I_SIM):
        """Return the properties associated with the specified interface.

        @param iface: Name of interface to retrieve the properties from.
        @return array of properties.

        """
        return self.iface_properties.GetAll(iface)
