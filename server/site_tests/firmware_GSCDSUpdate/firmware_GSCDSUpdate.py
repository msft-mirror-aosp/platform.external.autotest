# Copyright 2023 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import logging
import time

from autotest_lib.client.common_lib import error
from autotest_lib.client.common_lib.cros import cr50_utils
from autotest_lib.server.cros.faft.cr50_test import Cr50Test


class firmware_GSCDSUpdate(Cr50Test):
    """
    Verify a dut can pick up a gsc update after deep sleep.

    The AP flashes the GSC image in the inactive region. When the AP
    restarts, it tells GSC to enable the new image. Verify this process
    works when GSC enters deep sleep while the AP is shutdown.
    """
    version = 1

    UPDATE_OK = 1

    DBG_PATH = '/tmp/gsc.dbg.bin'

    def initialize(self, host, cmdline_args, full_args={}):
        """Get the DBG image information."""
        if not host.servo or host.servo.main_device_is_ccd():
            raise error.TestNAError(
                    'CCD not supported. Run with servo micro or c2d2')
        super(firmware_GSCDSUpdate, self).initialize(host,
                                                     cmdline_args,
                                                     full_args,
                                                     restore_cr50_image=True)
        self.host = host
        self.dbg_img = self.get_saved_dbg_image_path()

    def run_once(self):
        """Flash the dbg image. Verify GSC jumps to it after on resume"""
        # Flash the image on the DUT.
        dest, image_ver = cr50_utils.InstallImage(self.host, self.dbg_img,
                                                  self.DBG_PATH)
        self.gsc.wait_until_update_is_allowed()
        # Flash the dbg image in the inactive slot.
        result = self.host.run('gsctool -au %s' % dest, ignore_status=True)
        logging.info('Update result: %s', result)
        if result.exit_status != self.UPDATE_OK:
            try:
                # Reboot the dut to cleanup the update state.
                self.host.reboot()
            finally:
                raise error.TestError('Unable to run gsc update: %r' % result)

        # Disable CCD, so gsc can enter deep sleep.
        self.gsc.ccd_disable()
        start_ds_count = self.gsc.get_deep_sleep_count()

        # Shutdown the dut, so GSC will enter deep sleep.
        self.faft_client.system.run_shell_command('poweroff', True)
        logging.info('Waiting for gsc to enter deep sleep')
        time.sleep(self.gsc.DEEP_SLEEP_DELAY * 2)

        # Before turning on the system get the deep sleep count to make sure
        # GSC entered deep sleep.
        end_ds_count = self.gsc.get_deep_sleep_count()
        # Check the version to make sure GSC doesn't pickup the update until
        # the system boots.
        resume_ver = self.gsc.get_active_version_info()

        # Press the power button to turn on the DUT.
        logging.info('Turning on the device')
        self.servo.power_short_press()

        # Wait for dut to pickup update
        time.sleep(self.faft_config.delay_reboot_to_ping)

        running_ver = self.gsc.get_active_version_info()
        is_dbg = running_ver[2]
        logging.info('Running: %r', running_ver)
        logging.info('Expected: %r', image_ver)

        # Try to rollback to the release version, so cleanup will be faster.
        try:
            self.gsc.rollback()
        except:
            logging.info('Rollback failed. Cleanup should handle it')

        if start_ds_count >= end_ds_count:
            raise error.TestError('Unable to enter deep sleep')
        # Raise an error if the dut failed to update to the DBG image.
        if not is_dbg or image_ver[1] != running_ver[1]:
            raise error.TestFail('Unable to update after deep sleep')
        if resume_ver == running_ver:
            raise error.TestFail('Enabled the update before the system booted')
