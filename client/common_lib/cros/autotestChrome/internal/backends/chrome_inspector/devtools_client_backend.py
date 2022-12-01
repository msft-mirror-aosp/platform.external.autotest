# Copyright 2022 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import absolute_import
import logging
import re
import socket
import sys
import six

import common

from autotest_lib.client.common_lib.cros.autotestChrome.py_utils import exc_util
from autotest_lib.client.common_lib.cros.autotestChrome.py_utils import retry_util
from autotest_lib.client.common_lib.cros.autotestChrome.core import exceptions
from autotest_lib.client.common_lib.cros.autotestChrome import decorators
from autotest_lib.client.common_lib.cros.autotestChrome.internal.backends import browser_backend
from autotest_lib.client.common_lib.cros.autotestChrome.internal.backends.chrome_inspector import devtools_http
from autotest_lib.client.common_lib.cros.autotestChrome.internal.backends.chrome_inspector import inspector_backend
from autotest_lib.client.common_lib.cros.autotestChrome.internal.backends.chrome_inspector import inspector_websocket
from autotest_lib.client.common_lib.cros.autotestChrome.internal.backends.chrome_inspector import system_info_backend
from autotest_lib.client.common_lib.cros.autotestChrome.internal.backends.chrome_inspector import tracing_backend
from autotest_lib.client.common_lib.cros.autotestChrome.internal.platform.tracing_agent import (
    chrome_tracing_devtools_manager)


class TabNotFoundError(exceptions.Error):
  pass


class UnsupportedVersionError(exceptions.Error):
  pass


# Only versions of Chrome from M58 and above are supported. Older versions
# did not support many of the modern features currently in use by Telemetry.
MIN_SUPPORTED_BRANCH_NUMBER = 3029

# The first WebSocket connections or calls against a newly-started
# browser, specifically in Debug builds, can take a long time. Give
# them 60s to complete instead of the default 10s used in many places
# in this file.
_FIRST_CALL_TIMEOUT = 60

# These are possible exceptions raised when the DevTools agent is not ready
# to accept incomming connections.
_DEVTOOLS_CONNECTION_ERRORS = (
    devtools_http.DevToolsClientConnectionError,
    inspector_websocket.WebSocketException,
    socket.error)


def GetDevToolsBackEndIfReady(devtools_port, app_backend, browser_target=None, enable_tracing=True):
  client = _DevToolsClientBackend(app_backend)
  try:
    client.Connect(devtools_port, browser_target, enable_tracing)
    logging.info('DevTools agent ready at %s', client)
  except _DEVTOOLS_CONNECTION_ERRORS as exc:
    logging.info('DevTools agent at %s not ready yet: %s', client, exc)
    client = None
  return client


class FuchsiaBrowserTargetNotFoundException(Exception):
  pass

