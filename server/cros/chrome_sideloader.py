# Copyright 2021 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import base64
import json
import logging
import os
import random
import re
import requests
import stat
import string
import sys
import tempfile
import zipfile

from autotest_lib.client.bin import utils
from autotest_lib.client.common_lib import error
from autotest_lib.client.common_lib import utils as common_utils
from autotest_lib.client.common_lib.cros import dev_server


# Shell command to force unmount a mount point if it is mounted
FORCED_UMOUNT_DIR_IF_MOUNTPOINT_CMD = (
    'if mountpoint -q %(dir)s; then umount -l %(dir)s; fi')
# Shell command to set exec and suid flags
SET_MOUNT_FLAGS_CMD = 'mount -o remount,exec,suid %s'
# Shell command to send SIGHUP to dbus daemon
DBUS_RELOAD_COMMAND = 'killall -HUP dbus-daemon'
# Shell command to restore SELinux context of sideloaded files
RESTORECON_COMMAND = 'restorecon -R %s'

# Lacros artifact path mask
_LACROS_PATH_MASK = 'gs://chrome-unsigned/desktop-5c0tCh/{version}/{variant}/lacros.zip'
# Architecture to Lacros variant dictionary
_ARCH_LACROS_VARIANT_DICT = {
    'arm': 'lacros-arm32',
    'arm64': 'lacros-arm64',
    'i386': 'lacros64',
    'x86_64': 'lacros64'
}
# Architecture to Lacros platform dictionary
_ARCH_LACROS_PLATFORM_DICT = {
    'arm': 'lacros_arm32',
    'arm64': 'lacros_arm64',
    'i386': 'lacros',
    'x86_64': 'lacros'
}


def extract_from_image(host, image_name, dest_dir):
    """
    Extracts contents of an image to a directory.

    @param host: The DUT to execute the command on
    @param image_name: Name of image
    @param dest_dir: directory where contents of image will be placed.

    """

    if not host.path_exists('/var/lib/imageloader/%s' % image_name):
        raise Exception('Image %s not found on host %s' % (image_name, host))

    image_mount_point = '/tmp/image_%s' % _gen_random_str(8)

    # Create directories from scratch
    host.run(['rm', '-rf', dest_dir])
    host.run(['mkdir', '-p', '--mode', '0755', dest_dir, image_mount_point])

    try:
        # Mount image and copy content to the destination directory
        host.run([
            'imageloader', '--mount',
            '--mount_component=%s' % image_name,
            '--mount_point=%s' % image_mount_point
        ])

        host.run(['cp', '-r', '%s/*' % image_mount_point, '%s/' % dest_dir])
    except Exception as e:
        raise Exception(
            'Error extracting content from image %s on host %s ' %
            (image_name, host), e)
    finally:
        # Unmount image and remove the temporary directory
        host.run([
            'imageloader', '--unmount',
            '--mount_point=%s' % image_mount_point
        ])
        host.run(['rm', '-rf', image_mount_point])


def remove_image(host, image_name):
    """
    Removes an image from the host.

    @param host: The DUT to execute the command on
    @param image_name: Name of image
    """
    image_path = '/var/lib/imageloader/%s' % image_name
    if host.path_exists(image_path):
        host.run(['rm', '-rf', image_path])


def _gen_random_str(length):
    """
    Generate random string

    @param length: Length of the string

    @return random string of specified length

    """
    return ''.join(
        [random.choice(string.hexdigits) for _ in range(length)])


def _stop_chrome_if_necessary(host):
    """
    Stops chrome if it is running.

    @param host: The DUT to execute the command on

    @return True if chrome was stopped. False otherwise.

    """
    status = host.run_output('status ui')
    if 'start' in status:
        return host.run('stop ui', ignore_status=True).exit_status == 0

    return False


def _mount_lacros(host, chrome_dir, lacros_mount_point):
    """
    Mounts lacros chrome to a mount point

    A mutation of _mount_chrome, but lacros does not require
    mount command. We only move it to the specified path.

    @param host: The DUT to execute the command on
    @param chrome_dir: directory where the lacros binary and artifacts
                       was provisioned.
    @param chrome_mount_point: The path that lacros is expected to exist.

    """
    host.run(['rm', '-rf', lacros_mount_point])
    host.run(['mkdir', '-p', '--mode', '0755', lacros_mount_point])
    host.run(['mv', '%s/*' % chrome_dir, '%s/' % lacros_mount_point])


