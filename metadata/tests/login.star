
# Copyright 2020 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# !!! GENERATED FILE. DO NOT EDIT !!!

load('//metadata/test_common.star', 'test_common')

def define_tests():
    return [
        test_common.define_test(
            'login/ChromeProfileSanitary',
            suites = ['regression'],
        ),
        test_common.define_test(
            'login/CryptohomeDataLeak',
            suites = ['bvt-perbuild'],
        ),
        test_common.define_test(
            'login/CryptohomeIncognito',
            suites = [],
        ),
        test_common.define_test(
            'login/CryptohomeOwnerQuery',
            suites = ['bvt-perbuild'],
        ),
        test_common.define_test(
            'login/GaiaLogin',
            suites = ['bvt-perbuild'],
        ),
        test_common.define_test(
            'login/LoginSuccess',
            suites = ['bvt-inline', 'dev_drone_image_test', 'push_to_prod', 'skylab_staging_test', 'smoke'],
        ),
        test_common.define_test(
            'login/MultipleSessions',
            suites = ['bvt-perbuild'],
        ),
        test_common.define_test(
            'login/OobeLocalization',
            suites = ['experimental'],
        ),
        test_common.define_test(
            'login/UnicornLogin',
            suites = ['bvt-perbuild'],
        ),
        test_common.define_test(
            'login/UserPolicyKeys',
            suites = ['bvt-inline', 'smoke'],
        )
    ]
