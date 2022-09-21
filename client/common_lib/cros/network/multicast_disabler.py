# Lint as: python3
# Copyright 2022 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import logging
import re

from autotest_lib.client.bin import utils
from autotest_lib.client.common_lib.cros.network import interface


class MulticastDisabler(object):
    """Class to disable network multicast."""

    def __init__(self):
        """Initialize instance of class.

        By Default sets an empty set of multicast disabled interfaces.
        """
        self._multicast_disabled_ifaces = set()

    def disable_network_multicast(self):
        """Disable network multicast."""
        logging.debug(
                'Logging networking interface flags before disable multicast.')
        logging.debug(utils.system_output('ifconfig | grep flags'))

        ifaces = [
                iface for iface in interface.get_interfaces()
                if re.match(r'(eth|wlan).*', iface.name)
        ]
        for iface in ifaces:
            if not iface.is_multicast_enabled:
                continue
            iface.disable_multicast()
            self._multicast_disabled_ifaces.add(iface.name)
            # TODO(b/3872508) Run tcpdump to make sure that kernel drop the traffic.

        logging.debug(
                'Logging networking interface flags after disable multicast.')
        logging.debug(utils.system_output('ifconfig | grep flags'))

    def enable_network_multicast(self):
        """Verify that multicast is disabled and enable it."""
        if not self._multicast_disabled_ifaces:
            return

        logging.debug(
                'Logging networking interface flags before enable multicast.')
        logging.debug(utils.system_output('ifconfig | grep flags'))

        ifaces = [
                iface for iface in interface.get_interfaces()
                if iface.name in self._multicast_disabled_ifaces
        ]

        for iface in ifaces:
            if iface.is_multicast_enabled:
                logging.warning('Multicast is not disabled on %s', iface.name)
            iface.enable_multicast()

        self._multicast_disabled_ifaces.clear()

        logging.debug(
                'Logging networking interface flags after enable multicast.')
        logging.debug(utils.system_output('ifconfig | grep flags'))
