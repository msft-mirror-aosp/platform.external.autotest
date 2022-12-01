# Copyright 2022 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
from __future__ import absolute_import
try:
  from StringIO import StringIO
except ImportError:
  from io import StringIO

import common

from autotest_lib.client.common_lib.cros.autotestChrome.internal.backends.chrome_inspector import websocket


class InspectorConsole(object):
  def __init__(self, inspector_websocket):
    self._inspector_websocket = inspector_websocket
    self._inspector_websocket.RegisterDomain('Console', self._OnNotification)
    self._message_output_stream = None
    self._last_message = None
    self._console_enabled = False

  def _OnNotification(self, msg):
    if msg['method'] == 'Console.messageAdded':
      assert self._message_output_stream
      if msg['params']['message']['url'] == 'chrome://newtab/':
        return
      self._last_message = '(%s) %s:%i: %s' % (
          msg['params']['message']['level'],
          msg['params']['message']['url'],
          msg['params']['message']['line'],
          msg['params']['message']['text'])
      self._message_output_stream.write(
          '%s\n' % self._last_message)