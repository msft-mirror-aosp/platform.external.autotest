# Copyright 2020 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# This test makes sure the firmware stored in the OS image is signed with MP
# keys, not pre-MP or dev.  It is intended to be run as part of the FSI process.

from autotest_lib.server import utils

NAME = "firmware_FingerprintSigner.fsi"
METADATA = {
    "contacts": ["chromeos-fingerprint@google.com"],
    "bug_component": "b:782045",
    "criteria": "Fails if the on-disk fingerprint firmware image is signed with keys that aren't MP.",
}

PURPOSE = """
Verify that the signer ID is correct
"""
TEST_TYPE = "server"
DEPENDENCIES = "fingerprint, servo_state:WORKING"
JOB_RETRIES = 0

args_dict = utils.args_to_dict(args)
servo_args = hosts.CrosHost.get_servo_arguments(args_dict)

def run(machine):
    host = hosts.create_host(machine, servo_args=servo_args)
    job.run_test("firmware_FingerprintSigner", host=host, fsi=True)

parallel_simple(run, machines)
