# Copyright 2018 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# This file has been automatically generated. Do not edit!

AUTHOR = 'n/a'
NAME = 'cheets_CTS_P.x86.CtsDeqpTestCases.dEQP-VK.subgroups.b'
METADATA = {
    "contacts": ["arc-cts-eng@google.com"],
    "bug_component": "b:183644",
    "criteria": "A part of Android CTS",
}
ATTRIBUTES = 'suite:cts_P, suite:cts'
DEPENDENCIES = 'arc, cts_abi_x86'
HW_DEPS = ['android-container-pi']
JOB_RETRIES = 1
TEST_TYPE = 'server'
TIME = 'MEDIUM'
MAX_RESULT_SIZE_KB = 512000
PRIORITY = 50
DOC = 'n/a'

def run_TS(machine):
    host_list = [hosts.create_host(machine)]
    job.run_test(
        'cheets_CTS_P',
        hosts=host_list,
        iterations=1,
        tag='x86.CtsDeqpTestCases.dEQP-VK.subgroups.b',
        test_name='cheets_CTS_P.x86.CtsDeqpTestCases.dEQP-VK.subgroups.b',
        run_template=['run', 'commandAndExit', 'cts', '--include-filter', 'CtsDeqpTestCases', '--module', 'CtsDeqpTestCases', '--test', 'dEQP-VK.subgroups.b*'],
        retry_template=['run', 'commandAndExit', 'retry', '--retry', '{session_id}'],
        target_module='CtsDeqpTestCases.dEQP-VK.subgroups.b',
        target_plan=None,
        bundle='x86',
        retry_manual_tests=True,
        warn_on_test_retry=False,
        timeout=43200)

parallel_simple(run_TS, machines)
