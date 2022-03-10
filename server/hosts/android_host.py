# Lint as: python2, python3
# Copyright (c) 2022 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
#
# Expects to be run in an environment with sudo and no interactive password
# prompt, such as within the Chromium OS development chroot.

import logging

import common

from autotest_lib.client.common_lib import error
from autotest_lib.server.hosts import host_info
from autotest_lib.server.hosts import attached_device_host


class AndroidHost(object):
    """Host class for Android devices"""
    PHONE_STATION_LABEL_PREFIX = "associated_hostname"
    SERIAL_NUMBER_PREFIX = "serial_number"

    def __init__(self, hostname, host_info_store=None, *args, **dargs):
        """Construct a AndroidHost object.

        Args:
            hostname: Hostname of the Android phone.
            host_info_store: Optional host_info.CachingHostInfoStore object
                             to obtain / update host information.
        """
        self.hostname = hostname
        self.host_info_store = (host_info_store
                                or host_info.InMemoryHostInfoStore())
        self.associated_hostname = None
        self.serial_number = None
        self._read_essential_data_from_host_info_store()
        # Since we won't be ssh into an Android device directly, all the
        # communication will be handled by run ADB CLI on the phone
        # station(chromebox or linux machine) that physically connected
        # to the Android devices via USB cable. So we need to setup an
        # AttachedDeviceHost for phone station as ssh proxy.
        self.phone_station = self._create_phone_station_host_proxy()

    def _create_phone_station_host_proxy(self):
        logging.info('Creating host for phone station %s',
                     self.associated_hostname)
        return attached_device_host.AttachedDeviceHost(
                hostname=self.associated_hostname,
                serial_number=self.serial_number)

    def _read_essential_data_from_host_info_store(self):
        info = self.host_info_store.get()
        self.associated_hostname = info.get_label_value(
                self.PHONE_STATION_LABEL_PREFIX)
        if not self.associated_hostname:
            raise error.AutoservError(
                    'Failed to initialize Android host due to'
                    ' associated_hostname is not found in host_info_store.')
        self.serial_number = info.get_label_value(self.SERIAL_NUMBER_PREFIX)
        if not self.serial_number:
            raise error.AutoservError(
                    'Failed to initialize Android host due to'
                    ' serial_number is not found in host_info_store.')

    def close(self):
        """Clean up Android host and its phone station proxy host."""
        if self.phone_station:
            self.phone_station.close()
