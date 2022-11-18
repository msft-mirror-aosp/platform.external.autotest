# Lint as: python2, python3
# Copyright 2022 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""This class implements a Bluetooth link layer privacy health package"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import logging
import time

from autotest_lib.server.cros.bluetooth.bluetooth_adapter_quick_tests \
     import (BluetoothAdapterQuickTests, PROFILE_CONNECT_WAIT, SUSPEND_SEC)
from autotest_lib.server.cros.bluetooth.bluetooth_adapter_adv_monitor_tests \
     import (BluetoothAdapterAdvMonitorTests)
from autotest_lib.server.cros.bluetooth.bluetooth_adapter_tests import (
        SUSPEND_POWER_DOWN_CHIPSETS, SUSPEND_POWER_DOWN_MODELS, TABLET_MODELS)
from autotest_lib.server.cros.bluetooth.bluetooth_adapter_llprivacy_tests \
     import (BluetoothAdapterLLPrivacyTests)
from autotest_lib.server.cros.bluetooth.bluetooth_adapter_qr_tests import (
        BluetoothAdapterQRTests)
from autotest_lib.server.cros.bluetooth.bluetooth_adapter_controller_role_tests\
        import bluetooth_AdapterControllerRoleTests
from autotest_lib.server.cros.bluetooth.bluetooth_adapter_pairing_tests import (
        BluetoothAdapterPairingTests)
from autotest_lib.server.cros.bluetooth.bluetooth_adapter_hidreports_tests \
        import BluetoothAdapterHIDReportTests


