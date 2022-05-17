# Copyright 2022 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import absolute_import
import functools
import logging
import socket
import sys
import time
import six

import common

from six.moves import input # pylint: disable=redefined-builtin
from autotest_lib.client.common_lib.cros.autotestChrome.py_trace_event import trace_event
from autotest_lib.client.common_lib.cros.autotestChrome.core import exceptions
from autotest_lib.client.common_lib.cros.autotestChrome import decorators
from autotest_lib.client.common_lib.cros.autotestChrome.internal.backends.chrome_inspector import devtools_http
from autotest_lib.client.common_lib.cros.autotestChrome.internal.backends.chrome_inspector import inspector_console
from autotest_lib.client.common_lib.cros.autotestChrome.internal.backends.chrome_inspector import inspector_log
from autotest_lib.client.common_lib.cros.autotestChrome.internal.backends.chrome_inspector import inspector_memory
from autotest_lib.client.common_lib.cros.autotestChrome.internal.backends.chrome_inspector import inspector_page
from autotest_lib.client.common_lib.cros.autotestChrome.internal.backends.chrome_inspector import inspector_runtime
from autotest_lib.client.common_lib.cros.autotestChrome.internal.backends.chrome_inspector import inspector_serviceworker
from autotest_lib.client.common_lib.cros.autotestChrome.internal.backends.chrome_inspector import inspector_storage
from autotest_lib.client.common_lib.cros.autotestChrome.internal.backends.chrome_inspector import inspector_websocket
from autotest_lib.client.common_lib.cros.autotestChrome.util import js_template
from autotest_lib.client.common_lib.cros.autotestChrome import py_utils


def _HandleInspectorWebSocketExceptions(func):
  """Decorator for converting inspector_websocket exceptions.

  When an inspector_websocket exception is thrown in the original function,
  this decorator converts it into a telemetry exception and adds debugging
  information.
  """
  @functools.wraps(func)
  def Inner(inspector_backend, *args, **kwargs):
    try:
      return func(inspector_backend, *args, **kwargs)
    except (socket.error, inspector_websocket.WebSocketException,
            inspector_websocket.WebSocketDisconnected) as e:
      inspector_backend._ConvertExceptionFromInspectorWebsocket(e)

  return Inner


