# Copyright 2021 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from autotest_lib.client.common_lib import error
from autotest_lib.server.cros.faft.cr50_test import Cr50Test


class firmware_Cr50VerifyEK(Cr50Test):
    """Verify tpm verify ek."""
    version = 1

    def run_once(self, host):
        """Run tpm verify ek."""
        host.run('tpm_manager_client take_ownership')
        result = host.run('attestation_client verify_attestation --ek-only').stdout
        if 'verified: true' not in result:
            raise error.TestError("Attestation failed: %s" % result)
