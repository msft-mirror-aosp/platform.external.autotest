# Lint as: python2, python3
# Copyright 2022 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
#
# Expects to be run in an environment with sudo and no interactive password
# prompt, such as within the Chromium OS development chroot.

import time
import logging
import socket

import common

from autotest_lib.client.common_lib import error, utils
from autotest_lib.server.hosts import host_info
from autotest_lib.server.hosts import attached_device_host
from autotest_lib.server.hosts import android_constants
from autotest_lib.server.hosts import base_classes


class AndroidHost(base_classes.Host):
    """Host class for Android devices"""
    PHONE_STATION_LABEL_PREFIX = "associated_hostname"
    SERIAL_NUMBER_LABEL_PREFIX = "serial_number"
    # adb auth key path on the phone_station.
    ADB_KEY_PATH = '/var/lib/android_keys'

    def __init__(self,
                 hostname,
                 host_info_store=None,
                 android_args=None,
                 *args,
                 **dargs):
        """Construct a AndroidHost object.

        Args:
            hostname: Hostname of the Android phone.
            host_info_store: Optional host_info.CachingHostInfoStore object
                             to obtain / update host information.
            android_args: Android args for local test run.
        """
        self.hostname = hostname
        super(AndroidHost, self).__init__(*args, **dargs)
        self.host_info_store = (host_info_store
                                or host_info.InMemoryHostInfoStore())
        self.associated_hostname = None
        self.serial_number = None
        self.phone_station_ssh_port = None
        self.phone_station_ip_addr = None
        # For local test, android_args are passed in.
        if android_args:
            self._read_essential_data_from_args_dict(android_args)
            self._read_optional_data_from_args_dict(android_args)
        else:
            self._read_essential_data_from_host_info_store()
        # Since we won't be ssh into an Android device directly, all the
        # communication will be handled by run ADB CLI on the phone
        # station(chromebox or linux machine) that physically connected
        # to the Android devices via USB cable. So we need to setup an
        # AttachedDeviceHost for phone station as ssh proxy.
        self.phone_station = self._create_phone_station_host_proxy()
        self.adb_tcp_mode = False
        self.usb_dev_path = None
        self.closed = False
        # In order to expose the forwarded adb port to outside machines we start
        # socat in the background, cache the PID to clean up on close.
        self.socat_process_id = None

    def _create_phone_station_host_proxy(self):
        logging.info('Creating host for phone station %s',
                     self.associated_hostname)
        return attached_device_host.AttachedDeviceHost(
                hostname=self.associated_hostname,
                serial_number=self.serial_number,
                phone_station_ssh_port=self.phone_station_ssh_port)

    def _read_essential_data_from_args_dict(self, android_args):
        self.associated_hostname = android_args.get(
                android_constants.ANDROID_PHONE_STATION_ATTR)
        self.phone_station_ssh_port = android_args.get(
                android_constants.ANDROID_PHONE_STATION_SSH_PORT_ATTR)
        self.serial_number = android_args.get(
                android_constants.ANDROID_SERIAL_NUMBER_ATTR)

    def _read_optional_data_from_args_dict(self, android_args):
        self.phone_station_ip_addr = android_args.get(
                android_constants.ANDROID_PHONE_STATION_IP_ATTR, None)

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

    def adb_over_tcp(self, port=5555, persist_reboot=False):
        """Restart adb server listening on a TCP port.

        Args:
            port: Tcp port for adb server to listening on, default value
                  is 5555 which is the default TCP/IP port for adb.
            persist_reboot: True for adb over tcp to continue listening
                            after the device reboots.
        """
        port = str(port)
        if persist_reboot:
            # Configuring the adb-over-tcpip port to persist requires root.
            self.run_adb_command('root')
            self.run_adb_command('shell setprop persist.adb.tcp.port %s' %
                                 port)
            self.run_adb_command('shell setprop ctl.restart adbd')
            self.wait_for_transport_state()

        self.run_adb_command('tcpip %s' % port)
        self.adb_tcp_mode = True

    def get_free_port(self, start_port, end_port):
        """Attempts to find a free port on the labstation in provided range.

        Args:
            start_port: Start port of search range.
            end_port: End of port search range.
        """
        for port in range(start_port, end_port):
            try:
                self.phone_station.run('lsof -i:%d' % port)
            except:
                return port

        raise error.AutoservError('Failed to find free labstation port')

    def forward_device_port(self, phone_port=5555, duration=3600):
        """Forwards a port on the phone to one on the labstation.

        Args:
            phone_port: TCP port on phone to be forwarded.
            duration: The maximum length of time to forward the ports for.

        Returns:
            host_port: TCP port on the labstation that the phone port is forwarded to.
        """
        # Forward an intermediate port from the phone to the host.
        intermediate_port = self.get_free_port(phone_port, phone_port + 100)

        # Retry as it may take a few seconds for the adb server to start up on
        # the phone.
        for _ in range(5):
            try:
                self.run_adb_command('forward tcp:%s tcp:%s' %
                                     (intermediate_port, phone_port))
                break
            except:
                time.sleep(1)
        else:
            raise error.AutoservError(
                    'Failed to enable forwarding on labstation')

        # Create a new port listening on all interfaces (0.0.0.0) and redirect
        # to the intermediate port since the port opened by ADB will only
        # listen on the loopback interface and can't be easily accessed
        # externally.
        host_port = self.get_free_port(intermediate_port,
                                       intermediate_port + 100)
        res = self.phone_station.run_background(
                'timeout %ds socat tcp-listen:%d,bind=0.0.0.0,tcp-nodelay,fork,forever tcp:127.0.0.1:%d'
                % (duration, host_port, intermediate_port))

        # Since we launched using timeout, get the PID of the underlying socat
        # process otherwise we'll just orphan it.
        res = self.phone_station.run('ps -o pid= --ppid %s' %
                                     res).stdout.strip()

        # Cache the process_id for cleanup later.
        if res.isdigit():
            self.socat_process_id = int(res)
        else:
            logging.warning('Failed to parse socat process id from: %s', res)

        return host_port

    def cache_usb_dev_path(self):
        """
        Read and cache usb devpath for the Android device.
        """
        cmd = 'adb devices -l | grep %s' % self.serial_number
        res = self.phone_station.run(cmd)
        for line in res.stdout.strip().split('\n'):
            if len(line.split()) > 2 and line.split()[1] == 'device':
                self.usb_dev_path = line.split()[2]
                logging.info('USB devpath: %s', self.usb_dev_path)
                break
        if not self.usb_dev_path:
            logging.warning(
                    'Failed to collect usbdev path of the Android device.')

    def ensure_device_connectivity(self):
        """Ensure we can interact with the Android device via adb and
        the device is in the expected state.
        """
        res = self.run_adb_command('get-state')
        state = res.stdout.strip()
        logging.info('Android device state from adb: %s', state)
        return state == 'device'

    def get_gmscore_version(self):
        """Get the GMSCore version of the Android device."""
        res = self.run_adb_command('shell dumpsys package com.google.android.gms | grep versionCode')
        version = res.stdout.strip()
        logging.info('GMSCore Version on phone: %s', version)
        return version

    def get_phone_station_ip_address(self):
        """Get ipv4 address of the connected labstation."""
        return utils.get_ip_address(self.phone_station.hostname)

    def get_wifi_ip_address(self):
        """Get ipv4 address from the Android device"""
        res = self.run_adb_command('shell ip route')
        # An example response would looks like: "192.168.86.0/24 dev wlan0"
        # " proto kernel scope link src 192.168.86.22 \n"
        ip_string = res.stdout.strip().split(' ')[-1]
        logging.info('IP address collected from the Android device: %s',
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
        # When use adb to interact with an Android device, we prefer to use
        # devpath to distinguish the particular device as the serial number
        # is not guaranteed to be unique.
        if self.usb_dev_path:
            command = 'adb -s %s %s' % (self.usb_dev_path, adb_command)
        else:
            command = 'adb -s %s %s' % (self.serial_number, adb_command)
        return self.phone_station.run(command, ignore_status=ignore_status)

    def wait_for_transport_state(self, transport='usb', state='device'):
        """
        Wait for a device to reach a desired state.

        Args:
            transport: usb, local, any
            state: device, recovery, sideload, bootloader

        """
        self.run_adb_command('wait-for-%s-%s' % (transport, state))

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

    def setup_for_cross_device_tests(self, adb_persist_reboot=False):
        """
        Setup the Android phone for Cross Device tests.

        Ensures the phone can connect to its labstation and sets up
        adb-over-tcp.

        Returns:
            IP Address of Phone.
        """
        dut_out = self.phone_station.run('echo True').stdout.strip()
        if dut_out != 'True':
            raise error.TestError('phone station stdout != True (got: %s)',
                                  dut_out)

        self.restart_adb_server()
        self.cache_usb_dev_path()
        self.ensure_device_connectivity()
        self.get_gmscore_version()
        ip_address = self.get_wifi_ip_address()
        self.adb_over_tcp(persist_reboot=adb_persist_reboot)
        return ip_address

    def setup_for_adb_over_lab_network(self):
        """
        Setup the Android phone for testing using adb over the lab network.

        Ensures the phone can connect to its labstation and sets up
        adb-over-tcp and forwards the port to the labstation so adb can be  used
        on the labstation without requiring a separate local network to
        control the phone.

        Note: This configuration does not persist device reboots.

        Returns:
            IP Address of labstation.
            Port on labstation to connect to.
        """
        dut_out = self.phone_station.run('echo True').stdout.strip()
        if dut_out != 'True':
            raise error.TestError('phone station stdout != True (got: %s)',
                                  dut_out)

        self.restart_adb_server()
        self.cache_usb_dev_path()
        self.ensure_device_connectivity()
        self.get_gmscore_version()
        self.adb_over_tcp(persist_reboot=False)
        port = self.forward_device_port()

        # If IP address was not explicitly provided, get it from the labstation
        # host itself.
        ip_address = (self.phone_station_ip_addr
                      or self.get_phone_station_ip_address())
        return (ip_address, port)

    def close(self):
        """Clean up Android host and its phone station proxy host."""
        if self.closed:
            logging.debug('Android host %s already closed.', self.hostname)
            return
        try:
            if self.adb_tcp_mode:
                # In some rare cases, leave the Android device in adb over tcp
                # mode may break USB connection so we want to always reset adb
                # to usb mode before teardown.
                self.run_adb_command('usb', ignore_status=True)
            self.stop_adb_server()
            if self.socat_process_id:
                self.phone_station.run('kill -9 %d' % self.socat_process_id,
                                       ignore_status=True)
            if self.phone_station:
                self.phone_station.close()
            self.closed = True
        finally:
            super(AndroidHost, self).close()

    @staticmethod
    def get_android_arguments(args_dict):
        """Extract android args from `args_dict` and return the result.

        Recommended usage in control file:
            args_dict = utils.args_to_dict(args)
            android_args = hosts.Android.get_android_arguments(args_dict)
            host = hosts.create_host(machine, android_args=android_args)

        Args:
            args_dict: A dict of test args.

        Returns:
            An dict of android related args.
        """
        android_args = {
                key: args_dict[key]
                for key in android_constants.ALL_ANDROID_ATTRS
                if key in args_dict
        }
        for attr in android_constants.CRITICAL_ANDROID_ATTRS:
            if attr not in android_args or not android_args.get(attr):
                raise error.AutoservError("Critical attribute %s is missing"
                                          " from android_args." % attr)
        return android_args
