# Copyright 2014 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import common
from autotest_lib.client.cros.cellular.mbim_compliance.tests import test


class StubTest(test.Test):
    """ A stub test that always passes. """

    def run(self):
        """ Always passes. """
        pass
