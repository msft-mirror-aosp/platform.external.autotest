# Lint as: python2, python3
# Copyright (c) 2023 The Chromium OS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Host object for OpenWrt devices.

Host customization provided for fine-tuning autotest reset, verification,
and provisioning on OpenWrt devices.
"""

import logging
import re

import common
from autotest_lib.client.common_lib import error
from autotest_lib.server.hosts import ssh_host

OS_TYPE_OPENWRT = 'openwrt'


class OpenWrtHost(ssh_host.SSHHost):
    """OpenWrt-specific host class."""

    @staticmethod
    def check_host(host, timeout=10):
        """
        Check if the given host is OpenWrt host.

        @param host: An ssh host representing a device.
        @param timeout: The timeout for the run command.

        @return: True if the host is a OpenWrt device, otherwise False.
        """
        try:
            device_info_manufacturer = host.run(
                    'test -f /etc/device_info && '
                    'grep DEVICE_MANUFACTURER /etc/device_info').stdout
            match = re.match("(?m)^DEVICE_MANUFACTURER='OpenWrt'$",
                             device_info_manufacturer)
            return True if match else False

        except (error.AutoservRunError, error.AutoservSSHTimeout):
            return False

    def _initialize(self, *args, **dargs):
        logging.info('Initializing OpenWrt host')
        super(OpenWrtHost, self)._initialize(*args, **dargs)

    def get_os_type(self):
        return OS_TYPE_OPENWRT
