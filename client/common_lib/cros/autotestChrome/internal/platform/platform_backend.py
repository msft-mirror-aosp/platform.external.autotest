# Copyright 2022 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import absolute_import

import common

from autotest_lib.client.common_lib.cros.autotestChrome.internal.forwarders import do_nothing_forwarder
from autotest_lib.client.common_lib.cros.autotestChrome.internal.platform import network_controller_backend
from autotest_lib.client.common_lib.cros.autotestChrome.internal.platform import tracing_controller_backend


# pylint: disable=unused-argument

class PlatformBackend(object):

  def __init__(self, device=None):
    """ Initalize an instance of PlatformBackend from a device optionally.
      Call sites need to use SupportsDevice before intialization to check
      whether this platform backend supports the device.
      If device is None, this constructor returns the host platform backend
      which telemetry is running on.

      Args:
        device: an instance of telemetry.core.platform.device.Device.
    """
    if device and not self.SupportsDevice(device):
      raise ValueError('Unsupported device: %s' % device.name)
    self._platform = None
    self._network_controller_backend = None
    self._tracing_controller_backend = None
    self._forwarder_factory = None

  def InitPlatformBackend(self):
    self._network_controller_backend = (
        network_controller_backend.NetworkControllerBackend(self))
    self._tracing_controller_backend = (
        tracing_controller_backend.TracingControllerBackend(self))

  @classmethod
  def IsPlatformBackendForHost(cls):
    """ Returns whether this platform backend is the platform backend to be used
    for the host device which telemetry is running on. """
    return False

  @classmethod
  def SupportsDevice(cls, device):
    """ Returns whether this platform backend supports intialization from the
    device. """
    return False

  @classmethod
  def CreatePlatformForDevice(cls, device, finder_options):
    raise NotImplementedError

  def SetPlatform(self, platform):
    assert self._platform is None
    self._platform = platform

  @property
  def platform(self):
    return self._platform

  @property
  def is_host_platform(self):
    return self._platform.is_host_platform

  @property
  def network_controller_backend(self):
    return self._network_controller_backend

  @property
  def tracing_controller_backend(self):
    return self._tracing_controller_backend

  @property
  def forwarder_factory(self):
    if not self._forwarder_factory:
      self._forwarder_factory = self._CreateForwarderFactory()
    return self._forwarder_factory
