# Lint as: python2, python3
# Copyright (c) 2022 The Chromium OS Authors.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import enum
import os

from autotest_lib.client.common_lib import error
from autotest_lib.server import site_linux_system
from autotest_lib.server.cros import dnsname_mangler


class RPiRole(enum.Enum):
    """Possible roles for a RaspberryPi device."""
    HACKRF_RUNNER = 'hackrf_runner'


def build_rpi_hostname(client_hostname=None, rpi_hostname=None):
    """ Builds a hostname for the RaspberryPi from a client hostname.

    @param client_hostname: string hostname of DUT connected to the RaspberryPi.
    @param rpi_hostname: string hostname of the RaspberryPi.
    @return string hostname of the RaspberryPi or None if the hostname
            cannot be inferred from the client hostname.

    """
    if not rpi_hostname and not client_hostname:
        raise error.TestError('Either client_hostname or rpi_hostname must '
                              'be specified to build_rpi_hostname.')

    return dnsname_mangler.get_rpi_addr(client_hostname,
                                        cmdline_override=rpi_hostname)

class LinuxRPi(site_linux_system.LinuxSystem):
    """Linux RaspberryPi support for WiFiTest class."""

    def __init__(self, host, role=''):
        """Build a LinuxRPi.

        @param host Host object representing the remote machine.
        @param role string description of host (e.g. p2p, hackrf_runner).
        """
        # Since the wlan0 interface is needed for WiFi,
        # inherit_interface is set to True
        # to prevent wlan0 from being removed.
        inherit_interface = True
        super(LinuxRPi, self).__init__(host, role, inherit_interface)
        self.__setup()


    def __setup(self):
        """Set up this system.

        Can be used to complete initialization of a RaspberryPi object,
        or to re-establish a good state after a reboot.
        """
        self.setup_logs()


    def close(self):
        """Close global resources held by this system."""
        rpi_log = os.path.join(self.logdir, 'rpi_log')
        self.get_logs(rpi_log)
        super(LinuxRPi, self).close()
