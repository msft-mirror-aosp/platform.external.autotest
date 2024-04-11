# Lint as: python2, python3
# Copyright 2020 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import logging
import os

from autotest_lib.client.common_lib import error
from autotest_lib.client.common_lib.cros import kernel_utils
from autotest_lib.client.cros import cryptohome
from autotest_lib.server.cros.update_engine import update_engine_test

class autoupdate_Basic(update_engine_test.UpdateEngineTest):
    """Performs a simple AU using Nebraska."""
    version = 1

    def cleanup(self):
        super(autoupdate_Basic, self).cleanup()

    def touch_pil(self):
        """
        Create empty files for PIL to avoid import failures during the
        login_LoginSuccess test when pillow is missing from older images.
        """
        # telemetry is using python3.8 on the images where pillow is
        # missing. Later images that might be using a different python
        # should have PIL installed.
        pildir = '/usr/local/lib/python3.8/site-packages/PIL'
        # Create an empty PIL/ImageGrab since <R125 reven images will
        # always fail login_LoginSuccess due to the missing import.
        # b/317793587
        try:
            self._run('python "import PIL"')
        except error.AutoservRunError:
            logging.info("touching PIL to ensure it exists on the old image")
            self._run('mkdir -p %s' % pildir)
            self._run('touch %s %s' % (os.path.join(pildir, '__init__.py'),
                                       os.path.join(pildir, 'ImageGrab.py')))

    def run_once(self,
                 full_payload,
                 build=None,
                 m2n=False,
                 running_at_desk=False,
                 pin_login=False,
                 oldest_stable=False):
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
        @param oldest_stable: True to update from the oldest serving stable
                              version.

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
            skip_board_suffixes = ['-kernelnext', '-manatee', '-scudo']
            self.provision_dut(public_bucket=running_at_desk,
                               skip_board_suffixes=skip_board_suffixes,
                               oldest_stable=oldest_stable)

        self.touch_pil()
        # Login to device before update
        if pin_login:
            self._run_client_test_and_check_result(self._LOGIN_TEST_PIN,
                                                   tag='before')
        else:
            self._run_client_test_and_check_result(
                    self._LOGIN_TEST,
                    username=self._LOGIN_TEST_USERNAME,
                    password=self._LOGIN_TEST_PASSWORD,
                    tag='before',
                    session_start_timeout=30)

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

        self.touch_pil()
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
                    dont_override_profile=True,
                    session_start_timeout=30)