def _log_chrome_version(host):
    """
    Log the chrome version.

    @param host: The DUT to execute the command on

    """
    host.run(['/opt/google/chrome/chrome', '--version'])


def _mount_chrome(host, chrome_dir, chrome_mount_point):
    """
    Mounts chrome to a mount point

    @param host: The DUT to execute the command on
    @param chrome_dir: directory where the chrome binary and artifacts
                       will be placed.
    @param chrome_mount_point: Chrome mount point

    """
    logging.debug('Before mounting chrome on host: %s', host)
    _log_chrome_version(host)

    chrome_stopped = _stop_chrome_if_necessary(host)
    _umount_chrome(host, chrome_mount_point)

    # Mount chrome to the desired chrome directory
    # Upon restart, this version of chrome will be used instead.
    host.run(['mount', '--rbind', chrome_dir, chrome_mount_point])

    # Chrome needs partition to have exec and suid flags set
    host.run(SET_MOUNT_FLAGS_CMD % chrome_mount_point)

    # Restore SELinux context of sideloaded files.
    host.run(RESTORECON_COMMAND % chrome_mount_point)

    # Send SIGHUP to dbus-daemon to tell it to reload its configs. This won't
    # pick up major changes (bus type, logging, etc.), but all we care about is
    # getting the latest policy from /opt/google/chrome/dbus so that Chrome will
    # be authorized to take ownership of its service names.
    host.run(DBUS_RELOAD_COMMAND, ignore_status=True)

    if chrome_stopped:
        host.run('start ui', ignore_status=True)

    logging.debug('After mounting chrome on host: %s', host)
    _log_chrome_version(host)


def _umount_lacros(host, lacros_mount_point):
    """
    Unmounts lacros

    Because lacros does not require "mount", so we just remove its
    path. See _mount_lacros.

    @param host: The DUT to execute the command on
    @param lacros_mount_point: See _mount_lacros.

    """
    host.run(['rm', '-rf', lacros_mount_point])


def _umount_chrome(host, chrome_mount_point):
    """
    Unmounts chrome

    @param host: The DUT to execute the command on
    @param chrome_mount_point: Chrome mount point

    """
    logging.debug('Before unmounting chrome on host: %s', host)
    _log_chrome_version(host)

    chrome_stopped = _stop_chrome_if_necessary(host)
    # Unmount chrome. Upon restart, the default version of chrome
    # under the root partition will be used.
    try:
        host.run(FORCED_UMOUNT_DIR_IF_MOUNTPOINT_CMD %
                 {'dir': chrome_mount_point})
    except Exception as e:
        raise Exception('Exception during cleanup on host %s' % host, e)

    if chrome_stopped:
        host.run('start ui', ignore_status=True)

    logging.info('After unmounting chrome on host: %s', host)
    _log_chrome_version(host)


def setup_host(host, chrome_dir, chrome_mount_point, is_cros_chrome=True):
    """
    Performs setup on host.

    Mounts chrome to point to the version provisioned by TLS.
    The provisioning mechanism of chrome from the chrome builder is
    based on Lacros Tast Test on Skylab (go/lacros-tast-on-skylab).

    The lacros image provisioned by TLS contains the chrome binary
    and artifacts.

    @param host: The DUT to execute the command on
    @param chrome_dir: directory where the chrome binary and artifacts
                       will be placed.
    @param chrome_mount_point: Chrome mount point
    @is_cros_chrome: Mount cros chrome or lacros. True by default.
    """
    logging.info('Setting up host:%s', host)
    try:
        extract_from_image(host, 'lacros', chrome_dir)
        if chrome_mount_point:
            _mount = _mount_chrome if is_cros_chrome else _mount_lacros
            _mount(host, '%s/out/Release' % chrome_dir, chrome_mount_point)
    except Exception as e:
        raise Exception(
            'Exception while mounting %s on host %s' %
            (chrome_mount_point, host), e)


