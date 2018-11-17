# Copyright 2018 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# This file has been automatically generated. Do not edit!

AUTHOR = 'ARC++ Team'
NAME = 'cheets_CTS_P.x86.CtsDeqpTestCases.dEQP-VK.glsl'
ATTRIBUTES = 'suite:cts_P'
DEPENDENCIES = 'arc, cts_abi_x86'
JOB_RETRIES = 1
TEST_TYPE = 'server'
TIME = 'MEDIUM'
MAX_RESULT_SIZE_KB = 512000
PRIORITY = 50
DOC = 'Run module CtsDeqpTestCases.dEQP-VK.glsl of the Android Compatibility Test Suite (CTS) using x86 ABI in the ARC++ container.'

def run_CTS(machine):
    host_list = [hosts.create_host(machine)]
    job.run_test(
        'cheets_CTS_P',
        hosts=host_list,
        iterations=1,
        max_retry=3,
        needs_push_media=False,
        tag='x86.CtsDeqpTestCases.dEQP-VK.glsl',
        test_name='cheets_CTS_P.x86.CtsDeqpTestCases.dEQP-VK.glsl',
        run_template=['run', 'commandAndExit', 'cts', '--include-filter', 'CtsDeqpTestCases', '--module', 'CtsDeqpTestCases', '--test', 'dEQP-VK.glsl.*', '--logcat-on-failure'],
        retry_template=['run', 'commandAndExit', 'retry', '--retry', '{session_id}'],
        target_module='CtsDeqpTestCases',
        target_plan=None,
        bundle='x86',
        warn_on_test_retry=False,
        retry_manual_tests=True,
        timeout=3600)

parallel_simple(run_CTS, machines)
