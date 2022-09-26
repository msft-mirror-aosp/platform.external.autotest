# Lint as: python3
# Copyright 2022 The ChromiumOS Authors.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from autotest_lib.utils import labellib

MAX_ALLOWED_BTPEERS = 4
TAST_BTPEERS_COUNT_ATTRIBUTE_FORMAT = 'bluetooth_btpeers_%d'


def get_working_bluetooth_btpeer(host) -> int:
  """
  Retrieve the number of btpeers in the testbed from the
  "working_bluetooth_btpeer" host label as an integer.

  @param host: remote.RemoteHost instance representing DUT.

  @raises ValueError if the host does not have the "working_bluetooth_btpeer"
      label or if it is invalid.
  """
  labels = labellib.LabelsMapping(host.host_info_store.get().labels)
  working_bluetooth_btpeer = labels.get('working_bluetooth_btpeer')
  if working_bluetooth_btpeer is None:
      raise ValueError("missing required host label 'working_bluetooth_btpeer'")
  try:
      working_bluetooth_btpeer = int(working_bluetooth_btpeer)
  except ValueError as e:
      raise ValueError("host label 'working_bluetooth_btpeer' value must be an integer between 1 and %d, inclusive" % MAX_ALLOWED_BTPEERS) from e
  if working_bluetooth_btpeer < 1 or working_bluetooth_btpeer > MAX_ALLOWED_BTPEERS:
      raise ValueError("host label 'working_bluetooth_btpeer' value must be between 1 and %d, inclusive, but got '%d'" % (
          MAX_ALLOWED_BTPEERS,
          working_bluetooth_btpeer
      ))
  return working_bluetooth_btpeer


def build_tast_btpeer_count_attribute_test_expression(working_bluetooth_btpeers : int, allow_no_required_btpeers : bool = True) -> str:
  """
      Builds a tast test selection sub-expression matching sub-attributes of
      the "group:bluetooth" tast attribute that selects tests that require
      btpeers up to working_bluetooth_btpeers. This sub-expression must come
      after "group:bluetooth" in the final tast test selection expression this
      is used in.

      @param working_bluetooth_btpeers: The number of btpeers this testbed has.
      @param allow_no_required_btpeers: If True, the returned expression will
          also allow for tests that do not require any btpeers.
      @returns The built tast test selection sub-expression as a string.
  """
  if working_bluetooth_btpeers <= 0 and not allow_no_required_btpeers:
    raise ValueError("working_bluetooth_btpeers must be greater than 0 if allow_no_required_btpeers is False, got %d" % working_bluetooth_btpeers)
  expr = '('
  if working_bluetooth_btpeers > 0:
      expr_segments = []
      for i in range(1, working_bluetooth_btpeers + 1):
          expr_segments.append(TAST_BTPEERS_COUNT_ATTRIBUTE_FORMAT % i)
      expr += ' || '.join(expr_segments)
  if allow_no_required_btpeers:
    expr_segments = []
    for i in range(1, MAX_ALLOWED_BTPEERS + 1):
      expr_segments.append('!' + (TAST_BTPEERS_COUNT_ATTRIBUTE_FORMAT % i))
    if working_bluetooth_btpeers > 0:
      expr += ' || '
    expr += '(' + ' && '.join(expr_segments) + ')'
  expr += ')'
  return expr