class _DevToolsClientBackend(object):
  """An object that communicates with Chrome's devtools.

  This class owns a map of InspectorBackends. It is responsible for creating
  and destroying them.
  """
  def __init__(self, app_backend):
    """Create an object able to connect with the DevTools agent.

    Args:
      app_backend: The app that contains the DevTools agent.
    """
    self._app_backend = app_backend
    self._browser_target = None
    self._forwarder = None
    self._devtools_http = None
    self._browser_websocket = None
    self._created = False
    self._local_port = None
    self._remote_port = None

    # Other backends.
    self._tracing_backend = None
    self._memory_backend = None
    self._system_info_backend = None
    self._wm_backend = None
    self._devtools_context_map_backend = _DevToolsContextMapBackend(self)

  def __str__(self):
    s = self.browser_target_url
    if self.local_port != self.remote_port:
      s = '%s (remote=%s)' % (s, self.remote_port)
    return s

  @property
  def local_port(self):
    return self._local_port

  @property
  def remote_port(self):
    return self._remote_port

  @property
  def browser_target_url(self):
    # For Fuchsia browsers, we get the browser_target through a JSON request
    if self.platform_backend.GetOSName() == 'fuchsia':
      resp = self.GetVersion()
      if 'webSocketDebuggerUrl' in resp:
        return resp['webSocketDebuggerUrl']
      else:
        raise FuchsiaBrowserTargetNotFoundException(
            'Could not get the browser target.')
    return 'ws://127.0.0.1:%i%s' % (self._local_port, self._browser_target)

  @property
  def platform_backend(self):
    return self._app_backend.platform_backend

  def Connect(self, devtools_port, browser_target, enable_tracing=True):
    try:
      self._Connect(devtools_port, browser_target, enable_tracing)
    except:
      self.Close()  # Close any connections made if failed to connect to all.
      raise

  @retry_util.RetryOnException(devtools_http.DevToolsClientUrlError, retries=3)
  def _WaitForConnection(self, retries=None):
    del retries
    self._devtools_http.Request('')

  def _SetUpPortForwarding(self, devtools_port):
    self._forwarder = self.platform_backend.forwarder_factory.Create(
        local_port=None,  # Forwarder will choose an available port.
        remote_port=devtools_port, reverse=True)
    self._local_port = self._forwarder._local_port
    self._remote_port = self._forwarder._remote_port
    self._devtools_http = devtools_http.DevToolsHttp(self.local_port)

    # For Fuchsia, wait until port forwarding has started working.
    if self.platform_backend.GetOSName() == 'fuchsia':
      self._WaitForConnection()

  def _Connect(self, devtools_port, browser_target, enable_tracing):
    """Attempt to connect to the DevTools client.

    Args:
      devtools_port: The devtools_port uniquely identifies the DevTools agent.
      browser_target: An optional string to override the default path used to
        establish a websocket connection with the browser inspector.
      enable_tracing: Defines if a tracing_client is created.

    Raises:
      Any of _DEVTOOLS_CONNECTION_ERRORS if failed to establish the connection.
    """
    self._browser_target = browser_target or '/devtools/browser'
    self._SetUpPortForwarding(devtools_port)

    # If the agent is not alive and ready, trying to get the branch number will
    # raise a devtools_http.DevToolsClientConnectionError.
    branch_number = self.GetChromeBranchNumber()
    if branch_number < MIN_SUPPORTED_BRANCH_NUMBER:
      raise UnsupportedVersionError(
          'Chrome branch number %d is no longer supported' % branch_number)

    # Ensure that the inspector websocket is ready. This may raise a
    # inspector_websocket.WebSocketException or socket.error if not ready.
    self._browser_websocket = inspector_websocket.InspectorWebsocket()
    self._browser_websocket.Connect(self.browser_target_url, timeout=10)

    chrome_tracing_devtools_manager.RegisterDevToolsClient(self)

    # If there is a trace_config it means that Telemetry has already started
    # Chrome tracing via a startup config. The TracingBackend also needs needs
    # this config to initialize itself correctly.
    if enable_tracing:
      trace_config = (
          self.platform_backend.tracing_controller_backend.GetChromeTraceConfig())
      self._tracing_backend = tracing_backend.TracingBackend(
          self._browser_websocket, trace_config)

  @exc_util.BestEffort
  def Close(self):
    if self._tracing_backend is not None:
      self._tracing_backend.Close()
      self._tracing_backend = None
    if self._memory_backend is not None:
      self._memory_backend.Close()
      self._memory_backend = None
    if self._system_info_backend is not None:
      self._system_info_backend.Close()
      self._system_info_backend = None
    if self._wm_backend is not None:
      self._wm_backend.Close()
      self._wm_backend = None

    if self._devtools_context_map_backend is not None:
      self._devtools_context_map_backend.Clear()
      self._devtools_context_map_backend = None

    # Close the DevTools connections last (in case the backends above still
    # need to interact with them while closing).
    if self._browser_websocket is not None:
      self._browser_websocket.Disconnect()
      self._browser_websocket = None
    if self._devtools_http is not None:
      self._devtools_http.Disconnect()
      self._devtools_http = None
    if self._forwarder is not None:
      self._forwarder.Close()
      self._forwarder = None


  def IsAlive(self):
    """Whether the DevTools server is available and connectable."""
    if self._devtools_http is None:
      return False
    try:
      self._devtools_http.Request('')
    except devtools_http.DevToolsClientConnectionError:
      return False
    else:
      return True

  @decorators.Cache
  def GetVersion(self):
    """Return the version dict as provided by the DevTools agent."""
    return self._devtools_http.RequestJson('version')

  def GetChromeBranchNumber(self):
    # Detect version information.
    resp = self.GetVersion()
    if 'Protocol-Version' in resp:
      if 'Browser' in resp:
        branch_number_match = re.search(r'.+/\d+\.\d+\.(\d+)\.\d+',
                                        resp['Browser'])
      if not branch_number_match and 'User-Agent' in resp:
        branch_number_match = re.search(
            r'Chrome/\d+\.\d+\.(\d+)\.\d+ (Mobile )?Safari',
            resp['User-Agent'])

      if branch_number_match:
        branch_number = int(branch_number_match.group(1))
        if branch_number:
          return branch_number

    # Branch number can't be determined, so fail any branch number checks.
    return 0

  def _ListInspectableContexts(self):
    return self._devtools_http.RequestJson('')

  def RequestNewTab(self, timeout, in_new_window=False, url=None):
    """Creates a new tab, either in new window or current window.

    Returns:
      A dict of a parsed JSON object as returned by DevTools. Example:
      If an error is present, the dict will contain an 'error' key.
      If no error is present, the result is present in the 'result' key:
      {
        "result": {
          "targetId": "id-string"  # This is the ID for the tab.
        }
      }
    """
    request = {
        'method': 'Target.createTarget',
        'params': {
            'url': url if url else 'about:blank',
            'newWindow': in_new_window
        }
    }
    return self._browser_websocket.SyncRequest(request, timeout)

  def GetUrl(self, tab_id):
    """Returns the URL of the tab with |tab_id|, as reported by devtools.

    Raises:
      devtools_http.DevToolsClientConnectionError
    """
    for c in self._ListInspectableContexts():
      if c['id'] == tab_id:
        return c['url']
    return None

  def GetUpdatedInspectableContexts(self):
    """Returns an updated instance of _DevToolsContextMapBackend."""
    contexts = self._ListInspectableContexts()
    self._devtools_context_map_backend._Update(contexts)
    return self._devtools_context_map_backend

  def _CreateSystemInfoBackendIfNeeded(self):
    if not self._system_info_backend:
      self._system_info_backend = system_info_backend.SystemInfoBackend(
          self.browser_target_url)

  def GetSystemInfo(self, timeout=_FIRST_CALL_TIMEOUT):
    self._CreateSystemInfoBackendIfNeeded()
    return self._system_info_backend.GetSystemInfo(timeout)

