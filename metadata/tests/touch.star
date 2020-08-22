
# Copyright 2020 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# !!! GENERATED FILE. DO NOT EDIT !!!

load('//metadata/test_common.star', 'test_common')

def define_tests():
    return [
        test_common.define_test(
            'touch/GestureNav',
            suites = ['touch'],
        ),
        test_common.define_test(
            'touch/MouseScroll',
            suites = ['touch'],
        ),
        test_common.define_test(
            'touch/ScrollDirection',
            suites = ['touch'],
        ),
        test_common.define_test(
            'touch/StylusTaps',
            suites = ['touch'],
        ),
        test_common.define_test(
            'touch/TabSwitch',
            suites = ['touch'],
        ),
        test_common.define_test(
            'touch/TapSettings',
            suites = ['touch'],
        ),
        test_common.define_test(
            'touch/TouchscreenScroll',
            suites = ['touch'],
        ),
        test_common.define_test(
            'touch/TouchscreenTaps',
            suites = ['touch'],
        ),
        test_common.define_test(
            'touch/TouchscreenZoom',
            suites = ['touch'],
        )
    ]
