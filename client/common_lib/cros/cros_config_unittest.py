#!/usr/bin/python3
#
# Copyright 2019 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import unittest
import unittest.mock as mock

import common
from autotest_lib.client.common_lib import error
from autotest_lib.client.common_lib import utils
from autotest_lib.client.common_lib.cros import cros_config


class CallCrosConfigGetOutputTestCase(unittest.TestCase):
    """
    Verify cros_config.call_cros_config_get_output.
    """
    def test_cros_config_success(self):
        """
        Verify when cros_config reports a result, we get the result.
        """
        run_result = utils.CmdResult(stdout="someresult", exit_status=0)
        run = mock.Mock(return_value=run_result)

        result = cros_config.call_cros_config_get_output("/some/path node", run)
        run.assert_called_once_with("cros_config /some/path node")
        self.assertEqual(result, "someresult")

    def test_cros_config_exit_non_zero(self):
        """
        Verify when cros_config exits non-zero, we report no result.
        """
        run_result = utils.CmdResult(stdout="someresult", exit_status=1)
        run = mock.Mock(return_value=run_result)

        result = cros_config.call_cros_config_get_output("/some/path node", run)
        run.assert_called_once_with("cros_config /some/path node")
        self.assertEqual(result, "")

    def test_run_function_fails(self):
        """
        Verify when `run` raises an error, we get no result.
        """
        run = mock.Mock(side_effect=error.CmdError(command="", result_obj=""))

        result = cros_config.call_cros_config_get_output("/some/path node", run)
        run.assert_called_once_with("cros_config /some/path node")
        self.assertEqual(result, "")


if __name__ == "__main__":
    unittest.main()
