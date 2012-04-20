#!/usr/bin/python
# Copyright (c) 2012 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Implement a modem proxy to talk to a ModemManager1 modem."""

from autotest_lib.client.cros.cellular import cellular
from autotest_lib.client.cros.cellular import mm1
import dbus


class Modem(object):
    """An object which talks to a ModemManager1 modem."""
    # MM_MODEM_GSM_ACCESS_TECH (not exported)
    # From /usr/include/mm/mm-modem.h
    _MM_MODEM_GSM_ACCESS_TECH_UNKNOWN = 0
    _MM_MODEM_GSM_ACCESS_TECH_GSM = 1
    _MM_MODEM_GSM_ACCESS_TECH_GSM_COMPACT = 2
    _MM_MODEM_GSM_ACCESS_TECH_GPRS = 3
    _MM_MODEM_GSM_ACCESS_TECH_EDGE = 4
    _MM_MODEM_GSM_ACCESS_TECH_UMTS = 5
    _MM_MODEM_GSM_ACCESS_TECH_HSDPA = 6
    _MM_MODEM_GSM_ACCESS_TECH_HSUPA = 7
    _MM_MODEM_GSM_ACCESS_TECH_HSPA = 8

    # Mapping of modem technologies to cellular technologies
    _ACCESS_TECH_TO_TECHNOLOGY = {
        _MM_MODEM_GSM_ACCESS_TECH_GSM: cellular.Technology.WCDMA,
        _MM_MODEM_GSM_ACCESS_TECH_GSM_COMPACT: cellular.Technology.WCDMA,
        _MM_MODEM_GSM_ACCESS_TECH_GPRS: cellular.Technology.GPRS,
        _MM_MODEM_GSM_ACCESS_TECH_EDGE: cellular.Technology.EGPRS,
        _MM_MODEM_GSM_ACCESS_TECH_UMTS: cellular.Technology.WCDMA,
        _MM_MODEM_GSM_ACCESS_TECH_HSDPA: cellular.Technology.HSDPA,
        _MM_MODEM_GSM_ACCESS_TECH_HSUPA: cellular.Technology.HSUPA,
        _MM_MODEM_GSM_ACCESS_TECH_HSPA: cellular.Technology.HSDUPA,
    }

    def __init__(self, manager, path):
        self.manager = manager
        self.bus = manager.bus
        self.service = manager.service
        self.path = path

    def Modem(self):
        obj = self.bus.get_object(self.service, self.path)
        return dbus.Interface(obj, mm1.MODEM_INTERFACE)

    def SimpleModem(self):
        obj = self.bus.get_object(self.service, self.path)
        return dbus.Interface(obj, mm1.MODEM_SIMPLE_INTERFACE)

    def GsmModem(self):
        obj = self.bus.get_object(self.service, self.path)
        return dbus.Interface(obj, mm1.MODEM_MODEM3GPP_INTERFACE)

    def CdmaModem(self):
        obj = self.bus.get_object(self.service, self.path)
        return dbus.Interface(obj, mm1.MODEM_MODEMCDMA_INTERFACE)

    def Sim(self):
        obj = self.bus.get_object(self.service, self.path)
        return dbus.Interface(obj, mm1.SIM_INTERFACE)

    def GetAll(self, iface):
        obj = self.bus.get_object(self.service, self.path)
        obj_iface = dbus.Interface(obj, dbus.PROPERTIES_IFACE)
        return obj_iface.GetAll(iface)

    def _GetModemInterfaces(self):
        return [
            mm1.MODEM_MODEM_INTERFACE,
            mm1.MODEM_SIMPLE_INTERFACE,
            mm1.MODEM_MODEM3GPP_INTERFACE,
            mm1.MODEM_MODEMCDMA_INTERFACE
            ]

    def GetModemProperties(self):
        """Returns all DBus Properties of all the modem interfaces."""
        props = dict()
        for iface in self._GetModemInterfaces():
            try:
                d = self.GetAll(iface)
            except dbus.exceptions.DBusException:
                continue
            if d:
                for k, v in d.iteritems():
                    props[k] = v

        return props

    def GetAccessTechnology(self):
        props = self.GetModemProperties()
        tech = props.get('AccessTechnology')
        return Modem._ACCESS_TECH_TO_TECHNOLOGY[tech]

    def _GetRegistrationState(self):
        # TODO(jglasgow): implement
        return False

    def ModemIsRegistered(self):
        """Ensure that modem is registered on the network."""
        return self._GetRegistrationState()

    def ModemIsRegisteredUsing(self, technology):
        """Ensure that modem is registered on the network with a technology."""
        if not self.ModemIsRegistered():
            return False

        reported_tech = self.GetAccessTechnology()

        # TODO(jglasgow): Remove this mapping.  Basestation and
        # reported technology should be identical.
        BASESTATION_TO_REPORTED_TECHNOLOGY = {
            cellular.Technology.GPRS: cellular.Technology.GPRS,
            cellular.Technology.EGPRS: cellular.Technology.GPRS,
            cellular.Technology.WCDMA: cellular.Technology.HSDUPA,
            cellular.Technology.HSDPA: cellular.Technology.HSDUPA,
            cellular.Technology.HSUPA: cellular.Technology.HSDUPA,
            cellular.Technology.HSDUPA: cellular.Technology.HSDUPA,
            cellular.Technology.HSPA_PLUS: cellular.Technology.HSPA_PLUS
        }

        return BASESTATION_TO_REPORTED_TECHNOLOGY[technology] == reported_tech

    def IsEnabled(self):
        d = self.GetAll(mm1.MODEM_INTERFACE)
        return d['State'] >= mm1.MM_MODEM_STATE_ENABLED

    def Enable(self, enable):
        self.Modem().Enable(enable)

    def Connect(self, props):
        self.SimpleModem().Connect(props)

    def Disconnect(self):
        self.SimpleModem().Disconnect('/')


class ModemManager(object):
    """An object which talks to a ModemManager1 service."""

    def __init__(self):
        self.bus = dbus.SystemBus()
        self.service = mm1.MODEM_MANAGER_INTERFACE
        self.path = mm1.OMM
        self.manager = dbus.Interface(
            self.bus.get_object(self.service, self.path),
            mm1.MODEM_MANAGER_INTERFACE)
        self.objectmanager = dbus.Interface(
            self.bus.get_object(self.service, self.path), mm1.OFDOM)

    def EnumerateDevices(self):
        devices = self.objectmanager.GetManagedObjects()
        return devices.keys()

    def GetModem(self, path):
        return Modem(self, path)
