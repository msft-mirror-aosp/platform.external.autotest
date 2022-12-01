# Copyright 2022 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import unittest

from autotest_lib.client.common_lib import error
from autotest_lib.server.cros.power import utils


class TestCheckPowerState(unittest.TestCase):
    """Test that power_state matching is precise"""
    # power_state is supposed to be a string, but lists seem somewhat common,
    # so guard against them.

    def test_fails_on_list(self):
        with self.assertRaises(error.TestError):
            utils._check_power_state([], 'S0')

    def test_s0ix_isnt_s0(self):
        self.assertEqual(False, utils._check_power_state("S0", "S0ix"))

    def test_s0_is_found(self):
        self.assertEqual(True, utils._check_power_state("S0", "S0"))

    def test_s0_is_found_unicode(self):
        self.assertEqual(True, utils._check_power_state(u"S0", "S0"))
        self.assertEqual(True, utils._check_power_state("S0", u"S0"))
        self.assertEqual(True, utils._check_power_state(u"S0", u"S0"))

    def test_s0_or_s3_is_found(self):
        self.assertEqual(True, utils._check_power_state("(S0|S3)", "S0"))
        self.assertEqual(True, utils._check_power_state("(S0|S3)", "S3"))
        self.assertEqual(False, utils._check_power_state("(S0|S3)", "G3"))
