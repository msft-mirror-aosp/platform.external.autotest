#!/usr/bin/env python2
# Copyright 2020 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.


"""Tool to audit a DUT in the lab."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import argparse
import logging
import logging.config
import os
import sys
import socket

import common
from autotest_lib.client.common_lib import enum
from autotest_lib.client.common_lib import logging_manager
from autotest_lib.server import server_logging_config
from autotest_lib.server.hosts import factory
from autotest_lib.server.hosts import servo_host

import verifiers

RETURN_CODES = enum.Enum(
        'OK',
        'VERIFY_FAILURE',
        'OTHER_FAILURES'
)

ACTION_VERIFY_DUT_STORAGE = 'verify-dut-storage'
ACTION_VERIFY_SERVO_USB = 'verify-servo-usb-drive'
ACTION_VERIFY_SERVO_FW = 'verify-servo-fw'
ACTION_FLASH_SERVO_KEYBOARD_MAP = 'flash-servo-keyboard-map'

_LOG_FILE = 'audit.log'

VERIFIER_MAP = {
    ACTION_VERIFY_DUT_STORAGE: verifiers.VerifyDutStorage,
    ACTION_VERIFY_SERVO_USB: verifiers.VerifyServoUsb,
    ACTION_VERIFY_SERVO_FW: verifiers.VerifyServoFw,
    ACTION_FLASH_SERVO_KEYBOARD_MAP: verifiers.FlashServoKeyboardMapVerifier,
}

# Actions required Servod service
ACTIONS_REQUIRED_SERVOD = set([
    ACTION_VERIFY_SERVO_USB,
    ACTION_FLASH_SERVO_KEYBOARD_MAP,
])

# Actions required ServoHost without Servod process
ACTIONS_REQUIRED_SERVO_HOST = set([
    ACTION_VERIFY_SERVO_FW,
])

class DutAuditError(Exception):
  """Generic error raised during DUT audit."""


def main():
    """Tool to audit a DUT."""
    opts = _parse_args()

    # Create logging setting
    logging_manager.configure_logging(
        server_logging_config.ServerLoggingConfig(),
        results_dir=opts.results_dir)

    logging.debug('autoserv is running in drone %s.', socket.gethostname())
    logging.debug('audit environment: %r', os.environ)
    logging.debug('audit command was: %s', ' '.join(sys.argv))
    logging.debug('audit parsed options: %s', opts)

    # Initialize ServoHost without running Servod process.
    need_servo_host = bool(set(opts.actions) & ACTIONS_REQUIRED_SERVO_HOST)
    # Initialize ServoHost with running Servod process.
    need_servod = bool(set(opts.actions) & ACTIONS_REQUIRED_SERVOD)
    try:
        host_object = factory.create_target_host(
            opts.hostname,
            host_info_path=opts.host_info_file,
            try_lab_servo=need_servod)
    except Exception as err:
        logging.error("fail to create host: %s", err)
        return RETURN_CODES.OTHER_FAILURES

    with host_object as host:
        if need_servo_host and not need_servod:
            try:
                host.set_servo_host(servo_host.ServoHost(
                    **servo_host.get_servo_args_for_host(host)
                ))
            except Exception as err:
                logging.error("fail to init servo host: %s", err)
                return RETURN_CODES.OTHER_FAILURES

        for action in opts.actions:
            if opts.dry_run:
                logging.info('DRY RUN: Would have run actions %s', action)
                return

            response = _verify(action, host)
            if response:
                return response

    return RETURN_CODES.OK


def _verify(action, host):
    """Run verifier for the action with targeted host.

    @param action: The action requested to run the verifier.
    @param host: The host presentation of the DUT.
    """
    try:
        _log("START", action)
        verifier = VERIFIER_MAP[action]
        if verifier:
            verifier(host).verify()
        else:
            logging.info('Verifier is not specified')
        _log("END_GOOD", action)
    except Exception as err:
        _log("END_FAIL", action, err)
        return RETURN_CODES.VERIFY_FAILURE


def _log(status, action, err=None):
    if err:
        message = '%s:%s; %s' % (action, status, str(err))
    else:
        message = '%s:%s' % (action, status)
    logging.info(message)


def _parse_args():
  parser = argparse.ArgumentParser(
      description='Audit DUT in a lab.')

  parser.add_argument(
      'actions',
      nargs='+',
      choices=list(VERIFIER_MAP),
      help='DUT audit actions to execute.',
  )
  parser.add_argument(
      '--dry-run',
      action='store_true',
      default=False,
      help='Run in dry-run mode. No changes will be made to the DUT.',
  )
  parser.add_argument(
      '--results-dir',
      required=True,
      help='Directory to drop logs and output artifacts in.',
  )

  parser.add_argument(
      '--hostname',
      required=True,
      help='Hostname of the DUT to audit.',
  )
  parser.add_argument(
      '--host-info-file',
      required=True,
      help=('Full path to HostInfo file.'
            ' DUT inventory information is read from the HostInfo file.'),
  )

  return parser.parse_args()


if __name__ == '__main__':
  sys.exit(main())
