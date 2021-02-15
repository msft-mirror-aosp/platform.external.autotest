#!/usr/bin/env python2
# Copyright 2020 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import print_function
from __future__ import absolute_import
from __future__ import unicode_literals
from __future__ import division

import os
import copy
import json
import string
import base64
import logging

import common
from autotest_lib.client.common_lib import hosts
from autotest_lib.server.cros.servo.topology import topology_constants as stc


class ServoTopologyError(Exception):
    """
    Generic Exception for failures from ServoTopology object.
    """
    pass


class MissingServoError(ServoTopologyError):
    """
    Exception to throw when child servo type is missing.
    """

    def __init__(self, message, servo_type):
        self._servo_type = servo_type
        self.message = message

    def __str__(self):
        return repr(self.message)


class ServoTopology(object):
    """Class to read, generate and validate servo topology in the lab.

    The class support detection of servo listed in VID_PID_SERVO_TYPES.
    To save servo topology to host-info date passed two steps:
       - convert to the json
       - encode to base64
    """
    # Command to get usb-path to device
    SERVOD_TOOL_USB_PATH = 'servodtool device -s %s usb-path'

    def __init__(self, servo_host):
        self._host = servo_host
        self.reset()

    def read(self, host_info):
        """Reading servo-topology info."""
        logging.info('Reading servo topology info...')
        self.reset()
        if not host_info:
            logging.info('The host_info not provided. Skip reading.')
            return
        b64_val = host_info.get_label_value(stc.SERVO_TOPOLOGY_LABEL_PREFIX)
        self._topology = _parse_string_as_topology(b64_val)
        logging.debug('Loaded servo topology: %s', self._topology)
        if self._topology:
            logging.info('Servo topology loaded successfully.')

    def save(self, host_info_store):
        """Saving servo-topology info."""
        if self.is_empty():
            logging.info('Topology is empty. Skip saving.')
            return
        if not host_info_store:
            logging.info('The host_info_store not provided. Skip saving.')
            return
        logging.info('Saving servo topology info...')
        data = _convert_topology_to_string(self._topology)
        if not data:
            logging.info('Servo topology fail to save data.'
                         ' Please file a bug.')
            return
        host_info = host_info_store.get()
        prev_value = host_info.get_label_value(stc.SERVO_TOPOLOGY_LABEL_PREFIX)
        if prev_value and prev_value == data:
            logging.info('Servo topology was not changed. Skip saving.')
            return
        logging.debug('Previous saved topology: %s', prev_value)
        host_info.set_version_label(stc.SERVO_TOPOLOGY_LABEL_PREFIX, data)
        host_info_store.commit(host_info)
        logging.info('Servo topology saved successfully.')

    def reset(self):
        """Reset topology to the initialize state.

        All cash will be reset to empty state.
        """
        self._topology = None

    def generate(self):
        """Read servo data and create topology."""
        self.reset()
        try:
            self._topology = self._generate()
        except Exception as e:
            logging.debug('(Not critical) %s', e)
            logging.info('Fail to generate servo-topology')
        if not self.is_empty():
            logging.info('Servo topology successfully generated.')

    def is_empty(self):
        """If topology data was initialized."""
        return not bool(self._topology)

    def validate(self, raise_error=False, dual_set=False, compare=False):
        """Validate topology against expected topology.

        Validation against:
        - set-up expectation: min one child or 2 for DUAL_V4
        - last saved topology: check if any device missed

        Update topology cache if validation passed successfully.

        @params raise_error: raise error if validate did not pass otherwise
                             return False.
        @params dual_set:    Check if servo expect DUAL_V4 setup.
        @params compare:     Validate against saved topology.
        """
        new_st = self._generate()
        if not new_st or not new_st.get(stc.ST_DEVICE_MAIN):
            message = 'Main device is not detected'
            return self._process_error(message, raise_error)
        children = new_st.get(stc.ST_DEVICE_CHILDREN)
        # basic setup has to have minimum one child.
        if not children or len(children) < 1:
            message = 'Each setup has at least one child'
            return self._process_error(message, raise_error)
        children_types = [c.get(stc.ST_DEVICE_TYPE) for c in children]
        # DUAL_V4 setup has to have cr50 and one more child.
        if dual_set:
            if stc.ST_CR50_TYPE not in children_types:
                return self._missing_servo_error(stc.ST_CR50_TYPE, raise_error)
            if len(children) < 2:
                message = 'Expected two children but have only one'
                return self._process_error(message, raise_error)
        if compare and not self.is_empty():
            main_device = new_st.get(stc.ST_DEVICE_MAIN)
            t = self._topology
            old_main = t.get(stc.ST_DEVICE_MAIN)
            old_children = t.get(stc.ST_DEVICE_CHILDREN)
            if not all([
                    old_children,
                    old_main,
                    old_main.get(stc.ST_DEVICE_HUB_PORT),
            ]):
                # Old data is invalid for comparasing
                return True
            if not self._equal_item(old_main, main_device):
                message = 'Main servo was changed'
                return self._process_error(message, raise_error)
            for child in old_children:
                old_type = child.get(stc.ST_DEVICE_TYPE)
                if old_type not in children_types:
                    return self._missing_servo_error(old_type, raise_error)
            if len(children) < len(old_children):
                message = 'Some child is missed'
                return self._process_error(message, raise_error)
        logging.info('Servo topology successfully verified.')
        self._topology = new_st
        return True

    def is_servo_serial_provided(self):
        """Verify that core servo serial is provided."""
        core_servo_serial = self._host.servo_serial
        if not core_servo_serial:
            logging.info('Core servo serial is not provided.')
            return False
        logging.debug('Core servo serial: %s', core_servo_serial)
        return True

    def _process_error(self, message, raise_error):
        if not raise_error:
            logging.info('Validate servo topology failed with: %s', message)
            return False
        raise ServoTopologyError(message)

    def _missing_servo_error(self, servo_type, raise_error):
        message = 'Missed servo: %s!' % servo_type
        if not raise_error:
            logging.info('Validate servo topology failed with: %s', message)
            return False
        raise MissingServoError(message, servo_type)

    def _equal_item(self, old, new):
        """Servo was replugged to another port"""
        for field in stc.SERVO_TOPOLOGY_ITEM_COMPARE_FIELDS:
            if old.get(field) != new.get(field):
                return False
        return True

    def _generate(self):
        """Generate and return topology structure.

        Read and generate topology structure with out update the state.
        """
        logging.debug('Trying generate a servo-topology')
        if not self.is_servo_serial_provided():
            return
        core_servo_serial = self._host.servo_serial
        main_device = None
        children = []
        devices = self.get_list_of_devices()
        for device in devices:
            if not device.is_good():
                logging.info('Skip %s as missing some data', device)
                continue
            if device.get_serial_number() == core_servo_serial:
                main_device = device.get_topology_item()
            else:
                children.append(device.get_topology_item())
        if not main_device:
            logging.debug('Core device missed some data')
            return None
        topology = {
                stc.ST_DEVICE_MAIN: main_device,
                stc.ST_DEVICE_CHILDREN: children
        }
        logging.debug('Servo topology: %s', topology)
        return topology

    def _get_servo_hub_path(self, servo_serial):
        """Get path to the servo hub.

        The core servo is connected directly to the servo-hub. To find other
        servos connected to the hub we need find the path to the servo-hub.
        The servod-tool always return direct path to the servo, like:
            /sys/bus/usb/devices/1-3.2.1
            base path:  /sys/bus/usb/devices/
            core-servo:  1-3.2.1
        the alternative path is '/sys/bus/usb/devices/1-3.2/1-3.2.1/'
        where '1-3.2' is path to servo-hub. To extract path to servo-hub
        logic parse parse and remove last digit of the port where core servo
        connected to the servo-hub.
            base path:  /sys/bus/usb/devices/
            servo-hub:  1-3.2
            core-servo: .1
        After we will join only base path with servo-hub.

        @params servo_serial    Serial number of the servo connected to hub
        @returns: A string representation of fs-path to servo-hub device
        """
        logging.debug('Try to find a hub-path for servo:%s', servo_serial)
        cmd_hub = self.SERVOD_TOOL_USB_PATH % servo_serial
        servo_path = self._read_line(cmd_hub)
        logging.debug('Servo %s path: %s', servo_serial, servo_path)
        if not servo_path or len(servo_path) < 3:
            logging.info('Servo not detected.')
            return None
        base_path = os.path.dirname(servo_path)
        core_servo_tail = os.path.basename(servo_path)
        # Removing last port as
        servo_hub_tail = string.join(core_servo_tail.split('.')[:-1], '.')
        return os.path.join(base_path, servo_hub_tail)

    def get_list_of_devices(self):
        """Generate list of devices with serials.

        Logic based on detecting all device enumerated under servo-hub device.

        @returns: Collection of detected device connected to the servo-hub.
        """
        logging.debug('Trying generate device-a servo-topology')
        if not self.is_servo_serial_provided():
            return []
        # Find the path to the servo-hub folder.
        hub_path = self._get_servo_hub_path(self._host.servo_serial)
        if not hub_path:
            return []
        logging.debug('Servo hub path: %s', hub_path)

        # Find all serial filed of devices under servo-hub. Each device
        # has to have serial number.
        devices_cmd = 'find %s/* -name serial' % hub_path
        devices = self._read_multilines(devices_cmd)
        children = []
        for device in devices:
            logging.debug('Child device %s', device)
            device_dir = os.path.dirname(device)
            child = self._get_device(device_dir)
            if not child:
                logging.debug('Child missed some data.')
                continue
            children.append(child)
        logging.debug('Detected devices: %s', len(children))
        return children

    def _get_vid_pid(self, path):
        """Read VID and PID of the device.

        @params path    Absolute path to the device in FS.
        @returns: A string representation VID:PID of device.
        """
        vid = self._read_file(path, 'idVendor')
        pid = self._read_file(path, 'idProduct')
        if not vid or not pid:
            return None
        vid_pid = '%s:%s' % (vid, pid)
        logging.debug("VID/PID of device device: '%s'", vid_pid)
        return vid_pid

    def _get_device(self, path):
        """Create device representation.

        @params path:   Absolute path to the device in FS.
        @returns: ConnectedServo if VID/PID present.
        """
        vid_pid = self._get_vid_pid(path)
        if not vid_pid:
            return None
        serial = self._read_file(path, 'serial')
        product = self._read_file(path, 'product')
        hub_path = self._read_file(path, 'devpath')
        configuration = self._read_file(path, 'configuration')
        servo_type = stc.VID_PID_SERVO_TYPES.get(vid_pid)
        if not servo_type:
            return None
        return ConnectedServo(device_product=product,
                              device_serial=serial,
                              device_type=servo_type,
                              device_vid_pid=vid_pid,
                              device_hub_path=hub_path,
                              device_version=configuration)

    def _read_file(self, path, file_name):
        """Read context of the file and return result as one line.

        If execution finished with error result will be empty string.

        @params path:       Path to the folder where file located.
        @params file_name:  The file name to read.
        """
        if not path or not file_name:
            return ''
        f = os.path.join(path, file_name)
        return self._read_line('cat %s' % f)

    def _read_line(self, command):
        """Execute terminal command and return result as one line.

        If execution finished with error result will be empty string.

        @params command:    String to execute.
        """
        r = self._host.run(command, ignore_status=True, timeout=30)
        if r.exit_status == 0:
            return r.stdout.strip()
        return ''

    def _read_multilines(self, command):
        """Execute terminal command and return result as multi-line.

        If execution finished with error result will be an empty array.

        @params command:    String to execute.
        """
        r = self._host.run(command, ignore_status=True, timeout=30)
        if r.exit_status == 0:
            return r.stdout.splitlines()
        return []


