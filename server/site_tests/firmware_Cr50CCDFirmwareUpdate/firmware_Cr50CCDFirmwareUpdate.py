# Copyright 2020 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.


"""The autotest performing FW update, both EC and AP in CCD mode."""
import logging
import os

from autotest_lib.client.common_lib import error
from autotest_lib.server.cros.faft.cr50_test import Cr50Test
from autotest_lib.server.cros.servo import servo

MAX_EC_CLEANUP_TRIES=2
MAX_EC_RESPONSE_TRIES=3


class firmware_Cr50CCDFirmwareUpdate(Cr50Test):
    """A test that can provision a machine to the correct firmware version."""

    version = 1
    should_restore_fw = False

    BIOS_NAME = 'ccd.image.bin'
    EC_NAME = 'ccd.ec.bin'

    def initialize(self, host, cmdline_args, full_args, fw_path=None):
        """Initialize the test and check if cr50 exists.

        Raises:
            TestNAError: If the dut is not proper for this test for its RDD
                         recognition problem.
        """
        if not host.servo:
            raise error.TestNAError('Unable to start servod')
        servo_type = host.servo.get_servo_version()
        if 'ccd' not in servo_type:
            raise error.TestNAError('unsupported servo type: %s' % servo_type)
        super(firmware_Cr50CCDFirmwareUpdate,
              self).initialize(host, cmdline_args, full_args)

        # Don't bother if there is no Chrome EC.
        if not self.check_ec_capability():
            raise error.TestNAError('Nothing needs to be tested on this device')

        self.install_ec = full_args.get('skip_ec_fw_update',
                                        '').lower() != 'true'
        self.fw_path = fw_path
        self.fw_build = full_args.get('fw_build', '')
        self.ec_fw_path = full_args.get('ec_fw_path', None)
        self.bios_fw_path = full_args.get('bios_fw_path', None)

        if eval(full_args.get('backup_fw', 'False')):
            self.backup_firmware()

    def cleanup(self):
        try:
            if not self.should_restore_fw:
                return

            self.servo.enable_main_servo_device()
            self.gsc.reboot()

            # Verify the EC is responsive before raising an error and going to
            # cleanup. Repair and cleanup don't recover corrupted EC firmware
            # very well.
            try:
                self.verify_ec_response()
            except Exception as e:
                logging.error('Caught exception: %s', str(e))

            if self.is_firmware_saved():
                logging.info('Restoring firmware')
                self.restore_firmware()
            else:
                logging.info('chromeos-firmwareupdate --mode=recovery')
                result = self._client.run('chromeos-firmwareupdate'
                                          ' --mode=recovery',
                                          ignore_status=True,
                                          timeout=600)
                if result.exit_status != 0:
                    logging.error('chromeos-firmwareupdate failed: %s',
                                  result.stdout.strip())
                self._client.reboot()
        except Exception as e:
            logging.error('Caught exception: %s', str(e))
        finally:
            super(firmware_Cr50CCDFirmwareUpdate, self).cleanup()

    def verify_ec_response(self):
        """ Verify the EC is responsive."""
        if not self.install_ec:
            return
        # Try to reflash EC a couple of times to see if it's possible to recover
        # the device now.
        for _ in range(MAX_EC_CLEANUP_TRIES):
            # Try a few times to get response before resorting to reflash.
            for _ in range(MAX_EC_RESPONSE_TRIES):
                try:
                    if self.servo.get_ec_board():
                        return
                except servo.ConsoleError as e:
                    logging.error('EC console is unresponsive: %s', str(e))

            try:
                self.cros_host.firmware_install(build=self.fw_build,
                                                local_tarball=self.fw_path,
                                                install_bios=False,
                                                ec_image=self.ec_fw_path)
            except Exception as e:
                logging.error('firmware_install failed: %s', str(e))

        logging.error('DUT likely needs a manual recovery.')

    def _download_firmware_from_host(self):
        """Download the ap and ec image from the dut.

        Save the ec and ap firmware image locally, so the test can use them to
        verify flashing the ec and ap with ccd.
        """
        if self.ec_fw_path and self.bios_fw_path:
            logging.info('User supplied ec and ap fw images')
            return
        self.setup_firmwareupdate_shellball()
        work_path = self.faft_client.updater.get_work_path()

        if not self.bios_fw_path:
            self.bios_fw_path = os.path.join(self.resultsdir, self.BIOS_NAME)
            bios_name = self.faft_client.updater.get_bios_relative_path()
            bios_path = os.path.join(work_path, bios_name)
            logging.info('Using DUT bios image %s', bios_path)
            self._client.get_file(bios_path, self.bios_fw_path)

        if not self.ec_fw_path:
            self.ec_fw_path = os.path.join(self.resultsdir, self.EC_NAME)
            ec_name = self.faft_client.updater.get_ec_relative_path()
            ec_path = os.path.join(work_path, ec_name)
            logging.info('Using DUT ec image %s', ec_path)
            self._client.get_file(ec_path, self.ec_fw_path)

    def run_once(self, host, rw_only=False):
        """The method called by the control file to start the test.

        Args:
          host: a CrosHost object of the machine to update.
          rw_only: True to only update the RW firmware.

        Raises:
          TestFail: if the firmware version remains unchanged.
          TestError: if the latest firmware release cannot be located.
          TestNAError: if the test environment is not properly set.
                       e.g. the servo type doesn't support this test.
        """
        self.cros_host = host
        board = (getattr(self.faft_config, 'parent', None)
                 or getattr(self.faft_config, 'platform', None))
        platform = self.cros_host.get_platform()

        # Allow faft_config.fw_update_build to override
        # get_latest_release_version().
        config_fw_build = getattr(self.faft_config, 'fw_update_build', None)

        if self.fw_build:
            logging.info('using fw build: %s', self.fw_build)
        elif self.fw_path:
            logging.info('using fw tarball: %s', self.fw_path)
        else:
            self._download_firmware_from_host()
            # Find the latest firmware build, so the test can download
            # npcx_monitor.bin.
            if 'npcx' in self.servo.get('ec_chip'):
                try:
                    self.fw_build = self.cros_host.get_latest_release_version(
                            platform, board)
                except:
                    self.fw_build = None
            logging.info('using EC image: %s', self.ec_fw_path)
            logging.info('using bios image: %s', self.bios_fw_path)

        # Fast open cr50 and check if testlab is enabled.
        self.fast_ccd_open(enable_testlab=True)
        if not self.servo.enable_ccd_servo_device():
            raise error.TestNAError('Cannot make ccd active')
        # Add support for downloading npcx_monitor.bin without a tarball.
        if not self.fw_path and self.servo.get('ec_chip').startswith('npcx'):
            self.install_ec = False
        # If it is ITE EC, then allow CCD I2C access for flashing EC.
        if self.servo.get('ec_chip').startswith('it8'):
            self.gsc.set_cap('I2C', 'Always')

        # Make sure to use the GSC ec_reset command for cold reset snce that's
        # what normal ccd devices will use.
        if self.servo.has_control('cold_reset_select'):
            self.servo.set('cold_reset_select', 'gsc_ec_reset')
        # TODO(b/196824029): remove when servod supports using the power state
        # controller with the ccd device.
        try:
            self.host.servo.get_power_state_controller().reset()
        except Exception as e:
            logging.info(e)
            raise error.TestNAError('Unable to do power state reset with '
                                    'active ccd device')

        # Flashing the dut involves running power_state:reset. If this locks
        # ccd, flashing won't work. Raise an error to fix cold_reset.
        if self.gsc.get_ccd_level() != self.gsc.OPEN:
            raise error.TestError(
                    'Resetting the dut locked ccd. Flashing with '
                    'CCD will not work. Switch cold_reset to '
                    'gsc_ec_reset')

        self.should_restore_fw = True
        if not self.install_ec:
            self.ec_fw_path = None
        try:
            self.cros_host.firmware_install(build=self.fw_build,
                                            rw_only=rw_only,
                                            local_tarball=self.fw_path,
                                            dest=self.resultsdir,
                                            verify_version=True,
                                            install_ec=self.install_ec,
                                            ec_image=self.ec_fw_path,
                                            bios_image=self.bios_fw_path)
        except Exception as e:
            # The test failed to flash the firmware.
            raise error.TestFail('firmware_install failed with CCD: %s' %
                                 str(e))
