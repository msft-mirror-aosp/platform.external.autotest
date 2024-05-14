# Copyright 2023 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import json
import logging
import re
import common
import os
import shutil
import stat

from autotest_lib.client.bin import utils
from autotest_lib.client.common_lib import error
from autotest_lib.client.cros import upstart
from cryptography import x509

EXTERNAL_DRIVE_LABEL = "FWUPDTESTS"
TEMP_FW_DIR = "/tmp/fwupd_fw"
PKI_DIR = "/var/lib/fwupd/pki"
CERT_NAME = "client.pem"
PRIVATE_KEY_NAME = "secret.key"


def get_devices():
    """Gets info about all the devices currently detected by fwupd.

    Returns:
      A list of dicts containing the info of all the devices detected

    Raises:
      error.TestError if there was an error running fwupdmgr, if the
      output couldn't be parsed or if there were no devices found.
    """
    try:
        cmd = "fwupdmgr get-devices --json"
        output = utils.system_output(cmd)
    except error.CmdError as e:
        raise error.TestError(e)
    try:
        devices = json.loads(output)
    except json.decoder.JSONDecodeError as e:
        raise error.TestError("Error parsing <fwupdmgr get-devices> "
                              f"output: {e}")
    if 'Devices' not in devices:
        raise error.TestError("No devices found")
    return devices['Devices']


def _device_match_id(dev, dev_id):
    """Checks whether a device matches a device id.

    Args:
      dev: dictionary that defines the device to check. It should be
          one of the devices returned by get_devices()
      dev_id: the device id to match (string). It can be an fwupd
          instance id or a GUID

    Returns:
      True if dev has dev_id as an identifier. False otherwise
    """
    if dev.get('DeviceId') == dev_id:
        return True
    for guid in dev.get('Guid', []):
        if guid == dev_id:
            return True
    return False


def check_device(dev_id, devices):
    """Device sanity check.

    Checks if the device identified by dev_id is in the devices list
    and is updatable.

    Args:
      dev_id: the id of the device to check (string). It can be an
          fwupd instance id or a GUID
      devices: the list of devices returned by get_devices()

    Returns:
      The device identified by dev_id, if it exists in the devices list.

    Raises:
      error.TestError if the device is not found or is not updatable
    """
    for d in devices:
        if _device_match_id(d, dev_id):
            dev_name = d.get('Name', 'Unknown Device')
            if 'DeviceId' not in d:
                raise error.TestError(f"Device {dev_id} ({dev_name}) has "
                                      "no DeviceId")
            if 'Version' not in d:
                raise error.TestError(f"Device {dev_id} ({dev_name}) has "
                                      "no FW version info")
            if 'Flags' not in d:
                raise error.TestError(f"Device {dev_id} ({dev_name}) "
                                      "has no 'Flags' attribute")
            if 'updatable' in d['Flags']:
                return d
            else:
                raise error.TestError(f"Device {dev_id} ({dev_name}) "
                                      "is not updatable")
    raise error.TestError(f"Device {dev_id} not found")


def get_device_version(dev_id):
    """Returns the version of the device

    Args:
      dev_id: the id of the device to check (string). It can be an
          fwupd instance id or a GUID

    Returns:
      A string containing the device version.
    """
    # Verify that the device FW version has changed
    devices = get_devices()
    device = check_device(dev_id, devices)
    logging.debug('Device %s (%s) has version %s', dev_id, device['Name'],
                  str(device['Version']))
    return str(device['Version'])


def get_fwupdmgr_version():
    """Returns the fwupdmgr version as a string

    It can also be used to check whether fwupd (the daemon) is
    running, as fwupdmgr tries to connect to it to get the version
    info.

    Returns:
      A string containing the fwupdmgr version. <None> if fwupdmgr
      failed to run, if it couldn't connect to the daemon or if
      there was a problem fetching and parsing the data. Details are
      logged to the ERROR test log.

    Note:
      For the purposes of this test we don't need to differentiate
      between the daemon and client versions.
    """
    try:
        cmd = "fwupdmgr --version --json"
        output = utils.system_output(cmd)
        logging.debug(output)
    except error.CmdError as e:
        logging.error("fwupd not running, not found or broken")
        logging.error(e)
        return None
    try:
        versions = json.loads(output)
        for v in versions.get('Versions', []):
            if (v.get('AppstreamId') == 'org.freedesktop.fwupd'
                        and v.get('Type') == 'runtime'):
                return v.get('Version')
    except json.decoder.JSONDecodeError:
        # fallback: json output not supported, parse stdout
        m = re.search("client version:\s+([\d.]+)", output)
        if m:
            return m.group(1)
    logging.error("Error parsing fwupd version info")
    logging.error(output)
    return None


