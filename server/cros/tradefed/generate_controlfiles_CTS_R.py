#!/usr/bin/env python3
# Lint as: python2, python3
# Copyright 2020 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import os

CONFIG = {}

CONFIG['TEST_NAME'] = 'cheets_CTS_R'
CONFIG['BUNDLE_CONFIG_PATH'] = os.path.abspath(os.path.join(os.path.dirname(__file__),
        '..', '..', 'site_tests', CONFIG['TEST_NAME'], 'bundle_url_config.json'))
CONFIG['DOC_TITLE'] = 'Android Compatibility Test Suite (CTS)'
CONFIG['MOBLAB_SUITE_NAME'] = 'suite:cts'
CONFIG['COPYRIGHT_YEAR'] = 2020
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
CONFIG['TRADEFED_IGNORE_BUSINESS_LOGIC_FAILURE'] = False

# On moblab everything runs in the same suite.
CONFIG['INTERNAL_SUITE_NAMES'] = ['suite:arc-cts']
CONFIG['QUAL_SUITE_NAMES'] = ['suite:arc-cts-qual']
CONFIG['HARDWARE_SUITE_NAME'] = 'suite:arc-cts-hardware'
CONFIG['VM_SUITE_NAME'] = 'suite:arc-cts-vm'
CONFIG['STABLE_VM_SUITE_NAME'] = 'suite:arc-cts-vm-stable'

# Suite for rerunning failing camera test during qual
CONFIG['CAMERA_DUT_SUITE_NAME'] = 'suite:arc-cts-camera-opendut'

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
CONFIG['CTS_MAX_RETRIES'] = {}

