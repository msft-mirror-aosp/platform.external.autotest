# Copyright (c) 2010 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Routines for printing boot time performance test results."""

from __future__ import division
import resultset


def PrintRawData(reader, dirlist, keytype, keylist):
  """Print 'bootperf' results in "raw data" format.

  @param reader Function for reading results from results
                directories.
  @param dirlist List of directories to read results from.
  @param keytype Selector specifying the desired key set (e.g.
                 the boot time keyset, the disk stats keyset, etc.)
  @param keylist List of event keys to be printed in the report.

  """
  for dir_ in dirlist:
    results = reader(dir_)
    keyset = results.KeySet(keytype)
    for i in range(0, keyset.num_iterations):
      if len(dirlist) > 1:
        line = "{} {:3d}".format(results.name, i)
      else:
        line = "{:3d}".format(i)
      if keylist is not None:
        markers = keylist
      else:
        markers = keyset.markers
      for stat in markers:
        (_, v) = keyset.PrintableStatistic(keyset.RawData(stat)[i])
        line += " {!s:>5}".format(v)
      print(line)


def PrintStatisticsSummary(reader, dirlist, keytype, keylist):
  """Print 'bootperf' results in "summary of averages" format.

  @param reader Function for reading results from results
                directories.
  @param dirlist List of directories to read results from.
  @param keytype Selector specifying the desired key set (e.g.
                 the boot time keyset, the disk stats keyset, etc.)
  @param keylist List of event keys to be printed in the report.

  """
  if (keytype == resultset.TestResultSet.BOOTTIME_KEYSET or
      keytype == resultset.TestResultSet.FIRMWARE_KEYSET):
    header = "{:>5} {:>3}  {:>5} {:>3}  {}".format(
        "time", "s%", "dt", "s%", "event")
    tformat = "{:>5} {:2d}%  {:>5} {:2d}%  {}"
  else:
    header = "{:>7} {:>3}  {:>7} {:>3}  {}".format(
        "diskrd", "s%", "delta", "s%", "event")
    tformat = "{:>7} {:2d}%  {:>7} {:2d}%  {}"
  havedata = False
  for dir_ in dirlist:
    results = reader(dir_)
    keyset = results.KeySet(keytype)
    if keylist is not None:
      markers = keylist
    else:
      markers = keyset.markers
    if havedata:
      print
    if len(dirlist) > 1:
      print("{}".format(results.name)),
    print("(on {:d} cycles):".format(keyset.num_iterations))
    print(header)
    prevvalue = 0
    prevstat = None
    for stat in markers:
      (valueavg, valuedev) = keyset.Statistics(stat)
      valuepct = int(100.0 * valuedev / valueavg + 0.5)
      if prevstat:
        (deltaavg, deltadev) = keyset.DeltaStatistics(prevstat, stat)
        if deltaavg == 0.0:
          deltaavg = 1.0
          print("deltaavg is zero! (delta is {} to {})".format(prevstat, stat))

        deltapct = int(100.0 * deltadev / deltaavg + 0.5)
      else:
        deltapct = valuepct
      (valstring, val_printed) = keyset.PrintableStatistic(valueavg)
      delta = val_printed - prevvalue
      (deltastring, _) = keyset.PrintableStatistic(delta)
      print(tformat.format(valstring, valuepct, "+" + deltastring, deltapct, stat))
      prevvalue = val_printed
      prevstat = stat
    havedata = True
