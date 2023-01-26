# Copyright 2023 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import dbus
import logging
import re
from distutils.version import LooseVersion

from autotest_lib.client.bin import test
from autotest_lib.client.bin import utils
from autotest_lib.client.common_lib import error
from autotest_lib.client.common_lib.cros import fwupd


class fwupd_FirmwareDowngrade(test.test):
    """Tests that the firmware of a device can be downgraded.

    After a successful run, the device will be downgrade to the previous
    release published in the default fwupd remotes.
    """
    version = 1

    def downgrade_firmware(self, device_id):
        """Downgrades the FW release of a device to the previous version.

        Args:
          device_id: the id of the device to update (string). It can be
              an fwupd instance id or a GUID

        Raises:
          error.TestError if there aren't any available downgrades for
              the device in the default fwupd remotes or if there was
              any problem getting the FW downgrades info.
          error.TestFail if there was an error downgrading the device FW
              or if the reported FW version is the same after the
              update.
        """
        devices = fwupd.get_devices()
        dev_pre = fwupd.check_device(device_id, devices)
        dev_name = dev_pre.get('Name', 'Unknown Device')
        bus = dbus.SystemBus()
        proxy = bus.get_object("org.freedesktop.fwupd", "/")
        iface = dbus.Interface(proxy, "org.freedesktop.fwupd")
        try:
            downgrades = iface.GetDowngrades(dev_pre['DeviceId'])
            if not downgrades:
                raise error.TestError(
                        "Error fetching downgrades for device "
                        f"{device_id} ({dev_name}): {downgrades}")
        except dbus.DBusException as e:
            raise error.TestError(e)
        if 'Version' not in downgrades[0]:
            raise error.TestError("No version info in downgrade candidate "
                                  f"{downgrades[0]}")
        try:
            # The format of the 'install' command changed on fwupdmgr
            # 1.8.0, the older version needs a file path (or URI)
            # instead of a version string and it doesn't support json
            # output.
            if LooseVersion(self.fwupd_version) >= LooseVersion('1.8.0'):
                fw = str(downgrades[0].get('Version'))
                output = utils.system_output(
                        "fwupdmgr install --json --assume-yes "
                        f"{device_id} {fw}")
            else:
                fw = str(downgrades[0].get('Uri'))
                output = utils.system_output("fwupdmgr install --assume-yes "
                                             f"--allow-older {fw} {device_id}")
        except error.CmdError as e:
            raise error.TestFail(e)
        if not re.search("Successfully installed firmware", output):
            raise error.TestFail("Error downgrading firmware for device "
                                 f"{device_id} ({dev_name}): {output}")
        logging.info("Firmware flashing: done")
        # Verify that the device FW version has changed
        devices = fwupd.get_devices()
        dev_post = fwupd.check_device(device_id, devices)
        if dev_post['Version'] == dev_pre['Version']:
            raise error.TestFail("Error downgrading firmware for device "
                                 f"{device_id} ({dev_name}): "
                                 "the FW release version hasn't changed "
                                 f"({dev_post['Version']})")

    def run_once(self, device_id):
        """Downgrade a device FW and check the result.

        Args:
          device_id: the instance id of the device or any of its GUIDs (string)

        Fails if fwupd is not working properly.
        """
        if not device_id:
            raise error.TestError(
                    "No device id specified (test argument: device_id)")
        self.fwupd_version = fwupd.get_fwupdmgr_version()
        if not self.fwupd_version:
            raise error.TestError("Error checking fwupd status")
        self.downgrade_firmware(device_id)
