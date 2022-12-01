# Copyright 2022 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Starts a GSCDevboardHost manually for local testing."""

import logging
import os

import common
from autotest_lib.server.hosts import gsc_devboard_host

# Start service per env vars DOCKER_HOST, DEBUGGER_SERIAL, GSC_SERIAL, DEVBOARDSVC_PORT
logging.basicConfig(level=logging.INFO)
e = os.environ

h = gsc_devboard_host.GSCDevboardHost('localhost')
h._initialize('',
              service_debugger_serial=e.get('DEBUGGER_SERIAL'),
              service_gsc_serial=e.get('GSC_SERIAL'),
              service_port=e.get('DEVBOARDSVC_PORT',
                                 gsc_devboard_host.DEFAULT_SERVICE_PORT))
h.start_service()
logging.info("Service started, gsc service endpoint at %s:%s", h.service_ip,
             h.service_port)
