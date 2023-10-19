# Copyright 2023 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Tests for cf_parse."""

import os
import unittest

import cf_parse

TEST_DATA_DIR = 'test_data/'

class TestControlFileParse(unittest.TestCase):
    """Tests for cf_parse."""
    def test_parse(self):
        test_file = os.path.join(TEST_DATA_DIR, 'control.cf_parse')
        cf = cf_parse.ControlFile(test_file)
        self.assertEqual(cf.name_value, 'fake_test')
        self.assertEqual(cf.metadata_start, 19)
        self.assertEqual(cf.contents[cf.metadata_start], 'M')
        self.assertEqual(cf.metadata_end, 93)
        self.assertEqual(cf.contents[cf.metadata_end], '\n')

    def test_format_string(self):
        s_short = str(cf_parse.format_string_value('foo'))
        self.assertEqual(s_short, '"foo"')
        s_long = cf_parse.format_string_value(
                '123456789 123456 890123456 8901234 67890'
                '1234 6789012\n 4567890 234567890 234567890'
                '1234 6789012345678901234567\n 901234567890')
        expected_long = (
                '("123456789 123456 890123456 8901234 678901234 6789012"\n'
                '        "4567890 234567890 2345678901234 '
                '6789012345678901234567"\n'
                '        "901234567890")')
        self.assertEqual(s_long, expected_long)

    def test_format_list(self):
        l_short = cf_parse.format_list_value(['foo'])
        self.assertEqual(l_short, '["foo"]')

        l_long = cf_parse.format_list_value(['foo', 'bar'])
        expected_long = '[\n        "foo",\n        "bar",\n    ]'
        self.assertEqual(l_long, expected_long)

    def test_format_metadata(self):
        metadata_dict = {
                'foo': 'bar',
                'num': 4,
                'bool': True,
                'lnum': [1]
        }
        formatted = cf_parse.format_metadata(metadata_dict)
        expected = (
                'METADATA = {\n'
                '    "foo": "bar",\n'
                '    "num": 4,\n'
                '    "bool": True,\n'
                '    "lnum": [1],\n}'
        )
        self.assertEqual(formatted, expected)

    def test_update_contents(self):
        test_file = os.path.join(TEST_DATA_DIR, 'control.cf_parse')
        cf = cf_parse.ControlFile(test_file)
        cf.metadata = {}
        cf.update_contents()
        expected = (
                'NAME = "fake_test"\n'
                'METADATA = {\n}\n')
        self.assertEqual(cf.contents, expected)

if __name__ == '__main__':
    unittest.main()
