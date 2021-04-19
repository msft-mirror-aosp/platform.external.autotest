#!/usr/bin/env python2
# Copyright 2020 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import os
import logging

import common
from autotest_lib.client.common_lib import utils as client_utils
from autotest_lib.server.cros.servo.topology import topology_constants

try:
    from autotest_lib.utils.frozen_chromite.lib import metrics
except ImportError:
    metrics = client_utils.metrics_mock


class ServoFwVersionMissedError(Exception):
    """Raised when Available version is not detected."""


class _BaseUpdateServoFw(object):
    """Base class to update firmware on servo"""

    # Commands to kill active servo_updater fail with timeout
    ACTIVE_UPDATER_CORE = 'ps aux | grep -ie [s]ervo_updater |grep "%s" '
    ACTIVE_UPDATER_PRINT = ACTIVE_UPDATER_CORE + "| awk '{print $2}' "
    ACTIVE_UPDATER_KILL = ACTIVE_UPDATER_PRINT + "| xargs kill -9 "

    # Command to get PATH to the latest available firmware on the host
    # param 1: servo board (servo_v4|servo_micro)
    LATEST_VERSION_FW = 'realpath /usr/share/servo_updater/firmware/%s.bin'

    # Command to get servo firmware version for requested board and channel.
    LATEST_VERSION_CMD = 'servo_updater -p -b "%s" -c %s | grep firmware'

    # Default firmware channel.
    DEFAULT_FW_CHANNEL = 'stable'

    def __init__(self, servo_host, device):
        """Init servo-updater instance.

        @params servo_host: ServoHost instance to run terminal commands
        @params device:     ConnectedServo instance provided servo info
        """
        self._host = servo_host
        self._device = device
        # TODO(otabek@) remove when lab will use labstation R92
        self._updater_accept_channel = False

    def need_update(self, ignore_version=False, channel=None):
        """Verify that servo_update is required.

        @params ignore_version: Do not check the version on the device.
        @params channel:        Channel for servo firmware. Supported from
                                version R90. Possible values: stable, prev,
                                dev, alpha.

        @returns: True if update required, False if not
        """
        # Check if channel passed. If not then set stable as default.
        if not channel:
            channel = self.DEFAULT_FW_CHANNEL
        if not self._host:
            return False
        elif not self.get_serial_number():
            return False
        elif not self._host.is_labstation():
            return False
        elif not self._custom_verifier():
            return False
        elif not ignore_version:
            return self._is_outdated_version(channel=channel)
        return True

    def update(self, force_update=False, ignore_version=False, channel=None):
        """Update firmware on the servo.

        Steps:
        1) Verify servo is not updated by checking the versions.
        2) Try to get serial number for the servo.
        3) Updating firmware.

        @params force_update:   Run updater with force option.
        @params ignore_version: Do not check the version on the device.
        @params channel:        Channel for servo firmware. Supported from
                                version R90. Possible values: stable, prev,
                                dev, alpha.
        """
        # Check if channel passed. If not then set stable as default.
        if not channel:
            channel = self.DEFAULT_FW_CHANNEL
        if not self.need_update(ignore_version, channel=channel):
            logging.info("The board %s doesn't need update.", self.get_board())
            return
        if not self.get_serial_number():
            logging.info('Serial number is not detected. It means no update'
                         ' will be performed on servo.')
            return
        if self._device.get_type() != self.get_board():
            logging.info('Attempt use incorrect updater for %s. Expected: %s.',
                         self._device.get_type(), self.get_board())
            return
        self._update_firmware(force_update, channel)

    def _custom_verifier(self):
        """Custom verifier to block update proceed.

        Please override the method if board needs special checks.

        @returns: True if can proceed with update, False if not.
        """
        return True

    def get_board(self):
        """Return servo type supported by updater."""
        raise NotImplementedError('Please implement method to return'
                                  ' servo type')

    def get_device(self):
        """Return ConnectedServo instance"""
        return self._device

    def get_serial_number(self):
        """Return serial number for servo device"""
        return self._device.get_serial_number()

    def _get_updater_cmd(self, force_update, channel):
        """Return command to run firmware updater for the servo device.

        @params force_update:   Run updater with force option.
        @params channel:        Channel for servo firmware.
        """
        board = self.get_board()
        serial_number = self.get_serial_number()
        # Using inline command line build as creating separate constants
        # make code more complicated on this stage.
        # TODO(otabek@) use constants when lab will use labstation R92
        cmd = 'servo_updater -b %s -s "%s"' % (board, serial_number)
        if self._updater_accept_channel:
            cmd += ' -c %s ' % channel.lower()
        # always reboot servo after updating the firmware
        cmd += ' --reboot '
        if force_update:
            cmd += ' --force '
        return cmd

    def _update_firmware(self, force_update, channel):
        """Execute firmware updater command.

        @params force_update:   Run updater with force option.
        @params channel:        UpdateCompare version from special firmware channel
        """
        cmd = self._get_updater_cmd(force_update, channel)
        logging.info('Try to update servo fw update by running: %s', cmd)
        try:
            res = self._host.run(cmd, timeout=120)
            logging.debug('Servo fw update finished; %s', res.stdout.strip())
            logging.info('Servo fw update finished')
        finally:
            self._kill_active_update_process()

    def _kill_active_update_process(self):
        """Kill active servo_update processes when stuck after attempt."""
        try:
            cmd = self.ACTIVE_UPDATER_KILL % self.get_serial_number()
            self._host.run(cmd, timeout=30, ignore_status=True)
        except Exception as e:
            logging.debug('Fail kill active processes; %s', e)

    def _current_version(self):
        """Get current version on servo device"""
        return self._device.get_version()

    def _latest_version(self, channel):
        """Get latest version available on servo-host.

        @params channel: Compare version from special firmware channel
        """
        # New R90 moved firmware files and introduced new way to check
        # the available firmware version on labstation. The servo_updater
        # introduced new option 'print'.
        cmd = 'servo_updater --help | grep print'
        result = self._host.run(cmd, ignore_status=True)
        if result.exit_status == 0:
            self._updater_accept_channel = True
            return self._latest_version_from_updater(channel)
        self._updater_accept_channel = False
        return self._latest_version_from_binary()

    def _latest_version_from_updater(self, channel):
        """Get latest available version from servo_updater.

        @params channel: Compare version from special firmware channel
        """
        cmd = self.LATEST_VERSION_CMD % (self.get_board(), channel.lower())
        re = self._host.run(cmd, ignore_status=True)
        if re.exit_status == 0:
            result = re.stdout.strip().split(':')
            if len(result) == 2:
                return result[-1].strip()
        return None

    def _latest_version_from_binary(self):
        """Get latest available version by parse firmware bin filename."""
        cmd = self.LATEST_VERSION_FW % self.get_board()
        filepath = self._host.run(cmd, ignore_status=True).stdout.strip()
        if not filepath:
            return None
        version = os.path.basename(os.path.splitext(filepath)[0]).strip()
        logging.debug('Latest version: %s', version)
        return version

    def _is_outdated_version(self, channel):
        """Compare version to determine request to update the Servo or not.

        @params channel: Compare version from special firmware channel
        """
        current_version = self._current_version()
        logging.debug('Servo fw on the device: "%s"', current_version)
        latest_version = self._latest_version(channel)
        logging.debug('Latest servo fw: "%s"', latest_version)
        if not current_version:
            return True
        if not latest_version:
            raise ServoFwVersionMissedError()
        if current_version == latest_version:
            return False
        return True


