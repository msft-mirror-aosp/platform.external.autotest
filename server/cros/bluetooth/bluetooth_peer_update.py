# Lint as: python3
# Copyright 2023 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""
This file provides functions to implement bluetooth_PeerUpdate test
which downloads chameleond bundle from Google Cloud Storage and updates
peer device associated with a DUT

The chameleond bundle selection process is documented in the proto definition
of BluetoothPeerChameleondConfig.
"""

from __future__ import absolute_import
from . import common
import functools
import logging
import os
import tempfile
import time
from datetime import datetime
from autotest_lib.client.bin import utils
from autotest_lib.client.common_lib import error
from chromiumos.test.lab.api.bluetooth_peer_pb2 import (
        BluetoothPeerChameleondConfig)
from google.protobuf import json_format

from autotest_lib.client.cros.chameleon.chameleon import ChameleonBoard
from autotest_lib.server.hosts import CrosHost

GCS_BASE_DIR = 'gs://chromeos-connectivity-test-artifacts/btpeer'

# GCS_PROD_CONFIG_FILE is the production config file that all automated
# processes should use normally to select the btpeer chameleond version.
GCS_PROD_CONFIG_FILE = f'{GCS_BASE_DIR}/btpeer_chameleond_config_prod.json'

# GCS_TEST_CONFIG_FILE is the test config file that should only be used
# when validating a config change prior to pushing it to production by
# updating the GCS_PROD_CONFIG_FILE.
#
# Note: Config file updates should be done with the btpeer_manager CLI
# only, not manually, as it preforms validation on the contents and format.
GCS_TEST_CONFIG_FILE = f'{GCS_BASE_DIR}/btpeer_chameleond_config_test.json'

# Temporary install/download directory used on both local system and btpeer.
BTPEER_CHAMELEOND_INSTALL_TMP_DIR = "/tmp/chameleond_bundle_update"

# The following needs to be kept in sync with values chameleond code
BUNDLE_VERSION = '9999'
CHAMELEON_BOARD = 'fpga_tio'
BTPEER_CHAMELEOND_PLATFORM = 'RASPI'


def update_all_btpeers(dut_host: CrosHost,
                       raise_error: bool = False,
                       force_update: bool = False,
                       prod_config: bool = True):
    """
    Update the chameleond on all btpeer devices of the given host.

    @param dut_host: the DUT, usually a Chromebook
    @param raise_error: Set this to True to raise an error if any
            exception is thrown by _update_all_btpeers, or leave False
            to just log it and continue.
    @param force_update: Set this to True to always update the btpeer,
            even if is already on the correct version.
    @param prod_config: The GCS_PROD_CONFIG_FILE is used for the
            chameleond config if True, otherwise GCS_TEST_CONFIG_FILE is
            used.

    @returns: True if _update_all_peers success
            False if raise_error=False and _update_all_peers failed

    @raise error.TestFail: when raise_error=True and _update_all_btpeers
            raises any exception
    """
    try:
        _update_all_btpeers(dut_host, force_update, prod_config)
    except Exception as e:
        err_msg = f'Failed to update all btpeers: {str(e)}'
        if raise_error:
            raise error.TestFail(err_msg) from e
        logging.error(err_msg)
        logging.exception(e)
        return False
    return True


def _update_all_btpeers(dut_host: CrosHost,
                        force_update=False,
                        prod_config: bool = True):
    """
    Update the chameleond on all btpeer devices of the given host.
    """
    logging.info(f'Updating all btpeers (force_update={str(force_update)}, '
                 f'prod_config={str(prod_config)})')

    # Skip update if there are no btpeers.
    btpeers = dut_host.btpeer_list
    if len(btpeers) == 0:
        logging.info('No btpeers found, skipping update of btpeers')
        # No btpeers to update.
        return

    # Identify DUT hostname and ChromeOS version.
    logging.info('Identifying dut hostname and release version')
    if not hasattr(dut_host, 'hostname'):
        raise Exception('dut_host missing hostname')
    dut_hostname = dut_host.hostname.rstrip('.cros')
    dut_cros_release_version = str(dut_host.get_release_version())

    # Identify which chameleond bundle to use for btpeers.
    logging.info('Identifying which chameleond bundle to use for btpeers with '
                 f'dut hostname "{dut_hostname}" and '
                 f'release version "{dut_cros_release_version}"')
    btpeer_config = fetch_config(
            GCS_PROD_CONFIG_FILE if prod_config else GCS_TEST_CONFIG_FILE)
    chameleond_bundle_config = select_bundle_for_dut(btpeer_config,
                                                     dut_hostname,
                                                     dut_cros_release_version)
    logging.info('Identified chameleond bundle with chameleond commit '
                 f'"{chameleond_bundle_config.chameleond_commit}" '
                 'as the bundle to use for btpeers')

    # Identify btpeers that do not match expected bundle and need to be
    # updated.
    btpeers_to_update = []
    logging.info(f'Identifying which of the {len(btpeers)} btpeers need to be'
                 ' updated')
    if force_update:
        logging.info('Btpeer force_update is true, selecting all btpeers for '
                     'updating')
        btpeers_to_update.extend(btpeers)
    else:
        for btpeer in btpeers:
            btpeer_chameleond_commit = btpeer.get_bt_commit_hash()
            if (chameleond_bundle_config.chameleond_commit !=
                        btpeer_chameleond_commit):
                btpeers_to_update.append(btpeer)
                logging.info(f'Selected btpeer "{btpeer.host.hostname}" for '
                             'updating, has mismatched chameleond commit '
                             f'"{btpeer_chameleond_commit}"')
            else:
                logging.info(f'Skipping update of btpeer '
                             f'"{btpeer.host.hostname}", has matching '
                             f'chameleond commit "{btpeer_chameleond_commit}"')
        if len(btpeers_to_update) == 0:
            # No btpeers to update.
            logging.info('No btpeers selected for updating, skipping update '
                         'of btpeers')
            return
    btpeers_to_update_str = ', '.join(
            map(lambda b: f'"{b.host.hostname}"', btpeers_to_update))
    logging.info(f'Identified the following {len(btpeers_to_update)} btpeers '
                 f'to update: {btpeers_to_update_str}')

    # Prepare clean local temp dir for bundle download.
    utils.run(f"[ ! -e '{BTPEER_CHAMELEOND_INSTALL_TMP_DIR}' ] "
              f"|| rm -r '{BTPEER_CHAMELEOND_INSTALL_TMP_DIR}'")
    utils.run(f"mkdir -p '{BTPEER_CHAMELEOND_INSTALL_TMP_DIR}'")

    # Download bundle locally in preparation to send to btpeers.
    chameleond_bundle_filename = (
            chameleond_bundle_config.archive_path.split("/")[-1])
    chameleond_bundle_local_file_path = os.path.join(
            BTPEER_CHAMELEOND_INSTALL_TMP_DIR, chameleond_bundle_filename)
    logging.info('Downloading chameleond bundle archive from '
                 f'"{chameleond_bundle_config.archive_path}" to '
                 f'"{chameleond_bundle_local_file_path}"')
    download_google_cloud_file(chameleond_bundle_config.archive_path,
                               chameleond_bundle_local_file_path)

    # Update btpeers that need to be updated.
    for btpeer in btpeers_to_update:
        logging.info(f'Updating btpeer "{btpeer.host.hostname}" to chameleond '
                     f'commit "{chameleond_bundle_config.chameleond_commit}"')
        try:
            update_btpeer(btpeer, chameleond_bundle_local_file_path)
            btpeer_chameleond_commit = btpeer.get_bt_commit_hash()
            if (chameleond_bundle_config.chameleond_commit !=
                        btpeer_chameleond_commit):
                raise Exception(
                        'Btpeer chameleond commit '
                        f'"{btpeer_chameleond_commit}" '
                        'does not match expected chameleond commit '
                        f'"{chameleond_bundle_config.chameleond_commit}" '
                        'after update')
        except Exception as e:
            raise Exception(f'Failed to update btpeer '
                            f'"{btpeer.host.hostname}"') from e
        logging.info(f'Successfully updated btpeer "{btpeer.host.hostname}" '
                     f'to chameleond commit "{btpeer_chameleond_commit}"')

    # Delete local temp dir.
    utils.run(f"rm -r '{BTPEER_CHAMELEOND_INSTALL_TMP_DIR}'")

    logging.info(f'Successfully the following {len(btpeers_to_update)} '
                 f'btpeers: {btpeers_to_update_str}')


def update_btpeer(btpeer: ChameleonBoard,
                  chameleond_bundle_local_file_path: str):
    """
    Updates a single btpeer with the given chameleond bundle.
    """
    if btpeer.get_platform() != BTPEER_CHAMELEOND_PLATFORM:
        raise Exception('Unsupported btpeer chameleond platform '
                        f'"{btpeer.get_platform()}"')

    # Create a fresh temporary directory on the btpeer for install.
    btpeer.host.run(f"[ ! -e '{BTPEER_CHAMELEOND_INSTALL_TMP_DIR}' ] "
                    f"|| rm -r '{BTPEER_CHAMELEOND_INSTALL_TMP_DIR}'")
    btpeer.host.run(f"mkdir -p '{BTPEER_CHAMELEOND_INSTALL_TMP_DIR}'")

    # Copy bundle to btpeer from local system.
    chameleond_bundle_btpeer_file_path = (
            f'{BTPEER_CHAMELEOND_INSTALL_TMP_DIR}/'
            f'{os.path.basename(chameleond_bundle_local_file_path)}')
    btpeer.host.send_file(chameleond_bundle_local_file_path,
                          chameleond_bundle_btpeer_file_path)

    # Extract bundle and preform update on btpeer.
    host_now = datetime.strftime(datetime.now(), '%Y-%m-%d %H:%M:%S')
    chameleond_make_install_args = [
            'REMOTE_INSTALL=TRUE', f'HOST_NOW="{host_now}"',
            f'BUNDLE_VERSION={BUNDLE_VERSION}',
            f'CHAMELEON_BOARD={CHAMELEON_BOARD}', 'NEEDS_SYSTEM_UPDATE=TRUE',
            'PY_VERSION=python3'
    ]
    btpeer.host.run(f"cd '{BTPEER_CHAMELEOND_INSTALL_TMP_DIR}' && "
                    f"tar zxf '{chameleond_bundle_btpeer_file_path}' && "
                    f"cd \"$(find -mindepth 1 -maxdepth 1 -type d)\" && "
                    f"make install {' '.join(chameleond_make_install_args)}")

    # Cleanup temporary dir.
    btpeer.host.run(f"rm -r '{BTPEER_CHAMELEOND_INSTALL_TMP_DIR}'")

    # Ensure chameleond is running.
    restart_check_chameleond(btpeer)


def fetch_config(
        gcs_config_file_object_path: str) -> BluetoothPeerChameleondConfig:
    """
    Downloads and parses the specified BluetoothPeerChameleondConfig
    JSON from GCS.
    """
    config_json = read_google_cloud_file(gcs_config_file_object_path)
    config = BluetoothPeerChameleondConfig()
    json_format.Parse(config_json, config)
    return config


def read_google_cloud_file(gcs_file_object_path: str) -> bytes:
    """
    Reads and returns the contents of a file object from Google Cloud
    Storage (GCS).

    The file is downloaded to a temporary file using gsutil and read
    from that file. The temporary file is deleted afterwards.

    @param gcs_file_object_path: The GCS object path of the file to
            read.

    @returns: the contents of the file as bytes
    """
    try:
        with tempfile.NamedTemporaryFile() as tmp_file:
            tmp_filename = tmp_file.name
            download_google_cloud_file(gcs_file_object_path, tmp_filename)
            with open(tmp_filename, mode='rb') as f:
                content_bytes = f.read()
                content_str = content_bytes.decode('utf-8')
                logging.debug(f'Content of GCS file "{gcs_file_object_path}":'
                              f'\n{content_str}')
                return content_bytes
    except Exception as e:
        msg = f'Error in reading GCS file "{gcs_file_object_path}"'
        raise Exception(msg) from e


def download_google_cloud_file(gcs_file_object_path: str, dst_file_path: str):
    """
    Downloads a file from GCS to dst_file_path on the local system using
    gsutil.
    """
    try:
        result = utils.run('gsutil cp '
                           f"'{gcs_file_object_path}' "
                           f"'{dst_file_path}'")
        if result.exit_status != 0:
            raise Exception(
                    f'Downloading of GCS file "{gcs_file_object_path}" '
                    f'with gsutil failed with exit code {result.exit_status}')
    except Exception as e:
        raise Exception('Error in downloading GCS file '
                        f'"{gcs_file_object_path}"') from e


def select_bundle_by_chameleond_commit(
        config: BluetoothPeerChameleondConfig, chameleond_commit: str
) -> BluetoothPeerChameleondConfig.ChameleondBundle:
    """
    Selects the chameleond bundle with a matching chameleond_commit.

    See the proto definition of BluetoothPeerChameleondConfig for more
    details on the chameleond bundle selection process.
    """
    for bundleConfig in config.bundles:
        if bundleConfig.chameleond_commit == chameleond_commit:
            return bundleConfig
    raise Exception('Found no bundle with chameleond_commit '
                    f'"{chameleond_commit}" configured')


def select_bundle_by_next_commit(
        config: BluetoothPeerChameleondConfig
) -> BluetoothPeerChameleondConfig.ChameleondBundle:
    """
    Selects the chameleond bundle with the next chameleond commit.

    See the proto definition of BluetoothPeerChameleondConfig for more
    details on the chameleond bundle selection process.
    """
    if not config.next_chameleond_commit:
        raise Exception('No next bundle configured by next_chameleond_commit')
    return select_bundle_by_chameleond_commit(config,
                                              config.next_chameleond_commit)


def select_bundle_by_cros_release_version(
        config: BluetoothPeerChameleondConfig, dut_cros_release_version: str
) -> BluetoothPeerChameleondConfig.ChameleondBundle:
    """
    Selects the chameleond bundle based on the dut_cros_release_version.

    See the proto definition of BluetoothPeerChameleondConfig for more
    details on the chameleond bundle selection process.
    """
    # Collect all bundles with min versions less than or equal to dut version
    matching_versions = []
    bundle_version_to_config = {}
    for bundleConfig in config.bundles:
        if bundleConfig.chameleond_commit == config.next_chameleond_commit:
            # Ignore the next bundle
            continue
        if is_chromeos_release_version_greater_or_equal(
                dut_cros_release_version,
                bundleConfig.min_dut_release_version):
            matching_versions.append(bundleConfig.min_dut_release_version)
            bundle_version_to_config[
                    bundleConfig.min_dut_release_version] = bundleConfig
    if len(matching_versions) == 0:
        raise Exception(f'None of the {len(config.bundles)} bundles '
                        'configured have a min_dut_release_version greater '
                        f'than or equal to "{dut_cros_release_version}"')

    # Sort matching versions and select the highest.
    matching_versions.sort(
            key=functools.cmp_to_key(compare_chromeos_release_version),
            reverse=True)
    return bundle_version_to_config[matching_versions[0]]


def select_bundle_for_dut(
        config: BluetoothPeerChameleondConfig, dut_hostname: str,
        dut_cros_release_version: str
) -> BluetoothPeerChameleondConfig.ChameleondBundle:
    """
    Selects the chameleond bundle based on the dut_hostname and
    dut_cros_release_version.

    See the proto definition of BluetoothPeerChameleondConfig for more
    details on the chameleond bundle selection process.
    """
    if (
            config.next_chameleond_commit is not None
            and config.next_chameleond_commit != ""
            and dut_hostname in config.next_dut_hosts
            and dut_cros_release_version in config.next_dut_release_versions):
        return select_bundle_by_next_commit(config)
    return select_bundle_by_cros_release_version(config,
                                                 dut_cros_release_version)


def is_chromeos_release_version_greater_or_equal(versionA: str,
                                                 versionB: str) -> bool:
    """
    Check if versionA is greater or equal to the versionB.
    """
    versionA = [int(key) if key else 0 for key in versionA.split('.')]
    versionB = [int(key) if key else 0 for key in versionB.split('.')]
    for key1, key2 in zip(versionA, versionB):
        if key1 > key2:
            return True
        elif key1 == key2:
            continue
        else:
            return False
    return True


def compare_chromeos_release_version(versionA: str, versionB: str) -> int:
    """
    Compare function for ChromeOS release versions.
    """
    if versionA == versionB:
        return 0
    if is_chromeos_release_version_greater_or_equal(versionA, versionB):
        return 1
    return -1


def restart_check_chameleond(btpeer: ChameleonBoard):
    """
    Restart chameleond and make sure it is running.
    """
    restart_cmd = 'sudo /etc/init.d/chameleond restart'
    start_cmd = 'sudo /etc/init.d/chameleond start'
    status_cmd = 'sudo /etc/init.d/chameleond status'

    # Restart chameleond (or start if restart fails)
    try:
        restart_cmd_result = btpeer.host.run(restart_cmd, ignore_status=True)
        if restart_cmd_result.exit_status != 0:
            btpeer.host.run(start_cmd)
    except Exception as e:
        raise Exception('Failed to restart/start chameleond') from e

    # Wait till chameleond initialization is complete
    time.sleep(5)

    # Check if chameleond is running.
    status_cmd_result = btpeer.host.run(status_cmd)
    if 'chameleond is running' not in status_cmd_result.stdout:
        raise Exception('Chameleond service status check failed')
