# Copyright 2022 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import absolute_import
import logging
import os
import pprint
import shlex
import socket

import common

from autotest_lib.client.common_lib.cros.autotestChrome.core import exceptions
from autotest_lib.client.common_lib.cros.autotestChrome import decorators
from autotest_lib.client.common_lib.cros.autotestChrome.internal.backends import browser_backend
from autotest_lib.client.common_lib.cros.autotestChrome.internal.backends.chrome import extension_backend
from autotest_lib.client.common_lib.cros.autotestChrome.internal.backends.chrome import tab_list_backend
from autotest_lib.client.common_lib.cros.autotestChrome.internal.backends.chrome_inspector import devtools_client_backend
from autotest_lib.client.common_lib.cros.autotestChrome.internal.backends.chrome_inspector import inspector_websocket
from autotest_lib.client.common_lib.cros.autotestChrome.internal.browser import web_contents
from autotest_lib.client.common_lib.cros.autotestChrome import py_utils


class ChromeBrowserBackend(browser_backend.BrowserBackend):
  """An abstract class for chrome browser backends. Provides basic functionality
  once a remote-debugger port has been established."""
  # It is OK to have abstract methods. pylint: disable=abstract-method

  def __init__(self, platform_backend, browser_options,
               browser_directory, profile_directory,
               supports_extensions, supports_tab_control, build_dir=None,
               enable_tracing=True):
    """
    Args:
      platform_backend: The platform_backend.PlatformBackend instance to use.
      browser_options: The browser_options.BrowserOptions instance to use.
      browser_directory: A string containing a path to the directory where the
          the browser is installed. This is typically the directory containing
          the browser executable, but not guaranteed.
      profile_directory: A string containing a path to the directory to store
          browser profile information in.
      supports_extensions: A boolean indicating whether the browser supports
          extensions.
      supports_tab_control: A boolean indicating whether the browser supports
          the concept of tabs.
      build_dir: A string containing a path to the directory that the browser
          was built in, for finding debug artifacts. Can be None if the browser
          was not locally built, or the directory otherwise cannot be
          determined.
      enable_tracing: Defines if a tracing_client is created.
    """
    super(ChromeBrowserBackend, self).__init__(
        platform_backend=platform_backend,
        browser_options=browser_options,
        supports_extensions=supports_extensions,
        tab_list_backend=tab_list_backend.TabListBackend)
    self._browser_directory = browser_directory
    self._enable_tracing = enable_tracing
    self._profile_directory = profile_directory
    self._supports_tab_control = supports_tab_control
    self._build_dir = build_dir

    self._devtools_client = None
    self._ui_devtools_client = None

    self._extensions_to_load = browser_options.extensions_to_load
    if not supports_extensions and len(self._extensions_to_load) > 0:
      raise browser_backend.ExtensionsNotSupportedException(
          'Extensions are not supported on the selected browser')

    if self.browser_options.dont_override_profile:
      logging.warning('Not overriding profile. This can cause unexpected '
                      'effects due to profile-specific settings, such as '
                      'about:flags settings, cookies, and extensions.')

  @property
  def devtools_client(self):
    return self._devtools_client

  @property
  @decorators.Cache
  def extension_backend(self):
    if not self.supports_extensions:
      return None
    return extension_backend.ExtensionBackendDict(self)

  def HasDevToolsConnection(self):
    return self._devtools_client and self._devtools_client.IsAlive()

  def _GetDevToolsClient(self):
    # If the agent does not appear to be ready, it could be because we got the
    # details of an older agent that no longer exists. It's thus important to
    # re-read and update the port and target on each retry.
    try:
      devtools_port, browser_target = self._FindDevToolsPortAndTarget()
    except EnvironmentError:
      return None  # Port information not ready, will retry.

    return devtools_client_backend.GetDevToolsBackEndIfReady(
        devtools_port=devtools_port,
        app_backend=self,
        browser_target=browser_target,
        enable_tracing=self._enable_tracing)

  def BindDevToolsClient(self):
    """Find an existing DevTools agent and bind this browser backend to it."""
    if self._devtools_client:
      # In case we are launching a second browser instance (as is done by
      # the CrOS backend), ensure that the old devtools_client is closed,
      # otherwise re-creating it will fail.
      self._devtools_client.Close()
      self._devtools_client = None

    try:
      self._devtools_client = py_utils.WaitFor(
          self._GetDevToolsClient,
          timeout=self.browser_options.browser_startup_timeout)
    except (py_utils.TimeoutException, exceptions.ProcessGoneException) as e:
      if not self.IsBrowserRunning():
        logging.exception(e)  # crbug.com/940075
        raise exceptions.BrowserGoneException(self.browser, e)
      raise exceptions.BrowserConnectionGoneException(self.browser, e)

  def _WaitForExtensionsToLoad(self):
    """ Wait for all extensions to load.
    Be sure to check whether the browser_backend supports_extensions before
    calling this method.
    """
    assert self._supports_extensions
    assert self._devtools_client, (
        'Waiting for extensions required devtool client to be initiated first')
    try:
      py_utils.WaitFor(self._AllExtensionsLoaded, timeout=60)
    except py_utils.TimeoutException:
      logging.error('ExtensionsToLoad: ' + repr(
          [e.extension_id for e in self._extensions_to_load]))
      logging.error('Extension list: ' + pprint.pformat(
          self.extension_backend, indent=4))
      raise

  def _AllExtensionsLoaded(self):
    # Extension pages are loaded from an about:blank page,
    # so we need to check that the document URL is the extension
    # page in addition to the ready state.
    for e in self._extensions_to_load:
      try:
        extension_objects = self.extension_backend[e.extension_id]
      except KeyError:
        return False
      for extension_object in extension_objects:
        try:
          res = extension_object.EvaluateJavaScript(
              """
              document.URL.lastIndexOf({{ url }}, 0) == 0 &&
              (document.readyState == 'complete' ||
               document.readyState == 'interactive')
              """,
              url='chrome-extension://%s/' % e.extension_id)
        except exceptions.EvaluateException:
          # If the inspected page is not ready, we will get an error
          # when we evaluate a JS expression, but we can just keep polling
          # until the page is ready (crbug.com/251913).
          res = None

        # TODO(tengs): We don't have full support for getting the Chrome
        # version before launch, so for now we use a generic workaround to
        # check for an extension binding bug in old versions of Chrome.
        # See crbug.com/263162 for details.
        if res and extension_object.EvaluateJavaScript(
            'chrome.runtime == null'):
          extension_object.Reload()
        if not res:
          return False
    return True

  @property
  def supports_tab_control(self):
    return self._supports_tab_control

  def Close(self):
    # If Chrome tracing is running, flush the trace before closing the browser.
    tracing_backend = self._platform_backend.tracing_controller_backend
    if tracing_backend.is_chrome_tracing_running:
      tracing_backend.FlushTracing()

    if self._devtools_client:
      if "ENSURE_CLEAN_CHROME_SHUTDOWN" in os.environ:
        # Forces a clean shutdown by sending a command to close the browser via
        # the devtools client. Uses a long timeout as a clean shutdown can
        # sometime take a long time to complete.
        self._devtools_client.CloseBrowser()
        py_utils.WaitFor(lambda: not self.IsBrowserRunning(), 300)
      self._devtools_client.Close()
      self._devtools_client = None

    if self._ui_devtools_client:
      self._ui_devtools_client.Close()
      self._ui_devtools_client = None


  def GetSystemInfo(self):
    try:
      return self.devtools_client.GetSystemInfo()
    except (inspector_websocket.WebSocketException, socket.error) as e:
      if not self.IsBrowserRunning():
        raise exceptions.BrowserGoneException(self.browser, e)
      raise exceptions.BrowserConnectionGoneException(self.browser, e)