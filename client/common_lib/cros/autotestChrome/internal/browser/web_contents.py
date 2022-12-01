# Copyright 2022 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import absolute_import
import os
import six

import common

from autotest_lib.client.common_lib.cros.autotestChrome.core import exceptions
from autotest_lib.client.common_lib.cros.autotestChrome.py_trace_event import trace_event

DEFAULT_WEB_CONTENTS_TIMEOUT = 90

class ServiceWorkerState(object):
  # These strings should exactly match strings used in
  # wait_for_serviceworker_registration.js
  # The page did not call register().
  NOT_REGISTERED = 'not registered'
  # The page called register(), but there is not an activated service worker.
  INSTALLING = 'installing'
  # The page called register(), and has an activated service worker.
  ACTIVATED = 'activated'

# TODO(achuith, dtu, nduca): Add unit tests specifically for WebContents,
# independent of Tab.
class WebContents(six.with_metaclass(trace_event.TracedMetaClass, object)):

  """Represents web contents in the browser"""
  def __init__(self, inspector_backend):
    self._inspector_backend = inspector_backend

    with open(os.path.join(
        os.path.dirname(__file__),
        'network_quiescence.js')) as f:
      self._quiescence_js = f.read()

    with open(os.path.join(
        os.path.dirname(__file__),
        'wait_for_serviceworker_registration.js')) as f:
      self._wait_for_serviceworker_js = f.read()

    with open(os.path.join(
        os.path.dirname(__file__),
        'wait_for_frame.js')) as f:
      self._wait_for_frame_js = f.read()

    # An incrementing ID used to query frame timing javascript. Using a new id
    # with each request ensures that previously timed-out wait for frame
    # requests don't impact new requests.
    self._wait_for_frame_id = 0

  def ExecuteJavaScript(self, *args, **kwargs):
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
      exceptions.EvaluationException
      exceptions.WebSocketException
      exceptions.DevtoolsTargetCrashException
    """
    return self._inspector_backend.ExecuteJavaScript(*args, **kwargs)

  def EvaluateJavaScript(self, *args, **kwargs):
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
      Additional keyword arguments provide values to be interpolated within
          the expression. See telemetry.util.js_template for details.

    Raises:
      py_utils.TimeoutException
      exceptions.EvaluationException
      exceptions.WebSocketException
      exceptions.DevtoolsTargetCrashException
    """
    return self._inspector_backend.EvaluateJavaScript(*args, **kwargs)

  def WaitForJavaScriptCondition(self, *args, **kwargs):
    """Wait for a JavaScript condition to become true.

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

    Raises:
      py_utils.TimeoutException
      exceptions.EvaluationException
      exceptions.WebSocketException
      exceptions.DevtoolsTargetCrashException
    """
    return self._inspector_backend.WaitForJavaScriptCondition(*args, **kwargs)
    