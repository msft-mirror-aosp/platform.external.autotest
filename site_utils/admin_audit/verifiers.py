#!/usr/bin/env python2
# Copyright 2020 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import logging

import common
import base
import constants
import servo_updater

from autotest_lib.server.cros.storage import storage_validate as storage
from autotest_lib.client.common_lib import utils as client_utils

try:
    from chromite.lib import metrics
except ImportError:
    metrics = client_utils.metrics_mock

class VerifyDutStorage(base._BaseDUTVerifier):
    """Verify the state of the storage on the DUT

    The process to determine the type of storage and read metrics
    of usage and EOL(end-of-life) information to determine the
    state.
    Supported storage types: MMS, NVME, SSD.
    Possible states are:
      UNKNOWN - not access to the DUT, not determine type of storage,
                not information to determine metrics
      NORMAL - the storage is in good shape and will work stable
                device will work stable. (supported for all types)
      ACCEPTABLE - the storage almost used all resources, device will
                work stable but it is better be ready for replacement
                device will work stable. (supported by MMS, NVME)
      NEED_REPLACEMENT - the storage broken or worn off the life limit
                device can work by not stable and can cause the
                flakiness on the tests. (supported by all types)
    """
    def __init__(self, dut_host):
        super(VerifyDutStorage, self).__init__(dut_host)
        self._state = None

    def _verify(self, set_label=True):
        if not self.host_is_up():
            logging.info('Host is down; Skipping the verification')
            return
        try:
            validator = storage.StorageStateValidator(self.get_host())
            storage_type = validator.get_type()
            logging.debug('Detected storage type: %s', storage_type)
            storage_state = validator.get_state()
            logging.debug('Detected storage state: %s', storage_state)
            state = self.convert_state(storage_state)
            if state and set_label:
                self._set_host_info_state(constants.DUT_STORAGE_STATE_PREFIX,
                                          state)
            self._state = state
        except Exception as e:
            raise base.AuditError('Exception during getting state of'
                                  ' storage %s' % str(e))

    def convert_state(self, state):
        """Mapping state from validator to verifier"""
        if state == storage.STORAGE_STATE_NORMAL:
            return constants.HW_STATE_NORMAL
        if state == storage.STORAGE_STATE_WARNING:
            return constants.HW_STATE_ACCEPTABLE
        if state == storage.STORAGE_STATE_CRITICAL:
            return constants.HW_STATE_NEED_REPLACEMENT
        return None

    def get_state(self):
        return self._state


class VerifyServoUsb(base._BaseServoVerifier):
    """Verify the state of the USB-drive on the Servo

    The process to determine by checking the USB-drive on having any
    bad sectors on it.
    Possible states are:
      UNKNOWN - not access to the device or servo, not available
                software on the servo.
      NORMAL - the device available for testing and not bad sectors.
                was found on it, device will work stable
      NEED_REPLACEMENT - the device available for testing and
                some bad sectors were found on it. The device can
                work but cause flakiness in the tests or repair process.

    badblocks errors:
    No such device or address while trying to determine device size
    """
    def _verify(self):
        if not self.servo_is_up():
            logging.info('Servo not initialized; Skipping the verification')
            return
        servo = self.get_host().get_servo()
        usb = servo.probe_host_usb_dev()
        if not usb:
            logging.error('Usb not detected')
            metrics.Counter(
                'chromeos/autotest/servo/usb/not_detected'
                ).increment(fields={'host': self._dut_host.hostname})
            self._set_state(constants.HW_STATE_NEED_REPLACEMENT)
            return

        state = None
        try:
            # The USB will be format during checking to the bad blocks.
            command = 'badblocks -sw -e 1 -t 0xff %s' % usb
            logging.info('Running command: %s', command)
            # The response is the list of bad block on USB.
            result = servo.system_output(command)
            logging.info("Check result: '%s'", result)
            if result:
                # So has result is Bad and empty is Good.
                state = constants.HW_STATE_NEED_REPLACEMENT
            else:
                state = constants.HW_STATE_NORMAL
        except Exception as e:
            if 'Timeout encountered:' in str(e):
                logging.info('Timeout during running action')
                metrics.Counter(
                    'chromeos/autotest/audit/servo/usb/timeout'
                    ).increment(fields={'host': self._dut_host.hostname})
            else:
                # badblocks generate errors when device not reachable or
                # cannot read system information to execute process
                state = constants.HW_STATE_NEED_REPLACEMENT
            logging.debug(str(e))

        self._set_state(state)

        # install fresh image to the USB because badblocks formats it
        # https://crbug.com/1091406
        try:
            logging.debug('Started to install test image to USB-drive')
            _, image_path = self._dut_host.stage_image_for_servo()
            servo.image_to_servo_usb(image_path, power_off_dut=False)
            logging.debug('Finished installing test image to USB-drive')
        except:
            # ignore any error which happined during install image
            # it not relative to the main goal
            logging.debug('Fail to install test image to USB-drive')
            pass

    def _set_state(self, state):
        if state:
            self._set_host_info_state(constants.SERVO_USB_STATE_PREFIX, state)


class VerifyServoFw(base._BaseServoVerifier):
    """Force update Servo firmware if it not up-to-date.

    This is rarely case when servo firmware was not updated by labstation
    when servod started. This should ensure that the servo_v4 and
    servo_micro is up-to-date.
    """

    UPDATERS = [
        servo_updater.UpdateServoV4Fw,
        servo_updater.UpdateServoMicroFw,
    ]

    def _verify(self):
        if not self.servo_host_is_up():
            logging.info('Servo host is down; Skipping the verification')
            return
        host = self.get_host()
        # create all updater
        updaters = [updater(host) for updater in self.UPDATERS]
        # run checker for all updaters
        for updater in updaters:
            supported = updater.check_needs()
            logging.debug('The board %s is supported: %s',
                          updater.get_board(), supported)
        # to run updater we need make sure the servod is not running
        host.stop_servod()
        #  run update
        for updater in updaters:
            try:
                updater.update(force_update=True)
            except Exception as e:
                metrics.Counter(
                    'chromeos/autotest/audit/servo/fw/update/error'
                    ).increment(fields={'host': self._dut_host.hostname})
                logging.info('Fail update firmware for %s',
                             updater.get_board())
                logging.debug('Fail update firmware for %s: %s',
                              updater.get_board(), str(e))
