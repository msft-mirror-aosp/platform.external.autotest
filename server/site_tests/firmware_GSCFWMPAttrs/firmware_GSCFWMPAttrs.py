# Copyright 2024 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import logging
import re
import time

from autotest_lib.client.bin import utils
from autotest_lib.client.common_lib import error
from autotest_lib.server.cros.faft.firmware_test import FirmwareTest
from autotest_lib.server.cros.servo import chrome_cr50


class firmware_GSCFWMPAttrs(FirmwareTest):
    """Verify the GSC FWMP attributes."""
    version = 1

    WAIT_FOR_RESET = 10

    CMD_GET_FWMP_SPACE_INFO = 'tpm_manager_client get_space_info --index=0x100a'
    GET_FWMP_ACTION = '--action=get_firmware_management_parameters'
    FIND_ATTRS = re.compile('attributes: {(.*)}.*policy', re.DOTALL)

    NEW_ATTRS = set([
            'NVRAM_READ_AUTHORIZATION', 'NVRAM_PLATFORM_WRITE',
            'NVRAM_OWNER_WRITE', 'NVRAM_PLATFORM_READ', 'NVRAM_PLATFORM_CREATE'
    ])
    OLD_ATTRS = set([
            'NVRAM_PERSISTENT_WRITE_LOCK', 'NVRAM_WRITE_AUTHORIZATION',
            'NVRAM_READ_AUTHORIZATION', 'NVRAM_PLATFORM_READ'
    ])

    def cleanup(self):
        """Clear the FWMP."""
        try:
            self.gsc.ccd_reset_and_wipe_tpm()
            self._try_to_bring_dut_up()
        finally:
            super(firmware_GSCFWMPAttrs, self).cleanup()

    def get_fwmp_space_info(self):
        """Get the FWMP space information."""
        return self.host.run(self.CMD_GET_FWMP_SPACE_INFO)

    def using_old_attrs(self, output):
        """Return True if the FWMP uses the new attributes."""
        current_attrs = self.get_attrs(output)
        different_attrs = self.OLD_ATTRS.symmetric_difference(current_attrs)
        logging.info('old attr difference: %s', different_attrs)
        return not different_attrs

    def using_new_attrs(self, output):
        """Return True if the FWMP uses the new attributes."""
        current_attrs = self.get_attrs(output)
        different_attrs = self.NEW_ATTRS.symmetric_difference(current_attrs)
        logging.info('new attr difference: %s', different_attrs)
        return not different_attrs

    def get_attrs(self, output):
        """Extract the attributes from the space info output."""
        match = re.search(self.FIND_ATTRS, output)
        if not match:
            raise error.TestError('Could not find %s in %r' %
                                  (self.FIND_ATTRS, output))
        attrs = set()
        for attr in match.group(1).split(','):
            attr = attr.strip()
            if not attr:
                continue
            attrs.add(attr.strip())
        logging.info('attributes: %s', attrs)
        return attrs

    def get_fwmp(self):
        """Get the FWMP."""
        return self.run_fwmp_cmd(self.GET_FWMP_ACTION, ignore_status=True)

    def wait_for_dut(self):
        """Wait for the DUT to respond to ping."""
        return self.host.ping_wait_up(self.faft_config.delay_reboot_to_ping *
                                      2)

    def run_once(self, host):
        """Verify the FWMP attributes."""
        self.host = host
        if not hasattr(self, 'gsc'):
            raise error.TestNAError('Test can only be run on devices with '
                                    'access to the GSC console')

        self.fast_ccd_open(True)
        self.gsc.ccd_reset_and_wipe_tpm()
        time.sleep(self.WAIT_FOR_RESET)
        self.wait_for_dut()

        # Some boards should automatically create the FWMP after the TPM
        # is wiped.
        fwmp_result = self.get_fwmp()
        logging.info('FWMP after TPM wipe: %s', fwmp_result)
        space_info_result = self.get_fwmp_space_info()
        logging.info(space_info_result)
        fwmp_exists = fwmp_result.exit_status == 0
        # Exit status 1 means the FWMP doesn't exist. Any other errors are
        # unexpected.
        if not fwmp_exists and fwmp_result.exit_status != 1:
            raise error.TestError('Unexpected exit status (%d): %s' %
                                  (fwmp_result.exit_status, fwmp_result))

        if fwmp_exists:
            if not self.using_new_attrs(space_info_result.stdout):
                raise error.TestFail(
                        'Coreboot did not create space with new attrs')
            return

        # Cr50 devices are the only ones where coreboot may not reinitialize the
        # FWMP.
        if self.gsc.NAME != chrome_cr50.FW_NAME:
            raise error.TestFail('FWMP not initialized on non-cr50 device')

        # Set the FWMP
        self.host.run("tpm_manager_client take_ownership")
        if not utils.wait_for_value(self._tpm_is_owned, expected_value=True):
            raise error.TestError("Unable to own tpm while clearing fwmp.")
        # Set the flags to some non-zero value. It doesn't matter.
        # It doesn't set FWMP_DEV_DISABLE_CCD_UNLOCK, so the test can clear
        # the FWMP by opening ccd.
        self.run_fwmp_cmd(
                "--action=set_firmware_management_parameters --flags=0x1")

        fwmp_result = self.get_fwmp()
        if fwmp_result.exit_status:
            raise error.TestFail('Unable to set the FWMP')
        logging.info('FWMP after TPM wipe: %s', fwmp_result)
        space_info_result = self.get_fwmp_space_info()
        logging.info(space_info_result)
        if not self.using_old_attrs(space_info_result.stdout):
            raise error.TestFail(
                    'ChromeOS did not initialize FWMP with old attrs')

        self.host.reboot()
        space_info_result = self.get_fwmp_space_info()
        logging.info('Updated attrs: %s', space_info_result)
        if not self.using_new_attrs(space_info_result.stdout):
            raise error.TestFail('Cr50 did not update the FWMP attributes')
