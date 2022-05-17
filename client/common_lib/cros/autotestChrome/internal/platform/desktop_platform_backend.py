# Copyright 2022 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import absolute_import
import os
import subprocess

import common

from autotest_lib.client.common_lib.cros.autotestChrome.internal.platform import platform_backend


class DesktopPlatformBackend(platform_backend.PlatformBackend):

  # This is an abstract class. It is OK to have abstract methods.
  # pylint: disable=abstract-method

  def FlushSystemCacheForDirectory(self, directory):
    assert directory and os.path.exists(directory), \
        'Target directory %s must exist' % directory
    flush_command = binary_manager.FetchPath(
        'clear_system_cache', self.GetOSName(), self.GetArchName())
    assert flush_command, 'You must build clear_system_cache first'

    subprocess.check_call([flush_command, '--recurse', directory])

  def GetDeviceTypeName(self):
    return 'Desktop'

  def GetTypExpectationsTags(self):
    tags = super(DesktopPlatformBackend, self).GetTypExpectationsTags()
    tags.append('desktop')
    return tags
