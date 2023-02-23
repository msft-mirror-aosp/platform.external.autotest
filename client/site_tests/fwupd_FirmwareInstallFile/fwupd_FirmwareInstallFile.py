# Copyright 2023 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import logging
import os
import shutil
import re
import requests

from autotest_lib.client.bin import test
from autotest_lib.client.bin import utils
from autotest_lib.client.common_lib import error
from autotest_lib.client.common_lib.cros import fwupd
from distutils.version import LooseVersion


EXTERNAL_DRIVE_LABEL = "FWUPDTESTS"
TEMP_FW_DIR          = "/tmp/fwupd_fw"

class fwupd_FirmwareInstallFile(test.test):
    """Tests that a device's firmware can be updated with a specific file.

    After a successful run, the device will be running the specified
    firmware file.
    """
    version = 1

    def copy_file_from_external_storage(self, fwfile):
        """Copies a specified file from an external drive to /tmp.

        The external drive connected to the DUT must have
        label=<EXTERNAL_DRIVE_LABEL> and must contain a file with
        name=<fwfile>. This function copies the file to the /tmp folder
        in the DUT.

        Args:
          fwfile: name of the firmware file contained in the external drive

        Returns:
          If successful, the full path of the copied file to be used by
          fwupdmgr

        Raises:
          error.TestError if anything failed

        """
        def _cleanup():
            utils.system(f'umount {TEMP_FW_DIR}', ignore_status=True)
            shutil.rmtree(TEMP_FW_DIR)

        cmd = f'lsblk -npo NAME,LABEL | grep {EXTERNAL_DRIVE_LABEL}'
        out = utils.system_output(cmd, ignore_status=True)
        # Output is expected to be something like this:
        # <device_file>            <drive_label>
        # Capture the device_file in m.group(1)
        m = re.match(f'([\w/]+)\s+{EXTERNAL_DRIVE_LABEL}', out)
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
                dest = shutil.copy(os.path.join(TEMP_FW_DIR, fwfile),
                                   os.path.join('/tmp', fwfile))
            except FileNotFoundError:
                raise error.TestError(f"File {fwfile} not found in external drive")
            finally:
                _cleanup()
            return dest
        else:
            raise error.TestError("No external drive with label = "
                                  f"{EXTERNAL_DRIVE_LABEL} found.")

    def install_firmware(self, device_id, fwfile):
        """Installs a specific firmware file in a device.

        Args:
          device_id: the id of the device to update (string). It can be
              an fwupd instance id or a GUID
          fwfile: the URL or file name of the fw to install. If a file
              name is provided instead of a full URL, it's assumed to be
              located in an external drive with label=<EXTERNAL_DRIVE_LABEL>.

        Raises:
          error.TestError if the fw file couldn't be found or fetched
          error.TestFail if there was an error flashing the device FW or
              if fwupd detects any other problem during the operation
        """
        devices = fwupd.get_devices()
        dev = fwupd.check_device(device_id, devices)
        dev_name = dev.get('Name', 'Unknown Device')
        if re.match("https?://", fwfile):
            try:
                req = requests.get(fwfile)
                if not req:
                    raise error.TestError(
                            f"Error retrieving fw file {fwfile}: {req}")
            except requests.exceptions.RequestException as e:
                raise error.TestError(e)
        else:
            # Assume a local file name in an external drive (DUT)
            fwfile = self.copy_file_from_external_storage(fwfile)
        # From fwupd version 1.8.0 onwards, the old 'install' command is
        # called 'local-install'
        if LooseVersion(self.fwupd_version) >= LooseVersion('1.8.0'):
            cmd = 'local-install'
        else:
            cmd = 'install'
        try:
            output = utils.system_output("CACHE_DIRECTORY='/var/cache/fwupd' "
                                         f"fwupdmgr {cmd} --json "
                                         "--allow-older --allow-reinstall "
                                         f"{fwfile} {dev['DeviceId']}")
        except error.CmdError as e:
            raise error.TestFail(e)
        if not re.search("Successfully installed firmware", output):
            raise error.TestFail(f"Error installing firmware file {fwfile} "
                                 f"on {device_id} ({dev_name}): {output}")
        logging.info("Firmware flashing: done")

    def run_once(self, device_id, fwfile):
        """Install a FW version in a device FW and check the result.

        Args:
          device_id: the instance id of the device or any of its GUIDs (string)
          fwfile: URL or path of the firmware file to install.

        Fails if fwupd is not working properly.
        """
        if not device_id:
            raise error.TestError(
                    "No device id specified (test argument: device_id)")
        if not fwfile:
            raise error.TestError(
                    "No FW file specified (test argument: fwfile)")
        self.fwupd_version = fwupd.get_fwupdmgr_version()
        if not self.fwupd_version:
            raise error.TestError("Error checking fwupd status")
        self.install_firmware(device_id, fwfile)
