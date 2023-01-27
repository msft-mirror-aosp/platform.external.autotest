# Copyright 2018 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import logging
import time

from autotest_lib.client.common_lib import error
from autotest_lib.client.common_lib.cros import cr50_utils
from autotest_lib.server.cros.faft.cr50_test import Cr50Test


class firmware_Cr50Password(Cr50Test):
    """Verify cr50 set password."""
    version = 1
    NEW_PASSWORD = 'robot'

    def usb_set_password(self, password):
        """Try sending the password command from the console and ccd usb.

        Verify the console command and usb vendor command fail to set the
        password.
        """
        start_pw_state = self.gsc.password_is_reset()
        # CCD password from the console should always be inaccessible.
        self.gsc.set_password(password)
        if start_pw_state != self.gsc.password_is_reset():
            raise error.TestFail('changed password from console')
        # TODO: check ccd password vendor command can't change the password.

    def try_wrong_password(self, wrong_password):
        """Try to open ccd with the wrong password.

        Raise an error if it works.
        """
        time.sleep(self.gsc.CCD_PASSWORD_RATE_LIMIT)
        try:
            self.gsc.set_ccd_level('open', wrong_password)
            raise error.TestFail(
                    'Opened ccd with incorrect password: used %r actual %r',
                    wrong_password, self.test_password)
        except error.TestFail as e:
            logging.info('successfully rejected ccd open using %r',
                         wrong_password)

    def run_once(self):
        """Check we can set the cr50 password."""
        self.test_password = self.CCD_PASSWORD
        # Make sure the case is enforced. If the password is lower case, try
        # upper. If it's uppercase, try lower.
        wrong_case = (self.test_password.upper()
                      if self.test_password.islower() else
                      self.test_password.lower())

        # Make sure to enable testlab mode, so we can guarantee the password
        # can be cleared.
        self.fast_ccd_open(enable_testlab=True)
        self.gsc.ccd_reset()

        # CCD password from the console should always be inaccessible.
        self.usb_set_password(self.test_password)
        # Set the password.
        self.set_ccd_password(self.test_password)
        if self.gsc.password_is_reset():
            raise error.TestFail('Failed to set password')

        # Test 'ccd reset' clears the password.
        self.gsc.ccd_reset()
        if not self.gsc.password_is_reset():
            raise error.TestFail('ccd reset did not clear the password')
        # Set OpenFromUSB to IfOpened, so the test will only be able to open
        # ccd with a console command if the password is set. This is cleared
        # in Cr50Test cleanup.
        self.gsc.set_cap('OpenFromUSB', 'IfOpened')

        # Set the password again while cr50 is open.
        self.set_ccd_password(self.test_password)
        if self.gsc.password_is_reset():
            raise error.TestFail('Failed to set password')

        # The password can't be changed once it's set.
        # It needs to be cleared first.
        self.set_ccd_password(self.NEW_PASSWORD, expect_error=True)

        self.gsc.reboot()
        if self.gsc.password_is_reset():
            raise error.TestFail('Password cleared after reboot')

        # Verify ccd can't be opened with the wrong password. Verify case is
        # enforced
        self.try_wrong_password(wrong_case)
        self.try_wrong_password(self.NEW_PASSWORD)

        # Verify ccd can be opened with the correct password.
        self.gsc.set_ccd_level('open', self.test_password)

        self.gsc.set_ccd_level('lock')
        # The password can't be cleared while the console is locked from the
        # AP or ccd.
        self.usb_set_password('clear:' + self.test_password)
        self.set_ccd_password('clear:' + self.test_password, expect_error=True)
        if self.gsc.password_is_reset():
            raise error.TestFail('Cleared password while locked')

        if self.gsc.unlock_is_supported():
            self.gsc.send_command('ccd unlock ' + self.test_password)
            # The password can be cleared while the console is unlocked.
            self.set_ccd_password('clear:' + self.test_password)

            # Open the console, set the password again.
            self.gsc.send_command('ccd testlab open')
            self.set_ccd_password(self.test_password)
        else:
            # Open the console.
            self.gsc.send_command('ccd testlab open')

        # The password can't be cleared using the wrong password.
        self.set_ccd_password('clear:' + wrong_case, expect_error=True)
        self.set_ccd_password('clear:' + self.NEW_PASSWORD, expect_error=True)
        # The right password can't be used to clear the password from
        # the console.
        self.usb_set_password('clear:' + self.test_password)
        # The password can be cleared using the correct password.
        self.set_ccd_password('clear:' + self.test_password)
        if not self.gsc.password_is_reset():
            raise error.TestFail('Failed to clear password')

        # The password can be set to anything when there isn't one set.
        self.set_ccd_password(self.NEW_PASSWORD)
        if self.gsc.password_is_reset():
            raise error.TestFail('Failed to set password')

        self.gsc.send_command('ccd testlab open')
        self.gsc.ccd_reset()

        if not self.gsc.unlock_is_supported():
            return

        # Run through the same steps when the password was set with the console
        # unlocked.

        self.host.run('gsctool -a -U')

        # Set the password when the console is unlocked.
        self.set_ccd_password(self.test_password)

        self.gsc.set_ccd_level('lock')
        # The password can't be cleared while the console is locked.
        self.set_ccd_password('clear:' + self.test_password, expect_error=True)

        # Unlock the console.
        self.ccd_unlock_from_ap(self.test_password)
        # The password can be cleared while the console is unlocked.
        self.set_ccd_password('clear:' + self.test_password)
        # Set the password again when the console is unlocked.
        self.set_ccd_password(self.test_password)

        self.gsc.send_command('ccd testlab open')
        # The password can be cleared when the console is open.
        self.set_ccd_password('clear:' + self.test_password)
