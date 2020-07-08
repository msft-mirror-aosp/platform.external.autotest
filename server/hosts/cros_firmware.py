# Copyright 2016 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""
Repair actions and verifiers relating to CrOS firmware.

This contains the repair actions and verifiers need to find problems
with the firmware installed on Chrome OS DUTs, and when necessary, to
fix problems by updating or re-installing the firmware.

The operations in the module support two distinct use cases:
  * DUTs used for FAFT tests can in some cases have problems with
    corrupted firmware.  The module supplies `FirmwareStatusVerifier`
    to check for corruption, and supplies `FaftFirmwareRepair` to
    re-install firmware of current faft stable_version via servo
    when needed.
  * DUTs used for general testing normally should be running a
    designated "stable" firmware version.  This module supplies
    `FirmwareVersionVerifier` to detect and automatically update
    firmware that is out-of-date from the designated version. This model
    also supplys `GeneralFirmwareRepair` to re-install firmware that
    tied with current stable_version image via servo when needed.

For purposes of the operations in the module, we distinguish three kinds
of DUT, based on pool assignments:
  * DUTs used for general testing.  These DUTs automatically check for
    and install the stable firmware using `FirmwareVersionVerifier`.
  * DUTs in pools used for FAFT testing.  These check for bad firmware
    builds with `FirmwareStatusVerifier`, and will fix problems using
    `FirmwareRepair`.  These DUTs don't check for or install the
    stable firmware.
  * DUTs not in general pools, and not used for FAFT.  These DUTs
    are expected to be managed by separate processes and are excluded
    from all of the verification and repair code in this module.
