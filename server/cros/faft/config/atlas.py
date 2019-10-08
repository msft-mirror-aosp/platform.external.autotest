# Copyright 2018 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""FAFT config setting overrides for Atlas."""

class Values(object):
    """FAFT config values for Atlas."""
    chrome_ec = True
    ec_capability = ['battery', 'charging',
                     'keyboard', 'lid', 'x86' ]
    firmware_screen = 15
    spi_voltage = 'pp3300'
    servo_prog_state_delay = 10
    dark_resume_capable = True
    cr50_capability = ['rdd_leakage', 'wp_on_in_g3']
