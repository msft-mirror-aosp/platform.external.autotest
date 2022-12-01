# Copyright 2022 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import absolute_import
import base64
import json
import logging
import re
import socket
import time
import traceback

import common

from autotest_lib.client.common_lib.cros.autotestChrome.core import exceptions
from autotest_lib.client.common_lib.cros.autotestChrome import decorators
from autotest_lib.client.common_lib.cros.autotestChrome.internal.backends.chrome_inspector import inspector_websocket
from autotest_lib.client.common_lib.cros.autotestChrome.internal.backends.chrome_inspector import websocket
from autotest_lib.client.common_lib.cros.autotestChrome.tracing.trace_data import trace_data as trace_data_module


class TracingBackend(object):

  _TRACING_DOMAIN = 'Tracing'

  def __init__(self, inspector_socket, startup_tracing_config=None):
    self._inspector_websocket = inspector_socket
    self._inspector_websocket.RegisterDomain(
        self._TRACING_DOMAIN, self._NotificationHandler)
    self._is_tracing_running = False
    self._can_collect_data = False
    self._has_received_all_tracing_data = False
    self._trace_data_builder = None
    self._data_loss_occurred = False
    if startup_tracing_config is not None:
      self._TakeOwnershipOfTracingSession(startup_tracing_config)

  def _NotificationHandler(self, res):
    if res.get('method') == 'Tracing.dataCollected':
      value = res.get('params', {}).get('value')
      self._trace_data_builder.AddTraceFor(
          trace_data_module.CHROME_TRACE_PART,
          {'traceEvents': value})
    elif res.get('method') == 'Tracing.tracingComplete':
      params = res.get('params', {})
      # TODO(crbug.com/948412): Start requiring a value for dataLossOccurred
      # once we stop supporting Chrome M76 (which was the last version that
      # did not return this as a required parameter).
      self._data_loss_occurred = params.get('dataLossOccurred', False)
      stream_handle = params.get('stream')
      if not stream_handle:
        self._has_received_all_tracing_data = True
        return
      trace_handle = self._trace_data_builder.OpenTraceHandleFor(
          trace_data_module.CHROME_TRACE_PART,
          suffix=_GetTraceFileSuffix(params))
      reader = _DevToolsStreamReader(
          self._inspector_websocket, stream_handle, trace_handle)
      reader.Read(self._ReceivedAllTraceDataFromStream)

  def Close(self):
    self._inspector_websocket.UnregisterDomain(self._TRACING_DOMAIN)
    self._inspector_websocket = None
