# Lint as: python2, python3
# Copyright 2022 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""A Batch of Bluetooth Quality Report tests"""

import collections
import logging
import time

from autotest_lib.client.common_lib import error
from autotest_lib.client.cros.bluetooth.bluetooth_audio_test_data import (
        A2DP_MEDIUM, HFP_WBS, HFP_NBS, HFP_WBS_MEDIUM, HFP_NBS_MEDIUM)
from autotest_lib.server.cros.bluetooth.bluetooth_adapter_qr_tests import (
        BluetoothAdapterQRTests, QR_UNSUPPORTED_CHIPSETS)
from autotest_lib.server.cros.bluetooth.bluetooth_adapter_quick_tests import (
        BluetoothAdapterQuickTests)


class bluetooth_AdapterQRHealth(BluetoothAdapterQuickTests,
                                BluetoothAdapterQRTests):
    """A Batch of Bluetooth audio health tests"""

    test_wrapper = BluetoothAdapterQuickTests.quick_test_test_decorator
    batch_wrapper = BluetoothAdapterQuickTests.quick_test_batch_decorator

    def run_test_method(self,
                        devices,
                        test_method,
                        test_profile,
                        logging_and_check=True):
        """Common procedure to run a specific test method.

        @param devices: a list of devices.
        @param test_method: the test method to run.
        @param test_profile: audio test profile to use.
        @param logging_and_check: set this to True to opend the quality
                                  report log checking.
        """

        if not isinstance(devices, collections.Iterable):
            devices = (devices, )

        num_devices = len(devices)

        # Make sure WBS profile works fine.
        if test_profile in (HFP_WBS, HFP_WBS_MEDIUM):
            if self.check_wbs_capability():
                if not self.bluetooth_facade.enable_wbs(True):
                    raise error.TestError('failed to enble wbs')
            else:
                raise error.TestNAError(
                        'The DUT does not support WBS. Skip the test.')
        elif test_profile in (HFP_NBS, HFP_NBS_MEDIUM):
            if not self.bluetooth_facade.enable_wbs(False):
                raise error.TestError('failed to disable wbs')

        time.sleep(3)

        self.test_reset_on_adapter()
        self.test_bluetoothd_running()

        for device in devices:
            if device.device_type == 'BLUETOOTH_AUDIO':
                self.initialize_bluetooth_audio(device, test_profile)

            self.test_discover_device(device.address)
            self.test_pairing(device.address, device.pin, trusted=True)
            self.test_connection_by_adapter(device.address)

            time.sleep(2)

        if logging_and_check:
            self.dut_btmon_log_path = self.start_new_btmon()
            self.enable_disable_quality_report(enable=True)
            self.enable_disable_quality_debug_log(enable=True)

        test_method()

        if logging_and_check:
            self.test_send_log()
            self.check_qr_event_log(num_devices=num_devices)
            self.enable_disable_quality_debug_log(enable=False)
            self.enable_disable_quality_report(enable=False)

        for device in devices:
            self.test_disconnection_by_adapter(device.address)

            if device.device_type == 'BLUETOOTH_AUDIO':
                self.cleanup_bluetooth_audio(device, test_profile)

    # Remove flags=['Quick Health'] when this test is migrated to stable suite.
    @test_wrapper('Quality Report A2DP test',
                  devices={'BLUETOOTH_AUDIO': 1},
                  flags=['Quick Health'],
                  skip_chipsets=QR_UNSUPPORTED_CHIPSETS)
    def qr_a2dp_test(self):
        """Quality Report A2DP test"""
        device = self.devices['BLUETOOTH_AUDIO'][0]
        test_profile = A2DP_MEDIUM
        test_method = lambda: self.qr_a2dp(device, test_profile)

        self.run_test_method(device, test_method, test_profile)

    # Remove flags=['Quick Health'] when this test is migrated to stable suite.
    @test_wrapper('Quality Report power cycle and A2DP test',
                  devices={'BLUETOOTH_AUDIO': 1},
                  flags=['Quick Health'],
                  skip_chipsets=QR_UNSUPPORTED_CHIPSETS)
    def qr_power_cycle_a2dp_test(self):
        """Quality Report power cycle and A2DP test"""
        device = self.devices['BLUETOOTH_AUDIO'][0]
        test_profile = A2DP_MEDIUM
        test_method = lambda: self.qr_power_cycle_a2dp(device, test_profile)

        self.run_test_method(device, test_method, test_profile)

    # Remove flags=['Quick Health'] when this test is migrated to stable suite.
    @test_wrapper('Quality Report HFP NBS dut as source test',
                  devices={'BLUETOOTH_AUDIO': 1},
                  flags=['Quick Health'],
                  skip_chipsets=QR_UNSUPPORTED_CHIPSETS)
    def qr_hfp_nbs_dut_as_src_test(self):
        """Quality Report HFP NBS dut as source test"""
        device = self.devices['BLUETOOTH_AUDIO'][0]
        test_profile = HFP_NBS_MEDIUM
        test_method = lambda: self.qr_hfp_dut_as_src(device, test_profile)

        self.run_test_method(device, test_method, test_profile)

    # Remove flags=['Quick Health'] when this test is migrated to stable suite.
    @test_wrapper('Quality Report HFP WBS dut as source test',
                  devices={'BLUETOOTH_AUDIO': 1},
                  flags=['Quick Health'],
                  skip_chipsets=QR_UNSUPPORTED_CHIPSETS)
    def qr_hfp_wbs_dut_as_src_test(self):
        """Quality Report HFP WBS dut as source test"""
        device = self.devices['BLUETOOTH_AUDIO'][0]
        test_profile = HFP_WBS_MEDIUM
        test_method = lambda: self.qr_hfp_dut_as_src(device, test_profile)

        self.run_test_method(device, test_method, test_profile)

    # Remove flags=['Quick Health'] when this test is migrated to stable suite.
    @test_wrapper('Quality Report disabled A2DP test',
                  devices={'BLUETOOTH_AUDIO': 1},
                  flags=['Quick Health'],
                  skip_chipsets=QR_UNSUPPORTED_CHIPSETS)
    def qr_disabled_a2dp_test(self):
        """Quality Report disabled A2DP test"""
        device = self.devices['BLUETOOTH_AUDIO'][0]
        test_profile = A2DP_MEDIUM
        test_method = lambda: self.qr_disabled_a2dp(device, test_profile)

        self.run_test_method(device,
                             test_method,
                             test_profile,
                             logging_and_check=False)

    # Remove flags=['Quick Health'] when this test is migrated to stable suite.
    @test_wrapper('Quality Report A2DP and classic keyboard test',
                  devices={
                          'BLUETOOTH_AUDIO': 1,
                          "KEYBOARD": 1
                  },
                  flags=['Quick Health'],
                  skip_chipsets=QR_UNSUPPORTED_CHIPSETS)
    def qr_a2dp_cl_keyboard_test(self):
        """Quality Report A2DP and classic keyboard test"""
        audio_device = self.devices['BLUETOOTH_AUDIO'][0]
        keyboard_device = self.devices['KEYBOARD'][0]
        test_profile = A2DP_MEDIUM
        test_method = lambda: self.qr_a2dp_cl_keyboard(
                audio_device, keyboard_device, test_profile)

        self.run_test_method((audio_device, keyboard_device),
                             test_method,
                             test_profile)

    # Remove flags=['Quick Health'] when this test is migrated to stable suite.
    @test_wrapper(
            'Quality Report HFP WBS dut as sink and classic keyboard test',
            devices={
                    'BLUETOOTH_AUDIO': 1,
                    'KEYBOARD': 1
            },
            flags=['Quick Health'],
            skip_chipsets=QR_UNSUPPORTED_CHIPSETS)
    def qr_hfp_wbs_dut_as_sink_cl_keyboard_test(self):
        """Quality Report HFP WBS dut as sink and classic keyboard test"""
        audio_device = self.devices['BLUETOOTH_AUDIO'][0]
        keyboard_device = self.devices['KEYBOARD'][0]
        test_profile = HFP_WBS_MEDIUM
        test_method = lambda: self.qr_hfp_dut_as_sink_cl_keyboard(
                audio_device, keyboard_device, test_profile)

        self.run_test_method((audio_device, keyboard_device),
                             test_method,
                             test_profile)

    # Remove flags=['Quick Health'] when this test is migrated to stable suite.
    @test_wrapper(
            'Quality Report HFP NBS dut as sink and classic keyboard test',
            devices={
                    'BLUETOOTH_AUDIO': 1,
                    'KEYBOARD': 1
            },
            flags=['Quick Health'],
            skip_chipsets=QR_UNSUPPORTED_CHIPSETS)
    def qr_hfp_nbs_dut_as_sink_cl_keyboard_test(self):
        """Quality Report HFP NBS dut as sink and classic keyboard test"""
        audio_device = self.devices['BLUETOOTH_AUDIO'][0]
        keyboard_device = self.devices['KEYBOARD'][0]
        test_profile = HFP_NBS_MEDIUM
        test_method = lambda: self.qr_hfp_dut_as_sink_cl_keyboard(
                audio_device, keyboard_device, test_profile)

        self.run_test_method((audio_device, keyboard_device),
                             test_method,
                             test_profile)

    def run_check_states_seq(self, test_name, test_method, expected_states):
        """Framework to run a test for BQR state check.

        It first restarts btmon to clear the BQR toggle history. Then it runs
        the specified test_method. After a short pause, it checks if the BQR
        toggle history is expected.

        @param test_name: the test name
        @param test_method: the test method to run
        @param expected_states: the list of expected BQR toggle history
        """
        logging.info('')
        logging.info('%s %s %s', 6 * '.', test_name, 6 * '.')
        self.dut_btmon_log_path = self.start_new_btmon()
        test_method()
        # the D-Bus method may take near 1 second to arrive the
        # lower layers in the kernel. Wait a while for safety.
        time.sleep(2)
        self.send_btsnoop_log()
        self.test_check_qr_states(expected_states=expected_states)

    # This test does not need a btpeer device.
    # Remove flags=['Quick Health'] when this test is migrated to stable suite.
    @test_wrapper('Quality Report state test',
                  flags=['Quick Health'],
                  skip_chipsets=QR_UNSUPPORTED_CHIPSETS)
    def qr_check_states_test(self):
        """Quality Report check states test

        This test checks whether the bluetooth software stack, including the
        user space daemon and the kernel, enables or disables the Bluetooth
        Quality Report feature correctly under combinations of the following
        conditions:
        - DUT reboots
        - bluetoothd stops and starts
        - the adapter powers off and on
        - the system suspends and resumes

        Note that this test purely verifies the bluetooth software stack
        instead of the controller functionality. Hence, btpeer devices are not
        employed so that the test can verify various scenarios at a reasonable
        speed.
        """
        self.init_check_qr_states()

        # Assume that BQR is disabled initially.
        # When BQR is enabled by default, we will need to modify the ordering of
        # the following tests.
        # - placing the self.test_disable_quality_report test as the first test,
        # - placing the self.test_enable_quality_report test as the last test.

        # At this time, the kernel HCI_QUALITY_REPORT flag is initially false.
        # --------------------------------------------------------------------

        # The expected_states below indicates enable (True) or disable (Flase)
        # actions that are expected to observe in the captured btsnoop logs.
        #
        # Note that expected_states can be [], i.e., empty, because
        # - The kernel won't enable the BQR feature if it is already enabled.
        # - The kernel won't disable the BQR feature if it is already disabled.
        #
        # expected_states=[False] indicates the disabled action is expected.
        # expected_states=[True] indicates the enabled action is expected.
        # expected_states=[False, True] indicates the disabled action followed
        #   by the enabled action is expected, etc.

        # Reboot the DUT so that both the kernel and the user space are in
        # clean states. Do not check the expected_states for two reasons:
        # - There is a race condition regarding whether the btmon log could
        #   capture the BQR disablement command in powering down the machine.
        # - Whether the BQR is enabled on the bluetooth daemon startup is
        #   determined by the options in start_bluetoothd.sh which change
        #   over time.
        self.reboot()

        # Disable BQR so that there is a consistent BQR disabled state.
        # Whether a BQR disablement command can be captured in the btmon log
        # depends on whether BQR is enabled on the bluetooth daemon startup.
        self.test_disable_quality_report()

        # Stop bluetoothd and BQR should remain disabled.
        # expected_states=[] as kernel won't disable the already disabled BQR.
        self.run_check_states_seq('stop bluetoothd when BQR is disabled',
                                  self.test_stop_bluetoothd,
                                  expected_states=[])

        # Start bluetoothd and BQR should remain disabled.
        # expected_states=[] as kernel won't disable the already disabled BQR.
        self.run_check_states_seq('start bluetoothd when BQR is disabled',
                                  self.test_start_bluetoothd,
                                  expected_states=[])

        # Power off the adapter and BQR should remain disabled.
        # expected_states=[] as kernel won't disable the already disabled BQR.
        self.run_check_states_seq('power off the adapter when BQR is disabled',
                                  self.test_power_off_adapter,
                                  expected_states=[])

        # Power on the adapter and BQR should remain disabled.
        # expected_states=[] as kernel won't disable the already disabled BQR.
        self.run_check_states_seq('power on the adapter when BQR is disabled',
                                  self.test_power_on_adapter,
                                  expected_states=[])

        # Do system suspend and resume. BQR should remain disabled.
        # expected_states=[] as kernel won't disable the already disabled BQR.
        self.run_check_states_seq('system suspend and resume when BQR is disabled',
                                  self.suspend_resume,
                                  expected_states=[])

        # Enable BQR and BQR should be enabled.
        self.run_check_states_seq('enable BQR',
                                  self.test_enable_quality_report,
                                  expected_states=[True])

        # Stop bluetoothd and BQR should be disabled.
        self.run_check_states_seq('stop bluetoothd when BQR is enabled',
                                  self.test_stop_bluetoothd,
                                  expected_states=[False])

        # Start bluetoothd and BQR should be enabled.
        self.run_check_states_seq('start bluetoothd when BQR is enabled',
                                  self.test_start_bluetoothd,
                                  expected_states=[True])

        # Power off the adapter and BQR should be disabled.
        self.run_check_states_seq('power off the adapter when BQR is enabled',
                                  self.test_power_off_adapter,
                                  expected_states=[False])

        # Power on the adapter and BQR should be enabled.
        self.run_check_states_seq('power on the adapter when BQR is enabled',
                                  self.test_power_on_adapter,
                                  expected_states=[True])

        # Do system suspend and resume. BQR should be disabled and then re-enabled.
        self.run_check_states_seq('system suspend and resume when BQR is enabled',
                                  self.suspend_resume,
                                  expected_states=[False, True])

        # Disable BQR and BQR should be disabled.
        self.run_check_states_seq('Disable BQR',
                                  self.test_disable_quality_report,
                                  expected_states=[False])

    @batch_wrapper('Bluetooth BQR Batch Health Tests')
    def qr_health_batch_run(self, num_iterations=1, test_name=None):
        """Run the bluetooth audio health test batch or a specific given test.

        @param num_iterations: how many iterations to run
        @param test_name: specific test to run otherwise None to run the
                whole batch
        """
        self.qr_a2dp_test()
        self.qr_power_cycle_a2dp_test()
        self.qr_hfp_nbs_dut_as_src_test()
        self.qr_hfp_wbs_dut_as_src_test()
        self.qr_disabled_a2dp_test()
        self.qr_a2dp_cl_keyboard_test()
        self.qr_hfp_wbs_dut_as_sink_cl_keyboard_test()
        self.qr_hfp_nbs_dut_as_sink_cl_keyboard_test()

    def run_once(self,
                 host,
                 num_iterations=1,
                 args_dict=None,
                 test_name=None,
                 flag='Quick Health'):
        """Run the batch of Bluetooth stand health tests

        @param host: the DUT, usually a chromebook
        @param num_iterations: the number of rounds to execute the test
        @param test_name: the test to run, or None for all tests
        """
        self.host = host

        # The btpeers are not needed in the qr_check_states_test.
        use_btpeer_flag = (test_name != 'qr_check_states_test')
        self.quick_test_init(host,
                             use_btpeer=use_btpeer_flag,
                             flag=flag,
                             args_dict=args_dict)
        self.qr_health_batch_run(num_iterations, test_name)
        self.quick_test_cleanup()
