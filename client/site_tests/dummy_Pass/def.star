# Copyright 2020 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

load("//metadata/test_common.star", "test_common")

TESTS = test_common.define_client_test(
    test_name = "dummy_Pass",
    owner_emails = ["email_addr@chromium.org"],
    owner_groups = ["team-mdb-group"],
    suites = ["dummy", "dummyclientretries", "push_to_prod",
        "skylab_staging_test", "something_else"],
) + test_common.define_client_test(
    test_name = "dummy_Pass.bluetooth",
    owner_emails = ["email_addr@chromium.org"],
    suites = ["dummy", "push_to_prod", "skylab_staging_test"],
    common_deps = ["bluetooth"],
    #TODO: tag=bluetooth arg
)
