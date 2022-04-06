# Lint as: python2, python3
# Copyright 2022 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import unittest

from unittest.mock import Mock
from autotest_lib.server.cros.tradefed import adb


class AdbTest(unittest.TestCase):
    """Tests for ADB module."""

    # Verify that ipv4 is put into IP:PORT format.
    def test_get_adb_target_ipv4(self):
        mock_host = Mock()
        mock_host.port = 3467
        mock_host.hostname = '123.76.0.29'
        target = adb.get_adb_target(mock_host)
        self.assertEqual(target, '123.76.0.29:3467')

    # Verify that ipv6 is put into [IP]:PORT format.
    def test_get_adb_target_ipv6(self):
        mock_host = Mock()
        mock_host.port = 1234
        mock_host.hostname = '2409::3'
        target = adb.get_adb_target(mock_host)
        self.assertEqual(target, '[2409::3]:1234')

    # Verify that a host name works.
    def test_get_adb_target_hostname(self):
        mock_host = Mock()
        mock_host.port = 4792
        mock_host.hostname = 'some.hostname.cros'
        target = adb.get_adb_target(mock_host)
        self.assertEqual(target, 'some.hostname.cros:4792')

    # Verify that a list of hosts work.
    def test_get_adb_targets(self):
        mock_host1 = Mock()
        mock_host2 = Mock()
        mock_host3 = Mock()
        mock_host1.port = 1111
        mock_host2.port = 2222
        mock_host3.port = 3333
        mock_host1.hostname = 'host1'
        mock_host2.hostname = 'host2'
        mock_host3.hostname = 'host3'

        targets = adb.get_adb_targets([mock_host1, mock_host2, mock_host3])
        self.assertEqual(targets, ['host1:1111', 'host2:2222', 'host3:3333'])

    def test_tradefed_options_with_host(self):
        mock_host = Mock()
        mock_host.port = 4792
        mock_host.hostname = 'some.hostname.cros'
        options = adb.tradefed_options(mock_host)
        self.assertEqual(options, ('-s', 'some.hostname.cros:4792'))

    def test_tradefed_options_without_host(self):
        options = adb.tradefed_options(None)
        self.assertEqual(options, ('-H', 'localhost', '-P', '5037'))
