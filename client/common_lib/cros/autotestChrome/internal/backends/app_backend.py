# Copyright 2022 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import absolute_import
import six

import common

from autotest_lib.client.common_lib.cros.autotestChrome.py_trace_event import trace_event


class AppBackend(six.with_metaclass(trace_event.TracedMetaClass, object)):

  def __init__(self, app_type, platform_backend):
    super(AppBackend, self).__init__()
    self._app = None
    self._app_type = app_type
    self._platform_backend = platform_backend

  def SetApp(self, app):
    self._app = app

  @property
  def app(self):
    return self._app

  @property
  def platform_backend(self):
    return self._platform_backend