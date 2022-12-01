# Copyright 2022 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""A wrapper for common cmd operations"""

from __future__ import absolute_import
import logging
import os
import subprocess


def GetAllCmdOutput(args, cwd=None, quiet=False):
  """Open a subprocess to execute a program and returns its output.

  Args:
    args: A string or a sequence of program arguments. The program to execute is
      the string or the first item in the args sequence.
    cwd: If not None, the subprocess's current directory will be changed to
      |cwd| before it's executed.

  Returns:
    Captures and returns the command's stdout.
    Prints the command's stderr to logger (which defaults to stdout).
  """
  if not quiet:
    logging.debug(' '.join(args) + ' ' + (cwd or ''))
  with open(os.devnull, 'w') as devnull:
    p = subprocess.Popen(args=args,
                         cwd=cwd,
                         stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE,
                         stdin=devnull)
    stdout, stderr = p.communicate()
    if not quiet:
      logging.debug(' > stdout=[%s], stderr=[%s]', stdout, stderr)
    return stdout, stderr

