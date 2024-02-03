# Lint as: python2, python3
# Copyright 2022 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Server side bluetooth tests on LL Privacy"""

from autotest_lib.client.common_lib import error
from autotest_lib.server.cros.bluetooth import bluetooth_adapter_tests

import logging
import time
import threading

PROFILE_CONNECT_WAIT_SEC = 15
EXPECT_PEER_WAKE_SUSPEND_SEC = 60
PEER_WAKE_RESUME_TIMEOUT_SEC = 30
DEVICE_CONNECT_TIMEOUT_SEC = 20
SUSPEND_TIMEOUT_SEC = 15
DEFAULT_RPA_TIMEOUT_SEC = 900
MIN_RPA_TIMEOUT_SEC = 30

DEVICE_CONNECTED_TIMEOUT = 45

LOG_PEER_RANDOM = 'Peer address type: Random (0x01)'
LOG_PEER_RESOLVED_PUBLIC = 'Peer address type: Resolved Public (0x02)'

class BluetoothAdapterLLPrivacyTests(
        bluetooth_adapter_tests.BluetoothAdapterTests):
    """Server side bluetooth adapter ll privacy Test.

    This class comprises a number of test cases to verify bluetooth
    LL privacy.
    """

    test_case_log = bluetooth_adapter_tests.test_case_log
    test_retry_and_log = bluetooth_adapter_tests.test_retry_and_log

    def run_hid_wakeup_with_rpa(self, device, device_test=None, iterations=1):
        """ Uses paired peer HID device which is in privacy mode to wake
        from suspend.

        @param device: the meta device with the paired device
        @param device_test: What to test to run after waking and connecting the
                            adapter/host
        @param iterations: Number of suspend + peer wake loops to run
        """
        boot_id = self.host.get_boot_id()

        sleep_time = EXPECT_PEER_WAKE_SUSPEND_SEC
        resume_timeout = PEER_WAKE_RESUME_TIMEOUT_SEC
        measure_resume = True

        # Clear wake before testing
        self.test_adapter_set_wake_disabled()

        # Reduce RPA timeout
        self.test_update_rpa_timeout(device, MIN_RPA_TIMEOUT_SEC)

        self.test_set_device_privacy(device, True)
        self.test_start_device_advertise_with_rpa(device)
        curr_addr = device.GetRandomAddress()
        self.test_discover_device(device.rpa)

        time.sleep(self.TEST_SLEEP_SECS)
        self.test_pairing_with_rpa(device)
        self.test_stop_device_advertise_with_rpa(device)

        self.test_device_is_connected(device.init_paired_addr,
                                      timeout=DEVICE_CONNECT_TIMEOUT_SEC,
                                      identity_address=device.address)

        # Profile connection may not have completed yet and this will
        # race with a subsequent disconnection (due to suspend). Use the
        # device test to force profile connect or wait if no test was
        # given.
        if device_test is not None:
            self.assert_on_fail(device_test(device))
        else:
            time.sleep(PROFILE_CONNECT_WAIT_SEC)

        try:
            for it in range(iterations):
                logging.info(
                        'Running iteration {}/{} of suspend peer wake'.format(
                                it + 1, iterations))

                # Wait for RPA rotation
                logging.info("Wait %d seconds for RPA rotation.",
                             MIN_RPA_TIMEOUT_SEC)
                time.sleep(MIN_RPA_TIMEOUT_SEC)
                # Start a new suspend instance
                suspend = self.suspend_async(suspend_time=sleep_time,
                                             expect_bt_wake=True)
                start_time = self.bluetooth_facade.get_device_utc_time()

                self.test_device_wake_allowed(device.init_paired_addr,
                                              identity_address=device.address)
                # Also wait until powerd marks adapter as wake enabled
                self.test_adapter_wake_enabled()

                self.bluetooth_facade.btmon_start()

                # Trigger suspend, asynchronously wake and wait for resume
                self.test_suspend_and_wait_for_sleep(
                        suspend, sleep_timeout=SUSPEND_TIMEOUT_SEC)

                def _action_device_connect():
                    time.sleep(5)
                    # Set discoverable causes a short advertisement with public address
                    # this may lead to false positive test result.
                    # TODO: Uprev chameleon set address as random when set discoverable
                    # if privacy is enabled.
                    device.SetDiscoverable(True)
                    device.SetAdvertising(True)

                peer_wake = threading.Thread(target=_action_device_connect)
                peer_wake.start()

                # Expect a quick resume. If a timeout occurs, test fails. Since
                # we delay sending the wake signal, we should accommodate that
                # in our expected timeout.
                resume_success = self.test_wait_for_resume(
                        boot_id,
                        suspend,
                        resume_timeout=resume_timeout,
                        test_start_time=start_time,
                        resume_slack=0,
                        fail_on_timeout=True,
                        fail_early_wake=False,
                        collect_resume_time=measure_resume)

                # Finish peer wake process
                peer_wake.join()

                self.bluetooth_facade.btmon_stop()
                # Set the test NA if the controller received a public
                # address advertisement.
                addr_type_str = (LOG_PEER_RESOLVED_PUBLIC
                                 if self.llprivacy else LOG_PEER_RANDOM)
                if resume_success and not self.bluetooth_facade.btmon_find(
                        addr_type_str):
                    raise error.TestNAError(
                            "Peer address is not {}".format(addr_type_str))

                prev_addr = curr_addr
                curr_addr = device.GetRandomAddress()
                if prev_addr == curr_addr:
                    logging.info(
                            "RPA does not rotate. Using old address to reconnect."
                    )
                else:
                    logging.info("New RPA address: {}".format(curr_addr))

                # Make sure we're actually connected
                self.test_device_is_connected(
                        device.init_paired_addr,
                        timeout=DEVICE_CONNECT_TIMEOUT_SEC,
                        identity_address=device.address)
                # Verify the profile is working
                if device_test is not None:
                    device_test(device)

                self.test_stop_device_advertise_with_rpa(device)
        finally:
            # test_wait_for_resume can throw exception
            if peer_wake is not None and peer_wake.is_alive():
                peer_wake.join()
            self.test_remove_pairing(device.init_paired_addr,
                                     identity_address=device.address)
            # Restore privacy setting
            self.test_set_device_privacy(device, False)
            # Restore RPA timeout
            self.test_update_rpa_timeout(device, DEFAULT_RPA_TIMEOUT_SEC)

    @test_retry_and_log(False)
    def test_set_device_privacy(self, device, enable):
        """Test privacy mode has been enabled."""
        status = device.SetPrivacy(enable)
        # b:317736407 wait for a short delay so the own address type is set
        # correctly in the gatt server after bluetooth power toggle.
        time.sleep(0.5)
        return status

    @test_retry_and_log(False)
    def test_start_device_advertise_with_rpa(self, device):
        """Set discoverable, enable LE advertising, check random address is generated"""
        device.SetDiscoverable(True)
        advertising = device.SetAdvertising(True)
        after_address = device.GetRandomAddress()
        if isinstance(device.rpa, str):
            logging.debug('RPA updated: %r', device.rpa != after_address)
        self.results = {
                'set_advertising': advertising,
                'not_empty_addr': after_address != "00:00:00:00:00:00",
                'not_public': after_address != device.address,
        }
        device.rpa = after_address
        logging.info('Start device advertising with: %s', after_address)
        return all(self.results.values())

    @test_retry_and_log(False)
    def test_stop_device_advertise_with_rpa(self, device):
        """Stop LE advertising, set not discoverable, remove RPA from device"""
        logging.info('Stop device advertising with: %s', device.rpa)
        advertising = device.SetAdvertising(False)
        device.SetDiscoverable(False)
        device.rpa = None
        return advertising

    @test_retry_and_log(False)
    def test_power_cycle_with_address_resolution(self):
        """Check use resolving list. A device should be paired before running
        the power cycle.

        Steps:
        - Pair device with IRK/RPA. This step is done before this function by
          calling test_pairing_with_rpa().
        - Power off DUT
        - Power on DUT, check log

        Check the items:
        - Address resolution is enabled
        - Device is added to resolving list
        - Use policy 01 for passive scan
        """
        self.test_power_off_adapter()
        self._get_btmon_log(lambda: self.test_power_on_adapter())

        enable_address_resolution = self.bluetooth_facade.btmon_find(
                'Address resolution: Enabled')

        patterns = [
                '> HCI Event: Command Complete (0x0e)',
                'LE Add Device To Resolving List (0x08|0x0027)',
                'Status: Success (0x00)'
        ]
        add_dev_to_resolv_list = self.bluetooth_facade.btmon_find_consecutive(
                patterns)

        accept_list_pattern = 'Filter policy: Ignore not in accept list (0x01)'
        if self.floss:
            accept_list_pattern = 'Filter policy: Accept list is used (0x01)'
        use_accept_list = self.bluetooth_facade.btmon_find(accept_list_pattern)

        self.results = {
                'enable_address_resolution': enable_address_resolution,
                'add_device_to_resolving_list': add_dev_to_resolv_list,
                'use_accept_list': use_accept_list
        }
        return all(self.results.values())

    def auto_reconnect_loop_with_device_privacy(
            self,
            device,
            loops=1,
            check_connected_method=lambda device: True,
            disconnect_by_device=False,
            rpa_timeout=None):
        """Running a loop to verify the paired device can auto reconnect
        The device is in privacy mode.

        @param device: emulated peer device
        @param loops: number of disconnect/reconnect loops
        @param check_connected_method: method to check the device is connected
        @param disconnect_by_device: disconnect should be initiated by device
        @param rpa_timeout: RPA address rotation timeout in second
        """
        if rpa_timeout is not None:
            logging.info('Set RPA timeout to %d', rpa_timeout)
            self.test_update_rpa_timeout(device, rpa_timeout)
        self.test_set_device_privacy(device, True)

        # start advertising and set RPA
        self.test_start_device_advertise_with_rpa(device)
        previous_rpa = device.rpa
        self.test_discover_device(device.rpa)

        self.test_pairing_with_rpa(device)
        self.test_connection_by_adapter(device.init_paired_addr,
                                        device.address)

        self.test_stop_device_advertise_with_rpa(device)
        self.test_hid_device_created(self._input_dev_uniq_addr(device))
        check_connected_method(device)

        try:
            for i in range(loops):
                logging.info('iteration {} / {}'.format(i + 1, loops))
                if disconnect_by_device:
                    self.test_disconnection_by_device(device)
                else:
                    self.test_power_off_adapter()
                    self.test_power_on_adapter()

                # sleep for rpa_timeout seconds for RPA rotation
                if rpa_timeout is not None:
                    logging.info("Wait %d seconds for RPA rotation.",
                                 rpa_timeout)
                    time.sleep(rpa_timeout)

                self.bluetooth_facade.btmon_start()
                start_time = time.time()
                self.test_start_device_advertise_with_rpa(device)
                # expect RPA rotation
                if rpa_timeout is not None and previous_rpa == device.rpa:
                    logging.warning("RPA does not rotate.")
                previous_rpa = device.rpa

                # Verify that the device is reconnected. Wait for the input device
                # to become available before checking the profile connection.
                connect_status = self.test_device_is_connected(
                        device.init_paired_addr,
                        timeout=DEVICE_CONNECTED_TIMEOUT,
                        identity_address=device.address)
                end_time = time.time()
                time_diff = end_time - start_time

                self.bluetooth_facade.btmon_stop()
                # Set the test NA if the controller received a public
                # address advertisement.
                addr_type_str = (LOG_PEER_RESOLVED_PUBLIC
                                 if self.llprivacy else LOG_PEER_RANDOM)
                if connect_status and not self.bluetooth_facade.btmon_find(
                        addr_type_str):
                    raise error.TestNAError(
                            "Peer address is not {}".format(addr_type_str))

                self.test_hid_device_created(self._input_dev_uniq_addr(device))
                check_connected_method(device)
                logging.info('reconnect time %s', str(time_diff))
                self.test_stop_device_advertise_with_rpa(device)
        finally:
            self.test_remove_pairing(device.init_paired_addr,
                                     identity_address=device.address)
            # Restore privacy setting
            self.test_set_device_privacy(device, False)

            if rpa_timeout is not None:
                self.test_update_rpa_timeout(device, DEFAULT_RPA_TIMEOUT_SEC)
                logging.info('Restore RPA timeout to %d',
                             DEFAULT_RPA_TIMEOUT_SEC)

    @test_retry_and_log(False)
    def test_pairing_with_rpa(self, device):
        """Expect new IRK exchange during pairing and address is resolvable

        Random address: 54:35:24:F9:18:25 (Resolvable)

        @param device: device to pair with RPA stored

        @returns: true if IRK received and address is resolvable
        """
        # Device must advertise with RPA
        device_has_rpa = isinstance(device.rpa, str)
        self.results = {
                'device_has_rpa': device_has_rpa,
                'addr_resolvable': False
        }
        if not device_has_rpa:
            logging.error("Device has no RPA set. Start LE advertising first.")
            return False

        device.init_paired_addr = device.rpa
        self._get_btmon_log(lambda: self.test_pairing(device.rpa,
                                                      device.pin,
                                                      trusted=True,
                                                      identity_address=device.
                                                      address))

        self.results['addr_resolvable'] = self.bluetooth_facade.btmon_find(
                device.rpa + ' (Resolvable)')

        return all(self.results.values())

    @test_retry_and_log(False)
    def test_random_address_updated(self, device, should_update=True):
        """Check if RPA has changed for the device and update rpa in device."""
        if not isinstance(device.rpa, str):
            logging.error("RPA has not been set by start advertising.")
            return False
        old_random_address = device.rpa
        self.test_stop_device_advertise_with_rpa(device)
        self.test_start_device_advertise_with_rpa(device)
        self.results = {
                'old_rpa': old_random_address,
                'new_rpa': device.rpa,
        }
        updated = old_random_address != device.rpa
        return should_update == updated

    @test_retry_and_log(False)
    def test_update_rpa_timeout(self, device, test_timeout):
        """Test RPA timeout has been changed to test value."""
        if test_timeout < 30 or test_timeout > 3600:
            logging.error('RPA timeout must be in range [30, 3600]')
            return False

        self.results = {'test_timeout': test_timeout}
        old_timeout = device.GetRPATimeout()
        device.SetRPATimeout(test_timeout)
        new_timeout = device.GetRPATimeout()
        self.results['old_timeout'] = old_timeout
        self.results['new_timeout'] = new_timeout
        return new_timeout == test_timeout
