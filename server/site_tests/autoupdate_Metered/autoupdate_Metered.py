# Lint as: python2, python3
# Copyright 2023 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from autotest_lib.client.common_lib import error
from autotest_lib.client.common_lib.cros import kernel_utils
from autotest_lib.client.common_lib.cros.network import xmlrpc_datatypes
from autotest_lib.client.common_lib.cros.network import xmlrpc_security_types
from autotest_lib.server.cros.network import hostap_config
from autotest_lib.server.cros.network import wifi_test_context_manager
from autotest_lib.server.cros.update_engine import update_engine_test


class autoupdate_Metered(update_engine_test.UpdateEngineTest):
    """Performs an AU over metered connection using Nebraska."""

    version = 1

    def initialize(self, host, *args, **kwargs):
        super(autoupdate_Metered, self).initialize(host)
        self._wifi_context = None
        self._wifi_ssid = None

    def warmup(self, host, **kwargs):
        super(autoupdate_Metered, self).warmup()
        self._setup_ap_config()
        self._setup_wifi_context(host, **kwargs)
        self._connect_wifi_network()
        self._cleanup_update_engine_prefs()

    def cleanup(self):
        super(autoupdate_Metered, self).cleanup()
        self._cleanup_update_engine_prefs()

    def _cleanup_update_engine_prefs(self):
        """Remove all prefs so update-engine gets to a clean state"""
        try:
            self._stop_update_engine()
            self._remove_update_engine_pref('*')
        finally:
            self._start_update_engine()

    def _setup_ap_config(self):
        wpa_config = xmlrpc_security_types.WPAConfig(
                psk='auto_update',
                wpa_mode=xmlrpc_security_types.WPAConfig.MODE_PURE_WPA2,
                wpa2_ciphers=[xmlrpc_security_types.WPAConfig.CIPHER_CCMP])
        self._ap_config = hostap_config.HostapConfig(
                frequency=2412,
                mode=hostap_config.HostapConfig.MODE_11G,
                security_config=wpa_config)

    def _setup_wifi_context(self, host, **kwargs):
        self._wifi_context = wifi_test_context_manager.WiFiTestContextManager(
                self.__class__.__name__, host, kwargs, self.debugdir)
        self._wifi_context.setup(include_pcap=False, include_attenuator=False)

    def _connect_wifi_network(self):
        if not self._ap_config:
            raise error.TestError("Wi-Fi AP configuration is required.")
        if not self._wifi_context:
            raise error.TestError("Wi-Fi context is required.")

        # Connect to Wi-Fi.
        self._wifi_context.configure(self._ap_config)
        self._wifi_ssid = self._wifi_context.router.get_ssid()
        assoc_params = xmlrpc_datatypes.AssociationParameters(
                ssid= self._wifi_ssid,
                security_config=self._ap_config.security_config)
        self._wifi_context.assert_connect_wifi(assoc_params)

    def run_once(self, full_payload, build=None, running_at_desk=False):
        """
        Performs a N-to-N autoupdate over metered connection with Nebraska.

        @param full_payload: True for full payload, False for delta
        @param build: An optional parameter to specify the target build for the
                      update when running locally. If no build is supplied, the
                      current version on the DUT will be used. In the lab, the
                      job_repo_url from the host attributes will override this.
        @param running_at_desk: Indicates test is run locally from workstation.

        """
        # Get a payload to use for the test.
        payload_url = self.get_payload_for_nebraska(
                build=build,
                full_payload=full_payload,
                public_bucket=running_at_desk,
        )

        # Record DUT state before the update.
        active, _ = kernel_utils.get_kernel_state(self._host)

        # Perform the update.
        self._run_client_test_and_check_result('autoupdate_OverMetered',
                                               payload_url=payload_url,
                                               wifi_ssid=self._wifi_ssid)

        # Reboot and verify boot slot is unchanged.
        self._host.reboot()
        kernel_utils.verify_boot_expectations(active, host=self._host)
