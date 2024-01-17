#!/usr/bin/python3

# Copyright 2024 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Serial port driver and light control.

  This code was developed to control peripheral devices following DMX protocol
through serial port.
  The application is for AWB automation test only. Not fully DMX protocol, nor
fully serial driver methods were supported.
  Each light is configured by 8 parameters defined as:
      [0]: Intensity
      [1]: CCT
      [2]: Green saturation
      [3]: Fade
      [4]: Red
      [5]: Green
      [6]: Blue
      [7]: White
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import sys
import time
import numpy as np
from typing import List
import pathlib

import serial

_CONFIG_PER_LIGHT = 8
# Each configuration contains 1 bytes (8 bit mode) or 2 bytes for (16 bit mode)
_BYTE_PER_CONFIG = 1
# DMX buffer size.
_DMX_DATA_BUFFER_SIZE = 513
# A default serial port name, changes from PC to PC

_DEFAULT_SERIAL_PORT_NAME = (
        '/dev/serial/by-id/usb-FTDI_FT245R_USB_FIFO_A70EIKFV-if00-port0')
_DEFAULT_SERIAL_PORT_PATTERNS = [
        "*FT245R_USB_FIFO*",
]
_MIN_LIGHT_INTERVAL = 0.016
_MIN_NAP_TIME = 0.005


class SerialPortException(Exception):
    """Exception class for SerialPort"""


class LightControlException(Exception):
    """Exception class for LightControl"""


class SerialPortDriver:
    """Serial port driver.

    This class provides control to serial port in PC. The port name could be
        found in /dev/serial/, each PC might have different name.
    Serial port control requires settings of baud rate, start, stop...etc.
    """

    SERIAL_PORT_FS_ROOT = pathlib.Path("/") / "dev" / "serial" / "by-id"

    def __init__(self,
                 port_name: str = _DEFAULT_SERIAL_PORT_NAME,
                 port_data_size: int = _DMX_DATA_BUFFER_SIZE):
        """Initialize serial port and set serial protocols.

        Open serial port in general definition for AWB test purpose only, not to
            full fill serial driver protocol. Some of the protocols not used for
            our purpose are hard coded, ex: baud rate...etc.

        Args:
            port_name: the serial port name listed at /dev/serial/
            port_data_size: the size of the data in byte

        Raises:
            SerialPortException: Can't open serial port.
        """
        self.serial_port_name = port_name
        self.baud_rate = 115200
        self.data_size = port_data_size
        self.time_out = 1
        self.start = 0x7E
        self.stop = 0xE7
        self.tx = 0x06
        self.rx = 0x08
        # TX start package
        self.tx_start_package = np.array([
                self.start, self.tx, self.data_size & 0xFF,
                (self.data_size >> 8)
                & 0xFF
        ],
                                         dtype=np.uint8)
        # Stop package
        self.stop_package = np.array([self.stop], dtype=np.uint8)
        # Create data buffer.
        self.data_buffer = np.zeros(self.data_size, dtype=np.uint8)
        try:
            # Open serial port.
            self.serial_ctrl = serial.Serial(str(self.serial_port_name),
                                             baudrate=self.baud_rate,
                                             timeout=self.time_out)
            self.send_data()
        except serial.serialutil.SerialException as e:
            error_msg = f'Can not open serial port {port_name}:{repr(e)} '
            raise SerialPortException(error_msg)

    def send_data(self):
        """Send data through serial port.

        self.data_buffer will be sent through serial port.

        Returns:
            False is writing sequence failed.
        """
        stream = np.append(self.tx_start_package, self.data_buffer)
        stream = np.append(stream, self.stop_package)
        try:
            self.serial_ctrl.write(stream)
        except serial.serialutil.SerialException as e:
            error_msg = 'Serial port error: {}'.format(repr(e))
            raise SerialPortException(error_msg)

    def config_light(self, light_id: int, data: np.array):
        """Set a specific light's data into port buffer.

        Args:
            light_id: 0, 1, 2... corresponding to the physical lights connected
                in the chain.
            data: the configurations for this light.

        Raises:
            LightControlException: Exceed light number of DMX protocol.
        """
        # TODO(chengshengh): The control size per light is not always the same.
        size_per_light = _BYTE_PER_CONFIG * _CONFIG_PER_LIGHT
        if (light_id + 1) * size_per_light + 1 > _DMX_DATA_BUFFER_SIZE:
            error_msg = (f'Light {light_id} exceed DMX size '
                         f'{_DMX_DATA_BUFFER_SIZE}')
            raise LightControlException(error_msg)
        # Note: data_buffer[0] was reserved, so light data starts from byte 1.
        self.data_buffer[light_id * size_per_light +
                         1:(light_id + 1) * size_per_light + 1:] = data[:]

    def turn_off_all_arri_lights(self):
        """Turn OFF all lights in the link."""
        self.data_buffer[:] = 0
        self.send_data()

    @classmethod
    def list_port_name(cls, glob_pattern: str = "*"):
        """Find ports under serial that matches the pattern.

        By default returns all files.

        Args:
            glob_pattern: The pattern used to match. Default as "*"
        """
        return list(cls.SERIAL_PORT_FS_ROOT.glob(glob_pattern))


