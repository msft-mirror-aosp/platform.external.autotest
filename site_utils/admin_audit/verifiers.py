#!/usr/bin/env python2
# Copyright 2020 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import logging

import common


DUT_STORAGE_STATE_PREFIX = 'storage_state'
SERVO_USB_STATE_PREFIX = 'servo_usb_state'
VERYFY_STATE_NORMAL = 'NORMAL'
VERYFY_STATE_ACCEPTABLE = 'ACCEPTABLE'
VERYFY_STATE_NEED_REPLACEMENT = 'NEED_REPLACEMENT'
VERYFY_STATE_UNKNOWN = 'UNKNOWN'


class AuditError(Exception):
  """Generic error raised during audit."""


class VerifyDutStorage:
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
    def verify(self, host):
        # pylint: disable=missing-docstring
        if not host:
            raise AuditError('host is not present')

        state = VERYFY_STATE_UNKNOWN
        # implementation will come later
        _set_host_info_state(host, DUT_STORAGE_STATE_PREFIX, state)


class VerifyServoUsb:
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
    def verify(self, host):
        # pylint: disable=missing-docstring
        if not host:
            raise AuditError('host is not present')
        if not host.servo:
            raise AuditError('servo is not initilized')

        state = VERYFY_STATE_UNKNOWN
        # implementation will come later
        _set_host_info_state(host, SERVO_USB_STATE_PREFIX, state)


def _set_host_info_state(host, prefix, state):
    """Update state value to the label in the host_info

    @param host: dut host presentation to provide access to host_info
    @param prefix: label prefix. (ex. label_prefix:value)
    @param state: new state value for the label
    """
    if host and prefix:
        host_info = host.host_info_store.get()
        old_state = host_info.get_label_value(prefix)
        host_info.set_version_label(prefix, state)
        logging.info('Set %s as `%s` (previous: `%s`)',
                     prefix, state, old_state)
        host.host_info_store.commit(host_info)
