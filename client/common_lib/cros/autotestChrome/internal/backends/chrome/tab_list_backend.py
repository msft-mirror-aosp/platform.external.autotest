# Copyright 2022 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import absolute_import

import common

from autotest_lib.client.common_lib.cros.autotestChrome.core import exceptions
from autotest_lib.client.common_lib.cros.autotestChrome.internal.backends.chrome_inspector import inspector_backend_list
from autotest_lib.client.common_lib.cros.autotestChrome.internal.browser import tab


class TabUnexpectedResponseException(exceptions.DevtoolsTargetCrashException):
  pass


class TabListBackend(inspector_backend_list.InspectorBackendList):
  """A dynamic sequence of tab.Tabs in UI order."""

  def __init__(self, browser_backend):
    super(TabListBackend, self).__init__(browser_backend)

  def New(self, in_new_window, timeout, url):
    """Makes a new tab of specified type.

    Args:
      in_new_window: If True, opens the tab in a popup window. Otherwise, opens
        in current window.
      timeout: Seconds to wait for the new tab request to complete.

    Returns:
      The Tab object of the successfully created tab.

    Raises:
      devtools_http.DevToolsClientConnectionError
      exceptions.EvaluateException: for the current implementation of opening
        a tab in a new window.
    """
    if not self._browser_backend.supports_tab_control:
      raise NotImplementedError("Browser doesn't support tab control.")
    response = self._browser_backend.devtools_client.RequestNewTab(
        timeout, in_new_window=in_new_window, url=url)
    if 'error' in response:
      raise TabUnexpectedResponseException(
          app=self._browser_backend.browser,
          msg='Received response: %s' % response)
    try:
      return self.GetBackendFromContextId(response['result']['targetId'])
    except KeyError:
      raise TabUnexpectedResponseException(
          app=self._browser_backend.browser,
          msg='Received response: %s' % response)

  def ShouldIncludeContext(self, context):
    if 'type' in context:
      return (context['type'] == 'page' or
              context['url'] == 'chrome://media-router/' or
              (self._browser_backend.browser.supports_inspecting_webui and
               context['url'].startswith('chrome://')))
    # TODO: For compatibility with Chrome before r177683.
    # This check is not completely correct, see crbug.com/190592.
    return not context['url'].startswith('chrome-extension://')

  def CreateWrapper(self, inspector_backend):
    return tab.Tab(inspector_backend, self, self._browser_backend.browser)