class LightControl:
    """Main light control class.

    Currently, only support Arri light.
    """

    def __init__(self, port_name=''):
        """Initialize.

        Args:
            port_name: A string of serial port name.

        Raises:
            LightControlException: Failed on opening serial port.
        """
        # Start a serial port for DMX protocol.
        try:
            # Open serial port.
            self.serial_port = SerialPortDriver(port_name)
            # Send all zeros, turning off all connected lights.
            self.serial_port.send_data()
        except SerialPortException as e:
            error_msg = f'Fail to init light: {repr(e)}'
            raise LightControlException(error_msg)

        self.light_thread_running = False

    def direct_arri_light_intensity_cct(self, light_id, intensity, cct):
        """Set arri light's intensity and CCT.

        Args:
            light_id: Integer light ID in the chain.
            intensity: An integer light intensity code to set the light.
            cct: An integer color temperature code to set the light.

        Raises:
            LightControlException: Fail to set light.
        """
        data_buffer = np.zeros(_BYTE_PER_CONFIG * _CONFIG_PER_LIGHT,
                               dtype=np.uint8)
        if _BYTE_PER_CONFIG == 1:  # 8 bit mode
            data_buffer[0] = intensity
            data_buffer[1] = cct
        else:  # 16 bit mode
            intensity *= 256
            cct *= 256
            data_buffer[0 * _BYTE_PER_CONFIG + 1] = intensity & 0xFF
            data_buffer[0 * _BYTE_PER_CONFIG] = (intensity >> 8) & 0xFF
            data_buffer[1 * _BYTE_PER_CONFIG + 1] = cct & 0xFF
            data_buffer[1 * _BYTE_PER_CONFIG] = (cct >> 8) & 0xFF

        # Config the light
        self.serial_port.config_light(light_id, data_buffer)

        # Send the data out
        try:
            self.serial_port.send_data()
        except SerialPortException as e:
            raise LightControlException(repr(e))

    def config_arri_light_intensity_cct(self, light_id, intensity, cct):
        """Set arri light's intensity and CCT.

        Args:
            light_id: Integer light ID in the chain.
            intensity: An integer light intensity code to set the light.
            cct: An integer color temperature code to set the light.

        Raises:
            LightControlException: Fail to set light.
        """
        data_buffer = np.zeros(_BYTE_PER_CONFIG * _CONFIG_PER_LIGHT,
                               dtype=np.uint8)
        if _BYTE_PER_CONFIG == 1:  # 8 bit mode
            data_buffer[0] = intensity
            data_buffer[1] = cct
        else:  # 16 bit mode
            data_buffer[0 * _BYTE_PER_CONFIG] = intensity & 0xFF
            data_buffer[0 * _BYTE_PER_CONFIG + 1] = (intensity >> 8) & 0xFF
            data_buffer[1 * _BYTE_PER_CONFIG] = cct & 0xFF
            data_buffer[1 * _BYTE_PER_CONFIG + 1] = (cct >> 8) & 0xFF
        # Config the light
        self.serial_port.config_light(light_id, data_buffer)

    def write_config_to_arri_light(self):
        """Write configuration to arri light."""
        self.serial_port.send_data()

    def turn_off_all_arri_lights(self):
        """Turn OFF all lights in the link."""
        self.serial_port.turn_off_all_arri_lights()

    def intensity_sweep(self, light_id, intensity_points, cct, delay_time):
        """Light sweep evaluation.

        Args:
            light_id: An integer id of the light to be set.
            intensity_points: An integer array of intensity codes to set the
                light.
            cct: A cct code to be set the light.
            delay_time: delay this amount of seconds for each lighting
                condition.

        Raises:
            LightControlException: Intensity setting error.
        """
        for intensity in intensity_points:
            self.direct_arri_light_intensity_cct(light_id, intensity, cct)
            time.sleep(delay_time)

    def cct_sweep(self, light_id, intensity, cct_points, delay_time):
        """Light sweep evaluation.

        Args:
            light_id: An integer id of the light to be set.
            intensity: An integer.
            cct_points: A cct array.
            delay_time: delay this amount of seconds for each lighting
                condition.

        Raises:
            LightControlException: Intensity setting error.
        """
        for cct in cct_points:
            self.direct_arri_light_intensity_cct(light_id, intensity, cct)
            time.sleep(delay_time)

    def light_jump(self, light_id, intensity_points, cct_points, delay_time):
        """Light jump evaluation.

        Args:
            light_id: An integer id of the light to be set.
            intensity_points: An integer array of intensity codes to set the
                light.
            cct_points: A array of cct.
            delay_time: delay this amount of seconds for each lighting
                condition.

        Raises:
            LightControlException: Intensity setting error.
        """
        for i, intensity in enumerate(intensity_points):
            intensity = intensity_points[i]
            cct = cct_points[i]
            self.direct_arri_light_intensity_cct(light_id, intensity, cct)
            time.sleep(delay_time)


