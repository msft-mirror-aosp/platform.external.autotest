# Lint as: python2, python3
# Copyright 2023 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import logging

from autotest_lib.client.common_lib import error
from autotest_lib.client.cros.networking import shill_context
from autotest_lib.client.cros.networking import shill_proxy
from autotest_lib.client.cros.update_engine import nebraska_wrapper
from autotest_lib.client.cros.update_engine import update_engine_test


class autoupdate_OverMetered(update_engine_test.UpdateEngineTest):
    """Updates a DUT over metered connection."""

    version = 1

    _IGNORED_OVER_METERED = "66 (ErrorCode::kOmahaUpdateIgnoredOverMetered)"

    class MeteredWiFiContext:
        """The context that enables metered connection"""

        def __init__(self, ssid):
            """Initialize shill proxy"""
            self._proxy = shill_proxy.ShillProxy.get_proxy()
            target_service = {
                shill_proxy.ShillProxy.SERVICE_PROPERTY_TYPE:
                    shill_proxy.ShillProxy.TECHNOLOGY_WIFI,
                shill_proxy.ShillProxy.SERVICE_PROPERTY_NAME: ssid,
            }
            self._service = self._proxy.find_matching_service(target_service)
            if not self._service:
                raise error.TestError(f"Unable to find WiFi {ssid}.")

        def __enter__(self):
            """Setup metered property"""
            try:
                self._proxy.set_dbus_property(
                    self._service,
                    shill_proxy.ShillProxy.SERVICE_PROPERTY_METERED,
                    "true",
                )
            except:
                self.__exit__()
                raise

            if not self._proxy.get_dbus_property(
                self._service, shill_proxy.ShillProxy.SERVICE_PROPERTY_METERED
            ):
                raise error.TestError("Failed to configure metered connection.")

        def __exit__(self, *args):
            """Disable metered property"""
            self._proxy.set_dbus_property(
                self._service,
                shill_proxy.ShillProxy.SERVICE_PROPERTY_METERED,
                "false",
            )
            logging.info("Restored metered property to false.")

    def run_once(
        self, payload_url, wifi_ssid, public_key=None, interactive=True
    ):
        """Runs an update over metered connection using Nebraska.

        Args:
            payload_url: Path to a payload on Google storage.
            wifi_ssid: The SSID of WiFi network to setup metered property.
            public_key: The public key to serve to the update client.
            interactive: Whether the update is interactive or not.
        """
        with nebraska_wrapper.NebraskaWrapper(
            log_dir=self.resultsdir,
            payload_url=payload_url,
            public_key=public_key,
        ) as nebraska, self.MeteredWiFiContext(
            wifi_ssid,
        ), shill_context.AllowedTechnologiesContext(
            [shill_proxy.ShillProxy.TECHNOLOGY_WIFI],
        ):
            try:
                self._check_for_update(
                    nebraska.get_update_url(),
                    critical_update=True,
                    wait_for_completion=True,
                    interactive=interactive,
                )

                # Should not reach here, since an `_IGNORED_OVER_METERED` error
                # is expected.
                raise error.TestFail(
                    "Failed to block update over metered connection."
                )
            except error.CmdError:
                err = self._get_last_error_string()
                if err != self._IGNORED_OVER_METERED:
                    raise
                logging.info("Update blocked over metered connection.")