def ensure_remotes():
    """
    Enable all downloadable remotes (lvfs, lvfs-testing) -- this is
    needed for accessing CAB files on LVFS.
    Refresh outdated metadata if needed.
    """
    try:
        cmd = "fwupdmgr get-remotes --json"
        output = utils.system_output(cmd)
    except error.CmdError as e:
        raise error.TestError(f"Unable to remount the root"
                              "partition in R/W mode: %s" % e)
    try:
        json_data = json.loads(output)
    except json.decoder.JSONDecodeError as e:
        raise error.TestError(f"Error parsing <fwupdmgr get-remotes> "
                              "output: %s" % e)
    if 'Remotes' not in json_data:
        raise error.TestError("No remotes found")

    remotes = json_data['Remotes']
    for remote in remotes:
        kind = remote.get('Kind')
        if kind != 'download':
            continue

        rid = remote.get('Id')
        enabled = remote.get('Enabled')
        logging.info('Remote %s enabled: %s', rid, enabled)
        if enabled == 'true':
            continue

        orig = remote.get('FilenameSource')
        dest = os.path.join("/var/lib/fwupd/remotes.d/", \
                                'test-' + os.path.basename(orig))
        # Skip copying if already exists
        if (os.path.isfile(dest) or \
            os.path.dirname(orig) == os.path.dirname(dest)):
            continue

        shutil.copyfile(orig, dest)
        logging.info('Enable remote %s in %s', rid, dest)
        try:
            # Can't use `fwupdmgr enable-remote` since
            #`fwupd` is running in jail.
            cmd = "sed -i 's/Enabled=.*/Enabled=true/' " + dest
            output = utils.system_output(cmd)
        except error.CmdError as e:
            raise error.TestError(f"Unable to enable remote %s" % rid)

    # Refresh metadata if any remote has been enabled or have outdated metadata
    try:
        cmd = "fwupdmgr refresh"
        output = utils.system_output(cmd)
    except error.CmdError as e:
        pass

    return None


def copy_file_from_external_storage(filename, dst):
    """Copies a specified file from an external drive to /tmp.

    The external drive connected to the DUT must have
    label=<EXTERNAL_DRIVE_LABEL> and must contain a file with
    name=<filename>. This function copies the file to the <dst> folder
    in the DUT.

    Args:
      filename: name of the file contained in the external drive
      dst: target directory

    Returns:
      If successful, the full path of the copied file to be used by
      fwupdmgr

    Raises:
      error.TestError if anything failed

    """
    def _cleanup():
        utils.system(f'umount {TEMP_FW_DIR}', ignore_status=True)
        shutil.rmtree(TEMP_FW_DIR)

    if not os.path.isdir(dst):
        raise error.TestError(f"The directory {dst} doesn't exist.")

    cmd = f'lsblk -rnpo NAME,LABEL | grep {EXTERNAL_DRIVE_LABEL}'
    out = utils.system_output(cmd, ignore_status=True)
    # Output is expected to be something like this:
    # <device_file>            <drive_label>
    # Capture the device_file in m.group(1)
    m = re.search(f'([\w/]+)\s+{EXTERNAL_DRIVE_LABEL}', out)
    if m:
        # Create a temp mountpoint for the drive, mount it, copy the
        # fw file to /tmp, unmount and clean up
        try:
            os.mkdir(TEMP_FW_DIR)
        except FileNotFoundError:
            raise error.TestError(f"Can't create directory {TEMP_FW_DIR}: "
                                  "Parent directory doesn't exist.")
        except FileExistsError:
            _cleanup()
            os.mkdir(TEMP_FW_DIR)
        utils.system(f'mount {m.group(1)} {TEMP_FW_DIR}')
        try:
            dest = shutil.copyfile(os.path.join(TEMP_FW_DIR, filename),
                                   os.path.join(dst, filename))
        except FileNotFoundError:
            raise error.TestError(
                    f"File {filename} not found in external drive")
        finally:
            _cleanup()
        return dest
    else:
        raise error.TestError("No external drive with label = "
                              f"{EXTERNAL_DRIVE_LABEL} found.")


