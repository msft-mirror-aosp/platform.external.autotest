# Lint as: python2, python3
# Copyright 2020 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import logging
import os

from autotest_lib.client.common_lib import error
from autotest_lib.client.common_lib.cros import kernel_utils
from autotest_lib.client.cros import cryptohome
from autotest_lib.server.cros import provisioner
from autotest_lib.server.cros.update_engine import update_engine_test

class autoupdate_Basic(update_engine_test.UpdateEngineTest):
    """Performs a simple AU using Nebraska."""
    version = 1

    def cleanup(self):
        super(autoupdate_Basic, self).cleanup()


    def run_once(self,
                 full_payload,
                 build=None,
                 m2n=False,
                 running_at_desk=False,
                 pin_login=False):
        """
        Performs a N-to-N autoupdate with Nebraska.

        @param full_payload: True for full payload, False for delta
        @param build: An optional parameter to specify the target build for the
                      update when running locally. If no build is supplied, the
                      current version on the DUT will be used. In the lab, the
                      job_repo_url from the host attributes will override this.
        @m2n: M -> N update. This means we install the current stable version
              of this board before updating to ToT.
        @param running_at_desk: Indicates test is run locally from workstation.
        @param pin_login: True to use login via PIN.

        """
        if pin_login:
            if not cryptohome.is_low_entropy_credentials_supported(self._host):
                raise error.TestNAError(
                        'Skip test: No hardware support for PIN login')

        # Get a payload to use for the test.
        payload_url = self.get_payload_for_nebraska(
                build=build,
                full_payload=full_payload,
                public_bucket=running_at_desk)

        self._m2n = m2n
        if self._m2n:
            if self._host.get_board().endswith("-kernelnext"):
                raise error.TestNAError("Skipping test on kernelnext board")
            if self._host.get_board().endswith("-manatee"):
                raise error.TestNAError("Skipping test on manatee board")

            # Provision latest stable build for the current build.
            build_name = self._get_latest_serving_stable_build()
            logging.debug('build name is %s', build_name)

            # Install the matching build with quick provision.
            cache_server_url = None
            if running_at_desk:
                self._copy_quick_provision_to_dut()
                update_url = self._get_provision_url_on_public_bucket(
                        build_name)
            else:
                cache_server_url = self._get_cache_server_url()
                update_url = os.path.join(cache_server_url, 'update',
                                          build_name)

            logging.info('Installing source image with update url: %s',
                         update_url)
            provisioner.ChromiumOSProvisioner(
                    update_url,
                    host=self._host,
                    is_release_bucket=True,
                    public_bucket=running_at_desk,
                    cache_server_url=cache_server_url).run_provision()

        # Login to device before update
        if pin_login:
            self._run_client_test_and_check_result(self._LOGIN_TEST_PIN,
                                                   tag='before')
        else:
            self._run_client_test_and_check_result(
                    self._LOGIN_TEST,
                    username=self._LOGIN_TEST_USERNAME,
                    password=self._LOGIN_TEST_PASSWORD,
                    tag='before')

        # Record DUT state before the update.
        active, inactive = kernel_utils.get_kernel_state(self._host)

        # Perform the update.
        self._run_client_test_and_check_result('autoupdate_CannedOmahaUpdate',
                                               payload_url=payload_url)

        # Verify the update completed successfully.
        self._host.reboot()
        kernel_utils.verify_boot_expectations(inactive, host=self._host)
        rootfs_hostlog, _ = self._create_hostlog_files()
        self.verify_update_events(self._FORCED_UPDATE, rootfs_hostlog)

        if self._m2n:
            # Bring stateful version to the same version as rootfs.
            logging.info('Restoring stateful partition to ToT version')
            self._update_stateful()
        # Check we can login with the same user after update.
        if pin_login:
            self._run_client_test_and_check_result(self._LOGIN_TEST_PIN,
                                                   tag='after',
                                                   setup_pin=False)
        else:
            self._run_client_test_and_check_result(
                    self._LOGIN_TEST,
                    tag='after',
                    username=self._LOGIN_TEST_USERNAME,
                    password=self._LOGIN_TEST_PASSWORD,
                    dont_override_profile=True)
