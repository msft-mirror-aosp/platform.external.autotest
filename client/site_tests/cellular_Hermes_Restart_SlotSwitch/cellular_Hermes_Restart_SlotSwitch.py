# Copyright (c) 2021 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import dbus
import logging
import random
import time

from autotest_lib.client.bin import test
from autotest_lib.client.common_lib import error
from autotest_lib.client.cros import upstart
from autotest_lib.client.cros.cellular import cellular_logging
from autotest_lib.client.cros.cellular import hermes_constants
from autotest_lib.client.cros.cellular import hermes_utils
from autotest_lib.client.cros.cellular import mm1_constants
from autotest_lib.client.cros.networking import mm1_proxy

log = cellular_logging.SetupCellularLogging('HermesRestartSlotSwitchTest')
class cellular_Hermes_Restart_SlotSwitch(test.test):
    """
    This test randomly restarts hermes or switches slots in between hermes
    operations.

    The test fails if any of the hermes operations fail.

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

    def restart_hermes(self):
        """ Restarts Hermes daemon """
        logging.debug('->restart_hermes start')
        upstart.restart_job('hermes')

        # hermes takes 15+ sec to load all apis, wait on hermes dbus not enough
        time.sleep(hermes_constants.HERMES_RESTART_WAIT_SECONDS)
        self.hermes_manager = hermes_utils.connect_to_hermes()

        euicc = self.hermes_manager.get_euicc(self.euicc_path)
        euicc.use_test_certs(not self.is_prod_ci)
        logging.debug('restart_hermes done')

        if not self.hermes_manager:
            logging.error('restart_hermes failed, no hermes daemon')
            raise error.TestFail('restart_hermes operation failed')

    def slot_switch(self):
        """ Perform SIM slot switch """
        try:
            # Get current slot and available slots and switch to slot 1 or 2
            # using MM
            logging.info('->slot_switch start')
            hermes_utils.mm_inhibit(False, self.mm_proxy)

            modem_proxy = self.mm_proxy.get_modem()
            sim_slots = modem_proxy.get_sim_slots()
            logging.debug('sim slots available: %d', sim_slots)

            current_slot = modem_proxy.get_primary_sim_slot()
            switch_to_slot = random.choice([1,2])
            logging.info('current sim slot: %d switching to slot: %d',
                        current_slot, switch_to_slot)

            modem_proxy.set_primary_slot(switch_to_slot)
            # Wait for modem, as slot switch causes modem DBus reload
            self.mm_proxy.wait_for_modem(
                    mm1_constants.MM_REPROBE_PROCESSING_TIME)

            # TODO(b/182337446):
            # Investigate why ModemManager1Proxy.get_proxy().get_modem()
            # fails if called immediately after self.mm_proxy.wait_for_modem(
            # mm1_constants.MM_REPROBE_PROCESSING_TIME)
            time.sleep(mm1_constants.MM_REPROBE_PROCESSING_TIME)
            self.mm_proxy = mm1_proxy.ModemManager1Proxy.get_proxy()
            modem_proxy = self.mm_proxy.get_modem()

            if not modem_proxy:
                raise error.TestFail('slot_switch failed. No modem found')

            new_slot = modem_proxy.get_primary_sim_slot()
            logging.info('primary slot after switch: %d', new_slot)

            # Shill changes the modemmanager slot if the active slot is empty,
            # and the non-active slot has a sim. Thus we cannot confirm that MM
            # comes back on new_slot. b/181346457

            hermes_utils.mm_inhibit(True, self.mm_proxy)
            logging.info('slot_switch success & the current active slot is: '
                        '%d\n', new_slot)
        except dbus.DBusException as e:
            logging.error('slot_switch failed')
            raise error.TestFail('slot_switch failed', e)

    def randomize_hermes_state(self):
        """
        Randomly restart hermes and switch slots in between hermes operations.

        @return Fails the test if any operation fails

        """
        logging.info('==randomize_hermes_state start==')

        # Call Restart hermes, Slot switch in random
        operations = [self.restart_hermes, self.slot_switch]
        logging.debug('randomly calling operations on hermes')
        num_operations = random.randrange(len(operations)+1)
        random.shuffle(operations)
        operations = operations[:num_operations]

        logging.info('The following operations will be performed in a '
                    'sequence : %s ', operations)
        try:
            [f() for f in operations]
            logging.info('==randomize_hermes_state - done==')
        except dbus.DBusException as e:
            logging.error('randomize_hermes_state operation failed')
            raise error.TestFail('Could not randomize hermes state', e)

    def hermes_operations_test(self, euicc_path):
        """
        Perform hermes operations with restart, slotswitch in between

        Do Install, Enable, Disable, Uninstall operations combined with random
        operations hermes restart, sim slot switch

        @param euicc_path: available euicc dbus path as string
        @return Fails the test if any operation fails

        """
        try:
            logging.info('hermes_operations_test start')

            # Do restart, slotswitch and install, enable, disable, uninstall
            self.randomize_hermes_state()
            installed_iccid = None
            logging.info('INSTALL:\n')
            installed_iccid = hermes_utils.install_profile(
            euicc_path, self.hermes_manager, self.is_prod_ci)

            self.randomize_hermes_state()
            logging.info('ENABLE:\n')
            hermes_utils.enable_or_disable_profile_test(
            euicc_path, self.hermes_manager, installed_iccid, True)

            self.randomize_hermes_state()
            logging.info('DISABLE:\n')
            hermes_utils.enable_or_disable_profile_test(
            euicc_path, self.hermes_manager, installed_iccid, False)

            if not self.is_prod_ci:
                self.randomize_hermes_state()
                logging.info('UNINSTALL:\n')
                hermes_utils.uninstall_profile_test(
                euicc_path, self.hermes_manager, installed_iccid)

            logging.info('===hermes_operations_test succeeded===\n')
        except dbus.DBusException as e:
            logging.error('hermes_operations with random hermes state failed')
            raise error.TestFail('randomize_hermes_state with '
                                'hermes_operations failed', e)

    def run_once(self, test_env, is_prod_ci=False):
        """
        Perform hermes ops with random restart, refresh, sim slot switch

        """
        self.test_env = test_env
        self.is_prod_ci = is_prod_ci

        self.mm_proxy, self.hermes_manager, self.euicc_path = \
                    hermes_utils.initialize_test(is_prod_ci)

        self.hermes_operations_test(self.euicc_path)
        logging.info('HermesRestartSlotSwitchTest Completed')
