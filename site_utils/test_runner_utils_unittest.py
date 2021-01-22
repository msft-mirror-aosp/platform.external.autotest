#!/usr/bin/python2
# Copyright 2015 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
# pylint: disable-msg=C0111

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
import os, unittest
import mox
import common
import shutil
import tempfile
import types
from autotest_lib.client.common_lib import control_data
from autotest_lib.server.cros.dynamic_suite import control_file_getter
from autotest_lib.server.cros.dynamic_suite import suite as suite_module
from autotest_lib.server.hosts import host_info
from autotest_lib.site_utils import test_runner_utils
from six.moves import range
from six.moves import zip


class StartsWithList(mox.Comparator):
    def __init__(self, start_of_list):
        """Mox comparator which returns True if the argument
        to the mocked function is a list that begins with the elements
        in start_of_list.
        """
        self._lhs = start_of_list

    def equals(self, rhs):
        if len(rhs)<len(self._lhs):
            return False
        for (x, y) in zip(self._lhs, rhs):
            if x != y:
                return False
        return True


class ContainsSublist(mox.Comparator):
    def __init__(self, sublist):
        """Mox comparator which returns True if the argument
        to the mocked function is a list that contains sublist
        as a sub-list.
        """
        self._sublist = sublist

    def equals(self, rhs):
        n = len(self._sublist)
        if len(rhs)<n:
            return False
        return any((self._sublist == rhs[i:i+n])
                   for i in range(len(rhs) - n + 1))

class DummyJob(object):
    def __init__(self, id=1):
        self.id = id


class fake_tests(object):
    def __init__(self, text, deps=[]):
        self.text = text
        self.test_type = 'client'
        self.dependencies = deps


