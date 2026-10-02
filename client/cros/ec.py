# Lint as: python2, python3
# Copyright 2015 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import logging
import os
import re

from autotest_lib.client.bin import utils
from autotest_lib.client.common_lib import error

# en-US key matrix (from "kb membrane pin matrix.pdf")
KEYMATRIX = {'`': (3, 1), '1': (6, 1), '2': (6, 4), '3': (6, 2), '4': (6, 3),
             '5': (3, 3), '6': (3, 6), '7': (6, 6), '8': (6, 5), '9': (6, 9),
             '0': (6, 8), '-': (3, 8), '=': (0, 8), 'q': (7, 1), 'w': (7, 4),
             'e': (7, 2), 'r': (7, 3), 't': (2, 3), 'y': (2, 6), 'u': (7, 6),
             'i': (7, 5), 'o': (7, 9), 'p': (7, 8), '[': (2, 8), ']': (2, 5),
             '\\': (3, 11), 'a': (4, 1), 's': (4, 4), 'd': (4, 2), 'f': (4, 3),
             'g': (1, 3), 'h': (1, 6), 'j': (4, 6), 'k': (4, 5), 'l': (4, 9),
             ';': (4, 8), '\'': (1, 8), 'z': (5, 1), 'x': (5, 4), 'c': (5, 2),
             'v': (5, 3), 'b': (0, 3), 'n': (0, 6), 'm': (5, 6), ',': (5, 5),
             '.': (5, 9), '/': (5, 8), ' ': (5, 11), '<right>': (6, 12),
             '<alt_r>': (0, 10), '<down>': (6, 11), '<tab>': (2, 1),
             '<f10>': (0, 4), '<shift_r>': (7, 7), '<ctrl_r>': (4, 0),
             '<esc>': (1, 1), '<backspace>': (1, 11), '<f2>': (3, 2),
             '<alt_l>': (6, 10), '<ctrl_l>': (2, 0), '<f1>': (0, 2),
             '<search>': (0, 1), '<f3>': (2, 2), '<f4>': (1, 2), '<f5>': (3, 4),
             '<f6>': (2, 4), '<f7>': (1, 4), '<f8>': (2, 9), '<f9>': (1, 9),
             '<up>': (7, 11), '<shift_l>': (5, 7), '<enter>': (4, 11),
             '<left>': (7, 12)}


def has_cros_ec():
    """Check whether DUT has chromium ec or not.

    Returns:
        boolean whether device has ec or not.
    """
    return os.path.exists('/dev/cros_ec')


class ECError(Exception):
    """Base class for a failure when communicating with EC."""
    pass


class EC_Common(object):
    """Class for EC common.

    This incredibly brief base class is intended to encapsulate common elements
    across various CrOS MCUs (ec proper, USB-PD, Sensor Hub).  At the moment
    that includes only the use of ectool.
    """

    def __init__(self, target='cros_ec'):
        """Constructor.

        @param target: target name of ec to communicate with.
        """
        self._target = target

    def ec_command(self, cmd, **kwargs):
        """Executes ec command and returns results.

        @param cmd: string of command to execute.
        @param kwargs: optional params passed to utils.system_output

        @returns: string of results from ec command.
        """
        full_cmd = 'ectool --name=%s %s' % (self._target, cmd)
        logging.debug('Command: %s', full_cmd)
        result = utils.system_output(full_cmd, **kwargs)
        logging.debug('Result: %s', result)
        return result


