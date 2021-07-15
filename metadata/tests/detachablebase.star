
# Copyright 2020 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# !!! GENERATED FILE. DO NOT EDIT !!!

load('//metadata/test_common.star', 'test_common')

def define_tests():
    return [
        test_common.define_test(
            'detachablebase/TriggerHammerd',
            suites = ['bvt-perbuild'],
            main_package = 'autotest_lib.client.site_tests.detachablebase_TriggerHammerd.detachablebase_TriggerHammerd',
        )
    ]
