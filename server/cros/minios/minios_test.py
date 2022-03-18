# Lint as: python2, python3
# Copyright 2022 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import json
import logging
import os
import time

from autotest_lib.client.common_lib import error
from autotest_lib.server.cros.minios import minios_util
from autotest_lib.server.cros.update_engine import update_engine_test


class MiniOsTest(update_engine_test.UpdateEngineTest):
    """
    Base class that sets up helper objects/functions for NBR tests.

    """

    _MINIOS_CLIENT_CMD = 'minios_client'

    # Period to wait for firmware screen in seconds.
    # Value based on Brya, which is the slowest so far.
    _FIRMWARE_SCREEN_TIMEOUT = 30

    # Number of times to attempt booting into MiniOS.
    _MINIOS_BOOT_MAX_ATTEMPTS = 3

    # Timeout periods, given in seconds.
    _MINIOS_SHUTDOWN_TIMEOUT = 30

    # Number of seconds to wait for the host to boot into MiniOS. Should always
    # be greater than `_FIRMWARE_SCREEN_TIMEOUT`.
    _MINIOS_WAIT_UP_TIME_SECONDS = 120

    # Version reported to OMAHA/NEBRASKA for recovery.
    _RECOVERY_VERSION = '0.0.0.0'

    # Files used by the tests.
    _MINIOS_DEV_IMAGE_DIR = '/usr/local/tmp/stateful/dev_image_new'
    _MINIOS_TEMP_STATEFUL_DIR = '/usr/local/tmp/stateful'

    def initialize(self, host):
        """
        Sets default variables for the test.

        @param host: The DUT we will be running on.

        """
        super(MiniOsTest, self).initialize(host)
        self._nebraska = None

    def cleanup(self):
        """Clean up minios autotests."""
        if self._nebraska:
            self._nebraska.stop()
        super(MiniOsTest, self).cleanup()
        # Make sure to reboot DUT into CroS in case of failures.
        self._host.reboot()

    def _boot_minios(self):
        """Boot the DUT into MiniOS."""
        self._host.servo.boot_in_recovery_mode()
        self._host.test_wait_for_shutdown(self._MINIOS_SHUTDOWN_TIMEOUT)
        logging.info('Waiting for firmware screen')
        time.sleep(self._FIRMWARE_SCREEN_TIMEOUT)

        # Attempt multiple times to boot into MiniOS. If all attempts fail then
        # this is some kind of firmware issue. Since we failed to boot an OS use
        # servo to reset the unit and then report test failure.
        attempts = 0
        minios_is_up = False
        while not minios_is_up and attempts < self._MINIOS_BOOT_MAX_ATTEMPTS:
            # Use Ctrl+R shortcut to boot 'MiniOS
            logging.info('Try to boot MiniOS')
            self._host.servo.ctrl_r()
            minios_is_up = self._host.wait_up(
                    timeout=self._MINIOS_WAIT_UP_TIME_SECONDS,
                    host_is_down=True)
            attempts += 1

        if minios_is_up:
            # If mainfw_type is recovery then we are in MiniOS.
            mainfw_type = self._host.run_output('crossystem mainfw_type')
            if mainfw_type != 'recovery':
                raise error.TestError(
                        'Boot to MiniOS - invalid firmware: %s.' % mainfw_type)
        else:
            # Try to not leave unit on recovery firmware screen.
            self._host.power_cycle()
            raise error.TestError('Boot to MiniOS failed.')

    def _create_minios_hostlog(self):
        """Create the minios hostlog file.

        To ensure the recovery was successful we need to compare the update
        events against expected update events. This function creates the hostlog
        for minios before the recovery reboots the DUT.

        """
        # Check that update logs exist.
        if len(self._get_update_engine_logs()) < 1:
            err_msg = 'update_engine logs are missing. Cannot verify recovery.'
            raise error.TestFail(err_msg)

        # Download the logs instead of reading it over the network since it will
        # disappear after MiniOS reboots the DUT.
        logfile = os.path.join(self.resultsdir, 'minios_update_engine.log')
        self._host.get_file(self._UPDATE_ENGINE_LOG, logfile)
        logfile_content = None
        with open(logfile) as f:
            logfile_content = f.read()
        minios_hostlog = os.path.join(self.resultsdir, 'hostlog_minios')
        with open(minios_hostlog, 'w') as fp:
            # There are four expected hostlog events during recovery.
            extract_logs = self._extract_request_logs(logfile_content)
            json.dump(extract_logs[-4:], fp)
        return minios_hostlog

    def _install_test_dependencies(self, public_bucket=False):
        """
        Install test dependencies from a downloaded stateful archive.

        @param public_bucket: True to download stateful from a public bucket.

        """
        if not self._job_repo_url:
            raise error.TestError('No job repo url set.')

        statefuldev_url = self._stage_stateful(public_bucket)
        logging.info('Installing dependencies from %s', statefuldev_url)

        # Create destination directories.
        install_dirs = ['/usr/local/bin', '/usr/local/lib', '/usr/local/lib64']
        staging_dirs = [
                self._MINIOS_TEMP_STATEFUL_DIR, self._MINIOS_DEV_IMAGE_DIR
        ]
        self._run(['mkdir', '-p'] + staging_dirs + install_dirs)
        # Symlink the install dirs into the staging destination.
        for dir in install_dirs:
            self._run(['ln', '-s', dir, '%s/.' % self._MINIOS_DEV_IMAGE_DIR])

        try:
            self._download_and_extract_stateful(statefuldev_url,
                                                self._MINIOS_TEMP_STATEFUL_DIR,
                                                keep_symlinks=True)
        except error.AutoservRunError as e:
            err_str = 'Failed to install the test dependencies'
            raise error.TestFail('%s: %s' % (err_str, str(e)))

        # Clean-up unused files to save memory.
        self._run(['rm', '-rf', self._MINIOS_TEMP_STATEFUL_DIR])

    def _start_nebraska(self, payload_url=None):
        """
        Initialize and start nebraska on the DUT.

        @param payload_url: The payload to served by nebraska.

        """
        if not self._nebraska:
            self._nebraska = minios_util.NebraskaService(
                    self, self._host, payload_url)
        self._nebraska.start()

    def _verify_reboot(self, old_boot_id):
        """
        Verify that the unit rebooted using the boot_id.

        @param old_boot_id A boot id value obtained before the
                               reboot.

        """
        self._host.test_wait_for_shutdown(self._MINIOS_SHUTDOWN_TIMEOUT)
        self._host.test_wait_for_boot(old_boot_id)
