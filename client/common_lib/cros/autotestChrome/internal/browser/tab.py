# Copyright 2022 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import absolute_import

import common

from autotest_lib.client.common_lib.cros.autotestChrome.internal.actions import action_runner
from autotest_lib.client.common_lib.cros.autotestChrome.internal.browser import web_contents

DEFAULT_TAB_TIMEOUT = 60


class Tab(web_contents.WebContents):
  """Represents a tab in the browser

  The important parts of the Tab object are in the runtime and page objects.
  E.g.:
      # Navigates the tab to a given url.
      tab.Navigate('http://www.google.com/')

      # Evaluates 1+1 in the tab's JavaScript context.
      tab.Evaluate('1+1')
  """
  def __init__(self, inspector_backend, tab_list_backend, browser):
    super(Tab, self).__init__(inspector_backend)
    self._tab_list_backend = tab_list_backend
    self._browser = browser
    self._action_runner = action_runner.ActionRunner(self)