class UpdateServoV4Fw(_BaseUpdateServoFw):
    """Servo firmware updater for servo_v4."""

    def get_board(self):
        """Return servo type supported by updater"""
        return topology_constants.ST_V4_TYPE


class UpdateServoV4p1Fw(_BaseUpdateServoFw):
    """Servo firmware updater for servo_v4p1."""

    def get_board(self):
        """Return servo type supported by updater"""
        return topology_constants.ST_V4P1_TYPE


class UpdateServoMicroFw(_BaseUpdateServoFw):
    """Servo firmware updater for servo_micro."""

    def get_board(self):
        """Return servo type supported by updater"""
        return topology_constants.ST_SERVO_MICRO_TYPE


class UpdateC2D2Fw(_BaseUpdateServoFw):
    """Servo firmware updater for c2d2."""

    def get_board(self):
        """Return servo type supported by updater"""
        return topology_constants.ST_C2D2_TYPE


class UpdateSweetberryFw(_BaseUpdateServoFw):
    """Servo firmware updater for sweetberry."""

    def get_board(self):
        """Return servo type supported by updater"""
        return topology_constants.ST_SWEETBERRY_TYPE


# List servo firmware updaters mapped to the type
SERVO_UPDATERS = {
        topology_constants.ST_V4_TYPE: UpdateServoV4Fw,
        topology_constants.ST_V4P1_TYPE: UpdateServoV4p1Fw,
        topology_constants.ST_SERVO_MICRO_TYPE: UpdateServoMicroFw,
        topology_constants.ST_C2D2_TYPE: UpdateC2D2Fw,
        topology_constants.ST_SWEETBERRY_TYPE: UpdateSweetberryFw,
}


