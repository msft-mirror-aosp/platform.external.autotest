# Copyright 2018 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from autotest_lib.client.common_lib import error
from autotest_lib.server.cros.faft.cr50_test import Cr50Test


class firmware_Cr50Password(Cr50Test):
    """Verify cr50 set password."""
    version = 1
    PASSWORD = 'Password'
    NEW_PASSWORD = 'robot'

    def cleanup(self):
        """Clear the password."""
        self.cr50.send_command('ccd testlab open')
        self.cr50.send_command('ccd reset')
        super(firmware_Cr50Password, self).cleanup()


    def run_once(self):
        """Check we can set the cr50 password."""
        # Make sure to enable testlab mode, so we can guarantee the password
        # can be cleared.
        self.fast_open(enable_testlab=True)
        self.cr50.send_command('ccd reset')

        # Set the password
        self.set_ccd_password(self.PASSWORD)
        if self.cr50.get_ccd_info()['Password'] != 'set':
            raise error.TestFail('Failed to set password')

        # Test 'ccd reset' clears the password
        self.cr50.send_command('ccd reset')
        if self.cr50.get_ccd_info()['Password'] != 'none':
            raise error.TestFail('ccd reset did not clear the password')

        # Reset the password
        self.set_ccd_password(self.PASSWORD)
        if self.cr50.get_ccd_info()['Password'] != 'set':
            raise error.TestFail('Failed to set password')

        # Make sure we can't overwrite the password
        self.set_ccd_password(self.NEW_PASSWORD, expect_error=True)

        self.cr50.set_ccd_level('lock')
        # Make sure you can't clear the password while the console is locked
        self.set_ccd_password('clear:' + self.PASSWORD, expect_error=True)

        self.cr50.send_command('ccd unlock ' + self.PASSWORD)
        # Make sure you can't clear the password while the console is locked
        self.set_ccd_password('clear:' + self.PASSWORD, expect_error=True)

        self.cr50.send_command('ccd testlab open')

        # Set the password again
        self.set_ccd_password(self.PASSWORD)

        # Make sure you can't clear the password with the wrong password
        self.set_ccd_password('clear:' + self.PASSWORD.lower(),
                              expect_error=True)
        # Make sure you can clear the password when the console is open
        self.set_ccd_password('clear:' + self.PASSWORD)
        if self.cr50.get_ccd_info()['Password'] != 'none':
            raise error.TestFail('Failed to clear password')

        # Make sure you can set some other password after it is cleared
        self.set_ccd_password(self.NEW_PASSWORD)
        if self.cr50.get_ccd_info()['Password'] != 'set':
            raise error.TestFail('Failed to clear password')