def ensure_certificate(req_serial=''):
    """Ensures the installed certificate matches serial.

    If serial not passed, skip the check, otherwise check the local certificate.
    Try to copy 'secret.key' and 'client.pem' files from an external drive in case
    if requested certificate's serial is not installed.

    The external drive connected to the DUT must have
    label=<EXTERNAL_DRIVE_LABEL> and must contain files 'secret.key' and 'client.pem'.
    This function copies the file to the <dst> folder in the DUT.

    Args:
      req_serial: requested serial ID in hex format as shown on LVFS.

    Returns:
      True, if serial not required or proper serial found and installed

    Raises:
      error.TestError if anything failed

    """
    def _read_serial():
        with open(os.path.join(PKI_DIR, CERT_NAME), "rb") as f:
            cert = x509.load_pem_x509_certificate(f.read())
            read_serial = '{0:x}'.format(int(cert.serial_number))
            return read_serial

    serial = _read_serial()
    logging.info('fwupd certificate serial ID: %s', serial)

    # Using the existing certificate for reports signing
    if not req_serial:
        return True

    # If already installed the expected cert/key
    if req_serial.lower() == serial.lower():
        return True

    # Try to copy from external drive
    try:
        private_key = copy_file_from_external_storage(PRIVATE_KEY_NAME,
                                                      PKI_DIR)
        cert = copy_file_from_external_storage(CERT_NAME, PKI_DIR)
    except:
        raise error.TestError(f"Put 'secret.key' and 'client.pem' with serial "
                              f"{req_serial} to external drive")

    # Set proper ownership and permissions
    shutil.chown(private_key, "fwupd", "fwupd")
    os.chmod(private_key, stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP)
    shutil.chown(cert, "fwupd", "fwupd")
    os.chmod(cert, stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH)

    serial = _read_serial()
    logging.info('New fwupd certificate installed with serial ID: %s', serial)

    if req_serial.lower() != serial.lower():
        raise error.TestError(
                f"Files 'secret.key' and 'client.pem' from external "
                f"drive have incorrect serial ID {serial}")

    return True


def send_signed_report(req_serial=''):
    """Send signed report.

    Try to sign the report from the successful update and send it to LVFS.
    See https://lvfs.readthedocs.io/en/latest/testing.html?highlight=report#signed-reports
    Certificate ID should be passed explicitly, otherwise the report
    would be skipped.

    Args:
      req_serial: requested serial ID in hex format as shown on LVFS.
    """

    # Omit the report signing if certificate ID not passed explicitly
    if not req_serial:
        logging.info('Skip the signed report sending')
        return None

    # Ignore the result -- should not affect to test
    try:
        cmd = "fwupdmgr report-history --assume-yes --sign --json"
        output = utils.system_output(cmd)
        logging.info('Report sent successfully')
    except Exception as e:
        logging.warning("Unable to sign the report")
        logging.warning(e)

    return None


def clear_history():
    """Clear the results from the previous updates.
    """

    # Ignore the result -- should not affect the test
    try:
        # FIXME: usage of fwupdtool is preferable, however CQ is failing
        # due the tool absence in test environment:
        # fwupdtool clear-history
        # Workaround: remove DB and restart service
        pending_db = '/var/lib/fwupd/pending.db'
        if os.path.isfile(pending_db):
            os.remove(pending_db)
            logging.info('Restarting fwupd')
            upstart.restart_job('fwupd')

        logging.info('History cleared successfully')
    except Exception as e:
        logging.warning('Unable to clear reports history fwupd')
        logging.warning(e)

    return None
