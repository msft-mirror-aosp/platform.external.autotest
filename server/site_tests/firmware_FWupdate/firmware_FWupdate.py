# Copyright 2015 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import logging
import os

from chromite.lib import remote_access
from autotest_lib.client.common_lib import error
from autotest_lib.client.common_lib import utils
from autotest_lib.server.cros.faft.firmware_test import FirmwareTest


class firmware_FWupdate(FirmwareTest):
    """RO+RW firmware update using chromeos-firmware with various modes.
    If custom images are supplied, the DUT is left running that firmware, so the
    test can be used to apply updates.

    Accepted --args names:

    mode=[recovery|factory]
        Run test with the given mode (default 'recovery')

    new_bios=
    new_ec=
    new_pd=
        apply the given image(s)

    """

    # Region to use for flashrom wp-region commands
    WP_REGION = 'WP_RO'

    def initialize(self, host, cmdline_args):

        self.flashed = False

        dict_args = utils.args_to_dict(cmdline_args)
        super(firmware_FWupdate, self).initialize(host, cmdline_args)

        self.new_bios = dict_args.get('new_bios', None)
        self.new_ec = dict_args.get('new_ec', None)
        self.new_pd = dict_args.get('new_pd', None)

        if self.new_bios:
            self.images_specified = True
            if not os.path.isfile(self.new_bios):
                raise error.TestError('Specified BIOS file does not exist: %s'
                                      % self.new_bios)
            logging.info('new_bios=%s', self.new_bios)

        if self.new_ec:
            self.images_specified = True
            if not os.path.isfile(self.new_ec):
                raise error.TestError('Specified EC file does not exist: %s'
                                      % self.new_ec)
            logging.info('new_ec=%s', self.new_ec)

        if self.new_pd:
            self.images_specified = True
            if not os.path.isfile(self.new_pd):
                raise error.TestError('Specified PD file does not exist: %s'
                                      % self.new_pd)
            logging.info('new_pd=%s', self.new_pd)

        if not self.images_specified:
            raise error.TestError(
                    "This test requires specifying images to flash.")

        self._old_bios_wp = self.faft_client.bios.get_write_protect_status()

        if 'wp' in dict_args:
            self.wp = int(dict_args['wp'])
        else:
            self.wp = None

        self.set_hardware_write_protect(False)
        self.faft_client.bios.set_write_protect_region(self.WP_REGION, True)
        self.set_hardware_write_protect(True)

        self.mode = dict_args.get('mode', 'recovery')

        if self.mode not in ('factory', 'recovery'):
            raise error.TestError('Unhandled mode: %s' % self.mode)

        if self.mode == 'factory' and self.wp:
            # firmware_UpdateModes already checks this case, so skip it here.
            raise error.TestNAError(
                    "This test doesn't handle mode=factory with wp=1")

    def get_installed_versions(self):
        """Get the installed versions of BIOS and EC firmware.

        @return: A nested dict keyed by target ('bios' or 'ec') and then section
        @rtype: dict
        """
        versions = dict()
        versions['bios'] = self.faft_client.updater.get_device_fwids('bios')
        if self.faft_config.chrome_ec:
            versions['ec'] = self.faft_client.updater.get_device_fwids('ec')
        return versions

    def copy_cmdline_images(self, hostname):
        """Copy the specified command line images into the extracted shellball.

        @param hostname: hostname (not the Host object) to copy to
        """
        if self.new_bios or self.new_ec or self.new_pd:

            extract_dir = self.faft_client.updater.get_work_path()

            dut_access = remote_access.RemoteDevice(hostname, username='root')

            # Replace bin files.
            if self.new_bios:
                bios_rel = self.faft_client.updater.get_bios_relative_path()
                bios_path = os.path.join(extract_dir, bios_rel)
                dut_access.CopyToDevice(self.new_bios, bios_path, mode='scp')

            if self.new_ec:
                ec_rel = self.faft_client.updater.get_ec_relative_path()
                ec_path = os.path.join(extract_dir, ec_rel)
                dut_access.CopyToDevice(self.new_ec, ec_path, mode='scp')

            if self.new_pd:
                # note: pd.bin might likewise need special path logic
                pd_path = os.path.join(extract_dir, 'pd.bin')
                dut_access.CopyToDevice(self.new_pd, pd_path, mode='scp')

    def run_case(self, append, write_protected, before_fwids, image_fwids):
        """Run chromeos-firmwareupdate with given sub-case

        @param append: additional piece to add to shellball name
        @param write_protected: is the flash write protected (--wp)?
        @param before_fwids: fwids before flashing ('bios' and 'ec' as keys)
        @param image_fwids: fwids in image ('bios' and 'ec' as keys)
        @return: a list of failure messages for the case
        """

        cmd_desc = ('chromeos-firmwareupdate --mode=%s [wp=%s]'
                    % (self.mode, write_protected))

        # Unlock the protection of the wp-enable and wp-range registers
        self.set_hardware_write_protect(False)

        if write_protected:
            self.faft_client.bios.set_write_protect_region(self.WP_REGION, True)
            self.set_hardware_write_protect(True)
        else:
            self.faft_client.bios.set_write_protect_region(
                    self.WP_REGION, False)

        expected_written = {}

        if write_protected:
            bios_written = ['a', 'b']
            ec_written = []  # EC write is all-or-nothing

        else:
            bios_written = ['ro', 'a', 'b']
            ec_written = ['ro', 'rw']

        expected_written['bios'] = bios_written

        if self.faft_config.chrome_ec and ec_written:
            expected_written['ec'] = ec_written

        # remove quotes and braces: bios: [a, b], ec: [ro, rw]
        written_desc = repr(expected_written).replace("'", "")[1:-1]
        logging.debug('Before(%s): %s', append, before_fwids)
        logging.debug('Image(%s):  %s', append, image_fwids)
        logging.info("Run %s (should write %s)", cmd_desc, written_desc)

        # make sure we restore firmware after the test, if it tried to flash.
        self.flashed = True

        errors = []
        options = ['--quirks=ec_partial_recovery=0']
        result = self.run_chromeos_firmwareupdate(
                self.mode, append, options, ignore_status=True)

        if result.exit_status == 255:
            logging.warn("DUT network dropped during update.")
        elif result.exit_status != 0:
            if (image_fwids == before_fwids and
                    'Good. It seems nothing was changed.' in result.stdout):
                logging.info("DUT already matched the image; updater aborted.")
            else:
                errors.append('...updater: unexpectedly failed (rc=%s)' %
                              result.exit_status)

        after_fwids = self.get_installed_versions()
        logging.debug('After(%s):  %s', append, after_fwids)

        errors += self.check_fwids_written(
                before_fwids, image_fwids, after_fwids, expected_written)

        if errors:
            logging.debug('%s', '\n'.join(errors))
            return ["%s: %s\n%s" % (cmd_desc, written_desc, '\n'.join(errors))]
        else:
            return []

    def run_once(self, host):
        """Run chromeos-firmwareupdate with recovery or factory mode.

        @param host: host to run on
        """
        append = 'new'
        have_ec = bool(self.faft_config.chrome_ec)

        self.faft_client.updater.extract_shellball()

        before_fwids = self.get_installed_versions()

        # Use new images as-is
        logging.info(
                "Using specified image(s):"
                "new_bios=%s, new_ec=%s, new_pd=%s",
                self.new_bios, self.new_ec, self.new_pd)
        self.copy_cmdline_images(host.hostname)
        self.faft_client.updater.reload_images()
        self.faft_client.updater.repack_shellball(append)
        modded_fwids = self.identify_shellball(include_ec=have_ec)

        fail_msg = "Section contents didn't show the expected changes."

        errors = []
        if self.wp is not None:
            # try only the specified wp= value
            errors += self.run_case(append, self.wp, before_fwids, modded_fwids)

        elif self.mode == 'factory':
            # apply images with wp=0 by default
            errors += self.run_case(append, 0, before_fwids, modded_fwids)

        else:
            # no args specified, so check both wp=1 and wp=0
            errors += self.run_case(append, 1, before_fwids, modded_fwids)
            errors += self.run_case(append, 0, before_fwids, modded_fwids)

        if errors:
            raise error.TestFail("%s\n%s" % (fail_msg, '\n'.join(errors)))

    def cleanup(self):
        """Reboot the EC to apply the update."""

        if self.flashed:
            self.sync_and_ec_reboot('hard')

        # Restore the old write-protection value at the end of the test.
        self.faft_client.bios.set_write_protect_range(
                self._old_bios_wp['start'],
                self._old_bios_wp['length'],
                self._old_bios_wp['enabled'])

        super(firmware_FWupdate, self).cleanup()
