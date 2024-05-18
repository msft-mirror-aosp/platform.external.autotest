# Copyright 2021 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import logging

from autotest_lib.client.common_lib import error
from autotest_lib.server import test


class firmware_FingerprintCrosConfig(test.test):
    """A deprecated ChromeOS Test."""
    version = 1

    def initialize(self, host):
        logging.info(
                'Fingerprint autotests have been replaced with tast tests. Please see https://chromium.googlesource.com/chromiumos/platform/ec/+/HEAD/docs/fingerprint/fingerprint-firmware-testing-for-partners.md'
        )
        raise error.TestFail(
                'Fingerprint autotests have been deprecated in favor of tast. Please see https://chromium.googlesource.com/chromiumos/platform/ec/+/HEAD/docs/fingerprint/fingerprint-firmware-testing-for-partners.md'
        )
