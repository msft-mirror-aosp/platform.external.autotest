
# Copyright 2020 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# !!! GENERATED FILE. DO NOT EDIT !!!

load('//metadata/test_common.star', 'test_common')

def define_tests():
    return [
        test_common.define_test(
            'platform/AccurateTime',
            suites = [],
        ),
        test_common.define_test(
            'platform/ActivateDate',
            suites = ['regression'],
        ),
        test_common.define_test(
            'platform/AesThroughput',
            suites = ['hwqual', 'kernel_per-build_benchmarks'],
        ),
        test_common.define_test(
            'platform/AnomalyDetector',
            suites = ['bvt-perbuild'],
        ),
        test_common.define_test(
            'platform/BootLockbox',
            suites = [],
        ),
        test_common.define_test(
            'platform/BootLockboxServer',
            suites = ['bvt-perbuild'],
        ),
        test_common.define_test(
            'platform/BootPerf',
            suites = ['crosbolt_perf_nightly'],
        ),
        test_common.define_test(
            'platform/CheckErrorsInLog',
            suites = [],
        ),
        test_common.define_test(
            'platform/ChromeCgroups',
            suites = ['regression'],
        ),
        test_common.define_test(
            'platform/CleanShutdown',
            suites = [],
        ),
        test_common.define_test(
            'platform/CloseOpenLid',
            suites = [],
        ),
        test_common.define_test(
            'platform/CompromisedStatefulPartition',
            suites = ['bvt-perbuild'],
        ),
        test_common.define_test(
            'platform/CorruptRootfs',
            suites = [],
        ),
        test_common.define_test(
            'platform/CrashStateful',
            suites = [],
        ),
        test_common.define_test(
            'platform/CrosDisksArchive',
            suites = ['bvt-perbuild'],
        ),
        test_common.define_test(
            'platform/CrosDisksFilesystem',
            suites = ['bvt-perbuild'],
        ),
        test_common.define_test(
            'platform/CrosDisksFormat',
            suites = ['bvt-perbuild'],
        ),
        test_common.define_test(
            'platform/CrosDisksRename',
            suites = ['bvt-perbuild'],
        ),
        test_common.define_test(
            'platform/CrosDisksSshfs',
            suites = ['bvt-perbuild'],
        ),
        test_common.define_test(
            'platform/Crossystem',
            suites = ['bvt-perbuild'],
        ),
        test_common.define_test(
            'platform/Crouton',
            suites = [],
        ),
        test_common.define_test(
            'platform/CryptohomeBadPerms',
            suites = ['bvt-perbuild'],
        ),
        test_common.define_test(
            'platform/CryptohomeChangePassword',
            suites = ['bvt-perbuild'],
        ),
        test_common.define_test(
            'platform/CryptohomeFio',
            suites = ['bvt-perbuild'],
        ),
        test_common.define_test(
            'platform/CryptohomeKeyEviction',
            suites = ['bvt-perbuild'],
        ),
        test_common.define_test(
            'platform/CryptohomeLECredentialManager',
            suites = [],
        ),
        test_common.define_test(
            'platform/CryptohomeLECredentialManagerServer',
            suites = ['bvt-perbuild'],
        ),
        test_common.define_test(
            'platform/CryptohomeMigrateKey',
            suites = ['bvt-perbuild'],
        ),
        test_common.define_test(
            'platform/CryptohomeMount',
            suites = ['bvt-perbuild'],
        ),
        test_common.define_test(
            'platform/CryptohomeMultiple',
            suites = ['bvt-perbuild'],
        ),
        test_common.define_test(
            'platform/CryptohomeNonDirs',
            suites = ['bvt-perbuild'],
        ),
        test_common.define_test(
            'platform/CryptohomeStress',
            suites = ['bvt-perbuild'],
        ),
        test_common.define_test(
            'platform/CryptohomeTPMReOwn',
            suites = [],
        ),
        test_common.define_test(
            'platform/CryptohomeTPMReOwnServer',
            suites = ['bvt-perbuild'],
        ),
        test_common.define_test(
            'platform/CryptohomeTestAuth',
            suites = ['bvt-perbuild'],
        ),
        test_common.define_test(
            'platform/CryptohomeTpmLiveTest',
            suites = [],
        ),
        test_common.define_test(
            'platform/CryptohomeTpmLiveTestServer',
            suites = ['bvt-perbuild'],
        ),
        test_common.define_test(
            'platform/DBusMachineIdRotation',
            suites = ['experimental'],
        ),
        test_common.define_test(
            'platform/DaemonRespawn',
            suites = [],
        ),
        test_common.define_test(
            'platform/DebugDaemonDumpDebugLogs',
            suites = [],
        ),
        test_common.define_test(
            'platform/DebugDaemonGetNetworkStatus',
            suites = [],
        ),
        test_common.define_test(
            'platform/DebugDaemonGetPerfData',
            suites = ['bvt-perbuild'],
        ),
        test_common.define_test(
            'platform/DebugDaemonGetPerfOutputFd',
            suites = ['bvt-perbuild'],
        ),
        test_common.define_test(
            'platform/DebugDaemonGetRoutes',
            suites = [],
        ),
        test_common.define_test(
            'platform/DebugDaemonPerfDataInFeedbackLogs',
            suites = ['bvt-perbuild'],
        ),
        test_common.define_test(
            'platform/DebugDaemonPing',
            suites = [],
        ),
        test_common.define_test(
            'platform/DebugDaemonTracePath',
            suites = [],
        ),
        test_common.define_test(
            'platform/EncryptedStateful',
            suites = ['bvt-perbuild'],
        ),
        test_common.define_test(
            'platform/ExternalUSBBootStress',
            suites = [],
        ),
        test_common.define_test(
            'platform/ExternalUSBStress',
            suites = [],
        ),
        test_common.define_test(
            'platform/ExternalUsbPeripherals',
            suites = [],
        ),
        test_common.define_test(
            'platform/FileNum',
            suites = [],
        ),
        test_common.define_test(
            'platform/FileSize',
            suites = [],
        ),
        test_common.define_test(
            'platform/Firewall',
            suites = ['bvt-perbuild'],
        ),
        test_common.define_test(
            'platform/FlashErasers',
            suites = ['faft_flashrom'],
        ),
        test_common.define_test(
            'platform/Flashrom',
            suites = ['faft_flashrom'],
        ),
        test_common.define_test(
            'platform/GesturesRegressionTest',
            suites = ['bvt-perbuild', 'touch'],
        ),
        test_common.define_test(
            'platform/HWwatchdog',
            suites = ['kernel_per-build_regression'],
        ),
        test_common.define_test(
            'platform/HighResTimers',
            suites = ['bvt-perbuild', 'hwqual'],
        ),
        test_common.define_test(
            'platform/ImageLoader',
            suites = [],
        ),
        test_common.define_test(
            'platform/ImageLoaderServer',
            suites = ['bvt-perbuild'],
        ),
        test_common.define_test(
            'platform/InitLoginPerf',
            suites = [],
        ),
        test_common.define_test(
            'platform/InitLoginPerfServer',
            suites = ['crosbolt_perf_weekly'],
        ),
        test_common.define_test(
            'platform/InputBrightness',
            suites = ['bvt-perbuild'],
        ),
        test_common.define_test(
            'platform/InputBrowserNav',
            suites = [],
        ),
        test_common.define_test(
            'platform/InputNewTab',
            suites = ['bvt-perbuild'],
        ),
        test_common.define_test(
            'platform/InputScreenshot',
            suites = ['bvt-perbuild'],
        ),
        test_common.define_test(
            'platform/InputVolume',
            suites = ['bvt-perbuild'],
        ),
        test_common.define_test(
            'platform/InstallFW',
            suites = [],
        ),
        test_common.define_test(
            'platform/InstallRecoveryImage',
            suites = [],
        ),
        test_common.define_test(
            'platform/InstallTestImage',
            suites = [],
        ),
        test_common.define_test(
            'platform/InternalDisplay',
            suites = ['bvt-perbuild'],
        ),
        test_common.define_test(
            'platform/KernelVersion',
            suites = ['hwqual', 'regression'],
        ),
        test_common.define_test(
            'platform/LibCBench',
            suites = [],
        ),
        test_common.define_test(
            'platform/LogDupSuppression',
            suites = ['experimental'],
        ),
        test_common.define_test(
            'platform/LogNonKernelKmsg',
            suites = ['experimental'],
        ),
        test_common.define_test(
            'platform/LogoutPerf',
            suites = ['bvt-perbuild', 'crosbolt_perf_perbuild'],
        ),
        test_common.define_test(
            'platform/LongPressPower',
            suites = [],
        ),
        test_common.define_test(
            'platform/MemCheck',
            suites = ['bvt-perbuild'],
        ),
        test_common.define_test(
            'platform/MetricsUploader',
            suites = ['experimental'],
        ),
        test_common.define_test(
            'platform/MouseScrollTest',
            suites = ['crosbolt_perf_nightly'],
        ),
        test_common.define_test(
            'platform/Nvram',
            suites = [],
        ),
        test_common.define_test(
            'platform/OpenSSLActual',
            suites = [],
        ),
        test_common.define_test(
            'platform/Perf',
            suites = ['bvt-perbuild'],
        ),
        test_common.define_test(
            'platform/Pkcs11ChangeAuthData',
            suites = ['experimental'],
        ),
        test_common.define_test(
            'platform/Pkcs11Events',
            suites = ['experimental'],
        ),
        test_common.define_test(
            'platform/Pkcs11InitOnLogin',
            suites = ['bvt-perbuild'],
        ),
        test_common.define_test(
            'platform/Pkcs11InitUnderErrors',
            suites = ['regression'],
        ),
        test_common.define_test(
            'platform/Pkcs11LoadPerf',
            suites = [],
        ),
        test_common.define_test(
            'platform/Powerwash',
            suites = [],
        ),
        test_common.define_test(
            'platform/PrintJob',
            suites = ['audio_advanced'],
        ),
        test_common.define_test(
            'platform/Quipper',
            suites = ['experimental'],
        ),
        test_common.define_test(
            'platform/Rootdev',
            suites = ['regression'],
        ),
        test_common.define_test(
            'platform/RotationFps',
            suites = ['crosbolt_arc_perf_nightly'],
        ),
        test_common.define_test(
            'platform/S0ixCycle',
            suites = [],
        ),
        test_common.define_test(
            'platform/S3Cycle',
            suites = [],
        ),
        test_common.define_test(
            'platform/ScrollTest',
            suites = ['crosbolt_perf_nightly'],
        ),
        test_common.define_test(
            'platform/SecureEraseFile',
            suites = ['experimental'],
        ),
        test_common.define_test(
            'platform/SessionManagerBlockDevmodeSetting',
            suites = ['experimental'],
        ),
        test_common.define_test(
            'platform/SessionManagerStateKeyGeneration',
            suites = ['experimental'],
        ),
        test_common.define_test(
            'platform/StageAndRecover',
            suites = ['platform_test_nightly'],
        ),
        test_common.define_test(
            'platform/SuspendResumeTiming',
            suites = ['usb_detect'],
        ),
        test_common.define_test(
            'platform/TLSDate',
            suites = ['bvt-perbuild'],
        ),
        test_common.define_test(
            'platform/TLSDateActual',
            suites = ['bvt-perbuild'],
        ),
        test_common.define_test(
            'platform/TPMEvict',
            suites = ['regression'],
        ),
        test_common.define_test(
            'platform/TabletMode',
            suites = ['tablet_mode'],
        ),
        test_common.define_test(
            'platform/TempFS',
            suites = [],
        ),
        test_common.define_test(
            'platform/ToolchainTests',
            suites = ['bvt-perbuild', 'toolchain-tests'],
        ),
        test_common.define_test(
            'platform/TraceClockMonotonic',
            suites = ['bvt-perbuild'],
        ),
        test_common.define_test(
            'platform/TrackpadStressServer',
            suites = [],
        ),
        test_common.define_test(
            'platform/UReadAheadServer',
            suites = ['bvt-perbuild'],
        ),
        test_common.define_test(
            'platform/USBHIDWake',
            suites = [],
        ),
        test_common.define_test(
            'platform/UdevVars',
            suites = ['experimental'],
        ),
        test_common.define_test(
            'platform/Vpd',
            suites = ['regression'],
        )
    ]
