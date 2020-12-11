# Copyright (c) 2021 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Utilities to interact with the TPM on a CrOS device."""

import logging
import re

import common

from autotest_lib.client.bin import utils
from autotest_lib.client.common_lib import error

CRYPTOHOME_CMD = '/usr/sbin/cryptohome'
UNAVAILABLE_ACTION = 'Unknown action or no action given.'


class ChromiumOSError(error.TestError):
    """Generic error for ChromiumOS-specific exceptions."""

    pass


def get_tpm_status():
    """Get the TPM status.

    Returns:
        A TPM status dictionary, for example:
        { 'Enabled': True,
          'Owned': True,
          'Being Owned': False,
          'Ready': True,
          'Password': ''
        }
    """
    out = __run_cmd(CRYPTOHOME_CMD + ' --action=tpm_status')
    status = {}
    for field in ['Enabled', 'Owned', 'Being Owned', 'Ready']:
        match = re.search('TPM %s: (true|false)' % field, out)
        if not match:
            raise ChromiumOSError('Invalid TPM status: "%s".' % out)
        status[field] = match.group(1) == 'true'
    match = re.search('TPM Password: (\w*)', out)
    status['Password'] = ''
    if match:
        status['Password'] = match.group(1)
    return status


def get_tpm_more_status():
    """Get more of the TPM status.

    Returns:
        A TPM more status dictionary, for example:
        { 'dictionary_attack_lockout_in_effect': False,
          'attestation_prepared': False,
          'boot_lockbox_finalized': False,
          'enabled': True,
          'owned': True,
          'owner_password': ''
          'dictionary_attack_counter': 0,
          'dictionary_attack_lockout_seconds_remaining': 0,
          'dictionary_attack_threshold': 10,
          'attestation_enrolled': False,
          'initialized': True,
          'verified_boot_measured': False,
          'install_lockbox_finalized': True
        }
        An empty dictionary is returned if the command is not supported.
    """
    status = {}
    out = __run_cmd(CRYPTOHOME_CMD + ' --action=tpm_more_status | grep :')
    if out.startswith(UNAVAILABLE_ACTION):
        # --action=tpm_more_status only exists >= 41.
        logging.info('Method not supported!')
        return status
    for line in out.splitlines():
        items = line.strip().split(':')
        if items[1].strip() == 'false':
            value = False
        elif items[1].strip() == 'true':
            value = True
        elif items[1].strip().isdigit():
            value = int(items[1].strip())
        else:
            value = items[1].strip(' "')
        status[items[0]] = value
    return status


def __run_cmd(cmd):
    """Run a command on utils.system_output, and append '2>&1'."""
    return utils.system_output(cmd + ' 2>&1', retain_output=True,
                               ignore_status=True).strip()