class InspectorBackend(six.with_metaclass(trace_event.TracedMetaClass, object)):
  """Class for communicating with a devtools client.

  The owner of an instance of this class is responsible for calling
  Disconnect() before disposing of the instance.
  """

  def __init__(self, devtools_client, context, timeout=120):
    self._websocket = inspector_websocket.InspectorWebsocket()
    self._websocket.RegisterDomain(
        'Inspector', self._HandleInspectorDomainNotification)
    self._cast_issue_message, self._cast_sink_list = None, []
    self._websocket.RegisterDomain('Cast', self._HandleCastDomainNotification)

    self._devtools_client = devtools_client
    # Be careful when using the context object, since the data may be
    # outdated since this is never updated once InspectorBackend is
    # created. Consider an updating strategy for this. (For an example
    # of the subtlety, see the logic for self.url property.)
    self._context = context

    logging.debug('InspectorBackend._Connect() to %s', self.debugger_url)
    try:
      self._websocket.Connect(self.debugger_url, timeout)
      self._console = inspector_console.InspectorConsole(self._websocket)
      self._log = inspector_log.InspectorLog(self._websocket)
      self._memory = inspector_memory.InspectorMemory(self._websocket)
      self._page = inspector_page.InspectorPage(
          self._websocket, timeout=timeout)
      self._runtime = inspector_runtime.InspectorRuntime(self._websocket)
      self._serviceworker = inspector_serviceworker.InspectorServiceWorker(
          self._websocket, timeout=timeout)
      self._storage = inspector_storage.InspectorStorage(self._websocket)
    except (inspector_websocket.WebSocketException, exceptions.TimeoutException,
            py_utils.TimeoutException) as e:
      self._ConvertExceptionFromInspectorWebsocket(e)

  def Disconnect(self):
    """Disconnects the inspector websocket.

    This method intentionally leaves the self._websocket object around, so that
    future calls it to it will fail with a relevant error.
    """
    if self._websocket:
      self._websocket.Disconnect()

  @property
  def url(self):
    """Returns the URL of the tab, as reported by devtools.

    Raises:
      devtools_http.DevToolsClientConnectionError
    """
    return self._devtools_client.GetUrl(self.id)

  @property
  def id(self): # pylint: disable=invalid-name
    return self._context['id']

  @property
  def debugger_url(self):
    return self._context['webSocketDebuggerUrl']

  @_HandleInspectorWebSocketExceptions
  def ExecuteJavaScript(self, statement, **kwargs):
    """Executes a given JavaScript statement. Does not return the result.

    Example: runner.ExecuteJavaScript('var foo = {{ value }};', value='hi');

    Args:
      statement: The statement to execute (provided as a string).

    Optional keyword args:
      timeout: The number of seconds to wait for the statement to execute.
      context_id: The id of an iframe where to execute the code; the main page
          has context_id=1, the first iframe context_id=2, etc.
      user_gesture: Whether execution should be treated as initiated by user
          in the UI. Code that plays media or requests fullscreen may not take
          effects without user_gesture set to True.
      Additional keyword arguments provide values to be interpolated within
          the statement. See telemetry.util.js_template for details.

    Raises:
      py_utils.TimeoutException
      exceptions.EvaluateException
      exceptions.WebSocketException
      exceptions.DevtoolsTargetCrashException
    """
    # Use the default both when timeout=None or the option is ommited.
    timeout = kwargs.pop('timeout', None) or 60
    context_id = kwargs.pop('context_id', None)
    user_gesture = kwargs.pop('user_gesture', None) or False
    statement = js_template.Render(statement, **kwargs)
    self._runtime.Execute(statement, context_id, timeout,
                          user_gesture=user_gesture)

  def EvaluateJavaScript(self, expression, **kwargs):
    """Returns the result of evaluating a given JavaScript expression.

    Example: runner.ExecuteJavaScript('document.location.href');

    Args:
      expression: The expression to execute (provided as a string).

    Optional keyword args:
      timeout: The number of seconds to wait for the expression to evaluate.
      context_id: The id of an iframe where to execute the code; the main page
          has context_id=1, the first iframe context_id=2, etc.
      user_gesture: Whether execution should be treated as initiated by user
          in the UI. Code that plays media or requests fullscreen may not take
          effects without user_gesture set to True.
      promise: Whether the execution is a javascript promise, and should
          wait for the promise to resolve prior to returning.
      Additional keyword arguments provide values to be interpolated within
          the expression. See telemetry.util.js_template for details.

    Raises:
      py_utils.TimeoutException
      exceptions.EvaluateException
      exceptions.WebSocketException
      exceptions.DevtoolsTargetCrashException
    """
    # Use the default both when timeout=None or the option is ommited.
    timeout = kwargs.pop('timeout', None) or 60
    context_id = kwargs.pop('context_id', None)
    user_gesture = kwargs.pop('user_gesture', None) or False
    promise = kwargs.pop('promise', None) or False
    expression = js_template.Render(expression, **kwargs)
    return self._EvaluateJavaScript(expression, context_id, timeout,
                                    user_gesture=user_gesture,
                                    promise=promise)

  def WaitForJavaScriptCondition(self, condition, **kwargs):
    """Wait for a JavaScript condition to become truthy.

    Example: runner.WaitForJavaScriptCondition('window.foo == 10');

    Args:
      condition: The JavaScript condition (provided as string).

    Optional keyword args:
      timeout: The number in seconds to wait for the condition to become
          True (default to 60).
      context_id: The id of an iframe where to execute the code; the main page
          has context_id=1, the first iframe context_id=2, etc.
      Additional keyword arguments provide values to be interpolated within
          the expression. See telemetry.util.js_template for details.

    Returns:
      The value returned by the JavaScript condition that got interpreted as
      true.

    Raises:
      py_utils.TimeoutException
      exceptions.EvaluateException
      exceptions.WebSocketException
      exceptions.DevtoolsTargetCrashException
    """
    # Use the default both when timeout=None or the option is ommited.
    timeout = kwargs.pop('timeout', None) or 60
    context_id = kwargs.pop('context_id', None)
    condition = js_template.Render(condition, **kwargs)

    def IsJavaScriptExpressionTrue():
      try:
        return self._EvaluateJavaScript(condition, context_id, timeout)
      except exceptions.DevtoolsTargetClosedException:
        # Ignore errors caused by navigation.
        return False

    try:
      return py_utils.WaitFor(IsJavaScriptExpressionTrue, timeout)
    except py_utils.TimeoutException as toe:
      # Try to make timeouts a little more actionable by dumping console output.
      debug_message = None
      try:
        debug_message = (
            'Console output:\n%s' %
            self.GetCurrentConsoleOutputBuffer())
      except Exception as e: # pylint: disable=broad-except
        debug_message = (
            'Exception thrown when trying to capture console output: %s' %
            repr(e))
      # Rethrow with the original stack trace for better debugging.
      six.reraise(
          py_utils.TimeoutException,
          py_utils.TimeoutException(
              'Timeout after %ss while waiting for JavaScript:'
              % timeout + condition + '\n' + repr(toe) + '\n' + debug_message
          ),
          sys.exc_info()[2]
      )

  def _HandleInspectorDomainNotification(self, res):
    if (res['method'] == 'Inspector.detached' and
        res.get('params', {}).get('reason', '') == 'replaced_with_devtools'):
      self._WaitForInspectorToGoAway()
      return
    if res['method'] == 'Inspector.targetCrashed':
      exception = exceptions.DevtoolsTargetCrashException(self.app)
      self._AddDebuggingInformation(exception)
      raise exception

  def _WaitForInspectorToGoAway(self):
    self._websocket.Disconnect()
    input('The connection to Chrome was lost to the inspector ui.\n'
          'Please close the inspector and press enter to resume '
          'Telemetry run...')
    raise exceptions.DevtoolsTargetCrashException(
        self.app, 'Devtool connection with the browser was interrupted due to '
        'the opening of an inspector.')

  def _HandleCastDomainNotification(self, msg):
    """Runs an inspector command that starts observing Cast-enabled sinks.

    Raises:
      exceptions.TimeoutException
      exceptions.DevtoolsTargetCrashException
    """
    if msg['method'] == 'Cast.sinksUpdated':
      self._cast_sink_list = msg['params'].get('sinks', [])
    elif msg['method'] == 'Cast.issueUpdated':
      self._cast_issue_message = msg['params']

  @_HandleInspectorWebSocketExceptions
  def _EvaluateJavaScript(self, expression, context_id, timeout,
                          user_gesture=False, promise=False):
    try:
      return self._runtime.Evaluate(expression, context_id, timeout,
                                    user_gesture, promise)
    except inspector_websocket.WebSocketException as e:
      logging.error('Renderer process hung; forcibly crashing it and '
                    'GPU process. Note that GPU process minidumps '
                    'require --enable-gpu-benchmarking browser arg.')
      # In Telemetry-based GPU tests, the GPU process is likely hung, and that's
      # the reason the renderer process is hung. Crash it so we can see a
      # symbolized minidump. From manual testing, it is important that this be
      # done before crashing the renderer process, or the GPU process's minidump
      # doesn't show up for some reason.
      self._runtime.CrashGpuProcess(timeout)
      # Assume the renderer's main thread is hung. Try to use DevTools to crash
      # the target renderer process (on its IO thread) so we get a minidump we
      # can symbolize.
      self._runtime.CrashRendererProcess(context_id, timeout)
      # Wait several seconds for these minidumps to be written, so the calling
      # code has a better chance of discovering them.
      time.sleep(5)
      raise e

  @_HandleInspectorWebSocketExceptions
  def CollectGarbage(self):
    self._page.CollectGarbage()
