# Copyright 2022 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import division
from __future__ import absolute_import
import logging
import os
import re
import subprocess
from threading import Timer

import common

from autotest_lib.client.common_lib.cros.autotestChrome.internal.platform import tracing_agent
from autotest_lib.client.common_lib.cros.autotestChrome.tracing.trace_data import trace_data


def _ParsePsProcessString(line):
  """Parses a process line from the output of `ps`.

  Example of `ps` command output:
  '3.4 8.0 31887 31447 com.app.Webkit'
  """
  token_list = line.strip().decode('utf-8').split()
  if len(token_list) < 5:
    raise ValueError('Line has too few tokens: %s.' % token_list)

  return {
      'pCpu': float(token_list[0]),
      'pMem': float(token_list[1]),
      'pid': int(token_list[2]),
      'ppid': int(token_list[3]),
      'name': ' '.join(token_list[4:])
  }


class ProcessCollector(object):
  def _GetProcessesAsStrings(self):
    """Returns a list of strings, each of which contains info about a
    process.
    """
    raise NotImplementedError

  # pylint: disable=unused-argument
  def _ParseProcessString(self, proc_string):
    """Parses an individual process string returned by _GetProcessesAsStrings().

    Returns:
      A dictionary containing keys of 'pid' (an integer process ID), 'ppid' (an
      integer parent process ID), 'name' (a string for the process name), 'pCpu'
      (a float for the percent CPU load incurred by the process), and 'pMem' (a
      float for the percent memory load caused by the process).
    """
    raise NotImplementedError

  def Init(self):
    """Performs any required initialization before starting tracing."""
    pass

  def GetProcesses(self):
    """Fetches the top processes returned by top command.

    Returns:
      A list of dictionaries, each containing 'pid' (an integer process ID),
      'ppid' (an integer parent process ID), 'name (a string for the process
      name), pCpu' (a float for the percent CPU load incurred by the process),
      and 'pMem' (a float for the percent memory load caused by the process).
    """
    proc_strings = self._GetProcessesAsStrings()
    return [
        self._ParseProcessString(proc_string) for proc_string in proc_strings
    ]


class LinuxProcessCollector(ProcessCollector):
  """Class for collecting information about processes on Linux.

  Example of Linux command output:
  '3.4 8.0 31887 31447 com.app.Webkit'
  """
  _SHELL_COMMAND = [
      'ps',
      '-a', # Include processes that aren't session leaders.
      '-x', # List all processes, even those not owned by the user.
      '-o', # Show the output in the specified format.
      'pcpu,pmem,pid,ppid,cmd'
  ]

  def _GetProcessesAsStrings(self):
    # Skip the header row and strip the trailing newline.
    return subprocess.check_output(self._SHELL_COMMAND).strip().split(b'\n')[1:]

  def _ParseProcessString(self, proc_string):
    return _ParsePsProcessString(proc_string)
