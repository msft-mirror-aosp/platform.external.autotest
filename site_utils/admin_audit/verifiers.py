#!/usr/bin/env python2
# Copyright 2020 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import logging

import common
import base
import constants
import servo_updater
import time
import os

from autotest_lib.server.cros.storage import storage_validate as storage
from autotest_lib.client.common_lib import utils as client_utils
from autotest_lib.server.cros import servo_keyboard_utils

try:
    from chromite.lib import metrics
except ImportError:
    metrics = client_utils.metrics_mock

# Common status used for statistics.
STATUS_FAIL = 'fail'
STATUS_SUCCESS = 'success'
STATUS_SKIPPED = 'skipped'


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
    def _verify(self):
        if not self.servo_host_is_up():
            logging.info('Servo host is down; Skipping the verification')
            return
        servo_updater.update_servo_firmware(
            self.get_host(),
            force_update=True)


class FlashServoKeyboardMapVerifier(base._BaseDUTVerifier):
    """Flash the keyboard map on servo."""

    _ATMEGA_RESET_DELAY = 0.2
    _USB_PRESENT_DELAY = 1

    # Command to detect LUFA Keyboard Demo by VID.
    LSUSB_CMD = 'lsusb -d %s:' % servo_keyboard_utils.ATMEL_USB_VENDOR_ID

    def _verify(self):
        if not self.host_is_up():
            logging.info('Host is down; Skipping the action')
            return
        if not self.servo_is_up():
            logging.info('Servo not initialized; Skipping the action')
            return

        host = self.get_host()
        servo = host.servo
        try:
            logging.info('Starting flashing the keyboard map.')
            status = self._flash_keyboard_map(host, servo)
            logging.info('Set status: %s', status)
            if status == STATUS_FAIL:
                self._send_metrics()
        except Exception as e:
            # The possible errors is timeout of commands.
            logging.debug('Failed to flash servo keyboard map; %s', e)
            self._send_metrics()
        finally:
            # Restore the default settings.
            # Select the chip on the USB mux unless using Servo V4
            if 'servo_v4' not in servo.get_servo_version():
                servo.set('usb_mux_sel4', 'on')

    def _flash_keyboard_map(self, host, servo):
        if host.run('hash dfu-programmer', ignore_status=True).exit_status:
            logging.info(
                'The image is too old that does not have dfu-programmer.')
            return STATUS_SKIPPED

        servo.set_nocheck('init_usb_keyboard', 'on')

        if self._is_keyboard_present(host):
            logging.info('Already using the new keyboard map.')
            return STATUS_SUCCESS

        # Boot AVR into DFU mode by enabling the HardWareBoot mode
        # strapping and reset.
        servo.set_get_all(['at_hwb:on',
                            'atmega_rst:on',
                            'sleep:%f' % self._ATMEGA_RESET_DELAY,
                            'atmega_rst:off',
                            'sleep:%f' % self._ATMEGA_RESET_DELAY,
                            'at_hwb:off'])

        result = host.run(self.LSUSB_CMD, timeout=30).stdout.strip()
        if not 'Atmel Corp. atmega32u4 DFU bootloader' in result:
            logging.info('Not an expected chip: %s', result)
            return STATUS_FAIL

        # Update the keyboard map.
        bindir = os.path.dirname(os.path.realpath(__file__))
        local_path = os.path.join(bindir, 'data', 'keyboard.hex')
        host.send_file(local_path, '/tmp')
        logging.info('Updating the keyboard map...')
        host.run('dfu-programmer atmega32u4 erase --force', timeout=120)
        host.run('dfu-programmer atmega32u4 flash /tmp/keyboard.hex',
                 timeout=120)

        # Reset the chip.
        servo.set_get_all(['atmega_rst:on',
                            'sleep:%f' % self._ATMEGA_RESET_DELAY,
                            'atmega_rst:off'])
        if self._is_keyboard_present(host):
            logging.info('Update successfully!')
            return STATUS_SUCCESS

        logging.info('Update failed!')
        return STATUS_FAIL

    def _is_keyboard_present(self, host):
        # Check the result of lsusb.
        time.sleep(self._USB_PRESENT_DELAY)
        result = host.run(self.LSUSB_CMD, timeout=30).stdout.strip()
        logging.info('got the result: %s', result)
        if ('LUFA Keyboard Demo' in result and
            servo_keyboard_utils.is_servo_usb_wake_capable(host)):
            return True
        return False

    def _send_metrics(self):
        host = self.get_host()
        data = {'host': host.hostname, 'status': STATUS_FAIL}
        metrics.Counter(
            'chromeos/autotest/audit/servo_keyboard').increment(fields=data)