def get_port_name(patterns: List[str] = ...,
                  default_port_name: pathlib.Path = _DEFAULT_SERIAL_PORT_NAME):
    """Given a list of pattern name for serial port, return the first result

    Args:
        patterns: a list of glob patterns for the serial port name.
        default_port_name: the default value when no pattern are found.
    """
    if patterns is ...:
        patterns = _DEFAULT_SERIAL_PORT_PATTERNS

    available_ports: List[str] = []
    for pattern in patterns:
        available_ports += SerialPortDriver.list_port_name(pattern)

    return available_ports[0] if available_ports else default_port_name


def cmd_direct_light_control(argv):
    """Direct set intensity and cct to specific channel.

    Args:
        argv: [0] = channel, [1] = intensity, [2] = cct.
    """
    light_id = int(argv[0])
    intensity = int(argv[1])
    cct = int(argv[2])

    print(f'Set id={light_id}, intensity={intensity}, cct={cct}')

    port_name = get_port_name()
    light_obj = LightControl(port_name)
    light_obj.direct_arri_light_intensity_cct(light_id, intensity, cct)


def cmd_multi_light_control(argv):
    """Set intensity and cct to specific channel.

    Args:
        argv: [0] = channel, bit ORed, one bit per light , [1] = intensity,
          [2] = cct.
    """
    lights = int(argv[0])
    intensity = int(argv[1])
    cct = int(argv[2])

    print(f'Set id={lights}, intensity={intensity}, cct={cct}')

    port_name = get_port_name()
    light_obj = LightControl(port_name)
    light_id = 0
    while lights != 0:
        if (lights & 1) != 0:
            light_obj.config_arri_light_intensity_cct(light_id, intensity, cct)
        lights >>= 1
        light_id += 1

    light_obj.write_config_to_arri_light()


