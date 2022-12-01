# Copyright 2020 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.


"""The autotest performing uart_stress_tester on EC uart port. """
import logging

from autotest_lib.client.common_lib import error
from autotest_lib.server.cros.faft.firmware_test import FirmwareTest


FLAG_FILENAME = '/tmp/chargen_testing'
# A ChromeOS TPM command to burden CR50.
TPM_CMD = ('trunks_client --stress_test')
# A command line to burden Cr50 with TPM_CMD as long as FLAG_FILENAME exists.
CR50_LOAD_GEN_CMD = 'while [ -f %s ]; do %s; done &' % (FLAG_FILENAME, TPM_CMD)

# Character generator
CHARGEN_CMD = 'chargen'

class firmware_Cr50CCDUartStress(FirmwareTest):
    """A test that checks character loss with a UART and TPM stress workload."""

    version = 1
    flag_filename = '/tmp/chargen_testing'

    def initialize(self, host, cmdline_args, use_ccd=False, console=''):
        """Initialize the test

        Raises:
            TestNAError: if the test environment is not properly set.
                         e.g. the servo type doesn't support this test, or
                         EC Uart command, chargen is not available.
        """
        self.host = host
        self.console = console
        super(firmware_Cr50CCDUartStress,
              self).initialize(host, cmdline_args)

        # Don't bother if there is no Chrome EC or if EC hibernate doesn't work.
        check_cap = getattr(self, 'check_%s_capability' % self.console, None)
        if not check_cap or not check_cap():
            raise error.TestNAError('Nothing needs to be tested on this device')

        # Check EC chargen is available.
        servo_console = getattr(self, console, None)
        if not servo_console or not servo_console.has_command(CHARGEN_CMD):
            raise error.TestNAError('chargen command is not available in %s.' %
                                     console)
        logging.info('Checked %s has the uart command, %r.', console, CHARGEN_CMD)

        # Check CCD is in servo_type.
        servo_type = self.servo.get_servo_version()
        logging.info('Checked the servo type is %r.', servo_type)
        if use_ccd:
            if 'ccd' not in servo_type:
                raise error.TestNAError('unsupported servo type: %s' % servo_type)

            # Fast open cr50 and enable testlab.
            self.fast_ccd_open(enable_testlab=True)
            logging.info('CCD opened.')

            # Change active device to the ccd device
            if not self.servo.enable_ccd_servo_device():
                raise error.TestNAError('Cannot make ccd active')
        self.active_dev = self.servo.get_active_device_prefix()
        self.interp_control = self.console + '_ec3po_interp_connect'
        self._interp_name = '.'.join([self.active_dev, self.interp_control])
        logging.info('Checking %s %s uart', self.servo.get_servo_version(True),
                     self.console)
        logging.info('Device prefix %r', self.active_dev)

        # Store the original status of EC ec3po_interp_connect.
        self.ec3po_connect = self.servo.get(self.interp_control,
                                               prefix=self.active_dev)
        # turn off EC ec3po_interp_connect
        self.servo.set(self.interp_control, 'off', prefix=self.active_dev)
        logging.info('Turned off %s.', self._interp_name)

    def cleanup(self):
        """Clean up Uart stress test, then cleanup Cr50Test"""
        try:
            # Terminate cr50 stressing command run.
            self.host.run('rm -f ' + FLAG_FILENAME)

            # Restore EC ec3po interpreter connect config.
            if hasattr(self, '_interp_name'):
                self.servo.set(self.interp_control, self.ec3po_connect,
                               prefix=self.active_dev)
                logging.info('Recovered %s.', self._interp_name)
        finally:
            # Cleanup super class
            super(firmware_Cr50CCDUartStress, self).cleanup()

    def run_once(self, duration):
        """The method called by the control file to start the test.

        Args:
            duration: time in seconds to run uart_stress_tester.

        Raises:
            TestFail: uart_stress_tester returned non-zero exit code for
                      character loss or other reasons.
        """

        # Run TPM command to stress cr50 in CPU.
        self.host.run('touch ' + FLAG_FILENAME)
        self.host.run('nohup sh -c %r &> /dev/null' % CR50_LOAD_GEN_CMD)

        # Run uart_stress_tester.
        uart_pty = self.servo.get('raw_%s_uart_pty' % self.console,
                                  prefix=self.active_dev)
        logging.info('PTY: %s', uart_pty)
        testcmd = 'uart_stress_tester.py -t %d -d %s' % (duration, uart_pty)

        logging.info('Run Uart stress tester for %d seconds.', duration)
        logging.info(testcmd)
        try:
            self.servo.system(testcmd, timeout=duration*2)
        except error.AutoservRunError:
            raise error.TestFail('Uart stress tester failed.')

        logging.info('Uart stress tester passed.')
