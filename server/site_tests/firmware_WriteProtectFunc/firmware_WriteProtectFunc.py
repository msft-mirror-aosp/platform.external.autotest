# Copyright 2020 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import logging
import os

from autotest_lib.client.common_lib import error
from autotest_lib.server.cros.faft.firmware_test import FirmwareTest
from autotest_lib.server.cros.faft.firmware_test import ConnectionError


BIOS = 'bios'
EC = 'ec'


class firmware_WriteProtectFunc(FirmwareTest):
    """
    This test checks whether the SPI flash write-protection functionally works
    """
    version = 1

    def initialize(self, host, cmdline_args, dev_mode=False):
        """Initialize the test"""
        super(firmware_WriteProtectFunc, self).initialize(host, cmdline_args)
        self.switcher.setup_mode('dev' if dev_mode else 'normal')
        if self.faft_config.chrome_ec:
            self._targets = (BIOS, EC)
        else:
            self._targets = (BIOS, )
        self._rpcs = {BIOS: self.faft_client.bios,
                EC: self.faft_client.ec}
        self._flashrom_targets = {BIOS: 'host', EC: 'ec'}
        self._original_sw_wps = {}
        for target in self._targets:
            sw_wp_dict = self._rpcs[target].get_write_protect_status()
            self._original_sw_wps[target] = sw_wp_dict['enabled']
        self._original_hw_wp = 'on' in self.servo.get('fw_wp_state')
        self.backup_firmware()

    def cleanup(self):
        """Cleanup the test"""
        try:
            if self.is_firmware_saved():
                self.restore_firmware()
        except ConnectionError:
            logging.error("ERROR: DUT did not come up after firmware restore!")

        try:
            # Recover SW WP status.
            if hasattr(self._original_sw_wps):
                # If HW WP is enabled, we have to disable it first so that
                # SW WP can be changed.
                current_hw_wp = 'on' in self.servo.get('fw_wp_state')
                if current_hw_wp:
                    self.set_hardware_write_protect(False)
                for target in self._targets:
                    if hasattr(self._original_sw_wps, target):
                        self._set_write_protect(target,
                                self._original_sw_wps[target])
                self.set_hardware_write_protect(current_hw_wp)
            # Recover HW WP status.
            if hasattr(self, '_original_hw_wp'):
              self.set_hardware_write_protect(self._original_hw_wp)
        except Exception as e:
            logging.error('Caught exception: %s', str(e))

        super(firmware_WriteProtectFunc, self).cleanup()

    def _set_write_protect(self, target, enable):
        """
        Set write_protect to `enable` for the specified target.

        @param target: Which firmware to toggle the write-protect for,
                       either 'bios' or 'ec'
        @type target: string
        @param enable: Whether to enable or disable write-protect
        @type enable: bool
        """
        assert target in (BIOS, EC)
        if target == BIOS:
            self.set_hardware_write_protect(enable)
            self.faft_client.bios.set_write_protect_region('WP_RO', enable)
        elif target == EC:
            self.switcher.mode_aware_reboot('custom',
                    lambda:self.set_ec_write_protect_and_reboot(enable))

    def _get_relative_path(self, target):
        """
        Send an RPC.updater call to get the relative path for the target.

        @param target: Which firmware to get the relative path to,
                       either 'bios' or 'ec'.
        @type target: string
        @return: The relative path of the bios/ec image in the shellball.
        """
        assert target in (BIOS, EC)
        if target == BIOS:
            return self.faft_client.updater.get_bios_relative_path()
        elif target == EC:
            return self.faft_client.updater.get_ec_relative_path()

    def run_cmd(self, command, checkfor=''):
        """
        Log and execute command and return the output.

        @param command: Command to execute on device.
        @param checkfor: If not empty, make the test fail when this param
            is not found in the command output.
        @returns the output of command.
        """
        command = command + ' 2>&1'
        logging.info('Execute %s', command)
        output = self.faft_client.system.run_shell_command_get_output(command)
        logging.info('Output >>> %s <<<', output)
        if checkfor and checkfor not in '\n'.join(output):
            raise error.TestFail('Expect %s in output of cmd <%s>:\n\t%s' %
                                 (checkfor, command, '\n\t'.join(output)))
        return output

    def get_wp_ro_firmware_section(self, firmware_file, wp_ro_firmware_file):
        """
        Read out WP_RO section from the firmware file.

        @param firmware_file: The AP or EC firmware binary to be parsed.
        @param wp_ro_firmware_file: The file path for the WP_RO section
            dumped from the firmware_file.
        @returns the output of the dd command.
        """
        cmd_output = self.run_cmd(
                'futility dump_fmap -p %s WP_RO'% firmware_file)
        if cmd_output:
            unused_name, offset, size = cmd_output[0].split()

        return self.run_cmd('dd bs=1 skip=%s count=%s if=%s of=%s' %
                            (offset, size, firmware_file, wp_ro_firmware_file))

    def run_once(self):
        """Runs a single iteration of the test."""
        work_path = self.faft_client.updater.get_work_path()

        for target in self._targets:
            logging.info('Beginning test for target %s', target)
            ro_before = os.path.join(work_path, '%s_ro_before.bin' % target)
            ro_after = os.path.join(work_path, '%s_ro_after.bin' % target)
            ro_test = os.path.join(work_path, '%s_ro_test.bin' % target)

            # Use the firmware blobs unpacked from the firmware updater for
            # testing. To ensure there is difference in WP_RO section between
            # the firmware on the DUT and the firmware unpacked from the
            # firmware updater, we mess around FRID.
            self.faft_client.updater.modify_image_fwids(target, ['ro'])

            test = os.path.join(work_path, self._get_relative_path(target))
            self.get_wp_ro_firmware_section(test, ro_test)

            # Check if RO FW really can't be overwritten when WP is enabled.
            self._set_write_protect(target, True)
            self.run_cmd('flashrom -p %s -r -i WP_RO:%s' %
                    (self._flashrom_targets[target], ro_before),
                    'SUCCESS')

            # Writing WP_RO section is expected to fail.
            self.run_cmd('flashrom -p %s -w -i WP_RO:%s' %
                    (self._flashrom_targets[target], ro_test),
                    'FAIL')
            self.run_cmd('flashrom -p %s -r -i WP_RO:%s' %
                    (self._flashrom_targets[target], ro_after),
                    'SUCCESS')

            self.switcher.mode_aware_reboot(reboot_type='cold')

            # The WP_RO section on the DUT should not change.
            cmp_output = self.run_cmd('cmp %s %s' % (ro_before, ro_after))
            if ''.join(cmp_output) != '':
                raise error.TestFail('%s RO changes when WP is on!' %
                        target.upper())

            # Check if RO FW can be overwritten when WP is disabled.
            self._set_write_protect(target, False)

            # Writing WP_RO section is expected to succeed.
            self.run_cmd('flashrom -p %s -w -i WP_RO:%s' %
                    (self._flashrom_targets[target], ro_test),
                    'SUCCESS')
            self.run_cmd('flashrom -p %s -r -i WP_RO:%s' %
                    (self._flashrom_targets[target], ro_after),
                    'SUCCESS')

            # The DUT's WP_RO section should be the same as the test firmware.
            cmp_output = self.run_cmd('cmp %s %s' % (ro_test, ro_after))
            if ''.join(cmp_output) != '':
                raise error.TestFail('%s RO is not flashed correctly'
                                     'when WP is off!' % target.upper())
