# Copyright 2022 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

class PossibleApp(object):
  """A factory class that can be used to create a running instance of app.

  Call Create() to launch the app and begin manipulating it.
  """

  def __init__(self, app_type, target_os):
    self._app_type = app_type
    self._target_os = target_os
    self._platform = None
    self._platform_backend = None

  @property
  def app_type(self):
    return self._app_type