def cleanup_host(host, chrome_dir, chrome_mount_point, is_cros_chrome=True):
    """
    Umounts chrome and performs cleanup.

    @param host: The DUT to execute the command on
    @param chrome_dir: directory where the chrome binary and artifacts
                       is placed.
    @param chrome_mount_point: Chrome mount point
    @is_cros_chrome: Umount cros chrome or lacros. True by default.
    """
    logging.info('Cleaning up host: %s', host)
    try:
        if chrome_mount_point:
            _umount = _umount_chrome if is_cros_chrome else _umount_lacros
            _umount(host, chrome_mount_point)
        host.run(['rm', '-rf', chrome_dir])
    except Exception as e:
        raise Exception('Exception during cleanup on host %s' % host, e)


def get_tast_expr_from_file(host, args_dict, results_dir, base_path=None):
    """
    Gets Tast expression from argument dictionary using a file.
    If the tast_expr_file and tast_expr_key are in the dictionary returns the
    tast expression from the file. If either/both args are not in the dict,
    None is returned.
    tast_expr_file expects a file containing a json dictionary which it will
    then use tast_expr_key to pull the tast_expr.

    The tast_expr_file is a json file containing a dictionary of names to tast
    expressions like:

    {
    'default': '("group:mainline" && "dep:lacros" && !informational)',
    'tast_disabled_tests_from_lacros_example': '("group:mainline" && "dep:lacros" && !informational && !"name:lacros.Basic")'
    }

    @param host: Host having the provisioned lacros image with the file
    @param args_dict: Argument dictionary
    @param results_dir: Where to store the tast_expr_file from the dut
    @param base_path: Base path of the provisioned folder

    """
    tast_expr_file_name = args_dict.get('tast_expr_file')
    tast_expr_key = args_dict.get('tast_expr_key')
    if tast_expr_file_name and tast_expr_key:
        if base_path:
            tast_expr_file_name = os.path.join(base_path, tast_expr_file_name)

        # Get the tast expr file from the provisioned lacros folder
        if not host.path_exists(tast_expr_file_name):
            raise Exception(
                'tast_expr_file: %s could not be found on the dut' %
                tast_expr_file_name)
        local_file_name = os.path.join(results_dir,
                                       os.path.basename(tast_expr_file_name))
        st = os.stat(results_dir)
        os.chmod(results_dir, st.st_mode | stat.S_IWRITE)
        host.get_file(tast_expr_file_name, local_file_name, delete_dest=True)

        return _get_tast_expr_from_json_file(local_file_name, tast_expr_key)
    elif tast_expr_file_name or tast_expr_file_name:
        raise Exception('Missing tast_expr_file or tast_expr_key')
    return None


def get_tast_expr_from_local_file(args_dict, base_path=None):
    """
    Gets Tast expression from argument dictionary using a file.
    If the tast_expr_file and tast_expr_key are in the dictionary returns the
    tast expression from the file. If either/both args are not in the dict,
    None is returned.
    tast_expr_file expects a file containing a json dictionary which it will
    then use tast_expr_key to pull the tast_expr.

    The tast_expr_file is a json file containing a dictionary of names to tast
    expressions like:

    {
    'default': '("group:mainline" && "dep:lacros" && !informational)',
    'tast_disabled_tests_from_lacros_example': '("group:mainline" && "dep:lacros" && !informational && !"name:lacros.Basic")'
    }

    @param args_dict: Argument dictionary
    @param results_dir: Where to store the tast_expr_file from the dut
    @param base_path: Base path of the provisioned folder

    """
    tast_expr_file_name = args_dict.get('tast_expr_file')
    tast_expr_key = args_dict.get('tast_expr_key')
    if tast_expr_file_name and tast_expr_key:
        if base_path:
            tast_expr_file_name = os.path.join(base_path, tast_expr_file_name)
        return _get_tast_expr_from_json_file(tast_expr_file_name,
                                             tast_expr_key)
    elif tast_expr_file_name or tast_expr_file_name:
        raise Exception('Missing tast_expr_file or tast_expr_key')
    return None