def _run_update_attempt(updater, topology, try_count, force_update,
                        ignore_version, channel):
    """Run servo update attempt.

    @params updater:        Servo updater instance.
    @params topology:       ServoTopology instance to update version.
    @params try_count:      Count of attempt to run update.
    @params force_update:   Run updater with force option.
    @params ignore_version: Do not check the version on the device.
    @params channel:        Request servo firmware from special channel

    @returns:   True is finished without any error, False - with error
    """
    board = updater.get_board()
    success = False
    for a in range(try_count):
        msg = 'Starting attempt: %d (of %d) to update "%s".'
        if force_update:
            msg += ' with force'
        logging.info(msg, a + 1, try_count, board)
        try:
            updater.update(force_update=force_update,
                           ignore_version=ignore_version,
                           channel=channel)
            topology.update_servo_version(updater.get_device())
            if not updater.need_update(ignore_version=ignore_version,
                                       channel=channel):
                success = True
        except Exception as e:
            logging.debug('(Not critical) fail to update %s; %s', board, e)
        if success:
            break
    return success


def any_servo_needs_firmware_update(host):
    """Verify if any servo requires firmware update.

    @params host:   ServoHost instance to run required commands
                    and access to topology.
    @returns:       True if any servo requires an update.
    """
    if not host:
        raise ValueError('ServoHost is not provided.')

    has_servo_requires_update = False
    for device in host.get_topology().get_list_of_devices():
        # Verify that device can provide serial and servo_type.
        if not device.is_good():
            continue
        board = device.get_type()
        updater_type = SERVO_UPDATERS.get(board, None)
        if not updater_type:
            logging.debug('No specified updater for %s', board)
            continue
        # Creating update instance
        updater = updater_type(host, device)
        if updater.need_update(ignore_version=False,
                               channel=host.servo_fw_channel):
            logging.info('The servo: %s requires firmware update!', board)
            has_servo_requires_update = True
    return has_servo_requires_update


def update_servo_firmware(host,
                          boards=None,
                          try_attempt_count=1,
                          force_update=False,
                          try_force_update=False,
                          ignore_version=False):
    """Update firmware on servo devices.

    @params host:               ServoHost instance to run required commands
                                and access to topology.
    @params try_attempt_count:  Count of attempts to update servo. For force
                                option the count attempts is always 1 (one).
    @params try_force_update:   Try force force option if fail to update in
                                normal mode.
    @params force_update:       Run updater with force option. Override
                                try_force_update option.
    @params ignore_version:     Do not check the version on the device.

    @returns:                   True is all servos updated or does not need it,
                                False if any device could not updated.
    """
    if boards is None:
        boards = []
    if ignore_version:
        logging.debug('Running servo_updater with ignore_version=True')

    if not host:
        raise ValueError('ServoHost is not provided.')

    # Use force option as first attempt
    use_force_option_as_first_attempt = False
    # If requested to update with force then first attempt will be with force
    # and there no second attempt.
    if force_update:
        try_attempt_count = 1
        try_force_update = False
        use_force_option_as_first_attempt = True
    # to run updater we need make sure the servod is not running
    host.stop_servod()
    # Collection to count which board failed to update
    fail_boards = []

    servo_topology = host.get_topology()
    # Get list connected servos
    for device in servo_topology.get_list_of_devices():
        # Verify that device can provide serial and servo_type.
        if not device.is_good():
            continue
        board = device.get_type()
        if len(boards) > 0 and board not in boards:
            logging.info('The %s is not requested for update', board)
            continue
        updater_type = SERVO_UPDATERS.get(board, None)
        if not updater_type:
            logging.info('No specified updater for %s', board)
            continue
        # Creating update instance
        updater = updater_type(host, device)
        is_success_update = _run_update_attempt(
                updater=updater,
                topology=servo_topology,
                try_count=try_attempt_count,
                force_update=use_force_option_as_first_attempt,
                ignore_version=ignore_version,
                channel=host.servo_fw_channel)
        # If fail to update and we got requested to try force option then
        # run second time with force.
        if not is_success_update and try_force_update:
            is_success_update = _run_update_attempt(
                    updater=updater,
                    topology=servo_topology,
                    try_count=1,
                    force_update=True,
                    ignore_version=ignore_version,
                    channel=host.servo_fw_channel)
        if not is_success_update:
            logging.info('Fail update firmware for %s', board)
            hostname = host.get_dut_hostname() or host.hostname
            metrics.Counter('chromeos/autotest/servo/fw_update_fail'
                            ).increment(fields={'host': hostname})
            fail_boards.append(board)

    if len(fail_boards) == 0:
        logging.info('Successfull updated all requested servos.')
        return True
    return False
