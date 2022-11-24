#!/usr/bin/env python3
# Lint as: python2, python3
# Copyright 2022 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# This is a trampoline script to invoke the actual generator script.

import os
import sys

target_script_name = 'generate_controlfiles_CTS_T.py'
target_script_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), '..', '..', 'cros', 'tradefed',
                     target_script_name))

# The script specified in target_script_path expects it to be invoked (execv)
# from the directory containing this script (geneate_controlfiles.py).
# Doing a chdir here would meet the expectations for target_script_path
# and also allows this script to be invoked from any directory.
os.chdir(os.path.dirname(os.path.realpath(__file__)))
os.execv(target_script_path, sys.argv)
