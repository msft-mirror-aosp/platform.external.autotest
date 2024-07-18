# Lint as: python2, python3
# Copyright 2012 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import logging
import os
import re
import shutil

from autotest_lib.client.bin import utils
from autotest_lib.client.common_lib import error, bounds
from autotest_lib.client.common_lib.cros import arc, chrome
from autotest_lib.client.cros import upstart

class power_UiResume(arc.ArcTest):
    """
    Suspend the system while simulating user behavior.

    If ARC is present, open ARC before suspending. If ARC is not present, log
    into Chrome before suspending. To suspend, call autotest power_Resume. This
    reduces duplicate code, while cover all 3 cases: with ARC, with Chrome but
    without ARC, and without Chrome.

    """
    version = 3

    def initialize(self, no_arc=False, min_resume=5):
        """
        Entry point. Initialize ARC if it is enabled on the DUT, otherwise log
        in Chrome browser.

        @param min_resume: minimal time in seconds between suspends.
        """
        # --disable-sync disables test account info sync, eg. Wi-Fi credentials,
        # so that each test run does not remember info from last test run.
        extra_browser_args = ['--disable-sync']

        # TODO(b/191251229): Only enable ARC if ARC is available and it is not
        # running ARCVM.
        self._enable_arc = (utils.is_arc_available() and not utils.is_arcvm()
                            and not no_arc)
        if self._enable_arc:
            super(power_UiResume,
                  self).initialize(extra_browser_args=extra_browser_args)
        else:
            self._chrome = chrome.Chrome(extra_browser_args=extra_browser_args)

        self._min_resume = min_resume

    def run_once(self,
                 max_devs_returned=10,
                 seconds=0,
                 ignore_kernel_warns=False,
                 suspend_state='',
                 suspend_iterations=None,
                 metric_bounds=None):
        """
        Run client side autotest power_Resume, to reduce duplicate code.

        """
        service = 'powerd'
        err = 0
        pid_start = upstart.get_pid(service)
        if not pid_start:
            upstart.restart_job(service)
        pid_start = upstart.get_pid(service)
        if not pid_start:
            logging.error('%s is not running at start of test', service)
            err += 1

        res = self.job.run_test('power_Resume',
                                max_devs_returned=max_devs_returned,
                                seconds=seconds,
                                suspend_state=suspend_state,
                                suspend_iterations=suspend_iterations,
                                ignore_kernel_warns=ignore_kernel_warns,
                                measure_arc=self._enable_arc,
                                iteration_delay=self._min_resume)
        if res:
            result_files = os.listdir(
                    os.path.join(self.outputdir, "..", "power_Resume",
                                 "results"))
            for file in result_files:
                shutil.copy2(
                        os.path.join(self.outputdir, "..", "power_Resume",
                                     "results", file), self.resultsdir)
        else:
            logging.error(
                    "inner power_Resume test failed, see logs for details")
            err += 1

        pid_end = upstart.get_pid('powerd')
        if not pid_end:
            logging.error('%s is not running at end of test', service)
            err += 1

        if pid_start and pid_end and pid_start != pid_end:
            logging.error('%s respawned during test', service)
            err += 1

        if err:
            raise error.TestFail('Test failed.  See errors for details.')

        perf_dict = self._process_keyvals()
        bounds.evaluate_test_bounds(perf_dict, metric_bounds)

    def _process_keyvals(self):
        perf_dict = {}
        results_keyval_path = os.path.join(self.resultsdir, 'keyval')
        logging.info('processing keyvals from %s', results_keyval_path)
        if os.path.exists(results_keyval_path):
            with open(results_keyval_path) as results_keyval_file:
                keyval_result = results_keyval_file.readline()
                while keyval_result:
                    regmatch = re.search(r'(.*){(.*)}=(.*)', keyval_result)
                    if regmatch is None:
                        break
                    key = regmatch.group(1)
                    which_dict = regmatch.group(2)
                    value = regmatch.group(3)
                    if which_dict != 'perf':
                        continue
                    perf_dict[key] = value
                    keyval_result = results_keyval_file.readline()
        return perf_dict

    def cleanup(self):
        """
        Clean up ARC if it is enabled on the DUT, otherwise close the Chrome
        browser.
        """
        if self._enable_arc:
            super(power_UiResume, self).cleanup()
        else:
            self._chrome.close()
