
# Copyright 2020 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# !!! GENERATED FILE. DO NOT EDIT !!!

load('//metadata/test_common.star', 'test_common')

def define_tests():
    return [
        test_common.define_test(
            'telemetry/AFDOGenerate',
            suites = ['AFDO_record'],
        ),
        test_common.define_test(
            'telemetry/AFDOGenerateClient',
            suites = ['AFDO_page_replay'],
        ),
        test_common.define_test(
            'telemetry/Crosperf',
            suites = [],
        ),
        test_common.define_test(
            'telemetry/Sanity',
            suites = ['bvt-perbuild', 'smoke'],
        ),
        test_common.define_test(
            'telemetry/ScrollingActionTests',
            suites = [],
        )
    ]
