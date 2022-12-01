# Copyright 2022 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import absolute_import
import datetime
import glob
import heapq
import os
import subprocess
import time

import common

from autotest_lib.client.common_lib.cros.autotestChrome.internal.util import local_first_binary_manager


class MinidumpFinder(object):
  """Handles finding Crashpad/Breakpad minidumps.

  In addition to whatever data is expected to be returned, most public methods
  also return a list of strings. These strings are what would normally be
  logged, but returned in the list instead of being logged directly to help
  cut down on log spam from uses such as
  BrowserBackend.GetRecentMinidumpPathWithTimeout().
  """
  def __init__(self, os_name, arch_name):
    super(MinidumpFinder, self).__init__()
    self._os = os_name
    self._arch = arch_name
    self._minidump_path_crashpad_retrieval = {}
    self._explanation = []