# Lint as: python2, python3
# Copyright 2021 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Helper class for power autotests that force DUT to discharge with EC."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import logging
import time

from autotest_lib.client.common_lib import error
from autotest_lib.client.bin import utils
from autotest_lib.client.cros import ec
from six.moves import range

_FORCE_DISCHARGE_SETTINGS = ['false', 'true', 'optional']

# Retry times for ectool chargecontrol
ECTOOL_CHARGECONTROL_RETRY_TIMES = 3


def _parse(force_discharge):
    """
    Parse and return force discharge setting.

    @param force_discharge: string of whether to tell ec to discharge battery
            even when the charger is plugged in. 'false' means no forcing
            discharge; 'true' means forcing discharge and raising an error when
            it fails; 'optional' means forcing discharge when possible but not
            raising an error when it fails, which is more friendly to devices
            without a battery.

    @return: string representing valid force discharge setting.

    @raise error.TestError: for invalid force discharge setting.

    """
    setting = str(force_discharge).lower()
    if setting not in _FORCE_DISCHARGE_SETTINGS:
        raise error.TestError(
                'Force discharge setting \'%s\' need to be one of %s.' %
                (str(force_discharge), _FORCE_DISCHARGE_SETTINGS))
    return setting


def _wait_for_battery_discharge(status):
    """
    Polling every 100ms for 2 seconds until battery is discharging. This
    normally would take about 350ms.

    @param status: DUT power status object.

    @return: boolean indicating force discharge success.
    """
    for _ in range(20):
        status.refresh()
        if status.battery_discharging():
            return True
        time.sleep(0.1)
    return False


def chargeoverride_not_supported():
    """
    Jacuzzi/Kukui have a single type-C port and no PPC switch, so the
    'ectool chargeoverride dontcharge' command has no effect.

    @return: boolean indicating if chargeoverride has no effect.
    """
    return utils.get_board().startswith(('jacuzzi', 'kukui'))


def _skip_battery_sustainer():
    """
    Jacuzzi does not behave as expected with battery sustainer yet.
    TODO: b/293358575 - Modify/Delete this function when battery sustainer on
    Jacuzzi is fixed.

    @return: boolean indicating if battery sustainer command should be skipped.
    """
    return utils.get_board().startswith(('jacuzzi'))


def _charge_control_by_ectool(is_charge, ignore_status, host=None):
    """execute ectool commands.

    When forcing the battery to discharge, we force the charger off. If
    supported, we enable the battery sustainer for 5% display charge as a
    back-up in-case the charger connection resets (causing the system to charge
    again). Since the battery sustainer will only discharge on older firmwares
    if lower != upper, set the lower limit to 4%.

    For enabling charging, we reset chargeoverride and chargecontrol back to the
    default states.

    @param is_charge: bool, True for charging, False for discharging.
    @param ignore_status: do not raise an exception.
    @param host: An optional host object if running against a remote host

    @returns bool, True if the command success, False otherwise.

    @raises error.CmdError: if ectool returns non-zero exit status.
    """
    ec_cmd_discharge = 'ectool chargeoverride dontcharge'
    ec_cmd_charge = 'ectool chargeoverride off'
    ec_cmd_sustain = 'ectool chargecontrol normal 4 5'
    ec_cmd_normal = 'ectool chargecontrol normal'
    run_func = host.run if host else utils.run
    try:
        if is_charge:
            run_func(ec_cmd_charge)
            run_func(ec_cmd_normal)
        else:
            if chargeoverride_not_supported():
                # This will be overwritten by ec_cmd_sustain once is supported
                # on Jacuzzi/Kukui, and the latter will handle the discharge.
                run_func('ectool chargecontrol discharge')
            else:
                run_func(ec_cmd_discharge)
            if not _skip_battery_sustainer():
                try:
                    run_func(ec_cmd_sustain)
                except error.CmdError as e:
                    logging.info('Battery sustainer maybe not supported: %s',
                                 e)
    except error.CmdError as e:
        logging.warning('Unable to use ectool: %s', e)
        if ignore_status:
            return False
        else:
            raise e

    return True


def charge_control_by_ectool(is_charge, ignore_status=True, host=None):
    """Force the battery behavior by the is_charge paremeter.

    @param is_charge: Boolean, True for charging, False for discharging.
    @param ignore_status: do not raise an exception.
    @param host: An optional host object if running against a remote host

    @return: bool, True if the command success, False otherwise.

    @raises error.CmdError: if ectool returns non-zero exit status.
    """
    for i in range(ECTOOL_CHARGECONTROL_RETRY_TIMES):
        if _charge_control_by_ectool(is_charge, ignore_status, host):
            return True
        time.sleep(0.1)

    return False


def process(force_discharge, status):
    """
    Perform force discharge steps.

    @param force_discharge: string of whether to tell ec to discharge battery
            even when the charger is plugged in. 'false' means no forcing
            discharge; 'true' means forcing discharge and raising an error when
            it fails; 'optional' means forcing discharge when possible but not
            raising an error when it fails, which is more friendly to devices
            without a battery.
    @param status: DUT power status object.

    @return: bool to indicate whether force discharge steps are successful. Note
            that DUT cannot force discharge if DUT is not connected to AC.

    @raise error.TestError: for invalid force discharge setting.
    @raise error.TestNAError: when force_discharge is 'true' and the DUT is
            incapable of forcing discharge.
    @raise error.TestError: when force_discharge is 'true' and the DUT command
            to force discharge fails.
    """
    force_discharge = _parse(force_discharge)

    if force_discharge == 'true':
        if not status.battery:
            raise error.TestNAError('DUT does not have battery. '
                                    'Could not force discharge.')
        if not ec.has_cros_ec():
            raise error.TestNAError('DUT does not have CrOS EC. '
                                    'Could not force discharge.')
        if not charge_control_by_ectool(False):
            raise error.TestError('Could not run battery force discharge.')
        if not _wait_for_battery_discharge(status):
            logging.warning('Battery does not report discharging state.')
        return True
    elif force_discharge == 'optional':
        if not status.battery:
            logging.warning('DUT does not have battery. '
                            'Do not force discharge.')
            return False
        if not ec.has_cros_ec():
            logging.warning('DUT does not have CrOS EC. '
                            'Do not force discharge.')
            return False
        if not charge_control_by_ectool(False):
            logging.warning('Could not run battery force discharge. '
                            'Do not force discharge.')
            return False
        if not _wait_for_battery_discharge(status):
            logging.warning('Battery does not report discharging state.')
        return True
    elif force_discharge == 'false':
        return False


def restore(force_discharge_success):
    """
    Set DUT back to charging.

    @param force_discharge_success: if DUT previously forced discharge
            successfully, set DUT back to charging.
    """
    if force_discharge_success:
        if not charge_control_by_ectool(True):
            logging.warning('Can not restore from force discharge.')
