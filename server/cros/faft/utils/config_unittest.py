#!/usr/bin/env python3
#
# Copyright 2019 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Unit tests for config.py."""

import json
import os
import shutil
import tempfile
import unittest

# pylint: disable=import-error
import common  # pylint: disable=unused-import

from autotest_lib.client.common_lib import error
from autotest_lib.server.cros.faft.utils import config


# pylint: disable=protected-access

class CanLoadDefaultTestCase(unittest.TestCase):
    """Ensure that configs can load the default JSON"""

    def runTest(self):  # pylint: disable=invalid-name
        """Main test logic"""
        platform = "foo"
        cfg = config.Config(platform)
        self.assertIsInstance(cfg.has_keyboard, bool)


class _MockConfigTestCaseBaseClass(unittest.TestCase):
    """Base class which handles the setup/teardown of mock config files.

    Sub-classes should declare a class attribute, mock_configs,
    as a dict representing all platforms to be written as JSON files.
    This class writes those JSON files during setUp() and deletes them
    during tearDown().
    During runTest(), sub-classes can create config.Config instances by name
    and run assertions as normal.
    """

    mock_configs = None

    def setUp(self):
        """Set up a tempfile containing the test data"""
        if self.mock_configs is None:
            return

        # Setup mock config._SELF_DIR, but remember the original.
        self.temp_dir = tempfile.mkdtemp()
        self.original_self_dir = config._SELF_DIR
        config._SELF_DIR = os.path.join(
                self.temp_dir,
                "src/third_party/autotest/files/server/cros/faft/utils")
        os.makedirs(config._SELF_DIR, exist_ok=True)

        # Write mock config file.
        with open(os.path.join(self.temp_dir,
                               "src/third_party/autotest/CONSOLIDATED.json"),
                  'w',
                  encoding='utf-8') as f:
            json.dump(self.mock_configs, f)

    def tearDown(self):
        """After tests are complete, delete the tempfile"""
        if self.mock_configs is None:
            return
        shutil.rmtree(self.temp_dir)
        config._SELF_DIR = self.original_self_dir


class InheritanceTestCase(_MockConfigTestCaseBaseClass):
    """Ensure that platforms inherit attributes correctly"""

    mock_configs = {
            'DEFAULTS': {
                    'no_override': 'default',
                    'parent_override': 'default',
                    'child_override': 'default',
                    'both_override': 'default',
                    'parent': None
            },
            'childboard': {
                    'child_override': 'child',
                    'both_override': 'child',
                    'parent': 'parentboard'
            },
            'parentboard': {
                    'parent_override': 'parent',
                    'both_override': 'parent'
            }
    }

    def runTest(self):  # pylint: disable=invalid-name
        """Verify that the following situations resolve correctly:

            A platform that inherit some overridess from another platform
            A platform that does not inherit from another platform
            A platform not found in the config file
        """
        child_config = config.Config('childboard')
        self.assertEqual(child_config.no_override, 'default')
        self.assertEqual(child_config.parent_override, 'parent')
        self.assertEqual(child_config.child_override, 'child')
        self.assertEqual(child_config.both_override, 'child')
        with self.assertRaises(AttributeError):
            child_config.foo  # pylint: disable=pointless-statement

        parent_config = config.Config('parentboard')
        self.assertEqual(parent_config.no_override, 'default')
        self.assertEqual(parent_config.parent_override, 'parent')
        self.assertEqual(parent_config.child_override, 'default')
        self.assertEqual(parent_config.both_override, 'parent')

        foo_config = config.Config('foo')
        self.assertEqual(foo_config.no_override, 'default')
        self.assertEqual(foo_config.parent_override, 'default')
        self.assertEqual(foo_config.child_override, 'default')
        self.assertEqual(foo_config.both_override, 'default')

        # While we're here, verify that str(config) doesn't break
        str(child_config)  # pylint: disable=pointless-statement


class ModelOverrideTestCase(_MockConfigTestCaseBaseClass):
    """Verify that models of boards inherit overrides with proper precedence"""
    mock_configs = {
            'parentboard': {
                    'attr1': 'parent_attr1',
                    'attr2': 'parent_attr2',
                    'models': {
                            'modelA': {
                                    'attr1': 'parent_modelA_attr1'
                            }
                    }
            },
            'childboard': {
                    'parent': 'parentboard',
                    'attr1': 'child_attr1',
                    'models': {
                            'modelA': {
                                    'attr1': 'child_modelA_attr1'
                            }
                    }
            },
            'DEFAULTS': {
                    'models': None,
                    'attr1': 'default',
                    'attr2': 'default'
            }
    }

    def runTest(self):  # pylint: disable=invalid-name
        """Run assertions on test data"""
        child_config = config.Config('childboard')
        child_model_a_config = config.Config('childboard', 'modelA')
        child_model_b_config = config.Config('childboard', 'modelB')
        parent_config = config.Config('parentboard')
        parent_model_a_config = config.Config('parentboard', 'modelA')
        parent_model_b_config = config.Config('parentboard', 'modelB')

        self.assertEqual(child_config.attr1, 'child_attr1')
        self.assertEqual(child_config.attr2, 'parent_attr2')
        self.assertEqual(child_model_a_config.attr1, 'child_modelA_attr1')
        self.assertEqual(child_model_a_config.attr2, 'parent_attr2')
        self.assertEqual(child_model_b_config.attr1, 'child_attr1')
        self.assertEqual(child_model_b_config.attr2, 'parent_attr2')
        self.assertEqual(parent_config.attr1, 'parent_attr1')
        self.assertEqual(parent_config.attr2, 'parent_attr2')
        self.assertEqual(parent_model_a_config.attr1, 'parent_modelA_attr1')
        self.assertEqual(parent_model_a_config.attr2, 'parent_attr2')
        self.assertEqual(parent_model_b_config.attr1, 'parent_attr1')
        self.assertEqual(parent_model_b_config.attr2, 'parent_attr2')


