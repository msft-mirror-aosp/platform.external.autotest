# Copyright 2022 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import absolute_import

import common

from autotest_lib.client.common_lib.cros.autotestChrome.core import exceptions


class InspectorStorage(object):
  def __init__(self, inspector_websocket):
    self._websocket = inspector_websocket
    self._websocket.RegisterDomain('Storage', self._OnNotification)

  def _OnNotification(self, msg):
    # TODO: track storage events
    # (https://chromedevtools.github.io/devtools-protocol/tot/Storage/)
    pass