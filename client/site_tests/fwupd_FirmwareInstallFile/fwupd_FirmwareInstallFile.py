# Copyright 2023 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import logging
import re
import requests

from autotest_lib.client.bin import test
from autotest_lib.client.bin import utils
from autotest_lib.client.common_lib import error
from autotest_lib.client.common_lib.cros import fwupd
from distutils.version import LooseVersion


class fwupd_FirmwareInstallFile(test.test):
    """Tests that a device's firmware can be updated with a specific file.

    After a successful run, the device will be running the specified
    firmware file.
    """
    version = 1

    def setup(self):
        fwupd.clear_history()

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
            fwfile = fwupd.copy_file_from_external_storage(fwfile, "/tmp")
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

    def run_once(self, device_id, fwfile, cert_id):
        """Install a FW version in a device FW and check the result.

        Args:
          device_id: the instance id of the device or any of its GUIDs (string)
          fwfile: URL or path of the firmware file to install.
          cert_id: the serial ID of the certificate for reports signing.

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
        fwupd.ensure_certificate(cert_id)
        fwupd.get_device_version(device_id)
        try:
            self.install_firmware(device_id, fwfile)
        finally:
            fwupd.get_device_version(device_id)
            fwupd.send_signed_report(cert_id)
