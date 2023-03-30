# Copyright 2019 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from autotest_lib.server import utils

AUTHOR = "kmshelton, waihong"
NAME = "firmware_FAFTRPC.ec"
METADATA = {
        "contacts": ["chromeos-faft@google.com", "kmshelton@chromium.org", "waihong@chromium.org"],
        "bug_component": "b:792402", # ChromeOS > Platform > Enablement > Firmware > FAFT
        "criteria": "Verify that the RPC system, and all EC RPCs, work as expected"
}
ATTRIBUTES = "suite:faft_smoke"
DEPENDENCIES = "servo_state:WORKING"
TIME = "SHORT"
TEST_TYPE = "server"

DOC = """
This test checks that all RPC functions on the EC subsystem are connected,
and that they roughly work as expected.

"""

args_dict = utils.args_to_dict(args)
servo_args = hosts.CrosHost.get_servo_arguments(args_dict)

def run_faftrpc(machine):
    host = hosts.create_host(machine, servo_args=servo_args)
    job.run_test("firmware_FAFTRPC",
                 host=host,
                 cmdline_args=args,
                 disable_sysinfo=True,
                 category_under_test="ec",
                 reboot_after_completion=True,
                 tag='ec',
                 )

parallel_simple(run_faftrpc, machines)
