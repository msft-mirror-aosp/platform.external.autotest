# Copyright (c) 2013 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import logging
import sys

# TODO (b/206008069), remove this when migrated to new env
sys.path.insert(0,
                '/usr/local/lib/python2.7/dist-packages/six-1.16.0-py2.7.egg')
try:
    import six
    logging.debug("six version is {}".format(six.__version__))
except ImportError as e:
    logging.warning("Could not import six due to %s", e)

from autotest_lib.server import test
from autotest_lib.server.cros import telemetry_runner


class telemetry_ScrollingActionTests(test.test):
    """Run the telemetry scrolling action tests."""
    version = 1


    def run_once(self, host=None):
        """Run the telemetry scrolling action tests.

        @param host: host we are running telemetry on.
        """
        with telemetry_runner.TelemetryRunnerFactory().get_runner(
                host) as telemetry:
            result = telemetry.run_telemetry_test('ScrollingActionTest')
            logging.debug(
                    'Telemetry completed with a status of: %s with '
                    'output: %s', result.status, result.output)
