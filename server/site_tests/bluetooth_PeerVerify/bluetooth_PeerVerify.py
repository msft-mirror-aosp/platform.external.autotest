# Lint as: python2, python3
# Copyright 2021 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
""" Bluetooth test that checks the RSSI of Bluetooth peers

This to used for checking Bluetooth test beds and it is
assumed that this test is only run on test beds which is
expected to have 4 btpeers.

The test fails if
- 4 btpeers are not detected
- Any of the RSSI values detected is < -70

"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import logging

from autotest_lib.server.cros.bluetooth.bluetooth_adapter_quick_tests import (
        BluetoothAdapterQuickTests)

from autotest_lib.server.cros.bluetooth.bluetooth_adapter_tests import (
        test_retry_and_log)

test_wrapper = BluetoothAdapterQuickTests.quick_test_test_decorator
batch_wrapper = BluetoothAdapterQuickTests.quick_test_batch_decorator


class bluetooth_PeerVerify(BluetoothAdapterQuickTests):
    """Test to check the RSSI of btpeers."""

    @test_wrapper(
            'Check if rssi of peers > -70 and whether 4 btpeers are present',
            devices={'MOUSE': -1},
            use_all_peers=True,
            supports_floss=True)
    @test_retry_and_log(False)
    def check_rssi(self):
        """Check if RSSI > -70. """
        try:
            rssi_list = []
            self.result = {}
            for n, device in enumerate(self.devices['MOUSE']):
                rssi = self.get_device_sample_rssi(device,
                                                   use_cached_value=False)
                rssi_list.append(rssi)
                logging.info('RSSI for peer %s is %s', n, rssi)
            logging.info('RSSI values are %s', rssi_list)

            num_btpeer = len(rssi_list)
            self.results = {
                    'rssi_values': rssi_list,
                    'number_of_btpeers': num_btpeer
            }

            rssi_result = all([
                    True if rssi is not None and rssi > -70 else False
                    for rssi in rssi_list
            ])

            if not rssi_result:
                logging.info("Low or None rssi values detected")
            if num_btpeer != 4:
                logging.info("Only %s btpeer detected.  Expected 4 btpeers",
                             num_btpeer)

            self.write_perf_keyval(self.results)
            return rssi_result and num_btpeer == 4
        except Exception as e:
            logging.debug('exception in test_check_rssi %s', str(e))
            return False

    @batch_wrapper('Verify Peer RSSI')
    def verify_peer_batch_run(self, num_iterations=1, test_name=None):
        """ Batch of checks for btpeer. """
        self.check_rssi()

    def run_once(self,
                 host,
                 num_iterations=1,
                 args_dict=None,
                 test_name=None,
                 flag='Quick Health',
                 floss=False):
        """Running Bluetooth adapter suspend resume with peer autotest.

        @param host: the DUT, usually a chromebook
        @param num_iterations: the number of times to execute the test
        @param test_name: the test to run or None for all tests
        @param flag: run tests with this flag (default: Quick Health)

        """

        # Set rssi_check to false so that verify_device_rssi() does not run.
        # This test needs different behaviour for low rssi failures
        if args_dict is None:
            args_dict = {}
        if 'rssi_check' not in args_dict:
            args_dict['rssi_check'] = 'false'

        # Initialize and run the test batch or the requested specific test
        self.quick_test_init(host,
                             use_btpeer=True,
                             flag=flag,
                             args_dict=args_dict,
                             floss=floss)
        self.verify_peer_batch_run(num_iterations, test_name)
        self.quick_test_cleanup()
