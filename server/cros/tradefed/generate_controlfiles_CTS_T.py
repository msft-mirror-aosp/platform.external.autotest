#!/usr/bin/env python3
# Lint as: python2, python3
# Copyright 2022 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import os

CONFIG = {}

CONFIG['TEST_NAME'] = 'cheets_CTS_T'
CONFIG['BUNDLE_CONFIG_PATH'] = os.path.abspath(os.path.join(os.path.dirname(__file__),
        '..', '..', 'site_tests', CONFIG['TEST_NAME'], 'bundle_url_config.json'))
CONFIG['DOC_TITLE'] = 'Android Compatibility Test Suite (CTS)'
CONFIG['MOBLAB_SUITE_NAME'] = 'suite:cts'
CONFIG['MOBLAB_HARDWARE_SUITE_NAME'] = 'suite:cts-hardware'
CONFIG['COPYRIGHT_YEAR'] = 2022
CONFIG['AUTHKEY'] = ''

# Both arm, x86 tests results normally is below 200MB.
# 1000MB should be sufficient for CTS tests and dump logs for android-cts.
CONFIG['LARGE_MAX_RESULT_SIZE'] = 1000 * 1024

# Individual module normal produces less results than all modules, which is
# ranging from 4MB to 50MB. 500MB should be sufficient to handle all the cases.
CONFIG['NORMAL_MAX_RESULT_SIZE'] = 500 * 1024

CONFIG['TRADEFED_CTS_COMMAND'] = 'cts'
CONFIG['TRADEFED_RETRY_COMMAND'] = 'retry'
CONFIG['TRADEFED_DISABLE_REBOOT'] = False
CONFIG['TRADEFED_DISABLE_REBOOT_ON_COLLECTION'] = True
CONFIG['TRADEFED_MAY_SKIP_DEVICE_INFO'] = False
CONFIG['TRADEFED_EXECUTABLE_PATH'] = 'android-cts/tools/cts-tradefed'
CONFIG['JAVA_EXECUTABLE_PATH'] = 'android-cts/jdk/bin/java'
CONFIG['TRADEFED_IGNORE_BUSINESS_LOGIC_FAILURE'] = False

# On moblab everything runs in the same suite.
CONFIG['INTERNAL_SUITE_NAMES'] = ['suite:arc-cts']
CONFIG['QUAL_SUITE_NAMES'] = ['suite:arc-cts-qual']
CONFIG['HARDWARE_SUITE_NAME'] = 'suite:arc-cts-hardware'
CONFIG['VM_SUITE_NAME'] = 'suite:arc-cts-vm'
CONFIG['STABLE_VM_SUITE_NAME'] = 'suite:arc-cts-vm-stable'

CONFIG['CONTROLFILE_TEST_FUNCTION_NAME'] = 'run_TS'
CONFIG['CONTROLFILE_WRITE_SIMPLE_QUAL_AND_REGRESS'] = False
CONFIG['CONTROLFILE_WRITE_CAMERA'] = True
CONFIG['CONTROLFILE_WRITE_EXTRA'] = True

# The dashboard suppresses upload to APFE for GS directories (based on autotest
# tag) that contain 'tradefed-run-collect-tests'. b/119640440
# Do not change the name/tag without adjusting the dashboard.
_COLLECT = 'tradefed-run-collect-tests-only-internal'
_PUBLIC_COLLECT = 'tradefed-run-collect-tests-only'

CONFIG['LAB_DEPENDENCY'] = {'x86': ['cts_abi_x86']}

CONFIG['CTS_JOB_RETRIES_IN_PUBLIC'] = 1
CONFIG['CTS_QUAL_RETRIES'] = 9
CONFIG['CTS_MAX_RETRIES'] = {
}

