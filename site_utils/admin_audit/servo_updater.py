#!/usr/bin/env python2
# Copyright 2020 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import os
import logging

import common
from autotest_lib.client.common_lib import utils as client_utils
from autotest_lib.server.cros.servo.topology import servo_topology
from autotest_lib.server.cros.servo.topology import topology_constants

try:
    from autotest_lib.utils.frozen_chromite.lib import metrics
except ImportError:
    metrics = client_utils.metrics_mock


class _BaseUpdateServoFw(object):
    """Base class to update firmware on servo"""

    # Command to update servo device.
    # param 1: servo board (servo_v4|servo_micro)
    # param 2: serial number of main device on the board
    UPDATER = 'servo_updater -b %s -s "%s" --reboot'
    UPDATER_FORCE = UPDATER + ' --force'

    # Commands to kill active servo_updater fail with timeout
    ACTIVE_UPDATER_CORE = 'ps aux | grep -ie [s]ervo_updater |grep "%s" '
    ACTIVE_UPDATER_PRINT = ACTIVE_UPDATER_CORE + "| awk '{print $2}' "
    ACTIVE_UPDATER_KILL = ACTIVE_UPDATER_PRINT + "| xargs kill -9 "

    # Command to get PATH to the latest available firmware on the host
    # param 1: servo board (servo_v4|servo_micro)
    LATEST_VERSION_FW = 'realpath /usr/share/servo_updater/firmware/%s.bin'

    def __init__(self, servo_host, device):
        self._host = servo_host
        self._device = device

    def need_update(self, ignore_version=False):
        """Verify that servo_update is required.

        @params ignore_version: Do not check the version on the device.

        @returns: True if update required, False if not
        """
        if not self._host:
            return False
        elif not self.get_serial_number():
            return False
        elif not self._host.is_labstation():
            return False
        elif not self._custom_verifier():
            return False
        elif not ignore_version:
            return self._is_outdated_version()
        logging.info('The board %s is need update.', self.get_board())
        return True

    def update(self, force_update=False, ignore_version=False):
        """Update firmware on the servo.

        Steps:
        1) Verify servo is not updated by checking the versions.
        2) Try to get serial number for the servo.
        3) Updating firmware.

        @params force_update:   Run updater with force option.
        @params ignore_version: Do not check the version on the device.
        """
        if not self.need_update(ignore_version):
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
        self._update_firmware(force_update)

    def _custom_verifier(self):
        """Custom verifier to block update proceed.

        Please override the method if board needs special checks.

        @returns: True if can proceed with update, False if not.
        """
        return True

    def get_board(self):
        """Return servo type supported by updater"""
        raise NotImplementedError('Please implement method to return'
                                  ' servo type')

    def get_serial_number(self):
        """Return serial number for servo device"""
        return self._device.get_serial_number()

    def _get_updater_cmd(self, force_update):
        """Return command to run firmware updater for the servo device.

        @params force_update: run updater with force option.
        """
        board = self.get_board()
        serial_number = self.get_serial_number()
        if force_update:
            cmd = self.UPDATER_FORCE
        else:
            cmd = self.UPDATER
        return cmd % (board, serial_number)

    def _update_firmware(self, force_update):
        """Execute firmware updater command.

        @params force_update: run updater with force option.
        """
        cmd = self._get_updater_cmd(force_update)
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

    def _latest_version(self):
        """Get latest version available on servo-host"""
        cmd = self.LATEST_VERSION_FW % self.get_board()
        filepath = self._host.run(cmd, ignore_status=True).stdout.strip()
        if not filepath:
            return None
        version = os.path.basename(os.path.splitext(filepath)[0]).strip()
        logging.debug('Latest version: %s', version)
        return version

    def _is_outdated_version(self):
        """Compare version to determine request to update the Servo or not.
        """
        current_version = self._current_version()
        latest_version = self._latest_version()
        if not current_version or not latest_version:
            return True
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


def _run_update_attempt(updater, try_count, force_update, ignore_version):
    """Run servo update attempt.

    @params updater:        Servo updater instance.
    @params try_count:      Count of attempt to run update.
    @params force_update:   Run updater with force option.
    @params ignore_version: Do not check the version on the device.

    @returns:   True is finished without any error, False - with error
    """
    board = updater.get_board()
    success = False
    for a in range(try_count):
        msg = 'Starting attempt: %s to update "%s".'
        if force_update:
            msg += ' with force'
        logging.info(msg, a + 1, board)
        try:
            updater.update(force_update=force_update,
                           ignore_version=ignore_version)
            success = True
        except Exception as e:
            logging.debug('(Not critical) fail to update %s; %s', board, e)
        if success:
            break
    return success


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

    # Basic verification
    if not host:
        raise Exception('ServoHost is not provided.')

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

    # Get list connected servos
    topology = servo_topology.ServoTopology(host)
    for device in topology.get_list_of_devices():
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
                try_count=try_attempt_count,
                force_update=use_force_option_as_first_attempt,
                ignore_version=ignore_version)
        # If fail to update and we got requested to try force option then
        # run second time with force.
        if not is_success_update and try_force_update:
            is_success_update = _run_update_attempt(
                    updater=updater,
                    try_count=1,
                    force_update=True,
                    ignore_version=ignore_version)
        if not is_success_update:
            logging.info('Fail update firmware for %s', board)
            host = host.get_dut_hostname() or host.hostname
            metrics.Counter('chromeos/autotest/servo/fw_update_fail'
                            ).increment(fields={'host': host})
            fail_boards.append(board)

    if len(fail_boards) == 0:
        logging.info('Successfull updated all requested servos.')
        return True
    return False
