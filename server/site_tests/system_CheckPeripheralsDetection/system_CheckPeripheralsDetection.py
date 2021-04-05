# Copyright 2021 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import logging
import os
import re
import time

from autotest_lib.client.common_lib import error
from autotest_lib.client.cros import liststorage
from autotest_lib.client.cros.graphics import graphics_utils
from autotest_lib.server import test


class system_CheckPeripheralsDetection(test.test):
    """
    Shut down the device gracefully via Linux shell commands, then simulate
    a power button press and verify that it comes back up correctly. Also,
    checks peripherals detection
    """
    version = 1

    # Allowed timeout (in seconds) for graceful shutdown.
    TIMEOUT_POWEROFF_TRANSITION = 15

    # EC reset command
    EC_RESET_CMD = 'ectool reboot_ec cold at-shutdown'
    # Shutdown command
    SHUTDOWN_CMD = 'shutdown -h now'

    # Time to sleep (in seconds) to ensure full power off, after OS quits
    # replying to pings
    WAIT_TIME_FULL_POWEROFF = 5

    INFO_PATH = '/sys/block'
    SD_MODEL_NAME = 'STORAGE_DEVICE'
    BCDUSB_DICT = {
        '2.1': [2.0, 2.1],
        '2.0': [2.0, 2.1],
        '3.0': [3.0],
        '3.1': [3.1]

    }

    # USB devices that needs to be connected to chromebook
    USB_DEVICES = ['USB_2.0', 'USB_3.0', 'SD_CARD']

    # String constants are that used to identify different USB devices
    USB_HDD = 'USB_HDD_'
    USB = 'USB_'

    def cleanup(self):
        logging.info("Autotest cleanup")
            # If the chromebook is not pingable within 60 seconds, press the
            # servo power button
        for try_to_boot in range(2):
            if not self.host.is_up():
                logging.info("Bootup the DUT by pressing power button")
                self.host.servo.power_normal_press()
        if try_to_boot == 1 and not self.host.is_up():
            logging.warning("Not able to boot the DUT by pressing power button")

    def cold_boot(self):
        """ Perform cold boot of the AP by executing the EC_RESET_CMD command"""
        boot_id = self.host.get_boot_id()
        # The EC_RESET_CMD will ensure to boot the dut again once it reaches
        # S5 state
        logging.info("Executing %s command", self.EC_RESET_CMD)
        self.host.run(self.EC_RESET_CMD)
        logging.info("Executing %s command", self.SHUTDOWN_CMD)
        self.host.run(self.SHUTDOWN_CMD)
        self.host.test_wait_for_boot(boot_id)

    def get_sd_card_info(self, host=None):
        """Returns SD card info

        @param host: Host object of the DUT
        @returns: a list of SD card related info
        """
        self.sd_card_info = []
        def _find_partition(dev, blockdev, basename):
            # When the basename ends with the letter p followed by
            # a number, we know that it's a partition
            # E.g. If dev is mmcblk0 it's partition will be mmcblk0p1
            if re.match("%sp[0-9]+" % dev, basename):
                partition_path = "%s/%s" % (blockdev, basename)
                logging.info("Partition path: %s " % partition_path)
                return partition_path
            return None

        def _check_for_partition(dev):
            has_partition = False
            blockdev = os.path.join(self.INFO_PATH, dev)
            device_type_path = os.path.join(blockdev, 'device/type')
            if not host.path_exists(device_type_path):
                return
            if not liststorage.read_file(device_type_path, host).strip() == 'SD':
                return
            # Search through all the directories in blockdev location
            # and see if there are any partitions in the SD Card.
            for basename in liststorage.system_output(
                            'ls %s' % blockdev, host).splitlines():
                _partition = _find_partition(dev, blockdev, basename)
                if not _partition:
                    continue
                self.sd_card_info.append(liststorage.get_udev_info(
                        os.path.join('/dev', basename), host=host))
                has_partition = True
            if not has_partition:
                self.sd_card_info.append(
                        liststorage.get_udev_info(
                                os.path.join('/dev', dev), host=host))

        for dev in liststorage.system_output('ls %s' % self.INFO_PATH,
                                             host).splitlines():
            _check_for_partition(dev)
        # If SD card block not found then it might be detected as /dev/sd*
        # so iterating through the removable devices
        if not self.sd_card_info:
            expected_match = self.SD_MODEL_NAME
            devices = liststorage.get_all(host)
            for device in devices:
                try:
                    if device['model'] == expected_match:
                        self.sd_card_info.append(device)
                except Exception as e:
                    logging.error("No sd card found from /dev/sd* %s" % e)

        return self.sd_card_info

    def get_usbs(self, usb_type, host=None):
        """Gets the list of usb_devices of specific type

        @param usb_type: USB device type e.g. USB_2.0, USB_3.0
        @param host: Host object of the DUT
        """
        usb_info = self.get_removable_devices(host)
        logging.debug("Available removable devices:")
        logging.debug(usb_info)
        usb_devices = []
        if self.USB_HDD in usb_type or self.USB in usb_type:
            # Get the USB version number e.g. 2.0, 3.10
            usb_version = float(usb_type.split('_')[-1])
            # For each and every removal device, check if the usb_type is of
            # the required USB version and append to usb_devices
            for device in usb_info:
                if self.USB in usb_type:
                    if float(device['usb_type']) in self.BCDUSB_DICT[str(usb_version)]:
                        usb_devices.append(device)
                if self.USB_HDD in usb_type:
                    if float(device['usb_type']) in self.BCDUSB_DICT[
                        str(usb_type)] and device['fstype'] == 'fuseblk':
                        usb_devices.append(device)
        elif usb_type == 'SD_CARD':
            sd_card_info = self.get_sd_card_info(host)
            logging.debug('SD Card info %s', sd_card_info)
            if sd_card_info:
                usb_devices.append(sd_card_info[0])
        return usb_devices

    def get_removable_devices(self, host=None):
        removable_devices = []
        devices = liststorage.get_all(host)
        for device in devices:
            if device['is_removable'] and device['model'] != self.SD_MODEL_NAME:
                removable_devices.append(device)
        return removable_devices

    def run_once(self, host, iteration_count=1, action='cold_boot'):
        self.host = host
        self.errors = []

        for iteration in range(1, iteration_count + 1):
            if action.lower() == 'cold_boot':
                logging.info("====Cold boot iteration %d/%d====", iteration,
                             iteration_count)
                self.cold_boot()
            elif action.lower() == 'suspend_resume':
                logging.info("====Suspend resume iteration %d/%d====",
                             iteration, iteration_count)
                self.host.suspend(suspend_time=10)
            else:
                raise error.TestError(
                    "No implementation for the given action. provide either " \
                    "cold_boot or suspend_resume")
            for device in self.USB_DEVICES:
                try:
                    usb = self.get_usbs(device, self.host)
                    logging.info('%s devices are: %s', device, usb)
                    if not usb:
                        self.errors.append(
                            '%s is not detected during %d iteration' % (
                            device, iteration))
                except Exception as e:
                    logging.debug('lsusb -t output is :%s',
                                  self.host.run_output('lsusb -t'))
                    self.errors.append(
                        '%s is not properly detected during %d iteration' % (
                        device, iteration))
            hdmi = graphics_utils.get_external_connector_name()
            logging.info('Is HDMI connected: %s', hdmi)
            if not hdmi:
                self.errors.append(
                    'HDMI is not detected during %d iteration' % iteration)
        if self.errors:
            raise error.TestFail(';'.join(set(self.errors)))

