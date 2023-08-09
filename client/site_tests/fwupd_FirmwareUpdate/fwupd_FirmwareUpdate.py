# Copyright 2023 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import logging
import re

from autotest_lib.client.bin import test
from autotest_lib.client.bin import utils
from autotest_lib.client.common_lib import error
from autotest_lib.client.common_lib.cros import fwupd


class fwupd_FirmwareUpdate(test.test):
    """Tests that the firmware of a device can be upgraded.

    After a successful run, the device will be upgraded to the latest
    release published in the default fwupd remotes.
    """
    version = 1

    def update_firmware(self, device_id):
        """Updates the FW release of a device to its latest version.

        Args:
          device_id: the id of the device to update (string). It can be
              an fwupd instance id or a GUID

        Raises:
          error.TestError if there aren't any FW releases for the device
              in the default fwupd remotes or if the device is already
              running the latest FW version.
          error.TestFail if there was an error updating the device FW or
              if the reported FW version is the same after the update.
        """
        devices = fwupd.get_devices()
        dev_pre = fwupd.check_device(device_id, devices)
        dev_name = dev_pre.get('Name', 'Unknown Device')
        if 'Releases' not in dev_pre:
            raise error.TestError("No FW releases found for "
                                  f"{device_id} ({dev_name})")
        if dev_pre['Version'] == dev_pre['Releases'][0]['Version']:
            raise error.TestError(f"Device {device_id} ({dev_name}) "
                                  "already at latest FW release")
        try:
            cmd = f"fwupdmgr update {device_id} --json"
            output = utils.system_output(cmd)
        except error.CmdError as e:
            raise error.TestFail(e)
        # TBD: Proper testing of all corner cases
        if not re.search("Successfully installed firmware", output):
            raise error.TestFail("Error updating firmware for device "
                                 f"{device_id} ({dev_name}): {output}")
        logging.info("Firmware flashing: done")

        # Verify that the device FW version has changed
        devices = fwupd.get_devices()
        dev_post = fwupd.check_device(device_id, devices)
        if dev_post['Version'] == dev_pre['Version']:
            raise error.TestFail("Error updating firmware for device "
                                 f"{device_id} ({dev_name}): "
                                 "the FW release version hasn't changed "
                                 f"({dev_post['Version']})")

    def run_once(self, device_id, cert_id):
        """Update a device FW and check the result.

        Runs the test on the device specified by device_id. The
        parameter is mandatory, it's a test error to run this without
        specifying a device.  The device_id can be either the instance
        id of the device or any of its GUIDs.

        Fails if fwupd is not working properly.
        """
        if not device_id:
            raise error.TestError(
                    "No device id specified (test argument: device_id)")
        if not fwupd.get_fwupdmgr_version():
            raise error.TestError("Error checking fwupd status")
        fwupd.ensure_remotes()
        fwupd.ensure_certificate(cert_id)
        self.update_firmware(device_id)
