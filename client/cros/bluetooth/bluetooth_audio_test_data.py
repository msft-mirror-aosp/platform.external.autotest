# Copyright 2020 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""bluetooth audio test dat for a2dp, hfp nbs, and hfp wbs."""

import os


audio_test_dir = '/usr/local/autotest/cros/audio/test_data'
audio_record_dir = '/tmp'

A2DP = 'a2dp'
HFP_NBS = 'hfp_nbs'
HFP_WBS = 'hfp_wbs'


common_test_data = {
    'bit_width': 16,
    'format': 'S16_LE',
    'duration': 5,
}


# Audio test data for hfp narrow band speech
hfp_nbs_test_data = {
    'rate': 8000,
    'channels': 1,
    'frequencies': (3500,),
    'file': os.path.join(audio_test_dir, 'sine_3500hz_rate8000_ch1_5secs.wav'),
    'recorded_by_peer': os.path.join(audio_record_dir,
                                     'hfp_nbs_recorded_by_peer.wav'),
    'recorded_by_dut': os.path.join(audio_record_dir,
                                    'hfp_nbs_recorded_by_dut.raw'),
}
hfp_nbs_test_data.update(common_test_data)


# Audio test data for hfp wide band speech
hfp_wbs_test_data = {
    'rate': 16000,
    'channels': 1,

    'frequencies': (7000,),
    'file': os.path.join(audio_test_dir,
                         'sine_7000hz_rate16000_ch1_5secs.wav'),
    'recorded_by_peer': os.path.join(audio_record_dir,
                                     'hfp_wbs_recorded_by_peer.wav'),
    'recorded_by_dut': os.path.join(audio_record_dir,
                                    'hfp_wbs_recorded_by_dut.raw'),
}
hfp_wbs_test_data.update(common_test_data)


# Audio test data for a2dp
a2dp_test_data = {
    'rate': 48000,
    'channels': 2,
    'frequencies': (440, 20000),
    'file': os.path.join(audio_test_dir,
                         'binaural_sine_440hz_20000hz_rate48000_5secs.wav'),
    'recorded_by_peer': os.path.join(audio_record_dir,
                                     'a2dp_recorded_by_peer.wav'),
}
a2dp_test_data.update(common_test_data)


audio_test_data = {
    A2DP: a2dp_test_data,
    HFP_WBS: hfp_wbs_test_data,
    HFP_NBS: hfp_nbs_test_data,
}
