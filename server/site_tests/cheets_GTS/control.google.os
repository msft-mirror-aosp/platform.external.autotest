# Copyright 2016 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

AUTHOR = "ARC++ Team"
NAME = "cheets_GTS.google.os"
TIME = "LENGTHY"
TEST_TYPE = "server"
ATTRIBUTES = "suite:gts"
DEPENDENCIES = "arc"
JOB_RETRIES = 2

DOC = """Run the google.os package for ARC++."""

def run_GTS(machine):
    host = hosts.create_host(machine)
    job.run_test("cheets_GTS", host=host, iterations=1,
                 tag="google.os", target_package="google.os")

parallel_simple(run_GTS, machines)