class TestRunnerUnittests(mox.MoxTestBase):
    autotest_path = 'ottotest_path'
    suite_name = 'sweet_name'
    test_arg = 'suite:' + suite_name
    remote = 'remoat'
    build = 'bild'
    board = 'bored'
    fast_mode = False
    suite_control_files = ['c1', 'c2', 'c3', 'c4']
    results_dir = '/tmp/test_that_results_fake'
    id_digits = 1
    ssh_verbosity = 2
    ssh_options = '-F /dev/null -i /dev/null'
    args = 'matey'
    retry = True

    def setUp(self):
        mox.MoxTestBase.setUp(self)


    def _results_directory_from_results_list(self, results_list):
        """Generate a temp directory filled with provided test results.

        @param results_list: List of results, each result is a tuple of strings
                             (test_name, test_status_message).
        @returns: Absolute path to the results directory.
        """
        global_dir = tempfile.mkdtemp()
        for index, (test_name, test_status_message) in enumerate(results_list):
            dir_name = '-'.join(['results',
                                 "%02.f" % (index + 1),
                                 test_name])
            local_dir = os.path.join(global_dir, dir_name)
            os.mkdir(local_dir)
            os.mkdir('%s/debug' % local_dir)
            with open("%s/status.log" % local_dir, mode='w+') as status:
                status.write(test_status_message)
                status.flush()
        return global_dir


    def test_handle_local_result_for_good_test(self):
        getter = self.mox.CreateMock(control_file_getter.DevServerGetter)
        getter.get_control_file_list(suite_name=mox.IgnoreArg()).AndReturn([])
        job = DummyJob()
        test = self.mox.CreateMock(control_data.ControlData)
        test.job_retries = 5
        self.mox.StubOutWithMock(test_runner_utils.LocalSuite,
                                 '_retry_local_result')
        self.mox.ReplayAll()
        suite = test_runner_utils.LocalSuite([], "tag", [], None, getter,
                                             job_retry=True)
        suite._retry_handler = suite_module.RetryHandler({job.id: test})

        #No calls, should not be retried
        directory = self._results_directory_from_results_list([
            ("dummy_Good", "GOOD: nonexistent test completed successfully")])
        new_id = suite.handle_local_result(
            job.id, directory,
            lambda log_entry, log_in_subdir=False: None)
        self.assertIsNone(new_id)
        shutil.rmtree(directory)


    def test_handle_local_result_for_bad_test(self):
        getter = self.mox.CreateMock(control_file_getter.DevServerGetter)
        getter.get_control_file_list(suite_name=mox.IgnoreArg()).AndReturn([])
        job = DummyJob()
        test = self.mox.CreateMock(control_data.ControlData)
        test.job_retries = 5
        self.mox.StubOutWithMock(test_runner_utils.LocalSuite,
                                 '_retry_local_result')
        test_runner_utils.LocalSuite._retry_local_result(
            job.id, mox.IgnoreArg()).AndReturn(42)
        self.mox.ReplayAll()
        suite = test_runner_utils.LocalSuite([], "tag", [], None, getter,
                                             job_retry=True)
        suite._retry_handler = suite_module.RetryHandler({job.id: test})

        directory = self._results_directory_from_results_list([
            ("dummy_Bad", "FAIL")])
        new_id = suite.handle_local_result(
            job.id, directory,
            lambda log_entry, log_in_subdir=False: None)
        self.assertIsNotNone(new_id)
        shutil.rmtree(directory)


    def test_generate_report_status_code_success_with_retries(self):
        global_dir = self._results_directory_from_results_list([
            ("dummy_Flaky", "FAIL"),
            ("dummy_Flaky", "GOOD: nonexistent test completed successfully")])
        status_code = test_runner_utils.generate_report(
            global_dir, just_status_code=True)
        self.assertEquals(status_code, 0)
        shutil.rmtree(global_dir)


    def test_generate_report_status_code_failure_with_retries(self):
        global_dir = self._results_directory_from_results_list([
            ("dummy_Good", "GOOD: nonexistent test completed successfully"),
            ("dummy_Bad", "FAIL"),
            ("dummy_Bad", "FAIL")])
        status_code = test_runner_utils.generate_report(
            global_dir, just_status_code=True)
        self.assertNotEquals(status_code, 0)
        shutil.rmtree(global_dir)


    def test_get_predicate_for_test_arg(self):
        # Assert the type signature of get_predicate_for_test(...)
        # Because control.test_utils_wrapper calls this function,
        # it is imperative for backwards compatilbility that
        # the return type of the tested function does not change.
        tests = ['dummy_test', 'e:name_expression', 'f:expression',
                 'suite:suitename']
        for test in tests:
            pred, desc = test_runner_utils.get_predicate_for_test_arg(test)
            self.assertTrue(isinstance(pred, types.FunctionType))
            self.assertTrue(isinstance(desc, str))

    def test_perform_local_run(self):
        """Test a local run that should pass."""
        self.mox.StubOutWithMock(test_runner_utils, '_auto_detect_labels')
        self.mox.StubOutWithMock(test_runner_utils, 'get_all_control_files')

        test_runner_utils._auto_detect_labels(self.remote).AndReturn(
                ['os:cros', 'has_chameleon:True'])

        test_runner_utils.get_all_control_files(
                self.test_arg, self.autotest_path).AndReturn([
                        fake_tests(test, deps=['has_chameleon:True'])
                        for test in self.suite_control_files
                ])

        self.mox.StubOutWithMock(test_runner_utils, 'run_job')
        for control_file in self.suite_control_files:
            test_runner_utils.run_job(
                    mox.ContainsAttributeValue('control_file', control_file),
                    self.remote,
                    mox.IsA(host_info.HostInfo),
                    self.autotest_path,
                    self.results_dir,
                    self.fast_mode,
                    self.id_digits,
                    self.ssh_verbosity,
                    self.ssh_options,
                    mox.StrContains(self.args),
                    False,
                    False,
            ).AndReturn((0, '/fake/dir'))

        self.mox.ReplayAll()
        test_runner_utils.perform_local_run(self.autotest_path,
                                            ['suite:' + self.suite_name],
                                            self.remote,
                                            self.fast_mode,
                                            build=self.build,
                                            board=self.board,
                                            ssh_verbosity=self.ssh_verbosity,
                                            ssh_options=self.ssh_options,
                                            args=self.args,
                                            results_directory=self.results_dir,
                                            job_retry=self.retry,
                                            ignore_deps=False)

    def test_perform_local_run_missing_deps(self):
        """Test a local run with missing dependencies. No tests should run."""
        self.mox.StubOutWithMock(test_runner_utils, '_auto_detect_labels')
        self.mox.StubOutWithMock(test_runner_utils, 'get_all_control_files')

        test_runner_utils._auto_detect_labels(self.remote).AndReturn(
                ['os:cros', 'has_chameleon:True'])

        test_runner_utils.get_all_control_files(
                self.test_arg, self.autotest_path).AndReturn([
                        fake_tests(test, deps=['has_chameleon:False'])
                        for test in self.suite_control_files
                ])

        self.mox.ReplayAll()

        res = test_runner_utils.perform_local_run(
                self.autotest_path, ['suite:' + self.suite_name],
                self.remote,
                self.fast_mode,
                build=self.build,
                board=self.board,
                ssh_verbosity=self.ssh_verbosity,
                ssh_options=self.ssh_options,
                args=self.args,
                results_directory=self.results_dir,
                job_retry=self.retry,
                ignore_deps=False)

        # Verify when the deps are not met, the tests are not run.
        self.assertEquals(res, [])


if __name__ == '__main__':
    unittest.main()
