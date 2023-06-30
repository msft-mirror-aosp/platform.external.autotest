#!/usr/bin/env python
"""
This script generates autotest control files for dEQP. It supports
1) Generate control files for tests with Passing expectations.
2) Generate control files to run tests that are not passing.
3) Decomposing a test into shards. Ideally shard_count is chosen such that
   each shard will run less than 1 minute. It mostly makes sense in
   combination with "hasty".
"""
import os
from collections import namedtuple
# Use 'sudo pip install enum34' to install.
from enum import Enum
from string import Template

Test = namedtuple(
        'Test',
        'filter, suite, shards, time, tag, api, caselist, perf_failure_description'
)

ATTRIBUTES_PVS = ('suite:deqp, suite:graphics_per-week, suite:graphics_system, '
                  'suite:pvs-graphics')
ATTRIBUTES_DAILY = 'suite:deqp, suite:graphics_per-day, suite:graphics_system'
ATTRIBUTES_WEEKLY = 'suite:deqp, suite:graphics_per-week, suite:graphics_system'

class Suite(Enum):
    none = 1
    daily = 2
    weekly = 3
    pvs = 4


deqp_dir = '/usr/local/deqp'
caselists = 'caselists'
GLES2_FILE = os.path.join(deqp_dir, caselists, 'gles2.txt')
GLES3_FILE = os.path.join(deqp_dir, caselists, 'gles3.txt')
GLES31_FILE = os.path.join(deqp_dir, caselists, 'gles31.txt')
VK_FILE = os.path.join(deqp_dir, caselists, 'vk.txt')

tests = [
        Test('dEQP-GLES2',
             Suite.pvs,
             shards=1,
             time='MEDIUM',
             tag='gles2',
             api='gles2',
             caselist=GLES2_FILE,
             perf_failure_description='Failures_GLES2'),
        Test('dEQP-GLES3',
             Suite.pvs,
             shards=1,
             time='LONG',
             tag='gles3',
             api='gles3',
             caselist=GLES3_FILE,
             perf_failure_description='Failures_GLES3'),
        Test('dEQP-GLES31',
             Suite.pvs,
             shards=1,
             time='LONG',
             tag='gles31',
             api='gles31',
             caselist=GLES31_FILE,
             perf_failure_description='Failures_GLES31'),
        Test('dEQP-VK',
             Suite.weekly,
             shards=10,
             time='LONG',
             tag='vk',
             api='vk',
             caselist=VK_FILE,
             perf_failure_description='Failures_VK'),
]

CONTROLFILE_TEMPLATE = Template("\
# Copyright 2015-2021 The ChromiumOS Authors\n\
# Use of this source code is governed by a BSD-style license that can be\n\
# found in the LICENSE file.\n\
\n\
# Please do not edit this file! It has been created by generate_controlfiles.py.\n\
\n\
PY_VERSION = 3\n\
NAME = '$testname'\n\
AUTHOR = 'chromeos-gfx'\n\
PURPOSE = 'Run the drawElements Quality Program test suite with deqp-runner.'\n\
CRITERIA = 'All of the individual tests must pass unless marked as known failures.'\n\
ATTRIBUTES = '$attributes'\n\
TIME = '$time'\n\
TEST_CATEGORY = 'Functional'\n\
TEST_CLASS = 'graphics'\n\
TEST_TYPE = 'client'\n\
MAX_RESULT_SIZE_KB = 131072\n\
EXTENDED_TIMEOUT = 10500\n\
DOC = 'This test runs the drawElements Quality Program test suite.'\n\
METADATA = {\n\
  'contacts': [\n\
    'chromeos-gfx-gpu@google.com',\n\
    'ihf@google.com'\n\
  ],\n\
  'bug_component': 'b:995569',\n\
  'criteria': 'Pass the drawElements Quality Program test suite.'\n\
}\n\
job.run_test('graphics_parallel_dEQP',\n\
             tag = '$tag',\n\
             opts = args + [\n\
                 'api=$api',\n\
                 'caselist=$caselist',\n\
                 'perf_failure_description=$perf_failure_description',\n\
                 'shard_number=$shard',\n\
                 'shard_count=$shards'\n\
             ])")


def get_controlfilename(test, shard=0):
    return 'control.%s' % get_name(test, shard)


def get_attributes(test):
    if test.suite == Suite.pvs:
        return ATTRIBUTES_PVS
    if test.suite == Suite.daily:
        return ATTRIBUTES_DAILY
    if test.suite == Suite.weekly:
        return ATTRIBUTES_WEEKLY
    return ''


def get_time(test):
    return test.time


def get_name(test, shard):
    name = test.filter.replace('dEQP-', '', 1).lower()
    if test.shards > 1:
        name = '%s.%d' % (name, shard)
    return name


def get_testname(test, shard=0):
    return 'graphics_parallel_dEQP.%s' % get_name(test, shard)


def write_controlfile(filename, content):
    print(('Writing %s.' % filename))
    with open(filename, 'w+') as f:
        f.write(content)


def write_controlfiles(test):
    attributes = get_attributes(test)
    time = get_time(test)

    for shard in range(0, test.shards):
        testname = get_testname(test, shard)
        filename = get_controlfilename(test, shard)
        d = dict(
                testname=testname,
                attributes=attributes,
                time=time,
                subset='Pass',
                shard=shard,
                shards=test.shards,
                api=test.api,
                caselist=test.caselist,
                tag=test.tag,
                perf_failure_description=test.perf_failure_description
        )
        content = CONTROLFILE_TEMPLATE.substitute(d)
        write_controlfile(filename, content)


def main():
    for test in tests:
        write_controlfiles(test)


if __name__ == "__main__":
    main()
