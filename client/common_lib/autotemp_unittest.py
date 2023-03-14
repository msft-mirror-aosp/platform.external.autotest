#!/usr/bin/python3

import unittest, os
import common
from autotest_lib.client.common_lib import autotemp


class tempfile_test(unittest.TestCase):
    """Test autotemp.tempfile methods."""

    def test_create_file(self):
        temp = autotemp.tempfile(unique_id='file')
        self.assertTrue(os.path.exists(temp.name))


    def test_create_file_context_manager(self):
        with autotemp.tempfile(unique_id='file') as t:
            name = t.name
            self.assertTrue(os.path.exists(name))
        self.assertFalse(os.path.exists(name))

    def test_clean(self):
        temp = autotemp.tempfile(unique_id='clean')
        # clean up sets name to None so we preserve it this way
        name = temp.name
        self.assertTrue(os.path.exists(name))
        temp.clean()
        self.assertFalse(os.path.exists(name))


    def test_del(self):
        tmp_file = autotemp.tempfile(unique_id='del')
        name = tmp_file.name
        self.assertTrue(os.path.exists(name))
        tmp_file.__del__()
        self.assertFalse(os.path.exists(name))


class tempdir(unittest.TestCase):
    """Test autotemp.tempdir methods."""

    def test_create_dir(self):
        temp_dir = autotemp.tempdir(unique_id='dir')
        self.assertTrue(os.path.exists(temp_dir.name))
        self.assertTrue(os.path.isdir(temp_dir.name))


    def test_create_dir(self):
        with autotemp.tempdir(unique_id='dir') as t_dir:
            name = t_dir.name
            self.assertTrue(os.path.exists(name))
            self.assertTrue(os.path.isdir(name))
        self.assertFalse(os.path.exists(name))

    def test_clean(self):
        temp_dir = autotemp.tempdir(unique_id='clean')
        name = temp_dir.name
        self.assertTrue(os.path.exists(name))
        temp_dir.clean()
        self.assertFalse(os.path.exists(name))


    def test_del(self):
        temp_dir = autotemp.tempdir(unique_id='del')
        name = temp_dir.name
        self.assertTrue(os.path.exists(name))
        temp_dir.__del__()
        self.assertFalse(os.path.exists(name))


if __name__ == '__main__':
    unittest.main()
