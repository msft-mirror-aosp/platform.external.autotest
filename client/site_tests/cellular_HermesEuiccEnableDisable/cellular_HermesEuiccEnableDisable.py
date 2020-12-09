# Copyright (c) 2020 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import dbus
import logging
import random

from autotest_lib.client.bin import test
from autotest_lib.client.common_lib import error
from autotest_lib.client.cros.cellular import cellular_logging
from autotest_lib.client.cros.cellular import hermes_constants
from autotest_lib.client.cros.networking import hermes_proxy
from autotest_lib.client.cros.networking import mm1_proxy


log = cellular_logging.SetupCellularLogging('HermesEuiccEnableDisableTest')


class cellular_HermesEuiccEnableDisable(test.test):
    """
    Tests Enable and Disable functions on active/inactive Euicc present

    This test fails when not able to Enable/Disable a given Euicc profile

    """
    version = 1

    def _connect_to_hermes(self):
        """
        Attempts to connect to a DBus object.
        @raises: error.TestFail if connection fails.
        """
        self.hermes_manager = 'None'
        try:
            self.hermes_manager = \
                hermes_proxy.HermesManagerProxy().get_hermes_manager()
        except dbus.DBusException as e:
            logging.error('get_hermes_manager error: %s', e)
            raise error.TestFail('Connect to Hermes failed')
        if self.hermes_manager is 'None':
            raise error.TestFail('In Test Could not get connection to Hermes')

    def EnableTest(self, euicc_path):
        """ Validates enable profile api DBus call """
        try:
            euicc = self.hermes_manager.get_euicc(euicc_path)
            if not euicc:
                raise error.TestFail('No active euicc,'
                                     'try install profile and euicc on dut')

            installed_profiles = euicc.get_installed_profiles()
            if not installed_profiles:
                raise error.TestFail('No active profile,'
                                     'try install profiles on euicc')

            inactive_profile_found = False
            # Find inactive profile and enable
            for profile in installed_profiles.values():
                logging.info("profile to enable is : %s", profile)
                props = profile.properties()
                state = props.get('State')
                if hermes_constants.ProfileStateToString(state) == 'INACTIVE':
                    inactive_profile_found = True
                    profile.enable()
                    logging.info('EnableTest succeeded')
                    break
            if not inactive_profile_found:
                raise error.TestFail('EnableTest failed - No inactive profile')
            #Check profile state Active or not and all other profiles disabled
        except dbus.DBusException as e:
            logging.error('Profile enable error: %s', e)
            raise error.TestFail('Enable Failed')


    def DisableTest(self, euicc_path):
        """ Validates disable profile api DBus call """
        try:
            euicc = self.hermes_manager.get_euicc(euicc_path)
            if not euicc:
                raise error.TestFail('No active euicc,'
                                     'try install euicc and profile on dut')

            installed_profiles = euicc.get_installed_profiles()
            if not installed_profiles:
                raise error.TestFail('No active profile,'
                                     'try install profiles on euicc')

            active_profile_found = False
            # Find active profile and disable
            for profile in installed_profiles.values():
                logging.info("profile to disable is : %s", profile)
                props = profile.properties()
                state = props.get('State')
                if hermes_constants.ProfileStateToString(state) == 'ACTIVE':
                    active_profile_found = True
                    profile.disable()
                    logging.info('DisableTest succeeded')
                    break
            if not active_profile_found:
                raise error.TestFail('DisableTest failed - No active profile')
        except dbus.DBusException as e:
            logging.error('Resulted profile disable error: %s', e)
            raise error.TestFail('Disable Failed')

    def InstallProfileTest(self, euicc_path):
        """
        Validates InstallProfileFromActivationCode api on test euicc

        use SMDP calls to find iccid, activation code from pending profiles
        and install those profiles, this requires profiles generated based
        on EID of test esims in lab devices
        """

        try:
            # get all pending profiles which are generated on DUT EID
            # Read all profiles activation code from pending profile dict
            # Install a profile from activation code, keep iccid as well
            # Check the presence of this profile after installation

            activation_code = None
            confirmation_code = ""
            iccid = None
            euicc = None

            euicc = self.hermes_manager.get_euicc(euicc_path)
            if not euicc:
                logging.error('No Euicc enumerated')
                return False

            logging.info('euicc chosen: %s', euicc)
            profiles_pending = euicc.get_pending_profiles()
            if not profiles_pending:
                logging.error("No pending profile found")
                return False

            profile_path_to_install = list(profiles_pending.keys())[0]
            profile_to_install = profiles_pending[profile_path_to_install]
            logging.debug('First pending profile: %s', profile_path_to_install)

            props = profile_to_install.properties()
            iccid = props.get('Iccid')
            activation_code = props.get('ActivationCode')

            logging.info('Installing iccid: %s act_code:%s conf_code:%s',
                         iccid, activation_code, confirmation_code)
            # Install
            euicc.install_profile_from_activation_code(
                activation_code, confirmation_code)

            # Check if iccid found in installed profiles, installation success
            profiles_installed = euicc.get_installed_profiles()
            if not profiles_installed:
                logging.error("Zero profiles installed")
                raise error.TestFail('InstallProfileTest failed No Installed'
                                     'profile found')

            for profile in profiles_installed.values():
                props = profile.properties()
                if iccid == props.get('Iccid'):
                    self.iccid_installed = iccid
                    self.profile_installed = profile
                    logging.info('InstallProfileTest succeeded')
                    return True
            logging.error("Installed profile not found test failed")
            raise error.TestFail('InstallProfileTest failed, Just installed'
                                 'Iccid not found')
        except dbus.DBusException as e:
            logging.error("Failed to install a pending profile")
            if e.get_dbus_name() not in self.ok_errors:
                raise error.TestFail('InstallProfileTest failed with %s',
                                     repr(e))

    def InstallPendingProfileTest(self, euicc_path):
        """
        Validates InstallPendingProfile api on test euicc
        Find a profile from list of esim pending profiles which is not
        installed yet and install that profile

        Required to create pending profiles for each EID(euicc sim) in lab dut.
        create profiles from stork giving lab devices EID puts profiles in
        pending state for that euicc when RequestPendingProfiles called.
        Do install and immediately uninstall to keep those profiles in
        pending state
        """
        profile_to_install = None

        euicc = self.hermes_manager.get_euicc(euicc_path)
        if not euicc:
            logging.info('No euicc on DUT: %s', euicc)

        profiles_pending = euicc.get_pending_profiles()
        if not profiles_pending:
            logging.info("No pending profile found")
            return False

        profile_path_to_install = list(profiles_pending.keys())[0]
        profile_to_install = profiles_pending[profile_path_to_install]
        logging.debug('First pending profile: %s', profile_path_to_install)

        props = profile_to_install.properties()
        iccid = props.get('Iccid')
        activation_code = props.get('ActivationCode')

        logging.info('Installing profile:%s iccid: %s act_code: %s',
                     profile_path_to_install, iccid, activation_code)

        try:
            # Install
            profile = euicc.install_pending_profile(
                profile_path_to_install, "")
            logging.info('Installed pending profile is %s', profile)
            if not profile:
                logging.error('No profile object returned after install')
                return False
        except dbus.DBusException as e:
            logging.error("Failed to install pending profile error:%s", e)
            raise error.TestFail('Failed to install pending profile')

        # Find above installed profile, if not exists raise test failure
        installed_profiles = euicc.get_installed_profiles()
        if installed_profiles[profile_path_to_install] is None:
            raise error.TestFail('Install pending profile failed :%s',
                                 installed_profiles[profile_path_to_install])

        # Do uninstall the just installed profile if it has > 2 profiles
        if len(installed_profiles) > 2:
            logging.info('Uninstalling installed pending profile')
            euicc.uninstall_profile(profile)
        logging.info('InstallPendingProfileTest succeeded')
        return True

    def UninstallTest(self, euicc_path):
        """
        Validates UninstallProfile api by uninstalling any randomly
        selected installed profile
        """
        if self.is_prod_ci:
            raise error.TestFail("Cannot run uninstall test on eUICC's "
                                "with prod CI")
        logging.info('UninstallTest start')
        # Getinstalled profiles list and randomly uninstall a profile
        try:
            euicc = self.hermes_manager.get_euicc(euicc_path)
            if not euicc:
                logging.info('No euicc to uninstall any profile')
                return False

            profiles_installed = euicc.get_installed_profiles()
            if not profiles_installed:
                raise error.TestFail('In Test no installed profiles')

            profile_uninstall = random.choice(list(
                profiles_installed.keys()))
            euicc.uninstall_profile(profile_uninstall)
            logging.debug('Uninstalled profile %s', profile_uninstall)
            #Try to find the uninstalled profile, if exists raise test failure
            profiles_installed = {}
            profiles_installed = euicc.get_installed_profiles()
            for profile in profiles_installed.keys():
                if profile_uninstall in profile:
                    raise error.TestFail('Uninstall profile Failed')
            logging.info('UninstallTest succeeded')
            return True
        except dbus.DBusException as e:
            raise error.TestFail('Failed to uninstall profile %s', e)

    def run_once(self, is_prod_ci=False):
        """ Enable Disable Euicc by enabling or disabling a profile """
        self.is_prod_ci = is_prod_ci
        self.ok_errors = ['org.freedesktop.ModemManager1.Error.Core.InProgress'
                         'Timed out connecting to ModemManager1']
        try:
            mm1_proxy.ModemManager1Proxy.get_proxy().inhibit_device(
                    dbus.Boolean('true'))
        except dbus.exceptions.DBusException as error:
            if error.get_dbus_name() not in self.ok_errors:
                raise error

        logging.info('Connect to Hermes attempt')
        self._connect_to_hermes()

        logging.info('Refresh profiles')
        self.hermes_manager.refresh_profiles()

        # Always euicc/0 is prod one and euicc/1 is for test esim profiles
        self.prod_euicc_path = "/org/chromium/Hermes/euicc/0"
        self.test_euicc_path = "/org/chromium/Hermes/euicc/1"
        euicc_path = self.prod_euicc_path if self.is_prod_ci \
                                            else self.test_euicc_path
        if not self.is_prod_ci:
            is_smds_test = random.choice([True, False])
            logging.info('is_smds_test %s', is_smds_test)
            if is_smds_test:
                self.InstallPendingProfileTest(euicc_path)
            else:
                self.InstallProfileTest(euicc_path)

        self.EnableTest(euicc_path)
        self.DisableTest(euicc_path)

        if not self.is_prod_ci:
            self.UninstallTest(euicc_path)

        logging.info('Test Completed')
