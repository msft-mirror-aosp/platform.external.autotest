# Copyright 2014 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""FAFT configuration overrides for Mccloud."""

from autotest_lib.server.cros.faft.config import panther

class Values(panther.Values):
    """Inherit overrides from Panther."""
    pass
