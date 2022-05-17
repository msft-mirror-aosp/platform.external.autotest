# Copyright 2022 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import absolute_import
import ctypes
import ctypes.util
import os
import sys


GET_TICK_COUNT_LAST_NOW = 0
# If GET_TICK_COUNTER_LAST_NOW is less than the current time, the clock has
# rolled over, and this needs to be accounted for.
GET_TICK_COUNT_WRAPAROUNDS = 0
# The current detected platform
_CLOCK = None
_NOW_FUNCTION = None
# Mapping of supported platforms and what is returned by sys.platform.
_PLATFORMS = {
    'mac': 'darwin',
    'linux': 'linux',
    'windows': 'win32',
    'cygwin': 'cygwin',
    'freebsd': 'freebsd',
    'sunos': 'sunos5',
    'bsd': 'bsd'
}
# Mapping of what to pass get_clocktime based on platform.
_CLOCK_MONOTONIC = {
    'linux': 1,
    'freebsd': 4,
    'bsd': 3,
    'sunos5': 4
}

_LINUX_CLOCK = 'LINUX_CLOCK_MONOTONIC'
_MAC_CLOCK = 'MAC_MACH_ABSOLUTE_TIME'
_WIN_HIRES = 'WIN_QPC'
_WIN_LORES = 'WIN_ROLLOVER_PROTECTED_TIME_GET_TIME'


def GetClockGetTimeClockNumber(plat):
  for key in _CLOCK_MONOTONIC:
    if plat.startswith(key):
      return _CLOCK_MONOTONIC[key]
  raise LookupError('Platform not in clock dicitonary')

def InitializeLinuxNowFunction(plat):
  """Sets a monotonic clock for linux platforms.

    Args:
      plat: Platform that is being run on.
  """
  global _CLOCK  # pylint: disable=global-statement
  global _NOW_FUNCTION  # pylint: disable=global-statement
  _CLOCK = _LINUX_CLOCK
  clock_monotonic = GetClockGetTimeClockNumber(plat)
  try:
    # Attempt to find clock_gettime in the C library.
    clock_gettime = ctypes.CDLL(ctypes.util.find_library('c'),
                                use_errno=True).clock_gettime
  except AttributeError:
    # If not able to find int in the C library, look in rt library.
    clock_gettime = ctypes.CDLL(ctypes.util.find_library('rt'),
                                use_errno=True).clock_gettime

  class Timespec(ctypes.Structure):
    """Time specification, as described in clock_gettime(3)."""
    _fields_ = (('tv_sec', ctypes.c_long),
                ('tv_nsec', ctypes.c_long))

  def LinuxNowFunctionImpl():
    ts = Timespec()
    if clock_gettime(clock_monotonic, ctypes.pointer(ts)):
      errno = ctypes.get_errno()
      raise OSError(errno, os.strerror(errno))
    return ts.tv_sec + ts.tv_nsec / 1.0e9

  _NOW_FUNCTION = LinuxNowFunctionImpl


def InitializeNowFunction(plat):
  """Sets a monotonic clock for the current platform.

    Args:
      plat: Platform that is being run on.
  """
  if plat.startswith(_PLATFORMS['mac']):
    InitializeMacNowFunction(plat)

  elif (plat.startswith(_PLATFORMS['linux'])
        or plat.startswith(_PLATFORMS['freebsd'])
        or plat.startswith(_PLATFORMS['bsd'])
        or plat.startswith(_PLATFORMS['sunos'])):
    InitializeLinuxNowFunction(plat)

  elif (plat.startswith(_PLATFORMS['windows'])
        or plat.startswith(_PLATFORMS['cygwin'])):
    InitializeWinNowFunction(plat)

  else:
    raise RuntimeError('%s is not a supported platform.' % plat)

  global _NOW_FUNCTION
  global _CLOCK
  assert _NOW_FUNCTION, 'Now function not properly set during initialization.'
  assert _CLOCK, 'Clock not properly set during initialization.'


def Now():
  return _NOW_FUNCTION() * 1e6  # convert from seconds to microseconds


def GetClock():
  return _CLOCK


InitializeNowFunction(sys.platform)
