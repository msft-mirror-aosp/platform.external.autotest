
# Copyright 2020 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# !!! GENERATED FILE. DO NOT EDIT !!!

load('//metadata/test_common.star', 'test_common')

def define_tests():
    return [
        test_common.define_test(
            'security/CpuVulnerabilities',
            suites = ['bvt-perbuild'],
        ),
        test_common.define_test(
            'security/Libcontainer',
            suites = [],
        ),
        test_common.define_test(
            'security/OpenSSLRegressions',
            suites = [],
        ),
        test_common.define_test(
            'security/ProcessManagementPolicy',
            suites = ['bvt-perbuild'],
        ),
        test_common.define_test(
            'security/RendererSandbox',
            suites = ['security'],
        ),
        test_common.define_test(
            'security/RootfsOwners',
            suites = ['bvt-perbuild'],
        ),
        test_common.define_test(
            'security/SandboxLinuxUnittests',
            suites = ['bvt-perbuild'],
        ),
        test_common.define_test(
            'security/SeccompSyscallFilters',
            suites = ['security'],
        ),
        test_common.define_test(
            'security/SessionManagerDbusEndpoints',
            suites = ['bvt-perbuild'],
        ),
        test_common.define_test(
            'security/SysVIPC',
            suites = ['security'],
        ),
        test_common.define_test(
            'security/kASLR',
            suites = ['security_weekly'],
        ),
        test_common.define_test(
            'security/x86Registers',
            suites = ['security'],
        )
    ]
