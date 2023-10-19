# Copyright 2023 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Tests for actions."""

import os
import unittest

import actions
import cf_parse

TEST_DATA_DIR = 'test_data/'

class TestActions(unittest.TestCase):
    """Tests for actions."""
    def test_remove_contacts(self):
        delete_me = 'removable@google.com'
        action = actions.remove_contacts([delete_me])
        test_file = os.path.join(TEST_DATA_DIR, 'control.actions')
        cf = cf_parse.ControlFile(test_file)

        self.assertTrue('contacts' in cf.metadata)
        self.assertTrue(delete_me in cf.metadata['contacts'])
        self.assertTrue(action(cf))
        self.assertTrue('contacts' in cf.metadata)
        self.assertFalse(delete_me in cf.metadata['contacts'])

        self.assertFalse(action(cf))

    def test_append_contacts(self):
        append_1 = "appendable1@google.com"
        append_2 = "appendable2@google.com"
        action = actions.append_contacts([append_1, append_2])
        test_file = os.path.join(TEST_DATA_DIR, 'control.actions')
        cf = cf_parse.ControlFile(test_file)
        starting_len = len(cf.metadata['contacts'])

        self.assertTrue(action(cf))
        self.assertTrue('contacts' in cf.metadata)
        self.assertTrue(append_1 in cf.metadata['contacts'])
        self.assertTrue(append_2 in cf.metadata['contacts'])
        self.assertEqual(cf.metadata['contacts'].index(append_1), starting_len)
        self.assertEqual(cf.metadata['contacts'].index(append_2),
                         starting_len + 1)
        self.assertEqual(len(cf.metadata['contacts']), starting_len + 2)

        self.assertTrue(action(cf))
        self.assertEqual(len(cf.metadata['contacts']), starting_len + 2)

    def test_prepend_contacts(self):
        prepend = "prependable@google.com"
        action = actions.prepend_contacts([prepend])
        test_file = os.path.join(TEST_DATA_DIR, 'control.actions')
        cf = cf_parse.ControlFile(test_file)
        starting_len = len(cf.metadata['contacts'])

        self.assertTrue(action(cf))
        self.assertTrue('contacts' in cf.metadata)
        self.assertTrue(prepend in cf.metadata['contacts'])
        self.assertEqual(cf.metadata['contacts'].index(prepend), 0)
        self.assertEqual(len(cf.metadata['contacts']), starting_len + 1)

        self.assertTrue(action(cf))
        self.assertEqual(len(cf.metadata['contacts']), starting_len + 1)


if __name__ == '__main__':
    unittest.main()
