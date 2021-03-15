# Copyright (c) 2021 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import logging
import random

from autotest_lib.client.bin import test
from autotest_lib.client.common_lib import error
from autotest_lib.client.cros.cellular import cellular_logging
from autotest_lib.client.cros.cellular import hermes_utils

log = cellular_logging.SetupCellularLogging('HermesMultiProfile')

class cellular_Hermes_MultiProfile(test.test):
    """
    Test that Hermes can perform enable/disable operations on multiple profiles

    Prerequisites

    1) For test CI:
       Before running this test on test CI, two profiles need to be created on
    go/stork-profile. The profiles required to be linked to the EID of the dut.
    Profiles with class=operational and type=Android GTS test are known to work
    well with this test.

       We rely on the SMDS event to find the activation codes for the test.
    There is a limit of 99 downloads before profiles to be deleted and
    recreated.(b/181723689)

    2) For prod CI:
       Install two production profiles before running the test.

    """
    version = 1

    def run_once(self, test_env, is_prod_ci=False):
        """ Enable/Disable a profile """
        self.is_prod_ci = is_prod_ci

        self.mm_proxy, self.hermes_manager, euicc_path = \
                    hermes_utils.initialize_test(is_prod_ci)

        first_iccid = hermes_utils.get_iccid_of_disabled_profile(
            euicc_path, self.hermes_manager, self.is_prod_ci)

        logging.info('Enabling first profile')
        hermes_utils.enable_or_disable_profile_test(
            euicc_path, self.hermes_manager, first_iccid, True)

        # We need to get a second profile to test operations over multiple
        # profiles. It is important to enable the first_iccid before fetching
        # second_iccid, since get_iccid_of_disabled_profile returns the first
        # disabled profile it finds.
        second_iccid = hermes_utils.get_iccid_of_disabled_profile(
            euicc_path, self.hermes_manager, self.is_prod_ci)

        if not first_iccid or not second_iccid :
            fail_iccid = 'first' if not first_iccid else 'second'
            raise error.TestError('Could not get' + fail_iccid  + ' iccid')

        if first_iccid == second_iccid:
            raise error.TestError('Two distinct profiles need to be installed '
                'before test begins. Got only ' + first_iccid)

        logging.info('Enabling second profile, expecting Hermes to disable '
                    'the first profile behind the scenes.')
        hermes_utils.enable_or_disable_profile_test(
            euicc_path, self.hermes_manager, second_iccid, True)

        logging.info('Enabling first profile again')
        hermes_utils.enable_or_disable_profile_test(
            euicc_path, self.hermes_manager, first_iccid, True)

        logging.info('Disabling first profile to prevent enabling already '
                    'enabled profile in next stress loop')
        hermes_utils.enable_or_disable_profile_test(
            euicc_path, self.hermes_manager, first_iccid, False)

        logging.info('Stress enable/disable profiles')
        for i in range(1,10):
            for iccid in [first_iccid, second_iccid]:
                logging.info('Enabling profile:%s', iccid)
                hermes_utils.enable_or_disable_profile_test(
                    euicc_path, self.hermes_manager, iccid, True)
                explicitly_disable_profile = random.choice([True,False])
                if (explicitly_disable_profile):
                    logging.info('Disabling profile:%s', iccid)
                    hermes_utils.enable_or_disable_profile_test(
                        euicc_path, self.hermes_manager, iccid, False)

        logging.info('HermesMultiProfileTest Completed')
