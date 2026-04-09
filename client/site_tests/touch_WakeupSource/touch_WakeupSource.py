# Lint as: python2, python3
# Copyright 2014 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import logging
import os

from autotest_lib.client.cros import ec
from autotest_lib.client.bin import utils
from autotest_lib.client.common_lib import error
from autotest_lib.client.common_lib.cros import cros_config
from autotest_lib.client.cros import touch_playback_test_base


class touch_WakeupSource(touch_playback_test_base.touch_playback_test_base):
    """Check that touchpad/touchscreen are set/not set as wake sources."""
    version = 1

    # Devices whose touchpads should not be a wake source.
    #
    # Note, starting with octopus platform, convertibles should enable touchpad
    # wake.  If you  wish to enable on previous devices, see furquan@ doc
    # go/cros-trackpad-wake and/or consult chromeos-platform-power@ for more
    # details.
    _NO_TOUCHPAD_WAKE = [
            'caroline', 'clapper', 'elm', 'glimmer', 'hana', 'kevin', 'kukui',
            'pyro', 'veyron_minnie', 'eve', 'nautilus', 'reef'
    ]
    _TOUCHPAD_WAKE_SET_BY_CROS_CONFIG = ['coral', 'nami']
    _TOUCHPAD_WAKE_MODELS = ['kakadu']

    # Devices with Synaptics touchpads that do not report wake source,
    # or reference platforms like Rambi which are broken but do not ship,
    # or devices like Cyan which don't report this way: crosbug.com/p/46019.
    _INVALID_TOUCHPADS = ['x86-alex', 'x86-alex_he', 'x86-zgb', 'x86-zgb_he',
                          'x86-mario', 'stout', 'rambi', 'cyan']
    _INVALID_TOUCHSCREENS = ['cyan', 'nocturne', 'sumo', 'ultima']

    def _touchpad_should_be_wake_source(self):
        if self._platform in self._TOUCHPAD_WAKE_MODELS:
            return True
        base_board = self._board.replace('-kernelnext', '')
        if base_board in self._NO_TOUCHPAD_WAKE:
            return False
        if (base_board in self._TOUCHPAD_WAKE_SET_BY_CROS_CONFIG
                    and cros_config.call_cros_config_get_output(
                            '/power touchpad-wakeup', utils.run) == '0'):
            return False
        return True

    def _find_wakeup_file(self, input_type):
        """Return path to wakeup file or None.

        If the file does not exist, check the parent bus for wakeup rules
        as well, as is the setup for some devices.

        @param input_type: e.g. 'touchpad' or 'mouse'. See parent class for
                all options.

        @raises: TestError if input_type lacks required information.

        """
        device_dir = self.player.devices[input_type].device_dir
        if not device_dir:
            raise error.TestError('No device directory for %s!' % input_type)

        filename = os.path.join(device_dir, 'power', 'wakeup')
        if os.path.isfile(filename):
            return filename

        logging.info('%s not found for %s', filename, input_type)

        # Look for wakeup file on parent bus instead.
        event = self.player.devices[input_type].node.split('/')[-1]

        bus_types = ["i2c", "usb"]
        for bus in bus_types:
            devices_dir = os.path.join('/', 'sys', 'bus', bus, 'devices')
            # USB devices have an additional interface directory layer.
            subdir_depth = '*/*' if bus == 'usb' else '*'
            for device_dir in os.listdir(devices_dir):
                event_search = os.path.join(devices_dir, device_dir,
                                            subdir_depth, 'input', 'input*',
                                            event)
                match_count = utils.run('ls %s 2>/dev/null | wc -l' %
                                        (event_search)).stdout.strip()

                if int(match_count) > 0:
                    parent = os.path.join(devices_dir, device_dir)
                    parent_wakeup = os.path.join(parent, 'power', 'wakeup')
                    # Check if the wakeup file exists in the loop, as there might be multiple parent directories for USB.
                    if os.path.isfile(parent_wakeup):
                        return parent_wakeup

        logging.info('Could not find parent bus for %s.', input_type)
        return None

    def _is_wake_source(self, input_type):
        """Return True if the given device is a wake source, else False.

        If the file does not exist, return False.

        @param input_type: e.g. 'touchpad' or 'mouse'. See parent class for
                all options.

        @raises: TestError if test cannot interpret the file contents.

        """
        filename = self._find_wakeup_file(input_type)
        if filename is None:
            return False

        result = utils.run('cat %s' % filename).stdout.strip()
        if result == 'enabled':
            logging.info('Found that %s is a wake source.', input_type)
            return True
        elif result == 'disabled':
            logging.info('Found that %s is not a wake source.', input_type)
            return False
        raise error.TestError('Wakeup file for %s said "%s".' %
                              (input_type, result))

    def _is_tablet_mode(self):
        """Examine whether the device is in tablet mode based on the powerd log"""
        mode_indicator = 'Configuring devices for mode'
        cmd = 'cat /var/log/power_manager/powerd.LATEST | grep \'{}\''.format(
                mode_indicator)
        try:
            out = [i for i in utils.run(cmd).stdout.split('\n') if i != '']
            if out == []:
                return False
            else:
                return "tablet" in out[-1]
        except error.CmdError:
            logging.info('Failed to search for mode indicator {}.'.format(
                    mode_indicator))
            return False

    def _turn_off_tablet_mode(self):
        """Turn off the tablet mode"""
        if ec.has_cros_ec():
            result = utils.run('ectool tabletmode off',
                               ignore_status=True).stdout.strip()
            if result.find("SUCCESS") == -1:
                logging.info('Failed to turn off tablet mode.')

            try:
                utils.poll_for_condition(
                        condition=lambda: self._is_tablet_mode() == False,
                        timeout=5,
                        sleep_interval=0.5,
                )
                logging.info("Tablet mode has been turned off")
            except error.TimeoutError:
                logging.info("Failed to disable Tablet Mode within 5 seconds")

    def _reset_tablet_mode(self):
        """Reset the tablet mode"""
        if ec.has_cros_ec():
            result = utils.run('ectool tabletmode reset',
                               ignore_status=True).stdout.strip()
            if result.find("SUCCESS") == -1:
                logging.info('Failed to reset tablet mode.')

    def run_once(self, source):
        """Entry point of this test."""

        # Check that touchpad is a wake source for all but the excepted boards.
        if source == 'touchpad':
            try:
                # Prevent failures caused by the touchpad being unavailable
                # while tablet mode is enabled.
                if self._is_tablet_mode():
                    self._turn_off_tablet_mode()

                if (self._has_touchpad
                            and self._platform not in self._INVALID_TOUCHPADS):
                    if self._touchpad_should_be_wake_source():
                        if not self._is_wake_source('touchpad'):
                            raise error.TestFail(
                                    'Touchpad is not a wake source!')
                    else:
                        if self._is_wake_source('touchpad'):
                            raise error.TestFail('Touchpad is a wake source!')
            finally:
                self._reset_tablet_mode()

        # Check that touchscreen is not a wake source (if present).
        # Devices without a touchpad should have touchscreen as wake source.
        if source == 'touchscreen':
            if (self._has_touchscreen and
                self._platform not in self._INVALID_TOUCHSCREENS):
                touchscreen_wake = self._is_wake_source('touchscreen')
                if self._has_touchpad and touchscreen_wake:
                    raise error.TestFail('Touchscreen is a wake source!')
                if not self._has_touchpad and not touchscreen_wake:
                    raise error.TestFail('Touchscreen is not a wake source!')
