# Copyright 2017 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import logging
import re

from autotest_lib.client.common_lib import error
from autotest_lib.server import autotest, test
from autotest_lib.client.common_lib.cros import tpm_utils


class firmware_Cr50InvalidateRW(test.test):
    """
    Verify the inactive Cr50 header on the first login after cryptohome
    starts.

    There are two special cases this test covers: logging in after the TPM
    owner is cleared and logging in as guest.

    After the tpm owner is cleared, corrupting the header will be done on
    the first non-guest login. During guest login the owner wont be cleared.
    """
    version = 1

    GET_CRYPTOHOME_MESSAGE ='grep cryptohomed /var/log/messages'
    SUCCESS = r'Successfully invalidated inactive (Cr50|GSC) RW'
    FAIL = r'Invalidating inactive (Cr50|GSC) RW failed'
    NO_ATTEMPT = 'Did not try to invalidate header'
    LOGIN_ATTEMPTS = 5

    def initialize(self, host):
        """Initialize servo and cr50"""
        super(firmware_Cr50InvalidateRW, self).initialize()

        self.host = host
        self.client_at = autotest.Autotest(self.host)

        self.last_message = None
        # get the messages already in /var/log/messages so we don't use them
        # later.
        self.check_for_invalidated_rw()


    def check_for_invalidated_rw(self):
        """Use /var/log/messages to see if the rw header was invalidated.

        Returns a string NO_ATTEMPT if cryptohome did not try to invalidate the
        header or the cryptohome message if the attempt failed or succeeded.
        """
        # Get the relevant messages from /var/log/messages
        result = self.host.run(self.GET_CRYPTOHOME_MESSAGE,
                               verbose=False,
                               ignore_status=True)
        # Return NO_ATTEMPT if no cryptohomed messages are found
        if result.exit_status == 1:
            self.last_message = ""
            return self.NO_ATTEMPT
        elif result.exit_status:
            raise error.TestError('Failed to get crypthome messages: %r' %
                                  result)
        message_str = result.stdout.strip()
        # Remove the messages we have seen in the past
        if self.last_message:
            message_str = message_str.rsplit(self.last_message, 1)[-1]
        messages = message_str.split('\n')

        # Save the last message so we can identify new messages later
        self.last_message = messages[-1]

        rv = self.NO_ATTEMPT
        # print all cryptohome messages.
        for message in messages:
            logging.debug(message)
            # Return the message that is related to the RW invalidate attempt
            if re.search(self.FAIL, message) or re.search(
                    self.SUCCESS, message):
                rv = message
        return rv


    def login(self, use_guest, dont_override_profile=False):
        """Run the test to login."""
        if use_guest:
            self.client_at.run_test('login_CryptohomeIncognito')
        else:
            self.client_at.run_test('login_LoginSuccess',
                                    dont_override_profile=dont_override_profile)


    def login_and_verify(self, use_guest=False, corrupt_login_attempt=None):
        """Verify the header is only invalidated on the specified login.

        login LOGIN_ATTEMPTS times. Verify that cryptohome only tries to corrupt
        the inactive cr50 header on the specified login. If it tries on a
        different login or fails to corrupt the header, raise an error.

        Args:
            use_guest: True to login as guest
            corrupt_login_attempt: The login attempt that we expect the header
                                   to be corrupted on

        Raises:
            TestError if the system attempts to corrupt the header on any login
            that isn't corrupt_login_attempt or if an attepmt to corrupt the
            header fails.
        """
        for i in range(self.LOGIN_ATTEMPTS):
            attempt = i + 1
            # Dont override profile when we are not using guest and we are after
            # first attempt
            dont_override_profile = not use_guest and i > 0
            self.login(use_guest, dont_override_profile)
            result = self.check_for_invalidated_rw()

            message = '%slogin %d: %s' % ('guest ' if use_guest else '',
                                          attempt, result)
            logging.info(message)

            # Anytime the invalidate attempt fails raise an error
            if re.search(self.FAIL, result):
                raise error.TestError(message)

            # The header should be invalidated only on corrupt_login_attempt.
            # Raise an error if it was invalidated on some other login or if
            # cryptohome did not try on the first one.
            invalidated_rw = not not re.search(self.SUCCESS, result)
            if invalidated_rw:
                if attempt != corrupt_login_attempt:
                    raise error.TestFail(
                            'Invalidated header on wrong login %r' % message)
            else:
                if attempt == corrupt_login_attempt:
                    raise error.TestError(
                            'Did not invalidate header on login %d %s' %
                            (corrupt_login_attempt, message))


    def restart_cryptohome(self):
        """Restart cryptohome

        Cryptohome only sends the command to corrupt the header once. Once it
        has been sent it wont be sent again until cryptohome is restarted.
        """
        self.host.run('restart cryptohomed')


    def clear_tpm_owner(self):
        """Clear the tpm owner."""
        logging.info('Clearing the TPM owner')
        tpm_utils.ClearTPMOwnerRequest(self.host, wait_for_ready=True)

    def take_tpm_owner(self):
        """Take the tpm owner."""
        logging.info('Taking the TPM owner')
        self.host.run('tpm_manager_client take_ownership')

    def after_run_once(self):
        """Print the run information after each successful run"""
        logging.info('finished run %d', self.iteration)


    def run_once(self, host):
        """Login to validate ChromeOS corrupts the inactive header"""
        # The header is corrupted on the first non-guest login after clearing
        # the tpm owner. The fist login attempt happens during second ever login
        # for user in the AuthSession world. The first ever is just a key addition.
        self.clear_tpm_owner()
        self.take_tpm_owner()

        self.login_and_verify(use_guest=True)
        self.login_and_verify(corrupt_login_attempt=2)
