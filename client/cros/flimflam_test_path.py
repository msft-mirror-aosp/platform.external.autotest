# Lint as: python2, python3
# Copyright 2012 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import os, sys

from autotest_lib.client.cros import constants

sys.path.append(os.environ.get("SYSROOT", "/usr/local/") +
                constants.FLIMFLAM_TEST_PATH)
