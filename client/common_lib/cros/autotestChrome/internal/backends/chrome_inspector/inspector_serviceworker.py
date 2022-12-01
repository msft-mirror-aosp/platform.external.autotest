# Copyright 2022 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import absolute_import

import common

from autotest_lib.client.common_lib.cros.autotestChrome.internal.backends.chrome_inspector import inspector_websocket
from autotest_lib.client.common_lib.cros.autotestChrome.core import exceptions


class InspectorServiceWorker(object):
  def __init__(self, inspector_socket, timeout):
    self._websocket = inspector_socket
    self._websocket.RegisterDomain('ServiceWorker', self._OnNotification)
    # ServiceWorker.enable RPC must be called before calling any other methods
    # in ServiceWorker domain.
    res = self._websocket.SyncRequest(
        {'method': 'ServiceWorker.enable'}, timeout)
    if 'error' in res:
      raise exceptions.StoryActionError(res['error']['message'])

  def _OnNotification(self, msg):
    # TODO: track service worker events
    # (https://chromedevtools.github.io/devtools-protocol/tot/ServiceWorker/)
    pass