def _get_tast_expr_from_json_file(tast_expr_file_name, tast_expr_key):
    """
    Gets Tast expression from argument dictionary using a file.

    @param tast_expr_file_name: A json file containing a dictionary of names to tast
    expressions.
    @param tast_expr_key: key to pull the tast expression.

    @return: tast expression.
    """
    with open(tast_expr_file_name) as tast_expr_file:
        expr_dict = json.load(tast_expr_file)
        expr = expr_dict.get(tast_expr_key)
        # If both args were provided, the entry is expected in the file
        if not expr:
            raise Exception('tast_expr_key: %s could not be found' %
                            tast_expr_key)
        logging.info('tast_expr retrieved from:%s', tast_expr_file)
        return expr


def get_test_args(args_dict, expr_key):
    """Extract an arg or decode its b64 hash from args_dict."""
    expr = args_dict.get(expr_key)
    if expr:
        return expr

    expr_b64 = args_dict.get('{}_b64'.format(expr_key))
    if expr_b64:
        return base64.b64decode(expr_b64).decode()
    return None


def get_tast_expr(args_dict):
    """
    Gets Tast expression from argument dictionary.
    Users have options of using tast_expr or tast_expr_b64 in dictionary.
    tast_expr_b64 expects a base64 encoded tast_expr, for instance:
      tast_expr = '("group:mainline" && "dep:lacros")'
      tast_expr_b64 = base64.b64encode(s.encode('utf-8')).decode('ascii')

    @param args_dict: Argument dictionary

    """
    exception_msg = """
    Tast expression is unspecified: set tast_expr or tast_expr_b64 in --args.
    Example: test_that --args="tast_expr=lacros.Basic"
    If the expression contains spaces, consider transforming it to
    base64 and passing it via tast_expr_b64 flag.
    Example:
      In Python:
        tast_expr = '("group:mainline" && "dep:lacros")'
        # Yields "KCJncm91cDptYWlubGluZSIgJiYgImRlcDpsYWNyb3MiKQ=="
        tast_expr_b64 = base64.b64encode(s.encode("utf-8")).decode("ascii")
      Then in Autotest CLI:
        test_that --args="tast_expr_b64=KCJncm91cDptYWlubGluZSIgJiYgImRlcDpsYWNyb3MiKQ=="
    More details at go/lacros-on-skylab.
    """
    res = get_test_args(args_dict, 'tast_expr')
    assert res is not None, exception_msg
    return res


def _lookup_lacros_variant(arch):
    """
    Looks up the Lacros variant for the hardware architecture.

    @param arch: Hardware architecture of the machine

    @return: Lacros variant. e.g. lacros-arm32, lacros-arm64, lacros64
    """
    if arch not in _ARCH_LACROS_VARIANT_DICT:
        raise Exception(
            'Failed to find Lacros variant due to unknown architecture: %s' % arch)

    return _ARCH_LACROS_VARIANT_DICT[arch]


def _lookup_lacros_platform(arch):
    """
    Looks up the Lacros platform for the hardware architecture.

    @param arch: Hardware architecture of the machine

    @return: Lacros platform. e.g. 'lacros_arm32', 'lacros_arm64', 'lacros'
    """
    if arch not in _ARCH_LACROS_PLATFORM_DICT:
        raise Exception(
            'Failed to find Lacros platform due to unknown architecture: %s' % arch)

    return _ARCH_LACROS_PLATFORM_DICT[arch]


def _lookup_lacros_path(host, channel):
    """
    Looks up the Lacros artifact path.

    @param host: The DUT to execute the command on
    @param channel: The lacros channel. e.g. 'stable','beta','dev'

    @return: Lacros variant. e.g. 'lacros-arm32', 'lacros64'
    """
    arch = utils.get_arch_userspace(host.run)
    variant = _lookup_lacros_variant(arch)
    platform = _lookup_lacros_platform(arch)
    logging.info('Host uses Lacros variant: %s platform: %s',
                 variant, platform)

    version = _lookup_lacros_latest_version(channel, platform)
    logging.info('Latest Lacros version for channel %s platform %s : %s',
                 channel, platform, version)

    gs_path = _LACROS_PATH_MASK.format(version=version, variant=variant)
    return gs_path, version, variant


