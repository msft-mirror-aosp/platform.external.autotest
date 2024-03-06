# Lint as: python2, python3
# Copyright 2021 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Provide version control for Bluetooth tests"""

import logging
import os


from autotest_lib.client.common_lib import error
from autotest_lib.server import utils

CWD = os.getcwd()
CONNECTIVITY_DIR = os.path.dirname(__file__)
REMOTE_NAME = 'cros'
BRANCH_NAME = 'main'
BRANCH_NAME_FULL = os.path.join(REMOTE_NAME, BRANCH_NAME)
HTTP_MIRROR_URL =\
        'http://commondatastorage.googleapis.com/chromeos-localmirror'
BT_BUNDLE_PATH = 'distfiles/bluetooth_peer_bundle'
WIFI_BUNDLE_PATH = 'distfiles/wifi_bundle'
LATEST_STABLE_AUTOTEST_COMMIT = 'LATEST_STABLE_AUTOTEST_COMMIT'


class Args(object):
    """An Args class for test_that"""

    BOOL_DICT = {'true': True, 'false': False}

    @classmethod
    def get_bool(cls, arg_name, args_dict, default_value):
        """Get the bool argument value of arg_name from args_dict.

        @param arg_name: the target argument to query
        @param args_dict: the argument dictionary
        @param default_value: the default value of the argument
                if args_dict is not a dict or
                if the arg_name is not in args_dict or
                if the argument value is neither 'true' nor 'false'

        @returns: the bool value of the target argument
        """
        if type(args_dict) is dict and arg_name in args_dict:
            arg_value = str(args_dict[arg_name]).lower()
            return cls.BOOL_DICT.get(arg_value, default_value)
        return default_value


def get_latest_stable_autotest_commit_url(phy):
    """ Yield the correct API url depending on the connectivity type
    as different connectivity teams may have different autotest commit pins.

    @params phy: The name of the connectivity phy (e.g wifi, bluetooth).

    @returns: URL string to fetch commit hash
    """
    generate_commit_url = lambda bundle_url: os.path.join(
            HTTP_MIRROR_URL, bundle_url, LATEST_STABLE_AUTOTEST_COMMIT)

    if phy == 'bluetooth':
        url = generate_commit_url(BT_BUNDLE_PATH)
    elif phy == 'wifi':
        url = generate_commit_url(WIFI_BUNDLE_PATH)
    else:
        raise error.TestError('Invalid phy provided. Got {0}. Supported phys: ' \
                    'WiFi, Bluetooth'.format(phy))
    return url


def check_git_tree_clean():
    """ Check if local directory is clear from modification

    @returns: True if success, False otherwise
    """
    output = utils.run('git status --porcelain')
    if output.stdout != '':
        logging.info(
                'The Autotest directory is not clean! To perform the AVL\n'
                'testing consistently, the AVL setup process will fetch\n'
                'a specific commit hash from the server and check out\n'
                'locally. To preserve your local changes, please commit\n'
                'or stash your changes! Changes:')
        logging.info(output.stdout)
        return False

    logging.info('Local git tree is clean.')
    return True


def fetch_target_commit(phy):
    """ Fetch from the cloud or git to retrieve latest ToT or latest stable
    commit hash.

    @params phy: The name of the connectivity phy (e.g wifi, bluetooth).

    @returns: current and targeted commit hash
    """
    current_commit = utils.system_output('git rev-parse HEAD')
    utils.run('git fetch ' + REMOTE_NAME)
    target_commit = utils.system_output(
            'git rev-parse {}'.format(BRANCH_NAME_FULL))

    output = utils.run('curl {}'.format(
            get_latest_stable_autotest_commit_url(phy)),
                       ignore_status=True)

    if output.exit_status != 0:
        logging.info('Failed to fetch the latest commit from the server')
        logging.info(output.stdout)
        logging.info(output.stderr)
    else:
        target_commit = output.stdout.strip()

    logging.info('The latest commit will be used is:\n%s', target_commit)
    return current_commit, target_commit


def checkout_commit(commit):
    """ Checkout the autotest directory to the specified commit."""
    output = utils.run('git checkout {}'.format(commit), ignore_status=True)
    if output.exit_status != 0:
        logging.info(output.stderr)
        logging.info('Failed to checkout target commit, please retry '
                     'after\nrepo sync')
    else:
        logging.info('Target (stable or ToT) autotest commit is checked out,\n'
                     'please rerun the test!')


def test_version_setup_exit_print():
    """ Exit the setup and return to the previous CWD."""
    logging.info('=======================================================\n')
    os.chdir(CWD)


def test_version_setup(phy, args_dict={}):
    """This and above functions hope to sync the AVL test environments
    among different vendors, partners, and developers by providing an
    automatic process to fetch a commit hash of the "released"
    (or "stabled") version of the autotest directory from the cloud and
    checkout locally. No manual interaction should be expected.

    @params phy: The name of the connectivity phy (e.g wifi, bluetooth).
    @params args_dict: The argument dictionary passed to test_that through
            --args. For example, to skip test_version_setup, one can use
            the argument as
            test_that --args "version_check=false" ...

    @returns: True if current commit version satisfied requirement, the
              test shall proceed. False otherwise.
    """
    logging.info('=======================================================\n'
                 '                    AVL Test Setup\n')

    if not Args.get_bool('version_check', args_dict, default_value=True):
        logging.info('Skip test_version_setup() because version_check=false.')
        return True

    os.chdir(CONNECTIVITY_DIR)
    if not check_git_tree_clean():
        test_version_setup_exit_print()
        return False

    current_commit, target_commit = fetch_target_commit(phy)
    if current_commit == target_commit:
        logging.info('Local tree is already at target autotest commit.')
        test_version_setup_exit_print()
        return True

    checkout_commit(target_commit)
    test_version_setup_exit_print()
    return False