"""

# pylint: disable=missing-docstring

import json
import logging

import common
from autotest_lib.client.common_lib import global_config
from autotest_lib.client.common_lib import hosts
from autotest_lib.server import afe_utils
from autotest_lib.server.hosts import repair_utils


# _FIRMWARE_REPAIR_POOLS - The set of pools that should be
# managed by `FirmwareStatusVerifier` and `FirmwareRepair`.
#
_FIRMWARE_REPAIR_POOLS = set(
    global_config.global_config.get_config_value(
            'CROS',
            'pools_support_firmware_repair',
            type=str).split(','))


def _is_firmware_testing_device(host):
    """
    check if a host is dedicated for firmware testing.

    When this function returns true, the DUT should be managed by
    `FirmwareStatusVerifier` and `FaftFirmwareRepair`, but not
    `FirmwareVersionVerifier` and `GeneralFirmwareRepair.

    @return A true value if the host should use `FirmwareStatusVerifier`
            and `FaftFirmwareRepair`; a false value otherwise.
    """
    info = host.host_info_store.get()
    return bool(info.pools & _FIRMWARE_REPAIR_POOLS)


def _is_firmware_update_supported(host):
    """
    Return whether a DUT should be running the standard firmware.

    In the test lab, DUTs used for general testing, (e.g. the `bvt`
    pool) need their firmware kept up-to-date with
    `FirmwareVersionVerifier`.  However, some pools have alternative
    policies for firmware management.  This returns whether a given DUT
    should be updated via the standard stable version update, or
    managed by some other procedure.

    @param host   The host to be checked for update policy.
    @return A true value if the host should use
            `FirmwareVersionVerifier`; a false value otherwise.
    """
    return not _is_firmware_testing_device(host)


def _get_available_firmware(host, model):
    """Get the available RW firmware version given the model.

    @param host     The host to get available firmware for.
    @param model    The model name to get corresponding firmware version.
    @return The available RW firmware version if found, else, None.
    """
    result = host.run('chromeos-firmwareupdate --manifest', ignore_status=True)

    if result.exit_status != 0:
        return None

    # The manifest is a JSON in .model.host.versions.rw
    data = json.loads(result.stdout) or {}
    key = model if len(data) > 1 else next(data.iterkeys(), '')
    key += '.host.versions.rw'
    for k in key.split('.'):
        data = data.get(k, {})
    return data or None


class FirmwareStatusVerifier(hosts.Verifier):
    """
    Verify that a host's firmware is in a good state.

    For DUTs that run firmware tests, it's possible that the firmware
    on the DUT can get corrupted.  This verifier checks whether it
    appears that firmware should be re-flashed using servo.
    """

    def verify(self, host):
        if not _is_firmware_testing_device(host):
            return
        try:
            # Read the AP firmware and dump the sections that we're
            # interested in.
            cmd = ('mkdir /tmp/verify_firmware; '
                   'cd /tmp/verify_firmware; '
                   'for section in VBLOCK_A VBLOCK_B FW_MAIN_A FW_MAIN_B; '
                   'do flashrom -p host -r -i $section:$section; '
                   'done')
            host.run(cmd)

            # Verify the firmware blocks A and B.
            cmd = ('vbutil_firmware --verify /tmp/verify_firmware/VBLOCK_%c'
                   ' --signpubkey /usr/share/vboot/devkeys/root_key.vbpubk'
                   ' --fv /tmp/verify_firmware/FW_MAIN_%c')
            for c in ('A', 'B'):
                rv = host.run(cmd % (c, c), ignore_status=True)
                if rv.exit_status:
                    raise hosts.AutoservVerifyError(
                            'Firmware %c is in a bad state.' % c)
        finally:
            # Remove the temporary files.
            host.run('rm -rf /tmp/verify_firmware')

    @property
    def description(self):
        return 'Firmware on this DUT is clean'


class FirmwareRepair(hosts.RepairAction):
    """
    Reinstall the firmware image using servo.

    This repair function attempts to use servo to install the DUT's
    designated "stable firmware version".

    This repair method only applies to DUTs used for FAFT.
    """
    def _get_stable_build(self, host):
        raise NotImplementedError('Class %s does not implement '
                                  '_get_stable_build()'
                                   % type(self).__name__)

    def repair(self, host):
        repair_utils.require_servo(host, ignore_state=True)
        build = self._get_stable_build(host)
        if not build:
            raise hosts.AutoservRepairError(
                  'Failed to find stable firmware build for %s, if the DUT is'
                  ' in faft-*pool, faft stable_version needs to be set.'
                   % host.hostname, 'cannot find firmware stable_version')
        host.firmware_install(build)


class FaftFirmwareRepair(FirmwareRepair):
    """
    Reinstall the firmware for DUTs in faft related pool.
    """
    def _get_stable_build(self, host):
        info = host.host_info_store.get()
        return afe_utils.get_stable_faft_version_v2(info)

    def _is_applicable(self, host):
        return _is_firmware_testing_device(host)

    @property
    def description(self):
        return 'Re-install the stable firmware(faft) via servo'


class GeneralFirmwareRepair(FirmwareRepair):
    """Reinstall the firmware for non-faft DUTs.
    We need different RepairAction for non firmware testing DUT because
    we want only try re-install firmware if all other RepairAction could
    not restore ssh capability to the DUT.
    """
    def _get_stable_build(self, host):
        # Use firmware in current stable os build.
        return host.get_cros_repair_image_name()

    def _is_applicable(self, host):
        return not _is_firmware_testing_device(host)

    @property
    def description(self):
        return 'Re-install the stable firmware(non-faft) via servo'


class FirmwareVersionVerifier(hosts.Verifier):
    """
    Check for a firmware update, and apply it if appropriate.

    This verifier checks to ensure that either the firmware on the DUT
    is up-to-date, or that the target firmware can be installed from the
    currently running build.

    Failure occurs when all of the following apply:
     1. The DUT is not excluded from updates.  For example, DUTs used
        for FAFT testing use `FirmwareRepair` instead.
     2. The DUT's board has an assigned stable firmware version.
     3. The DUT is not running the assigned stable firmware.
     4. The firmware supplied in the running OS build is not the
        assigned stable firmware.

    If the DUT needs an upgrade and the currently running OS build
    supplies the necessary firmware, the verifier installs the new
    firmware using `chromeos-firmwareupdate`.  Failure to install will
    cause the verifier to fail.

    This verifier nominally breaks the rule that "verifiers must succeed
    quickly", since it can invoke `reboot()` during the success code
    path.  We're doing it anyway for two reasons:
      * The time between updates will typically be measured in months,
        so the amortized cost is low.
      * The reason we distinguish repair from verify is to allow
        rescheduling work immediately while the expensive repair happens
        out-of-band.  But a firmware update will likely hit all DUTs at
        once, so it's pointless to pass the buck to repair.

    N.B. This verifier is a trigger for all repair actions that install
    the stable repair image.  If the firmware is out-of-date, but the
    stable repair image does *not* contain the proper firmware version,
    _the target DUT will fail repair, and will be unable to fix itself_.
    """

    @staticmethod
    def _get_rw_firmware(host):
        result = host.run('crossystem fwid', ignore_status=True)
        if result.exit_status == 0:
            return result.stdout
        else:
            return None

    @staticmethod
    def _check_hardware_match(version_a, version_b):
        """
        Check that two firmware versions identify the same hardware.

        Firmware version strings look like this:
            Google_Gnawty.5216.239.34
        The part before the numbers identifies the hardware for which
        the firmware was built.  This function checks that the hardware
        identified by `version_a` and `version_b` is the same.

        This is a sanity check to protect us from installing the wrong
        firmware on a DUT when a board label has somehow gone astray.

        @param version_a  First firmware version for the comparison.
        @param version_b  Second firmware version for the comparison.
        """
        hardware_a = version_a.split('.')[0]
        hardware_b = version_b.split('.')[0]
        if hardware_a != hardware_b:
            message = 'Hardware/Firmware mismatch updating %s to %s'
            raise hosts.AutoservVerifyError(
                    message % (version_a, version_b))

    def verify(self, host):
        # Test 1 - The DUT is not excluded from updates.
        if not _is_firmware_update_supported(host):
            return
        # Test 2 - The DUT has an assigned stable firmware version.
        info = host.host_info_store.get()
        if info.model is None:
            raise hosts.AutoservVerifyError(
                    'Can not verify firmware version. '
                    'No model label value found')

        stable_firmware = None
        try:
            stable_firmware = afe_utils.get_stable_firmware_version_v2(info)
        except Exception as e:
            logging.exception('Failed lookup to AFE for stable fw version '
                              ' with exception: %s', e)

        if stable_firmware is None:
            # This DUT doesn't have a firmware update target
            return

        # For tests 3 and 4:  If the output from `crossystem` or
        # `chromeos-firmwareupdate` isn't what we expect, we log an
        # error, but don't fail:  We don't want DUTs unable to test a
        # build merely because of a bug or change in either of those
        # commands.

        # Test 3 - The DUT is not running the target stable firmware.
        current_firmware = self._get_rw_firmware(host)
        if current_firmware is None:
            logging.error('DUT firmware version can\'t be determined.')
            return
        if current_firmware == stable_firmware:
            return
        # Test 4 - The firmware supplied in the running OS build is not
        # the assigned stable firmware.
        available_firmware = _get_available_firmware(host, info.model)
        if available_firmware is None:
            logging.error('Supplied firmware version in OS can\'t be '
                          'determined.')
            return
        if available_firmware != stable_firmware:
            raise hosts.AutoservVerifyError(
                    'DUT firmware requires update from %s to %s' %
                    (current_firmware, stable_firmware))
        # Time to update the firmware.
        logging.info('Updating firmware from %s to %s',
                     current_firmware, stable_firmware)
        self._check_hardware_match(current_firmware, stable_firmware)
        try:
            host.run('chromeos-firmwareupdate --mode=autoupdate')
            host.reboot()
        except Exception as e:
            message = ('chromeos-firmwareupdate failed: from '
                       '%s to %s')
            logging.exception(message, current_firmware, stable_firmware)
            raise hosts.AutoservVerifyError(
                    message % (current_firmware, stable_firmware))
        final_firmware = self._get_rw_firmware(host)
        if final_firmware != stable_firmware:
            message = ('chromeos-firmwareupdate failed: tried upgrade '
                       'to %s, now running %s instead')
            raise hosts.AutoservVerifyError(
                    message % (stable_firmware, final_firmware))

    @property
    def description(self):
        return 'The firmware on this DUT is up-to-date'
