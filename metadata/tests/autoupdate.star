
# Copyright 2020 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# !!! GENERATED FILE. DO NOT EDIT !!!

load('//metadata/test_common.star', 'test_common')

def define_tests():
    return [
        test_common.define_test(
            'autoupdate/Backoff',
            suites = [],
        ),
        test_common.define_test(
            'autoupdate/BadMetadata',
            suites = [],
        ),
        test_common.define_test(
            'autoupdate/CannedOmahaUpdate',
            suites = [],
        ),
        test_common.define_test(
            'autoupdate/CatchBadSignatures',
            suites = ['au-perbuild'],
        ),
        test_common.define_test(
            'autoupdate/CrashBrowserAfterUpdate',
            suites = [],
        ),
        test_common.define_test(
            'autoupdate/EOL',
            suites = ['au-perbuild'],
        ),
        test_common.define_test(
            'autoupdate/EndToEndTest',
            suites = [],
        ),
        test_common.define_test(
            'autoupdate/InstallAndUpdateDLC',
            suites = [],
        ),
        test_common.define_test(
            'autoupdate/LoginStartUpdateLogout',
            suites = [],
        ),
        test_common.define_test(
            'autoupdate/Rollback',
            suites = ['bvt-installer'],
        ),
        test_common.define_test(
            'autoupdate/StartOOBEUpdate',
            suites = [],
        ),
        test_common.define_test(
            'autoupdate/StatefulCompatibility',
            suites = [],
        ),
        test_common.define_test(
            'autoupdate/UpdateFromUI',
            suites = [],
        ),
        test_common.define_test(
            'autoupdate/UrlSwitch',
            suites = [],
        ),
        test_common.define_test(
            'autoupdate/UserData',
            suites = [],
        )
    ]
