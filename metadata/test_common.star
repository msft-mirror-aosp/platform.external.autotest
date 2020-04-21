# Copyright 2020 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

load("@proto//chromiumos/config/api/test/metadata/v1/metadata.proto",
    metadata_pb = "chromiumos.config.api.test.metadata.v1"
)

_TEST_NAME_PREFIX = "remoteTestDrivers/tauto/tests/"

def _define_client_test(
    test_name,
    owner_emails = [],
    owner_groups = [],
    suites = [],
    ):

    attrs = [metadata_pb.Attribute(name = "suite:" + s) for s in suites]

    contacts = ([metadata_pb.Contact(email = e) for e in owner_emails]
                + [metadata_pb.Contact(mdb_group = g) for g in owner_groups])

    info = metadata_pb.Informational(
        authors = contacts
        #TODO add doc, purpose, etc. here
    )

    return [metadata_pb.Test(
                name = _TEST_NAME_PREFIX + test_name,
                attributes = attrs,
                informational = info,
    )]


test_common = struct(
    define_client_test = _define_client_test,
)
