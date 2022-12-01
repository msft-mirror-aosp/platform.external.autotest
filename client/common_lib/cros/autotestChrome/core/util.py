# Copyright 2022 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import absolute_import
import glob
import imp
import logging
import os
import socket
import sys

import common

import autotest_lib.client.common_lib.cros.autotestChrome.py_utils as catapult_util  # pylint: disable=import-error

IsRunningOnCrosDevice = ( # pylint: disable=invalid-name
    catapult_util.IsRunningOnCrosDevice)
GetCatapultDir = catapult_util.GetCatapultDir # pylint: disable=invalid-name


def GetTelemetryDir():
  return os.path.normpath(os.path.join(
      os.path.abspath(__file__), '..', '..', '..'))


def GetTelemetryThirdPartyDir():
  return os.path.join(GetTelemetryDir(), 'third_party')