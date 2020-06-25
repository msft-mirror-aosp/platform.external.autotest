# Copyright 2016 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import logging
import time

from autotest_lib.client.common_lib import error
from autotest_lib.server.cros.faft.firmware_test import FirmwareTest
from autotest_lib.server.cros.servo import pd_console


class firmware_PDPowerSwap(FirmwareTest):
    """
    Servo based USB PD power role swap test.

    Pass critera is all power role swaps are successful if the DUT
    is dualrole capable. If not dualrole, then pass criteria is
    the DUT sending a reject message in response to swap request.

    """

    version = 1
    PD_ROLE_DELAY = 1
    PD_CONNECT_DELAY = 10
    # Should be an even number; back to the original state at the end
    POWER_SWAP_ITERATIONS = 10

    def _set_pdtester_power_role_to_src(self):
        """Force PDTester to act as a source

        @returns True if PDTester power role is source, false otherwise
        """
        PDTESTER_SRC_VOLTAGE = 20
        self.pdtester.charge(PDTESTER_SRC_VOLTAGE)
        # Wait for change to take place
        time.sleep(self.PD_CONNECT_DELAY)
        pdtester_state = self.pdtester_pd_utils.get_pd_state(self.pdtester_port)
        # Current PDTester power role should be source
        return self.pdtester_pd_utils.is_src_connected(self.pdtester_port)

    def _send_power_swap_get_reply(self, console, port):
        """Send power swap request, get PD control msg reply

        The PD console debug mode is enabled prior to sending
        a pd power role swap request message. This allows the
        control message reply to be extracted. The debug mode
        is disabled prior to exiting.

        @param console: pd console object for uart access

        @returns: PD control header message
        """
        # Enable PD console debug mode to show control messages
        console.enable_pd_console_debug()
        cmd = 'pd %d swap power' % port
        m = console.send_pd_command_get_output(cmd, ['RECV\s([\w]+)'])
        ctrl_msg = int(m[0][1], 16) & console.PD_CONTROL_MSG_MASK
        console.disable_pd_console_debug()
        return ctrl_msg

    def _attempt_power_swap(self, pd_port, direction):
        """Perform a power role swap request

        Initiate a power role swap request on either the DUT or
        PDTester depending on the direction parameter. The power
        role swap is then verified to have taken place.

        @param pd_port: DUT pd port value 0/1
        @param direction: rx or tx from the DUT perspective

        @returns True if power swap is successful
        """
        # Get DUT current power role
        dut_pr = self.dut_pd_utils.get_pd_state(pd_port)
        if direction == 'rx':
            console = self.pdtester_pd_utils
            port = self.pdtester_port
        else:
            console = self.dut_pd_utils
            port = pd_port
        # Send power swap request
        self._send_power_swap_get_reply(console, port)
        time.sleep(self.PD_CONNECT_DELAY)
        # Get PDTester power role
        pdtester_pr = self.pdtester_pd_utils.get_pd_state(self.pdtester_port)
        if (self.dut_pd_utils.is_src_connected(pd_port, dut_pr) and
            self.pdtester_pd_utils.is_src_connected(self.pdtester_port, pdtester_pr)):
            return True
        elif (self.dut_pd_utils.is_snk_connected(pd_port, dut_pr) and
            self.pdtester_pd_utils.is_snk_connected(self.pdtester_port, pdtester_pr)):
            return True
        else:
            return False

    def _test_power_swap_reject(self, pd_port):
        """Verify that a power swap request is rejected

        This tests the case where the DUT isn't in dualrole mode.
        A power swap request is sent by PDTester, and then
        the control message checked to ensure the request was rejected.
        In addition, the connection state is verified to not have
        changed.

        @param pd_port: port for DUT pd connection
        """
        # Get current DUT power role
        dut_power_role = self.dut_pd_utils.get_pd_state(pd_port)
        # Send swap command from PDTester and get reply
        ctrl_msg = self._send_power_swap_get_reply(self.pdtester_pd_utils,
                                                   self.pdtester_port)
        if ctrl_msg != self.dut_pd_utils.PD_CONTROL_MSG_DICT['Reject']:
            raise error.TestFail('Power Swap Req not rejected, returned %r' %
                                 ctrl_msg)
        # Get DUT current state
        pd_state = self.dut_pd_utils.get_pd_state(pd_port)
        if pd_state != dut_power_role:
            raise error.TestFail('PD not connected! pd_state = %r' %
                                 pd_state)

    def _test_one_way_power_swap_in_suspend(self, pd_port):
        """Verify SRC-to-SNK power role swap on DUT PD port in S0ix/S3

        Set the DUT power role to source and then suspend the DUT.
        Verify SRC-to-SNK power role request from the PD tester works,
        while SNK-to-SRC power role request fails. Note that this is
        Chrome OS policy decision, not part of the PD spec.

        @param pd_port: port for DUT pd connection
        """
        # Ensure DUT PD port is sourcing power.
        time.sleep(self.PD_CONNECT_DELAY)
        if not self.dut_pd_utils.is_src_connected(pd_port):
            if (self._attempt_power_swap(pd_port, 'rx') == False or
                not self.dut_pd_utils.is_src_connected(pd_port)):
                raise error.TestFail('Fail to set DUT power role to source.')

        self.set_ap_off_power_mode('suspend')

        new_state = self.dut_pd_utils.get_pd_state(pd_port)
        if not self.dut_pd_utils.is_src_connected(pd_port):
            raise error.TestFail('DUT power role changed to %s '
                    'during S0-to-S3 transition!' % new_state)

        # If the DUT PD port supports DRP in S0, it should supports SRC-to-SNK
        # power role swap in suspend mode. The other way around (SNK-to-SRC) in
        # suspend mode should fail.
        logging.info('Request a SRC-to-SNK power role swap to DUT PD port '
                     'in suspend mode. Expect to succeed.')
        if self._attempt_power_swap(pd_port, 'rx') == False:
            raise error.TestFail('SRC-to-SNK power role swap failed.')
        logging.info('Request a SNK-to-SRC power role swap to DUT PD port '
                     'in suspend mode. Expect to fail.')
        self._test_power_swap_reject(pd_port)

        self.restore_ap_on_power_mode()

    def initialize(self, host, cmdline_args, flip_cc=False, dts_mode=False,
                   init_power_mode=None):
        super(firmware_PDPowerSwap, self).initialize(host, cmdline_args)
        self.setup_pdtester(flip_cc, dts_mode, min_batt_level=10)
        # Only run in normal mode
        self.switcher.setup_mode('normal')
        if init_power_mode:
            # Set the DUT to suspend (S3) or shutdown (G3/S5) mode
            self.set_ap_off_power_mode(init_power_mode)
        # Turn off console prints, except for USBPD.
        self.usbpd.enable_console_channel('usbpd')

    def cleanup(self):
        if hasattr(self, 'pd_port'):
            # Restore DUT dual role operation
            self.dut_pd_utils.set_pd_dualrole(self.pd_port, 'on')
        if hasattr(self, 'pdtester_port'):
            # Set connection back to default arrangement
            self.pdtester_pd_utils.set_pd_dualrole(self.pdtester_port, 'off')

        if hasattr(self, 'pd_port') and hasattr(self, 'pdtester_port'):
            # Fake-disconnect to restore the original power role
            self.pdtester_pd_utils.send_pd_command('fakedisconnect 100 1000')

        self.usbpd.send_command('chan 0xffffffff')
        self.restore_ap_on_power_mode()
        super(firmware_PDPowerSwap, self).cleanup()

    def run_once(self):
        """Execute Power Role swap test.

        1. Verify that pd console is accessible
        2. Verify that DUT has a valid PD contract and connected to PDTester
        3. Determine if DUT is in dualrole mode
        4. If dualrole mode is not supported, verify DUT rejects power swap
           request. If dualrole mode is supported, test power swap (tx/rx) in
           S0 and one-way power swap (SRC-to-SNK on DUT PD port) in S3/S0ix.
           Then force DUT to be sink or source only and verify rejection of
           power swap request.

        """
        # TODO(b/35573842): Refactor to use PDPortPartner to probe the port
        self.pdtester_port = 1 if 'servo_v4' in self.pdtester.servo_type else 0

        # create objects for pd utilities
        self.dut_pd_utils = pd_console.create_pd_console_utils(self.usbpd)
        self.pdtester_pd_utils = pd_console.create_pd_console_utils(
                                 self.pdtester)
        self.connect_utils = pd_console.PDConnectionUtils(
            self.dut_pd_utils, self.pdtester_pd_utils)

        # Make sure PD support exists in the UART console
        if self.dut_pd_utils.verify_pd_console() == False:
            raise error.TestFail("pd command not present on console!")

        time.sleep(self.PD_CONNECT_DELAY)
        # Type C connection (PD contract) should exist at this point
        # For this test, the DUT must be connected to a PDTester.
        self.pd_port = self.connect_utils.find_dut_to_pdtester_connection()
        if self.pd_port is None:
            raise error.TestFail("DUT to PDTester PD connection not found")
        dut_connect_state = self.dut_pd_utils.get_pd_state(self.pd_port)
        logging.info('Initial DUT connect state = %s', dut_connect_state)

        # Get DUT dualrole status
        if self.dut_pd_utils.is_pd_dual_role_enabled(self.pd_port) == False:
            # DUT does not support dualrole mode, power swap
            # requests to the DUT should be rejected.
            logging.info('Power Swap support not advertised by DUT')
            self._test_power_swap_reject(self.pd_port)
            logging.info('Power Swap request rejected by DUT as expected')
        else:
            if self.get_power_state() != 'S0':
                raise error.TestFail('If the DUT is not is S0, the DUT port '
                        'shouldn\'t claim dualrole is enabled.')
            # Start with PDTester as source
            if self._set_pdtester_power_role_to_src() == False:
                raise error.TestFail('PDTester not set to source')
            # DUT is dualrole in dual role mode. Test power role swap
            # operation intiated both by the DUT and PDTester.
            success = 0
            for attempt in xrange(self.POWER_SWAP_ITERATIONS):
                if attempt & 1:
                    direction = 'rx'
                else:
                    direction = 'tx'
                if self._attempt_power_swap(self.pd_port, direction):
                    success += 1
                new_state = self.dut_pd_utils.get_pd_state(self.pd_port)
                logging.info('New DUT power role = %s', new_state)

            if success != self.POWER_SWAP_ITERATIONS:
                raise error.TestFail('Failed %r power swap attempts' %
                                     (self.POWER_SWAP_ITERATIONS - success))

            self._test_one_way_power_swap_in_suspend(self.pd_port)

            # Force DUT to only support current power role
            if new_state in self.dut_pd_utils.get_src_connect_states():
                dual_mode = 'src'
            else:
                dual_mode = 'snk'

            logging.info('Setting dualrole mode to %s', dual_mode)
            self.dut_pd_utils.set_pd_dualrole(self.pd_port, dual_mode)
            time.sleep(self.PD_ROLE_DELAY)
            # Expect behavior now is that DUT will reject power swap
            self._test_power_swap_reject(self.pd_port)
            logging.info('Power Swap request rejected by DUT as expected')

