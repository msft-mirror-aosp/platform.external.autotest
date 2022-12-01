# Lint as: python2, python3
# Copyright 2012 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from autotest_lib.client.bin import test
from autotest_lib.client.cros.power import sys_power

class power_KernelSuspend(test.test):
    """Suspend the system."""

    version = 1

    def run_once(self, seconds=10):
        # go to suspend
        sys_power.kernel_suspend(seconds)
