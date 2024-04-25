# Copyright 2018 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# This file has been automatically generated. Do not edit!

AUTHOR = 'n/a'
NAME = 'cheets_CTS_P.arm.CtsDeqpTestCases.dEQP-VK.glsl'
METADATA = {
    "contacts": ["arc-cts-eng@google.com"],
    "bug_component": "b:183644",
    "criteria": "A part of Android CTS",
}
ATTRIBUTES = 'suite:cts_P, suite:cts'
DEPENDENCIES = 'arc'
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
        tag='arm.CtsDeqpTestCases.dEQP-VK.glsl',
        test_name='cheets_CTS_P.arm.CtsDeqpTestCases.dEQP-VK.glsl',
        run_template=['run', 'commandAndExit', 'cts', '--include-filter', 'CtsDeqpTestCases', '--module', 'CtsDeqpTestCases', '--test', 'dEQP-VK.glsl.*'],
        retry_template=['run', 'commandAndExit', 'retry', '--retry', '{session_id}'],
        target_module='CtsDeqpTestCases.dEQP-VK.glsl',
        target_plan=None,
        bundle='arm',
        retry_manual_tests=True,
        warn_on_test_retry=False,
        timeout=43200)

parallel_simple(run_TS, machines)