# Timeout in hours.
CONFIG['CTS_TIMEOUT_DEFAULT'] = 1.0
CONFIG['CTS_TIMEOUT'] = {
        'CtsAppSecurityHostTestCases': 2.0,
        'CtsAutoFillServiceTestCases': 2.5,  # TODO(b/134662826)
        'CtsCameraTestCases': 1.5,
        'CtsDeqpTestCases': 30.0,
        'CtsDeqpTestCases.dEQP-EGL': 2.0,
        'CtsDeqpTestCases.dEQP-GLES2': 2.0,
        'CtsDeqpTestCases.dEQP-GLES3': 6.0,
        'CtsDeqpTestCases.dEQP-GLES31': 6.0,
        'CtsDeqpTestCases.dEQP-VK': 15.0,
        'CtsFileSystemTestCases': 3.0,
        'CtsHardwareTestCases': 2.0,
        'CtsIcuTestCases': 2.0,
        'CtsKeystoreTestCases': 2.0,
        'CtsLibcoreOjTestCases': 2.0,
        'CtsMediaStressTestCases': 5.0,
        'CtsMediaPlayerTestCases': 2.0,
        'CtsMediaDecoderTestCases': 2.0,
        'CtsNNAPIBenchmarkTestCases': 2.0,
        'CtsPrintTestCases': 1.5,
        'CtsSecurityTestCases': 20.0,
        'CtsSecurityTestCases[instant]': 20.0,
        'CtsSensorTestCases': 2.0,
        'CtsStatsdHostTestCases': 2.0,
        'CtsVideoTestCases': 1.5,
        'CtsViewTestCases': 2.5,
        'CtsWidgetTestCases': 2.0,
        _COLLECT: 2.5,
        _PUBLIC_COLLECT: 2.5,
}

# Any test that runs as part as blocking BVT needs to be stable and fast. For
# this reason we enforce a tight timeout on these modules/jobs.
# Timeout in hours. (0.1h = 6 minutes)
CONFIG['BVT_TIMEOUT'] = 0.1
# We allow a very long runtime for qualification (2 days).
CONFIG['QUAL_TIMEOUT'] = 48

CONFIG['QUAL_BOOKMARKS'] = sorted([
        'A',  # A bookend to simplify partition algorithm.
        'CtsAccessibilityServiceTestCases',  # TODO(ihf) remove when b/121291711 fixed. This module causes problems. Put it into its own control file.
        'CtsAccessibilityServiceTestCasesz',
        'CtsCameraTestCases',  # Flaky
        'CtsCameraTestCasesz',
        'CtsDeqpTestCases',
        'CtsDeqpTestCasesz',  # Put Deqp in one control file. Long enough, fairly stable.
        'CtsFileSystemTestCases',  # Runs long enough. (3h)
        'CtsFileSystemTestCasesz',
        'CtsMediaStressTestCases',  # Put heavy  Media module in its own control file. Long enough.
        'CtsMediaTestCases',
        'CtsMediaTestCasesz',
        'CtsJvmti',
        'CtsProvider',  # TODO(b/184680306): Remove once the USB stick issue is resolved.
        'CtsSecurityHostTestCases',  # TODO(ihf): remove when passing cleanly.
        'CtsSecurityHostTestCasesz',
        'CtsSensorTestCases',  # TODO(ihf): Remove when not needing 30 retries.
        'CtsSensorTestCasesz',
        'CtsSystem',  # TODO(b/183170604): Remove when flakiness is fixed.
        'CtsViewTestCases',  # TODO(b/126741318): Fix performance regression and remove this.
        'CtsViewTestCasesz',
        'zzzzz'  # A bookend to simplify algorithm.
])

CONFIG['BVT_PERBUILD'] = [
        'CtsAccelerationTestCases',
        'CtsMidiTestCases',
]

CONFIG['NEEDS_POWER_CYCLE'] = [
        'CtsAppTestCases',
        'CtsSensorTestCases',
]

# Modules that are known to download and/or push media file assets.
CONFIG['MEDIA_MODULES'] = [
        'CtsMediaStressTestCases',
        'CtsMediaBitstreamsTestCases',
]

CONFIG['NEEDS_PUSH_MEDIA'] = CONFIG['MEDIA_MODULES'] + [
        'CtsMediaStressTestCases.camera',
]

CONFIG['NEEDS_CTS_HELPERS'] = [
        'CtsPrintTestCases',
]

