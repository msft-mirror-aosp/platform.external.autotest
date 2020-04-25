# Copyright 2020 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

load("//metadata/test_common.star", "test_common")

DOC = """
Verify effects of policy_AllowDinosaurEasterEgg policy.
True: enable the Dino game inside the Chrome browser.
False: disable the dino game within the Chrome browser.
Not set: disable the dino game within the Chrome browser.
"""

def _allow_dino_test(name, case):
    return test_common.define_client_test(
        test_name = "policy_AllowDinosaurEasterEgg." + name,
        purpose = "AllowDinosaurEasterEgg: verify %s case" % case,
        doc = DOC,
        owner_emails = ["dbeckett@chromium.org"],
        suites = ["ent-nightly", "policy"],
        named_args = {"case": case}
    )

TESTS = [
    _allow_dino_test('true', True),
    _allow_dino_test('false', False),
    _allow_dino_test('not_set', None),
]
