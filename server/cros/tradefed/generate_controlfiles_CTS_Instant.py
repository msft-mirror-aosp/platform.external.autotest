#!/usr/bin/env python3
# Lint as: python2, python3
# Copyright 2016 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import os

from generate_controlfiles_common import main


_ALL = 'all'

CONFIG = {}

CONFIG['TEST_NAME'] = 'cheets_CTS_Instant'
CONFIG['BUNDLE_CONFIG_PATH'] = os.path.abspath(os.path.join(os.path.dirname(__file__),
        '..', '..', 'site_tests', CONFIG['TEST_NAME'], 'bundle_url_config.json'))
CONFIG['DOC_TITLE'] = \
    'Android Compatibility Test Suite for Instant Apps (CTS Instant)'
CONFIG['MOBLAB_SUITE_NAME'] = 'suite:cts_P, suite:cts'
CONFIG['COPYRIGHT_YEAR'] = 2018
CONFIG['AUTHKEY'] = ''

CONFIG['LARGE_MAX_RESULT_SIZE'] = 1000 * 1024
CONFIG['NORMAL_MAX_RESULT_SIZE'] = 500 * 1024

CONFIG['TRADEFED_CTS_COMMAND'] = 'cts-instant'
CONFIG['TRADEFED_RETRY_COMMAND'] = 'retry'
CONFIG['TRADEFED_DISABLE_REBOOT'] = False
CONFIG['TRADEFED_DISABLE_REBOOT_ON_COLLECTION'] = True
CONFIG['TRADEFED_MAY_SKIP_DEVICE_INFO'] = False
CONFIG['TRADEFED_EXECUTABLE_PATH'] = \
    'android-cts_instant/tools/cts-instant-tradefed'
CONFIG['TRADEFED_IGNORE_BUSINESS_LOGIC_FAILURE'] = False

# TODO(b/287160788): Implement split suites
CONFIG['INTERNAL_SUITE_NAMES'] = ['suite:arc-cts', 'suite:arc-cts-long']
CONFIG['QUAL_SUITE_NAMES'] = ['suite:arc-cts-qual', 'suite:arc-cts-qual-long']

# CTS Instant is relatively small (= shorter turnaround time), and very
# unlikely to fail alone (= regression almost always caught by the
# corresponding CTS module.) For now we don't generate this type of control
# files.
CONFIG['CONTROLFILE_TEST_FUNCTION_NAME'] = 'run_TS'
CONFIG['CONTROLFILE_WRITE_SIMPLE_QUAL_AND_REGRESS'] = True
CONFIG['CONTROLFILE_WRITE_CAMERA'] = False
CONFIG['CONTROLFILE_WRITE_EXTRA'] = False

# The dashboard suppresses upload to APFE for GS directories (based on autotest
# tag) that contain 'tradefed-run-collect-tests'. b/119640440
# Do not change the name/tag without adjusting the dashboard.
_COLLECT = 'tradefed-run-collect-tests-only-internal'
_PUBLIC_COLLECT = 'tradefed-run-collect-tests-only'

# Unlike regular CTS we have to target the primary ABI only.
CONFIG['LAB_DEPENDENCY'] = {
    'x86': ['cts_cpu_x86'],
    'arm': ['cts_cpu_arm']
}

CONFIG['CTS_JOB_RETRIES_IN_PUBLIC'] = 1
CONFIG['CTS_QUAL_RETRIES'] = 9
CONFIG['CTS_MAX_RETRIES'] = {}

# TODO(ihf): Update timeouts once P is more stable.
# Timeout in hours.
CONFIG['CTS_TIMEOUT_DEFAULT'] = 1.0
CONFIG['CTS_TIMEOUT'] = {
    _ALL: 5.0,
    _COLLECT: 2.0,
    _PUBLIC_COLLECT: 2.0,
    'CtsFileSystemTestCases': 2.5,
}

