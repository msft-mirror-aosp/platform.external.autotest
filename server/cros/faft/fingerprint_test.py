# Lint as: python2, python3
# Copyright 2018 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import logging

from autotest_lib.server import test
from autotest_lib.client.common_lib import error


class FingerprintTest(test.test):
    """Base class that sets up helpers for deprecated fingerprint tests."""
    version = 1

    def initialize(self, host):
        logging.info(
                'Fingerprint autotests have been replaced with tast tests. Please see https://chromium.googlesource.com/chromiumos/platform/ec/+/HEAD/docs/fingerprint/fingerprint-firmware-testing-for-partners.md'
        )
        raise error.TestFail(
                'Fingerprint autotests have been deprecated in favor of tast. Please see https://chromium.googlesource.com/chromiumos/platform/ec/+/HEAD/docs/fingerprint/fingerprint-firmware-testing-for-partners.md'
        )
