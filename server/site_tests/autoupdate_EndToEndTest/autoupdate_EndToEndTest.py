# Copyright (c) 2012 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import logging
import os

from autotest_lib.client.common_lib import error
from autotest_lib.client.common_lib.cros import dev_server
from autotest_lib.server.cros.update_engine import chromiumos_test_platform
from autotest_lib.server.cros.update_engine import update_engine_test


class autoupdate_EndToEndTest(update_engine_test.UpdateEngineTest):
    """Complete update test between two Chrome OS releases.

    Performs an end-to-end test of updating a ChromeOS device from one version
    to another. The test performs the following steps:

      - Stages the source (full) and target update payloads on a devserver.
      - Installs source image on the DUT (if provided) and reboots to it.
      - Verifies that sign in works correctly on the source image.
      - Installs target image on the DUT and reboots.
      - Does a final update check.
      - Verifies that sign in works correctly on the target image.
      - Returns the hostlogs collected during each update check for
        verification against expected update events.

    This class interacts with several others:
    UpdateEngineTest: base class for comparing expected update events against
                      the events listed in the hostlog.
    UpdateEngineEvent: class representing a single expected update engine event.
    ChromiumOSTestPlatform: A class representing the Chrome OS device we are
                            updating. It has functions for things the DUT can
                            do: get logs, reboot, start update etc

    """
    version = 1

    # Timeout periods, given in seconds.
    _WAIT_FOR_INITIAL_UPDATE_CHECK_SECONDS = 12 * 60
    # TODO(sosa): Investigate why this needs to be so long (this used to be
    # 120 and regressed).
    _WAIT_FOR_DOWNLOAD_STARTED_SECONDS = 4 * 60
    # See https://crbug.com/731214 before changing WAIT_FOR_DOWNLOAD
    _WAIT_FOR_DOWNLOAD_COMPLETED_SECONDS = 20 * 60
    _WAIT_FOR_UPDATE_COMPLETED_SECONDS = 4 * 60
    _WAIT_FOR_UPDATE_CHECK_AFTER_REBOOT_SECONDS = 15 * 60

    _LOGIN_TEST = 'login_LoginSuccess'


    def _stage_payloads_onto_devserver(self, test_conf):
        """Stages payloads that will be used by the test onto the devserver.

        @param test_conf: a dictionary containing payload urls to stage.

        """
        logging.info('Staging images onto autotest devserver (%s)',
                     self._autotest_devserver.url())

        self._stage_payloads(test_conf['source_payload_uri'],
                             test_conf['source_archive_uri'])

        self._stage_payloads(test_conf['target_payload_uri'],
                             test_conf['target_archive_uri'],
                             test_conf['update_type'])


    def _get_hostlog_file(self, filename, identifier):
        """Return the hostlog file location.

        This hostlog file contains the update engine events that were fired
        during the update.

        @param filename: The partial filename to look for.
        @param identifier: A string that is appended to the logfile when it is
                           saved so that multiple files with the same name can
                           be differentiated.

        """
        hostlog = '%s_%s_%s' % (filename, self._host.hostname, identifier)
        file_url = os.path.join(self.job.resultdir,
                                dev_server.AUTO_UPDATE_LOG_DIR,
                                hostlog)
        if os.path.exists(file_url):
            logging.info('Hostlog file to be used for checking update '
                         'steps: %s', file_url)
            return file_url
        raise error.TestFail('Could not find %s' % filename)


    def _verify_active_slot_changed(self, source_active_slot,
                                    target_active_slot, source_release,
                                    target_release):
        """Make sure we're using a different slot after the update."""
        if target_active_slot == source_active_slot:
            err_msg = 'The active image slot did not change after the update.'
            if source_release is None:
                err_msg += (
                    ' The DUT likely rebooted into the old image, which '
                    'probably means that the payload we applied was '
                    'corrupt.')
            elif source_release == target_release:
                err_msg += (' Given that the source and target versions are '
                            'identical, either it (1) rebooted into the '
                            'old image due to a bad payload or (2) we retried '
                            'the update after it failed once and the second '
                            'attempt was written to the original slot.')
            else:
                err_msg += (' This is strange since the DUT reported the '
                            'correct target version. This is probably a system '
                            'bug; check the DUT system log.')
            raise error.TestFail(err_msg)

        logging.info('Target active slot changed as expected: %s',
                     target_active_slot)


    def _verify_version(self, expected, actual):
        """Compares actual and expected versions."""
        if expected != actual:
            err_msg = 'Failed to verify OS version. Expected %s, was %s' % (
                expected, actual)
            logging.error(err_msg)
            raise error.TestFail(err_msg)


    def update_device_without_cros_au_rpc(self, cros_device, payload_uri,
                                          clobber_stateful=False):
        """Updates the device.

        @param cros_device: The device to be updated.
        @param payload_uri: The payload with which the device should be updated.
        @param clobber_stateful: Boolean that determines whether the stateful
                                 of the device should be force updated. By
                                 default, set to False

        @raise error.TestFail if anything goes wrong with the update.

        @return Path to directory where generated hostlog files and nebraska
                logfiles are stored.
        """
        try:
            logs_dir = cros_device.install_version_without_cros_au_rpc(
                payload_uri, clobber_stateful=clobber_stateful)
        except Exception as e:
            logging.error('ERROR: Failed to update device.')
            raise error.TestFail(str(e))
        return logs_dir


    def run_update_test(self, cros_device, test_conf):
        """Runs the update test and checks it succeeded.

        @param cros_device: The device under test.
        @param test_conf: A dictionary containing test configuration values.

        """
        # Record the active root partition.
        source_active_slot = self._host.get_active_boot_slot()
        logging.info('Source active slot: %s', source_active_slot)

        source_release = test_conf['source_release']
        target_release = test_conf['target_release']

        logs_dir = self.update_device_without_cros_au_rpc(
            cros_device, test_conf['target_payload_uri'])
        self._copy_generated_nebraska_logs(logs_dir, 'target')

        file_url = self._get_hostlog_file(self._DEVSERVER_HOSTLOG_ROOTFS,
                                          'target')

        try:
            # Call into base class to compare expected events against hostlog.
            self.verify_update_events(source_release, file_url)
        except update_engine_test.UpdateEngineEventMissing:
            logging.exception('Event missing from target update.')
            raise

        # Device is updated. Check that we are running the expected version.
        if self._host.oobe_triggers_update():
            # If DUT automatically checks for update during OOBE (e.g
            # rialto), this update check fires before the test can get the
            # post-reboot update check. So we just check the version from
            # lsb-release.
            logging.info('Skipping post reboot update check.')
            self._verify_version(target_release, self._get_chromeos_version())
        else:
            # Verify we have a hostlog for the post-reboot update check.
            file_url = self._get_hostlog_file(self._DEVSERVER_HOSTLOG_REBOOT,
                                              'target')

            try:
                # Compare expected events against hostlog.
                self.verify_update_events(source_release, file_url,
                                          target_release)
            except update_engine_test.UpdateEngineEventMissing:
                logging.exception('Event missing from post-reboot check.')
                raise

        target_active_slot = self._host.get_active_boot_slot()
        self._verify_active_slot_changed(source_active_slot,
                                         target_active_slot,
                                         source_release, target_release)

        logging.info('Update successful, test completed')


    def run_once(self, test_conf):
        """Performs a complete auto update test.

        @param test_conf: a dictionary containing test configuration values.

        """
        logging.debug('The test configuration supplied: %s', test_conf)
        self._autotest_devserver = self._get_least_loaded_devserver(test_conf)
        self._stage_payloads_onto_devserver(test_conf)

        # Get an object representing the CrOS DUT.
        cros_device = chromiumos_test_platform.ChromiumOSTestPlatform(
            self._host, self._autotest_devserver, self.job.resultdir)

        # Install source image
        source_payload_uri = test_conf['source_payload_uri']
        if source_payload_uri is not None:
            logs_dir = self.update_device_without_cros_au_rpc(
                cros_device, source_payload_uri, clobber_stateful=True)
            self._copy_generated_nebraska_logs(logs_dir, 'source')
            self._run_client_test_and_check_result(self._LOGIN_TEST,
                                                   tag='source')

        # Start the update to the target image.
        self.run_update_test(cros_device, test_conf)

        # Check we can login after the update.
        self._run_client_test_and_check_result(self._LOGIN_TEST, tag='target')
