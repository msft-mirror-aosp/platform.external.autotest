import collections
import logging


PortId = collections.namedtuple('PortId', ['bus', 'port_number'])

# Mapping from bus ID and port number to the GPIO Index.
# We know of no way to detect this through tools, why the board
# specific setup is hard coded here.
_PORT_ID_TO_GPIO_INDEX_DICT = {
    'guado': {
        # On Guados, there are three gpios that control usb port power:
        PortId(bus=1, port_number=2): 218,  # Front left USB 2
        PortId(bus=2, port_number=1): 218,  # Front left USB 3
        PortId(bus=1, port_number=3): 219,  # Front right USB 2
        PortId(bus=2, port_number=2): 219,  # Front right USB 3
        # Back ports (same GPIO is used for both ports)
        PortId(bus=1, port_number=5): 209,  # Back upper USB 2
        PortId(bus=2, port_number=3): 209,  # Back upper USB 3
        PortId(bus=1, port_number=6): 209,  # Back lower USB 2
        PortId(bus=2, port_number=4): 209,  # Back lower USB 3
    },
    # On Fizz, there are in total 5 usb ports and per port usb power
    # is controlled by EC with user space command:
    # ectool gpioset USBx_ENABLE 0/1 (x from 1 to 5).
    'fizz': {
        # USB 2 bus.
        PortId(bus=1, port_number=3): 4,    # Front right USB 2
        PortId(bus=1, port_number=4): 5,    # Front left USB 2
        PortId(bus=1, port_number=5): 1,    # Back left USB 2
        PortId(bus=1, port_number=6): 2,    # Back middle USB 2
        PortId(bus=1, port_number=2): 3,    # Back right USB 2
        # USB 3 bus.
        PortId(bus=2, port_number=3): 4,    # Front right USB 3
        PortId(bus=2, port_number=4): 5,    # Front left USB 3
        PortId(bus=2, port_number=5): 1,    # Back left USB 3
        PortId(bus=2, port_number=6): 2,    # Back middle USB 3
        PortId(bus=2, port_number=2): 3,    # Back right USB 3
    }
}


def _get_gpio_index(board, port_id):
    return _PORT_ID_TO_GPIO_INDEX_DICT[board][port_id]


class UsbPortManager(object):
    """
    Manages USB ports.

    Can for example power cycle them.
    """
    def __init__(self, host):
        """
        Initializes with a host.

        @param host a Host object.
        """
        self._host = host

    def set_port_power(self, port_ids, power_on):
        """
        Turns on or off power to the USB port for peripheral devices.

        @param port_ids Iterable of PortId instances (i.e. bus, port_number
            tuples) to set power for.
        @param power_on If true, turns power on. If false, turns power off.
        """
        for port_id in port_ids:
            gpio_index = _get_gpio_index(self._get_board(), port_id)
            self._set_gpio_power(self._get_board(), gpio_index, power_on)

    def _get_board(self):
        # host.get_board() adds 'board: ' in front of the board name
        return self._host.get_board().split(':')[1].strip()

    def _set_gpio_power_guado(self, gpio_index, power_on):
        """
        Turns on or off the power for a specific GPIO on board Guado.

        @param gpio_idx The index of the gpio to set the power for.
        @param power_on If True, powers on the GPIO. If False, powers it off.
        """
        gpio_path = '/sys/class/gpio/gpio{}'.format(gpio_index)
        did_export = False
        if not self._host.path_exists(gpio_path):
            did_export = True
            self._run('echo {} > /sys/class/gpio/export'.format(
                    gpio_index))
        try:
            self._run('echo out > {}/direction'.format(gpio_path))
            value_string = '1' if power_on else '0'
            self._run('echo {} > {}/value'.format(
                    value_string, gpio_path))
        finally:
            if did_export:
                self._run('echo {} > /sys/class/gpio/unexport'.format(
                        gpio_index))

    def _set_gpio_power_fizz(self, gpio_idx, power_on):
        """
        Turns on or off the power for a specific GPIO on board Fizz.

        @param gpio_idx The index of the gpio to set the power for.
        @param power_on If True, powers on the GPIO. If False, powers it off.
        """
        value_string = '1' if power_on else '0'
        cmd = 'ectool gpioset USB{}_ENABLE {}'.format(gpio_idx,
              value_string)
        self._run(cmd)

    def _set_gpio_power(self, board, gpio_index, power_on):
        """
        Turns on or off the power for a specific GPIO.

        @param board Board type. Currently support: Guado, Fizz.
        @param gpio_idx The index of the gpio to set the power for.
        @param power_on If True, powers on the GPIO. If False, powers it off.
        """
        if board == 'guado':
            self._set_gpio_power_guado(gpio_index, power_on)
        elif board == 'fizz':
            self._set_gpio_power_fizz(gpio_index, power_on)
        else:
            raise ValueError('Unsupported board type {}.'.format(board))

    def _run(self, command):
        logging.debug('Running: "%s"', command)
        res = self._host.run(command)
        logging.debug('Result: "%s"', res)