class bluetooth_AdapterLLPrivacyHealth(
        BluetoothAdapterLLPrivacyTests, BluetoothAdapterQuickTests,
        BluetoothAdapterAdvMonitorTests, BluetoothAdapterQRTests,
        BluetoothAdapterPairingTests, BluetoothAdapterHIDReportTests,
        bluetooth_AdapterControllerRoleTests):
    """This class implements a Bluetooth ll privacy health package, using
    methods provided in BluetoothAdapterQuickTests,
    The package is running several sub batches of tests.
    A batch is defined as a set of tests, preferably with a common subject, e.g
    'LE Health' batch, or the 'Stand Alone Health' batch.
    The quick health test package is improving test time by doing the minimal
    cleanups between each test and test batches, saving the auto-test ramp up
    time of about 90-120 second per test.
    """

    test_wrapper = BluetoothAdapterQuickTests.quick_test_test_decorator
    batch_wrapper = BluetoothAdapterQuickTests.quick_test_batch_decorator

    def _test_mouse(self, device):
        return (self.test_hid_device_created(device.address)
                and self.test_mouse_left_click(device)
                and self.test_mouse_move_in_xy(device, -60, 100)
                and self.test_mouse_scroll_down(device, 70)
                and self.test_mouse_click_and_drag(device, 90, 30))

    def _test_keyboard_with_string(self, device):
        return (self.test_hid_device_created(device.address)
                and self.test_keyboard_input_from_trace(device, "simple_text"))

    # ---------------------------------------------------------------
    # Reconnect after suspend tests
    # ---------------------------------------------------------------

    def run_reconnect_device(self,
                             devtuples,
                             iterations=1,
                             auto_reconnect=False):
        """ Reconnects a device after suspend/resume.

        @param devtuples: array of tuples consisting of the following
                            * device_type: MOUSE, BLE_MOUSE, etc.
                            * device: meta object for peer device
                            * device_test: Optional; test function to run w/
                                           device (for example, mouse click)
        @params iterations: number of suspend/resume + reconnect iterations
        @params auto_reconnect: Expect host to automatically reconnect to peer
        """
        boot_id = self.host.get_boot_id()

        try:
            # Set up the device; any failures should assert
            for _, device, device_test in devtuples:
                self.assert_discover_and_pair(device)
                self.assert_on_fail(
                        self.test_device_set_discoverable(device, False))
                self.assert_on_fail(
                        self.test_connection_by_adapter(device.address))

                # Profile connection may not have completed yet and this will
                # race with a subsequent disconnection (due to suspend). Use the
                # device test to force profile connect or wait if no test was
                # given.
                if device_test is not None:
                    self.assert_on_fail(device_test(device))
                else:
                    time.sleep(PROFILE_CONNECT_WAIT)

            for it in range(iterations):
                logging.info('Running iteration {}/{} of suspend reconnection'.
                             format(it + 1, iterations))

                # Start the suspend process
                suspend = self.suspend_async(suspend_time=SUSPEND_SEC)
                start_time = self.bluetooth_facade.get_device_utc_time()

                # Trigger suspend, wait for regular resume, verify we can reconnect
                # and run device specific test
                self.test_suspend_and_wait_for_sleep(suspend,
                                                     sleep_timeout=SUSPEND_SEC)
                self.test_wait_for_resume(boot_id,
                                          suspend,
                                          resume_timeout=SUSPEND_SEC,
                                          test_start_time=start_time)

                # Only reconnect if we don't expect automatic reconnect.
                # Let the devices initiate connections before the DUT initiates
                # auto reconnections.
                # Complete reconnecting all peers before running device tests.
                # Otherwise, we may have a race between auto reconnection
                # from the dut and peer initiated connection. See b/177870286
                if not auto_reconnect:
                    for device_type, device, _ in devtuples:
                        if 'BLE' in device_type:
                            # LE can't reconnect without
                            # advertising/discoverable
                            self.test_device_set_discoverable(device, True)
                            # Make sure we're actually connected
                            self.test_device_is_connected(device.address)
                        else:
                            # Classic requires peer to initiate a connection to
                            # wake up the dut
                            self.test_connection_by_device(device)

                for _, device, device_test in devtuples:
                    if device_test is not None:
                        device_test(device)

        finally:
            for _, device, __ in devtuples:
                self.test_remove_pairing(device.address)

    @test_wrapper('Monitor Object Health Tests')
    def advmon_monitor_health_tests(self):
        """Tests advertisement monitor object health."""
        self.advmon_test_monitor_creation()
        self.advmon_test_monitor_validity()

    # TODO(b/150897528) - Dru loses firmware around suspend, which causes bluez
    #                     removes all the monitors.
    @test_wrapper('Interleave Scan Tests',
                  devices={'BLE_MOUSE': 1},
                  skip_models=SUSPEND_POWER_DOWN_MODELS,
                  skip_chipsets=SUSPEND_POWER_DOWN_CHIPSETS)
    def advmon_interleaved_scan_tests(self):
        """Tests interleave scan."""
        self.advmon_test_interleaved_scan()

    @test_wrapper('Reconnect Classic HID', devices={'MOUSE': 1})
    def sr_reconnect_classic_hid(self):
        """ Reconnects a classic HID device after suspend/resume. """
        device_type = 'MOUSE'
        device = self.devices[device_type][0]
        self.run_reconnect_device([(device_type, device, self._test_mouse)])

    @test_wrapper('Reconnect LE HID', devices={'BLE_MOUSE': 1})
    def sr_reconnect_le_hid(self):
        """ Reconnects a LE HID device after suspend/resume. """
        device_type = 'BLE_MOUSE'
        device = self.devices[device_type][0]
        self.run_reconnect_device([(device_type, device, self._test_mouse)])

    # TODO(b/151332866) - Bob can't wake from suspend due to wrong power/wakeup
    # TODO(b/150897528) - Dru is powered down during suspend, won't wake up
    @test_wrapper('Peer wakeup Classic HID',
                  devices={'MOUSE': 1},
                  skip_models=TABLET_MODELS + SUSPEND_POWER_DOWN_MODELS +
                  ['bob'],
                  skip_chipsets=SUSPEND_POWER_DOWN_CHIPSETS)
    def sr_peer_wake_classic_hid(self):
        """ Use classic HID device to wake from suspend. """
        device = self.devices['MOUSE'][0]
        self.run_peer_wakeup_device('MOUSE',
                                    device,
                                    device_test=self._test_mouse)

    # TODO(b/151332866) - Bob can't wake from suspend due to wrong power/wakeup
    # TODO(b/150897528) - Dru is powered down during suspend, won't wake up
    @test_wrapper('Peer wakeup LE HID',
                  devices={'BLE_MOUSE': 1},
                  skip_models=TABLET_MODELS + SUSPEND_POWER_DOWN_MODELS +
                  ['bob'],
                  skip_chipsets=SUSPEND_POWER_DOWN_CHIPSETS)
    def sr_peer_wake_le_hid(self):
        """ Use LE HID device to wake from suspend. """
        device = self.devices['BLE_MOUSE'][0]
        self.run_peer_wakeup_device('BLE_MOUSE',
                                    device,
                                    device_test=self._test_mouse)

    # TODO(b/163143005) - Hana can't handle two concurrent HID connections
    @test_wrapper('Reconnect Multiple Classic HID',
                  devices={
                          'MOUSE': 1,
                          'KEYBOARD': 1
                  },
                  skip_models=['hana'])
    def sr_reconnect_multiple_classic_hid(self):
        """ Reconnects multiple classic HID devices after suspend/resume. """
        devices = [('MOUSE', self.devices['MOUSE'][0], self._test_mouse),
                   ('KEYBOARD', self.devices['KEYBOARD'][0],
                    self._test_keyboard_with_string)]
        self.run_reconnect_device(devices)

    @test_wrapper('Reconnect one of each classic+LE HID',
                  devices={
                          'BLE_MOUSE': 1,
                          'KEYBOARD': 1
                  })
    def sr_reconnect_multiple_classic_le_hid(self):
        """ Reconnects one of each classic and LE HID devices after
            suspend/resume.
        """
        devices = [('BLE_MOUSE', self.devices['BLE_MOUSE'][0],
                    self._test_mouse),
                   ('KEYBOARD', self.devices['KEYBOARD'][0],
                    self._test_keyboard_with_string)]
        self.run_reconnect_device(devices)

    @test_wrapper('Connect Disconnect by Device Loop',
                  devices={'BLE_MOUSE': 1},
                  flags=['Quick Health'])
    def le_connect_disconnect_by_device_loop(self):
        """Run connect/disconnect loop initiated by device.
           The test also checks that there are no undesired
           reconnections.
        """

        device = self.devices['BLE_MOUSE'][0]
        self.connect_disconnect_by_device_loop(
                device=device,
                loops=3,
                device_type='BLE_MOUSE',
                check_connected_method=self.test_mouse_move_in_xy)

    @test_wrapper('Connect Disconnect Loop', devices={'BLE_MOUSE': 1})
    def le_connect_disconnect_loop(self):
        """Run connect/disconnect loop initiated by DUT.
           The test also checks that there are no undesired
           reconnections.
           TODO(ysahvit) - add connection creation attempts
                           initiated by HID device
        """

        device = self.devices['BLE_MOUSE'][0]
        self.connect_disconnect_loop(device=device, loops=3)

    @test_wrapper('HID Reconnect Speed',
                  devices={'BLE_MOUSE': 1},
                  flags=['Quick Health'])
    def le_hid_reconnect_speed(self):
        """Test the speed of a LE HID device reconnect to DUT"""

        device = self.devices['BLE_MOUSE'][0]
        self.hid_reconnect_speed(device=device, device_type='BLE_MOUSE')

    @test_wrapper('Auto Reconnect', devices={'BLE_MOUSE': 1})
    def le_auto_reconnect(self):
        """LE reconnection loop by resetting HID and check reconnection"""

        device = self.devices['BLE_MOUSE'][0]
        self.auto_reconnect_loop(
                device=device,
                loops=3,
                check_connected_method=self.test_mouse_left_click)

    # TODO (b/165949047) Flaky behavior on MVL/4.4 kernel causes flakiness when
    # connection is initiated by the peripheral. Skip the test until 2021 uprev
    @test_wrapper('LE Receiver Role Test',
                  devices={'BLE_KEYBOARD': 1},
                  skip_models=['bob'])
    def le_role_receiver(self):
        """Tests basic Nearby Receiver role"""

        self.verify_controller_capability(required_roles=['peripheral'],
                                          test_type=self.flag)

        kbd = self.devices['BLE_KEYBOARD'][0]
        kbd_test_func = lambda device: self.test_keyboard_input_from_trace(
                device, 'simple_text')

        self.nearby_receiver_role_test(kbd, kbd_test_func)

    @test_wrapper('LE Sender Role Test', devices={'BLE_KEYBOARD': 1})
    def le_role_sender(self):
        """Tests basic Nearby Sender role"""

        self.verify_controller_capability(required_roles=['central'],
                                          test_type=self.flag)

        kbd = self.devices['BLE_KEYBOARD'][0]
        kbd_test_func = lambda device: self.test_keyboard_input_from_trace(
                device, 'simple_text')

        self.nearby_sender_role_test(kbd, kbd_test_func)

    @test_wrapper('LE Sender Role Test During HID',
                  devices={
                          'BLE_KEYBOARD': 1,
                          'BLE_MOUSE': 1
                  })
    def le_role_sender_during_hid(self):
        """Tests Nearby Sender role while already connected to HID device"""

        self.verify_controller_capability(
                required_roles=['central-peripheral'], test_type=self.flag)

        kbd = self.devices['BLE_KEYBOARD'][0]
        mouse = self.devices['BLE_MOUSE'][0]

        kbd_test_func = lambda device: self.test_keyboard_input_from_trace(
                device, 'simple_text')
        mouse_test_func = self.test_mouse_left_click

        hid_test_device = (mouse, mouse_test_func, 'pre')
        self.nearby_sender_role_test(kbd,
                                     kbd_test_func,
                                     secondary_info=hid_test_device)

    @batch_wrapper("LL Privacy Health")
    def ll_privacy_batch_run(self, num_iterations=1, test_name=None):
        """A batch of tests with LL privacy enabled."""
        # adv monitor test
        self.advmon_monitor_health_tests()
        self.advmon_interleaved_scan_tests()
        # suspend resume test
        # b/234975037 we may remove some of the SR tests if they are stabilized
        self.sr_reconnect_classic_hid()
        self.sr_reconnect_le_hid()
        self.sr_peer_wake_classic_hid()
        self.sr_peer_wake_le_hid()
        self.sr_reconnect_multiple_classic_hid()
        self.sr_reconnect_multiple_classic_le_hid()
        # LE health test
        self.le_connect_disconnect_by_device_loop()
        self.le_connect_disconnect_loop()
        self.le_hid_reconnect_speed()
        self.le_auto_reconnect()
        # LE role test
        self.le_role_receiver()
        self.le_role_sender()
        self.le_role_sender_during_hid()

    def run_once(self,
                 host,
                 num_iterations=1,
                 args_dict=None,
                 peer_required=True,
                 test_name=None,
                 flag='Quick Health'):
        """Run the package of Bluetooth LL privacy health tests. Currently,
        the tests are directly copied from other test packages, but with
        the LL privacy enabled.
        The reason to copy tests directly instead of deriving from other test
        classes is a limitation of using the "import pattern" as described in
        crbug/992796, b/138597710, b/144429218. Also we do not schedule batch
        job in the lab. Creating separate job gives us more control in terms
        of test pre-conditions and we can implement LL privacy specific tests
        if necessary.

        @param host: the DUT, usually a chromebook
        @param num_iterations: the number of rounds to execute the test
        @param test_name: the test to run or None for all tests
        @param flag: run tests with this flag (default: Quick Health)
        """

        # Init the quick test and start the package
        self.quick_test_init(host,
                             use_btpeer=peer_required,
                             flag=flag,
                             args_dict=args_dict,
                             llprivacy=True)
        self.ll_privacy_batch_run(num_iterations, test_name)
        # End and cleanup test package
        self.quick_test_cleanup()
