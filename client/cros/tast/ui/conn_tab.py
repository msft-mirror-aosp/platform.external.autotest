# Lint as: python2, python3
# Copyright 2022 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import logging

from autotest_lib.client.cros import tast
from autotest_lib.client.cros.tast.ui import conn_service_pb2


def new_tab(conn_service, url):
    """
    Opens a new tab with the provided url and returns a new ConnTab object.
    """
    response = conn_service.NewConn(conn_service_pb2.NewConnRequest(
                url = url
            ))
    return ConnTab(conn_service, response.id)


class ConnTab():
    """Wraps Conn to act as autotest Tab class."""

    def __init__(self, conn_service, conn_id):
        self._conn = tast.Conn(conn_service, conn_id)

    def ActivateTarget(self):
        """Calls ActivateTarget on tast.Conn."""
        self._conn.ActivateTarget()

    def Navigate(self, url):
        """Calls Navigate on tast.Conn."""
        self._conn.Navigate(url)

    def WaitForDocumentReadyStateToBeComplete(self):
        """Waits for document ready state to be complete."""
        self._conn.WaitForExpr(
            'document.readyState == "complete"',
            90, # DEFAULT_WEB_CONTENTS_TIMEOUT
            True)

    def WaitForJavaScriptCondition(self, condition, timeout):
        """
        Args:
            condition: The JavaScript condition provided as a string.
            timeout: The number in seconds to wait for the condition to become
                True.
        """
        self._conn.WaitForExpr(condition, int(timeout), True)

    def EvaluateJavaScript(self, expression):
        """Calls Eval on tast.Conn."""
        return self._conn.Eval(expression)

    def IsAlive(self):
        """Checks if connection is alive."""
        try:
            return self._conn.Eval('true')
        except:
            logging.error(
                'An error occured while calling Conn.Eval(). This could be '
                'because the tab has crashed.')
            return False
