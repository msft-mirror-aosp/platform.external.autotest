#!/usr/bin/python3
#
# Copyright 2023 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""
Unit tests for server/cros/bluetooth_peer_update.py.
"""

import unittest
from . import common
from . import bluetooth_peer_update
from chromiumos.test.lab.api.bluetooth_peer_pb2 import (
        BluetoothPeerChameleondConfig)
from collections import namedtuple


class BluetoothPeerUpdateTest(unittest.TestCase):
    """
    Unit tests for bluetooth_peer_update.
    """
    def test_select_bundle_by_chameleond_commit(self):
        TestCase = namedtuple('TestCase', [
                'name',
                'arg_config',
                'arg_chameleond_commit',
                'expected_error',
        ])
        test_cases = [
                TestCase(
                        'no_bundles',
                        BluetoothPeerChameleondConfig(),
                        '',
                        Exception,
                ),
                TestCase(
                        'no_bundles',
                        BluetoothPeerChameleondConfig(bundles=[
                                BluetoothPeerChameleondConfig.ChameleondBundle(
                                        chameleond_commit='def')
                        ]),
                        'abc',
                        Exception,
                ),
                TestCase(
                        'matching_bundle',
                        BluetoothPeerChameleondConfig(bundles=[
                                BluetoothPeerChameleondConfig.ChameleondBundle(
                                        chameleond_commit='abc'),
                                BluetoothPeerChameleondConfig.ChameleondBundle(
                                        chameleond_commit='def'),
                                BluetoothPeerChameleondConfig.ChameleondBundle(
                                        chameleond_commit='ghi')
                        ]),
                        'def',
                        None,
                )
        ]
        for tc in test_cases:
            tc_name = f'select_bundle_by_chameleond_commit.{tc.name}'
            try:
                if tc.expected_error is not None:
                    self.assertRaises(
                            tc.expected_error, bluetooth_peer_update.
                            select_bundle_by_chameleond_commit, tc.arg_config,
                            tc.arg_chameleond_commit)
                else:
                    result = bluetooth_peer_update.select_bundle_by_chameleond_commit(
                            tc.arg_config, tc.arg_chameleond_commit)
                    self.assertEqual(tc.arg_chameleond_commit,
                                     result.chameleond_commit)
            except Exception as e:
                raise Exception(f'TestCase "{tc_name}" failed') from e

    def test_select_bundle_by_next_commit(self):
        TestCase = namedtuple('TestCase', [
                'name',
                'arg_config',
                'expected_error',
        ])
        test_cases = [
                TestCase(
                        'no_next_bundle',
                        BluetoothPeerChameleondConfig(bundles=[
                                BluetoothPeerChameleondConfig.ChameleondBundle(
                                        chameleond_commit='abc'),
                                BluetoothPeerChameleondConfig.ChameleondBundle(
                                        chameleond_commit='def'),
                                BluetoothPeerChameleondConfig.ChameleondBundle(
                                        chameleond_commit='ghi')
                        ]),
                        Exception,
                ),
                TestCase(
                        'next_bundle_selected',
                        BluetoothPeerChameleondConfig(
                                next_chameleond_commit='def',
                                bundles=[
                                        BluetoothPeerChameleondConfig.
                                        ChameleondBundle(
                                                chameleond_commit='abc'),
                                        BluetoothPeerChameleondConfig.
                                        ChameleondBundle(
                                                chameleond_commit='def'),
                                        BluetoothPeerChameleondConfig.
                                        ChameleondBundle(
                                                chameleond_commit='ghi')
                                ]),
                        None,
                )
        ]
        for tc in test_cases:
            tc_name = f'select_bundle_by_next_commit.{tc.name}'
            try:
                if tc.expected_error is not None:
                    self.assertRaises(
                            tc.expected_error,
                            bluetooth_peer_update.select_bundle_by_next_commit,
                            tc.arg_config)
                else:
                    result = bluetooth_peer_update.select_bundle_by_next_commit(
                            tc.arg_config)
                    self.assertEqual(tc.arg_config.next_chameleond_commit,
                                     result.chameleond_commit)
            except Exception as e:
                raise Exception(f'TestCase "{tc_name}" failed') from e

    def test_select_bundle_by_cros_release_version(self):
        TestCase = namedtuple('TestCase', [
                'name', 'arg_config', 'arg_dut_cros_release_version',
                'expected_error', 'expected_chameleond_commit'
        ])
        test_config_with_no_next_bundle = BluetoothPeerChameleondConfig(
                bundles=[
                        BluetoothPeerChameleondConfig.ChameleondBundle(
                                chameleond_commit='a',
                                min_dut_release_version='10',
                        ),
                        BluetoothPeerChameleondConfig.ChameleondBundle(
                                chameleond_commit='b',
                                min_dut_release_version='30',
                        ),
                        BluetoothPeerChameleondConfig.ChameleondBundle(
                                chameleond_commit='c',
                                min_dut_release_version='20',
                        )
                ])
        test_config_with_next_bundle = BluetoothPeerChameleondConfig(
                next_chameleond_commit='b',
                bundles=[
                        BluetoothPeerChameleondConfig.ChameleondBundle(
                                chameleond_commit='a',
                                min_dut_release_version='10',
                        ),
                        BluetoothPeerChameleondConfig.ChameleondBundle(
                                chameleond_commit='b',
                                min_dut_release_version='30',
                        ),
                        BluetoothPeerChameleondConfig.ChameleondBundle(
                                chameleond_commit='c',
                                min_dut_release_version='20',
                        )
                ])
        test_cases = [
                TestCase(
                        'no_matching',
                        test_config_with_no_next_bundle,
                        '5',
                        Exception,
                        '',
                ),
                TestCase(
                        'matching_mid',
                        test_config_with_no_next_bundle,
                        '25',
                        None,
                        'c',
                ),
                TestCase(
                        'matching_highest',
                        test_config_with_no_next_bundle,
                        '4000',
                        None,
                        'b',
                ),
                TestCase(
                        'matching_highest_excluding_next',
                        test_config_with_next_bundle,
                        '4000',
                        None,
                        'c',
                ),
        ]
        for tc in test_cases:
            tc_name = f'select_bundle_by_cros_release_version.{tc.name}'
            try:
                if tc.expected_error is not None:
                    self.assertRaises(
                            tc.expected_error, bluetooth_peer_update.
                            select_bundle_by_cros_release_version,
                            tc.arg_config, tc.arg_dut_cros_release_version)
                else:
                    result = bluetooth_peer_update.select_bundle_by_cros_release_version(
                            tc.arg_config, tc.arg_dut_cros_release_version)
                    self.assertEqual(tc.expected_chameleond_commit,
                                     result.chameleond_commit)
            except Exception as e:
                raise Exception(f'TestCase "{tc_name}" failed') from e

    def test_select_bundle_for_dut(self):
        TestCase = namedtuple('TestCase', [
                'name', 'arg_config', 'arg_dut_hostname',
                'arg_dut_cros_release_version', 'expected_chameleond_commit'
        ])
        test_config_with_no_next_bundle = BluetoothPeerChameleondConfig(
                bundles=[
                        BluetoothPeerChameleondConfig.ChameleondBundle(
                                chameleond_commit='a',
                                min_dut_release_version='10',
                        ),
                        BluetoothPeerChameleondConfig.ChameleondBundle(
                                chameleond_commit='b',
                                min_dut_release_version='30',
                        ),
                        BluetoothPeerChameleondConfig.ChameleondBundle(
                                chameleond_commit='c',
                                min_dut_release_version='20',
                        )
                ])
        test_config_with_next_bundle = BluetoothPeerChameleondConfig(
                next_chameleond_commit='b',
                next_dut_hosts=[
                        'host1',
                        'host2',
                ],
                next_dut_release_versions=[
                        '30',
                        '40',
                ],
                bundles=[
                        BluetoothPeerChameleondConfig.ChameleondBundle(
                                chameleond_commit='a',
                                min_dut_release_version='10',
                        ),
                        BluetoothPeerChameleondConfig.ChameleondBundle(
                                chameleond_commit='b',
                                min_dut_release_version='30',
                        ),
                        BluetoothPeerChameleondConfig.ChameleondBundle(
                                chameleond_commit='c',
                                min_dut_release_version='20',
                        )
                ])
        test_cases = [
                TestCase(
                        'no_next_bundle__select_by_version',
                        test_config_with_no_next_bundle,
                        'host1',
                        '15',
                        'a',
                ),
                TestCase(
                        'only_host_matches_for_next__select_non_next_by_version',
                        test_config_with_next_bundle,
                        'host1',
                        '45',
                        'c',
                ),
                TestCase(
                        'only_version_matches_for_next__select_non_next_by_version',
                        test_config_with_next_bundle,
                        'host3',
                        '40',
                        'c',
                ),
                TestCase(
                        'both_host_and_version_matches_for_next__select_next',
                        test_config_with_next_bundle,
                        'host2',
                        '40',
                        'b',
                ),
        ]
        for tc in test_cases:
            tc_name = f'select_bundle_for_dut.{tc.name}'
            try:
                result = bluetooth_peer_update.select_bundle_for_dut(
                        tc.arg_config, tc.arg_dut_hostname,
                        tc.arg_dut_cros_release_version)
                self.assertEqual(tc.expected_chameleond_commit,
                                 result.chameleond_commit)
            except Exception as e:
                raise Exception(f'TestCase "{tc_name}" failed') from e

    def test_is_chromeos_release_version_greater_or_equal(self):
        TestCase = namedtuple('TestCase', [
                'arg_version_a',
                'arg_version_b',
                'expected_result',
        ])
        test_cases = [
                TestCase('', '', True),
                TestCase('0', '0', True),
                TestCase('1.2.3', '1.2.3', True),
                TestCase('5', '0', True),
                TestCase('0', '5', False),
                TestCase('1.2.3', '3.2.1', False),
                TestCase('5.6.3', '5.5.3', True),
        ]
        for tc in test_cases:
            result = None
            try:
                result = bluetooth_peer_update.is_chromeos_release_version_greater_or_equal(
                        tc.arg_version_a, tc.arg_version_b)
                self.assertEqual(tc.expected_result, result)
            except Exception as e:
                raise Exception('TestCase failed: Expected'
                                'is_chromeos_release_version_greater_or_equal('
                                f'"{tc.arg_version_a}", '
                                f'"{tc.arg_version_b}") '
                                f'to return {tc.expected_result}, but got'
                                f'{result}') from e

    def test_compare_chromeos_release_version(self):
        TestCase = namedtuple('TestCase', [
                'arg_version_a',
                'arg_version_b',
                'expected_result',
        ])
        test_cases = [
                TestCase('', '', 0),
                TestCase('0', '0', 0),
                TestCase('1.2.3', '1.2.3', 0),
                TestCase('5', '0', 1),
                TestCase('0', '5', -1),
                TestCase('1.2.3', '3.2.1', -1),
                TestCase('5.6.3', '5.5.3', 1),
        ]
        for tc in test_cases:
            result = None
            try:
                result = bluetooth_peer_update.compare_chromeos_release_version(
                        tc.arg_version_a, tc.arg_version_b)
                self.assertEqual(tc.expected_result, result)
            except Exception as e:
                raise Exception('TestCase failed: Expected'
                                'compare_chromeos_release_version('
                                f'"{tc.arg_version_a}", '
                                f'"{tc.arg_version_b}") '
                                f'to return {tc.expected_result}, but got'
                                f'{result}') from e


if __name__ == '__main__':
    unittest.main()