CONFIG['SPLIT_SUITES'] = {
        'DEV_SUITE_FORMAT': 'suite:arc-cts-{abi}-{shard}',
        'DEV_SUITE_LONG': 'suite:arc-cts-long',
        'DEV_VM_STABLE_SUITE_FORMAT': 'suite:arc-cts-vm-stable-{abi}-{shard}',
        'DEV_VM_STABLE_SUITE_LONG': 'suite:arc-cts-vm-stable-long',
        'QUAL_SUITE_FORMAT': 'suite:arc-cts-qual-{abi}-{shard}',
        'QUAL_SUITE_LONG': 'suite:arc-cts-qual-long',
        'MAX_RUNTIME_SECS': 9000,  # 2.5hr; hard limit is 3hr
        'PER_TEST_OVERHEAD_SECS': 600,  # 10min for DUT provisioning etc.
        # P95 runtime from PASS/WARN runs between 20230515-20230615.
        'RUNTIME_HINT_SECS': {
                'CtsAbiOverrideHost': 398,
                'CtsAcceleration': 355,
                'CtsAccessibility': 1614,
                'CtsAccountManager': 614,
                'CtsAccountsHost': 333,
                'CtsActivityManagerBackgroundActivity': 693,
                'CtsAdb': 332,
                'CtsAdmin': 385,
                'CtsAlarmManager': 637,
                'CtsAndroid': 595,
                'CtsAngleIntegrationHost': 534,
                'CtsAnimation': 741,
                'CtsApacheHttpLegacy': 505,
                'CtsApex': 321,
                'CtsApp': 16033,
                'CtsAslrMalloc': 800,
                'CtsAssist': 724,
                'CtsAtomicInstall': 362,
                'CtsAtraceHost': 454,
                'CtsAttentionServiceDevice': 302,
                'CtsAutoFillService': 8904,
                'CtsBackgroundRestrictions': 368,
                'CtsBackup': 1069,
                'CtsBatterySaving': 656,
                'CtsBionic': 1251,
                'CtsBlobStore': 2599,
                'CtsBluetooth': 997,
                'CtsBootStats': 567,
                'CtsCalendarProvider': 351,
                'CtsCalendarcommon2': 298,
                'CtsCameraApi25TestCases': 523,
                'CtsCar': 345,
                'CtsCarrierApiTestCases': 328,
                'CtsClassLoaderFactory': 391,
                'CtsClassloaderSplitsHost': 448,
                'CtsCodePathHost': 419,
                'CtsColorMode': 377,
                'CtsCompilation': 384,
                'CtsContactsProvider': 854,
                'CtsContent': 2918,
                'CtsControlsDevice': 324,
                'CtsCppTools': 367,
                'CtsCurrentApiSignature': 326,
                'CtsDatabase': 601,
                'CtsDeqp.32': 50678,
                'CtsDeqp.64': 48260,
                'CtsDevice': 4457,
                'CtsDexMetadataHost': 352,
                'CtsDisplay': 616,
                'CtsDownloadManager': 505,
                'CtsDpi': 475,
                'CtsDreams': 348,
                'CtsDrm': 414,
                'CtsDropBoxManagerTestCases': 517,
                'CtsDumpsysHost': 337,
                'CtsDynamic': 4719,
                'CtsEdiHost': 419,
                'CtsEffect': 390,
                'CtsExtendedMocking': 740,
                'CtsExternalService': 330,
                'CtsExtractNativeLibsHost': 358,
                'CtsFileSystem': 11481,
                'CtsFragment': 968,
                'CtsFsMgr': 350,
                'CtsGesture': 366,
                'CtsGpu': 1890,
                'CtsGraphics': 2641,
                'CtsGwpAsan': 382,
                'CtsHardware': 694,
                'CtsHarmfulAppWarningHost': 315,
                'CtsHdmiCecHost': 334,
                'CtsHiddenApi': 2359,
                'CtsHostTzData': 369,
                'CtsHostside': 2792,
                'CtsIcu': 4580,
                'CtsIdentity': 394,
                'CtsIke': 479,
                'CtsIncidentHost': 2141,
                'CtsIncrementalInstallHost': 591,
                'CtsInit': 309,
                'CtsInlineMocking': 665,
                'CtsInputMethod': 2412,
                'CtsInstantApp': 320,
                'CtsIntentSignature': 340,
                'CtsJdwp': 2084,
                'CtsJni': 522,
                'CtsJobScheduler': 1524,
                'CtsJvmti': 4974,
                'CtsKernelConfigTestCases': 406,
                'CtsKeystore': 9424,
                'CtsLeanbackJank': 326,
                'CtsLegacyNotification2': 559,
                'CtsLibcore': 14210,
                'CtsLiblog': 349,
                'CtsLocation': 907,
                'CtsLogd': 652,
                'CtsMatchFlag': 326,
                'CtsMediaBitstreamsTestCases': 813,
                'CtsMediaHostTestCases': 566,
                'CtsMediaParserTestCases': 511,
                'CtsMediaPerformanceClassTestCases': 601,
                'CtsMediaStressTestCases': 20951,
                'CtsMediaTestCases.32': 30846,
                'CtsMediaTestCases.64': 33006,
                'CtsMediaV2TestCases': 3449,
                'CtsMidiTestCases': 568,
                'CtsMimeMap': 335,
                'CtsMocking': 613,
                'CtsMonkey': 494,
                'CtsMultiUser': 435,
                'CtsNNAPI': 2510,
                'CtsNNAPIBenchmark': 595,
                'CtsNative': 1663,
                'CtsNdef': 301,
                'CtsNdkBinder': 528,
                'CtsNet': 2291,
                'CtsNfc': 322,
                'CtsNoPermission': 377,
                'CtsOmapi': 305,
                'CtsOpenG': 2258,
                'CtsOs': 3316,
                'CtsPackage': 965,
                'CtsPdf': 2268,
                'CtsPerfetto': 682,
                'CtsPermission': 2271,
                'CtsPreference': 1031,
                'CtsPrint': 278,
                'CtsProto': 366,
                'CtsProvider': 1987,
                'CtsQuickAccessWallet': 399,
                'CtsRenderscript': 1200,
                'CtsResolverService': 328,
                'CtsResourcesLoader': 526,
                'CtsRole': 844,
                'CtsRollbackManagerHostTestCases': 450,
                'CtsRs': 1139,
                'CtsSample': 504,
                'CtsSax': 332,
                'CtsScopedStorageHostTest': 2595,
                'CtsSdkExtensions': 428,
                'CtsSeccompHost': 503,
                'CtsSecure': 456,
                'CtsSecurity': 2275,
                'CtsSelinux': 510,
                'CtsSensor': 6146,
                'CtsSettings': 332,
                'CtsSharedLibsApiSignature': 355,
                'CtsSharesheet': 560,
                'CtsShortcut': 2430,
                'CtsSignedConfigHost': 414,
                'CtsSimRestrictedApis': 312,
                'CtsSimpleCpu': 770,
                'CtsSimpleperfTestCases': 1340,
                'CtsSkQP': 2549,
                'CtsSlice': 327,
                'CtsSoundTrigger': 338,
                'CtsSpeech': 364,
                'CtsStagedInstallHostTestCases': 872,
                'CtsStatsdHost': 14732,
                'CtsStrictJavaPackages': 351,
                'CtsSuspendApps': 390,
                'CtsSustainedPerformanceHost': 354,
                'CtsSync': 517,
                'CtsSystem': 1028,
                'CtsTaggingHost': 527,
                'CtsTelecom': 435,
                'CtsTelephony': 679,
                'CtsTestHarnessMode': 287,
                'CtsTetheringTest': 317,
                'CtsText': 1614,
                'CtsTfliteNnapiDelegate': 344,
                'CtsTheme': 500,
                'CtsThermal': 1575,
                'CtsToast': 513,
                'CtsTransition': 670,
                'CtsTrustedVoiceHost': 331,
                'CtsTv': 380,
                'CtsUi': 1223,
                'CtsUidIsolation': 363,
                'CtsUsageStats': 1375,
                'CtsUsb': 443,
                'CtsUsesLibraryHost': 355,
                'CtsUtil': 440,
                'CtsVideo': 7244,
                'CtsView': 12737,
                'CtsVoice': 632,
                'CtsVr': 395,
                'CtsWebkit': 1341,
                'CtsWidget': 6112,
                'CtsWifi': 1567,
                'CtsWindowManager': 7170,
                'CtsWrap': 554,
                'LegacyStorageTest': 2377,
                'ScopedStorageTest': 2350,
                'signed-Cts': 545,
                'vm-tests-tf': 5528,
        },
}

