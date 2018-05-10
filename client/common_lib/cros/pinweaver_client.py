# Copyright 2018 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import json

from subprocess import CalledProcessError


class PinWeaverNotAvailableError(CalledProcessError):
    """This exception is thrown when pinweaver_client reports that the PinWeaver
    feature is not available.
    """

    def __init__(self, *args, **kwargs):
        super(PinWeaverNotAvailableError, self).__init__(*args, **kwargs)


def __execute_for_dict(client, *args, **kwargs):
    """Executes a command with the specified args and parses stdout as JSON
    based on the expected output of pinweaver_client.
    """
    result = {}
    stack = [result]
    if 'ignore_status' not in kwargs:
        kwargs['ignore_status'] = True
    run = client.run(*args, **kwargs)
    if run.exit_status == 2:  # EXIT_PINWEAVER_NOT_SUPPORTED
        raise PinWeaverNotAvailableError(run.exit_status, args[0]);
    return json.loads(run.stdout)


def ResetTree(client, bits_per_level, height):
    """Returns a dictionary with keys result_code and root_hash.

    @param client: client object to run commands on.
    """
    return __execute_for_dict(client, 'pinweaver_client resettree %d %d' %
                              (bits_per_level, height))


def InsertLeaf(client, label, auxilary_hashes, low_entropy_secret,
               high_entropy_secret, reset_secret, delay_schedule):
    """Returns a dictionary with keys result_code, root_hash, cred_metadata,
    and mac.

    @param client: client object to run commands on.
    """
    return __execute_for_dict(
        client, 'pinweaver_client insert %d %s %s %s %s %s' %
                (label, auxilary_hashes, low_entropy_secret,
                 high_entropy_secret, reset_secret, delay_schedule))


def RemoveLeaf(client, label, auxilary_hashes, mac):
    """Returns a dictionary with keys result_code and root_hash.

    @param client: client object to run commands on.
    """
    return __execute_for_dict(
        client, 'pinweaver_client remove %d %s %s' %
                (label, auxilary_hashes, mac))


def TryAuth(client, auxilary_hashes, low_entropy_secret, cred_metadata):
    """Returns a dictionary with keys result_code, root_hash, cred_metadata,
    mac, and he_secret.

    @param client: client object to run commands on.
    """
    return __execute_for_dict(
        client, 'pinweaver_client auth %s %s %s' %
                (auxilary_hashes, low_entropy_secret, cred_metadata))


def ResetAuth(client, auxilary_hashes, reset_secret, cred_metadata):
    """Returns a dictionary with keys result_code, root_hash, cred_metadata,
    mac, and he_secret.

    @param client: client object to run commands on.
    """
    return __execute_for_dict(
        client, 'pinweaver_client resetleaf %s %s %s' %
                (auxilary_hashes, reset_secret, cred_metadata))


def GetLog(client, root):
    """Returns a dictionary with keys result_code, root_hash, and a list of
    entry[#] sub dictionaries for each log entry.

    @param client: client object to run commands on.
    """
    return __execute_for_dict(client, 'pinweaver_client getlog %s' % (root))


def LogReplay(client, auxilary_hashes, log_root, cred_metadata):
    """Returns a dictionary with keys result_code, root_hash, cred_metadata,
    and mac.

    @param client: client object to run commands on.
    """
    return __execute_for_dict(
        client, 'pinweaver_client replay %d %s %s %s' %
                (auxilary_hashes, log_root, cred_metadata))


def SelfTest(client):
    """Returns True if the test succeeded.

    @param client: client object to run commands on.
    """
    run = client.run('pinweaver_client selftest')
    if run.exit_status == -2:
        raise PinWeaverNotAvailableError();
    output = run.stdout
    return "Success!" in output
