
# Copyright 2020 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# !!! GENERATED FILE. DO NOT EDIT !!!

load('//metadata/test_common.star', 'test_common')

def define_tests():
    return [
        test_common.define_test(
            'kernel/AsyncDriverProbe',
            suites = ['kernel_daily_regression'],
        ),
        test_common.define_test(
            'kernel/CrosECSysfsAccel',
            suites = ['kernel_daily_regression'],
        ),
        test_common.define_test(
            'kernel/Delay',
            suites = ['kernel_daily_regression'],
        ),
        test_common.define_test(
            'kernel/ExternalUsbPeripheralsDetectionTest',
            suites = [],
        ),
        test_common.define_test(
            'kernel/FirmwareRequest',
            suites = ['kernel_daily_regression'],
        ),
        test_common.define_test(
            'kernel/IdlePerf',
            suites = ['crosbolt_perf_weekly'],
        ),
        test_common.define_test(
            'kernel/Ktime',
            suites = ['kernel_daily_regression'],
        ),
        test_common.define_test(
            'kernel/Lmbench',
            suites = ['kernel_per-build_benchmarks'],
        ),
        test_common.define_test(
            'kernel/MemoryRamoop',
            suites = ['experimental'],
        ),
        test_common.define_test(
            'kernel/SchedBandwith',
            suites = ['hwqual'],
        ),
        test_common.define_test(
            'kernel/TPMStress',
            suites = ['kernel_daily_regression', 'stress'],
        )
    ]
