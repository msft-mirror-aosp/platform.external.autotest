# Lint as:python3
# Copyright 2024 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Client class to access the Floss telephony interface."""
from autotest_lib.client.cros.bluetooth.floss.utils import (glib_call)


class FlossTelephonyClient(object):
    """Handles method calls and callbacks from the Telephony client interface."""

    TELEPHONY_SERVICE = "org.chromium.bluetooth"
    TELEPHONY_INTERFACE = "org.chromium.bluetooth.BluetoothTelephony"
    TELEPHONY_OBJECT_PATTERN = "/org/chromium/bluetooth/hci{}/telephony"

    def __init__(self, bus, hci, api_version):
        """Constructs the client.

        @param bus: D-Bus bus over which we'll establish connections.
        @param hci: HCI adapter index. Get this value from 'get_default_adapter'
                    on FlossManagerClient.
        @param api_version: The Floss API version.
        """
        self.bus = bus
        self.hci = hci
        self.objpath = self.TELEPHONY_OBJECT_PATTERN.format(hci)
        self.api_version = api_version

        # We don't register callbacks by default.
        self.callbacks = None

    def __del__(self):
        """Destructor"""
        del self.callbacks

    @glib_call(False)
    def has_proxy(self):
        """Checks whether the telephony proxy is present."""
        return bool(self.proxy())

    def proxy(self):
        """Gets a proxy object to telephony interface for method calls."""
        return self.bus.get(self.TELEPHONY_SERVICE,
                            self.objpath)[self.TELEPHONY_INTERFACE]

    @glib_call(False)
    def set_phone_ops_enabled(self, enable):
        """Set bluetooth telephony flag in floss.

        @return: always True if no error raise

        """
        self.proxy().SetPhoneOpsEnabled(enable)
        return True
