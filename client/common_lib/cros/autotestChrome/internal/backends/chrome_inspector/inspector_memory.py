# Copyright 2022 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
from __future__ import absolute_import
import json

import common

from autotest_lib.client.common_lib.cros.autotestChrome.core import exceptions


class InspectorMemoryException(exceptions.Error):
  pass


class InspectorMemory(object):
  """Communicates with the remote inspector's Memory domain."""

  def __init__(self, inspector_websocket):
    self._inspector_websocket = inspector_websocket
    self._inspector_websocket.RegisterDomain('Memory', self._OnNotification)

  def _OnNotification(self, msg):
    pass
