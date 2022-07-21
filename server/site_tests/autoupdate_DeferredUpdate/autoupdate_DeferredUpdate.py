# Lint as: python2, python3
# Copyright 2022 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import logging

from autotest_lib.client.common_lib import error
from autotest_lib.client.common_lib.cros import kernel_utils
from autotest_lib.server.cros.update_engine import update_engine_test


class autoupdate_DeferredUpdate(update_engine_test.UpdateEngineTest):
    """Verify deferred updates by update_engine."""
    version = 1

    def initialize(self, host, *args, **kwargs):
        """Initialize the test."""
        super(autoupdate_DeferredUpdate, self).initialize(host)
        self.deep_cleanup()

    def cleanup(self):
        """Clean up after testing."""
        self.deep_cleanup()
        super(autoupdate_DeferredUpdate, self).cleanup()

    def deep_cleanup(self):
        """Deep cleanup of all states created during test."""
        # Disable deferred updates, currently deferred updates are guarded by
        # consumer auto update feature.
        self._set_feature(feature_name=self._CONSUMER_AUTO_UPDATE_FEATURE,
                          enable=True)
        # Remove all prefs so update-engine gets to a clean state.
        try:
            self._stop_update_engine()
            self._remove_update_engine_pref('*')
        finally:
            self._start_update_engine()

    def run_once(self,
                 periodic_interval=5,
                 full_payload=True,
                 running_at_desk=False,
                 build=None):
        """
        Runs the deferred update check test.

        @param periodic_interval: Seconds between each periodic update check.
        @param full_payload: True for full payload. False for delta.
        @param running_at_desk: True if the test is being run locally.
        @param build: An optional parameter to specify the target build for the
                      update when running locally. If no build is supplied, the
                      current version on the DUT will be used.

        """

        # Get a payload to use for the test.
        payload_url = self.get_payload_for_nebraska(
                full_payload=full_payload,
                public_bucket=running_at_desk,
                build=build)

        # Record kernel state before any updates.
        active, inactive = kernel_utils.get_kernel_state(self._host)

        # Enable deferred updates, currently deferred updates are guarded by
        # consumer auto update feature.
        self._set_feature(feature_name=self._CONSUMER_AUTO_UPDATE_FEATURE,
                          enable=False)

        # Sanity check to see that trying to apply a deferred update won't work.
        try:
            self._apply_deferred_update()
        except:
            logging.info('Deferred update did not apply as expected.')
        else:
            raise error.TestFail('Deferred update should not have applied.')

        # Check that the periodic update checks are activated and fire.
        self._run_client_test_and_check_result(
                'autoupdate_PeriodicCheck',
                payload_url=payload_url,
                periodic_interval=periodic_interval,
                check_kernel_after_update=False)

        # Verify the update completed successfully.
        self._host.reboot()
        rootfs_hostlog, _ = self._create_hostlog_files(
                ignore_event_rootfs=False)
        self.verify_update_events(self._CUSTOM_LSB_VERSION, rootfs_hostlog)

        # Deferred updates will *always* reboot into the active slot, until
        # applied action.
        kernel_utils.verify_boot_expectations(active, host=self._host)

        # Check the update_engine status before applying deferred update.
        if self._is_update_deferred():
            logging.info('Deferred update is on hold.')
        else:
            raise error.TestFail('Deferred update is not on hold.')

        # Apply the deferred update.
        self._apply_deferred_update()

        # Wait for DUT to restart + apply the deferred update.
        self._wait_for_update_to_idle()

        # Verity the slot switch.
        kernel_utils.verify_boot_expectations(inactive, host=self._host)
