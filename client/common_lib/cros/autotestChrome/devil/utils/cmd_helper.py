# Copyright (c) 2022 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""A wrapper for subprocess to make calling shell commands easier."""

import codecs
import logging
import os
import pipes
import select
import signal
import string
import subprocess
import sys
import time
import six

logger = logging.getLogger(__name__)

_SafeShellChars = frozenset(string.ascii_letters + string.digits + '@%_-+=:,./')


def SingleQuote(s):
  """Return an shell-escaped version of the string using single quotes.

  Reliably quote a string which may contain unsafe characters (e.g. space,
  quote, or other special characters such as '$').

  The returned value can be used in a shell command line as one token that gets
  to be interpreted literally.

  Args:
    s: The string to quote.

  Return:
    The string quoted using single quotes.
  """
  return pipes.quote(s)