CONFIG['SPLIT_BY_BITS_MODULES'] = [
        'CtsDeqpTestCases',
        'CtsDeqpTestCases.dEQP-VK',
]

# Specifies if the VM suite should include only a single ABI. If unspecified,
# the suite includes both arm/x86 modules.
CONFIG['VM_RUN_SINGLE_ABI'] = 'x86'

# Syntax:
# - First character is either '+' (include) or '-' (exclude).
# - Remaining is a regex that matches the CTS module name.
# Rules are evaluated in list order, and the first match is returned.
CONFIG['VM_MODULES_RULES'] = [
        # Exception to CtsUi.* below.
        '+CtsUidIsolation.*',

        # HW-dependent tests to exclude.
        '-CtsBluetooth.*',
        '-CtsCamera.*',
        '-CtsDeqp.*',
        '-CtsFileSystem.*',
        '-CtsGpu.*',
        '-CtsGraphics.*',
        '-CtsHardware.*',
        '-CtsMedia.*',
        '-CtsNNAPI.*',
        '-CtsNative.*',
        '-CtsOpenG.*',
        '-CtsSample.*',
        '-CtsSecurity.*',
        '-CtsSensor.*',
        '-CtsSimpleCpu.*',
        '-CtsSkQP.*',
        '-CtsUi.*',
        '-CtsVideo.*',
        '-CtsView.*',
        '-CtsWifi.*',

        # Add everything else.
        '+.*',
]

# Same Syntax as VM_MODULES_RULES.
# These VM testing are unstable, and will also run at regular frequency on
# hardware.
CONFIG['VM_UNSTABLE_MODULES_RULES'] = [
        # Uncomment the line below to add all tests back to hardware.
        # TODO(fqj): comment out once arc-cts-vm is running.
        "+.*",

        # These tests failed more than once between Oct/13 and Nov/09 2022 on R.
        "+CtsApp.*",
        "+CtsBionic.*",
        "+CtsCamera.*",
        "+CtsJobScheduler.*",
        "+CtsNet.*",
        "+CtsOs.*",
        "+CtsProvider.*",
        "+CtsSimpleperfTestCases",
        "+CtsStatsdHost.*",

        # These tests has suspicious bug reports on R.
        '+CtsAccessibility.*',  # b/192310577, b/196934844
        '+CtsApp.*',  # b/216741475
        '+CtsAssist.*',  # b/160541876
        '+CtsAutoFillService.*',  # b/216897339
        '+CtsBionic.*',  # b/160851611
        '+CtsBlobStore.*',  # b/180681350
        '+CtsBootStats.*',  # b/174224484
        '+CtsDownloadManager.*',  # b/163729385
        '+CtsDropBoxManagerTestCases.*',  # b/177029550
        '+CtsDynamic.*',  # b/163121640
        '+CtsFragment.*',  # b/251276296
        '+CtsIke.*',  # b/160541882
        '+CtsInputMethod.*',  # b/253540001, b/191413875
        '+CtsJni.*',  # b/160867403
        '+CtsJobScheduler.*',  # b/226422237
        '+CtsMidiTestCases.*',  # b/222242213
        '+CtsNdkBinder.*',  # b/163123128
        '+CtsNet.*',  # b/258074918
        '+CtsOs.*',  # b/b/187745471
        '+CtsPerfetto.*',  # b/203614416
        '+CtsProvider.*',  # b/212194116
        '+CtsRs.*',  # b/166168119
        '+CtsScopedStorageHostTest.*',  # b/232055847
        '+CtsSimpleperfTestCases.*',  # b/247434877
        '+CtsTransition.*',  # b/160544400
        '+CtsWidget.*',  # b/214332007
        '+LegacyStorageTest.*',  # b/190457907
        '+ScopedStorageTest.*',  # b/190457907
        '+vm-tests-tf.*',  # b/158533921

        # May depend on HW ?
        '+CtsDisplay.*',
        '+CtsDpi.*',
        # This suite include tests sensitive to graphics performance
        # (GraphicsStatsValidationTest) so we probably need HW coverage.
        '+CtsIncidentHost.*',
        # We do see device-specfic failure from CtsWM (e.g., b/264339925) and
        # formfactor dependence (5 or 6 kukui/nocturne-only failures must have
        # been addressed before they become launch ready.) It is safer to leave
        # this to the hw-dependence family at least until we have tablet/laptop
        # coverage by Betty
        '+CtsWindowManager.*',
        '+signed-Cts.*',

        # All others tests are stable on VM.
        '-.*',
]

