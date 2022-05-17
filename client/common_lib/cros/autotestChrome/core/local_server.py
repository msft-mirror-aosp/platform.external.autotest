# Copyright 2022 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# TODO(aiolos): this should be moved to catapult/base after the repo move.
# It is used by tracing in tvcm/browser_controller.
from __future__ import print_function
from __future__ import absolute_import
import collections
import json
import logging
import os
import re
import subprocess
import sys
import time
import six

import common

from autotest_lib.client.common_lib.cros.autotestChrome.core import util

NamedPort = collections.namedtuple('NamedPort', ['name', 'port'])


class LocalServerBackend(object):

  def __init__(self):
    pass


class LocalServer(object):

  def __init__(self, server_backend_class):
    assert LocalServerBackend in server_backend_class.__bases__
    server_module_name = server_backend_class.__module__
    assert server_module_name in sys.modules, \
        'The server class\' module must be findable via sys.modules'
    assert getattr(sys.modules[server_module_name],
                   server_backend_class.__name__), \
        'The server class must getattrable from its __module__ by its __name__'

    self._server_backend_class = server_backend_class
    self._subprocess = None
    self._devnull = None
    self._local_server_controller = None
    self.host_ip = None
    self.port = None


class LocalServerController(object):
  """Manages the list of running servers

  This class manages the running servers, but also provides an isolation layer
  to prevent LocalServer subclasses from accessing the browser backend directly.

  """

  def __init__(self, platform_backend):
    self._platform_backend = platform_backend
    self._local_servers_by_class = {}
    self.host_ip = self._platform_backend.forwarder_factory.host_ip

  def Close(self):
    # TODO(crbug.com/953365): This is a terrible infinite loop scenario
    # and we should fix it.
    while len(self._local_servers_by_class):
      server = next(six.itervalues(self._local_servers_by_class))
      try:
        server.Close()
      except Exception: # pylint: disable=broad-except
        import traceback
        traceback.print_exc()
