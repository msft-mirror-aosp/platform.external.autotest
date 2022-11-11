# Copyright 2018 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import print_function

import logging
import time

from autotest_lib.client.bin import utils
from autotest_lib.client.common_lib import error
from autotest_lib.client.common_lib.cros import cr50_utils
from autotest_lib.server.cros.faft.cr50_test import Cr50Test


class firmware_Cr50Open(Cr50Test):
    """Verify cr50 open."""
    version = 1

    DEEP_SLEEP_DELAY = 20

    def initialize(self, host, cmdline_args, ccd_open_restricted, full_args):
        """Initialize the test"""
        super(firmware_Cr50Open, self).initialize(host, cmdline_args,
                full_args)

        if not self.faft_config.has_powerbutton:
            raise error.TestNAError('No power button. Unable to test ccd open')

        self.ccd_open_restricted = ccd_open_restricted
        self.fast_ccd_open(enable_testlab=True)
        self.gsc.ccd_reset()
        self.gsc.set_ccd_level('lock')

    def wait_ap_reboot(self, old_boot_id):
        """Wait for AP reboot after ccd open."""
        time.sleep(15)
        # CCD open should cause an AP reboot, so boot_id should change.
        # test_wait_for_boot will check this.
        self.host.test_wait_for_boot(old_boot_id)

    def check_cr50_open(self, dev_mode, batt_pres):
        """Verify you can't open ccd unless dev mode is enabled.

        Make sure the ability to open ccd corresponds with the device being in
        dev mode. When the device is in dev mode, open should be accessible from
        the AP. When the device is in normal mode it shouldn't be accessible.
        Open will never work from the console.

        Args:
            dev_mode: bool reflecting whether the device is in dev mode. If
                    True, the device is in dev mode. If False, the device is in
                    normal mode.
            batt_pres: True if the battery is connected
        """
        self.gsc.set_ccd_level('lock')
        self.gsc.get_ccd_info()

        #Make sure open doesn't work from the console.
        logging.info('ccd open from console')
        try:
            boot_id = self.host.get_boot_id()
            self.gsc.set_ccd_level('open')
            self.wait_ap_reboot(boot_id)
        except error.TestFail as e:
            self.gsc.check_for_console_errors('ccd open from console')
            if not batt_pres:
                raise error.TestFail('Unable to open cr50 from console with '
                                     'batt disconnected: %s' % str(e))
            # If ccd open is limited, open should fail with access denied
            #
            # TODO: move logic to set_ccd_level.
            if 'Access Denied' in str(e) and self.ccd_open_restricted:
                logging.info('console ccd open successfully rejected')
            else:
                raise
        else:
            if self.ccd_open_restricted and batt_pres:
                raise error.TestFail('Open should not be accessible from the '
                                     'console')
        self.gsc.set_ccd_level('lock')

        if not batt_pres:
            logging.info('ccd open from AP (batt disconnected)')
            boot_id = self.host.get_boot_id()
            cr50_utils.GSCTool(self.host, ['-a', '-o'],
                               expect_reboot=not batt_pres)
            self.wait_ap_reboot(boot_id)
            if self.gsc.OPEN != self.gsc.get_ccd_level():
                raise error.TestFail('Unable to open cr50 from AP with batt '
                                     'disconnected')
            return
        #Make sure open only works from the AP when the device is in dev mode.
        logging.info('ccd open from AP')
        try:
            boot_id = self.host.get_boot_id()
            self.ccd_open_from_ap()
            self.wait_ap_reboot(boot_id)
        except error.TestFail as e:
            logging.info(e)
            self.gsc.check_for_console_errors('ccd open from ap')
            # ccd open should work if the device is in dev mode or ccd open
            # isn't restricted. If open failed for some reason raise the error.
            if dev_mode or not self.ccd_open_restricted:
                raise


    def run_once(self):
        """Check open only works when the device is in dev mode."""
        self.gsc.send_command('ccd testlab open')
        self.gsc.set_batt_pres_state('connected', True)
        self.switcher.reboot_to_mode(to_mode='dev')
        logging.info('check open in dev mode, battery connected')
        self.check_cr50_open(True, True)
        self.switcher.reboot_to_mode(to_mode='normal')
        logging.info('check open in normal mode, battery connected')
        self.check_cr50_open(False, True)

        self.gsc.send_command('ccd testlab open')
        self.gsc.set_batt_pres_state('disconnected', True)
        logging.info('check open in normal mode, battery disconnected')
        self.check_cr50_open(False, False)

        self.gsc.send_command('ccd testlab open')
        self.gsc.ccd_disable()
        # Verify ccd open survives deep sleep.
        logging.info('check deep sleep')
        start_ds_count = self.gsc.get_deep_sleep_count()
        self.faft_client.system.run_shell_command('poweroff', True)
        utils.wait_for_value(self.gsc.ap_is_on, False)
        time.sleep(self.DEEP_SLEEP_DELAY)
        if start_ds_count == self.gsc.get_deep_sleep_count():
            raise error.TestNAError('Unable to enter deep sleep')
        if self.gsc.OPEN != self.gsc.get_ccd_level():
            raise error.TestFail('Open cleared after deep sleep')

        # Verify ccd open is cleared after a hard reset.
        logging.info('check reboot')
        self.gsc.reboot()
        if self.gsc.OPEN == self.gsc.get_ccd_level():
            raise error.TestFail('Open survived hard reset')
