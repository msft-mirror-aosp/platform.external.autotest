# Copyright 2022 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import absolute_import
import logging

import common

from autotest_lib.client.common_lib.cros.autotestChrome import decorators
from autotest_lib.client.common_lib.cros.autotestChrome.core import cros_interface
from autotest_lib.client.common_lib.cros.autotestChrome.core import platform
from autotest_lib.client.common_lib.cros.autotestChrome.core import util
from autotest_lib.client.common_lib.cros.autotestChrome.internal.forwarders import cros_forwarder
from autotest_lib.client.common_lib.cros.autotestChrome.internal.platform import cros_device
from autotest_lib.client.common_lib.cros.autotestChrome.internal.platform import linux_based_platform_backend


class CrosPlatformBackend(
    linux_based_platform_backend.LinuxBasedPlatformBackend):
  def __init__(self, device=None):
    super(CrosPlatformBackend, self).__init__(device)
    if device and not device.is_local:
      self._cri = cros_interface.CrOSInterface(
          device.host_name, device.ssh_port, device.ssh_identity)
      self._cri.TryLogin()
    else:
      self._cri = cros_interface.CrOSInterface()

  def GetDeviceId(self):
    return self._cri.hostname

  @classmethod
  def IsPlatformBackendForHost(cls):
    return util.IsRunningOnCrosDevice()

  @classmethod
  def SupportsDevice(cls, device):
    return isinstance(device, cros_device.CrOSDevice)

  @classmethod
  def CreatePlatformForDevice(cls, device, finder_options):
    assert cls.SupportsDevice(device)
    return platform.Platform(CrosPlatformBackend(device))

  @property
  def cri(self):
    return self._cri

  def _CreateForwarderFactory(self):
    return cros_forwarder.CrOsForwarderFactory(self._cri)

  @decorators.Cache
  def GetArchName(self):
    return self._cri.GetArchName()

  def GetOSName(self):
    return 'chromeos'

  def GetOSVersionName(self):
    return ''  # TODO: Implement this.

  def GetOSVersionDetailString(self):
    return ''  # TODO(kbr): Implement this.

  def GetTypExpectationsTags(self):
    tags = super(CrosPlatformBackend, self).GetTypExpectationsTags()
    tags.append('desktop')
    if self.cri.local:
      tags.append('chromeos-local')
    else:
      tags.append('chromeos-remote')
    if self.cri.GetBoard():
      tags.append('chromeos-board-%s' % self.cri.GetBoard())
    return tags
