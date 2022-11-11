#!/usr/bin/python3

# Copyright (c) 2021 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import os
import six
import unittest
import tempfile
import shutil

os.environ["PY_VERSION"] = '3'

import common

# These tests are strictly not supported in python2.
if six.PY2:
    exit(0)

from autotest_lib.client.common_lib import control_data
from autotest_lib.utils import generate_metadata

CONTROL_DATA1 = """
# Copyright 2021 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

AUTHOR = 'an author with email@google.com'
NAME = 'fake_test1'
PURPOSE = 'A fake test.'
ATTRIBUTES = 'suite:fake_suite1, suite:fake_suite2'
TIME = 'SHORT'
TEST_CATEGORY = 'Functional'
TEST_CLASS = 'audio'
TEST_TYPE = 'client'
DEPENDENCIES = 'chameleon,servo_state:WORKING'
METADATA = {
    'requirements': ['req1', 'req2'],
    'bug_component': 'xyz123',
    'hw_agnostic' : True
}

DOC = '''
a doc
'''

job.run_test('fake_test1')

"""

CONTROL_DATA2 = """
# Copyright 2021 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

AUTHOR = 'an author with email@google.com'
NAME = 'fake_test2'
PURPOSE = 'A fake test.'
ATTRIBUTES = 'suite:fake_suite1, suite:fake_suite2'
TIME = 'SHORT'
TEST_CATEGORY = 'Functional'
TEST_CLASS = 'audio'
TEST_TYPE = 'client'
DEPENDENCIES = 'fakedep2'

DOC = '''
a doc
'''

job.run_test('fake_test2')

"""

CONTROL_DATA3 = """
# Copyright 2021 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

AUTHOR = 'an author with email@google.com'
NAME = 'fake_test3'
PURPOSE = 'A fake test.'
ATTRIBUTES = 'suite:fake_suite3, suite:fake_suite4'
TIME = 'SHORT'
TEST_CATEGORY = 'Functional'
TEST_CLASS = 'audio'
TEST_TYPE = 'client'
DEPENDENCIES = 'fakedep3'
METADATA = {
    'criteria': 'overriding purpose',
    'contacts': ['overriding_contact@google.com'],
    'hw_agnostic': False
}
DOC = '''
a doc
'''

job.run_test('fake_test3')

"""

class Namespace:
    """Stub for mocking args."""

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


class MetadataTest(unittest.TestCase):
    """Test generate_metadata."""

    def setUp(self):
        """Build up a tmp directory to host control files."""
        self.tmp_dir = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.tmp_dir, 'server/site_tests'))
        os.makedirs(os.path.join(self.tmp_dir, 'client/site_tests'))
        self.path1 = os.path.join(self.tmp_dir, 'server/site_tests',
                                  'control.1')
        self.path2 = os.path.join(self.tmp_dir, 'client/site_tests',
                                  'control.2')

        self.path3 = os.path.join(self.tmp_dir, 'client/site_tests',
                                  'control.3')
        self.test1 = control_data.parse_control_string(CONTROL_DATA1,
                                                       raise_warnings=True,
                                                       path=self.path1)
        self.test2 = control_data.parse_control_string(CONTROL_DATA2,
                                                       raise_warnings=True,
                                                       path=self.path2)

        self.test3 = control_data.parse_control_string(CONTROL_DATA3,
                                                       raise_warnings=True,
                                                       path=self.path3)

    def tearDown(self):
        """Delete the tmp directory."""
        shutil.rmtree(self.tmp_dir)

    def test_args(self):
        """Test CLI."""
        parsed = generate_metadata.parse_local_arguments(
                ['-autotest_path', '/tauto/path', '-output_file', 'testout'])
        self.assertEqual(parsed.autotest_path, '/tauto/path')
        self.assertEqual(parsed.output_file, 'testout')

    def test_all_control_files(self):
        """Test all_control_files finds all ctrl files in the expected dirs."""
        with open(self.path1, 'w') as wf:
            wf.write(CONTROL_DATA1)
        with open(self.path2, 'w') as wf:
            wf.write(CONTROL_DATA2)

        files = generate_metadata.all_control_files(
                Namespace(autotest_path=self.tmp_dir))

        # Verify the files are found.
        self.assertEqual(set(files), set([self.path1, self.path2]))

    def test_serialization(self):
        """Test a single control file gets properly serialized."""
        meta_data = generate_metadata.serialized_test_case_metadata(self.test1)
        self.assertEqual(meta_data.test_case.id.value, 'tauto.fake_test1')
        self.assertEqual(meta_data.test_case.name, 'fake_test1')
        # verify tags
        expected_tags = set([
                'test_class:audio', 'suite:fake_suite1',
                'suite:fake_suite2'
        ])
        actual_tags = set([item.value for item in meta_data.test_case.tags])
        self.assertEqual(expected_tags, actual_tags)

        # Verify Deps
        expected_deps = set(['chameleon', 'servo_state:WORKING'])
        actual_deps = set([
                item.value for item in meta_data.test_case.dependencies])
        self.assertEqual(expected_deps, actual_deps)
        # verify harness. This is a bit of a hack but works and keeps import
        # hacking down.
        self.assertIn('tauto', str(meta_data.test_case_exec.test_harness))
        # verify owners
        expected_owners = set(
                [item.email for item in meta_data.test_case_info.owners])
        self.assertEqual(expected_owners,
                         set(['an author with email@google.com']))

        expected_requirements = ['req1', 'req2']
        actual_requirements = [req.value for req in meta_data.test_case_info.requirements]
        self.assertListEqual(expected_requirements, actual_requirements)

        expected_bug_component = 'xyz123'
        actual_bug_component = meta_data.test_case_info.bug_component.value
        self.assertEqual(expected_bug_component, actual_bug_component)

        # Test hw_agnostic when set to True
        self.assertTrue(meta_data.test_case_info.hw_agnostic.value)

        # Test override of criteria and contacts
        meta_data = generate_metadata.serialized_test_case_metadata(self.test3)
        expected_criteria = 'overriding purpose'
        actual_criteria = meta_data.test_case_info.criteria.value
        self.assertEqual(expected_criteria, actual_criteria)

        expected_contacts = set(['overriding_contact@google.com'])
        actual_contacts = set([item.email for item in meta_data.test_case_info.owners])
        self.assertEqual(expected_contacts, actual_contacts)

        # Test hw_agnostic when set to False
        self.assertFalse(meta_data.test_case_info.hw_agnostic.value)

    def test_serialized_test_case_metadata_list(self):
        """Test all control file get properly serialized."""
        serialized_list = generate_metadata.serialized_test_case_metadata_list(
                [
                        generate_metadata.serialized_test_case_metadata(
                                self.test1),
                        generate_metadata.serialized_test_case_metadata(
                                self.test2),
                        generate_metadata.serialized_test_case_metadata(
                                self.test3)
                ])
        names = set([item.test_case.name for item in serialized_list.values])
        self.assertEqual(set(['fake_test1', 'fake_test2', 'fake_test3']), names)


if __name__ == '__main__':
    if six.PY2:
        print('cannot run in py2')
        exit(0)
    else:
        unittest.main()
