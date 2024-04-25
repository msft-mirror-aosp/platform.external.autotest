# Lint as:python3
# Copyright 2023 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Class to access the Floss Logger interface."""

from autotest_lib.client.cros.bluetooth.floss.utils import glib_call


class FlossLogger:
    """Handles method calls from the logger interface."""
    LOGGER_SERVICE = 'org.chromium.bluetooth'
    LOGGER_INTERFACE = 'org.chromium.bluetooth.Logging'
    LOGGER_OBJ_PATH_PATTERN = '/org/chromium/bluetooth/hci{}/logging'

    def __init__(self, bus, hci, api_version):
        """Constructs the logger client.

        @param bus: D-Bus bus over which we'll establish connections.
        @param hci: HCI adapter index. Get this value from `get_default_adapter`
                    on FlossManagerClient.
        @param api_version: The Floss API version.
        """
        self.bus = bus
        self.hci = hci
        self.objpath = self.LOGGER_OBJ_PATH_PATTERN.format(hci)
        self.api_version = api_version

    def proxy(self):
        """Gets proxy object to Logger interface for method calls."""
        return self.bus.get(self.LOGGER_SERVICE,
                            self.objpath)[self.LOGGER_INTERFACE]

    @glib_call(None)
    def is_debug_enabled(self):
        """Checks if debug is enabled.

        @return: True on success, False on failure, None on DBus error.
        """
        return self.proxy().IsDebugEnabled()

    @glib_call(False)
    def set_debug_logging(self, enable):
        """Sets debug logging enabled or disabled.

        @param enable: Enable or disable debug logging.

        @return: True on success, False otherwise.
        """
        self.proxy().SetDebugLogging(enable)
        return True

    @glib_call(False)
    def has_proxy(self):
        """Checks whether logger proxy can be acquired."""
        return bool(self.proxy())
