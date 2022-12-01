# Copyright 2022 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
from __future__ import absolute_import

import socket

import common

# pylint: disable=unused-import
from autotest_lib.client.common_lib.cros.autotestChrome.websocket._core import create_connection as _create_connection

def CreateConnection(*args, **kwargs):
  sockopt = kwargs.get('sockopt', [])

  # By default, we set SO_REUSEADDR on all websockets used by Telemetry.
  # This prevents spurious address in use errors on Windows.
  #
  # TODO(tonyg): We may want to set SO_NODELAY here as well.
  sockopt.append((socket.SOL_SOCKET, socket.SO_REUSEADDR, 1))

  kwargs['sockopt'] = sockopt
  return _create_connection(*args, **kwargs)
