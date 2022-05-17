# Copyright 2022 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import absolute_import
import logging
import six

import common

from autotest_lib.client.common_lib.cros.autotestChrome.py_utils import cloud_storage
from autotest_lib.client.common_lib.cros.autotestChrome.py_utils import exc_util
from autotest_lib.client.common_lib.cros.autotestChrome.core import exceptions
from autotest_lib.client.common_lib.cros.autotestChrome import decorators
from autotest_lib.client.common_lib.cros.autotestChrome.internal import app
from autotest_lib.client.common_lib.cros.autotestChrome.internal.backends import browser_backend
from autotest_lib.client.common_lib.cros.autotestChrome.internal.backends.chrome_inspector import tracing_backend
from autotest_lib.client.common_lib.cros.autotestChrome.internal.browser import extension_dict
from autotest_lib.client.common_lib.cros.autotestChrome.internal.browser import tab_list
from autotest_lib.client.common_lib.cros.autotestChrome.internal.browser import web_contents


class Browser(app.App):
  """A running browser instance that can be controlled in a limited way.

  To create a browser instance, use browser_finder.FindBrowser, e.g:

    possible_browser = browser_finder.FindBrowser(finder_options)
    with possible_browser.BrowserSession(
        finder_options.browser_options) as browser:
      # Do all your operations on browser here.

  See telemetry.internal.browser.possible_browser for more details and use
  cases.
  """
  def __init__(self, backend, platform_backend, startup_args,
               find_existing=False):
    super(Browser, self).__init__(app_backend=backend,
                                  platform_backend=platform_backend)
    try:
      self._browser_backend = backend
      self._platform_backend = platform_backend
      self._startup_args = startup_args
      self._tabs = tab_list.TabList(backend.tab_list_backend)
      self._browser_backend.SetBrowser(self)
      self._supports_inspecting_webui = False
      if find_existing:
        self._browser_backend.BindDevToolsClient()
      else:
        self._browser_backend.Start(startup_args)
      self._LogBrowserInfo()
    except Exception:
      self.DumpStateUponFailure()
      self.Close()
      raise

  @property
  def supports_extensions(self):
    return self._browser_backend.supports_extensions

  @property
  def tabs(self):
    return self._tabs

  @property
  @decorators.Cache
  def extensions(self):
    if not self.supports_extensions:
      raise browser_backend.ExtensionsNotSupportedException(
          'Extensions not supported')
    return extension_dict.ExtensionDict(self._browser_backend.extension_backend)

  def _LogBrowserInfo(self):
    trim_logs = self._browser_backend.browser_options.trim_logs
    logs = []
    logs.append(' Browser started (pid=%s).' % self._browser_backend.GetPid())
    logs.append(' OS: %s %s' % (
        self._platform_backend.platform.GetOSName(),
        self._platform_backend.platform.GetOSVersionName()))
    os_detail = self._platform_backend.platform.GetOSVersionDetailString()
    if os_detail:
      logs.append(' Detailed OS version: %s' % os_detail)
    system_info = self.GetSystemInfo()
    if system_info:
      if system_info.model_name:
        logs.append(' Model: %s' % system_info.model_name)
      if not trim_logs:
        if system_info.command_line:
          logs.append(' Browser command line: %s' % system_info.command_line)
      if system_info.gpu:
        for i, device in enumerate(system_info.gpu.devices):
          logs.append(' GPU device %d: %s' % (i, device))
        if not trim_logs:
          if system_info.gpu.aux_attributes:
            logs.append(' GPU Attributes:')
            for k, v in sorted(six.iteritems(system_info.gpu.aux_attributes)):
              logs.append('  %-20s: %s' % (k, v))
          if system_info.gpu.feature_status:
            logs.append(' Feature Status:')
            for k, v in sorted(six.iteritems(system_info.gpu.feature_status)):
              logs.append('  %-20s: %s' % (k, v))
          if system_info.gpu.driver_bug_workarounds:
            logs.append(' Driver Bug Workarounds:')
            for workaround in system_info.gpu.driver_bug_workarounds:
              logs.append('  %s' % workaround)
      else:
        logs.append(' No GPU devices')
    else:
      logging.warning('System info not supported')
    logging.info('Browser information:\n%s', '\n'.join(logs))

  @exc_util.BestEffort
  def Close(self):
    """Closes this browser."""
    try:
      if self._browser_backend.IsBrowserRunning():
        logging.info(
            'Closing browser (pid=%s) ...', self._browser_backend.GetPid())

      if self._browser_backend.supports_uploading_logs:
        try:
          self._browser_backend.UploadLogsToCloudStorage()
        except cloud_storage.CloudStorageError as e:
          logging.error('Cannot upload browser log: %s' % str(e))
    finally:
      self._browser_backend.Close()
      if self._browser_backend.IsBrowserRunning():
        logging.error(
            'Browser is still running (pid=%s).'
            , self._browser_backend.GetPid())
      else:
        logging.info('Browser is closed.')

  def GetSystemInfo(self):
    """Returns low-level information about the system, if available.

       See the documentation of the SystemInfo class for more details."""
    return self._browser_backend.GetSystemInfo()

  @property
  def supports_memory_dumping(self):
    return self._browser_backend.supports_memory_dumping

  def DumpMemory(self, timeout=None):
    try:
      return self._browser_backend.DumpMemory(timeout=timeout)
    except tracing_backend.TracingUnrecoverableException:
      logging.exception('Failed to record memory dump due to exception:')
      # Re-raise as an AppCrashException to obtain further debug information
      # about the browser state.
      raise exceptions.AppCrashException(
          app=self, msg='Browser failed to record memory dump.')

  @property
  def supports_inspecting_webui(self):
    '''If this flag is enabled, any inspectable targets with chrome:// will
    pass through browser.tabs

    This is mainly used for inspecting non-content area browser WebUI.
    (e.g. Tab Search, WebUI TabStrip)
    '''
    return self._supports_inspecting_webui

  @supports_inspecting_webui.setter
  def supports_inspecting_webui(self, value):
    self._supports_inspecting_webui = value
