
# Copyright 2020 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# !!! GENERATED FILE. DO NOT EDIT !!!

load('//metadata/test_common.star', 'test_common')

def define_tests():
    return [
        test_common.define_test(
            'display/ClientChameleonConnection',
            suites = ['chameleon_dp', 'chameleon_dp_hdmi', 'chameleon_hdmi', 'chameleon_vga'],
        ),
        test_common.define_test(
            'display/DisplayContainEdid',
            suites = ['platform_internal_display'],
        ),
        test_common.define_test(
            'display/EdidStress.daily',
            suites = ['chameleon_hdmi_perbuild'],
        ),
        test_common.define_test(
            'display/InternalDisplayRotation',
            suites = ['platform_internal_display'],
        ),
        test_common.define_test(
            'display/ServerChameleonConnection',
            suites = ['chameleon_hdmi_unstable'],
        ),
        test_common.define_test(
            'display/SwitchMode',
            suites = ['chameleon_dp', 'chameleon_dp_hdmi', 'chameleon_hdmi', 'chameleon_hdmi_perbuild'],
        )
    ]