# Timeout in hours.
CONFIG['CTS_TIMEOUT_DEFAULT'] = 1.0
CONFIG['CTS_TIMEOUT'] = {
        'CtsAppSecurityHostTestCases': 2.0,
        'CtsAutoFillServiceTestCases': 2.5,  # TODO(b/134662826)
        'CtsCameraTestCases': 2.5,
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
        'CtsMediaTestCases': 10.0,
        'CtsMediaTestCases.video': 10.0,
        'CtsNNAPIBenchmarkTestCases': 2.0,
        'CtsPrintTestCases': 1.5,
        'CtsSecurityTestCases': 20.0,
        'CtsSecurityTestCases[instant]': 20.0,
        'CtsSensorTestCases': 2.0,
        'CtsStatsdHostTestCases': 2.0,
        'CtsVideoTestCases': 1.5,
        'CtsViewTestCases': 2.5,
        'CtsWidgetTestCases': 2.0,
        'CtsMediaTestCases.arc_perf': 1.5,
        'CtsVideoTestCases.arc_perf': 2.0,
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

# Tests to run against each release build via suite:arc-cts-perbuild.
# This coverage is required for pre-unibuild "follower" boards; see b/303561124
# for context.
CONFIG['PERBUILD_TESTS'] = [
        'CtsEdiHostTestCases',
        'CtsGraphicsTestCases',
]

CONFIG['NEEDS_POWER_CYCLE'] = [
        'CtsAppTestCases',
        'CtsSensorTestCases',
]

CONFIG['CAMERA_MODULES'] = [
       # CONTAINS ONLY CAMERA TESTS
       'CtsCameraTestCases',
]

# Specifies if the VM suite should include only a single ABI. If unspecified,
# the suite includes both arm/x86 modules.
CONFIG['VM_RUN_SINGLE_ABI'] = 'arm'

# Syntax:
# - First character is either '+' (include) or '-' (exclude).
# - Remaining is a regex that matches the CTS module name.
# Rules are evaluated in list order, and the first match is returned.
CONFIG['VM_MODULES_RULES'] = [
        # Intentionally add a HW test.
        # Note this generates a warning as CtsCameraApi25TestCases gets included
        # as well.
        '+CtsCameraTestCases',

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
    # "+.*",

    # These tests failed more than once between Oct/13 and Nov/09 2022.
    "+CtsApp.*",
    "+CtsBionic.*",
    "+CtsCamera.*",
    "+CtsJobScheduler.*",
    "+CtsNet.*",
    "+CtsOs.*",
    "+CtsProvider.*",
    "+CtsSimpleperfTestCases",
    "+CtsStatsdHost.*",

    # These tests has suspicious bug reports.
    '+CtsAccessibility.*', # b/192310577, b/196934844
    '+CtsApp.*', # b/216741475
    '+CtsAssist.*', # b/160541876
    '+CtsAutoFillService.*', # b/216897339
    '+CtsBionic.*', # b/160851611
    '+CtsBlobStore.*', # b/180681350
    '+CtsBootStats.*', # b/174224484
    '+CtsDownloadManager.*', # b/163729385
    '+CtsDropBoxManagerTestCases.*', # b/177029550
    '+CtsDynamic.*', # b/163121640
    '+CtsFragment.*', # b/251276296
    '+CtsIke.*', # b/160541882
    '+CtsInputMethod.*', # b/253540001, b/191413875
    '+CtsJni.*', # b/160867403
    '+CtsJobScheduler.*', # b/226422237
    '+CtsMidiTestCases.*', # b/222242213
    '+CtsNdkBinder.*', # b/163123128
    '+CtsNet.*', # b/258074918
    '+CtsOs.*', # b/b/187745471
    '+CtsPerfetto.*', # b/203614416
    '+CtsProvider.*', # b/212194116
    '+CtsRs.*', # b/166168119
    '+CtsScopedStorageHostTest.*', # b/232055847
    '+CtsSimpleperfTestCases.*', # b/247434877
    '+CtsTransition.*', # b/160544400
    '+CtsWidget.*', # b/214332007
    '+LegacyStorageTest.*', # b/190457907
    '+ScopedStorageTest.*', # b/190457907
    '+vm-tests-tf.*', # b/158533921

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

# List of suite that stable VM modules will skip.
CONFIG['VM_SKIP_SUITES'] = ['suite:arc-cts']

CONFIG['VM_CONFIG'] = {
        'SUITE_NAME': CONFIG['VM_SUITE_NAME'],
        'STABLE_SUITE_NAME': CONFIG['STABLE_VM_SUITE_NAME'],
        'STABLE_SKIP_SUITES': CONFIG['VM_SKIP_SUITES'],
        'RUN_SINGLE_ABI': CONFIG['VM_RUN_SINGLE_ABI'],
        'MODULES_RULES': CONFIG['VM_MODULES_RULES'],
        'UNSTABLE_MODULES_RULES': CONFIG['VM_UNSTABLE_MODULES_RULES'],
}

# Modules that are known to download and/or push media file assets.
CONFIG['MEDIA_MODULES'] = [
        'CtsMediaTestCases',
        'CtsMediaStressTestCases',
        'CtsMediaBitstreamsTestCases',
]

CONFIG['NEEDS_PUSH_MEDIA'] = CONFIG['MEDIA_MODULES'] + [
        'CtsMediaStressTestCases.camera',
        'CtsMediaTestCases.arc_perf',
]

CONFIG['NEEDS_CTS_HELPERS'] = [
        'CtsPrintTestCases',
]

CONFIG['SPLIT_BY_BITS_MODULES'] = [
        'CtsDeqpTestCases',
        'CtsMediaTestCases',
]

CONFIG['PUBLIC_SPLIT_BY_BITS_MODULES'] = [
        'CtsDeqpTestCases',
]

CONFIG['SHARD_COUNT'] = {'CtsDeqpTestCases': 10}

# Modules that are known to need the default apps of Chrome (eg. Files.app).
CONFIG['ENABLE_DEFAULT_APPS'] = [
        'CtsAppSecurityHostTestCases',
        'CtsContentTestCases',
]

# Modules that need to be tested at higher display resolution in VM.
CONFIG['SPLIT_BY_VM_FORCE_MAX_RESOLUTION'] = [
        'CtsWindowManagerDeviceTestCases',
        'CtsAccessibilityServiceTestCases',
]

# Modules that need to be tested for tablet mode in VM.
CONFIG['SPLIT_BY_VM_TABLET_MODE'] = [
        'CtsWindowManagerDeviceTestCases',
]

# Run `eject` for (and only for) each device with RM=1 in lsblk output.
_EJECT_REMOVABLE_DISK_COMMAND = (
        "\'lsblk -do NAME,RM | sed -n s/1$//p | xargs -n1 eject\'")

_WIFI_CONNECT_COMMANDS_V2 = [
        # These needs to be in order.
        "'adb shell cmd wifi add-network %s %s %s' % (pipes.quote(ssid), 'open' if wifipass == '' else 'wpa', pipes.quote(wifipass))",
        "'adb shell cmd wifi connect-network %s' % pipes.quote(ssid)",
        "'adb shell dumpsys wifi transports -eth'",
]

# R-container: Behave more like in the verififed mode.
_SECURITY_PARANOID_COMMAND = (
    "\'echo 3 > /proc/sys/kernel/perf_event_paranoid\'")
# R-container: Expose /proc/config.gz
_CONFIG_MODULE_COMMAND = "\'modprobe configs\'"

# Preconditions applicable to public and internal tests.
CONFIG['PRECONDITION'] = {
        'CtsSecurityHostTestCases':
            [_SECURITY_PARANOID_COMMAND, _CONFIG_MODULE_COMMAND],
}

CONFIG['LOGIN_PRECONDITION'] = {
        'CtsAppSecurityHostTestCases': [_EJECT_REMOVABLE_DISK_COMMAND],
        'CtsJobSchedulerTestCases': [_EJECT_REMOVABLE_DISK_COMMAND],
        'CtsMediaTestCases': [_EJECT_REMOVABLE_DISK_COMMAND],
        'CtsOsTestCases': [_EJECT_REMOVABLE_DISK_COMMAND],
        'CtsProviderTestCases': [_EJECT_REMOVABLE_DISK_COMMAND],
}

# Preconditions applicable to public tests.
CONFIG['PUBLIC_PRECONDITION'] = {
        'CtsLibcoreTestCases': _WIFI_CONNECT_COMMANDS_V2,
        'CtsNetApi23TestCases': _WIFI_CONNECT_COMMANDS_V2,
        'CtsNetTestCases': _WIFI_CONNECT_COMMANDS_V2,
        'CtsJobSchedulerTestCases': _WIFI_CONNECT_COMMANDS_V2,
        'CtsUsageStatsTestCases': _WIFI_CONNECT_COMMANDS_V2,
        'CtsStatsdHostTestCases': _WIFI_CONNECT_COMMANDS_V2,
        'CtsWifiTestCases': _WIFI_CONNECT_COMMANDS_V2,
}

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
CONFIG['PUBLIC_MODULE_RETRY_COUNT'] = {}

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
        'CtsLibcoreTestCases',
])

