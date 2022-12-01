# Copyright 2022 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
from __future__ import division
from __future__ import absolute_import
import logging as real_logging
import os
import subprocess
import time
import six

import common

from autotest_lib.client.common_lib.cros.autotestChrome.core import local_server
from autotest_lib.client.common_lib.cros.autotestChrome.core import network_controller
from autotest_lib.client.common_lib.cros.autotestChrome.core import tracing_controller
from autotest_lib.client.common_lib.cros.autotestChrome.core import util
from autotest_lib.client.common_lib.cros.autotestChrome.internal.platform import (platform_backend as
                                         platform_backend_module)
from autotest_lib.client.common_lib.cros.autotestChrome.py_utils import discover

_HOST_PLATFORM = None
# Remote platform is a dictionary from device ids to remote platform instances.
_REMOTE_PLATFORMS = {}


def _InitHostPlatformIfNeeded():
  global _HOST_PLATFORM # pylint: disable=global-statement
  if _HOST_PLATFORM:
    return
  backend = None
  backends = _IterAllPlatformBackendClasses()
  for platform_backend_class in backends:
    if platform_backend_class.IsPlatformBackendForHost():
      backend = platform_backend_class()
      break
  if not backend:
    raise NotImplementedError()
  _HOST_PLATFORM = Platform(backend)


def GetHostPlatform():
  _InitHostPlatformIfNeeded()
  return _HOST_PLATFORM


def _IterAllPlatformBackendClasses():
  platform_dir = os.path.dirname(os.path.realpath(
      platform_backend_module.__file__))
  return six.itervalues(discover.DiscoverClasses(
      platform_dir, util.GetTelemetryDir(),
      platform_backend_module.PlatformBackend))


def GetPlatformForDevice(device, finder_options, logging=real_logging):
  """ Returns a platform instance for the device.
    Args:
      device: a device.Device instance.
  """
  if device.guid in _REMOTE_PLATFORMS:
    return _REMOTE_PLATFORMS[device.guid]
  try:
    for platform_backend_class in _IterAllPlatformBackendClasses():
      if platform_backend_class.SupportsDevice(device):
        _REMOTE_PLATFORMS[device.guid] = (
            platform_backend_class.CreatePlatformForDevice(device,
                                                           finder_options))
        return _REMOTE_PLATFORMS[device.guid]
    return None
  except Exception: # pylint: disable=broad-except
    logging.error('Fail to create platform instance for %s.', device.name)
    raise


class Platform(object):
  """The platform that the target browser is running on.

  Provides a limited interface to interact with the platform itself, where
  possible. It's important to note that platforms may not provide a specific
  API, so check with IsFooBar() for availability.
  """

  def __init__(self, platform_backend):
    self._platform_backend = platform_backend
    self._platform_backend.InitPlatformBackend()
    self._platform_backend.SetPlatform(self)
    self._network_controller = network_controller.NetworkController(
        self._platform_backend.network_controller_backend)
    self._tracing_controller = tracing_controller.TracingController(
        self._platform_backend.tracing_controller_backend)
    self._local_server_controller = local_server.LocalServerController(
        self._platform_backend)
    self._forwarder = None

  @property
  def network_controller(self):
    """Control network settings and servers to simulate the Web."""
    return self._network_controller

  def GetArchName(self):
    """Returns a string description of the Platform architecture.

    Examples: x86_64 (posix), AMD64 (win), armeabi-v7a, x86"""
    return self._platform_backend.GetArchName()

  def GetOSName(self):
    """Returns a string description of the Platform OS.

    Examples: WIN, MAC, LINUX, CHROMEOS"""
    return self._platform_backend.GetOSName()

  def GetOSVersionName(self):
    """Returns a logically sortable, string-like description of the Platform OS
    version.

    Examples: VISTA, WIN7, LION, MOUNTAINLION"""
    return self._platform_backend.GetOSVersionName()

  def GetOSVersionDetailString(self):
    """Returns more detailed information about the OS version than
    GetOSVersionName, if available. Otherwise returns the empty string.

    Examples: '10.12.4' on macOS."""
    return self._platform_backend.GetOSVersionDetailString()

  def StopAllLocalServers(self):
    self._local_server_controller.Close()
    if self._forwarder:
      self._forwarder.Close()