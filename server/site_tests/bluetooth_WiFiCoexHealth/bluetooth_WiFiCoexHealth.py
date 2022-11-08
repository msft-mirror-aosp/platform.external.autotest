# Lint as: python3
# Copyright 2022 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import logging
import multiprocessing
import sys

from autotest_lib.server.cros.bluetooth.bluetooth_adapter_quick_tests import (
        BluetoothAdapterQuickTests)
from autotest_lib.client.common_lib import error
from autotest_lib.client.common_lib.cros.network import ping_runner
from autotest_lib.client.common_lib.cros.network import xmlrpc_datatypes
from autotest_lib.server.cros.network import hostap_config
from autotest_lib.server.cros.network import wifi_test_context_manager


class bluetooth_WiFiCoexHealth(BluetoothAdapterQuickTests):
    """A Batch of BT WiFi coexist tests."""

    test_wrapper = BluetoothAdapterQuickTests.quick_test_test_decorator
    batch_wrapper = BluetoothAdapterQuickTests.quick_test_batch_decorator

    # Remove flags=['Quick Health'] when this test is migrated to stable suite.
    @test_wrapper('Independent reset test', flags='Quick Health')
    def independent_reset_test(self):
        """Verify the adapter can be reset without affecting WiFi component"""

        try:
            # We use the default router name by passing an empty args to WiFi
            # context. E.g., the router name would be dut-router.cros if the DUT
            # name is dut.cros.
            wifi_context = wifi_test_context_manager.WiFiTestContextManager(
                    'bluetooth_WiFiCoexHealth.independent_reset_test',
                    self.host, {}, self.debugdir)
            wifi_context.setup(include_pcap=False, include_attenuator=False)

            # Connect to the AP and verify the connection with ping.
            ap_config = hostap_config.HostapConfig(
                    channel=48, mode=hostap_config.HostapConfig.MODE_11A)
            wifi_context.configure(ap_config)
            ap_ssid = wifi_context.router.get_ssid()
            assoc_params = xmlrpc_datatypes.AssociationParameters(
                    ssid=ap_ssid, security_config=ap_config.security_config)
            wifi_context.assert_connect_wifi(assoc_params)
            wifi_context.assert_ping_from_dut()
        except Exception as e:
            raise error.TestNAError('Failed to set up WiFi connection') from e

        def do_ping():
            try:
                logging.info('Started to ping for 10 seconds, 20 packets.')
                ping_config = ping_runner.PingConfig(
                        wifi_context.get_wifi_addr(),
                        interval=0.5,
                        count=20,
                        source_iface=wifi_context.client.wifi_if)
                wifi_context.assert_ping_from_dut(ping_config=ping_config)
            except Exception as e:
                logging.exception('Ping failed')
                sys.exit(1)

        async_ping = multiprocessing.Process(target=do_ping)
        async_ping.daemon = True
        async_ping.start()

        for _ in range(5):
            self.test_reset_on_adapter()

        async_ping.join(20)
        wifi_context.teardown()

        if async_ping.exitcode is None:
            async_ping.terminate()
            raise error.TestError('Ping thread hangs')
        elif async_ping.exitcode:
            raise error.TestFail('Ping failed')

    @batch_wrapper('BT WiFi Coexist')
    def wifi_coex_health_batch_run(self, num_iterations=1, test_name=None):
        """Run the BT WiFi coexist health test batch or a specific given test.

        @param num_iterations: the number of rounds to execute the test.
        @param test_name: a single test to run or leave None to run the batch.
        """
        self.independent_reset_test()

    def run_once(self,
                 host,
                 num_iterations=1,
                 test_name=None,
                 peer_required=False,
                 flag='Quick Health',
                 floss=False):
        """Run the batch of Bluetooth WiFi coexist health tests.

        @param host: the DUT, usually a chromebook.
        @param num_iterations: the number of rounds to execute the test.
        @param test_name: a single test to run or leave None to run the batch.
        @param peer_required: whether a btpeer is required.
        @param flag: run 'Quick Health' tests or 'AVL' tests.
        @param floss: enbluetooth_WiFiCoexHealthble Floss.
        """
        self.quick_test_init(host,
                             use_btpeer=peer_required,
                             flag=flag,
                             start_browser=False,
                             floss=floss)
        self.wifi_coex_health_batch_run(num_iterations, test_name)
        self.quick_test_cleanup()
