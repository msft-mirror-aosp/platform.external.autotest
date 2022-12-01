# Lint as: python2, python3
# Copyright 2018 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from autotest_lib.server.cros.update_engine import update_engine_test

class autoupdate_OmahaResponse(update_engine_test.UpdateEngineTest):
    """
    This server test is used just to get the URL of the payload to use. It
    will then call into a client side test to test different things in
    the omaha response (e.g switching between two urls, bad hash, bad SHA256).
    """
    version = 1

    def cleanup(self):
        """Cleans up after the test."""
        super(autoupdate_OmahaResponse, self).cleanup()
        self._host.reboot()

    def run_once(self,
                 full_payload=True,
                 switch_urls=False,
                 bad_sha256=False,
                 bad_metadata_size=False,
                 test_backoff=False,
                 backoff=False,
                 running_at_desk=False,
                 build=None):
        """
        Runs the Omaha response test. This test can be configured to respond
        to an update client in variaty of ways.

        @param full_payload: True if the payload should be full.
        @param switch_urls: True if we want to test URL switch capability of
            update_engine.
        @param bad_sha256: True if the response should have invalid SHA256.
        @param bad_metadata_size: True if the response should have invalid
            metadta size.
        @param test_backoff: True if we want to test the backoff functionality.
        @param backoff: Whether the backoff is enabled or not.
        @param running_at_desk: True if the test is being run locally.
        @param build: An optional parameter to specify the target build for the
                      update when running locally. If no build is supplied, the
                      current version on the DUT will be used.

        """
        # Reboot DUT if a previous test left update_engine not idle.
        if not self._is_update_engine_idle():
            self._host.reboot()

        payload_url = self.get_payload_for_nebraska(
                build=build,
                full_payload=full_payload,
                public_bucket=running_at_desk)

        if switch_urls:
            self._run_client_test_and_check_result('autoupdate_UrlSwitch',
                                                   payload_url=payload_url)

        if bad_sha256 or bad_metadata_size:
            self._run_client_test_and_check_result(
                'autoupdate_BadMetadata',
                payload_url=payload_url,
                bad_metadata_size=bad_metadata_size,
                bad_sha256=bad_sha256)

        if test_backoff:
            self._run_client_test_and_check_result('autoupdate_Backoff',
                                                   payload_url=payload_url,
                                                   backoff=backoff)
