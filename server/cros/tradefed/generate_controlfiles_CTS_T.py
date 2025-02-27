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
CONFIG['EXECUTABLE_PATH_LIST'] = ['android-cts/jdk/bin/java']
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

# Tests are only run if ANY of the following USE flags are on for the board.
CONFIG['TAUTO_HW_DEPS'] = ['android-vm-tm']

# The dashboard suppresses upload to APFE for GS directories (based on autotest
# tag) that contain 'tradefed-run-collect-tests'. b/119640440
# Do not change the name/tag without adjusting the dashboard.
_COLLECT = 'tradefed-run-collect-tests-only-internal'
_PUBLIC_COLLECT = 'tradefed-run-collect-tests-only'

# Modules to skip in collect-tests-only job.
# TODO(b/329176953): Re-include these modules once fixed in upstream.
CONFIG['COLLECT_EXCLUDE_MODULES'] = [
        'CtsIcu4cTestCases',
        'CtsMediaDecoderTestCases',
        'CtsSkQPTestCases',
        'CtsVideoTestCases',
]

CONFIG['CTS_JOB_RETRIES_IN_PUBLIC'] = 1
CONFIG['CTS_QUAL_RETRIES'] = 9
CONFIG['CTS_MAX_RETRIES'] = {
}

CONFIG['SPLIT_SUITES'] = {
        'DEV_SUITE_FORMAT': 'suite:arc-cts-{abi}-{shard}',
        'DEV_SUITE_LONG': 'suite:arc-cts-long',
        'DEV_VM_STABLE_SUITE_FORMAT': 'suite:arc-cts-vm-stable-{abi}-{shard}',
        'DEV_VM_STABLE_SUITE_LONG': 'suite:arc-cts-vm-stable-long',
        'QUAL_SUITE_FORMAT': 'suite:arc-cts-qual-{abi}-{shard}',
        'QUAL_SUITE_LONG': 'suite:arc-cts-qual-long',
        'MAX_RUNTIME_SECS': 9000,  # 2.5hr; hard limit is 3hr
        'PER_TEST_OVERHEAD_SECS': 600,  # 10min for DUT provisioning etc.
        # P95 runtime from PASS/WARN runs between 20250201-20250227, minus fixed
        # approximate overhead of 300 secs with lower bound of 300 secs.
        # https://plx.corp.google.com/scripts2/script_f6._9000b0_45f2_4cd1_9f61_234a4f879717
        'RUNTIME_HINT_SECS': {
                'CtsAbiOverrideHost': 325,
                'CtsAcceleration': 300,
                'CtsAccessibility': 806,
                'CtsAccountManager': 407,
                'CtsAccountsHost': 300,
                'CtsActivity': 300,
                'CtsAdServicesDevice': 300,
                'CtsAdb': 300,
                'CtsAdmin': 300,
                'CtsAlarmManager': 887,
                'CtsAmbientContextService': 300,
                'CtsAndroid': 410,
                'CtsAngleIntegrationHost': 300,
                'CtsAnimation': 608,
                'CtsApacheHttp': 300,
                'CtsApex': 306,
                'CtsApp': 13000,
                'CtsAppTestCases.feature.ctshardware': 300,
                'CtsArt': 300,
                'CtsAslrMalloc': 300,
                'CtsAssist': 333,
                'CtsAtomicInstall': 300,
                'CtsAtraceHost': 300,
                'CtsAttentionServiceDevice': 300,
                'CtsAutoFillService': 6415,
                'CtsBackgroundRestrictions': 300,
                'CtsBackup': 1024,
                'CtsBatterySaving': 300,
                'CtsBiometrics': 300,
                'CtsBionic': 770,
                'CtsBlobStore': 582,
                'CtsBluetooth': 1293,
                'CtsBoot': 300,
                'CtsBugreportTestCases': 300,
                'CtsCalendarProvider': 300,
                'CtsCalendarcommon2': 300,
                'CtsCallLogTestCases': 300,
                'CtsCameraApi25TestCases': 300,
                'CtsCameraApi31TestCases': 300,
                'CtsCameraTestCases': 7464,
                'CtsCar': 300,
                'CtsCarrierApi': 300,
                'CtsClassLoaderFactory': 300,
                'CtsClassloaderSplitsHost': 413,
                'CtsClasspathDeviceInfo': 300,
                'CtsClasspaths': 300,
                'CtsColorMode': 300,
                'CtsCompanionDeviceManager': 300,
                'CtsContactsProvider': 885,
                'CtsContent': 2637,
                'CtsControlsDevice': 342,
                'CtsCppTools': 300,
                'CtsCurrentApiSignature': 300,
                'CtsDatabase': 478,
                'CtsDeqp': 9436,
                'CtsDeqpTestCases.isolated-flaky-tests': 300,
                'CtsDevice': 957,
                'CtsDexMetadataHost': 300,
                'CtsDisplay': 470,
                'CtsDomainVerification': 507,
                'CtsDownloadManager': 300,
                'CtsDpi': 300,
                'CtsDreams': 300,
                'CtsDrm': 300,
                'CtsDropBoxManagerTestCases': 300,
                'CtsDumpsysHost': 300,
                'CtsDynamic': 2741,
                'CtsEdiHost': 383,
                'CtsEffect': 300,
                'CtsExternalService': 300,
                'CtsExtractNativeLibsHost': 4155,
                'CtsFileSystem': 6663,
                'CtsFragment': 511,
                'CtsFrameRateOverride': 396,
                'CtsFsMgr': 300,
                'CtsGame': 383,
                'CtsGesture': 300,
                'CtsGpu': 412,
                'CtsGraphics': 1853,
                'CtsGwpAsan': 319,
                'CtsHardware': 745,
                'CtsHarmfulAppWarningHost': 300,
                'CtsHdmiCecHost': 397,
                'CtsHiddenApi': 1119,
                'CtsHostTzData': 300,
                'CtsHostside': 4726,
                'CtsIcu': 2278,
                'CtsIdentity': 300,
                'CtsIke': 300,
                'CtsIncidentHost': 836,
                'CtsIncrementalInstallHost': 307,
                'CtsInit': 315,
                'CtsInlineMocking': 300,
                'CtsInput': 2853,
                'CtsInstallHostTestCases': 1706,
                'CtsInstalledLoadingProgressHost': 887,
                'CtsInstantApp': 300,
                'CtsIntentSignature': 300,
                'CtsJdwp': 1838,
                'CtsJni': 300,
                'CtsJobScheduler': 2344,
                'CtsJvmti': 4043,
                'CtsKernelConfigTestCases': 300,
                'CtsKeystore': 4889,
                'CtsLeanbackJank': 300,
                'CtsLegacyNotification': 395,
                'CtsLibcore': 9222,
                'CtsLiblog': 300,
                'CtsLibnativehelper': 362,
                'CtsLocale': 300,
                'CtsLocation': 498,
                'CtsLogd': 300,
                'CtsMatchFlag': 300,
                'CtsMediaAudioTestCases': 3008,
                'CtsMediaAudioTestCases.ctshardware': 3853,
                'CtsMediaBitstreamsTestCases': 1478,
                'CtsMediaCodecTestCases': 1770,
                'CtsMediaCodecTestCases.ctshardware': 3744,
                'CtsMediaDecoderTestCases': 6528,
                'CtsMediaDecoderTestCases.ctshardware': 10029,
                'CtsMediaDrmFrameworkTestCases': 570,
                'CtsMediaDrmFrameworkTestCases.ctshardware': 692,
                'CtsMediaEncoderTestCases': 4921,
                'CtsMediaEncoderTestCases.ctshardware': 6205,
                'CtsMediaExtractorTestCases': 300,
                'CtsMediaExtractorTestCases.ctshardware': 300,
                'CtsMediaHostTestCases': 751,
                'CtsMediaMiscTestCases': 916,
                'CtsMediaMiscTestCases.ctshardware': 2047,
                'CtsMediaMuxerTestCases': 300,
                'CtsMediaMuxerTestCases.ctshardware': 300,
                'CtsMediaParserHostTestCases': 321,
                'CtsMediaParserTestCases': 300,
                'CtsMediaPerformanceClassTestCases': 300,
                'CtsMediaPlayerTestCases': 6899,
                'CtsMediaPlayerTestCases.ctshardware': 12925,
                'CtsMediaProviderTranscodeTests': 300,
                'CtsMediaRecorderTestCases': 921,
                'CtsMediaRecorderTestCases.ctshardware': 965,
                'CtsMediaStressTestCases': 11248,
                'CtsMediaTranscodingTestCases': 300,
                'CtsMediaV2TestCases': 1878,
                'CtsMidiTestCases': 300,
                'CtsMimeMap': 300,
                'CtsMocking': 383,
                'CtsMultiUser': 300,
                'CtsMusicRecognition': 300,
                'CtsNNAPI': 876,
                'CtsNNAPIBenchmark': 300,
                'CtsNNAPIJava': 300,
                'CtsNNAPIStatsdAtomHost': 300,
                'CtsNative': 623,
                'CtsNativeMediaAAudioTestCases.ctshardware': 417,
                'CtsNdef': 300,
                'CtsNdkBinder': 300,
                'CtsNearbyFastPair': 300,
                'CtsNet': 3190,
                'CtsNetTestCases.ctshardware': 2319,
                'CtsNfc': 300,
                'CtsNoPermission': 300,
                'CtsOnDevicePersonalization': 300,
                'CtsOpenG': 447,
                'CtsOs': 2961,
                'CtsPackage': 1195,
                'CtsPdf': 980,
                'CtsPerfetto': 346,
                'CtsPermission': 2884,
                'CtsPersistentDataBlockManager': 300,
                'CtsPhotoPickerTest': 300,
                'CtsPreference': 761,
                'CtsPrint': 300,
                'CtsProcessTest': 300,
                'CtsProto': 300,
                'CtsProvider': 675,
                'CtsQuickAccessWallet': 757,
                'CtsRebootReadiness': 300,
                'CtsRenderscript': 422,
                'CtsResolverService': 300,
                'CtsResourcesLoader': 300,
                'CtsRole': 773,
                'CtsRollbackManagerHostTestCases': 300,
                'CtsRotationResolverServiceDevice': 300,
                'CtsRs': 368,
                'CtsSafetyCenter': 340,
                'CtsSample': 300,
                'CtsSax': 300,
                'CtsScopedStorage': 1063,
                'CtsSdkExtensions': 300,
                'CtsSearchUiService': 300,
                'CtsSeccompHost': 327,
                'CtsSecureFrpInstall': 300,
                'CtsSecurity': 1090,
                'CtsSelinux': 300,
                'CtsSensor': 3704,
                'CtsSensorTestCases.ctshardware': 3081,
                'CtsServiceKillTestCases': 300,
                'CtsSettings': 300,
                'CtsShared': 300,
                'CtsSharesheet': 300,
                'CtsShortcut': 689,
                'CtsSignedConfigHost': 300,
                'CtsSilentUpdateHost': 300,
                'CtsSim': 300,
                'CtsSimpleCpu': 393,
                'CtsSimpleperf': 493,
                'CtsSkQP': 300,
                'CtsSlice': 300,
                'CtsSmartspaceService': 300,
                'CtsSoundTrigger': 300,
                'CtsSpeech': 300,
                'CtsStagedInstallHostTestCases': 389,
                'CtsStatsd': 7759,
                'CtsStrictJavaPackages': 300,
                'CtsSuspendApps': 300,
                'CtsSustainedPerformanceHost': 300,
                'CtsSync': 300,
                'CtsSystem': 1387,
                'CtsTaggingHost': 657,
                'CtsTaskFpsCallback': 300,
                'CtsTelecom': 402,
                'CtsTelephony': 300,
                'CtsTestHarnessMode': 300,
                'CtsTetheringTest': 300,
                'CtsText': 640,
                'CtsTfliteNnapiDelegate': 300,
                'CtsTheme': 311,
                'CtsThermal': 1512,
                'CtsTileService': 300,
                'CtsTime': 300,
                'CtsToast': 300,
                'CtsTransition': 300,
                'CtsTranslation': 300,
                'CtsTv': 300,
                'CtsUffdGc': 300,
                'CtsUi': 530,
                'CtsUidIsolation': 300,
                'CtsUsageStats': 2149,
                'CtsUsb': 300,
                'CtsUses': 300,
                'CtsUtil': 300,
                'CtsUwb': 300,
                'CtsVcn': 300,
                'CtsVideo': 3011,
                'CtsView': 3107,
                'CtsViewTestCases.ctshardware': 4589,
                'CtsVirtualDevices': 300,
                'CtsVoice': 532,
                'CtsVr': 300,
                'CtsWallpaperEffectsGenerationService': 300,
                'CtsWebkit': 644,
                'CtsWidget': 4263,
                'CtsWifi': 3814,
                'CtsWifiTestCases.ctshardware': 3370,
                'CtsWindowManager': 5022,
                'CtsWrap': 300,
                'MicrodroidHost': 300,
                'MicrodroidTestApp': 300,
                'ResourceObserverNativeTest': 300,
                'art-run-test-048-reflect-v8': 300,
                'art_libnativebridge_cts_tests': 300,
                'art_standalone_dex2oat_cts_tests': 300,
                'art_standalone_libartpalette_tests': 300,
                'art_standalone_libdexfile_external_tests': 300,
                'libnativeloader_test': 300,
                'odsign_e2e_tests': 300,
                'signed-Cts': 300,
                'vm-tests-tf': 2152,
        },
}

