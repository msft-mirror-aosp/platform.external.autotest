# Lint as: python2, python3
# Copyright (c) 2012 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import logging
import os

from autotest_lib.client.common_lib import autotemp
from autotest_lib.client.common_lib import error
from autotest_lib.client.common_lib import utils
from autotest_lib.client.common_lib.cros import kernel_utils
from autotest_lib.client.cros import constants
from autotest_lib.client.cros.update_engine import nebraska_wrapper
from autotest_lib.server.cros.update_engine import update_engine_test


class autoupdate_EndToEndTest(update_engine_test.UpdateEngineTest):
    """Complete update test between two ChromeOS releases.

    Performs an end-to-end test of updating a ChromeOS device from one version
    to another. The test performs the following steps:

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

    """
    version = 1


    def cleanup(self):
        """Save the logs from stateful_partition's preserved/log dir."""
        stateful_preserved_logs = os.path.join(self.resultsdir,
                                               '~stateful_preserved_logs')
        os.makedirs(stateful_preserved_logs)
        self._host.get_file(constants.AUTOUPDATE_PRESERVE_LOG,
                            stateful_preserved_logs, safe_symlinks=True,
                            preserve_perm=False)
        super(autoupdate_EndToEndTest, self).cleanup()


    def _print_rerun_command(self, test_conf):
        """Prints the command to rerun a test run from the lab at your desk."""
        logging.debug('Rerun this test run at your desk using this command:')
        rerun_cmd = ('test_that <DUT NAME>.cros autoupdate_EndToEndTest '
                     '--args="update_type=%s source_release=%s '
                     'source_payload_uri=%s target_release=%s '
                     'target_payload_uri=%s"')
        rerun_cmd = rerun_cmd % (
                test_conf['update_type'], test_conf['source_release'],
                test_conf['source_payload_uri'], test_conf['target_release'],
                test_conf['target_payload_uri'])
        logging.debug(rerun_cmd)

    def run_update_test(self, test_conf, m2n):
        """Runs the update test and checks it succeeded.

        @param test_conf: A dictionary containing test configuration values.
        @param m2n: True for an m2n test run.

        """
        # Record the active root partition.
        active, inactive = kernel_utils.get_kernel_state(self._host)
        logging.info('Source active slot: %s', active)

        source_release = test_conf['source_release']
        target_release = test_conf['target_release']

        if m2n:
            payload_url = test_conf['target_payload_uri']
        else:
            update_parameters = self._get_update_parameters_from_uri(
                    test_conf['target_payload_uri'])
            payload_url = os.path.join(self._get_cache_server_url(), 'static',
                                       update_parameters[0],
                                       update_parameters[1])

        # Perform the update.
        with nebraska_wrapper.NebraskaWrapper(
                host=self._host,
                payload_url=payload_url) as nebraska:
            self._check_for_update(nebraska.get_update_url(),
                                   critical_update=True)
            self._wait_for_update_to_complete()
            nebraska.save_log(self.resultsdir)

        self._host.reboot()

        # Restoring stateful triggers a reboot and creation of another
        # update_engine log, so grab the update_engine events before that.
        rootfs, _ = self._create_hostlog_files(
                rootfs_filename='rootfs_pre_stateful_restore',
                reboot_filename='reboot_pre_stateful_restore')
        self.verify_update_events(source_release, rootfs)

        # Restore stateful in case of any incompatibility between source and
        # target versions.
        logging.info('Restoring stateful partition to target version')
        self._update_stateful()

        # Check that update-engine is ready after reboot. Wait for the UI to
        # come up first, in case there are any FW updates that delay
        # update-engine from starting.
        self._host.wait_for_service('ui')
        utils.poll_for_condition(self._get_update_engine_status,
                                 desc='update engine to start')
        # Do a final update check with no_update=True to get post reboot event.
        with nebraska_wrapper.NebraskaWrapper(
                host=self._host,
                payload_url=payload_url) as nebraska:
            nebraska.update_config(no_update=True)
            self._check_for_update(nebraska.get_update_url())

        # Compare hostlog events from the update to the expected ones.
        _, reboot = self._create_hostlog_files()
        self.verify_update_events(source_release, reboot, target_release)
        kernel_utils.verify_boot_expectations(inactive, host=self._host)
        logging.info('Update successful, test completed')


    def run_once(self, test_conf, m2n=False, build=None,
                 running_at_desk=False):
        """Performs a complete auto update test.

        @param test_conf: a dictionary containing test configuration values.
        @param m2n: M -> N update. This means we install the current stable
                    version of this board before updating to ToT.
        @param build: target build for the update, i.e. R102-14650.0.0. Optional
                      argument for running locally.
        @param running_at_desk: Indicates test is run locally on a DUT which is
                                not in the lab network.

        """
        if m2n:
            if self._host.get_board().endswith("-kernelnext"):
                raise error.TestNAError("Skipping test on kernelnext board")
            # No test_conf is provided, we need to assemble it ourselves for
            # the target update information.
            source_release = self._get_serving_stable_build().rsplit(
                    '/')[-1]
            target_release = build.split(
                    '-')[1] if build else self._host.get_release_version()
            target_uri = self.get_payload_for_nebraska(
                    build=build, public_bucket=running_at_desk)
            test_conf = {
                    'target_release': target_release,
                    'target_payload_uri': target_uri,
                    'source_release': source_release,
                    'source_payload_uri': None
            }

        logging.debug('The test configuration supplied: %s', test_conf)
        if not m2n:
            self._print_rerun_command(test_conf)

        # Copy nebraska from the initially provisioned version to use for the
        # update. We don't want to use the potentially very old nebraska script
        # from the source version.
        temp = autotemp.tempdir()
        temp_nebraska = os.path.join(temp.name, 'nebraska.py')
        self._host.get_file(self._NEBRASKA_PATH, temp_nebraska)

        # Install source image with quick-provision.
        build_name = None
        source_payload_uri = test_conf['source_payload_uri']
        if m2n:
            build_name = self._get_serving_stable_build()
        elif source_payload_uri:
            build_name, _ = self._get_update_parameters_from_uri(
                source_payload_uri)

        if build_name is not None:
            # Install the matching build with quick provision.
            self.provision_dut(build_name=build_name,
                               public_bucket=running_at_desk)
            try:
                self._run(['python', '--version'])
            except error.AutoservRunError as e:
                # TODO(b/261782079): Remove this once provisioning between
                # certain versions is fixed and doesn't trigger repairs that
                # wipe the stateful partition. For now, provision again in to
                # ensure the DUT is in a good state for testing.
                logging.warning(
                    'Python unavailable after provisioning source version. '
                    'Re-attempting provisioning.')
                self.provision_dut(build_name=build_name,
                                   public_bucket=running_at_desk)

            self._run_client_test_and_check_result(
                    self._LOGIN_TEST,
                    tag='source',
                    username=self._LOGIN_TEST_USERNAME,
                    password=self._LOGIN_TEST_PASSWORD)

        # Restore the latest nebraska before performing the update.
        self._host.send_file(temp_nebraska, self._NEBRASKA_PATH)

        # Start the update to the target image.
        self.run_update_test(test_conf, m2n)

        # Check we can login after the update.
        self._run_client_test_and_check_result(
                self._LOGIN_TEST,
                tag='target',
                username=self._LOGIN_TEST_USERNAME,
                password=self._LOGIN_TEST_PASSWORD)