class DirectSelfInheritanceTestCase(_MockConfigTestCaseBaseClass):
    """Ensure that a config which inherits from itself raises an error."""

    mock_configs = {
        'selfloop': {
            'parent': 'selfloop',
        },
    }

    def runTest(self):  # pylint: disable=invalid-name
        """Run assertions on test data."""
        with self.assertRaises(error.TestError):
            config.Config('selfloop')


class IndirectSelfInheritanceTestCase(_MockConfigTestCaseBaseClass):
    """Ensure that configs which inherit from each other raise an error."""

    mock_configs = {
        'indirectloop1': {
            'parent': 'indirectloop2',
        },
        'indirectloop2': {
            'parent': 'indirectloop1',
        },
        'indirectloop3': {
            'parent': 'indirectloop1',
        },
    }

    def runTest(self):  # pylint: disable=invalid-name
        """Run assertions on test data."""
        with self.assertRaises(error.TestError):
            config.Config('indirectloop1')
        with self.assertRaises(error.TestError):
            config.Config('indirectloop3')


class FindMostSpecificConfigTestCase(_MockConfigTestCaseBaseClass):
    """Ensure that configs named like $BOARD-kernelnext load $BOARD.json."""

    mock_configs = {
            'DEFAULTS': {},
            'samus': {},
            'veyron': {},
            'minnie': {'parent': 'veyron'},
    }

    def runTest(self):  # pylint: disable=invalid-name
        """Ensure that configs named like $BOARD-kernelnext load $BOARD.json."""
        self.assertEqual(config.Config('samus-kernelnext').platform, 'samus')
        self.assertEqual(config.Config('samus-arc-r').platform, 'samus')
        self.assertEqual(config.Config('veyron_minnie').platform, 'minnie')
        self.assertEqual(config.Config('veyron_monroe').platform, 'veyron')
        self.assertEqual(
                config.Config('veyron_minnie-arc-r').platform, 'minnie')
        self.assertEqual(
                config.Config('veyron_monroe-arc-r').platform, 'veyron')


class FindJSONFile(_MockConfigTestCaseBaseClass):
    """Ensure CONSOLIDATED.json can be found in many locations."""

    mock_configs = {}

    def runTest(self):  # pylint: disable=invalid-name
        """Check all the possible paths."""
        # Autotest ebuild location.
        autotest_path = os.path.join(
                self.temp_dir, "src/third_party/autotest/CONSOLIDATED.json")
        with open(autotest_path, 'w', encoding='utf-8') as f:
            json.dump(self.mock_configs, f)
        # Chroot location.
        chroot_dir = os.path.join(self.temp_dir,
                                  "src/platform/fw-testing-configs")
        chroot_path = os.path.join(chroot_dir, "CONSOLIDATED.json")
        os.makedirs(chroot_dir, exist_ok=True)
        with open(chroot_path, 'w', encoding='utf-8') as f:
            json.dump(self.mock_configs, f)
        # Legacy location.
        legacy_dir = os.path.join(
                self.temp_dir,
                "src/third_party/autotest/files/server/cros/faft/"
                "fw-testing-configs")
        legacy_path = os.path.join(legacy_dir, "CONSOLIDATED.json")
        os.makedirs(legacy_dir, exist_ok=True)
        with open(legacy_path, 'w', encoding='utf-8') as f:
            json.dump(self.mock_configs, f)
        # An invalid location.
        with open(os.path.join(
                self.temp_dir,
                "src/third_party/autotest/files/server/cros/faft/"
                "utils/CONSOLIDATED.json"),
                  'w',
                  encoding='utf-8') as f:
            json.dump(self.mock_configs, f)

        self.assertEqual(config._consolidated_json_fp(), autotest_path)
        os.remove(autotest_path)
        self.assertEqual(config._consolidated_json_fp(), chroot_path)
        os.remove(chroot_path)
        self.assertEqual(config._consolidated_json_fp(), legacy_path)
        os.remove(legacy_path)
        with self.assertRaises(error.TestError):
            config._consolidated_json_fp()



if __name__ == '__main__':
    unittest.main()
