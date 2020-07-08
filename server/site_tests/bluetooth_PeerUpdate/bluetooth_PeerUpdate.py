# Copyright 2019 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""
Test which updates chameleond on the Bluetooth Peer device

This is not a test per se. This 'test' checks if the chameleond commit on the
Bluetooth peer device and updates it if it below the expected value.

The expected commit and the installation bundle is downloaded from google cloud
storage.
"""

import logging
import os
import sys
import time
import tempfile

from datetime import datetime

from autotest_lib.client.common_lib import error
from autotest_lib.server import test
from autotest_lib.client.bin import utils


# The location of the package in the cloud
GS_PUBLIC = 'gs://chromeos-localmirror/distfiles/bluetooth_peer_bundle/'

# NAME of the file that stores  commit info in the cloud
COMMIT_FILENAME = 'latest_bluetooth_commit'

# The following needs to be kept in sync with values chameleond code
BUNDLE_TEMPLATE='chameleond-0.0.2-{}.tar.gz' # Name of the chamleond package
BUNDLE_DIR = 'chameleond-0.0.2'
BUNDLE_VERSION = '9999'
CHAMELEON_BOARD = 'fpga_tio'

def run_cmd(peer, cmd):
    """A wrapper around host.run()."""
    try:
        logging.info('executing command %s on peer',cmd)
        result = peer.host.run(cmd)
        logging.info('exit_status is %s', result.exit_status)
        logging.info('stdout is %s stderr is %s', result.stdout, result.stderr)
        output = result.stderr if result.stderr else result.stdout
        if result.exit_status == 0:
            return True, output
        else:
            return False, output
    except error.AutoservRunError as e:
        logging.error('Error while running cmd %s %s', cmd, e)
        return False, None

def is_update_needed(peer, latest_commit):
    """ Check if update is required

    Update if the commit hash doesn't match

    @returns: True/False
    """
    return not is_commit_hash_equal(peer, latest_commit)


def is_commit_hash_equal(peer, latest_commit):
    """ Check if chameleond commit hash is the expected one"""
    try:
        commit = peer.get_bt_commit_hash()
    except:
        logging.error('Getting the commit hash failed %s', sys.exc_info())
        return False

    logging.debug('commit %s found on peer %s', commit, peer.host)
    return commit == latest_commit


def perform_update(peer, latest_commit):
    """ Update the chameleond on the peer"""

    logging.info('copy the file over to the peer')
    try:

        cur_dir = '/tmp/'
        bundle = BUNDLE_TEMPLATE.format(latest_commit)
        bundle_path = os.path.join(cur_dir, bundle)
        logging.debug('package location is %s', bundle_path)

        peer.host.send_file(bundle_path, '/tmp/')
    except:
        logging.error('copying the file failed %s ', sys.exc_info())
        logging.error(str(os.listdir(cur_dir)))
        return False

    HOST_NOW = datetime.strftime(datetime.now(), '%Y-%m-%d %H:%M:%S')
    logging.info('running make on peer')
    cmd = ('cd %s && rm -rf %s && tar zxf %s &&'
           'cd %s && find -exec touch -c {} \; &&'
           'make install REMOTE_INSTALL=TRUE '
           'HOST_NOW="%s" BUNDLE_VERSION=%s '
           'CHAMELEON_BOARD=%s && rm %s%s') % (cur_dir,BUNDLE_DIR, bundle,
                                               BUNDLE_DIR, HOST_NOW,
                                               BUNDLE_VERSION,
                                               CHAMELEON_BOARD, cur_dir,
                                               bundle)
    logging.debug(cmd)
    status, _ = run_cmd(peer, cmd)
    if not status:
        logging.info('make failed')
        return False

    logging.info('chameleond installed on peer')
    return True


def restart_check_chameleond(peer):
    """restart chamleond and make sure it is running."""

    restart_cmd = 'sudo /etc/init.d/chameleond restart'
    start_cmd = 'sudo /etc/init.d/chameleond start'
    status_cmd = 'sudo /etc/init.d/chameleond status'

    status, _ = run_cmd(peer, restart_cmd)
    if not status:
        status, _ = run_cmd(peer, start_cmd)
        if not status:
            logging.error('restarting/starting chamleond failed')
    #
    #TODO: Refactor so that we wait for all peer devices all together.
    #
    # Wait till chameleond initialization is complete
    time.sleep(5)

    status, output = run_cmd(peer, status_cmd)
    expected_output = 'chameleond is running'
    return status and expected_output in output


def update_peer(peer, latest_commit):
    """Update the chameleond on peer devices if required"""

    if not perform_update(peer, latest_commit):
        return False, 'Update failed'

    if not restart_check_chameleond(peer):
        return False, 'Unable to start chameleond'

    if is_update_needed(peer, latest_commit):
        return False, 'Commit not updated after upgrade'

    logging.info('updating chameleond succeded')
    return True, ''


def update_peers(host, latest_commit):
    """Update the chameleond on peer devices"""

    peer_list =  host.btpeer_list[:]
    if host.chameleon is not None:
        peer_list.append(host.chameleon)

    if peer_list == []:
        raise error.TestError('Bluetooth Peer not present')

    status = {}
    for peer in peer_list:
        if peer.get_platform() != 'RASPI':
            logging.error('Unsupported peer %s',str(peer.host))
            continue
        status[peer] = {'updated': False,
                        'reason' : None,
                        'update_needed' : True}
        if not is_update_needed(peer,latest_commit):
            status[peer]['update_needed'] = False
            logging.info('Update not needed on peer %s', str(peer.host))
            continue

        status[peer]['updated'], status[peer]['reason'] = update_peer(
                peer, latest_commit)

    logging.debug(status)

    # If none of the peer need update raise TestNA
    if not any([v['update_needed'] for v in status.values()]):
        raise error.TestNAError('Update not needed')

    # If any of the peers failed update, raise failure with the reason
    if not all([v['updated'] for k,v in status.items() if v['update_needed']]):
        for peer, v in status.items():
            if not v['updated']:
                logging.error('peer %s failed %s', str(peer.host),  v['reason'])
        raise error.TestFail()

    logging.info('All eligible peers updated')


def get_latest_commit():
    """ Get the latest commit

    Download the file containing the latest commit and
    parse it contents, and cleanup.
    @returns (True,commit) in case of success (False, None) in case of failure
    """
    try:
        commit = None
        src = GS_PUBLIC + COMMIT_FILENAME

        with tempfile.NamedTemporaryFile(suffix='bt_commit') as tmp_file:
            tmp_filename = tmp_file.name
            cmd = 'gsutil cp {} {}'.format(src, tmp_filename)
            result = utils.run(cmd)
            if result.exit_status != 0:
                logging.debug('Downloading commit file failed with %s', result.exit_status)
                return (False, None)
            with open(tmp_filename) as f:
                content = f.read()
                logging.debug('content of the file is %s', content)
                commit = content.strip('\n').strip()

        logging.info('latest commit is %s', commit)
        if commit is None:
            return (False, None)
        else:
            return (True, commit)
    except Exception as e:
        logging.error('exception %s in get_latest_commit', str(e))
        return (False, None)


def download_installation_files(host, commit):
    """ Download the chameleond installation bundle"""
    src_path = GS_PUBLIC + BUNDLE_TEMPLATE.format(commit)
    dest_path = '/tmp/' + BUNDLE_TEMPLATE.format(commit)
    logging.debug('chamelond bundle path is %s', src_path)
    logging.debug('bundle path in DUT is %s', dest_path)

    cmd = 'gsutil cp {} {}'.format(src_path, dest_path)
    try:
        result = utils.run(cmd)
        if result.exit_status != 0:
            logging.debug('Downloading the chameleond bundle failed with %d',
                          result.exit_status)
            return False
        host.send_file(dest_path, dest_path)
        logging.debug('file send to %s %s',host, dest_path)
        return True
    except Exception as e:
        logging.error('exception %s in download_installation_files', str(e))
        raise error.TestFail('Failed to copy the bundle file to the DUT')


def cleanup(host, commit):
    """ Cleanup the installation file from server."""
    try:
        dest_path = '/tmp/' + BUNDLE_TEMPLATE.format(commit)
        if os.path.exists(dest_path):
            logging.debug('Remove file %s', dest_path)
            os.remove(dest_path)
        else:
            logging.debug('File %s not found', dest_path)

        result = host.run('rm {}'.format(dest_path))
        if result.exit_status != 0:
            logging.error('Unable to delete %s on dut', dest_path)
    except Exception as e:
        logging.error('Exception %s in cleanup', str(e))
        raise error.TestFail('Cleanup failed')



class bluetooth_PeerUpdate(test.test):
    """
    This test updates chameleond on Bluetooth peer devices

    """

    version = 1

    def run_once(self, host):
        """ Update Bluetooth peer device

        @param host: the DUT, usually a chromebook
        """
        try:
            self.host = host
            commit = None
            (status, commit) = get_latest_commit()
            if commit is None:
                raise error.TestFail('Unable to get current commit')
            if not download_installation_files(self.host, commit):
                raise error.TestFail('Unable to download installation files ')
            update_peers(self.host, commit)
        finally:
            cleanup(host, commit)
