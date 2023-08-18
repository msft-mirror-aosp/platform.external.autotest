#!/usr/bin/python3

# Copyright 2021 The ChromiumOS Authors
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

CONTROL_DATA_1 = """
# Copyright 2021 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

NAME = 'fake_test1'
ATTRIBUTES = 'suite:fake_suite1, suite:fake_suite2'
TEST_TYPE = 'client'
DEPENDENCIES = 'chameleon,servo_state:WORKING'
METADATA = {
    'contacts': ['name@google.com'],
}

job.run_test('fake_test1')
"""

CONTROL_DATA_2 = """
# Copyright 2021 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

NAME = 'fake_test2'
METADATA = {
    'contacts': ['name@google.com'],
}
ATTRIBUTES = 'suite:fake_suite1, suite:fake_suite2'
TEST_TYPE = 'server'
DEPENDENCIES = 'fakedep2'

job.run_test('fake_test2')
"""

CONTROL_DATA_3 = """
# Copyright 2021 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

NAME = 'fake_test3'
AUTHOR = 'outdated author field'
ATTRIBUTES = 'suite:fake_suite3, suite:fake_suite4'
TEST_TYPE = 'client'
DEPENDENCIES = 'chameleon,servo_state:WORKING'
METADATA = {
    'criteria': 'overriding purpose',
    'bug_component': 'xyz123',
    'contacts': ['overriding_contact@google.com'],
    'hw_agnostic': False,
    'life_cycle_stage': 'in_development',
    'requirements': ['req1', 'req2'],
    'variant_category': 'xyz123'
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
        parsed_1 = control_data.parse_control_string(CONTROL_DATA_1,
                                                     raise_warnings=True)
        parsed_2 = control_data.parse_control_string(CONTROL_DATA_2,
                                                     raise_warnings=True)
        parsed_3 = control_data.parse_control_string(CONTROL_DATA_3,
                                                     raise_warnings=True)
        self.metadata_1 = generate_metadata.serialized_test_case_metadata(
                parsed_1)
        self.metadata_2 = generate_metadata.serialized_test_case_metadata(
                parsed_2)
        self.metadata_3 = generate_metadata.serialized_test_case_metadata(
                parsed_3)

    def test_args(self):
        """Test CLI."""
        parsed = generate_metadata.parse_local_arguments(
                ['-autotest_path', '/tauto/path', '-output_file', 'testout'])
        self.assertEqual(parsed.autotest_path, '/tauto/path')
        self.assertEqual(parsed.output_file, 'testout')

    def test_control_files_are_findable(self):
        """Test all_control_files finds all ctrl files in the expected dirs."""
        # Build up a tmp directory to host control files.
        tmp_dir = tempfile.mkdtemp()
        server_path = os.path.join(tmp_dir, 'server/site_tests')
        client_path = os.path.join(tmp_dir, 'client/site_tests')
        os.makedirs(server_path)
        os.makedirs(client_path)
        server_file = os.path.join(server_path, 'control')
        client_file = os.path.join(client_path, 'control')
        with open(server_file, 'w') as wf:
            wf.write(CONTROL_DATA_1)
        with open(client_file, 'w') as wf:
            wf.write(CONTROL_DATA_2)

        files = generate_metadata.all_control_files(
                Namespace(autotest_path=tmp_dir))

        # Verify the files are found.
        self.assertEqual(set(files), set([client_file, server_file]))

        # Delete the tmp directory.
        shutil.rmtree(tmp_dir)

    def test_serialization(self):
        """Test a single control file gets properly serialized."""
        metadata = self.metadata_3

        # Verify name.
        self.assertEqual(metadata.test_case.id.value, 'tauto.fake_test3')
        self.assertEqual(metadata.test_case.name, 'fake_test3')

        # Verify tags.
        expected_tags = set(['suite:fake_suite3', 'suite:fake_suite4'])
        actual_tags = set([item.value for item in metadata.test_case.tags])
        self.assertEqual(expected_tags, actual_tags)

        # Verify Deps.
        expected_deps = set(['chameleon', 'servo_state:WORKING'])
        actual_deps = set(
                [item.value for item in metadata.test_case.dependencies])
        self.assertEqual(expected_deps, actual_deps)

        # Verify harness. This is a bit of a hack but works and keeps import
        # hacking down.
        self.assertIn('tauto', str(metadata.test_case_exec.test_harness))

        # Verify owners.
        expected_owners = set(
                [item.email for item in metadata.test_case_info.owners])
        self.assertEqual(expected_owners,
                         set(['overriding_contact@google.com']))

        # Verify requirements.
        expected_requirements = ['req1', 'req2']
        actual_requirements = [
                req.value for req in metadata.test_case_info.requirements
        ]
        self.assertListEqual(expected_requirements, actual_requirements)

        # Verify bug_component.
        expected_bug_component = 'xyz123'
        actual_bug_component = metadata.test_case_info.bug_component.value
        self.assertEqual(expected_bug_component, actual_bug_component)

        # Verify variant_category.
        expected_variant_category = 'xyz123'
        actual_variant_category = metadata.test_case_info.variant_category.value
        self.assertEqual(expected_variant_category, actual_variant_category)

        # Verify criteria.
        expected_criteria = 'overriding purpose'
        actual_criteria = metadata.test_case_info.criteria.value
        self.assertEqual(expected_criteria, actual_criteria)

        # Verify life_cycle_stage.
        expected_life_cycle = 2
        actual_life_cycle = metadata.test_case_info.life_cycle_stage.value
        self.assertEqual(expected_life_cycle, actual_life_cycle)

    def test_hw_agnostic(self):
        """Test the hw_agnostic field when it is both true and false."""
        DATA_TRUE = ('NAME = "test_name"\n'
                     'TEST_TYPE = "client"\n'
                     'METADATA = {"hw_agnostic": True,\n'
                     '"contacts": ["email@google.com"]}')
        parsed_true = control_data.parse_control_string(DATA_TRUE,
                                                        raise_warnings=True)
        metadata_true = generate_metadata.serialized_test_case_metadata(
                parsed_true)
        self.assertTrue(metadata_true.test_case_info.hw_agnostic.value)

        DATA_FALSE = ('NAME = "test_name"\n'
                      'TEST_TYPE = "client"\n'
                      'METADATA = {"hw_agnostic": False,\n'
                      '"contacts": ["email@google.com"]}')
        parsed_false = control_data.parse_control_string(DATA_FALSE,
                                                         raise_warnings=True)
        metadata_false = generate_metadata.serialized_test_case_metadata(
                parsed_false)
        self.assertFalse(metadata_false.test_case_info.hw_agnostic.value)


    def test_serialized_test_case_metadata_list(self):
        """Test that a list of control files get properly serialized."""
        serialized_list = generate_metadata.serialized_test_case_metadata_list(
                [self.metadata_1, self.metadata_2, self.metadata_3])
        names = set([item.test_case.name for item in serialized_list.values])
        self.assertEqual(set(['fake_test1', 'fake_test2', 'fake_test3']), names)


if __name__ == '__main__':
    if six.PY2:
        print('cannot run in py2')
        exit(0)
    else:
        unittest.main()
