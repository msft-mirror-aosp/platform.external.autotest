# Copyright 2023 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import print_function

import logging
import re

from autotest_lib.client.common_lib import error
from autotest_lib.client.common_lib.cros import tpm_utils
from autotest_lib.server.cros.faft.cr50_test import Cr50Test


class firmware_GSCPinweaverUpdate(Cr50Test):
    """Verify pinweaver data survives GSC Update."""

    OLD_VERSIONS = {
            # Cr50 image with the old version of Pinweaver
            'cr50': '0.5.160',
            # Ti50 always used platform/pinweaver. This is just a ti50 image with
            # the same rollback era.
            'ti50': '0.23.21'
    }
    USER = 'name1'
    PWD = 'passwd1'
    PIN = '12345'
    WRONG_PIN = '012345'
    PWD_LABEL = 'pwd1'
    PIN_LABEL = 'pin1'

    AUTH_SESSION_ID_RE = r'auth_session_id: ([0-9A-F]*)\s'

    CMD_START_AUTH = 'cryptohome --action=start_auth_session --user=%s'
    CMD_CREATE_USER = ('cryptohome --action=create_persistent_user '
                       '--auth_session_id=%s')
    CMD_AUTH = 'cryptohome --action=%s --auth_session_id=%s --key_label=%s %s%s'
    PWD_ARG = ' --password='
    PIN_ARG = ' --pin='

    SUCCESS = 0
    # Wrong pin/password.
    CRYPTOHOME_ERROR_AUTHORIZATION_KEY_FAILED = 3
    # Too many pin attempts. The pin is locked until the password is used.
    CRYPTOHOME_ERROR_TPM_DEFEND_LOCK = 8
    # One more pin attempt will lockout the credential
    CRYPTOHOME_ERROR_CREDENTIAL_LOCKED = 59

    def initialize(self, host, cmdline_args, full_args):
        """Setup the test to restore the release image."""
        self.ran_test = False
        if not host.servo:
            raise error.TestNAError('No valid servo found')
        if host.servo.main_device_is_ccd():
            raise error.TestNAError('Use a flex cable instead of CCD cable.')
        # Restore the original image and board id during cleanup.
        super().initialize(host,
                           cmdline_args,
                           full_args,
                           restore_cr50_image=True,
                           restore_cr50_board_id=True)
        if self.gsc.NAME not in self.OLD_VERSIONS:
            raise error.TestNAError(
                    '%r is unsupported. Add image version to OLD_VERSIONS' %
                    self.gsc.NAME)
        self.remove_gsc_firmware_images()
        old_path = full_args.get('old_pinweaver_gsc_path', None)
        if old_path:
            self._old_release_path = old_path
        else:
            self._old_release_path = self.download_cr50_release_image(
                    self.OLD_VERSIONS[self.gsc.NAME])[0]

    def create_user(self, session):
        """Create a persistent user in the given session."""
        return self.host.run(self.CMD_CREATE_USER % session)

    def start_auth(self, user):
        """Create a persistent user in the given session."""
        logging.info('Start auth: %s', user)
        result = self.host.run(self.CMD_START_AUTH % user)
        match = re.search(self.AUTH_SESSION_ID_RE, result.stdout)
        if not match:
            raise error.TestFail('Did not find auth session id in %r' %
                                 result.stdout)
        logging.info('Session Id: %s', match.group(1))
        return match.group(1)

    def run_auth_cmd(self, action, session, label, auth_type, secret,
                     ignore_status):
        """Run the auth command.

        @param action: auth action string: add_auth_factor or authenticate_auth_factor'
        @param session: the session id string from the start auth session output.
        @param label: key label string.
        @param auth_type: " --password" or " --pin="
        @param secret: the pin or password value
        @param ignore_status: True if the command should fail.
        """
        cmd = self.CMD_AUTH % (action, session, label, auth_type, secret)
        logging.info('Run %s', cmd)
        result = self.host.run(cmd, ignore_status=ignore_status)
        logging.info('Result %s', result)
        return result

    def create_pin(self, session, pin):
        """Create a pin"""
        logging.info('Create pin: %s', pin)
        return self.run_auth_cmd('add_auth_factor', session, self.PIN_LABEL,
                                 self.PIN_ARG, pin, False)

    def create_password(self, session, pwd):
        """Create a password"""
        logging.info('Create password: %s', pwd)
        return self.run_auth_cmd('add_auth_factor', session, self.PWD_LABEL,
                                 self.PWD_ARG, pwd, False)

    def authenticate_pin(self, session, pin, expected_status):
        """Create a password"""
        logging.info('Auth pin: %s', pin)
        result = self.run_auth_cmd('authenticate_auth_factor', session,
                                   self.PIN_LABEL, self.PIN_ARG, pin,
                                   bool(expected_status))
        if expected_status != result.exit_status:
            raise error.TestFail(
                    'Unexpected Auth Result: expected %d. Got %r' %
                    (expected_status, result))

    def authenticate_password(self, session, pwd):
        """Create a password"""
        logging.info('Auth password: %s', pwd)
        return self.run_auth_cmd('authenticate_auth_factor', session,
                                 self.PWD_LABEL, self.PWD_ARG, pwd, False)

    def cleanup(self):
        """Clear the factory config."""
        try:
            if self.ran_test:
                self.cr50_update(self.get_saved_cr50_original_path())
                self._restore_device_images_and_running_cr50_firmware()
        finally:
            super().cleanup()

    def run_once(self):
        """Verify the Cr50 BID response of each test bid."""
        self.ran_test = True

        # Rollback to the old gsc image
        logging.info('Update to old gsc release')
        self.eraseflashinfo_and_restore_image(self._old_release_path)
        # Do a powerwash to clear the state.
        logging.info('Powerwash')
        self.host.run(
                "echo 'clobber' > /mnt/stateful_partition/.update_available")
        tpm_utils.ClearTPMOwnerRequest(self.host, wait_for_ready=True)

        # Initialize Pinweaver
        session_id = self.start_auth(self.USER)
        self.create_user(session_id)
        self.create_password(session_id, self.PWD)
        self.create_pin(session_id, self.PIN)
        logging.info('Verify the wrong pin does not work')
        self.authenticate_pin(session_id, self.WRONG_PIN,
                              self.CRYPTOHOME_ERROR_AUTHORIZATION_KEY_FAILED)
        logging.info('Verify the pin works')
        self.authenticate_pin(session_id, self.PIN, self.SUCCESS)

        # Use the wrong pin twice.
        logging.info('Sending 2 invalid pin attempts')
        self.authenticate_pin(session_id, self.WRONG_PIN,
                              self.CRYPTOHOME_ERROR_AUTHORIZATION_KEY_FAILED)
        self.authenticate_pin(session_id, self.WRONG_PIN,
                              self.CRYPTOHOME_ERROR_AUTHORIZATION_KEY_FAILED)

        # Update to the release image from the AP to mimic the normal update
        # path.
        logging.info('Update to the current release')
        self.cr50_update(self.get_saved_cr50_original_path())
        session_id = self.start_auth(self.USER)

        # Verify pinweaver lockout still works after the update.
        # Use the wrong pin three more times to lockout the node. It gets
        # locked after 4 attempts.
        logging.info('Verify pin lockout')
        self.authenticate_pin(session_id, self.WRONG_PIN,
                              self.CRYPTOHOME_ERROR_AUTHORIZATION_KEY_FAILED)
        logging.info('Last wrong pin attempt before lockout')
        self.authenticate_pin(session_id, self.WRONG_PIN,
                              self.CRYPTOHOME_ERROR_CREDENTIAL_LOCKED)

        logging.info('Verify the incorrect pin is locked out.')
        self.authenticate_pin(session_id, self.WRONG_PIN,
                              self.CRYPTOHOME_ERROR_TPM_DEFEND_LOCK)
        logging.info('Verify the correct pin is locked out.')
        self.authenticate_pin(session_id, self.PIN,
                              self.CRYPTOHOME_ERROR_TPM_DEFEND_LOCK)

        # Use the password to clear the pin lockout
        self.authenticate_password(session_id, self.PWD)
        self.authenticate_pin(session_id, self.WRONG_PIN,
                              self.CRYPTOHOME_ERROR_AUTHORIZATION_KEY_FAILED)
        logging.info('Verify pin works again after the password has been used')
        self.authenticate_pin(session_id, self.PIN, self.SUCCESS)
