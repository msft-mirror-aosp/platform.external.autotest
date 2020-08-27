
# Copyright 2020 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# !!! GENERATED FILE. DO NOT EDIT !!!

load('//metadata/test_common.star', 'test_common')

def define_tests():
    return [
        test_common.define_test(
            'hardware/Backlight',
            suites = ['hwqual'],
        ),
        test_common.define_test(
            'hardware/Badblocks',
            suites = [],
        ),
        test_common.define_test(
            'hardware/DiskFirmwareUpgrade_Client',
            suites = [],
        ),
        test_common.define_test(
            'hardware/DiskFirmwareUpgrade_Server',
            suites = ['experimental'],
        ),
        test_common.define_test(
            'hardware/DiskSize',
            suites = [],
        ),
        test_common.define_test(
            'hardware/EC',
            suites = ['bvt-perbuild'],
        ),
        test_common.define_test(
            'hardware/GPIOSwitches',
            suites = [],
        ),
        test_common.define_test(
            'hardware/GPS',
            suites = [],
        ),
        test_common.define_test(
            'hardware/GobiGPS',
            suites = [],
        ),
        test_common.define_test(
            'hardware/Keyboard',
            suites = [],
        ),
        test_common.define_test(
            'hardware/LightSensor',
            suites = ['hwqual'],
        ),
        test_common.define_test(
            'hardware/MemoryLatency',
            suites = ['hwqual', 'kernel_daily_benchmarks'],
        ),
        test_common.define_test(
            'hardware/MemoryThroughput',
            suites = ['hwqual', 'kernel_daily_benchmarks'],
        ),
        test_common.define_test(
            'hardware/MemoryZRAMThroughput',
            suites = ['crosbolt_perf_weekly'],
        ),
        test_common.define_test(
            'hardware/Memtester',
            suites = [],
        ),
        test_common.define_test(
            'hardware/MultiReader',
            suites = [],
        ),
        test_common.define_test(
            'hardware/MultiReaderPowerConsumption',
            suites = [],
        ),
        test_common.define_test(
            'hardware/ProbeComponents',
            suites = [],
        ),
        test_common.define_test(
            'hardware/RamFio',
            suites = ['bvt-perbuild', 'crosbolt_perf_weekly'],
        ),
        test_common.define_test(
            'hardware/RealtekCardReader',
            suites = [],
        ),
        test_common.define_test(
            'hardware/Resolution',
            suites = ['hwqual'],
        ),
        test_common.define_test(
            'hardware/SAT',
            suites = ['kernel_per-build_regression'],
        ),
        test_common.define_test(
            'hardware/Smartctl',
            suites = [],
        ),
        test_common.define_test(
            'hardware/SsdDetection',
            suites = ['hwqual'],
        ),
        test_common.define_test(
            'hardware/StorageFio',
            suites = ['crosbolt_perf_weekly', 'kernel_daily_benchmarks'],
        ),
        test_common.define_test(
            'hardware/StorageFioOther.test',
            suites = [],
        ),
        test_common.define_test(
            'hardware/StorageQualCheckSetup',
            suites = ['check_setup_storage_qual'],
        ),
        test_common.define_test(
            'hardware/StorageStress',
            suites = [],
        ),
        test_common.define_test(
            'hardware/StorageTrim',
            suites = [],
        ),
        test_common.define_test(
            'hardware/StorageWearoutDetect',
            suites = ['bvt-perbuild'],
        ),
        test_common.define_test(
            'hardware/TPMCheck',
            suites = ['kernel_per-build_regression'],
        ),
        test_common.define_test(
            'hardware/TPMLoadKey',
            suites = [],
        ),
        test_common.define_test(
            'hardware/TPMTakeOwnership',
            suites = [],
        ),
        test_common.define_test(
            'hardware/TPMtspi',
            suites = [],
        ),
        test_common.define_test(
            'hardware/TPMttci',
            suites = [],
        ),
        test_common.define_test(
            'hardware/Thermal',
            suites = [],
        ),
        test_common.define_test(
            'hardware/TouchScreenPowerCycles',
            suites = [],
        ),
        test_common.define_test(
            'hardware/TrimIntegrity',
            suites = [],
        ),
        test_common.define_test(
            'hardware/UnsafeMemory',
            suites = [],
        ),
        test_common.define_test(
            'hardware/Usb30Throughput',
            suites = [],
        ),
        test_common.define_test(
            'hardware/UsbBasicFileOperations',
            suites = [],
        ),
        test_common.define_test(
            'hardware/UsbMount',
            suites = [],
        )
    ]