def _lookup_lacros_latest_version(channel, platform):
    """
    Looks up the latest Lacros version for a channel.

    @param channel: Lacros channel. e.g. 'stable','beta','dev'
    @param platform: Lacros platform. e.g. 'lacros_arm32', 'lacros_arm64', 'lacros'

    @return: Latest Lacros version
    """
    # Retrieve latest version of all channels
    api_url = 'https://versionhistory.googleapis.com/v1/chrome/platforms/%s/channels/all/versions/all/releases?filter=endtime=none' % platform
    try:
        res = requests.get(api_url)
    except requests.exceptions.RequestException as e:
        raise Exception('Failed when call versionhistory api.') from e

    release_prefix = 'chrome/platforms/%s/channels/%s/' % (platform, channel)
    json_object = json.loads(res.text)

    versions = [r['version'] for r in json_object['releases']
                if r['name'].startswith(release_prefix)]
    if len(versions) < 1:
        raise Exception(
            'Failed to extract latest version for channel %s from json: %s' % (channel, res.text))
    if len(versions) > 1:
        logging.info(
            "VersionHistory API returns more than 1 version: %s", versions)

    # key function to turn version string into list of integers so that
    # entries can be compared and sorted
    # E.g. "104.0.5112.86" to [104,0,5112,86]
    def key_func(version):
        ret = list(map(int, version.split('.')))
        return ret
    sorted_versions = sorted(versions, key=key_func, reverse=True)

    return sorted_versions[0]


def deploy_lacros(host,
                  channel=None,
                  gs_path=None,
                  lacros_dir='/usr/local/lacros-chrome',
                  args_dict={}):
    """
    Deploys Lacros to DUT.

    Users can either specify channel or gs_path.

    @param channel: The Lacros channel. e.g. 'stable','beta','dev'
    @param gs_path: The GCS path of the Lacros artifacts.
    @param lacros_dir: The directory for Lacros artifacts.
    @param args_dict: Additional argument dictionary.
    """
    if not lacros_dir:
        raise Exception('Failed to specify Lacros directory.')

    logging.info('deploy_lacros to host: %s channel: %s gs_path: %s onto %s',
                 host, channel, gs_path, lacros_dir)

    lacros_version = None
    if gs_path:
        pass
    elif channel:
        # lookup lacros artifact path based on channel
        gs_path, lacros_version, _ = _lookup_lacros_path(host, channel)
    else:
        raise Exception(
            'Please specify either channel or gs_path to locate Lacros artifacts.')

    # Create directories from scratch
    tmp_dir = '/tmp/lacros_%s' % _gen_random_str(8)
    host.run(['rm', '-rf', lacros_dir])
    host.run(['mkdir', '-p', '--mode', '0755', lacros_dir, tmp_dir])

    try:
        # Download Lacros zip archive from Cache Server.
        zip_path = download_gs_to_host(host, gs_path, tmp_dir,
                                       args_dict.get('cache_endpoint'))

        # unzip file to Lacros directory
        host.run(['unzip', zip_path, '-d', lacros_dir])

        # if user specifies Lacros artifacts through lacros_gcs_path, lacros_version
        # is retrieved directly from metadata.json
        if not lacros_version:
            result = host.run(
                ['jq', '-r', "'.content.version'", os.path.join(lacros_dir, 'metadata.json')])
            if result.exit_status != 0 or result.stderr:
                raise Exception(
                    'Error getting Lacros version from metadata.json: %s' % result.stderr)
            lacros_version = result.stdout.rstrip()
            if not re.match(r'^\d*\.\d*\.\d*\.\d*$', lacros_version):
                raise Exception(
                    'Incorrect Lacros version format: %s' % lacros_version)

    except Exception as e:
        raise Exception('Error extracting content from %s to %s' %
                        (gs_path, lacros_dir)) from e
    finally:
        host.run(['rm', '-rf', tmp_dir])

    # Write ash_version and lacros_version into keyval to be included in RDB
    keyvals = {}
    ash_version, _ = host.get_chrome_version()
    keyvals['ash_version'] = ash_version
    keyvals['lacros_version'] = lacros_version
    logging.info('deploy_lacros successful. ash_version: %s  lacros_version: %s',
                 ash_version, lacros_version)
    utils.write_keyval(host.job.resultdir, keyvals)


