# Copyright 2018 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import logging

from autotest_lib.client.common_lib import error
from autotest_lib.server.cros.faft.cr50_test import Cr50Test


class firmware_Cr50DevModeUnlock(Cr50Test):
    """Verify cr50 unlock."""
    version = 1
    PASSWORD = 'Password'

    def cleanup(self):
        """Make sure the device is in normal mode"""
        self.cr50.send_command('ccd testlab open')
        self.cr50.send_command('ccd reset')
        super(firmware_Cr50DevModeUnlock, self).cleanup()


    def run_once(self):
        """Check cr50 can see dev mode open works correctly"""
        # Make sure testlab mode is enabled, so we can guarantee the password
        # can be cleared.
        self.fast_open(enable_testlab=True)
        self.cr50.send_command('ccd reset')

        # Set the password
        self.set_ccd_password(self.PASSWORD)
        if self.cr50.get_ccd_info()['Password'] != 'set':
            raise error.TestFail('Failed to clear password')

        self.cr50.set_ccd_level('lock')

        # Verify the password can be used to unlock the console
        self.cr50.send_command('ccd unlock ' + self.PASSWORD)
        if self.cr50.get_ccd_level() != 'unlock':
            raise error.TestFail('Could not unlock cr50 with the password')

        self.cr50.set_ccd_level('lock')
        # Try with the lowercase version of the passsword. Make sure it doesn't
        # work.
        self.cr50.send_command('ccd unlock ' + self.PASSWORD.lower())
        if self.cr50.get_ccd_level() == 'unlock':
            raise error.TestFail('Unlocked cr50 with incorrect password')

        # Try Unlock from the AP
        self.cr50.set_ccd_level('lock')
        self.ccd_unlock_from_ap(self.PASSWORD)
        if self.cr50.get_ccd_level() != 'unlock':
            raise error.TestFail('Could not unlock cr50 from the AP')

        # Try Unlock from the AP with lower case version. Make sure it fails
        self.cr50.set_ccd_level('lock')
        try:
            self.ccd_unlock_from_ap(self.PASSWORD.lower())
        except error.TestFail, e:
            if 'unlock failed' in str(e):
                logging.info('Successfully rejected unlock')
            else:
                raise
        if self.cr50.get_ccd_level() != 'lock':
            raise error.TestFail('Unlocked cr50 from AP with incorrect '
                    'password')
