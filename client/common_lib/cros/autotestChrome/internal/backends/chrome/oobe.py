# Copyright 2022 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import absolute_import
import logging

import common

from autotest_lib.client.common_lib.cros.autotestChrome.core import exceptions
from autotest_lib.client.common_lib.cros.autotestChrome.internal.browser import web_contents
from autotest_lib.client.common_lib.cros.autotestChrome.internal.backends.chrome_inspector.inspector_websocket import \
    WebSocketException
from autotest_lib.client.common_lib.cros.autotestChrome import py_utils


class Oobe(web_contents.WebContents):
  def __init__(self, inspector_backend):
    super(Oobe, self).__init__(inspector_backend)

  def _ExecuteOobeApi(self, api, *args):
    logging.info('Invoking %s', api)
    self.WaitForJavaScriptCondition(
        "typeof Oobe == 'function' && Oobe.readyForTesting", timeout=120)

    if self.EvaluateJavaScript(
        "typeof {{ @api }} == 'undefined'", api=api):
      raise exceptions.LoginException('%s js api missing' % api)

    # Example values:
    #   |api|:    'doLogin'
    #   |args|:   ['username', 'pass', True]
    #   Executes: 'doLogin("username", "pass", true)'
    self.ExecuteJavaScript('{{ @f }}({{ *args }})', f=api, args=args)

  def NavigateGuestLogin(self):
    """Logs in as guest."""
    self._ExecuteOobeApi('Oobe.guestLoginForTesting')

  def NavigateFakeLogin(self, username, password, gaia_id,
                        enterprise_enroll=False):
    """Fake user login."""
    self._ExecuteOobeApi('Oobe.loginForTesting', username, password, gaia_id,
                         enterprise_enroll)
    if enterprise_enroll:
      # Oobe context recreated after the enrollment (crrev.com/c/2144279).
      py_utils.WaitFor(lambda: not self.IsAlive(), 60)

