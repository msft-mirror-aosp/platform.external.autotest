#!/usr/bin/python
# Copyright (c) 2013 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import StringIO
import mox
import unittest
import urllib2

import common
from autotest_lib.client.common_lib.cros import retry
from autotest_lib.server import site_utils
from autotest_lib.server.cros.dynamic_suite import frontend_wrappers
from autotest_lib.server.cros.dynamic_suite import reporting
# Mock the retry.retry used in the test_push before import it.
def mock_retry(ExceptionToCheck, timeout_min, exception_to_raise=None):
    """A mock retry decorator to use in place of the actual one for testing.

    @param ExceptionToCheck: the exception to check.
    @param timeout_mins: Amount of time in mins to wait before timing out.
    @param exception_to_raise: Ignored

    """
    def inner_retry(func):
        """The actual decorator.

        @param func: Function to be called in decorator.

        """
        return func

    return inner_retry
retry.retry = mock_retry
from autotest_lib.site_utils import test_push

AUTOFILED_COUNT_2 = '%s2' % reporting.Reporter.AUTOFILED_COUNT

class TestPushUnittests(mox.MoxTestBase):
    """Unittest for test_push script."""

    def setUp(self):
        """Initialize the unittest."""
        super(TestPushUnittests, self).setUp()
        # Overwrite expected test results.
        test_push.EXPECTED_TEST_RESULTS = {
            '^SERVER_JOB$':                  'GOOD',
            '.*control.dependency$':         'TEST_NA',
            '.*dummy_Fail.RetryFail$':       'FAIL',
            }


    def stub_out_methods(self, test_views):
        """Stub out methods in test_push module with given test results.

        @param test_views: Desired test result views.

        """
        self.mox.UnsetStubs()
        response = StringIO.StringIO('some_value')
        self.mox.StubOutWithMock(urllib2, 'urlopen')
        urllib2.urlopen(mox.IgnoreArg()).AndReturn(response)

        self.mox.StubOutWithMock(test_push, 'get_default_build')
        test_push.get_default_build(mox.IgnoreArg()).AndReturn(
                'stumpy-release/R36-5881-0.0')
        test_push.get_default_build(mox.IgnoreArg()).AndReturn(
                'quawks-release/R36-5881-0.0')

        self.mox.StubOutWithMock(test_push, 'check_dut_image')
        test_push.check_dut_image(mox.IgnoreArg(), mox.IgnoreArg()).AndReturn(
                None)

        self.mox.StubOutWithMock(test_push, 'do_run_suite')
        test_push.do_run_suite(test_push.PUSH_TO_PROD_SUITE, mox.IgnoreArg(),
                               mox.IgnoreArg(), mox.IgnoreArg()
                               ).AndReturn((1))

        self.mox.StubOutWithMock(site_utils, 'get_test_views_from_tko')
        self.mox.StubOutWithMock(frontend_wrappers, 'RetryingTKO')
        frontend_wrappers.RetryingTKO(timeout_min=0.1,
                                      delay_sec=10).AndReturn(None)
        site_utils.get_test_views_from_tko(1, None).AndReturn(test_views)


    def test_suite_success(self):
        """Test test_suite method with matching results."""
        test_views = {'SERVER_JOB':                        'GOOD',
                      'dummy_fail/control.dependency':     'TEST_NA',
                      'dummy_Fail.RetryFail':              'FAIL'
                      }

        self.stub_out_methods(test_views)
        self.mox.ReplayAll()
        test_push.test_suite(test_push.PUSH_TO_PROD_SUITE, test_views,
                             arguments=test_push.parse_arguments())
        self.mox.VerifyAll()


    def test_suite_fail_with_missing_test(self):
        """Test test_suite method that should fail with missing test."""
        test_views = {'SERVER_JOB':                        'GOOD',
                      'dummy_fail/control.dependency':     'TEST_NA',
                      }

        self.stub_out_methods(test_views)
        self.mox.ReplayAll()
        test_push.test_suite(test_push.PUSH_TO_PROD_SUITE, test_views,
                             arguments=test_push.parse_arguments())
        self.mox.VerifyAll()


    def test_suite_fail_with_unexpected_test_results(self):
        """Test test_suite method that should fail with unexpected test results.
        """
        test_views = {'SERVER_JOB':                        'FAIL',
                      'dummy_fail/control.dependency':     'TEST_NA',
                      'dummy_Fail.RetryFail':              'FAIL',
                      }

        self.stub_out_methods(test_views)
        self.mox.ReplayAll()
        test_push.test_suite(test_push.PUSH_TO_PROD_SUITE, test_views,
                             arguments=test_push.parse_arguments())
        self.mox.VerifyAll()


    def test_suite_fail_with_extra_test(self):
        """Test test_suite method that should fail with extra test."""
        test_views = {'SERVER_JOB':                        'GOOD',
                      'dummy_fail/control.dependency':     'TEST_NA',
                      'dummy_Fail.RetryFail':              'FAIL',
                      'dummy_Fail.ExtraTest':              'GOOD',
                      }

        self.stub_out_methods(test_views)
        self.mox.ReplayAll()
        test_push.test_suite(test_push.PUSH_TO_PROD_SUITE, test_views,
                             arguments=test_push.parse_arguments())
        self.mox.VerifyAll()


if __name__ == '__main__':
    unittest.main()
