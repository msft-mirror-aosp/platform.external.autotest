# Copyright 2022 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import logging
import os
import sys
import shutil

from autotest_lib.client.common_lib import error
from autotest_lib.client.common_lib import utils
from autotest_lib.client.common_lib.cros import tpm_utils
from autotest_lib.server import test
from autotest_lib.server.cros import chrome_sideloader

MAX_GPU_TELEMETRY_TIMEOUT_SEC = 3600


class chromium_Graphics(test.test):
    """Run graphics tests for the Chrome built by browser infra.

    This is a wrapper class to exeucte run_gpu_integration_test.py
    on Skylab bot for chrome artifacts built by browser infra.
    """
    version = 1

    # The path where we install chromium/src. In this experimental
    # stage, we may use existing lacros image, which built at src.
    CHROME_BUILD = '/usr/local/lacros-build'

    # run_gpu_integration_test are calling telemetry to manipulate the DUT.
    # In telemetry the lacros chrome must be stored at below path.
    # See go/lacros_browser_backend.
    LACROS_MOUNT_POINT = '/usr/local/lacros-chrome'
    CHROME_MOUNT_POINT = '/opt/google/chrome'

    def initialize(self, host=None, args=None):
        self.host = host

        self.args_dict = utils.args_to_dict(args)
        self.test_args = chrome_sideloader.get_test_args(
                self.args_dict, 'test_args').split(' ')

        # 'chromite_deploy_chrome' installs Ash/Lacros via chromite and leave
        # chrome checkout on Drone, which contains the GPU test's server package.
        archive_type = 'chrome' if self.is_cros_chrome else 'lacros'
        self.server_pkg = chrome_sideloader.chromite_deploy_chrome(
                self.host, self.args_dict.get('lacros_gcs_path'), archive_type)

        if not self.args_dict.get('run_private_tests',
                                  True) in [False, 'False']:
            tpm_utils.ClearTPMOwnerRequest(self.host, wait_for_ready=True)

        # The test script needs to know it is running in Skylab environment.
        os.environ['RUNNING_IN_SKYLAB'] = '1'

    @property
    def is_cros_chrome(self):
        return any(['--browser=cros-chrome' in x for x in self.test_args])

    def run_once(self):
        """Invoke run_gpu_integration_test."""
        cmd = [
                'vpython3',
                '-vpython-spec',
                '../../.vpython3',
                os.path.join('../../testing', 'scripts',
                             'run_gpu_integration_test_as_googletest.py'),
                os.path.join('../../content', 'test', 'gpu',
                             'run_gpu_integration_test.py'),
                # Generate a gtest-ish result file. This is mostly for reference now,
                # because GPU tests do not upload it to RDB.
                '--isolated-script-test-output={}'.format(
                        os.path.join(self.resultsdir, 'output.json')),
                # GPU team requires a bunch of tags with the results, and the
                # gtest output does not suffice.
                # GPU test script exports each test result into a json string
                # in sinkpb.TestResult, aka the native RDB format.
                # Test runner recipe will call native result_adapter
                # to upload them to RDB. See crrev.com/c/4081733.
                '--rdb-content-output-file={}'.format(
                        os.path.join(self.resultsdir, 'native_results.jsonl')),
                '--chromium-output-directory=./',
                '--remote={}'.format(self.host.hostname),
        ]
        # Pass the test arguments from the browser test owners.
        # Note utils.run() quotes all members in the cmd list. We have
        # to split our test_args, or it will feed to
        # run_gpu_integration_test.py as a single string. The same
        # reason we have to pass extra-browser-args separately.
        cmd.extend(self.test_args)
        # Autotest does not recognize args with '-'.
        cmd.append('--extra-browser-args={}'.format(
                chrome_sideloader.get_test_args(self.args_dict,
                                                'extra_browser_args')))

        logging.debug('Running: %s', cmd)
        exit_code = 0
        # We must kick off the test from src/out/Release, because
        # the flags configured by browser side are assumed so.
        os.chdir(os.path.join(self.server_pkg, 'out', 'Release'))
        logging.debug('CWD: %s', os.getcwd())
        try:
            result = utils.run(cmd,
                               stdout_tee=sys.stdout,
                               stderr_tee=sys.stderr,
                               timeout=MAX_GPU_TELEMETRY_TIMEOUT_SEC,
                               extra_paths=['/opt/infra-tools'])
            exit_code = result.exit_status
        except error.CmdError as e:
            logging.debug('Error occurred executing GPU integration tests.')
            exit_code = e.result_obj.exit_status

        if exit_code:
            raise error.TestFail('Chromium GPU Integration Test'
                                 ' failed to run.')

    def cleanup(self):
        chrome_sideloader.cleanup_host(
                self.host,
                self.CHROME_BUILD,
                self.CHROME_MOUNT_POINT
                if self.is_cros_chrome else self.LACROS_MOUNT_POINT,
                is_cros_chrome=self.is_cros_chrome)
        shutil.rmtree(self.server_pkg)
