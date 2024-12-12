# Copyright 2024 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import logging
import time

from autotest_lib.client.common_lib import error
from autotest_lib.server.cros import vboot_constants as vboot
from autotest_lib.server.cros.faft.firmware_test import FirmwareTest


class firmware_GSCEncStateful(FirmwareTest):
    """Verify EncStateful is created in normal and dev mode after the TPM is wiped."""
    version = 1

    WAIT_FOR_RESET = 10

    FOUND_ENCSTATEFUL = 'Found encstateful NVRAM area'
    NO_ENCSTATEFUL = 'No encstateful NVRAM area defined'
    SRCH_STR = '"(%s|%s)"' % (FOUND_ENCSTATEFUL, NO_ENCSTATEFUL)
    CMD_FIND_ENCSTATEFUL_MESSAGES = 'grep -a -Ei %s /var/log/messages' % SRCH_STR

    def initialize(self, host, cmdline_args, mode=None):
        """Setup the test type."""
        self.host = host
        self.started_test = False
        if mode == 'dev':
            self.test_set_gbb = vboot.GBB_FLAG_FORCE_DEV_SWITCH_ON
            self.test_clear_gbb = 0
        elif mode == 'normal':
            self.test_clear_gbb = vboot.GBB_FLAG_FORCE_DEV_SWITCH_ON
            self.test_set_gbb = 0
        else:
            raise error.TestError('Invalid mode %r. Use dev or normal' % mode)
        super(firmware_GSCEncStateful, self).initialize(host, cmdline_args)
        self.expected_pcr_value = self.get_pcr_value(mode)
        self.test_mode = mode
        self.last_message = ''
        self.get_encstateful_message()
        self.started_test = True

    def cleanup(self):
        """Clear the FWMP."""
        try:
            if self.started_test:
                self.gsc.ccd_reset_and_wipe_tpm()
                self._try_to_bring_dut_up()
                self.clear_set_gbb_flags(vboot.GBB_FLAG_FORCE_DEV_SWITCH_ON, 0)
                self._try_to_bring_dut_up()
        finally:
            super(firmware_GSCEncStateful, self).cleanup()

    def get_encstateful_message(self):
        """Get the EncStateful messages in /var/log/messages."""
        messages = self.host.run(self.CMD_FIND_ENCSTATEFUL_MESSAGES).stdout
        if self.last_message and self.last_message in messages:
            messages = messages.partition(self.last_message)[-1]
        valid_lines = []
        logging.info('New EncStateful messages:')
        for line in messages.splitlines():
            # remove blank lines and the grep command.
            if not line.strip() or self.CMD_FIND_ENCSTATEFUL_MESSAGES in line:
                continue
            logging.info(line)
            valid_lines.append(line)
        self.last_message = valid_lines[-1]
        logging.info("Last line: %s", self.last_message)
        return self.last_message

    def wait_for_ping(self):
        """Wait until the DUT boots."""
        if not self._client.ping_wait_up(
                self.faft_config.delay_reboot_to_ping * 2):
            raise error.TestError('Dut did not respond to ping')

    def wait_for_dut(self):
        """Wait for the DUT to respond to ping."""
        return self.host.ping_wait_up(self.faft_config.delay_reboot_to_ping *
                                      2)

    def get_pcr_value(self, mode):
        for k, v in self.gsc.PCR0_DICT.items():
            if mode == v:
                return k
        raise error.TestError('Did not find %r in pcr dict' % mode)

    def no_encstateful_found(self):
        """Returns True if the no encstateful message showed up this boot."""
        message = self.get_encstateful_message()
        return self.NO_ENCSTATEFUL in message

    def found_encstateful(self):
        """Returns True if the found encstateful message showed up this boot."""
        message = self.get_encstateful_message()
        return self.FOUND_ENCSTATEFUL in message

    def run_once(self, host):
        """Verify the FWMP attributes."""
        self.host = host
        if not hasattr(self, 'gsc'):
            raise error.TestNAError('Test can only be run on devices with '
                                    'access to the GSC console')
        self.fast_ccd_open(True)
        self.clear_set_gbb_flags(self.test_clear_gbb, self.test_set_gbb)
        self.gsc.ccd_reset_and_wipe_tpm()
        time.sleep(self.WAIT_FOR_RESET)
        self.wait_for_dut()

        pcr_value = self.gsc.get_ccdstate()['pcr0']
        if pcr_value != self.expected_pcr_value:
            raise error.TestError('Current PCR0 value %r does not match the '
                                  'expected value %r' %
                                  (pcr_value[:8], self.expected_pcr_value[:8]))
        # Wiping the TPM should clear the EncStateful space.
        if not self.no_encstateful_found():
            raise error.TestFail('EncStateful was not deleted during TPM wipe')
        logging.info('EncStateful was deleted during CCD open')
        # The next boot EncStateful should exist.
        self.host.reboot()
        self.wait_for_dut()
        time.sleep(self.WAIT_FOR_RESET)
        if not self.found_encstateful():
            raise error.TestFail(
                    'EncStateful was not preserved over reboot in '
                    '%s mode' % self.test_mode)
        logging.info('EncStateful survived reboot')
