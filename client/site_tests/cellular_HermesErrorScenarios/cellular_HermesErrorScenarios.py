# Lint as: python2, python3
# Copyright (c) 2021 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import dbus
import logging

from autotest_lib.client.bin import test
from autotest_lib.client.common_lib import error
from autotest_lib.client.cros.cellular import cellular_logging
from autotest_lib.client.cros.cellular import hermes_constants
from autotest_lib.client.cros.cellular import hermes_utils

log = cellular_logging.SetupCellularLogging('HermesErrorScenariosTest')

class cellular_HermesErrorScenarios(test.test):
    """
    Tests Hermes Error Scenarios on active Euicc

    This test fails when not able to do error validation

    Prerequisites

    1) For test CI:
       Before running this test on test CI, a profile needs to be created on
    go/stork-profile. The profile needs to be linked to the EID of the dut.
    Profiles with class=operational and type=Android GTS test are known to work
    well with this test.

       We rely on the SMDS event to find the activation code for the test.
    There is a limit of 99 downloads before the profile needs to be deleted and
    recreated.(b/181723689)

    2) For prod CI:
       Install a production profile before running the test.

    """
    version = 1

    def install_invalid_profile_test(self, euicc_path):
        """
        Install a profile with incorrect activation code
        Check expected error, also validates InstallProfileFromActivationCode
        api on test euicc

        @param euicc_path: esim path based on testci/prodci
        @return raise error.TestFail if expected error not resulted

        """
        expected_exception = 'org.chromium.Hermes.Error.InvalidActivationCode'
        try:
            logging.info('install_invalid_profile_test start')
            euicc, _ = hermes_utils.request_installed_profiles(
                    euicc_path, self.hermes_manager)

            # Incorrect activation code
            activation_code = 'W567-EQ7A-TEST-CODE'

            logging.info('Installing activation_code:%s conf_code:%s',
                          activation_code, '')

            # Install and check for expected error
            euicc.install_profile_from_activation_code(activation_code, '')
            raise error.TestFail(expected_exception, ' not raised while '
            'installing a profile with an invalid activation code.')
        except dbus.DBusException as e:
            self.check_exception(expected_exception, e.get_dbus_name())
        logging.info('===install_invalid_profile_test done===\n')

    def enable_uninstall_profile_test(self, euicc_path):
        """
        Attempt to uninstall an enabled profile, and check that an error is
        received.

        @param euicc_path: esim path based on testci/prodci
        @return raise error.TestFail if expected error not resulted

        """
        expected_exception = 'org.chromium.Hermes.Error.Unknown'
        try:
            logging.info('enable_uninstall_profile_test start')
            # Get a profile to enable which is not active
            installed_iccid = self.get_installed_profile(euicc_path, False)
            hermes_utils.set_profile_state(
            True, euicc_path, self.hermes_manager, installed_iccid, None)

            # Uninstall already enabled profile
            euicc = self.hermes_manager.get_euicc(euicc_path)
            profile = euicc.get_profile_from_iccid(installed_iccid)
            if (hermes_constants.ProfileClassToString(profile.profileclass) !=
                    'TESTING'):
                euicc.uninstall_profile(profile.path)
            logging.info('enable_uninstall_profile_test success')
        except dbus.DBusException as e:
            self.check_exception(expected_exception, e.get_dbus_name())
        logging.info('===enable_uninstall_profile_test done===\n')

    def get_installed_profile(self, euicc_path, is_active):
        """
        Attempts to get an active/inactive profile. If a profile in the desired
        state is not found, installs a profile and enables/disables the profile

        @param euicc_path: esim path based on testci/prodci
        @param is_active: true to get active profile, false to get inactive one

        """
        logging.info('get_installed_profile start')
        installed_iccid = hermes_utils.get_profile(
                    euicc_path, self.hermes_manager, is_active)

        if (installed_iccid is None and not self.is_prod_ci):
            logging.info('Could not find an installed profile with '
            'state==%s. Will attempt to install a profile and set it to the '
            'desired state.', is_active)
            installed_iccid = hermes_utils.install_pending_profile_test(
            euicc_path, self.hermes_manager)

            hermes_utils.enable_or_disable_profile_test(
            euicc_path, self.hermes_manager, installed_iccid, is_active)

        if not installed_iccid:
            raise error.TestFail('get_installed_profile failed - no profile')
        logging.info('get_installed_profile done')
        return installed_iccid

    def check_exception(self, expected_exception, received_exception):
        """
        Checks the exception is an expected one or not

        @param expected_exception: DBus expected exception
        @param received_exception: DBus resulted exception

        """
        if received_exception in expected_exception:
            logging.info('Received exception %s as expected.',
                expected_exception)
        else:
            raise error.TestFail('Expected exception:' + expected_exception +
                '. Got exception:' + received_exception)

    def enable_active_profile_test(self, euicc_path):
        """
        Check that an exception is raised upon re-enabling an active profile.

        @param euicc_path: esim path based on testci/prodci
        @return raise error.TestFail if expected error not resulted

        """
        expected_exception = 'org.chromium.Hermes.Error.AlreadyEnabled'
        try:
            logging.info('===enable_active_profile_test start===')
            installed_iccid = self.get_installed_profile(euicc_path, True)
            hermes_utils.set_profile_state(
            True, euicc_path, self.hermes_manager, installed_iccid, None)
            raise error.TestFail(expected_exception, ' not raised while '
            'enabling a profile which is already in enabled state.')
        except dbus.DBusException as e:
            self.check_exception(expected_exception, e.get_dbus_name())
        logging.info('===enable_active_profile_test done===\n')

    def disable_inactive_profile_test(self, euicc_path):
        """
        Validate expected result after disabling already disabled profile

        @param euicc_path: esim path based on testci/prodci
        @return raise error.TestFail if expected error not resulted

        """
        expected_exception = 'org.chromium.Hermes.Error.AlreadyDisabled'
        try:
            logging.info('===disable_inactive_profile_test start===')
            installed_iccid = self.get_installed_profile(euicc_path, False)
            hermes_utils.set_profile_state(
            False, euicc_path, self.hermes_manager, installed_iccid, None)
            raise error.TestFail(expected_exception, ' not raised while '
            'disabling a profile which is already in disabled state.')
        except dbus.DBusException as e:
            self.check_exception(expected_exception, e.get_dbus_name())
        logging.info('===disable_inactive_profile_test done===\n')

    def run_once(self, is_prod_ci=False):
        """
        Validated error scenarios on Profile

        @param is_prod: is_prod_ci true if prod sim dut & false for test sim dut
        @return raise error.TestFail if expected error not resulted

        expected_exceptions are
                'org.chromium.Hermes.Error.AlreadyEnabled',
                'org.chromium.Hermes.Error.AlreadyDisabled',
                'org.chromium.Hermes.Error.InvalidActivationCode'
                'org.chromium.Hermes.Error.Unknown'

        """
        self.is_prod_ci = is_prod_ci

        self.mm_proxy, self.hermes_manager, euicc_path = \
                    hermes_utils.initialize_test(is_prod_ci)

        # Error cases: Do operations that can result expected dbus errors
        # Install an invalid profile(wrong activation code)
        self.install_invalid_profile_test(euicc_path)

        # Enable a previously enabled profile
        self.enable_active_profile_test(euicc_path)

        # Disable a previously disabled profile
        self.disable_inactive_profile_test(euicc_path)

        if not self.is_prod_ci:
            # Do Enable->Uninstall same profile
            self.enable_uninstall_profile_test(euicc_path)

        logging.info('HermesErrorScenariosTest Completed')
