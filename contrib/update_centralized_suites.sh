#!/bin/bash -e
# Copyright 2024 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# Generates updates to the starlark suite files from the existing autotest
# suites.  This can be run manually to sync suites that with any changes made
# to the autotest suites.


SUITES=(
    # "<suite name> <subdirectory>"
    "bvt-cq cq"
    "bvt-inline cq"
    "bvt-tast-cq cq"
)

CHROOT_DIR="$(cd "$(dirname "$(readlink -f "$0")")"/../../../../.. && pwd)"
echo "${CHROOT_DIR}"
cd "${CHROOT_DIR}"

cros_sdk ../third_party/autotest/files/contrib/suite_migration.py \
    --update-metadata

for INFO in "${SUITES[@]}"; do
    SUITE=$(echo "${INFO}" | cut -d ' ' -f 1)
    SUBDIR=$(echo "${INFO}" | cut -d ' ' -f 2)
    echo "Writing updated ${SUITE} to dir ${SUBDIR}"
    # shellcheck disable=SC2016
    cros_sdk \
        ../third_party/autotest/files/contrib/suite_migration.py \
        --suite "${SUITE}" \
        --output ../"config/test/suite_sets/suite_sets/${SUBDIR}/${SUITE}.star"
done

echo "Updating generated protos..."
"${CHROOT_DIR}/src/config/test/suite_sets/generate.sh"