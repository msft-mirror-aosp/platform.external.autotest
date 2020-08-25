
# Copyright 2020 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# !!! GENERATED FILE. DO NOT EDIT !!!

load('//metadata/test_common.star', 'test_common')

def define_tests():
    return [
        test_common.define_test(
            'enterprise/CFM_AtrusUpdaterStress',
            suites = ['hotrod-remora'],
        ),
        test_common.define_test(
            'enterprise/CFM_AutoZoomSanity',
            suites = [],
        ),
        test_common.define_test(
            'enterprise/CFM_AutotestSmokeTest',
            suites = ['bluestreak-pre-cq', 'hotrod'],
        ),
        test_common.define_test(
            'enterprise/CFM_BizlinkUpdater',
            suites = [],
        ),
        test_common.define_test(
            'enterprise/CFM_CEC',
            suites = [],
        ),
        test_common.define_test(
            'enterprise/CFM_HuddlyMonitor',
            suites = [],
        ),
        test_common.define_test(
            'enterprise/CFM_HuddlyUpdater',
            suites = [],
        ),
        test_common.define_test(
            'enterprise/CFM_LogitechMeetupUpdater',
            suites = ['hotrod'],
        ),
        test_common.define_test(
            'enterprise/CFM_LogitechPtzUpdater',
            suites = ['hotrod'],
        ),
        test_common.define_test(
            'enterprise/CFM_MeetAppSanity',
            suites = ['hotrod-remora'],
        ),
        test_common.define_test(
            'enterprise/CFM_MimoUpdater',
            suites = ['hotrod-remora'],
        ),
        test_common.define_test(
            'enterprise/CFM_SiSFwUpdater',
            suites = [],
        ),
        test_common.define_test(
            'enterprise/ClearTPM',
            suites = [],
        ),
        test_common.define_test(
            'enterprise/FakeEnrollment',
            suites = [],
        ),
        test_common.define_test(
            'enterprise/KioskEnrollment',
            suites = [],
        ),
        test_common.define_test(
            'enterprise/KioskEnrollmentServer',
            suites = ['enterprise'],
        ),
        test_common.define_test(
            'enterprise/KioskPerf',
            suites = [],
        ),
        test_common.define_test(
            'enterprise/OnlineDemoMode',
            suites = [],
        ),
        test_common.define_test(
            'enterprise/OnlineDemoModeEnrollment',
            suites = [],
        ),
        test_common.define_test(
            'enterprise/PowerManagement',
            suites = [],
        ),
        test_common.define_test(
            'enterprise/RemoraRequisition',
            suites = [],
        ),
        test_common.define_test(
            'enterprise/RemoraRequisitionDisplayUsage',
            suites = ['hotrod-remora'],
        ),
        test_common.define_test(
            'enterprise/RemoraRequisitionDisplayUsageServer',
            suites = ['hotrod-remora'],
        ),
        test_common.define_test(
            'enterprise/RemoraRequisitionServer',
            suites = [],
        ),
        test_common.define_test(
            'enterprise/SmbProviderDaemon',
            suites = [],
        )
    ]
