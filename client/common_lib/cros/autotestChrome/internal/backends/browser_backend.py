# Copyright 2022 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import division
from __future__ import absolute_import
import logging
import os
import posixpath
import uuid
import sys
import tempfile
import threading
import time

import common

from autotest_lib.client.common_lib.cros.autotestChrome import decorators
from autotest_lib.client.common_lib.cros.autotestChrome.core import debug_data
from autotest_lib.client.common_lib.cros.autotestChrome.core import exceptions
from autotest_lib.client.common_lib.cros.autotestChrome.internal.backends import app_backend
from autotest_lib.client.common_lib.cros.autotestChrome.internal.browser import web_contents


class ExtensionsNotSupportedException(Exception):
  pass


class BrowserBackend(app_backend.AppBackend):
  """A base class for browser backends."""

  def __init__(self, platform_backend, browser_options,
               supports_extensions, tab_list_backend):
    assert browser_options.browser_type
    super(BrowserBackend, self).__init__(browser_options.browser_type,
                                         platform_backend)
    self.browser_options = browser_options
    self._supports_extensions = supports_extensions
    self._tab_list_backend_class = tab_list_backend
    self._dump_finder = None
    self._tmp_minidump_dir = tempfile.mkdtemp()
    self._symbolized_minidump_paths = set([])
    self._periodic_screenshot_timer = None
    self._collect_periodic_screenshots = False

  def SetBrowser(self, browser):
    super(BrowserBackend, self).SetApp(app=browser)

  @property
  def browser(self):
    return self.app

  @property
  def supports_uploading_logs(self):
    # Specific browser backend is responsible for overriding this properly.
    return False

  @property
  def supports_extensions(self):
    """True if this browser backend supports extensions."""
    return self._supports_extensions

  @property
  @decorators.Cache
  def tab_list_backend(self):
    return self._tab_list_backend_class(self)