# This list of modules will be used for reduced set of testing for build
# variant process. Suites: cts_hardware & arc-cts-hardware. that is run in camerabox infra
CONFIG['HARDWARE_MODULES'] = [
        'CtsPerfettoTestCases',
        'CtsSustainedPerformanceHostTestCases',
        'CtsViewTestCases',
        'CtsMediaTestCases',
        'CtsNativeMediaAAudioTestCases',
        'CtsNetTestCases',
        'CtsWifiTestCases',
        'CtsUsageStatsTestCases',
        'CtsSensorTestCases',
]

R_QUAL_SUITES = ['suite:arc-cts-qual']
R_QUAL_AND_REGRESSION_SUITES = R_QUAL_SUITES + ['suite:arc-cts']

CONFIG['EXTRA_MODULES'] = {}

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

ARC_PERF_SUITE = ['suite:arc-cts-perf']
CONFIG['PERF_MODULES'] = {
    'CtsCameraTestCases': {
        'CtsCameraTestCases.arc_perf': ARC_PERF_SUITE,
    },
    'CtsMediaTestCases': {
       'CtsMediaTestCases.arc_perf' : ARC_PERF_SUITE,
    },
    'CtsVideoTestCases': {
        'CtsVideoTestCases.arc_perf' : ARC_PERF_SUITE,
    },
    'CtsFileSystemTestCases': {
        'CtsFileSystemTestCases.arc_perf' : ARC_PERF_SUITE,
    },
    'CtsSimpleCpuTestCases': {
        'CtsSimpleCpuTestCases.arc_perf' : ARC_PERF_SUITE,
    },
}

