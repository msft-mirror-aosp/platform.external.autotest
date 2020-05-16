# Copyright (c) 2013 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import logging
import os

from autotest_lib.client.common_lib import error
from autotest_lib.client.common_lib.cros import kernel_utils
from autotest_lib.server.cros.update_engine import update_engine_test

POWERWASH_COMMAND = 'safe fast keepimg'
POWERWASH_MARKER_FILE = '/mnt/stateful_partition/factory_install_reset'
STATEFUL_MARKER_FILE = '/mnt/stateful_partition/autoupdate_Rollback_flag'

class autoupdate_Rollback(update_engine_test.UpdateEngineTest):
    """Test that updates the machine and performs rollback."""
    version = 1

    def _powerwash(self):
        """Powerwashes DUT."""
        logging.info('Powerwashing device before rollback.')
        self._host.run('echo car > %s' % STATEFUL_MARKER_FILE)
        self._host.run("echo '%s' > %s" % (POWERWASH_COMMAND,
                                           POWERWASH_MARKER_FILE))
        self._host.reboot()
        marker = self._host.run('[ -e %s ]' % STATEFUL_MARKER_FILE,
                                ignore_status=True, ignore_timeout=True)
        if marker is None or marker.exit_status == 0:
            raise error.TestFail("Powerwash cycle didn't remove the marker "
                                 "file on the stateful partition.")


    def cleanup(self):
        """Clean up states."""
        # Delete rollback-version and rollback-happened pref which are
        # generated during Rollback and Enterprise Rollback.
        # rollback-version is written when update_engine Rollback D-Bus API is
        # called. The existence of rollback-version prevents update_engine to
        # apply payload whose version is the same as rollback-version.
        # rollback-happened is written when update_engine finished Enterprise
        # Rollback operation.
        preserved_prefs_path = ('/mnt/stateful_partition/unencrypted/preserve'
                                '/update_engine/prefs/')
        self._host.run('rm %s %s' %
                      (os.path.join(preserved_prefs_path, 'rollback-version'),
                       os.path.join(preserved_prefs_path, 'rollback-happened')),
                      ignore_status=True)
        # Restart update-engine to pick up new prefs.
        self._host.run('restart update-engine', ignore_status=True)


    def run_once(self, job_repo_url=None, powerwash_before_rollback=False):
        """Runs the test.

        @param job_repo_url: URL to get the image.
        @param powerwash_before_rollback: True if we should rollback before
                                          powerwashing.

        @raise error.TestError if anything went wrong with setting up the test;
               error.TestFail if any part of the test has failed.

        """
        update_url = self.get_update_url_for_test(job_repo_url)
        initial_kernel, updated_kernel = kernel_utils.get_kernel_state(
            self._host)
        logging.info('Initial device state: active kernel %s, '
                     'inactive kernel %s.', initial_kernel, updated_kernel)

        logging.info('Performing an update.')
        self._check_for_update(update_url, wait_for_completion=True)
        kernel_utils.verify_kernel_state_after_update(self._host)
        self._host.reboot()

        # We should be booting from the new partition.
        error_message = 'Failed to set up test by updating DUT.'
        kernel_utils.verify_boot_expectations(self._host, updated_kernel,
                                              error_message)

        if powerwash_before_rollback:
            self._powerwash()

        logging.info('Update verified, initiating rollback.')
        # Powerwash is tested separately from rollback.
        self._rollback(powerwash=False)
        self._host.reboot()

        # We should be back on our initial partition.
        error_message = ('Autoupdate reported that rollback succeeded but we '
                         'did not boot into the correct partition.')
        kernel_utils.verify_boot_expectations(self._host, initial_kernel,
                                              error_message)
        logging.info('We successfully rolled back to initial kernel.')
