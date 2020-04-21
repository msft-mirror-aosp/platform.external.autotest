# Copyright 2020 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.


# TODO: eventually METADATA should be a RemoteTestDriver.
load("//client/site_tests/dummy_Pass/def.star", client_dummy_Pass = "TESTS")
METADATA = client_dummy_Pass[0]
