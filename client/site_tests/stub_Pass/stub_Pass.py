# Copyright 2010 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from autotest_lib.client.bin import test
from autotest_lib.client.common_lib import error


class stub_Pass(test.test):
    version = 1

    def run_once(self):
        return
