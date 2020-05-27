#!/usr/bin/env python2
# Copyright 2020 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import logging

import common
import base
import constants
from autotest_lib.server.cros.storage import storage_validate as storage


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
    def _verify(self):
        try:
            validator = storage.StorageStateValidator(self.get_host())
            storage_type = validator.get_type()
            logging.debug('Detected storage type: %s', storage_type)
            storage_state = validator.get_state()
            logging.debug('Detected storage state: %s', storage_state)
            state  = self.convert_state(storage_state)
            if state:
                self._set_host_info_state(constants.DUT_STORAGE_STATE_PREFIX,
                                          state)
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

    """
    def _verify(self):
        servo = self.get_host().get_servo()
        usb = servo.probe_host_usb_dev()
        if not usb:
            logging.error('Usb not detected')
            return

        state = constants.HW_STATE_NORMAL

        # The USB will be format during checking to the bad blocks.
        command = 'badblocks -sw -e 1 -t 0xff %s' % usb
        logging.info('Running command: %s', command)

        # The response is the list of bad block on USB.
        result = servo.system_output(command, ignore_status=True)
        logging.info("Check result: '%s'", result)
        if result:
            # So has result is Bad and empty is Good.
            state = constants.HW_STATE_NEED_REPLACEMENT
        self._set_host_info_state(constants.SERVO_USB_STATE_PREFIX, state)
