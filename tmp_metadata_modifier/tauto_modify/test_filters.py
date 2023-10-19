# Copyright 2023 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Tests for filters."""

import os
import unittest

import filters
import cf_parse

TEST_DATA_DIR = 'test_data/'

class TestFilters(unittest.TestCase):
    """Tests for filters."""
    def test_list_of_tests(self):
        filter_func = filters.test_list(['tauto.filterable_name'])
        test_file_match = os.path.join(TEST_DATA_DIR, 'control.filter_name')
        cf_match = cf_parse.ControlFile(test_file_match)
        test_file_no_match = os.path.join(TEST_DATA_DIR, 'control.actions')
        cf_no_match = cf_parse.ControlFile(test_file_no_match)

        self.assertTrue(filter_func(cf_match))
        self.assertFalse(filter_func(cf_no_match))

if __name__ == '__main__':
    unittest.main()
