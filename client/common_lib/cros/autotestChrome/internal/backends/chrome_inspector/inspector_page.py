# Copyright 2022 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
from __future__ import absolute_import
import time

import common


class InspectorPage(object):
  """Class that controls a page connected by an inspector_websocket.

  This class provides utility methods for controlling a page connected by an
  inspector_websocket. It does not perform any exception handling. All
  inspector_websocket exceptions must be handled by the caller.
  """
  def __init__(self, inspector_websocket, timeout):
    self._inspector_websocket = inspector_websocket
    self._inspector_websocket.RegisterDomain('Page', self._OnNotification)

    self._navigation_pending = False
    self._navigation_url = ''  # Support for legacy backends.
    self._navigation_frame_id = ''
    self._navigated_frame_ids = None  # Holds frame ids while navigating.
    self._script_to_evaluate_on_commit = None
    # Turn on notifications. We need them to get the Page.frameNavigated event.
    self._EnablePageNotifications(timeout=timeout)

  def _OnNotification(self, msg):
    if msg['method'] == 'Page.frameNavigated':
      url = msg['params']['frame']['url']
      if not self._navigated_frame_ids is None:
        frame_id = msg['params']['frame']['id']
        if self._navigation_frame_id == frame_id:
          self._navigation_frame_id = ''
          self._navigated_frame_ids = None
          self._navigation_pending = False
        else:
          self._navigated_frame_ids.add(frame_id)
      elif self._navigation_url == url:
        # TODO(tonyg): Remove this when Chrome 38 goes stable.
        self._navigation_url = ''
        self._navigation_pending = False
      elif (not url == 'chrome://newtab/' and not url == 'about:blank' and
            not 'parentId' in msg['params']['frame']):
        # Marks the navigation as complete and unblocks the
        # WaitForNavigate call.
        self._navigation_pending = False

  def _EnablePageNotifications(self, timeout=60):
    request = {
        'method': 'Page.enable'
        }
    res = self._inspector_websocket.SyncRequest(request, timeout)
    assert len(res['result']) == 0

  def CollectGarbage(self, timeout=60):
    request = {
        'method': 'HeapProfiler.collectGarbage'
        }
    res = self._inspector_websocket.SyncRequest(request, timeout)
    assert 'result' in res
