#!/usr/bin/python3

# Copyright 2014 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import common, os
from autotest_lib.client.bin import utils

version = 1

def setup():
    """Nothing needs to be done here."""
    pass

pwd = os.getcwd()
utils.update_version(pwd + '/src', True, version, setup)
