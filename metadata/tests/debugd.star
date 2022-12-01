
# Copyright 2020 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# !!! GENERATED FILE. DO NOT EDIT !!!

load('//metadata/test_common.star', 'test_common')

def define_tests():
    return [
        test_common.define_test(
            'debugd/DevTools',
            suites = [],
            main_package = 'autotest_lib.server.site_tests.debugd_DevTools.debugd_DevTools',
        )
    ]
