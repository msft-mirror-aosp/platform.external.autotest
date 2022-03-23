# Lint as: python2, python3
# Copyright (c) 2022 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
#
# Expects to be run in an environment with sudo and no interactive password
# prompt, such as within the Chromium OS development chroot.

import logging
import socket

import common

from autotest_lib.client.common_lib import error
from autotest_lib.server.hosts import host_info
from autotest_lib.server.hosts import attached_device_host


class AndroidHost(object):
    """Host class for Android devices"""
    PHONE_STATION_LABEL_PREFIX = "associated_hostname"
    SERIAL_NUMBER_LABEL_PREFIX = "serial_number"
    # adb auth key path on the phone_station.
    ADB_KEY_PATH = '/var/lib/android_keys'

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
        self.adb_tcp_mode = False
        self.closed = False

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
        self.serial_number = info.get_label_value(
                self.SERIAL_NUMBER_LABEL_PREFIX)
        if not self.serial_number:
            raise error.AutoservError(
                    'Failed to initialize Android host due to'
                    ' serial_number is not found in host_info_store.')

    def adb_over_tcp(self, port=5555):
        """Restart adb server listening on a TCP port.

        Args:
            port: Tcp port for adb server to listening on, default value
                  is 5555 which is the default TCP/IP port for adb.
        """
        self.run_adb_command('tcpip %s' % str(port))
        self.adb_tcp_mode = True

    def ensure_device_connectivity(self):
        """Ensure we can interact with the Android device via adb and
        the device is in the expected state.
        """
        res = self.run_adb_command('get-state')
        state = res.stdout.strip()
        logging.info('Android device state from adb: %s', state)
        return state == 'device'

    def get_wifi_ip_address(self):
        """Get ipv4 address from the Android device"""
        res = self.run_adb_command('shell ip route')
        # An example response would looks like: "192.168.86.0/24 dev wlan0"
        # " proto kernel scope link src 192.168.86.22 \n"
        ip_string = res.stdout.strip().split(' ')[-1]
        logging.info('Ip address collected from the Android device: %s',
                     ip_string)
        try:
            socket.inet_aton(ip_string)
        except (OSError, ValueError, socket.error):
            raise error.AutoservError(
                    'Failed to get ip address from the Android device.')
        return ip_string

    def job_start(self):
        """This method is called from create_host factory when
        construct the host object. We need to override it since actions
        like copy /var/log/messages are not applicable on Android devices.
        """
        logging.info('Skip standard job_start actions for Android host.')

    def restart_adb_server(self):
        """Restart adb server from the phone station"""
        self.stop_adb_server()
        self.start_adb_server()

    def run_adb_command(self, adb_command, ignore_status=False):
        """Run adb command on the Android device.

        Args:
            adb_command: adb commands to execute on the Android device.

        Returns:
            An autotest_lib.client.common_lib.utils.CmdResult object.
        """
        command = 'adb -s %s %s' % (self.serial_number, adb_command)
        return self.phone_station.run(command, ignore_status=ignore_status)

    def start_adb_server(self):
        """Start adb server from the phone station."""
        # Adb home is created upon CrOS login, however on labstation we
        # never login so we'll need to ensure the adb home is exist before
        # starting adb server.
        self.phone_station.run("mkdir -p /run/arc/adb")
        self.phone_station.run("ADB_VENDOR_KEYS=%s adb start-server" %
                               self.ADB_KEY_PATH)
        # Logging states of all attached devices.
        self.phone_station.run('adb devices')

    def stop_adb_server(self):
        """Stop adb server from the phone station."""
        self.phone_station.run("adb kill-server")

    def close(self):
        """Clean up Android host and its phone station proxy host."""
        if self.closed:
            logging.debug('Android host %s already closed.', self.hostname)
            return
        if self.adb_tcp_mode:
            # In some rare cases, leave the Android device in adb over tcp
            # mode may break USB connection so we want to always reset adb
            # to usb mode before teardown.
            self.run_adb_command('usb', ignore_status=True)
        self.stop_adb_server()
        if self.phone_station:
            self.phone_station.close()
        self.closed = True
