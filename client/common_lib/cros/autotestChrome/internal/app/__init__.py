# Copyright 2022 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import absolute_import
import logging
import time

import common

from autotest_lib.client.common_lib.cros.autotestChrome.core import debug_data

class App(object):
  """ A running application instance that can be controlled in a limited way.

  Be sure to clean up after yourself by calling Close() when you are done with
  the app. Or better yet:
    with possible_app.Create(options) as app:
      ... do all your operations on app here
  """
  def __init__(self, app_backend, platform_backend):
    assert platform_backend.platform != None
    self._app_backend = app_backend
    self._platform_backend = platform_backend
    self._app_backend.SetApp(self)

  @property
  def platform(self):
    return self._platform_backend.platform