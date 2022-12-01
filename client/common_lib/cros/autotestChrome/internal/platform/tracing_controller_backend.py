# Copyright 2022 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import absolute_import
import contextlib
import gc
import logging
import os
import sys
import traceback
import uuid

import common

from autotest_lib.client.common_lib.cros.autotestChrome.py_trace_event import trace_event
from autotest_lib.client.common_lib.cros.autotestChrome.internal.platform.tracing_agent import chrome_report_events_tracing_agent
from autotest_lib.client.common_lib.cros.autotestChrome.internal.platform.tracing_agent import chrome_return_as_stream_tracing_agent
from autotest_lib.client.common_lib.cros.autotestChrome.internal.platform.tracing_agent import chrome_tracing_agent
from autotest_lib.client.common_lib.cros.autotestChrome.internal.platform.tracing_agent import cpu_tracing_agent
from autotest_lib.client.common_lib.cros.autotestChrome.internal.platform.tracing_agent import display_tracing_agent
from autotest_lib.client.common_lib.cros.autotestChrome.internal.platform.tracing_agent import telemetry_tracing_agent
from autotest_lib.client.common_lib.cros.autotestChrome.tracing.trace_data import trace_data


# Note: TelemetryTracingAgent should be first so that we can record debug
# trace events when the other agents start/stop.
_TRACING_AGENT_CLASSES = (
    telemetry_tracing_agent.TelemetryTracingAgent,
    chrome_report_events_tracing_agent.ChromeReportEventsTracingAgent,
    chrome_return_as_stream_tracing_agent.ChromeReturnAsStreamTracingAgent,
    cpu_tracing_agent.CpuTracingAgent,
    display_tracing_agent.DisplayTracingAgent
)

_EXPERIMENTAL_TRACING_AGENTS = (
    telemetry_tracing_agent.TelemetryTracingAgent
)


def _GenerateClockSyncId():
  return str(uuid.uuid4())


@contextlib.contextmanager
def _DisableGarbageCollection():
  try:
    gc.disable()
    yield
  finally:
    gc.enable()


class _TraceDataDiscarder(object):
  """A do-nothing data builder that just discards trace data.

  TODO(crbug.com/928278): This should be moved as a "discarding mode" in
  TraceDataBuilder itself.
  """
  def OpenTraceHandleFor(self, part, suffix):
    del part, suffix  # Unused.
    return open(os.devnull, 'wb')

  def AddTraceFor(self, part, data, allow_unstructured=False):
    assert not allow_unstructured
    del part  # Unused.
    del data  # Unused.

  def RecordTraceDataException(self):
    logging.info('Ignoring exception while flushing to TraceDataDiscarder:\n%s',
                 ''.join(traceback.format_exception(*sys.exc_info())))


class _TracingState(object):

  def __init__(self, config, timeout):
    self._builder = trace_data.TraceDataBuilder()
    self._config = config
    self._timeout = timeout

  @property
  def builder(self):
    return self._builder

  @property
  def config(self):
    return self._config

  @property
  def timeout(self):
    return self._timeout


class TracingControllerBackend(object):
  def __init__(self, platform_backend):
    self._platform_backend = platform_backend
    self._current_state = None
    self._active_agents_instances = []
    self._is_tracing_controllable = True

  @property
  def is_tracing_running(self):
    return self._current_state is not None

  @property
  def is_chrome_tracing_running(self):
    return self._GetActiveChromeTracingAgent() is not None

  @property
  def current_state(self):
    return self._current_state

  def _GetActiveChromeTracingAgent(self):
    if not self.is_tracing_running:
      return None
    if not self._current_state.config.enable_chrome_trace:
      return None
    for agent in self._active_agents_instances:
      if isinstance(agent, chrome_tracing_agent.ChromeTracingAgent):
        return agent
    return None

  def GetChromeTraceConfig(self):
    agent = self._GetActiveChromeTracingAgent()
    if agent:
      return agent.trace_config
    return None

  def GetChromeTraceConfigFile(self):
    agent = self._GetActiveChromeTracingAgent()
    if agent:
      return agent.trace_config_file
    return None
