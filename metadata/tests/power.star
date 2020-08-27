
# Copyright 2020 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# !!! GENERATED FILE. DO NOT EDIT !!!

load('//metadata/test_common.star', 'test_common')

def define_tests():
    return [
        test_common.define_test(
            'power/AudioDetector',
            suites = ['bvt-perbuild'],
        ),
        test_common.define_test(
            'power/BacklightControl',
            suites = [],
        ),
        test_common.define_test(
            'power/BatteryCharge',
            suites = [],
        ),
        test_common.define_test(
            'power/BatteryDrain',
            suites = [],
        ),
        test_common.define_test(
            'power/BrightnessResetAfterReboot',
            suites = ['bvt-perbuild', 'partners'],
        ),
        test_common.define_test(
            'power/CPUFreq',
            suites = ['power_build'],
        ),
        test_common.define_test(
            'power/CPUIdle',
            suites = ['power_build'],
        ),
        test_common.define_test(
            'power/ChargeControlWrapper',
            suites = [],
        ),
        test_common.define_test(
            'power/CheckAC',
            suites = [],
        ),
        test_common.define_test(
            'power/Consumption',
            suites = [],
        ),
        test_common.define_test(
            'power/DeferForFlashrom',
            suites = ['power_build'],
        ),
        test_common.define_test(
            'power/Display',
            suites = ['power_daily', 'power_monitoring', 'power_sanity'],
        ),
        test_common.define_test(
            'power/Draw',
            suites = [],
        ),
        test_common.define_test(
            'power/Dummy',
            suites = [],
        ),
        test_common.define_test(
            'power/HotCPUSuspend',
            suites = ['kernel_daily_regression'],
        ),
        test_common.define_test(
            'power/Idle',
            suites = ['bvt-perbuild', 'power_idle', 'power_monitoring', 'power_sanity'],
        ),
        test_common.define_test(
            'power/IdleServer',
            suites = [],
        ),
        test_common.define_test(
            'power/IdleSuspend',
            suites = ['kernel_daily_regression'],
        ),
        test_common.define_test(
            'power/KernelSuspend',
            suites = ['jailed_build'],
        ),
        test_common.define_test(
            'power/LoadTest',
            suites = ['power_loadtest'],
        ),
        test_common.define_test(
            'power/LowMemorySuspend',
            suites = ['crosbolt_perf_weekly'],
        ),
        test_common.define_test(
            'power/MemorySuspend',
            suites = ['jailed_build'],
        ),
        test_common.define_test(
            'power/Monitoring',
            suites = [],
        ),
        test_common.define_test(
            'power/NoConsoleSuspend',
            suites = ['kernel_daily_regression'],
        ),
        test_common.define_test(
            'power/PowerlogWrapper',
            suites = [],
        ),
        test_common.define_test(
            'power/ProbeDriver.probe_ac',
            suites = ['power_build'],
        ),
        test_common.define_test(
            'power/RPMTest',
            suites = [],
        ),
        test_common.define_test(
            'power/Resume',
            suites = ['crosbolt_perf_perbuild'],
        ),
        test_common.define_test(
            'power/ServodWrapper',
            suites = [],
        ),
        test_common.define_test(
            'power/Speedometer2',
            suites = ['power_daily'],
        ),
        test_common.define_test(
            'power/Standby',
            suites = [],
        ),
        test_common.define_test(
            'power/StatsCPUFreq',
            suites = ['power_build'],
        ),
        test_common.define_test(
            'power/StatsUSB',
            suites = ['power_build'],
        ),
        test_common.define_test(
            'power/SuspendToIdle',
            suites = ['power_daily'],
        ),
        test_common.define_test(
            'power/Thermal',
            suites = [],
        ),
        test_common.define_test(
            'power/ThermalLoad',
            suites = [],
        ),
        test_common.define_test(
            'power/USBHotplugInSuspend',
            suites = [],
        ),
        test_common.define_test(
            'power/UiResume',
            suites = ['crosbolt_perf_perbuild'],
        ),
        test_common.define_test(
            'power/VideoCall',
            suites = [],
        ),
        test_common.define_test(
            'power/VideoDRMPlayback',
            suites = [],
        ),
        test_common.define_test(
            'power/VideoDetector',
            suites = ['kernel_daily_regression'],
        ),
        test_common.define_test(
            'power/VideoEncode',
            suites = [],
        ),
        test_common.define_test(
            'power/VideoPlayback',
            suites = ['power_daily', 'power_monitoring', 'power_sanity'],
        ),
        test_common.define_test(
            'power/VideoSuspend',
            suites = ['kernel_daily_regression', 'video'],
        ),
        test_common.define_test(
            'power/WaitForCoolDown',
            suites = [],
        ),
        test_common.define_test(
            'power/WakeSources',
            suites = ['power_build'],
        ),
        test_common.define_test(
            'power/WakeupRTC',
            suites = ['kernel_per-build_regression'],
        ),
        test_common.define_test(
            'power/WebGL',
            suites = ['power_daily', 'power_monitoring', 'power_sanity'],
        ),
        test_common.define_test(
            'power/WifiIdle',
            suites = ['power_daily'],
        )
    ]
