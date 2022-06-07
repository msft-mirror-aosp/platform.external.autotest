#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright 2020 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
import os

import common
import unittest

from autotest_lib.contrib.upload_results import *

class UploadResultsTestCase(unittest.TestCase):

    # test mandatory fields are filled on load
    def test_generate_job_serialize(self):
        rp = ResultsParser
        job1 = rp.parse(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'data', 'results-1-test_UploadResults'), False)
        job2 = rp.parse(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'data', 'results-1-test_UploadResults'), False)

        # test mandatory fields are populated
        assert job1.machine_group == 'test_model'
        assert job1.board == 'test_board'
        assert job1.suite == 'default_suite'
        assert job1.label == 'chroot/test_UploadResults'

        # test uniqueness
        assert job1.afe_job_id != job2.afe_job_id

    # test mandatory fields are filled after save and reload
    def test_persist_and_reload_job(self):
        rp = ResultsParser
        job1 = rp.parse(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'data', 'results-1-test_UploadResults'), False)
        job2 = rp.parse(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'data', 'results-1-test_UploadResults'), True)

        assert job1.machine_group == job2.machine_group
        assert job1.board == job2.board
        assert job1.suite == job2.suite
        assert job1.label == job2.label

        # even with a reload, we should *still* have a unique job
        assert job1.afe_job_id != job2.afe_job_id

if __name__ == '__main__':
    unittest.main()