_firmware_sensor_tests = {
        'CtsSensorTestCases.faft': ['suite:faft_experimental']
}

# TODO(b/277861132): remove once the root cause is fixed.
# This is for working around test stability when full dEQP was executed.
_public_deqp_tests = {
        'CtsDeqpTestCases.dEQP-EGL': [CONFIG['MOBLAB_SUITE_NAME']],
        'CtsDeqpTestCases.dEQP-GLES2': [CONFIG['MOBLAB_SUITE_NAME']],
        'CtsDeqpTestCases.dEQP-GLES3': [CONFIG['MOBLAB_SUITE_NAME']],
        'CtsDeqpTestCases.dEQP-GLES31': [CONFIG['MOBLAB_SUITE_NAME']],
        'CtsDeqpTestCases.dEQP-VK': [CONFIG['MOBLAB_SUITE_NAME']],
}

CONFIG['PUBLIC_EXTRA_MODULES'] = {
        'arm': {
                'CtsDeqpTestCases': _public_deqp_tests,
                'CtsSensorTestCases': _firmware_sensor_tests,
        },
        'x86': {
                'CtsDeqpTestCases': _public_deqp_tests,
        }
}

CONFIG['EXTRA_SUBMODULE_OVERRIDE'] = {
}

CONFIG['EXTRA_COMMANDLINE'] = {
        'CtsAppTestCases.feature': [
                '--module', 'CtsAppTestCases', '--test',
                'android.app.cts.SystemFeaturesTest'
        ],
        'CtsDeqpTestCases.dEQP-EGL': [
                '--include-filter', 'CtsDeqpTestCases', '--module',
                'CtsDeqpTestCases', '--test', 'dEQP-EGL.*'
        ],
        'CtsDeqpTestCases.dEQP-GLES2': [
                '--include-filter', 'CtsDeqpTestCases', '--module',
                'CtsDeqpTestCases', '--test', 'dEQP-GLES2.*'
        ],
        'CtsDeqpTestCases.dEQP-GLES3': [
                '--include-filter', 'CtsDeqpTestCases', '--module',
                'CtsDeqpTestCases', '--test', 'dEQP-GLES3.*'
        ],
        'CtsDeqpTestCases.dEQP-GLES3.functional.prerequisite': [
                '--module', 'CtsDeqpTestCases', '--test',
                'dEQP-GLES3.functional.prerequisite#*'
        ],
        'CtsDeqpTestCases.dEQP-GLES31': [
                '--include-filter', 'CtsDeqpTestCases', '--module',
                'CtsDeqpTestCases', '--test', 'dEQP-GLES31.*'
        ],
        'CtsDeqpTestCases.dEQP-VK': [
                '--include-filter', 'CtsDeqpTestCases', '--module',
                'CtsDeqpTestCases', '--test', 'dEQP-VK.*'
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
        'CtsVideoTestCases.arc_perf': [
                '--include-filter',
                'CtsVideoTestCases android.video.cts.VideoEncoderDecoderTest',
        ],
        'CtsMediaTestCases.arc_perf': [
                '--include-filter',
                'CtsMediaTestCases android.media.cts.VideoDecoderPerfTest',
                '--include-filter',
                'CtsMediaTestCases android.media.cts.AudioRecordTest',
                '--include-filter',
                'CtsMediaTestCases android.media.cts.AudioTrackTest',
                '--include-filter',
                'CtsMediaTestCases android.media.cts.AudioTrack_ListenerTest',
                '--include-filter',
                'CtsMediaTestCases android.media.cts.VideoDecoderPerfTest',
        ],
        'CtsCameraTestCases.arc_perf': [
                '--include-filter',
                'CtsCameraTestCases android.hardware.camera2.cts.PerformanceTest',
        ],
        'CtsFileSystemTestCases.arc_perf': [
                '--include-filter',
                'CtsFileSystemTestCases android.filesystem.cts.AlmostFullTest',
                '--include-filter',
                'CtsFileSystemTestCases android.filesystem.cts.RandomRWTest',
                '--include-filter',
                'CtsFileSystemTestCases android.filesystem.cts.SequentialRWTest',
        ],
        'CtsSimpleCpuTestCases.arc_perf': [
                '--include-filter',
                'CtsSimpleCpuTestCases android.simplecpu.cts.SimpleCpuTest',
        ],
}

CONFIG['EXTRA_ATTRIBUTES'] = {}

CONFIG['EXTRA_ARTIFACTS'] = {}
CONFIG['PREREQUISITES'] = {}

from generate_controlfiles_new import main

if __name__ == '__main__':
    main(CONFIG)
