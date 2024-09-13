# Lint as: python2, python3
# Copyright 2020 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
""" Server-side bluetooth adapter tests that involve suspend/resume with peers

paired and/or connected.

Single btpeer tests:
  - Reconnect on resume test
    - Classic HID
    - LE HID
    - A2DP
  - Wake from suspend test
    - Classic HID
    - LE HID
    - A2DP shouldn't wake from suspend
  - Suspend while discovering (discovering should pause and unpause)
  - Suspend while advertising (advertising should pause and unpause)

Multiple btpeer tests:
  - Reconnect on resume test
    - One classic HID, One LE HID
    - Two classic HID
    - Two LE HID
  - Wake from suspend test
    - Two classic HID
    - Two classic LE
"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import logging
import time

from autotest_lib.client.common_lib import error

from autotest_lib.client.cros.bluetooth.bluetooth_audio_test_data import A2DP
from autotest_lib.server.cros.bluetooth.bluetooth_adapter_tests import (
        TABLET_MODELS, SUSPEND_POWER_DOWN_CHIPSETS, SUSPEND_POWER_DOWN_MODELS)
from autotest_lib.server.cros.bluetooth.bluetooth_adapter_qr_tests import (
        QR_UNSUPPORTED_CHIPSETS, QR_EVENT_PERIOD, BluetoothAdapterQRTests)
from autotest_lib.server.cros.bluetooth.bluetooth_adapter_quick_tests import (
        BluetoothAdapterQuickTests)
from autotest_lib.server.cros.bluetooth.bluetooth_adapter_quick_tests import (
        PROFILE_CONNECT_WAIT, SUSPEND_SEC, EXPECT_NO_WAKE_SUSPEND_SEC)
from six.moves import range

test_wrapper = BluetoothAdapterQuickTests.quick_test_test_decorator
batch_wrapper = BluetoothAdapterQuickTests.quick_test_batch_decorator

STRESS_ITERATIONS = 50

# Intel controllers may have up to 2 seconds deviation.
# Use a longer suspend delay to make sure QR events are received during
# the pre-suspend phase.
SUSPEND_DELAY_FOR_QR_SECS = QR_EVENT_PERIOD + 3
SUSPEND_DELAY_TIMEOUT_FOR_QR_SECS = QR_EVENT_PERIOD * 2
WAKEUP_TIMEOUT_FOR_QR_SECS = 30
RESUME_TIMEOUT_FOR_QR_SECS = (WAKEUP_TIMEOUT_FOR_QR_SECS -
                              SUSPEND_DELAY_TIMEOUT_FOR_QR_SECS)


class bluetooth_AdapterSRHealth(BluetoothAdapterQuickTests,
                                BluetoothAdapterQRTests):
    """Server side bluetooth adapter suspend resume test with peer."""

    def _test_keyboard_with_string(self, device):
        # b/328691072: WCN3991 suspend fails with device tests
        # TODO: Remove after the root cause is fixed.
        if self.bluetooth_facade.get_chipset_name() == 'QCA-WCN3991':
            return self.test_hid_device_created(device.address)
        return (self.test_hid_device_created(device.address)
                and self.test_keyboard_input_from_trace(device, "simple_text"))

    def _test_mouse(self, device):
        # b/328691072: WCN3991 suspend fails with device tests
        # TODO: Remove after the root cause is fixed.
        if self.bluetooth_facade.get_chipset_name() == 'QCA-WCN3991':
            return self.test_hid_device_created(device.address)
        return (self.test_hid_device_created(device.address)
                and self.test_mouse_left_click(device)
                and self.test_mouse_move_in_xy(device, -60, 100)
                and self.test_mouse_scroll_down(device, 70)
                and self.test_mouse_click_and_drag(device, 90, 30))

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
                self._get_btmon_log(
                        lambda: self.test_suspend_and_wait_for_sleep(
                                suspend, sleep_timeout=SUSPEND_SEC))
                invalid_hci_suspend = self._check_btmon_pattern(
                        "Status: Invalid HCI Command Parameters")

                self._get_btmon_log(lambda: self.test_wait_for_resume(
                        boot_id,
                        suspend,
                        resume_timeout=SUSPEND_SEC,
                        test_start_time=start_time))
                invalid_hci_resume = self._check_btmon_pattern(
                        "Status: Invalid HCI Command Parameters")

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
                            # Set not discoverable for the next iteration
                            self.test_device_set_discoverable(device, False)
                        else:
                            # Classic requires peer to initiate a connection to
                            # wake up the dut
                            self.test_connection_by_device(device)

                for _, device, device_test in devtuples:
                    if device_test is not None:
                        device_test(device)

                if invalid_hci_suspend or invalid_hci_resume:
                    raise error.TestError(
                            'Invalid HCI command at suspend: {}, resume: {}'.
                            format(invalid_hci_suspend, invalid_hci_resume))

        finally:
            for _, device, __ in devtuples:
                self.test_remove_pairing(device.address)

    @test_wrapper('Reconnect Classic HID',
                  devices={'MOUSE': 1},
                  supports_floss=True)
    def sr_reconnect_classic_hid(self):
        """ Reconnects a classic HID device after suspend/resume. """
        device_type = 'MOUSE'
        device = self.devices[device_type][0]
        self.run_reconnect_device([(device_type, device,
                                    self._test_mouse)])

    @test_wrapper('Reboot and Reconnect Classic HID',
                  devices={'MOUSE': 1},
                  supports_floss=True)
    def sr_reboot_and_reconnect_classic_hid(self):
        """ Reboot and reconnects a classic HID device after suspend/resume. """
        device_type = 'MOUSE'
        device = self.devices[device_type][0]
        # On boot, OOBE could attempt to pair any nearby HID device and
        # affects the test result. Set peer undiscoverable during reboot.
        self.test_device_set_discoverable(device, False)
        # Reboot the DUT so that it starts with a clean state.
        logging.info('Rebooting the DUT')
        self.reboot()
        self.test_device_set_discoverable(device, True)
        self.run_reconnect_device([(device_type, device, self._test_mouse)])

    @test_wrapper('Reconnect LE HID',
                  devices={'BLE_MOUSE': 1},
                  supports_floss=True)
    def sr_reconnect_le_hid(self):
        """ Reconnects a LE HID device after suspend/resume. """
        device_type = 'BLE_MOUSE'
        device = self.devices[device_type][0]
        self.run_reconnect_device([(device_type, device,
                                    self._test_mouse)])

    # TODO(b/163143005) - Hana can't handle two concurrent HID connections
    @test_wrapper('Reconnect Multiple Classic HID',
                  devices={
                          'MOUSE': 1,
                          'KEYBOARD': 1
                  },
                  skip_models=['hana'],
                  supports_floss=True)
    def sr_reconnect_multiple_classic_hid(self):
        """ Reconnects multiple classic HID devices after suspend/resume. """
        devices = [('MOUSE', self.devices['MOUSE'][0],
                    self._test_mouse),
                   ('KEYBOARD', self.devices['KEYBOARD'][0],
                    self._test_keyboard_with_string)]
        self.run_reconnect_device(devices)

    @test_wrapper('Reconnect Multiple LE HID',
                  devices={
                          'BLE_MOUSE': 1,
                          'BLE_KEYBOARD': 1
                  },
                  supports_floss=True)
    def sr_reconnect_multiple_le_hid(self):
        """ Reconnects multiple LE HID devices after suspend/resume. """
        devices = [('BLE_MOUSE', self.devices['BLE_MOUSE'][0],
                    self._test_mouse),
                   ('BLE_KEYBOARD', self.devices['BLE_KEYBOARD'][0],
                    self._test_keyboard_with_string)]
        self.run_reconnect_device(devices)

    @test_wrapper('Reconnect one of each classic+LE HID',
                  devices={
                          'BLE_MOUSE': 1,
                          'KEYBOARD': 1
                  },
                  supports_floss=True)
    def sr_reconnect_multiple_classic_le_hid(self):
        """ Reconnects one of each classic and LE HID devices after
            suspend/resume.
        """
        devices = [('BLE_MOUSE', self.devices['BLE_MOUSE'][0],
                    self._test_mouse),
                   ('KEYBOARD', self.devices['KEYBOARD'][0],
                    self._test_keyboard_with_string)]
        self.run_reconnect_device(devices)

    @test_wrapper('Reconnect Classic HID Stress Test', devices={'MOUSE': 1})
    def sr_reconnect_classic_hid_stress(self):
        """ Reconnects a classic HID device after suspend/resume. """
        device_type = 'MOUSE'
        device = self.devices[device_type][0]
        self.run_reconnect_device(
                [(device_type, device, self._test_mouse)],
                iterations=STRESS_ITERATIONS)

    @test_wrapper('Reconnect LE HID Stress Test', devices={'BLE_MOUSE': 1})
    def sr_reconnect_le_hid_stress(self):
        """ Reconnects a LE HID device after suspend/resume. """
        device_type = 'BLE_MOUSE'
        device = self.devices[device_type][0]
        self.run_reconnect_device(
                [(device_type, device, self._test_mouse)],
                iterations=STRESS_ITERATIONS)

    @test_wrapper('Reconnect A2DP',
                  devices={'BLUETOOTH_AUDIO': 1},
                  skip_chipsets=SUSPEND_POWER_DOWN_CHIPSETS,
                  supports_floss=True)
    def sr_reconnect_a2dp(self):
        """ Reconnects an A2DP device after suspend/resume. """
        device_type = 'BLUETOOTH_AUDIO'
        device = self.devices[device_type][0]
        self.initialize_bluetooth_audio(device, A2DP)
        self.run_reconnect_device(
                [(device_type, device, self.test_device_a2dp_connected)],
                auto_reconnect=True)


    @test_wrapper('Peer wakeup Classic HID',
                  devices={'MOUSE': 1},
                  skip_models=TABLET_MODELS + SUSPEND_POWER_DOWN_MODELS,
                  skip_chipsets=SUSPEND_POWER_DOWN_CHIPSETS,
                  supports_floss=True)
    def sr_peer_wake_classic_hid(self):
        """ Use classic HID device to wake from suspend. """
        device = self.devices['MOUSE'][0]
        self.run_peer_wakeup_device('MOUSE',
                                    device,
                                    device_test=self._test_mouse)

    @test_wrapper('Peer wakeup dark resume Classic HID',
                  devices={'MOUSE': 1},
                  skip_models=TABLET_MODELS + SUSPEND_POWER_DOWN_MODELS,
                  skip_chipsets=SUSPEND_POWER_DOWN_CHIPSETS,
                  supports_floss=True)
    def sr_peer_wake_dark_resume_classic_hid(self):
        """ Use classic HID device to wake from suspend with dark resume enabled. """
        device = self.devices['MOUSE'][0]
        self.run_peer_wakeup_device('MOUSE',
                                    device,
                                    device_test=self._test_mouse,
                                    dark_resume=True)

    @test_wrapper('Peer wakeup LE HID',
                  devices={'BLE_MOUSE': 1},
                  skip_models=TABLET_MODELS + SUSPEND_POWER_DOWN_MODELS,
                  skip_chipsets=SUSPEND_POWER_DOWN_CHIPSETS,
                  supports_floss=True)
    def sr_peer_wake_le_hid(self):
        """ Use LE HID device to wake from suspend. """
        device = self.devices['BLE_MOUSE'][0]
        self.run_peer_wakeup_device('BLE_MOUSE',
                                    device,
                                    device_test=self._test_mouse)

    @test_wrapper('Peer wakeup dark resume LE HID',
                  devices={'BLE_MOUSE': 1},
                  skip_models=TABLET_MODELS + SUSPEND_POWER_DOWN_MODELS,
                  skip_chipsets=SUSPEND_POWER_DOWN_CHIPSETS,
                  supports_floss=True)
    def sr_peer_wake_dark_resume_le_hid(self):
        """ Use LE HID device to wake from suspend with dark resume enabled. """
        device = self.devices['BLE_MOUSE'][0]
        self.run_peer_wakeup_device('BLE_MOUSE',
                                    device,
                                    device_test=self._test_mouse,
                                    dark_resume=True)

    @test_wrapper('Peer wakeup LE HID with reconnect LE HID',
                  devices={
                          'BLE_MOUSE': 1,
                          'BLE_KEYBOARD': 1
                  },
                  skip_models=TABLET_MODELS + SUSPEND_POWER_DOWN_MODELS,
                  skip_chipsets=SUSPEND_POWER_DOWN_CHIPSETS,
                  supports_floss=True)
    def sr_peer_wake_le_hid_reconnect_le_hid(self):
        """ Use LE HID device to wake from suspend. And reconnects a secondary
            LE HID device afterwards
        """
        device = self.devices['BLE_MOUSE'][0]
        device_reconnect = self.devices['BLE_KEYBOARD'][0]

        self.assert_discover_and_pair(device_reconnect)
        self.test_device_set_discoverable(device_reconnect, False)
        self.test_connection_by_adapter(device_reconnect.address)
        self._test_keyboard_with_string(device_reconnect)

        self.run_peer_wakeup_device('BLE_MOUSE',
                                    device,
                                    device_test=self._test_mouse,
                                    keep_paired=True)

        self.test_device_set_discoverable(device_reconnect, True)
        self.test_device_is_connected(device_reconnect.address)
        self._test_keyboard_with_string(device_reconnect)


    @test_wrapper('Peer wakeup Classic HID',
                  devices={'MOUSE': 1},
                  skip_models=TABLET_MODELS + SUSPEND_POWER_DOWN_MODELS,
                  skip_chipsets=SUSPEND_POWER_DOWN_CHIPSETS)
    def sr_peer_wake_classic_hid_stress(self):
        """ Use classic HID device to wake from suspend. """
        device = self.devices['MOUSE'][0]
        self.run_peer_wakeup_device('MOUSE',
                                    device,
                                    device_test=self._test_mouse,
                                    iterations=STRESS_ITERATIONS)

    @test_wrapper('Peer wakeup LE HID',
                  devices={'BLE_MOUSE': 1},
                  skip_models=TABLET_MODELS + SUSPEND_POWER_DOWN_MODELS,
                  skip_chipsets=SUSPEND_POWER_DOWN_CHIPSETS)
    def sr_peer_wake_le_hid_stress(self):
        """ Use LE HID device to wake from suspend. """
        device = self.devices['BLE_MOUSE'][0]
        self.run_peer_wakeup_device('BLE_MOUSE',
                                    device,
                                    device_test=self._test_mouse,
                                    iterations=STRESS_ITERATIONS)

    @test_wrapper('Peer wakeup with A2DP should fail',
                  devices={'BLUETOOTH_AUDIO': 1},
                  skip_chipsets=SUSPEND_POWER_DOWN_CHIPSETS,
                  supports_floss=True)
    def sr_peer_wake_a2dp_should_fail(self):
        """ Use A2DP device to wake from suspend and fail. """
        device_type = 'BLUETOOTH_AUDIO'
        device = self.devices[device_type][0]
        self.initialize_bluetooth_audio(device, A2DP)
        self.run_peer_wakeup_device(
                device_type,
                device,
                device_test=self.test_device_a2dp_connected,
                should_wake=False)

    # ---------------------------------------------------------------
    # Suspend while discovering and advertising
    # ---------------------------------------------------------------

    @test_wrapper('Suspend while discovering',
                  devices={'BLE_MOUSE': 1},
                  skip_models=SUSPEND_POWER_DOWN_MODELS,
                  skip_chipsets=SUSPEND_POWER_DOWN_CHIPSETS,
                  supports_floss=True)
    def sr_while_discovering(self):
        """ Suspend while discovering. """
        device = self.devices['BLE_MOUSE'][0]
        boot_id = self.host.get_boot_id()

        self.test_device_set_discoverable(device, True)

        # Test discovery without setting discovery filter
        # ----------------------------------------------------------------------
        suspend = self.suspend_async(suspend_time=EXPECT_NO_WAKE_SUSPEND_SEC)
        start_time = self.bluetooth_facade.get_device_utc_time()

        # We don't pair to the peer device because we don't want it in the
        # allowlist. However, we want an advertising peer in this test
        # responding to the discovery requests.
        self.test_start_discovery()
        self.test_suspend_and_wait_for_sleep(suspend,
                                             sleep_timeout=SUSPEND_SEC)

        # If discovery events wake us early, we will raise and suspend.exitcode
        # will be non-zero
        self.test_wait_for_resume(boot_id,
                                  suspend,
                                  resume_timeout=EXPECT_NO_WAKE_SUSPEND_SEC,
                                  test_start_time=start_time)

        # Discovering should restore after suspend
        self.test_is_discovering()
        self.test_stop_discovery()

        # Test discovery with discovery filter set
        # ----------------------------------------------------------------------
        suspend = self.suspend_async(suspend_time=EXPECT_NO_WAKE_SUSPEND_SEC)
        start_time = self.bluetooth_facade.get_device_utc_time()

        # SetDiscoveryFilter was used for catching a regression around suspend
        # on BlueZ. It won't be implemented on Floss.
        if not self.floss:
            self.test_set_discovery_filter({'Transport': 'auto'})
        self.test_start_discovery()
        self.test_suspend_and_wait_for_sleep(suspend,
                                             sleep_timeout=SUSPEND_SEC)

        # If discovery events wake us early, we will raise and suspend.exitcode
        # will be non-zero
        self.test_wait_for_resume(boot_id,
                                  suspend,
                                  resume_timeout=EXPECT_NO_WAKE_SUSPEND_SEC,
                                  test_start_time=start_time)

        # Discovering should restore after suspend
        self.test_is_discovering()
        self.test_stop_discovery()

    @test_wrapper('Suspend while advertising',
                  devices={'MOUSE': 1},
                  skip_models=SUSPEND_POWER_DOWN_MODELS,
                  skip_chipsets=SUSPEND_POWER_DOWN_CHIPSETS,
                  supports_floss=True)
    def sr_while_advertising(self):
        """ Suspend while advertising. """
        device = self.devices['MOUSE'][0]
        boot_id = self.host.get_boot_id()
        suspend = self.suspend_async(suspend_time=EXPECT_NO_WAKE_SUSPEND_SEC)
        start_time = self.bluetooth_facade.get_device_utc_time()

        self.test_discoverable()
        self.test_suspend_and_wait_for_sleep(suspend,
                                             sleep_timeout=SUSPEND_SEC)

        # Peer device should not be able to discover us in suspend
        self.test_discover_by_device_fails(device)

        self.test_wait_for_resume(boot_id,
                                  suspend,
                                  resume_timeout=EXPECT_NO_WAKE_SUSPEND_SEC,
                                  test_start_time=start_time)

        # Test that we are properly discoverable again
        self.test_is_discoverable()
        self.test_discover_by_device(device)

        self.test_nondiscoverable()

    # ---------------------------------------------------------------
    # Health checks
    # ---------------------------------------------------------------

    @test_wrapper('Suspend while powered off',
                  devices={'MOUSE': 1},
                  supports_floss=True)
    def sr_while_powered_off(self):
        """ Suspend while adapter is powered off. """
        device = self.devices['MOUSE'][0]
        boot_id = self.host.get_boot_id()
        suspend = self.suspend_async(suspend_time=SUSPEND_SEC)
        start_time = self.bluetooth_facade.get_device_utc_time()

        # Pair device so we have something to do in suspend
        self.assert_discover_and_pair(device)

        # Trigger power down and quickly suspend
        self.test_power_off_adapter()
        self.test_suspend_and_wait_for_sleep(suspend,
                                             sleep_timeout=SUSPEND_SEC)
        # Suspend and resume should succeed
        self.test_wait_for_resume(boot_id,
                                  suspend,
                                  resume_timeout=SUSPEND_SEC,
                                  test_start_time=start_time)

        # We should be able to power it back on
        self.test_power_on_adapter()

        # Test that we can reconnect to the device after powering back on
        self.test_connection_by_device(device)

    @test_wrapper('Suspend while receiving BQR test',
                  devices={
                          'BLUETOOTH_AUDIO': 1,
                          'KEYBOARD': 1
                  },
                  flags=['Quick Health'],
                  skip_models=SUSPEND_POWER_DOWN_MODELS,
                  skip_chipsets=QR_UNSUPPORTED_CHIPSETS +
                  SUSPEND_POWER_DOWN_CHIPSETS)
    def sr_while_receiving_bqr(self):
        """Suspend while receiving BQR to check the health."""
        audio_device = self.devices['BLUETOOTH_AUDIO'][0]
        keyboard_device = self.devices['KEYBOARD'][0]
        devices = (audio_device, keyboard_device)
        test_profile = A2DP
        start_time = self.bluetooth_facade.get_device_utc_time()

        # Enable BQR
        self.qr_enable_quality_report()
        self.dut_btmon_log_path = self.start_new_btmon()

        try:
            # Connecting to all devices
            for device in devices:
                if device.device_type == 'BLUETOOTH_AUDIO':
                    self.initialize_bluetooth_audio(device, test_profile)

                self.test_discover_device(device.address)
                self.test_pairing(device.address, device.pin, trusted=True)
                self.test_connection_by_device(device)
                time.sleep(2)

            # Connect to the audio device with A2DP profile.
            self.test_device_a2dp_connected(audio_device)

            # Checking the bqr logs before suspend/resume.
            time.sleep(QR_EVENT_PERIOD * 2)
            self.test_send_log()
            self.check_qr_event_log(num_devices=len(devices))

            # Starting to suspend/resume.
            boot_id = self.host.get_boot_id()
            suspend = self.suspend_async(suspend_time=SUSPEND_SEC)
            self.test_suspend_and_wait_for_sleep(suspend,
                                                 sleep_timeout=SUSPEND_SEC)

            self.test_wait_for_resume(boot_id,
                                      suspend,
                                      resume_timeout=SUSPEND_SEC,
                                      test_start_time=start_time)

            # Open a 2nd btmon log for BQR log checking.
            self.dut_btmon_log_path = self.start_new_btmon()

            # After suspend/resume DUT should be able to connect to devices.
            # Expect the A2DP devices are connected after suspend/resume.
            self.test_connection_by_device(keyboard_device)

            self.test_device_a2dp_connected(audio_device)

            # Checking the bqr logs after suspend/resume.
            time.sleep(QR_EVENT_PERIOD * 2)
            self.test_send_log()
            self.check_qr_event_log(num_devices=len(devices))
        finally:
            for device in devices:
                if device.device_type == 'BLUETOOTH_AUDIO':
                    self.cleanup_bluetooth_audio(device, test_profile)
                self.test_remove_pairing(device.address)
            self.qr_disable_quality_report()

    def _sr_suspend_delay(self, devices, enable_BQR):
        """Suspend with a delay to check the health.

        @param enable_BQR: to enable BQR for testing.
        """
        boot_id = self.host.get_boot_id()
        audio_test_profile = A2DP

        # Enable BQR
        if enable_BQR:
            self.qr_enable_quality_report()

        try:
            # Connecting to all devices
            for device in devices:
                if device.device_type == 'BLUETOOTH_AUDIO':
                    self.initialize_bluetooth_audio(device, audio_test_profile)

                self.test_discover_device(device.address)
                self.test_pairing(device.address, device.pin, trusted=True)
                self.test_connection_by_device(device)
                time.sleep(2)

                # Connect to the audio device with A2DP profile.
                if device.device_type == 'BLUETOOTH_AUDIO':
                    self.test_device_a2dp_connected(device)

            # Start the suspend delay thread
            suspend_delay_thread = self.suspend_delay_async(
                    SUSPEND_DELAY_FOR_QR_SECS,
                    SUSPEND_DELAY_TIMEOUT_FOR_QR_SECS,
                    WAKEUP_TIMEOUT_FOR_QR_SECS)
            start_time = self.bluetooth_facade.get_device_utc_time()

            # Trigger suspend, wait for regular resume. Verify the system
            # can suspend and resume correctly.
            self.test_suspend_and_wait_for_sleep(suspend_delay_thread,
                                                 sleep_timeout=SUSPEND_SEC)
            self.test_wait_for_resume(boot_id,
                                      suspend_delay_thread,
                                      resume_timeout=RESUME_TIMEOUT_FOR_QR_SECS,
                                      test_start_time=start_time)

        finally:
            # Disable BQR if it is enabled.
            if enable_BQR:
                self.qr_disable_quality_report()

            for device in devices:
                if device.device_type == 'BLUETOOTH_AUDIO':
                    self.cleanup_bluetooth_audio(device, audio_test_profile)
                self.test_remove_pairing(device.address)

    @test_wrapper('Suspend with a delay',
                  devices={
                          'BLUETOOTH_AUDIO': 1,
                          'BLE_MOUSE': 1
                  },
                  flags=['Quick Health'])
    def sr_suspend_delay(self):
        """Suspend with a delay to check the health.

        In this test, the BQR feature is not enabled. Hence, this test is
        expected to execute on all DUTs.
        """
        audio_device = self.devices['BLUETOOTH_AUDIO'][0]
        ble_mouse_device = self.devices['BLE_MOUSE'][0]
        devices = (audio_device, ble_mouse_device)
        self._sr_suspend_delay(devices, enable_BQR=False)

    @test_wrapper('Suspend with a delay while receiving BQR test',
                  devices={
                          'BLUETOOTH_AUDIO': 1,
                          'KEYBOARD': 1
                  },
                  skip_models=SUSPEND_POWER_DOWN_MODELS,
                  skip_chipsets=QR_UNSUPPORTED_CHIPSETS +
                  SUSPEND_POWER_DOWN_CHIPSETS)
    def sr_suspend_delay_while_receiving_bqr(self):
        """Suspend with a delay while receiving BQR to check the health."""
        audio_device = self.devices['BLUETOOTH_AUDIO'][0]
        keyboard_device = self.devices['KEYBOARD'][0]
        devices = (audio_device, keyboard_device)
        self._sr_suspend_delay(devices, enable_BQR=True)

    @batch_wrapper('SR with Peer Health')
    def sr_health_batch_run(self, num_iterations=1, test_name=None):
        """ Batch of suspend/resume peer health tests. """
        self.sr_reconnect_classic_hid()
        self.sr_reconnect_le_hid()
        self.sr_peer_wake_classic_hid()
        self.sr_peer_wake_le_hid()
        self.sr_while_discovering()
        self.sr_while_advertising()
        self.sr_while_receiving_bqr()
        # Promote the sr_suspend_delay test later when proving to be stable.
        # self.sr_suspend_delay()
        self.sr_suspend_delay_while_receiving_bqr()
        self.sr_reconnect_multiple_classic_hid()
        self.sr_reconnect_multiple_le_hid()
        self.sr_reconnect_multiple_classic_le_hid()

    def run_once(self,
                 host,
                 num_iterations=1,
                 args_dict=None,
                 test_name=None,
                 flag='Quick Health',
                 floss=False,
                 floss_lm_quirk=False):
        """Running Bluetooth adapter suspend resume with peer autotest.

        @param host: the DUT, usually a chromebook
        @param num_iterations: the number of times to execute the test
        @param test_name: the test to run or None for all tests
        @param flag: run tests with this flag (default: Quick Health)

        """

        # Initialize and run the test batch or the requested specific test
        self.quick_test_init(host,
                             use_btpeer=True,
                             flag=flag,
                             args_dict=args_dict,
                             floss=floss,
                             floss_lm_quirk=floss_lm_quirk)
        self.sr_health_batch_run(num_iterations, test_name)
        self.quick_test_cleanup()
