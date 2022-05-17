# Copyright 2022 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import absolute_import
import re

import common

from autotest_lib.client.common_lib.cros.autotestChrome.internal.browser import web_contents


def UrlToExtensionId(url):
  return re.match(r"(chrome-extension://)([^/]+)", url).group(2)


class ExtensionPage(web_contents.WebContents):
  """Represents an extension page in the browser"""

  def __init__(self, inspector_backend):
    super(ExtensionPage, self).__init__(inspector_backend)
    self.url = inspector_backend.url
    self.extension_id = UrlToExtensionId(self.url)
