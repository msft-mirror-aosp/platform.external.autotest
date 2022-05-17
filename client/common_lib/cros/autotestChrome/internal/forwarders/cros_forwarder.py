# Copyright 2022 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import absolute_import

import common

from autotest_lib.client.common_lib.cros.autotestChrome.core import util
from autotest_lib.client.common_lib.cros.autotestChrome.internal import forwarders
from autotest_lib.client.common_lib.cros.autotestChrome.internal.forwarders import do_nothing_forwarder


class CrOsForwarderFactory(forwarders.ForwarderFactory):

  def __init__(self, cri):
    super(CrOsForwarderFactory, self).__init__()
    self._cri = cri

  def Create(self, local_port, remote_port, reverse=False):
    if self._cri.local:
      return do_nothing_forwarder.DoNothingForwarder(local_port, remote_port)
    else:
      return CrOsSshForwarder(
          self._cri, local_port, remote_port, port_forward=not reverse)
