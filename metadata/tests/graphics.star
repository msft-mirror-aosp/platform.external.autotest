
# Copyright 2020 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# !!! GENERATED FILE. DO NOT EDIT !!!

load('//metadata/test_common.star', 'test_common')

def define_tests():
    return [
        test_common.define_test(
            'graphics/GLAPICheck',
            suites = ['bvt-perbuild', 'graphics', 'graphics_per-day', 'graphics_system', 'hwqual'],
        ),
        test_common.define_test(
            'graphics/GLBench',
            suites = ['graphics', 'graphics_per-day', 'graphics_system'],
        ),
        test_common.define_test(
            'graphics/GLMark2',
            suites = ['graphics', 'graphics_per-day', 'graphics_system'],
        ),
        test_common.define_test(
            'graphics/Gbm',
            suites = ['bvt-perbuild', 'graphics', 'graphics_per-day', 'graphics_system'],
        ),
        test_common.define_test(
            'graphics/Gralloc',
            suites = ['graphics', 'graphics_per-day'],
        ),
        test_common.define_test(
            'graphics/Idle',
            suites = ['bvt-perbuild', 'graphics', 'graphics_per-day', 'graphics_system'],
        ),
        test_common.define_test(
            'graphics/KernelConfig',
            suites = ['graphics_per-day', 'graphics_system'],
        ),
        test_common.define_test(
            'graphics/KernelMemory',
            suites = ['bvt-perbuild', 'graphics', 'graphics_per-day', 'graphics_system'],
        ),
        test_common.define_test(
            'graphics/LibDRM',
            suites = ['bvt-perbuild', 'graphics', 'graphics_per-day', 'graphics_system'],
        ),
        test_common.define_test(
            'graphics/PerfControl',
            suites = ['bvt-perbuild', 'graphics', 'graphics_per-day', 'graphics_system'],
        ),
        test_common.define_test(
            'graphics/PowerConsumption',
            suites = ['bvt-perbuild'],
        ),
        test_common.define_test(
            'graphics/SanAngeles',
            suites = ['graphics', 'graphics_per-day', 'graphics_system'],
        ),
        test_common.define_test(
            'graphics/Sanity',
            suites = ['graphics', 'graphics_per-day', 'graphics_system'],
        ),
        test_common.define_test(
            'graphics/VTSwitch',
            suites = ['bvt-perbuild', 'graphics_per-day'],
        ),
        test_common.define_test(
            'graphics/WebGLAquarium',
            suites = ['bvt-perbuild', 'crosbolt_perf_perbuild', 'graphics', 'graphics_browser', 'graphics_per-day', 'partners'],
        ),
        test_common.define_test(
            'graphics/WebGLManyPlanetsDeep',
            suites = ['graphics', 'graphics_browser', 'graphics_per-day', 'partners'],
        )
    ]