def chromite_deploy_chrome(host, gs_path, archive_type, **kwargs):
    """
    Deploy chrome onto DUT using chromite.
    Chromite is expected to be packaged in the chrome archive.

    @param host: The DUT to execute the command on
    @param gs_path: The GCS file of the chrome archive.
    @param archive_type: The type of archive. e.g. chrome, lacros

    @return: Directory on drone server that contains the unarchived chrome contents
    """
    if not gs_path:
        raise Exception('gs_path is required')

    chrome_dir = tempfile.mkdtemp()
    # Download artifacts onto drone server and unarchive to a temp directory.
    with tempfile.TemporaryDirectory() as tmp_archive_dir:
        archive_file_path = download_gs(gs_path, tmp_archive_dir)
        if os.path.basename(archive_file_path).endswith(".zip"):
            with zipfile.ZipFile(archive_file_path, 'r') as zip_ref:
                zip_ref.extractall(chrome_dir)
        elif os.path.basename(archive_file_path).endswith(".squash"):
            unsquashfs(archive_file_path, chrome_dir)
        else:
            raise Exception('Unsupported file extension: %s' %
                            archive_file_path)

    # change file permissions to allow for script execution
    cmd = ['chmod', '-R', '755', chrome_dir]
    try:
        common_utils.run(cmd, stdout_tee=sys.stdout, stderr_tee=sys.stderr)
    except error.CmdError as e:
        raise Exception('Error changing file permissions', e)

    # Deploy chrome with chromite
    logging.info('Before deploy_chrome')
    _log_chrome_version(host)

    # Changing current working directory to allow chromite to be properly located by wrapper scripts.
    chromite_dir = os.path.join(chrome_dir, 'third_party/chromite')
    if not os.path.isdir(chromite_dir):
        raise Exception(
                'chromite is not packaged in the lacros_gcs_path archive')

    if archive_type == 'chrome':
        board = _remove_prefix(host.get_board(), 'board:')
        cmd = [
                'deploy_chrome', '--force', '--build-dir',
                os.path.join(chrome_dir, 'out/Release/'), '--process-timeout',
                '180', '--device', host.host_port, '--board', board, '--mount',
                '--nostrip'
        ]
    elif archive_type == 'lacros':
        cmd = [
                'deploy_chrome', '--build-dir',
                os.path.join(chrome_dir, 'out/Release/'), '--device',
                host.host_port, '--lacros', '--nostrip', '--force',
                '--skip-modifying-config-file'
        ]
    else:
        raise Exception('Unknown archive_type:%s' % archive_type)

    try:
        common_utils.run(cmd,
                         stdout_tee=sys.stdout,
                         stderr_tee=sys.stderr,
                         timeout=1200,
                         extra_paths=[os.path.join(chromite_dir, 'bin')])
    except error.CmdError as e:
        logging.debug('Error occurred executing chromite.deploy_chrome')
        raise e

    logging.info('After deploy_chrome')
    _log_chrome_version(host)

    return chrome_dir


def _remove_prefix(text, prefix):
    return text[text.startswith(prefix) and len(prefix):]


def download_gs_to_host(host, gs_path, dest_dir, cache_endpoint):
    """
    Download GCS file to host.

    @param host: The DUT to execute the command on
    @param gs_path: The GCS file path.
    @param dest_dir: The directory where the file is copied to.
    @param cache_endpoint: Cache server endpoint.

    @return: The path of the downloaded file on host
    """
    archive_url, bucket, image, file_name = _parse_info_from_gs_path(gs_path)
    download_url = _stage_artifacts_on_dev_server(host.hostname,
                                                  cache_endpoint, archive_url,
                                                  bucket, image, file_name)
    try:
        # Download gs file from Cache Server.
        file_path = os.path.join(dest_dir, file_name)
        host.run(['curl', download_url, '--output', file_path])

    except Exception as e:
        raise Exception('Error downloading cache server content %s to %s' %
                        (download_url, dest_dir)) from e

    return file_path


