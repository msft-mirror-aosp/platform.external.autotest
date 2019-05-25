# Copyright 2019 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import logging
import sys

from autotest_lib.client.common_lib import error
from autotest_lib.server.cros.faft.firmware_test import FirmwareTest
from autotest_lib.server.site_tests.firmware_FAFTRPC import config


def get_rpc_category_by_name(name):
    """Find a category from config.RPC_CATEGORIES by its category_name."""
    for rpc_category in config.RPC_CATEGORIES:
        if rpc_category["category_name"] == name:
            return rpc_category
    raise ValueError("No RPC category defined with category_name=%s" % name)


def get_rpc_method_names_from_test_case(test_case):
    """
    Extract the method_name or method_names from a test case configuration.
@param test_case: An element from a test_cases array,
                      like those in config.RPC_CATEGORIES

    @return: A list of names of RPC methods in that test case.

    """
    if (("method_name" in test_case) ^ ("method_names" in test_case)):
        if "method_name" in test_case:
            return [test_case["method_name"]]
        elif "method_names" in test_case:
            return test_case["method_names"]
        else:
            err_msg = "Something strange happened while parsing RPC methods"
            raise ValueError(err_msg)
    else:
        err_msg = "test_case must contain EITHER method_name OR method_names"
        raise ValueError(err_msg)



class firmware_FAFTRPC(FirmwareTest):
    """
    This test checks that all RPC commands work as intended.

    For now, we only need to verify that the RPC framework is intact,
    so we only verify that all RPCs can be called with the
    expected arguments.

    It would be good to expand this test to verify that all RPCs
    yields the expected results.

    """
    version = 1


    def _log_success(self, rpc_name, params, success_message):
        """Report on an info level that a test passed."""
        logging.info("RPC test for %s%s successfully %s",
                     rpc_name, params, success_message)


    def _fail(self, rpc_name, params, error_msg):
        """Raise a TestFail error explaining why a test failed."""
        raise error.TestFail("RPC function %s%s had an unexpected result: %s"
                             % (rpc_name, params, error_msg))


    def _assert_passes(self, category, method, params, allow_error_msg=None):
        """
        Check whether an RPC function with given input passes,
        and fail if it does not.

        @param category: The RPC subsystem category; ex. kernel, bios
        @param method: The name of the RPC function within the subsystem
        @param params: A tuple containing params to pass into the RPC function
        @param allow_error_msg: If a string is passed in, and the RPC call
                                returns an RPC error containing this string,
                                then the test will pass instead of failing.

        @raise error.TestFail: If the RPC raises any error (unless handled by
                               allow_error_msg).

        @return: Not meaningful.

        """
        rpc_function = self.get_rpc_function(category, method)
        rpc_name = ".".join([category, method])
        try:
            result = rpc_function(*params)
        except config.RPC_ERRORS as e:
            if allow_error_msg is not None and allow_error_msg in str(e):
                success_msg = "raised an acceptable error during RPC handling"
                self._log_success(rpc_name, params, success_msg)
                return e
            error_msg = "Unexpected RPC error: %s" % e
            self._fail(rpc_name, params, error_msg)
        except:
            error_msg = "Unexpected misc error: %s" % sys.exc_info()[0]
            self._fail(rpc_name, params, error_msg)
        else:
            self._log_success(rpc_name, params, "passed")
            return result


    def _assert_fails(self, category, method, params):
        """
        Check whether an RPC function with given input throws an RPC error,
        and fail if it does not.

        @param category: The RPC subsystem category; ex. kernel, bios
        @param method: The name of the RPC function within the subsystem
        @param params: A tuple containing params to pass into the RPC function

        @raise error.TestFail: If the RPC raises no error, or if it raises any
                               error other than xmlrpclib.Fault or grpc.RpcError

        @return: Not meaningful.

        """
        rpc_function = self.get_rpc_function(category, method)
        rpc_name = ".".join([category, method])
        try:
            result = rpc_function(*params)
        except config.RPC_ERRORS as e:
            self._log_success(rpc_name, params, "raised RPC error")
        except:
            error_msg = "Unexpected misc error: %s" % sys.exc_info()[0]
            self._fail(rpc_name, params, error_msg)
        else:
            error_msg = "Should have raised an RPC error, but did not"
            self._fail(rpc_name, params, error_msg)


    def _assert_output(self, category, method, params, expected_output,
                       allow_error_msg=None):
        """
        Check whether an RPC function with given input
        returns a particular value, and fail if it does not.

        @param category: The RPC subsystem category; ex. kernel, bios
        @param method: The name of the RPC function within the subsystem
        @param params: A tuple containing params to pass into the RPC function
        @param expected_output: The value that the RPC function should return
        @param allow_error_msg: If a string is passed in, and the RPC call
                                returns an RPC error containing this string,
                                then the test will pass instead of failing.

        @raise error.TestFail: If self._assert_passes(...) fails, or if the
                               RPC return value does not match expected_output

        @return: Not meaningful.

        """
        rpc_name = ".".join([category, method])
        actual_output = self._assert_passes(category, method, params)
        if expected_output == actual_output:
            success_message = "returned the expected value <%s>" \
                              % expected_output
            self._log_success(rpc_name, params, success_message)
        else:
            error_msg = "Expected output <%s>, but actually returned <%s>" \
                        % (expected_output, actual_output)
            self._fail(rpc_name, params, error_msg)


    def get_rpc_function(self, category, method):
        """
        Find a callable RPC function given its name.

        @param category: The name of an RPC subsystem category; ex. kernel, ec
        @param method: The name of an RPC function within the subsystem

        @return: A callable method of the RPC proxy
        """
        rpc_function_handler = getattr(self.faft_client, category)
        rpc_function = getattr(rpc_function_handler, method)
        return rpc_function


    def run_once(self, category_under_test="*"):
        """
        Main test logic.

        For all RPC categories being tested,
        iterate through all test cases defined in config.py.

        @param category_under_test: The name of an RPC category to be tested,
                                    such as ec, bios, or kernel.
                                    Default is '*', which tests all categories.

        """
        if category_under_test == "*":
            logging.info("Testing all %d RPC categories",
                         len(config.RPC_CATEGORIES))
            rpc_categories_to_test = config.RPC_CATEGORIES
        else:
            rpc_categories_to_test = [
                    get_rpc_category_by_name(category_under_test)]
            logging.info("Testing RPC category '%s'", category_under_test)
        for rpc_category in rpc_categories_to_test:
            category_name = rpc_category["category_name"]
            test_cases = rpc_category["test_cases"]
            logging.info("Testing %d cases for RPC category '%s'",
                         len(test_cases), category_name)
            for test_case in test_cases:
                method_names = get_rpc_method_names_from_test_case(test_case)
                passing_args = test_case.get("passing_args", [])
                failing_args = test_case.get("failing_args", [])
                allow_error_msg = test_case.get("allow_error_msg", None)
                for method_name in method_names:
                    for passing_arg_tuple in passing_args:
                        result = self._assert_passes(category_name, method_name,
                                                     passing_arg_tuple,
                                                     allow_error_msg)
                    for failing_arg_tuple in failing_args:
                        self._assert_fails(category_name, method_name,
                                           failing_arg_tuple)