class ConnectedServo(object):
    """Class to hold info about connected detected."""

    def __init__(self,
                 device_product=None,
                 device_serial=None,
                 device_type=None,
                 device_vid_pid=None,
                 device_hub_path=None,
                 device_version=None):
        self._product = device_product
        self._serial = device_serial
        self._type = device_type
        self._vid_pid = device_vid_pid
        self._hub_path = device_hub_path
        self._version = device_version

    def get_topology_item(self):
        """Extract as topology item."""
        return {
                stc.ST_DEVICE_SERIAL: self._serial,
                stc.ST_DEVICE_TYPE: self._type,
                stc.ST_DEVICE_PRODUCT: self._product,
                stc.ST_DEVICE_HUB_PORT: self._hub_path
        }

    def is_good(self):
        """Check if minimal data for topology item is present."""
        return self._serial and self._type and self._hub_path

    def get_type(self):
        """Servo type."""
        return self._type

    def get_serial_number(self):
        """Servo serial number."""
        return self._serial

    def get_version(self):
        """Get servo version."""
        return self._version

    def __str__(self):
        return ("Device %s:%s (%s, %s) version: %s" %
                (self._type, self._serial, self._vid_pid, self._hub_path,
                 self._version))


def _convert_topology_to_string(topology):
    """Convert topology to the string respresentation.

    Convert topology to json and encode by Base64 for host-info file.

    @params topology: Servo topology data
    @returns: topology representation in Base64 string
    """
    if not topology:
        return ''
    try:
        # generate json similar to golang to avoid extra updates
        json_string = json.dumps(topology, separators=(',', ':'))
        logging.debug('Servo topology (json): %s', json_string)
    except Exception as e:
        logging.debug('(Not critical) %s', e)
        logging.info('Failed to convert topology to json')
        return ''
    try:
        # recommended to convert to the bytes for python 3
        b64_string = base64.b64encode(json_string.encode("utf-8"))
        logging.debug('Servo topology (b64): %s', b64_string)
        return b64_string
    except Exception as e:
        logging.debug('(Not critical) %s', e)
        logging.info('Failed to convert topology to base64')
    return ''


def _parse_string_as_topology(src):
    """Parse and load servo topology from string.

    Decode Base64 and load as json of servo-topology data.

    @params src: topology representation in Base64 string
    @returns: servo topology data
    """
    if not src:
        logging.debug('Servo topology data not present in host-info.')
        return None
    try:
        json_string = base64.b64decode(src)
        logging.debug('Servo topology (json) from host-info: %s', json_string)
        return json.loads(json_string)
    except Exception as e:
        logging.debug('(Not critical) %s', e)
        logging.info('Fail to read servo-topology from host-info.')
    return None
