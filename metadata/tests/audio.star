
# Copyright 2020 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# !!! GENERATED FILE. DO NOT EDIT !!!

load('//metadata/test_common.star', 'test_common')

def define_tests():
    return [
        test_common.define_test(
            'audio/Aconnect',
            suites = ['audio'],
        ),
        test_common.define_test(
            'audio/ActiveStreamStress',
            suites = [],
        ),
        test_common.define_test(
            'audio/Aplay',
            suites = ['kernel_per-build_regression'],
        ),
        test_common.define_test(
            'audio/AudioBasicAssistant',
            suites = [],
        ),
        test_common.define_test(
            'audio/AudioBasicBluetoothPlayback',
            suites = [],
        ),
        test_common.define_test(
            'audio/AudioBasicBluetoothPlaybackRecord',
            suites = [],
        ),
        test_common.define_test(
            'audio/AudioBasicBluetoothRecord',
            suites = [],
        ),
        test_common.define_test(
            'audio/AudioBasicExternalMicrophone',
            suites = ['audio_essential'],
        ),
        test_common.define_test(
            'audio/AudioBasicHDMI',
            suites = ['audio_basic'],
        ),
        test_common.define_test(
            'audio/AudioBasicHeadphone',
            suites = ['audio_essential'],
        ),
        test_common.define_test(
            'audio/AudioBasicHotwording',
            suites = ['audio_basic'],
        ),
        test_common.define_test(
            'audio/AudioBasicInternalMicrophone',
            suites = ['audio_essential'],
        ),
        test_common.define_test(
            'audio/AudioBasicInternalSpeaker',
            suites = ['audio_essential'],
        ),
        test_common.define_test(
            'audio/AudioBasicUSBPlayback',
            suites = ['audio_basic'],
        ),
        test_common.define_test(
            'audio/AudioBasicUSBPlaybackRecord',
            suites = ['audio_basic'],
        ),
        test_common.define_test(
            'audio/AudioBasicUSBRecord',
            suites = ['audio_basic'],
        ),
        test_common.define_test(
            'audio/AudioBluetoothConnectionStability',
            suites = [],
        ),
        test_common.define_test(
            'audio/AudioCorruption',
            suites = ['bvt-perbuild'],
        ),
        test_common.define_test(
            'audio/AudioInputGain',
            suites = ['audio_essential'],
        ),
        test_common.define_test(
            'audio/AudioNodeSwitch',
            suites = [],
        ),
        test_common.define_test(
            'audio/AudioRoutingUSB',
            suites = [],
        ),
        test_common.define_test(
            'audio/AudioSanityCheck',
            suites = [],
        ),
        test_common.define_test(
            'audio/AudioWebRTCLoopback',
            suites = [],
        ),
        test_common.define_test(
            'audio/CRASFormatConversion',
            suites = ['audio'],
        ),
        test_common.define_test(
            'audio/CrasDevSwitchStress',
            suites = ['audio'],
        ),
        test_common.define_test(
            'audio/CrasGetNodes',
            suites = ['audio_essential'],
        ),
        test_common.define_test(
            'audio/CrasPinnedStream',
            suites = ['audio', 'partners'],
        ),
        test_common.define_test(
            'audio/CrasSanity',
            suites = ['bvt-perbuild'],
        ),
        test_common.define_test(
            'audio/CrasStress',
            suites = ['audio'],
        ),
        test_common.define_test(
            'audio/PlaybackPower',
            suites = [],
        ),
        test_common.define_test(
            'audio/SeekAudioFeedback',
            suites = ['audio'],
        ),
        test_common.define_test(
            'audio/WebRtcAudioLoopback',
            suites = ['hotrod'],
        ),
        test_common.define_test(
            'audio/YoutubePlayback',
            suites = ['audio'],
        )
    ]
