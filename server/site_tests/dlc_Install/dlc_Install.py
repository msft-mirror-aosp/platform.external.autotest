# Lint as: python2, python3
# Copyright 2022 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from autotest_lib.client.common_lib import error
from autotest_lib.server.cros.update_engine import update_engine_test

class dlc_Install(update_engine_test.UpdateEngineTest):
    """Performs a DLC installation."""

    def initialize(self, host=None, dlc=None):
        """Remove all DLCs on the DUT before starting the test. """
        super(dlc_Install, self).initialize(host=host)

        if dlc is None:
          raise error.TestFail('Must pass in a DLC for testing.')

        self._dlc_util.purge(dlc)


    def cleanup(self, dlc):
        self._dlc_util.purge(dlc)


    def run_once(self, dlc):
        """
        Install a DLC.

        @param dlc: The name of the DLC to install, DLC ID.
        """
        self._dlc_util.install(dlc_id=dlc, omaha_url='')
