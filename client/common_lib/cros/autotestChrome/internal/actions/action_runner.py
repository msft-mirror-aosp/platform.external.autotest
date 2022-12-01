# Copyright 2022 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import division
from __future__ import absolute_import
import logging
import time
import six

import six.moves.urllib.parse # pylint: disable=import-error
from six.moves import input # pylint: disable=redefined-builtin

import common

from autotest_lib.client.common_lib.cros.autotestChrome.core import exceptions
from autotest_lib.client.common_lib.cros.autotestChrome.py_trace_event import trace_event


# Time to wait in seconds before requesting a memory dump in deterministic
# mode, thus allowing metric values to stabilize a bit.
_MEMORY_DUMP_WAIT_TIME = 3

# Time to wait in seconds after forcing garbage collection to allow its
# effects to propagate. Experimentally determined on an Android One device
# that Java Heap garbage collection can take ~5 seconds to complete.
_GARBAGE_COLLECTION_PROPAGATION_TIME = 6


if six.PY2:
  ActionRunnerBase = object
else:
  ActionRunnerBase = six.with_metaclass(trace_event.TracedMetaClass, object)

class ActionRunner(ActionRunnerBase):

  if six.PY2:
    __metaclass__ = trace_event.TracedMetaClass

  def __init__(self, tab, skip_waits=False):
    self._tab = tab
    self._skip_waits = skip_waits