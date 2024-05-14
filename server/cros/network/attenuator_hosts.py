# Lint as: python2, python3
# Copyright 2019 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

""" Attenuator hostnames with fixed loss overhead on a given antenna line. """

# This map represents the fixed loss overhead on a given antenna line.
# The map maps from:
#     attenuator hostname -> attenuator number -> frequency -> loss in dB.
# Note: This is the single source of truth for wificell attenuator DB.
#       Sync changes here to:
#       tast-tests/cros/remote/wificell/attenuator/attenuator_hosts.go
# yapf: disable
HOST_FIXED_ATTENUATIONS = {
        'fake-atten-host': {
                0: {2437: 0, 5220: 0, 5765: 0},
                1: {2437: 0, 5220: 0, 5765: 0},
                2: {2437: 0, 5220: 0, 5765: 0},
                3: {2437: 0, 5220: 0, 5765: 0}},
        # localhost is the default attenuator configuration used when running
        # attenuator tests remotely and does not correspond to a single host.
        'localhost' : {
                0: {2437: 55, 5220: 60, 5765: 58},
                1: {2437: 59, 5220: 58, 5765: 61},
                2: {2437: 56, 5220: 60, 5765: 57},
                3: {2437: 59, 5220: 58, 5765: 60},
                4: {2450: 37},
                5: {2450: 37},
                6: {2450: 37},
                7: {2450: 37}},
        'chromeos1-dev-host4-attenuator': {
                0: {2437: 53, 5220: 59, 5765: 59},
                1: {2437: 56, 5220: 56, 5765: 56},
                2: {2437: 53, 5220: 59, 5765: 59},
                3: {2437: 57, 5220: 56, 5765: 56}},
        'chromeos1-dev-host15-attenuator': {
                0: {2437: 32, 5220: 36, 5765: 38},
                1: {2437: 35, 5220: 34, 5765: 36},
                2: {2437: 32, 5220: 36, 5765: 38},
                3: {2437: 35, 5220: 34, 5765: 36}},
        'chromeos1-dev-host16-attenuator': {
                0: {2437: 32, 5220: 37, 5765: 39},
                1: {2437: 35, 5220: 34, 5765: 36},
                2: {2437: 32, 5220: 37, 5765: 39},
                3: {2437: 35, 5220: 34, 5765: 36}},
        'chromeos1-dev-host17-attenuator': {
                0: {2437: 33, 5220: 36, 5765: 38},
                1: {2437: 35, 5220: 34, 5765: 36},
                2: {2437: 33, 5220: 36, 5765: 38},
                3: {2437: 35, 5220: 34, 5765: 36}},
        'chromeos1-dev-host18-attenuator': {
                0: {2437: 32, 5220: 36, 5765: 37},
                1: {2437: 35, 5220: 34, 5765: 35},
                2: {2437: 32, 5220: 36, 5765: 37},
                3: {2437: 35, 5220: 34, 5765: 35}},
        'chromeos1-dev-host19-attenuator': {
                0: {2437: 52, 5220: 57, 5765: 60},
                1: {2437: 55, 5220: 54, 5765: 56},
                2: {2437: 52, 5220: 57, 5765: 60},
                3: {2437: 55, 5220: 54, 5765: 55}},
        'chromeos1-dev-host20-attenuator': {
                0: {2437: 53, 5220: 57, 5765: 62},
                1: {2437: 57, 5220: 55, 5765: 55},
                2: {2437: 53, 5220: 57, 5765: 61},
                3: {2437: 57, 5220: 55, 5765: 55}},
        'chromeos1-test-host2-attenuator': {
                0: {2437: 53, 5220: 59, 5765: 58},
                1: {2437: 57, 5220: 57, 5765: 59},
                2: {2437: 53, 5220: 59, 5765: 58},
                3: {2437: 57, 5220: 57, 5765: 59}},
        # Row 3 rack 7 is conductive grover setups
        'chromeos15-row3-rack7-host1-attenuator': {
                0: {2437: 53, 5220: 59, 5765: 59},
                1: {2437: 56, 5220: 56, 5765: 58},
                2: {2437: 53, 5220: 58, 5765: 60},
                3: {2437: 56, 5220: 56, 5765: 57}},
        'chromeos15-row3-rack7-host2-attenuator': {
                0: {2437: 53, 5220: 59, 5765: 59},
                1: {2437: 56, 5220: 57, 5765: 58},
                2: {2437: 53, 5220: 58, 5765: 60},
                3: {2437: 56, 5220: 57, 5765: 56}},
        'chromeos15-row3-rack7-host3-attenuator': {
                0: {2437: 53, 5220: 58, 5765: 60},
                1: {2437: 56, 5220: 56, 5765: 56},
                2: {2437: 53, 5220: 58, 5765: 60},
                3: {2437: 56, 5220: 56, 5765: 56}},
        'chromeos15-row3-rack7-host4-attenuator': {
                0: {2437: 53, 5220: 59, 5765: 60},
                1: {2437: 57, 5220: 56, 5765: 58},
                2: {2437: 53, 5220: 59, 5765: 60},
                3: {2437: 57, 5220: 56, 5765: 58}},
        'chromeos15-row3-rack7-host5-attenuator': {
                0: {2437: 53, 5220: 58, 5765: 60},
                1: {2437: 55, 5220: 55, 5765: 54},
                2: {2437: 52, 5220: 57, 5765: 60},
                3: {2437: 55, 5220: 56, 5765: 54}},
        'chromeos15-row3-rack7-host6-attenuator': {
                0: {2437: 53, 5220: 58, 5765: 59},
                1: {2437: 56, 5220: 57, 5765: 57},
                2: {2437: 52, 5220: 58, 5765: 58},
                3: {2437: 56, 5220: 56, 5765: 56}},
        # Row 3 rack 8 is conductive grover setups
        'chromeos15-row3-rack8-host1-attenuator': {
                0: {2437: 53, 5220: 59, 5765: 58},
                1: {2437: 56, 5220: 57, 5765: 59},
                2: {2437: 52, 5220: 59, 5765: 58},
                3: {2437: 56, 5220: 57, 5765: 59}},
        'chromeos15-row3-rack8-host2-attenuator': {
                0: {2437: 52, 5220: 59, 5765: 59},
                1: {2437: 56, 5220: 56, 5765: 60},
                2: {2437: 52, 5220: 58, 5765: 60},
                3: {2437: 56, 5220: 56, 5765: 59}},
        'chromeos15-row3-rack8-host3-attenuator': {
                0: {2437: 52, 5220: 58, 5765: 59},
                1: {2437: 56, 5220: 56, 5765: 60},
                2: {2437: 52, 5220: 58, 5765: 59},
                3: {2437: 56, 5220: 56, 5765: 57}},
        'chromeos15-row3-rack8-host4-attenuator': {
                0: {2437: 52, 5220: 58, 5765: 60},
                1: {2437: 56, 5220: 56, 5765: 58},
                2: {2437: 52, 5220: 58, 5765: 58},
                3: {2437: 56, 5220: 56, 5765: 56}},
        'chromeos15-row3-rack8-host5-attenuator': {
                0: {2437: 53, 5220: 58, 5765: 58},
                1: {2437: 56, 5220: 56, 5765: 57},
                2: {2437: 53, 5220: 59, 5765: 58},
                3: {2437: 56, 5220: 56, 5765: 60}},
        'chromeos15-row3-rack8-host6-attenuator': {
                0: {2437: 53, 5220: 59, 5765: 59},
                1: {2437: 56, 5220: 56, 5765: 57},
                2: {2437: 53, 5220: 60, 5765: 59},
                3: {2437: 56, 5220: 58, 5765: 58}},
        # Row 3 racks 9 to 14 are conductive grover setups
        'chromeos15-row3-rack9-host1-attenuator': {
                0: {2437: 53, 5220: 60, 5765: 59},
                1: {2437: 57, 5220: 57, 5765: 58},
                2: {2437: 53, 5220: 59, 5765: 60},
                3: {2437: 57, 5220: 57, 5765: 60}},
        'chromeos15-row3-rack9-host2-attenuator': {
                0: {2437: 53, 5220: 59, 5765: 59},
                1: {2437: 57, 5220: 58, 5765: 60},
                2: {2437: 53, 5220: 58, 5765: 58},
                3: {2437: 57, 5220: 58, 5765: 61}},
        'chromeos15-row3-rack9-host3-attenuator': {
                0: {2437: 53, 5220: 59, 5765: 59},
                1: {2437: 57, 5220: 58, 5765: 59},
                2: {2437: 53, 5220: 58, 5765: 59},
                3: {2437: 57, 5220: 58, 5765: 60}},
        'chromeos15-row3-rack9-host4-attenuator': {
                0: {2437: 53, 5220: 59, 5765: 59},
                1: {2437: 57, 5220: 58, 5765: 60},
                2: {2437: 53, 5220: 58, 5765: 59},
                3: {2437: 57, 5220: 57, 5765: 60}},
        'chromeos15-row3-rack9-host5-attenuator': {
                0: {2437: 53, 5220: 59, 5765: 59},
                1: {2437: 57, 5220: 58, 5765: 59},
                2: {2437: 53, 5220: 58, 5765: 60},
                3: {2437: 57, 5220: 58, 5765: 60}},
        'chromeos15-row3-rack9-host6-attenuator': {
                0: {2437: 53, 5220: 59, 5765: 59},
                1: {2437: 57, 5220: 57, 5765: 60},
                2: {2437: 53, 5220: 59, 5765: 60},
                3: {2437: 57, 5220: 58, 5765: 58}},
        'chromeos15-row3-rack10-host1-attenuator': {
                0: {2437: 52, 5220: 55, 5765: 56},
                1: {2437: 55, 5220: 53, 5765: 57},
                2: {2437: 52, 5220: 55, 5765: 57},
                3: {2437: 55, 5220: 53, 5765: 57}},
        'chromeos15-row3-rack10-host2-attenuator': {
                0: {2437: 52, 5220: 56, 5765: 58},
                1: {2437: 55, 5220: 54, 5765: 58},
                2: {2437: 52, 5220: 56, 5765: 58},
                3: {2437: 55, 5220: 54, 5765: 57}},
        'chromeos15-row3-rack10-host3-attenuator': {
                0: {2437: 53, 5220: 57, 5765: 57},
                1: {2437: 56, 5220: 56, 5765: 57},
                2: {2437: 53, 5220: 57, 5765: 59},
                3: {2437: 56, 5220: 57, 5765: 58}},
        'chromeos15-row3-rack10-host4-attenuator': {
                0: {2437: 51, 5220: 55, 5765: 59},
                1: {2437: 55, 5220: 53, 5765: 58},
                2: {2437: 51, 5220: 54, 5765: 59},
                3: {2437: 55, 5220: 53, 5765: 58}},
        'chromeos15-row3-rack10-host5-attenuator': {
                0: {2437: 51, 5220: 55, 5765: 60},
                1: {2437: 55, 5220: 53, 5765: 58},
                2: {2437: 51, 5220: 55, 5765: 60},
                3: {2437: 55, 5220: 53, 5765: 58}},
        'chromeos15-row3-rack10-host6-attenuator': {
                0: {2437: 52, 5220: 55, 5765: 57},
                1: {2437: 55, 5220: 54, 5765: 59},
                2: {2437: 52, 5220: 55, 5765: 57},
                3: {2437: 55, 5220: 54, 5765: 57}},
        'chromeos15-row3-rack11-host1-attenuator': {
                0: {2437: 53, 5220: 58, 5765: 57},
                1: {2437: 56, 5220: 56, 5765: 58},
                2: {2437: 53, 5220: 58, 5765: 57},
                3: {2437: 56, 5220: 56, 5765: 57}},
        'chromeos15-row3-rack11-host2-attenuator': {
                0: {2437: 53, 5220: 58, 5765: 56},
                1: {2437: 56, 5220: 56, 5765: 58},
                2: {2437: 53, 5220: 59, 5765: 56},
                3: {2437: 56, 5220: 56, 5765: 56}},
        'chromeos15-row3-rack11-host3-attenuator': {
                0: {2437: 52, 5220: 57, 5765: 59},
                1: {2437: 55, 5220: 55, 5765: 54},
                2: {2437: 52, 5220: 57, 5765: 59},
                3: {2437: 55, 5220: 55, 5765: 54}},
        'chromeos15-row3-rack11-host4-attenuator': {
                0: {2437: 52, 5220: 58, 5765: 59},
                1: {2437: 56, 5220: 56, 5765: 55},
                2: {2437: 52, 5220: 57, 5765: 59},
                3: {2437: 56, 5220: 56, 5765: 55}},
        'chromeos15-row3-rack11-host5-attenuator': {
                0: {2437: 53, 5220: 58, 5765: 58},
                1: {2437: 55, 5220: 56, 5765: 55},
                2: {2437: 53, 5220: 58, 5765: 59},
                3: {2437: 56, 5220: 55, 5765: 55}},
        'chromeos15-row3-rack11-host6-attenuator': {
                0: {2437: 52, 5220: 58, 5765: 59},
                1: {2437: 55, 5220: 55, 5765: 54},
                2: {2437: 52, 5220: 57, 5765: 59},
                3: {2437: 55, 5220: 55, 5765: 54}},
        'chromeos15-row3-rack12-host1-attenuator': {
                0: {2437: 53, 5220: 59, 5765: 58},
                1: {2437: 55, 5220: 57, 5765: 55},
                2: {2437: 57, 5220: 59, 5765: 58},
                3: {2437: 55, 5220: 56, 5765: 55}},
        'chromeos15-row3-rack12-host2-attenuator': {
                0: {2437: 52, 5220: 59, 5765: 56},
                1: {2437: 55, 5220: 56, 5765: 55},
                2: {2437: 52, 5220: 59, 5765: 57},
                3: {2437: 55, 5220: 56, 5765: 55}},
        'chromeos15-row3-rack12-host3-attenuator': {
                0: {2437: 52, 5220: 58, 5765: 57},
                1: {2437: 55, 5220: 57, 5765: 55},
                2: {2437: 52, 5220: 59, 5765: 59},
                3: {2437: 55, 5220: 59, 5765: 55}},
        'chromeos15-row3-rack12-host4-attenuator': {
                0: {2437: 52, 5220: 58, 5765: 56},
                1: {2437: 55, 5220: 56, 5765: 55},
                2: {2437: 52, 5220: 58, 5765: 56},
                3: {2437: 55, 5220: 56, 5765: 56}},
        'chromeos15-row3-rack12-host5-attenuator': {
                0: {2437: 53, 5220: 59, 5765: 58},
                1: {2437: 55, 5220: 56, 5765: 55},
                2: {2437: 52, 5220: 59, 5765: 59},
                3: {2437: 55, 5220: 56, 5765: 55}},
        'chromeos15-row3-rack12-host6-attenuator': {
                0: {2437: 52, 5220: 59, 5765: 57},
                1: {2437: 55, 5220: 56, 5765: 55},
                2: {2437: 52, 5220: 58, 5765: 56},
                3: {2437: 55, 5220: 56, 5765: 55}},
        'chromeos15-row3-rack13-host1-attenuator': {
                0: {2437: 59, 5220: 59, 5765: 59},
                1: {2437: 52, 5220: 54, 5765: 54},
                2: {2437: 59, 5220: 59, 5765: 59},
                3: {2437: 52, 5220: 54, 5765: 54}},
        'chromeos15-row3-rack13-host2-attenuator': {
                0: {2437: 64, 5220: 62, 5765: 62},
                1: {2437: 58, 5220: 57, 5765: 57},
                2: {2437: 64, 5220: 62, 5765: 62},
                3: {2437: 58, 5220: 57, 5765: 57}},
        'chromeos15-row3-rack13-host3-attenuator': {
                0: {2437: 60, 5220: 58, 5765: 58},
                1: {2437: 52, 5220: 57, 5765: 57},
                2: {2437: 60, 5220: 58, 5765: 58},
                3: {2437: 52, 5220: 57, 5765: 57}},
        'chromeos15-row3-rack13-host4-attenuator': {
                0: {2437: 52, 5220: 58, 5765: 58},
                1: {2437: 59, 5220: 60, 5765: 60},
                2: {2437: 52, 5220: 58, 5765: 58},
                3: {2437: 59, 5220: 60, 5765: 60}},
        'chromeos15-row3-rack13-host5-attenuator': {
                0: {2437: 58, 5220: 60, 5765: 60},
                1: {2437: 53, 5220: 58, 5765: 58},
                2: {2437: 58, 5220: 60, 5765: 60},
                3: {2437: 53, 5220: 58, 5765: 58}},
        'chromeos15-row3-rack13-host6-attenuator': {
                0: {2437: 52, 5220: 56, 5765: 58},
                1: {2437: 53, 5220: 56, 5765: 57},
                2: {2437: 52, 5220: 56, 5765: 58},
                3: {2437: 53, 5220: 56, 5765: 57}},
        'chromeos15-row3-rack14-host1-attenuator': {
                0: {2437: 53, 5220: 56, 5765: 56},
                1: {2437: 52, 5220: 56, 5765: 56},
                2: {2437: 53, 5220: 56, 5765: 56},
                3: {2437: 52, 5220: 56, 5765: 56}},
        'chromeos15-row3-rack14-host2-attenuator': {
                0: {2437: 59, 5220: 59, 5765: 59},
                1: {2437: 59, 5220: 60, 5765: 60},
                2: {2437: 59, 5220: 59, 5765: 59},
                3: {2437: 59, 5220: 60, 5765: 60}},
        'chromeos15-row3-rack14-host3-attenuator': {
                0: {2437: 52, 5220: 56, 5765: 56},
                1: {2437: 64, 5220: 63, 5765: 63},
                2: {2437: 52, 5220: 56, 5765: 56},
                3: {2437: 64, 5220: 63, 5765: 63}},
        'chromeos15-row3-rack14-host4-attenuator': {
                0: {2437: 52, 5220: 55, 5765: 55},
                1: {2437: 58, 5220: 58, 5765: 58},
                2: {2437: 52, 5220: 55, 5765: 55},
                3: {2437: 58, 5220: 58, 5765: 58}},
        'chromeos15-row3-rack14-host5-attenuator': {
                0: {2437: 57, 5220: 58, 5765: 58},
                1: {2437: 52, 5220: 55, 5765: 55},
                2: {2437: 57, 5220: 58, 5765: 58},
                3: {2437: 52, 5220: 55, 5765: 55}},
        'chromeos15-row3-rack14-host6-attenuator': {
                0: {2437: 57, 5220: 57, 5765: 57},
                1: {2437: 52, 5220: 55, 5765: 55},
                2: {2437: 57, 5220: 57, 5765: 57},
                3: {2437: 52, 5220: 55, 5765: 55}},
        'chromeos15-row10-rack1-host1-attenuator': {
                0: {2437: 55, 5220: 60, 5765: 58},
                1: {2437: 59, 5220: 58, 5765: 61},
                2: {2437: 56, 5220: 60, 5765: 57},
                3: {2437: 59, 5220: 58, 5765: 60},
                4: {2450: 37},
                5: {2450: 37},
                6: {2450: 37},
                7: {2450: 37}},
        'chromeos15-row10-rack1-host2-attenuator': {
                0: {2437: 57, 5220: 61, 5765: 59},
                1: {2437: 60, 5220: 59, 5765: 57},
                2: {2437: 57, 5220: 61, 5765: 59},
                3: {2437: 60, 5220: 60, 5765: 58},
                4: {2450: 39},
                5: {2450: 38},
                6: {2450: 39},
                7: {2450: 39}},
        'chromeos15-row10-rack1-host3-attenuator': {
                0: {2437: 56, 5220: 59, 5765: 58},
                1: {2437: 59, 5220: 59, 5765: 59},
                2: {2437: 56, 5220: 59, 5765: 58},
                3: {2437: 59, 5220: 58, 5765: 60},
                4: {2450: 38},
                5: {2450: 38},
                6: {2450: 38},
                7: {2450: 39}},
        'chromeos15-row10-rack1-host4-attenuator': {
                0: {2437: 56, 5220: 60, 5765: 58},
                1: {2437: 59, 5220: 58, 5765: 60},
                2: {2437: 56, 5220: 59, 5765: 58},
                3: {2437: 59, 5220: 58, 5765: 60},
                4: {2450: 38},
                5: {2450: 38},
                6: {2450: 38},
                7: {2450: 38}},
        'chromeos15-row10-rack1-host5-attenuator': {
                0: {2437: 56, 5220: 60, 5765: 59},
                1: {2437: 59, 5220: 60, 5765: 59},
                2: {2437: 56, 5220: 60, 5765: 59},
                3: {2437: 59, 5220: 59, 5765: 58},
                4: {2450: 36},
                5: {2450: 36},
                6: {2450: 36},
                7: {2450: 36}},
        'chromeos15-row10-rack2-host1-attenuator': {
                0: {2437: 57, 5220: 61, 5765: 59},
                1: {2437: 60, 5220: 58, 5765: 57},
                2: {2437: 57, 5220: 61, 5765: 59},
                3: {2437: 60, 5220: 58, 5765: 58},
                4: {2450: 37},
                5: {2450: 36},
                6: {2450: 37},
                7: {2450: 37}},
        'chromeos15-row10-rack2-host2-attenuator': {
                0: {2437: 57, 5220: 60, 5765: 59},
                1: {2437: 60, 5220: 59, 5765: 57},
                2: {2437: 57, 5220: 60, 5765: 59},
                3: {2437: 59, 5220: 59, 5765: 57},
                4: {2450: 36},
                5: {2450: 36},
                6: {2450: 37},
                7: {2450: 37}},
        'chromeos15-row10-rack2-host3-attenuator': {
                0: {2437: 59, 5220: 60, 5765: 59},
                1: {2437: 59, 5220: 58, 5765: 60},
                2: {2437: 56, 5220: 60, 5765: 60},
                3: {2437: 59, 5220: 59, 5765: 60},
                4: {2450: 36},
                5: {2450: 36},
                6: {2450: 37},
                7: {2450: 37}},
        'chromeos15-row10-rack2-host4-attenuator': {
                0: {2437: 55, 5220: 60, 5765: 60},
                1: {2437: 58, 5220: 58, 5765: 59},
                2: {2437: 55, 5220: 60, 5765: 60},
                3: {2437: 58, 5220: 57, 5765: 60},
                4: {2450: 36},
                5: {2450: 36},
                6: {2450: 36},
                7: {2450: 36}},
        'chromeos15-row10-rack2-host5-attenuator': {
                0: {2437: 55, 5220: 60, 5765: 60},
                1: {2437: 58, 5220: 58, 5765: 60},
                2: {2437: 55, 5220: 60, 5765: 60},
                3: {2437: 58, 5220: 58, 5765: 59},
                4: {2450: 36},
                5: {2450: 36},
                6: {2450: 36},
                7: {2450: 36}},
        'chromeos15-row10-rack3-host1-attenuator': {
                0: {2437: 56, 5220: 61, 5765: 58},
                1: {2437: 59, 5220: 58, 5765: 57},
                2: {2437: 56, 5220: 61, 5765: 60},
                3: {2437: 59, 5220: 59, 5765: 57},
                4: {2450: 37},
                5: {2450: 37},
                6: {2450: 37},
                7: {2450: 37}},
        'chromeos15-row10-rack3-host2-attenuator': {
                0: {2437: 55, 5220: 60, 5765: 61},
                1: {2437: 59, 5220: 58, 5765: 59},
                2: {2437: 56, 5220: 56, 5765: 60},
                3: {2437: 59, 5220: 59, 5765: 59},
                4: {2450: 37},
                5: {2450: 36},
                6: {2450: 37},
                7: {2450: 36}},
        'chromeos15-row10-rack3-host3-attenuator': {
                0: {2437: 55, 5220: 60, 5765: 61},
                1: {2437: 58, 5220: 59, 5765: 58},
                2: {2437: 57, 5220: 61, 5765: 61},
                3: {2437: 58, 5220: 60, 5765: 59},
                4: {2450: 37},
                5: {2450: 36},
                6: {2450: 36},
                7: {2450: 36}},
        'chromeos15-row10-rack3-host4-attenuator': {
                0: {2437: 56, 5220: 60, 5765: 61},
                1: {2437: 60, 5220: 60, 5765: 57},
                2: {2437: 55, 5220: 60, 5765: 61},
                3: {2437: 59, 5220: 61, 5765: 58},
                4: {2450: 36},
                5: {2450: 36},
                6: {2450: 36},
                7: {2450: 37}},
        'chromeos15-row10-rack3-host5-attenuator': {
                0: {2437: 57, 5220: 61, 5765: 60},
                1: {2437: 59, 5220: 59, 5765: 57},
                2: {2437: 56, 5220: 61, 5765: 59},
                3: {2437: 59, 5220: 58, 5765: 57},
                4: {2450: 36},
                5: {2450: 36},
                6: {2450: 36},
                7: {2450: 36}},
         'chromeos15-row10-rack4-host1-attenuator': {
                0: {2437: 56, 5220: 59, 5765: 59},
                1: {2437: 60, 5220: 58, 5765: 59},
                2: {2437: 60, 5220: 60, 5765: 59},
                3: {2437: 59, 5220: 58, 5765: 60},
                4: {2450: 38},
                5: {2450: 37},
                6: {2450: 38},
                7: {2450: 38}},
         'chromeos15-row10-rack4-host2-attenuator': {
                0: {2437: 56, 5220: 60, 5765: 58},
                1: {2437: 59, 5220: 57, 5765: 60},
                2: {2437: 56, 5220: 60, 5765: 59},
                3: {2437: 59, 5220: 58, 5765: 61},
                4: {2450: 37},
                5: {2450: 37},
                6: {2450: 37},
                7: {2450: 37}},
         'chromeos15-row10-rack4-host3-attenuator': {
                0: {2437: 55, 5220: 60, 5765: 57},
                1: {2437: 58, 5220: 57, 5765: 61},
                2: {2437: 55, 5220: 60, 5765: 57},
                3: {2437: 58, 5220: 58, 5765: 60},
                4: {2450: 38},
                5: {2450: 36},
                6: {2450: 36},
                7: {2450: 39}},
         'chromeos15-row10-rack4-host4-attenuator': {
                0: {2437: 55, 5220: 59, 5765: 57},
                1: {2437: 58, 5220: 57, 5765: 60},
                2: {2437: 56, 5220: 60, 5765: 58},
                3: {2437: 58, 5220: 57, 5765: 60},
                4: {2450: 37},
                5: {2450: 37},
                6: {2450: 37},
                7: {2450: 37}},
         'chromeos15-row10-rack4-host5-attenuator': {
                0: {2437: 55, 5220: 59, 5765: 58},
                1: {2437: 59, 5220: 58, 5765: 60},
                2: {2437: 55, 5220: 60, 5765: 61},
                3: {2437: 59, 5220: 58, 5765: 60},
                4: {2450: 37},
                5: {2450: 37},
                6: {2450: 36},
                7: {2450: 37}},
        'chromeos15-row10-rack5-host1-attenuator': {
                0: {2437: 55, 5220: 60, 5765: 58},
                1: {2437: 60, 5220: 58, 5765: 57},
                2: {2437: 55, 5220: 60, 5765: 59},
                3: {2437: 59, 5220: 58, 5765: 57},
                4: {2450: 37},
                5: {2450: 36},
                6: {2450: 36},
                7: {2450: 36}},
        'chromeos15-row10-rack5-host2-attenuator': {
                0: {2437: 56, 5220: 60, 5765: 58},
                1: {2437: 59, 5220: 58, 5765: 57},
                2: {2437: 55, 5220: 59, 5765: 61},
                3: {2437: 59, 5220: 58, 5765: 58},
                4: {2450: 36},
                5: {2450: 36},
                6: {2450: 36},
                7: {2450: 36}},
        'chromeos15-row10-rack5-host3-attenuator': {
                0: {2437: 55, 5220: 59, 5765: 61},
                1: {2437: 58, 5220: 57, 5765: 57},
                2: {2437: 56, 5220: 60, 5765: 61},
                3: {2437: 59, 5220: 58, 5765: 58},
                4: {2450: 37},
                5: {2450: 35},
                6: {2450: 36},
                7: {2450: 36}},
        'chromeos15-row10-rack5-host4-attenuator': {
                0: {2437: 60, 5220: 59, 5765: 59},
                1: {2437: 55, 5220: 60, 5765: 60},
                2: {2437: 60, 5220: 59, 5765: 58},
                3: {2437: 55, 5220: 60, 5765: 60},
                4: {2450: 38},
                5: {2450: 38},
                6: {2450: 38},
                7: {2450: 37}},
        'chromeos15-row10-rack5-host5-attenuator': {
                0: {2437: 55, 5220: 59, 5765: 59},
                1: {2437: 58, 5220: 57, 5765: 58},
                2: {2437: 55, 5220: 60, 5765: 61},
                3: {2437: 58, 5220: 58, 5765: 58},
                4: {2450: 36},
                5: {2450: 36},
                6: {2450: 36},
                7: {2450: 36}},
}