class _DevToolsContextMapBackend(object):
  def __init__(self, devtools_client):
    self._devtools_client = devtools_client
    self._contexts = None
    self._inspector_backends_dict = {}

  @property
  def contexts(self):
    """The most up to date contexts data.

    Returned in the order returned by devtools agent."""
    return self._contexts

  def GetContextInfo(self, context_id):
    for context in self._contexts:
      if context['id'] == context_id:
        return context
    raise KeyError('Cannot find a context with id=%s' % context_id)

  def GetInspectorBackend(self, context_id):
    """Gets an InspectorBackend instance for the given context_id.

    This lazily creates InspectorBackend for the context_id if it does
    not exist yet. Otherwise, it will return the cached instance."""
    if context_id in self._inspector_backends_dict:
      return self._inspector_backends_dict[context_id]

    for context in self._contexts:
      if context['id'] == context_id:
        new_backend = inspector_backend.InspectorBackend(
            self._devtools_client, context)
        self._inspector_backends_dict[context_id] = new_backend
        return new_backend

    raise KeyError('Cannot find a context with id=%s' % context_id)

  def _Update(self, contexts):
    # Remove InspectorBackend that is not in the current inspectable
    # contexts list.
    context_ids = [context['id'] for context in contexts]
    for context_id in list(self._inspector_backends_dict.keys()):
      if context_id not in context_ids:
        backend = self._inspector_backends_dict[context_id]
        backend.Disconnect()
        del self._inspector_backends_dict[context_id]

    valid_contexts = []
    for context in contexts:
      # If the context does not have webSocketDebuggerUrl, skip it.
      # If an InspectorBackend is already created for the tab,
      # webSocketDebuggerUrl will be missing, and this is expected.
      context_id = context['id']
      if context_id not in self._inspector_backends_dict:
        if 'webSocketDebuggerUrl' not in context:
          logging.debug('webSocketDebuggerUrl missing, removing %s',
                        context_id)
          continue
      valid_contexts.append(context)
    self._contexts = valid_contexts

  def Clear(self):
    for backend in self._inspector_backends_dict.values():
      backend.Disconnect()
    self._inspector_backends_dict = {}
    self._contexts = None
