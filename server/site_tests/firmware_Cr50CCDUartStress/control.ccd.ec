# Copyright 2022 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from autotest_lib.server import utils

AUTHOR = "Cr50 FW team"
NAME = "firmware_Cr50CCDUartStress.ccd.ec"
METADATA = {
    "contacts": ["chromeos-faft@google.com", "jbettis@chromium.org"],
    "bug_component": "b:792402",  # ChromeOS > Platform > Enablement > Firmware > FAFT
    "criteria": "Uart Stress Test in ccd mode",
}
ATTRIBUTES = "suite:faft_ccd"
TIME = "MEDIUM"
TEST_TYPE = "server"
DEPENDENCIES = "servo_state:WORKING"

DOC = """
This is a test for Uart-USB bridging qualification.
This test runs 'uart_stress_tester.py' and checks if there are any characters
lost.
"""

if "args_dict" not in locals():
    args_dict = {}

args_dict.update(utils.args_to_dict(args))
servo_args = hosts.CrosHost.get_servo_arguments(args_dict)


def run(machine):
    host = hosts.create_host(machine, servo_args=servo_args)
    duration = int(args_dict.get("uart_duration", "60"))
    job.run_test(
        "firmware_Cr50CCDUartStress",
        host=host,
        cmdline_args=args,
        duration=duration,
        use_ccd=True,
        console="ec",
        tag="ccd.ec",
    )


parallel_simple(run, machines)