def cmd_sweep_ae(argv):
    """Direct set intensity and cct to specific channel.

    Args:
        argv: [0] = channel, [1] = intensity array, [2] = cct, [3] = interval.
    """
    light_id = int(argv[0])
    intensity = [int(i) for i in argv[1].split(',')
                 ]  # a string of values splitted with ','
    cct = int(argv[2])
    interval = float(argv[3])  # time in sec.

    print(f'Set id={light_id}, intensity={intensity}, cct={cct}, '
          f'interval={interval}')

    port_name = get_port_name()
    light_obj = LightControl(port_name)
    light_obj.intensity_sweep(light_id, intensity, cct, interval)


def cmd_light_jump(argv):
    """Set intensity and cct to specific channel.

    Args:
        argv: [0] = channel, bit ORed, one bit per light , [1] = interleaved(
            intensity,cct) [2] = interval (sec).

    Useful test settings:
    [2 lights, change @ 3000K, lux:10,18,40,80,200,400,1000,1600, interval 6 sec]
        jump 3 '0,0, 10,1, 20,5, 40,10, 60,10, 95,10, 130,10, 180,10, 220,10' 6
    [2 lights, change @ 6500K, lux:10,18,40,80,200,400,1000,1600, interval 6 sec]
        jump 3 '0,0,10,150,20,175,40,205,60,210,95,188,130,190,180,185,220,170' 6
    [2 lights, change @ 400Lux, CCT 2800 3000 3500 4000 4500 5000 5500 6000 6500 7000 6 sec]
        jump 3 '0,0,130,1,130,10,130,30,130,60,130,80,130,110,130,135,130,165,130,195,130,230' 6
    [2 lights, (lux,K): (18,3000),(150,3000), (80,6500),(2000, 6500),(80, 3000)
        interval 6 sec] jump 3 '0,0,20,5, 80,10, 60,210, 250,170, 60,10' 6
    """
    light_ids = int(argv[0])
    configs = [int(i) for i in argv[1].split(',')]
    interval = float(argv[2])

    port_name = get_port_name()
    light_obj = LightControl(port_name)
    for i in range(0, len(configs), 2):
        lights = light_ids
        intensity = configs[i]
        cct = configs[i + 1]
        print(f'intensity={intensity}, cct={cct}')
        light_id = 0
        while lights != 0:
            if (lights & 1) != 0:
                light_obj.config_arri_light_intensity_cct(
                        light_id, intensity, cct)
            lights >>= 1
            light_id += 1
        light_obj.write_config_to_arri_light()
        time.sleep(interval)


_COMMANDS = {
        'direct': (3, 3, 'direct id intensity cct ', cmd_direct_light_control),
        'multi':
        (3, 3, 'multi bit_id intensity cct ', cmd_multi_light_control),
        'sweep_ae': (4, 4, 'sweep_ae id intensity cct time', cmd_sweep_ae),
        'jump': (3, 3, 'jump bit_id configs time', cmd_light_jump),
}


def dispatch(argv: List[str], commands):
    """Dispatch functions.

    Args:
        argv: argv from sys.argv to main.
        commands: dictionary of
            {'command': (min param number, max param number, help,
                service_function)}
    """
    if len(argv) <= 1 or argv[1] not in commands:
        # Error: Command not found.
        print('=======================================')
        print('Command not found. Availables are:')
        for key, [_, _, param_help, _] in commands.items():
            print(f'   {key}: {param_help}')
        print('=======================================')

        port_name = get_port_name(default_port_name=None)
        if port_name is None:
            print('WARNING: No serial port found.')
        else:
            print(f'Found serial port name: {port_name}')
        return

    # 0 and 1 is the application and command, parameters starts at index 2
    parameter_num = len(argv) - 2
    command = argv[1]
    [min_num_param, max_num_param, param_help,
     command_func] = commands[command]
    if not min_num_param <= parameter_num <= max_num_param:
        # Error.
        print(f'Error: {param_help}')
        return

    # Call command.
    command_func(argv[2:])


def main(argv):
    """Main entry point

    Args:
        argv: argv from command line input.
    """
    dispatch(argv, _COMMANDS)


if __name__ == '__main__':
    print(f'Running at {sys.platform} OS')
    main(sys.argv)
