# Copyright 2023 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import logging
import re

from autotest_lib.client.bin import test
from autotest_lib.client.bin import utils
from autotest_lib.client.common_lib import error
from autotest_lib.client.common_lib.cros import fwupd
from distutils.version import LooseVersion


class fwupd_FirmwareInstallVersion(test.test):
    """Tests that a device's firmware can be updated to a specific version.

    After a successful run, the device will be running the specified
    firmware version.
    """
    version = 1

    def install_firmware(self, device_id, version):
        """Installs a specific firmware version in a device.

        Args:
          device_id: the id of the device to update (string). It can be
              an fwupd instance id or a GUID
          version: the version string of the fw release to install

        Raises:
          error.TestError if there aren't any available fw releases for
              the device in the default fwupd remotes or if there was
              any problem getting the FW downgrades info.
          error.TestFail if there was an error flashing the device FW or
              if the reported device FW version after the update is
              different than the specified version
        """
        devices = fwupd.get_devices()
        dev_pre = fwupd.check_device(device_id, devices)
        dev_name = dev_pre.get('Name', 'Unknown Device')
        if 'Releases' not in dev_pre:
            raise error.TestError("No FW releases found for "
                                  f"{device_id} ({dev_name})")
        release = None
        for r in dev_pre['Releases']:
            if 'Version' not in r:
                raise error.TestError(f"No version info in FW release: {r}")
            if r['Version'] == version:
                release = r
                break
        if not release:
            raise error.TestError(f"Device {device_id} ({dev_name}) has "
                                  f"no firmware release {version} available")
        try:
            # The format of the 'install' command changed on fwupdmgr
            # 1.8.0, the older version needs a file path (or URI)
            # instead of a version string and it doesn't support json
            # output.
            if LooseVersion(self.fwupd_version) >= LooseVersion('1.8.0'):
                output = utils.system_output(
                        "fwupdmgr install --json --assume-yes "
                        f"{device_id} {version}")
            else:
                fw = release['Uri']
                output = utils.system_output(
                        "fwupdmgr install --allow-older "
                        f"--allow-reinstall {fw} {device_id}")
        except error.CmdError as e:
            raise error.TestFail(e)
        if not re.search("Successfully installed firmware", output):
            raise error.TestFail(
                    f"Error installing firmware release {version} "
                    f"on {device_id} ({dev_name}): {output}")
        logging.info("Firmware flashing: done")
        # Verify that the device FW version has changed
        devices = fwupd.get_devices()
        dev_post = fwupd.check_device(device_id, devices)
        if dev_post['Version'] != version:
            raise error.TestFail(
                    f"Error installing firmware release {version} "
                    f"on {device_id} ({dev_name}): "
                    f"Current FW version: {dev_post['Version']}")

    def run_once(self, device_id, version, cert_id):
        """Install a FW version in a device FW and check the result.

        Args:
          device_id: the instance id of the device or any of its GUIDs (string)
          version: version string of the FW release to install, as
              specified in the release
          cert_id: the serial ID of the certificate for reports signing

        Fails if fwupd is not working properly.
        """
        if not device_id:
            raise error.TestError(
                    "No device id specified (test argument: device_id)")
        if not version:
            raise error.TestError(
                    "No FW version specified (test argument: version)")
        self.fwupd_version = fwupd.get_fwupdmgr_version()
        if not self.fwupd_version:
            raise error.TestError("Error checking fwupd status")
        fwupd.ensure_remotes()
        fwupd.ensure_certificate(cert_id)
        self.install_firmware(device_id, version)
