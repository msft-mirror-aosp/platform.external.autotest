# Copyright 2022 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Finds devices that can be controlled by telemetry."""

from __future__ import absolute_import

import common

from autotest_lib.client.common_lib.cros.autotestChrome.internal.platform import cros_device

DEVICES = [
    cros_device,
]


def _GetDeviceFinders(supported_platforms):
  if not supported_platforms or 'all' in supported_platforms:
    return DEVICES
  device_finders = []
  if any(p in supported_platforms for p in ['mac', 'linux', 'win']):
    device_finders.append(desktop_device)
  if 'chromeos' in supported_platforms:
    device_finders.append(cros_device)
  return device_finders


def _GetAllAvailableDevices(options):
  """Returns a list of all available devices."""
  devices = []
  for finder in _GetDeviceFinders(options.target_platforms):
    devices.extend(finder.FindAllAvailableDevices(options))
  return devices


def GetDevicesMatchingOptions(options):
  """Returns a list of devices matching the options."""
  devices = []
  remote_platform_options = options.remote_platform_options
  if (not remote_platform_options.device or
      remote_platform_options.device == 'list'):
    devices = _GetAllAvailableDevices(options)
  else:
    devices = _GetAllAvailableDevices(options)
    devices = [d for d in devices if d.guid ==
               options.remote_platform_options.device]

  devices.sort(key=lambda device: device.name)
  return devices
