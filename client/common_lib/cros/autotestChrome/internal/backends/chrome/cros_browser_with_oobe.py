# Copyright 2022 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import absolute_import

import common

from autotest_lib.client.common_lib.cros.autotestChrome.internal.backends.chrome import cros_browser_backend
from autotest_lib.client.common_lib.cros.autotestChrome.internal.browser import browser


class CrOSBrowserWithOOBE(browser.Browser):
  """Cros-specific browser."""
  def __init__(self, backend, platform_backend, startup_args):
    assert isinstance(backend, cros_browser_backend.CrOSBrowserBackend)
    super(CrOSBrowserWithOOBE, self).__init__(
        backend, platform_backend, startup_args)
