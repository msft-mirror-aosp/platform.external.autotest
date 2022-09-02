# Copyright 2022 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from autotest_lib.server import utils

AUTHOR = "Cr50 FW team"
NAME = "firmware_Cr50CCDUartStress.ccd.ec"
PURPOSE = "Uart Stress Test in ccd mode"
ATTRIBUTES = "suite:faft_gsc_nightly, suite:faft_ccd, suite:faft_cr50_prepvt, suite:faft_cr50_pvt, suite:faft_ti50_qual"
TIME = "MEDIUM"
TEST_TYPE = "server"
DEPENDENCIES = "servo_state:WORKING"
PY_VERSION = 3

DOC = """
This is a test for Uart-USB bridging qualification.
This test runs 'uart_stress_tester.py' and checks if there are any characters
lost.
"""

if 'args_dict' not in locals():
    args_dict = {}

args_dict.update(utils.args_to_dict(args))
servo_args = hosts.CrosHost.get_servo_arguments(args_dict)

def run(machine):
    host = hosts.create_host(machine, servo_args=servo_args)
    job.run_test('firmware_Cr50CCDUartStress', host=host, cmdline_args=args,
                 duration=600, use_ccd=True, console='ec')

parallel_simple(run, machines)
