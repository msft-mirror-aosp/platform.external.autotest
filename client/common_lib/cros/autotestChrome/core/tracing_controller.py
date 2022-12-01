# Copyright 2022 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

class TracingController(object):

  def __init__(self, tracing_controller_backend):
    """Provides control of the tracing systems supported by Telemetry."""
    self._tracing_controller_backend = tracing_controller_backend