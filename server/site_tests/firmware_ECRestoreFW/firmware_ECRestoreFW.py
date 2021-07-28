# Copyright 2020 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.


"""The autotest performing FW update, both EC and AP in CCD mode."""
import logging

from autotest_lib.client.common_lib import error
from autotest_lib.server.cros.faft.firmware_test import FirmwareTest


class firmware_ECRestoreFW(FirmwareTest):
    """A test that restores a machine from an incrrect FW to backup."""

    version = 1

    def initialize(self, host, cmdline_args, full_args):
        """Initialize the test and pick a fake board to use for corruption. """
        super(firmware_ECRestoreFW, self).initialize(host, cmdline_args,
                                                   full_args)

        # Don't bother if there is no Chrome EC.
        if not self.check_ec_capability():
            raise error.TestNAError('Nothing needs to be tested on this device')

        self.backup_firmware()

    def cleanup(self):
        """The method called by the control file to start the test.

        Raises:
          TestFail: if the firmware restoration fails.
        """
        try:
            if self.is_firmware_saved():
                self.restore_firmware()
        except Exception as e:
            raise error.TestFail('FW Restoration failed: %s' % str(e))
        finally:
            super(firmware_ECRestoreFW, self).cleanup()

    def run_once(self, host):
        """The method called by the control file to start the test.

        Args:
          host:  a CrosHost object of the machine to update.
        """

        try:
            host.firmware_install(build="",
                                  dest=self.resultsdir,
                                  install_ec=True,
                                  install_bios=False)
        except error.TestError as e:
            # It failed before the test attempts to install firmware.
            # It could be either devserver timeout or servo device error.
            # Let this test fail in those cases.
            raise e
        except Exception as e:
            # Nothing can be guaranteed with the firmware corruption with wrong
            # firmware. Let's not this test fail for that.
            logging.info('Caught an exception: %s', e)
