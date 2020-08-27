
# Copyright 2020 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# !!! GENERATED FILE. DO NOT EDIT !!!

load('//metadata/test_common.star', 'test_common')

def define_tests():
    return [
        test_common.define_test(
            'dummy/Fail',
            suites = ['another_suite', 'dev_drone_image_test', 'dummy', 'push_to_prod', 'skylab_staging_test'],
        ),
        test_common.define_test(
            'dummy/FailServer',
            suites = [],
        ),
        test_common.define_test(
            'dummy/Pass',
            suites = ['dev_drone_image_test', 'dummy', 'dummyclientretries', 'push_to_prod', 'skylab_staging_test', 'something_else'],
        ),
        test_common.define_test(
            'dummy/PassServer',
            suites = ['dummy_server'],
        ),
        test_common.define_test(
            'dummy/RepeatArgs',
            suites = [],
        ),
        test_common.define_test(
            'dummy/SynchronousOffload',
            suites = ['offloads'],
        ),
        test_common.define_test(
            'dummy/SynchronousOffloadServer',
            suites = ['offloads'],
        )
    ]