def download_gs(gs_path, dest_dir):
    """
    Download GCS file to drone server.

    @param gs_path: The GCS file path.
    @param dest_dir: The directory where the file is copied to.

    @return: The path of the downloaded file
    """
    _, _, _, file_name = _parse_info_from_gs_path(gs_path)
    try:
        # Download gs file from Cache Server.
        cmd = [
                'BOTO_CONFIG=', 'gsutil', '-o',
                'Credentials:gs_service_key_file=/creds/service_accounts/skylab-drone.json',
                'cp', gs_path, dest_dir
        ]
        file_path = os.path.join(dest_dir, file_name)
        common_utils.run(cmd,
                         stdout_tee=sys.stdout,
                         stderr_tee=sys.stderr,
                         timeout=1200,
                         extra_paths=['/opt/infra-tools'])

    except Exception as e:
        raise Exception('Error downloading with gsutil from %s to %s' %
                        (gs_path, dest_dir)) from e

    return file_path


def _stage_artifacts_on_dev_server(hostname, cache_endpoint, archive_url,
                                   bucket, image, file_name):
    # Stage artifact onto Cache Server

    logging.info('cache_endpoint: %s', cache_endpoint)
    if cache_endpoint:
        # CFT handles the Cache Server lookup outside of Tauto.
        ds = dev_server.ImageServer('http://%s' % cache_endpoint)
    else:
        # For Non-CFT, Tauto handles Cache Server lookup.
        ds = dev_server.ImageServer.resolve(image, hostname)

    try:
        ds.stage_artifacts(image=image,
                           archive_url=archive_url,
                           files=[file_name])
        download_url = ds.get_staged_file_url(
                file_name, image) + '?gs_bucket={bucket}'.format(bucket=bucket)
    except Exception as e:
        raise Exception('Failed to stage image on Cache Server', e)

    return download_url


def _parse_info_from_gs_path(gs_path):
    # expects gs path format to be gs://{bucket}/{path}/{zipfile}
    matches = re.match('(gs://(.*?)/(.*))/(.*)', gs_path)
    if len(matches.groups()) != 4:
        raise Exception('Failed to extract required parts from gs_path: %s' %
                        gs_path)
    archive_url, bucket, image, file_name = matches.groups()
    return archive_url, bucket, image, file_name


def unsquashfs(file_path, dest_dir):
    """
    Unarchive squashfs file into a directory.

    @param file_path: The path for squashfs archive.
    @param dest_dir: The directory where the file is copied to.
    """
    # Download artifacts onto drone server and unzip to a temp directory.
    with tempfile.TemporaryDirectory() as tmp_squashfs_dir:
        # create ensure-file for squashfs
        ensure_file_path = os.path.join(tmp_squashfs_dir, 'ensure_file.txt')
        with open(ensure_file_path, 'w') as f:
            f.write('infra/3pp/tools/squashfs/linux-amd64 latest\n')
            f.write('infra/3pp/static_libs/libzstd/linux-amd64 latest')

        # download squashfs from cipd
        cmd = [
                'cipd', 'ensure', '-ensure-file', ensure_file_path, '-root',
                tmp_squashfs_dir
        ]
        try:
            common_utils.run(cmd,
                             stdout_tee=sys.stdout,
                             stderr_tee=sys.stderr,
                             extra_paths=['/opt/infra-tools'])
        except error.CmdError as e:
            raise Exception('Error downloading squashfs from CIPD', e)

        # unsquashfs archive into destination directory
        env_dict = {'LD_LIBRARY_PATH': os.path.join(tmp_squashfs_dir, 'lib')}
        cmd = [
                os.path.join(tmp_squashfs_dir, 'squashfs-tools', 'unsquashfs'),
                '-f', '-d', dest_dir, file_path
        ]
        try:
            common_utils.run(cmd,
                             stdout_tee=sys.stdout,
                             stderr_tee=sys.stderr,
                             env=env_dict,
                             extra_paths=['/opt/infra-tools'])
        except error.CmdError as e:
            raise Exception('Error running unsquashfs on %s' % file_path, e)
