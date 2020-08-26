
# Copyright 2020 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# !!! GENERATED FILE. DO NOT EDIT !!!

load('//metadata/test_common.star', 'test_common')

def define_tests():
    return [
        test_common.define_test(
            'cellular/ConnectFailure',
            suites = [],
        ),
        test_common.define_test(
            'cellular/DisableWhileConnecting',
            suites = ['cellular_qual'],
        ),
        test_common.define_test(
            'cellular/Identifiers',
            suites = ['cellular_qual'],
        ),
        test_common.define_test(
            'cellular/ModemControl',
            suites = ['cellular_qual'],
        ),
        test_common.define_test(
            'cellular/SafetyDance',
            suites = ['cellular_qual'],
        ),
        test_common.define_test(
            'cellular/Smoke',
            suites = ['cellular_qual'],
        ),
        test_common.define_test(
            'cellular/StaleModemReboot',
            suites = ['cellular_modem_repair'],
        ),
        test_common.define_test(
            'cellular/StressEnable',
            suites = ['cellular_qual'],
        ),
        test_common.define_test(
            'cellular/SuspendResume',
            suites = ['cellular_qual'],
        )
    ]