# Modules that are known to need the default apps of Chrome (eg. Files.app).
CONFIG['ENABLE_DEFAULT_APPS'] = [
        'CtsAppSecurityHostTestCases',
        'CtsContentTestCases',
]

_WIFI_CONNECT_COMMANDS = [
        # These needs to be in order.
        "'/usr/local/autotest/cros/scripts/wifi connect %s %s\' % (ssid, wifipass)",
        "'android-sh -c \\'dumpsys wifi transports -eth\\''"
]

_WIFI_CONNECT_COMMANDS_V2 = [
        # These needs to be in order.
        "'adb shell cmd wifi add-network %s %s %s' % (pipes.quote(ssid), 'open' if wifipass == '' else 'wpa', pipes.quote(wifipass))",
        "'adb shell cmd wifi connect-network %s' % pipes.quote(ssid)",
        "'adb shell dumpsys wifi transports -eth'",
]

IPV6_MODULES = [
        'CtsLibcoreTestCases',
]

CONFIG['WIFI_MODULES'] = [
        'CtsNetApi23TestCases',
        'CtsNetTestCases',
        'CtsJobSchedulerTestCases',
        'CtsStatsdHostTestCases',
        'CtsWifiTestCases',
]

# Preconditions applicable to public and internal tests.
CONFIG['PRECONDITION'] = {
}

CONFIG['LOGIN_PRECONDITION'] = {
}

# Preconditions applicable to public tests.
CONFIG['PUBLIC_PRECONDITION'] = {
}

for m in IPV6_MODULES:
    CONFIG['PUBLIC_PRECONDITION'][m] = _WIFI_CONNECT_COMMANDS_V2

for m in CONFIG['WIFI_MODULES']:
    CONFIG['PUBLIC_PRECONDITION'][m] = _WIFI_CONNECT_COMMANDS_V2
    CONFIG['PRECONDITION'][m] = _WIFI_CONNECT_COMMANDS_V2

CONFIG['PUBLIC_DEPENDENCIES'] = {
        'CtsCameraTestCases': ['lighting'],
        'CtsMediaTestCases': ['noloopback'],
}

CONFIG['PUBLIC_OVERRIDE_TEST_PRIORITY'] = {
        _PUBLIC_COLLECT: 70,
        'CtsDeqpTestCases': 70,
        'CtsDeqpTestCases': 70,
        'CtsMediaTestCases': 70,
        'CtsMediaStressTestCases': 70,
        'CtsSecurityTestCases': 70,
        'CtsCameraTestCases': 70
}

# This information is changed based on regular analysis of the failure rate on
# partner moblabs.
CONFIG['PUBLIC_MODULE_RETRY_COUNT'] = {
}

# This information is changed based on regular analysis of the job run time on
# partner moblabs.

CONFIG['OVERRIDE_TEST_LENGTH'] = {
        'CtsDeqpTestCases': 4,  # LONG
        'CtsMediaTestCases': 4,
        'CtsMediaStressTestCases': 4,
        'CtsSecurityTestCases': 4,
        'CtsCameraTestCases': 4,
        # Even though collect tests doesn't run very long, it must be the very first
        # job executed inside of the suite. Hence it is the only 'LENGTHY' test.
        _COLLECT: 5,  # LENGTHY
        _PUBLIC_COLLECT: 5,  # LENGTHY
}