# Timeout in hours.
CONFIG['CTS_TIMEOUT_DEFAULT'] = 1.0
CONFIG['CTS_TIMEOUT'] = {
        'CtsAppSecurityHostTestCases': 2.0,
        'CtsAutoFillServiceTestCases': 2.5,  # TODO(b/134662826)
        'CtsCameraTestCases': 2.0,
        'CtsDeqpTestCases': 30.0,
        'CtsDeqpTestCases.dEQP-EGL': 2.0,
        'CtsDeqpTestCases.dEQP-GLES2': 2.0,
        'CtsDeqpTestCases.dEQP-GLES3': 6.0,
        'CtsDeqpTestCases.dEQP-GLES31': 6.0,
        'CtsDeqpTestCases.dEQP-VK': 15.0,
        'CtsFileSystemTestCases': 3.0,
        'CtsHardwareTestCases': 2.0,
        'CtsHostsideNetworkTests': 2.0,
        'CtsIcuTestCases': 2.0,
        'CtsKeystoreTestCases': 2.0,
        'CtsLibcoreOjTestCases': 2.0,
        'CtsMediaEncoderTestCases': 2.0,
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
        'CtsWindowManagerDeviceTestCases': 1.5,
        _COLLECT: 2.5,
        _PUBLIC_COLLECT: 2.5,
}

