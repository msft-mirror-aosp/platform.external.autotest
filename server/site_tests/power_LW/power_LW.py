# Lint as: python2, python3
# Copyright 2020 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
import logging


from autotest_lib.client.common_lib import error
from autotest_lib.client.common_lib import utils
from autotest_lib.client.common_lib.cros import force_discharge_utils
from autotest_lib.server import autotest
from autotest_lib.server import test
from autotest_lib.server.hosts import factory


class power_LW(test.test):
    """Wrapper test around a client test for power lab."""
    version = 1

    SERVO_V4_ETH_VENDOR = '0bda'
    SERVO_V4_ETH_PRODUCT = '8153'
    WIFI_SSID = 'powertest_ap'
    WIFI_PASSWORD = 'chromeos'

    def _get_wlan_ip(self, host):
        """Connect to wifi and return wlan ip address."""
        wlan_ip = host.get_wlan_ip()
        logging.info('wlan_ip=%s', wlan_ip)
        if wlan_ip:
            return wlan_ip

        if not host.connect_to_wifi(self.WIFI_SSID, self.WIFI_PASSWORD):
            logging.info('Script to connect to wifi is probably missing.'
                         'Run stub_Pass as a workaround to install it.')
            autotest_client = autotest.Autotest(host)
            autotest_client.run_test('stub_Pass')
            if not host.connect_to_wifi(self.WIFI_SSID, self.WIFI_PASSWORD):
                raise error.TestError('Can not connect to wifi.')

        wlan_ip = host.get_wlan_ip()
        logging.info('After connected to wifi wlan_ip=%s', wlan_ip)
        if not wlan_ip:
            raise error.TestError('Can not find wlan ip.')
        return wlan_ip

    def _get_wlan_host(self, host, machine):
        """Return CrosHost object that use wifi."""
        wlan_ip = self._get_wlan_ip(host)
        if machine['hostname'] == wlan_ip:
            return host

        hostname = wlan_ip
        if utils.host_is_in_power_lab(machine['hostname']):
            hostname = utils.get_power_lab_wlan_hostname(machine['hostname'])

        wlan_machine = machine.copy()
        wlan_machine['hostname'] = hostname
        return factory.create_host(wlan_machine)

    def _start_servo_usb_and_ethernet(self, host, wlan_host):
        if host.servo and host.servo.supports_usb_mux_control():
            host.servo.set_usb_mux('on')
            # Restore the prior USB3 state.
            if (host.servo.supports_usb3_control()
                        and self._usb3_state == 'allowed/enabled'):
                host.servo.set_usb3_control('enable')
        else:
            # Reboot to restore USB ethernet if it was stopped via unbind.
            wlan_host.reboot()

    def _stop_servo_usb_and_ethernet(self, host, wlan_host):
        """Find and unbind servo v4 usb and ethernet."""
        # Stop check_ethernet.hook to reconnect the usb device
        try:
            host.run('stop recover_duts')
        except:
            logging.warning("Continue if stop recover_duts failed.")

        try:
            # Turn off the servo USB connection (which includes ethernet) by
            # default.
            if host.servo and host.servo.supports_usb_mux_control():
                host.servo.set_usb_mux('off')

                # Also disable USB3 if it's on.
                if host.servo.supports_usb3_control():
                    self._usb3_state = host.servo.get_usb3_control()
                    if self._usb3_state == 'allowed/enabled':
                        host.servo.set_usb3_control('disable')
            elif host != wlan_host:
                # Fall back to unbinding the USB device for ethernet if eth
                # power control isn't supported on the servo.
                eth_usb = host.find_usb_devices(self.SERVO_V4_ETH_VENDOR,
                                                self.SERVO_V4_ETH_PRODUCT)
                if len(eth_usb) == 1 and eth_usb[0] and host.get_wlan_ip():
                    host.unbind_usb_device(eth_usb[0])

        except Exception as e:
            self._start_servo_usb_and_ethernet(host, wlan_host)
            raise e

    def run_once(self, host, test, args, machine):
        """Prepare DUT for power test then run the client test.

        The DUT will
        - Switch from ethernet connection to wifi.
        - Power off Servo v4 USB and ethernet devices.
        - Set EC to force discharge during the client test.

        @param host: CrosHost object representing the DUT.
        @param test: testname
        @param args: arguments of the test in a dict.
        @param machine: machine dict of the host.
        """
        wlan_host = self._get_wlan_host(host, machine)
        self._stop_servo_usb_and_ethernet(host, wlan_host)

        try:
            args['force_discharge'] = True
            args['tag'] = args.get('tag', 'PLW')

            autotest_client = autotest.Autotest(wlan_host)
            autotest_client.run_test(test, check_client_result=True, **args)
        finally:
            self._start_servo_usb_and_ethernet(host, wlan_host)
            if not host.wait_up(timeout=30):
                logging.warning("ethernet connection did not return.")
                host.servo.usb_mux_reset()
                host.servo.usb3_control_reset()
                force_discharge_utils.charge_control_by_ectool(True,
                                                               host=wlan_host)
            else:
                force_discharge_utils.charge_control_by_ectool(True, host=host)