class EC(EC_Common):
    """Class for CrOS embedded controller (EC)."""
    HELLO_RE = "EC says hello"
    GET_FANSPEED_RE = "Current fan RPM: ([0-9]*)"
    SET_FANSPEED_RE = "Fan target RPM set."
    TEMP_SENSOR_TEMP_RE = "([0-9]+) K"
    # <sensor idx>: <sensor type> <sensor name>
    TEMP_SENSOR_INFO_RE = "(\d+):\s+(\d+)\s+([a-zA-Z_0-9]+)"
    TOGGLE_AUTO_FAN_RE = "Automatic fan control is now on"
    # For battery, check we can see a non-zero capacity value.
    BATTERY_RE = "Design capacity:\s+[1-9]\d*\s+mAh"
    LIGHTBAR_RE = "^ 05\s+3f\s+3f$"

    def __init__(self):
        """Constructor."""
        super(EC, self).__init__()
        self._temperature_dict = None

    def hello(self, **kwargs):
        """Test EC hello command.

        @param kwargs: optional params passed to utils.system_output

        @returns True if success False otherwise.
        """
        response = self.ec_command('hello', **kwargs)
        return (re.search(self.HELLO_RE, response) is not None)

    def auto_fan_ctrl(self):
        """Turns auto fan ctrl on.

        @returns True if success False otherwise.
        """
        response = self.ec_command('autofanctrl')
        logging.info('Turned on auto fan control.')
        return (re.search(self.TOGGLE_AUTO_FAN_RE, response) is not None)

    def get_fanspeed(self):
        """Gets fanspeed.

        @raises error.TestError if regexp fails to match.

        @returns integer of fan speed RPM.
        """
        response = self.ec_command('pwmgetfanrpm')
        match = re.search(self.GET_FANSPEED_RE, response)
        if not match:
            raise error.TestError('Unable to read fan speed')

        rpm = int(match.group(1))
        logging.info('Fan speed: %d', rpm)
        return rpm

    def set_fanspeed(self, rpm):
        """Sets fan speed.

        @param rpm: integer of fan speed RPM to set

        @returns True if success False otherwise.
        """
        response = self.ec_command('pwmsetfanrpm %d' % rpm)
        logging.info('Set fan speed: %d', rpm)
        return (re.search(self.SET_FANSPEED_RE, response) is not None)

    def _get_temperature_dict(self):
        """Read EC temperature name and idx into a dict.

        @returns dict where key=<sensor name>, value =<sensor idx>
        """
        # The sensor (name, idx) mapping does not change.
        if self._temperature_dict:
            return self._temperature_dict

        temperature_dict = {}
        response = self.ec_command('tempsinfo all')
        for rline in response.split('\n'):
            match = re.search(self.TEMP_SENSOR_INFO_RE, rline)
            if match:
                temperature_dict[match.group(3)] = int(match.group(1))

        self._temperature_dict = temperature_dict
        return temperature_dict

    def get_temperature(self, idx=None, name=None):
        """Gets temperature from idx sensor.

        Reads temperature either directly if idx is provided or by discovering
        idx using name.

        @param idx:  integer of temp sensor to read.  Default=None
        @param name: string of temp sensor to read.  Default=None.
            For example: Battery, Ambient, Charger, DRAM, eMMC, Gyro

        @raises ECError if fails to find idx of name.
        @raises error.TestError if fails to read sensor or fails to identify
        sensor to read from idx & name param.

        @returns integer of temperature reading in degrees Kelvin.
        """
        if idx is None:
            temperature_dict = self._get_temperature_dict()
            if name in temperature_dict:
                idx = temperature_dict[name]
            else:
                raise ECError('Finding temp idx for name %s' % name)

        response = self.ec_command('temps %d' % idx)
        match = re.search(self.TEMP_SENSOR_TEMP_RE, response)
        if not match:
            raise error.TestError('Reading temperature idx %d' % idx)

        return int(match.group(1))

    def get_battery(self):
        """Get battery presence (design capacity found).

        @returns True if success False otherwise.
        """
        try:
            response = self.ec_command('battery')
        except error.CmdError:
            raise ECError('calling EC battery command')

        return (re.search(self.BATTERY_RE, response) is not None)

    def get_lightbar(self):
        """Test lightbar.

        @returns True if success False otherwise.
        """
        self.ec_command('lightbar on')
        self.ec_command('lightbar init')
        self.ec_command('lightbar 4 255 255 255')
        response = self.ec_command('lightbar')
        self.ec_command('lightbar off')
        return (re.search(self.LIGHTBAR_RE, response, re.MULTILINE) is not None)