# Any test that runs as part as blocking BVT needs to be stable and fast. For
# this reason we enforce a tight timeout on these modules/jobs.
# Timeout in hours. (0.1h = 6 minutes)
CONFIG['BVT_TIMEOUT'] = 0.1

CONFIG['QUAL_TIMEOUT'] = 5

# Split tests so that large and flaky tests are distributed evenly.
CONFIG['QUAL_BOOKMARKS'] = [
        'A',  # A bookend to simplify partition algorithm.
        # CtsAccessibility, CtsAutoFill
        'CtsBackgroundRestrictionsTestCases',
        # CtsMedia, CtsPrint
        'CtsSampleDeviceTestCases',
        # CtsView, CtsWidget
        'zzzzz'  # A bookend to simplify algorithm.
]

CONFIG['BVT_PERBUILD'] = [
]

CONFIG['NEEDS_POWER_CYCLE'] = [
]

# Modules that are known to download and/or push media file assets.
CONFIG['MEDIA_MODULES'] = []
CONFIG['NEEDS_PUSH_MEDIA'] = []

CONFIG['ENABLE_DEFAULT_APPS'] = []

# Run `eject` for (and only for) each device with RM=1 in lsblk output.
_EJECT_REMOVABLE_DISK_COMMAND = (
    "\'lsblk -do NAME,RM | sed -n s/1$//p | xargs -n1 eject\'")

# Mitigation attempt for b/281975410
_SLEEP_60_COMMAND = "\'sleep 60\'"

# Preconditions applicable to public and internal tests.
CONFIG['PRECONDITION'] = {
        'CtsViewTestCases': [_SLEEP_60_COMMAND],
}

CONFIG['LOGIN_PRECONDITION'] = {
    'CtsAppSecurityHostTestCases': [_EJECT_REMOVABLE_DISK_COMMAND],
    'CtsJobSchedulerTestCases': [_EJECT_REMOVABLE_DISK_COMMAND],
    'CtsOsTestCases': [_EJECT_REMOVABLE_DISK_COMMAND],
    'CtsProviderTestCases': [_EJECT_REMOVABLE_DISK_COMMAND],
    _ALL: [_EJECT_REMOVABLE_DISK_COMMAND],
}

# Preconditions applicable to public tests.
CONFIG['PUBLIC_PRECONDITION'] = {}

CONFIG['PUBLIC_DEPENDENCIES'] = {
    'CtsCameraTestCases': ['lighting'],
    'CtsMediaTestCases': ['noloopback'],
}

# This information is changed based on regular analysis of the failure rate on
# partner moblabs.
CONFIG['PUBLIC_MODULE_RETRY_COUNT'] = {
}

CONFIG['PUBLIC_OVERRIDE_TEST_PRIORITY'] = {
    _PUBLIC_COLLECT: 70,
}

# This information is changed based on regular analysis of the job run time on
# partner moblabs.

CONFIG['OVERRIDE_TEST_LENGTH'] = {
    'CtsDeqpTestCases': 4,  # LONG
    'CtsMediaTestCases': 4,
    'CtsMediaStressTestCases': 4,
    'CtsSecurityTestCases': 4,
    'CtsCameraTestCases': 4,
    _ALL: 4,
    # Even though collect tests doesn't run very long, it must be the very first
    # job executed inside of the suite. Hence it is the only 'LENGTHY' test.
    _COLLECT: 5,  # LENGTHY
}

CONFIG['DISABLE_LOGCAT_ON_FAILURE'] = set()
CONFIG['EXTRA_MODULES'] = {}
CONFIG['PUBLIC_EXTRA_MODULES'] = {}
CONFIG['EXTRA_SUBMODULE_OVERRIDE'] = {}

CONFIG['EXTRA_COMMANDLINE'] = {}

CONFIG['EXTRA_ATTRIBUTES'] = {
    'tradefed-run-collect-tests-only-internal': ['suite:arc-cts'],
}

CONFIG['EXTRA_ARTIFACTS'] = {}

CONFIG['PREREQUISITES'] = {}

if __name__ == '__main__':
    main(CONFIG)