# Enabling --logcat-on-failure can extend total run time significantly if
# individual tests finish in the order of 10ms or less (b/118836700). Specify
# modules here to not enable the flag.
CONFIG['DISABLE_LOGCAT_ON_FAILURE'] = set([
        'all',
        'CtsDeqpTestCases',
        'CtsDeqpTestCases.dEQP-EGL',
        'CtsDeqpTestCases.dEQP-GLES2',
        'CtsDeqpTestCases.dEQP-GLES3',
        'CtsDeqpTestCases.dEQP-GLES31',
        'CtsDeqpTestCases.dEQP-VK',
        'CtsLibcoreTestCases',
])

# This list of modules will be used for reduced set of testing for build
# variant process. Suites: cts_hardware & arc-cts-hardware.
CONFIG['HARDWARE_MODULES'] = [
        'CtsPerfettoTestCases',
        'CtsSustainedPerformanceHostTestCases',
        'CtsCameraTestCases',
        'CtsViewTestCases',
        'CtsMediaAudioTestCases',
        'CtsMediaCodecTestCases',
        'CtsMediaDecoderTestCases',
        'CtsMediaEncoderTestCases',
        'CtsMediaDrmFrameworkTestCases',
        'CtsMediaExtractorTestCases',
        'CtsMediaMuxerTestCases',
        'CtsMediaPlayerTestCases',
        'CtsMediaRecorderTestCases',
        'CtsMediaMiscTestCases',
        'CtsNativeMediaAAudioTestCases',
        'CtsNetTestCases',
        'CtsWifiTestCases',
        'CtsUsageStatsTestCases',
        'CtsSensorTestCases',
]


R_REGRESSION_SUITES = ['suite:arc-cts']
R_REGRESSION_AND_QUAL_SUITES = CONFIG['QUAL_SUITE_NAMES'] + R_REGRESSION_SUITES

CONFIG['EXTRA_MODULES'] = { }

# In addition to EXTRA_MODULES, these modules do require separate control files
# for internal and moblab.
CONFIG['HARDWAREONLY_EXTRA_MODULES'] = {
        'CtsAppTestCases': {
                'CtsAppTestCases.feature': [],
        },
        'CtsDeqpTestCases': {
                'CtsDeqpTestCases.dEQP-GLES3.functional.prerequisite': [],
        },
        'CtsMediaStressTestCases': {
                'CtsMediaStressTestCases.camera': [],
        },
        'CtsPermissionTestCases': {
                'CtsPermissionTestCases.camera': [],
        },
}

_firmware_sensor_tests = {
        'CtsSensorTestCases.faft': ['suite:faft_experimental']
}

CONFIG['PUBLIC_EXTRA_MODULES'] = {
        'arm': {
                'CtsSensorTestCases': _firmware_sensor_tests,
        },
}

CONFIG['EXTRA_SUBMODULE_OVERRIDE'] = {
}

CONFIG['EXTRA_COMMANDLINE'] = {
        'CtsAppTestCases.feature': [
                '--module', 'CtsAppTestCases', '--test',
                'android.app.cts.SystemFeaturesTest'
        ],
        'CtsDeqpTestCases.dEQP-GLES3.functional.prerequisite': [
                '--module', 'CtsDeqpTestCases', '--test',
                'dEQP-GLES3.functional.prerequisite#*'
        ],
        'CtsMediaStressTestCases.camera': [
                '--module',
                'CtsMediaStressTestCases',
                '--test',
                'android.mediastress.cts.MediaRecorderStressTest',
        ],
        'CtsPermissionTestCases.camera': [
                '--include-filter',
                'CtsPermissionTestCases android.permission.cts.CameraPermissionTest',
                '--include-filter',
                'CtsPermissionTestCases android.permission.cts.Camera2PermissionTest',
        ],
        'CtsSensorTestCases.faft': [
                '--include-filter',
                'CtsSensorTestCases',
                '--abi',
                'armeabi-v7a',
        ],
}

CONFIG['EXTRA_ATTRIBUTES'] = {}

CONFIG['EXTRA_ARTIFACTS'] = {}
CONFIG['PREREQUISITES'] = {}

from generate_controlfiles_common import main

if __name__ == '__main__':
    main(CONFIG)
