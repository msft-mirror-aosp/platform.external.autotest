# Copyright 2022 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# A singleton map from platform backends to maps of uniquely-identifying
# remote port (which may be the same as local port) to DevToolsClientBackend.
# There is no guarantee that the devtools agent is still alive.

from __future__ import absolute_import

_platform_backends_to_devtools_clients_maps = {}


def RegisterDevToolsClient(devtools_client_backend):
  """Register DevTools client

  This should only be called from DevToolsClientBackend when it is initialized.
  """
  remote_port = str(devtools_client_backend.remote_port)
  platform_clients = _platform_backends_to_devtools_clients_maps.setdefault(
      devtools_client_backend.platform_backend, {})
  platform_clients[remote_port] = devtools_client_backend
