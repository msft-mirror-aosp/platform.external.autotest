# Copyright 2023 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import json
import logging
import re

from autotest_lib.client.bin import test
from autotest_lib.client.bin import utils
from autotest_lib.client.common_lib import error


class fwupd_FirmwareUpdate(test.test):
    """Tests that the firmware of a device can be upgraded.

    After a successful run, the device will be upgraded to the latest
    release published in the default fwupd remotes.
    """
    version = 1

    def get_devices(self):
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

    def device_match_id(self, dev, dev_id):
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

    def check_device(self, dev_id, devices):
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
            if self.device_match_id(d, dev_id):
                dev_name = d.get('Name', 'Unknown Device')
                if 'Flags' not in d:
                    raise error.TestError(f"Device {dev_id} ({dev_name}) "
                                          "has no 'Flags' attribute")
                if 'updatable' in d['Flags']:
                    return d
                else:
                    raise error.TestError(f"Device {dev_id} ({dev_name}) "
                                          "is not updatable")
        raise error.TestError(f"Device {dev_id} not found")

    def get_fwupdmgr_version(self):
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
        except error.CmdError as e:
            logging.error("fwupd not running, not found or broken")
            logging.error(e)
            return None
        try:
            versions = json.loads(output)
            for v in versions.get('Versions', []):
                if (v.get('AppstreamId') == 'org.freedesktop.fwupd' and
                    v.get('Type')        == 'runtime'):
                    return v.get('Version')
        except json.decoder.JSONDecodeError:
            # fallback: json output not supported, parse stdout
            m = re.search("client version:\s+([\d.]+)", output)
            if m:
                return m.group(1)
        logging.error("Error parsing fwupd version info")
        logging.error(output)
        return None

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
        devices = self.get_devices()
        dev_pre = self.check_device(device_id, devices)
        dev_name = dev_pre.get('Name', 'Unknown Device')
        if 'Releases' not in dev_pre:
            raise error.TestError("No FW releases found for "
                                  f"{device_id} ({dev_name})")
        if 'Version' not in dev_pre:
            raise error.TestError(f"Device {device_id} ({dev_name}) has "
                                  "no FW version info")
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
        # Verify that the device FW version has changed
        devices = self.get_devices()
        dev_post = self.check_device(device_id, devices)
        if 'Version' not in dev_post:
            raise error.TestError(f"Device {device_id} ({dev_name}) has "
                                  "no FW version info")
        if dev_post['Version'] == dev_pre['Version']:
            raise error.TestFail("Error updating firmware for device "
                                 f"{device_id} ({dev_name}): "
                                 "the FW release version hasn't changed "
                                 f"({dev_post['Version']})")

    def run_once(self, device_id):
        """Update a device FW and check the result.

        Runs the test on the device specified by device_id. The
        parameter is mandatory, it's a test error to run this without
        specifying a device.  The device_id can be either the instance
        id of the device or any of its GUIDs.

        Fails if fwupd is not working properly.
        """
        if not device_id:
            raise error.TestError("No device id specified (test argument: device_id)")
        if not self.get_fwupdmgr_version():
            raise error.TestError("Error checking fwupd status")
        self.update_firmware(device_id)
