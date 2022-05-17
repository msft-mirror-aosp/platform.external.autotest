# Copyright 2022 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""A binary manager the prioritizes local versions first.

This is a wrapper around telemetry.internal.util.binary_manager which first
checks for local versions of dependencies in the build directory before falling
back to whatever binary_manager finds, typically versions downloaded from
Google Storage.

This is not meant to be used everywhere, but is useful for dependencies that
get stale relatively quickly and produce hard-to-diagnose issues such as
dependencies for stack symbolization.
"""

from __future__ import absolute_import
import datetime
import logging
import os

import common

from autotest_lib.client.common_lib.cros.autotestChrome.core import exceptions

class LocalFirstBinaryManager(object):
  """Singleton wrapper around telemetry.internal.util.binary_manager.

  Prioritizes locally built versions of dependencies.
  """
  _instance = None

  def __init__(self, build_dir, browser_binary, os_name, arch,
               ignored_dependencies, os_version):
    """
    Args:
      build_dir: A string containing a path to the build directory used to
          build the browser being used. Can be None, in which case the fallback
          to binary_manager will be immediate.
      browser_binary: A string containing a path to the browser binary that will
          be used. Can be None, in which case dependency staleness cannot be
          determined.
      os_name: A string containing the OS name that will be used with
          binary_manager if fallback is required, e.g. "linux".
      arch: A string containing the architecture that will be used with
          binary manager if fallback is required, e.g. "x86_64".
      ignored_dependencies: A list of strings containing names of dependencies
          to skip the local check for.
      os_version: A string containing a specific OS version that will be used
          with binary_manager if fallback is required.
    """
    assert LocalFirstBinaryManager._instance is None
    self._build_dir = build_dir
    self._os = os_name
    self._arch = arch
    self._ignored_dependencies = ignored_dependencies
    self._os_version = os_version
    self._dependency_cache = {}
    self._browser_mtime = None
    if browser_binary:
      mtime = os.path.getmtime(browser_binary)
      self._browser_mtime = datetime.date.fromtimestamp(mtime)

  @classmethod
  def NeedsInit(cls):
    return not cls._instance

  @classmethod
  def Init(cls, build_dir, browser_binary, os_name, arch,
           ignored_dependencies=None, os_version=None):
    """Initializes the singleton.

    Args:
      See constructor.
    """
    if not cls.NeedsInit():
      raise exceptions.InitializationError(
          'Tried to re-initialize LocalFirstBinarymanager with build dir %s '
          'and browser binary %s' % (build_dir, browser_binary))
    ignored_dependencies = ignored_dependencies or []
    cls._instance = LocalFirstBinaryManager(
        build_dir, browser_binary, os_name, arch, ignored_dependencies,
        os_version)
