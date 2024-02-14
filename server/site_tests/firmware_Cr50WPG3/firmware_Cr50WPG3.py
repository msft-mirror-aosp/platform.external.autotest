# Copyright 2019 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import logging
import re
import time

from autotest_lib.client.common_lib import error
from autotest_lib.server.cros.faft.cr50_test import Cr50Test


class firmware_Cr50WPG3(Cr50Test):
    """Verify WP in G3."""
    version = 1

    WAIT_FOR_STATE = 20
    CMD_FIND_WP_GPIO = 'ectool gpioget | grep -i wp | grep -vi cbi'
    WP_REGEX = r'WP status: ((en|dis)abled)'
    STATUS_CMD = '--wp-status --ignore-hw'
    WP_ENABLE_CMD = '--wp-enable'
    WP_DISABLE_CMD = '--wp-disable'
    DISABLED = 'disabled'
    ENABLED = 'enabled'
    CUSTOM_RST = ',custom_rst=true'

    def cleanup(self):
        """Reenable servo wp."""
        self.gsc.send_command('ccd testlab open')
        try:
            # Reset the WP state.
            if hasattr(self, '_start_fw_wp_vref'):
                self.set_gsc_hw_wp('disable atboot')
                self.ccd_set_sw_wp(self.WP_DISABLE_CMD)
                self.set_gsc_hw_wp('follow_batt_pres atboot')
                self.servo.set_nocheck('fw_wp_state', self._start_fw_wp_state)
                if self._start_fw_wp_vref:
                    self.servo.set_nocheck('fw_wp_vref', self._start_fw_wp_vref)
            self.gsc.send_command('rddkeepalive disable')
            self.enable_servo_ec_uart()
        finally:
            super(firmware_Cr50WPG3, self).cleanup()

    def generate_futility_wp_cmd(self):
        """Use the cr50 serialname to generate the futility command."""
        self._futility_cmd = (
                'sudo futility flash -p raiden_debug_spi:target=AP,serial=%s%s '
                % (self.gsc.get_serial(),
                   self.CUSTOM_RST if self._use_custom_rst else ''))

    def ccd_get_sw_wp(self):
        """Returns 'on' if write protect is enabled. 'off' if it's disabled."""
        output = self.servo.system_output(self._futility_cmd + self.STATUS_CMD)
        m = re.search(self.WP_REGEX, output)
        logging.info('SW WP is %s', m.group(1) if m else 'UKNOWN')
        logging.info('futility output\n%s', output)
        if not m:
            raise error.TestError(
                    'Unable to find WP status in futility output')
        return m.group(1)

    def ccd_set_sw_wp(self, cmd):
        """Set SW WP."""
        self.enable_ccd_spi()
        time.sleep(self.gsc.SHORT_WAIT)
        output = self.servo.system_output(self._futility_cmd + cmd,
                                          ignore_status=True)
        logging.debug('SW WP output: %r', output)
        time.sleep(self.gsc.SHORT_WAIT)
        sw_wp = self.ccd_get_sw_wp()
        # Done with ccd spi access. Reenable servo ec uart access.
        self.enable_servo_ec_uart()
        return sw_wp

    def find_ec_wp_gpio_name(self):
        """Find the EC WP gpio name from ectool gpioget."""
        self.wp_gpio = None
        result = self.host.run(self.CMD_FIND_WP_GPIO).stdout.strip()
        logging.info('WP gpio output: %s', result)
        if len(result.splitlines()) > 1:
            logging.info('Too many wp lines.')
            return
        self.wp_gpio = result.split()[1]
        logging.info('WP GPIO: %s', self.wp_gpio)

    def get_ec_hw_wp(self):
        """Check the WP GPIO from the EC console."""
        if not self.wp_gpio:
            return
        for i in range(3):
            try:
                rv = self.ec.send_command_get_output(
                        'gpioget %s' % self.wp_gpio,
                        ['gpioget.*([01]).*%s.*>' % self.wp_gpio])[0][1]
                logging.info('EC %s: %s', self.wp_gpio, rv)
                return
            except Exception as e:
                logging.info('Issue getting ec wp: %s', e)

    def set_ccd_cpu_fw_spi(self, state):
        """Set ccd_cpu_fw_spi if the board uses custom reset."""
        if self._use_custom_rst:
            self.servo.set_nocheck('ccd_cpu_fw_spi', state)

    def enable_ccd_spi(self):
        """Enable ccd spi access.

        Make GSC ignore servo, so it can enable CCD SPI access.
        """
        # There's no need to switch servo control if the main device is ccd.
        if self.servo.main_device_is_ccd():
            self.set_ccd_cpu_fw_spi('on')
            return

        # Setup the AP flash access. This could require EC uart access. It
        # has to be done before making ccd active.
        self.servo.enable_main_servo_device()
        self.set_ccd_cpu_fw_spi('on')

        # Enable the CCD servo device.
        self.servo.enable_ccd_servo_device()
        self.gsc.send_command('rddkeepalive enable')
        time.sleep(2)
        self.gsc.get_ccdstate()

    def enable_servo_ec_uart(self):
        """Enable servo control of ec uart."""
        # There's no need to switch servo control if the main device is ccd.
        if self.servo.main_device_is_ccd():
            self.set_ccd_cpu_fw_spi('off')
            return
        self.servo.set('ec_uart_en', 'on')
        self.servo.enable_main_servo_device()
        self.set_ccd_cpu_fw_spi('off')
        time.sleep(2)
        self.gsc.get_ccdstate()

    def check_state_from_consoles(self):
        """Log device state from EC and GSC consoles."""
        self.gsc.get_ccdstate()
        logging.info('EC Power State: %s', self.get_power_state())
        self.get_ec_hw_wp()
        self.gsc.get_wp_state()

    def set_gsc_hw_wp(self, state):
        """Open GSC. Set GSC wp."""
        logging.info('Set GSC WP: %s', state)
        self.gsc.set_wp_state(state)

    def run_once(self):
        """Verify WP in G3."""
        self._use_custom_rst = self.servo.has_control('ccd_cpu_fw_spi')
        if not self.servo.get_ccd_servo_device():
            raise error.TestNAError('Only supported with dual-v4')
        if not self.check_ec_capability(suppress_warning=True):
            raise error.TestNAError('Only supported on boards with ECs')
        if self.check_cr50_capability(['wp_on_in_g3'], suppress_warning=True):
            raise error.TestNAError('config: WP not pulled up in G3')
        try:
            self.gsc.ccd_enable(True)
        except:
            raise error.TestNAError('CCD required to check wp.')
        self.find_ec_wp_gpio_name()
        self.generate_futility_wp_cmd()
        self.fast_ccd_open(enable_testlab=True)
        self.gsc.send_command('ccd set OverrideWP Always')
        self.gsc.send_command('ccd set FlashAP Always')

        if self.servo.has_control('cold_reset_select'):
            self.servo.set_nocheck('cold_reset_select', 'gsc_ec_reset')

        if self.servo.main_device_is_flex():
            self._start_fw_wp_state = self.servo.get('fw_wp_state')
            # If nothing is forcing write protect, then the initial state is
            # "reset".
            if "force" not in self._start_fw_wp_state:
                self._start_fw_wp_state = "reset"
            self._start_fw_wp_vref = (self.servo.get('fw_wp_vref') if
                    self.servo.has_control('fw_wp_vref') else None)
            # Stop forcing wp using servo, so we can set it with ccd.
            self.servo.set_nocheck('fw_wp_state', 'reset')
            if self._start_fw_wp_vref:
                self.servo.set_nocheck('fw_wp_vref', 'off')

        # Disable HW WP.
        self.set_gsc_hw_wp('disable atboot')

        # Disable SW WP.
        wp_state = self.ccd_set_sw_wp(self.WP_DISABLE_CMD)
        # Bring the DUT up since futility commands put the EC in reset.
        self._try_to_bring_dut_up()
        if wp_state != self.DISABLED:
            raise error.TestFail('Unable to disable SW WP with HW WP enabled')

        # Verify we can see it's disabled. This should always work. If it
        # doesn't, it may be a setup issue.
        logging.info('Checking WP from DUT')
        self.check_state_from_consoles()
        if not self.checkers.crossystem_checker({'wpsw_cur': '0'}):
            raise error.TestError("HW WP isn't disabled in S0")

        # Enable HW WP.
        self.set_gsc_hw_wp('enable atboot')
        self.check_state_from_consoles()
        if not self.checkers.crossystem_checker({'wpsw_cur': '1'}):
            raise error.TestError("HW WP isn't enabled in S0")

        self.faft_client.system.run_shell_command('poweroff')
        time.sleep(self.WAIT_FOR_STATE)
        self.check_state_from_consoles()

        # SW WP can be enabled at any time.
        logging.info('Check enabling SW WP with HW WP enabled')
        if self.ccd_set_sw_wp(self.WP_ENABLE_CMD) != self.ENABLED:
            self.gsc.reboot()
            self._try_to_bring_dut_up()
            raise error.TestFail('Unable to enable SW WP in G3')

        # It shouldn't be possible to disable SW WP with HW WP enabled.
        logging.info('Check disabling SW WP with HW WP enabled')
        self.check_state_from_consoles()
        if self.ccd_set_sw_wp(self.WP_DISABLE_CMD) == self.DISABLED:
            self.gsc.reboot()
            self._try_to_bring_dut_up()
            raise error.TestFail('Disabled SW WP with HW WP enabled')

        # It should be possible to disable SW WP after HW WP is disabled.
        logging.info('Check disabling SW WP with HW WP disabled')
        # Disable HW WP.
        self.set_gsc_hw_wp('disable atboot')
        self.check_state_from_consoles()
        # Verify setting SW WP.
        if self.ccd_set_sw_wp(self.WP_DISABLE_CMD) != self.DISABLED:
            self.gsc.reboot()
            self._try_to_bring_dut_up()
            raise error.TestFail('Disabled SW WP with HW WP enabled')
        self._try_to_bring_dut_up()