# Any test that runs as part as blocking BVT needs to be stable and fast. For
# this reason we enforce a tight timeout on these modules/jobs.
# Timeout in hours.
#
# CtsGraphicsTestCases passing runs take 2000~ secs on slower models.
# 1hr = 3600sec should be plenty.
CONFIG['BVT_TIMEOUT'] = 1.0

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

# Tests to run against each release build via suite:bvt-arc.
CONFIG['PERBUILD_TESTS'] = [
        'CtsEdiHostTestCases',
        'CtsGraphicsTestCases',
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

# Modules to add to suite:arc-cts-media
CONFIG['MEDIA_SUITE_MODULES'] = [
        'CtsMedia.*',
        'CtsVideo.*',
]

CONFIG['NEEDS_CTS_HELPERS'] = [
        'CtsPrintTestCases',
]

CONFIG['SHARD_COUNT'] = {'CtsDeqpTestCases': 10}

CONFIG['CAMERA_MODULES'] = [
        # CONTAINS ONLY CAMERA TESTS
        'CtsCameraTestCases',
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
        # "+.*",

        # These tests failed more than once between Oct/13 and Nov/09 2022 on R.
        "+CtsApp.*",
        "+CtsBionic.*",
        "+CtsCamera.*",
        "+CtsJobScheduler.*",
        "+CtsNet.*",
        "+CtsOs.*",
        "+CtsProvider.*",
        "+CtsSimpleperf.*",
        "+CtsStatsd.*",

        # These tests has suspicious bug reports on R.
        '+CtsAccessibility.*',  # b/192310577, b/196934844
        '+CtsApp.*',  # b/216741475
        '+CtsAssist.*',  # b/160541876
        '+CtsAutoFillService.*',  # b/216897339
        '+CtsBionic.*',  # b/160851611
        '+CtsBlobStore.*',  # b/180681350
        '+CtsBoot.*',  # b/174224484
        '+CtsDownloadManager.*',  # b/163729385
        '+CtsDropBoxManagerTestCases.*',  # b/177029550
        '+CtsDynamic.*',  # b/163121640
        '+CtsFragment.*',  # b/251276296
        '+CtsIke.*',  # b/160541882
        '+CtsInput.*',  # b/253540001, b/191413875
        '+CtsJni.*',  # b/160867403
        '+CtsJobScheduler.*',  # b/226422237
        '+CtsMidiTestCases.*',  # b/222242213
        '+CtsNdkBinder.*',  # b/163123128
        '+CtsNet.*',  # b/258074918
        '+CtsOs.*',  # b/b/187745471
        '+CtsPerfetto.*',  # b/203614416
        '+CtsProvider.*',  # b/212194116
        '+CtsRs.*',  # b/166168119
        '+CtsScopedStorage.*',  # b/232055847
        '+CtsSimpleperf.*',  # b/247434877
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

IPV6_MODULES = []

CONFIG['WIFI_MODULES'] = [
        'CtsNetApi23TestCases',
        'CtsNetTestCases',
        'CtsNetTestCasesMaxTargetSdk31',
        'CtsJobSchedulerTestCases',
        'CtsStatsdAtomHostTestCases',
        'CtsStatsdHostTestCases',
        'CtsWifiTestCases',
]

# Preconditions applicable to public and internal tests.
CONFIG['PRECONDITION'] = {
        # b/330127117#comment42: sound_effects_enabled can be set to 1 during
        # retries, causing test failures.
        'CtsMediaAudioTestCases': [
                "'adb shell settings put system sound_effects_enabled 0'",
        ],
        # b/390260941#comment61: Extend idle timeout to avoid interfering with
        # doze mode-related tests.
        'CtsHostsideNetworkTests': [
                "'adb shell device_config set_sync_disabled_for_tests persistent'",
                "'adb shell device_config put device_idle idle_to 90000'",
        ]
}

CONFIG['LOGIN_PRECONDITION'] = {
}

# Preconditions applicable to public tests.
CONFIG['PUBLIC_PRECONDITION'] = {
        # b/330127117#comment42: sound_effects_enabled can be set to 1 during
        # retries, causing test failures.
        'CtsMediaAudioTestCases': [
                "'adb shell settings put system sound_effects_enabled 0'",
        ],
        # b/390260941#comment61: Extend idle timeout to avoid interfering with
        # doze mode-related tests.
        'CtsHostsideNetworkTests': [
                "'adb shell device_config set_sync_disabled_for_tests persistent'",
                "'adb shell device_config put device_idle idle_to 90000'",
        ]
}

for m in IPV6_MODULES:
    CONFIG['PUBLIC_PRECONDITION'][m] = _WIFI_CONNECT_COMMANDS_V2

for m in CONFIG['WIFI_MODULES']:
    CONFIG['PUBLIC_PRECONDITION'][m] = _WIFI_CONNECT_COMMANDS_V2
    CONFIG['PRECONDITION'][m] = _WIFI_CONNECT_COMMANDS_V2

# Internal lab dependencies. Key can be either abi or module name.
CONFIG['LAB_DEPENDENCY'] = {
        'x86': ['cts_abi_x86'],
        # b/346839603: Deqp require "large" cloudbot or legacy drone
        'CtsDeqpTestCases': ['label-bot_size:BOT_SIZE_LARGE'],
        # b/369256917: MediaStress requires "large" cloudbot or legacy drone
        'CtsMediaStressTestCases': ['label-bot_size:BOT_SIZE_LARGE'],
}

# Internal lab dependencies that apply to all tests.
CONFIG['LAB_DEPENDENCY_GLOBAL'] = ['arc', 'label-bot_size:BOT_SIZE_LARGE']

# b/343614317: Wifi-dependent modules need device with label-wifi_on_site
for m in CONFIG['WIFI_MODULES']:
    CONFIG['LAB_DEPENDENCY'][m] = ['wifi_on_site']

# Public lab dependencies.
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
        'CtsSensorTestCases',
]


REGRESSION_SUITES = ['suite:arc-cts']
REGRESSION_AND_QUAL_SUITES = CONFIG['QUAL_SUITE_NAMES'] + REGRESSION_SUITES

CONFIG['EXTRA_MODULES'] = {
        'CtsDeqpTestCases': {
                'CtsDeqpTestCases.isolated-flaky-tests':
                ['suite:arc-cts-long', 'suite:arc-cts-qual-long'],
        },
}

# In addition to EXTRA_MODULES, these modules do require separate control files
# for internal and moblab.
CONFIG['HARDWAREONLY_EXTRA_MODULES'] = {
        'CtsAppTestCases': {
                'CtsAppTestCases.feature': [],
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
        'CtsDeqpTestCases.isolated-flaky-tests': [
                '--include-filter',
                'CtsDeqpTestCases dEQP-VK.pipeline.render_to_image.core.2d_array.huge.height_layers#r8g8b8a8_unorm_d24_unorm_s8_uint',
                '--include-filter',
                'CtsDeqpTestCases dEQP-GLES3.functional.shaders.builtin_functions.precision.refract.lowp_vertex#vec4',
                '--include-filter',
                'CtsDeqpTestCases dEQP-GLES3.functional.texture.units.all_units.only_cube#0',
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

CONFIG['PREREQUISITES'] = {
        'CtsCameraTestCases': [
                'camera_enumerate',
        ],
        'CtsMediaPlayerTestCases': [
                'camera_enumerate',
        ],
        'CtsStatsdAtomHostTestCases': [
                'camera_enumerate',
        ],
}

from generate_controlfiles_new import main

if __name__ == '__main__':
    main(CONFIG)
