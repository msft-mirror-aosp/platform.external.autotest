# Lint as: python2, python3
# Copyright 2023 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import logging
import os
import sys

from autotest_lib.client.bin import utils as client_utils
from autotest_lib.server import utils
from autotest_lib.server.cros.tradefed import bundle_utils
from autotest_lib.server.cros.tradefed.tradefed_test import BundleSpecification
from autotest_lib.server.cros.tradefed.tradefed_test import TradefedTest

CTS_TARGET_MODULE = 'CtsBluetooth'
CTS_BUNDLE = 'arm'
CTS_URI = 'DEV'
CTS_TIMEOUT_SECONDS = 5400
CTS_CONFIG_RELATIVE_PATH = '../../cheets_CTS_{}/bundle_url_config.json'


class bluetooth_AdapterCTSHealth(TradefedTest):
    """Class to run Bluetooth CTS health tests"""

    def _tradefed_retry_command(self, template, session_id):
        """Needed by tradefed. Content is copy-pasted."""
        cmd = []
        for arg in template:
            cmd.append(arg.format(session_id=session_id))
        return cmd

    def _tradefed_run_command(self, template):
        """Needed by tradefed. Content is copy-pasted."""
        cmd = template[:]

        if self.arc_version == 'P':
            # Apply this PATH change only for chroot environment
            if not utils.is_in_container() and not client_utils.is_moblab():
                try:
                    os.environ['JAVA_HOME'] = '/opt/icedtea-bin-3.4.0'
                    os.environ['PATH'] = os.environ['JAVA_HOME']\
                                       + '/bin:' + os.environ['PATH']
                except OSError:
                    logging.error('Can\'t change current PATH directory')

            # Suppress redundant output from tradefed.
            cmd.append('--quiet-output=true')

        return cmd

    def _get_tradefed_base_dir(self):
        """Needed by tradefed. Content is copy-pasted."""
        return 'android-cts'

    def _tradefed_cmd_path(self):
        """Needed by tradefed. Content is copy-pasted."""
        return os.path.join(self._repository, 'tools', 'cts-tradefed')

    def _get_bundle_specification(self, uri, bundle):
        """Tradefed function to get the test bundle.

        This function is overrided to obtain the correct path for each arc
        versions.

        @param uri: determined by tradefed, could be 'DEV' or 'LATEST'
        @param bundle: always 'arm' in our case, but can also be 'x86'
        """
        test_path = sys.modules[self.__class__.__module__].__file__
        config_path = os.path.abspath(
                os.path.join(test_path,
                             CTS_CONFIG_RELATIVE_PATH.format(
                                     self.arc_version)))
        url_config = bundle_utils.load_config(config_path)
        bundle_password = bundle_utils.get_bundle_password(url_config)

        return BundleSpecification(
                bundle_utils.make_bundle_url(url_config, uri, bundle),
                bundle_password)

    def initialize(self, arc_version=None, host=None):
        """Tradefed function to initialize the test.

        This function is overrided to store the arc_version, in order to
        avoid creating one test file for each of the arc versions.

        @param arc_version: The arc version to test, e.g. 'P', 'R', or 'T'
        @param host: The DUT, usually a chromebook
        """
        self.arc_version = arc_version

        super(bluetooth_AdapterCTSHealth, self).initialize(bundle=CTS_BUNDLE,
                                                           uri=CTS_URI,
                                                           host=host)

    def run_once(self,
                 test_name=None,
                 run_template=None,
                 retry_template=None,
                 floss=False):
        """Run the batch of Bluetooth CTS health tests

        @param test_name: The name of the test
        @param run_template: Needed by tradefed. Content is copy-pasted
        @param retry_template: Needed by tradefed. Content is copy-pasted
        @param floss: Is bluetooth running Floss?
        """
        chrome_feature = 'Floss' if floss else None

        self._run_tradefed_with_retries(test_name=test_name,
                                        run_template=run_template,
                                        retry_template=retry_template,
                                        target_module=CTS_TARGET_MODULE,
                                        bundle=CTS_BUNDLE,
                                        timeout=CTS_TIMEOUT_SECONDS,
                                        chrome_feature=chrome_feature)
