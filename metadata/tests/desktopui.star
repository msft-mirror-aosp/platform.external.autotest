
# Copyright 2020 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# !!! GENERATED FILE. DO NOT EDIT !!!

load('//metadata/test_common.star', 'test_common')

def define_tests():
    return [
        test_common.define_test(
            'desktopui/CheckRlzPingSent',
            suites = [],
        ),
        test_common.define_test(
            'desktopui/ChromeSanity',
            suites = ['bvt-perbuild'],
        ),
        test_common.define_test(
            'desktopui/ConnectivityDiagnostics',
            suites = [],
        ),
        test_common.define_test(
            'desktopui/FontCache',
            suites = [],
        ),
        test_common.define_test(
            'desktopui/GmailLatency',
            suites = [],
        ),
        test_common.define_test(
            'desktopui/HangDetector',
            suites = ['regression'],
        ),
        test_common.define_test(
            'desktopui/MediaAudioFeedback',
            suites = ['bvt-perbuild'],
        ),
        test_common.define_test(
            'desktopui/ScreenLocker',
            suites = ['bvt-perbuild'],
        ),
        test_common.define_test(
            'desktopui/SetFieldsWithChromeDriver',
            suites = [],
        ),
        test_common.define_test(
            'desktopui/SimpleLogin',
            suites = [],
        ),
        test_common.define_test(
            'desktopui/SpeechSynthesisSemiAuto',
            suites = [],
        ),
        test_common.define_test(
            'desktopui/UrlFetchWithChromeDriver',
            suites = [],
        )
    ]
