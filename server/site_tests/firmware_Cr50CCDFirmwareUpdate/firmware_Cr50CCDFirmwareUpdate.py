# Copyright 2020 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.


"""The autotest performing FW update, both EC and AP in CCD mode."""


from autotest_lib.client.common_lib import error
from autotest_lib.server.cros.faft.cr50_test import Cr50Test

class firmware_Cr50CCDFirmwareUpdate(Cr50Test):
    """A test that can provision a machine to the correct firmware version."""

    version = 1

    def initialize(self, host, cmdline_args, full_args):
        """Initialize the test and check if cr50 exists.

        Raises:
            TestNAError: If the dut is not proper for this test for its RDD
                         recognition problem.
        """
        super(firmware_Cr50CCDFirmwareUpdate,
              self).initialize(host, cmdline_args, full_args)

        servo_type = self.servo.get_servo_version()
        if 'ccd_cr50' not in servo_type:
            raise error.TestNAError('unsupported servo type: %s' % servo_type)

    def run_once(self, host, rw_only=False):
        """The method called by the control file to start the test.

        Args:
          host:  a CrosHost object of the machine to update.
          rw_only: True to only update the RW firmware.

        Raises:
          TestFail: if the firmware version remains unchanged.
          TestError: if the latest firmware release cannot be located.
          TestNAError: if the test environment is not properly set.
                       e.g. the servo type doesn't support this test.
        """

        # Get the parent (a.k.a. referebce board or baseboard), and hand it
        # to get_latest_release_version so that it
        # can use it in search as secondary candidate. For example, bob doesn't
        # have its own release directory, but its parent, gru does.
        parent = getattr(self.faft_config, 'parent', None)

        value = host.get_latest_release_version(self.faft_config.platform,
                                                parent)
        if not value:
            raise error.TestError('Cannot locate the latest release for %s',
                                  self.faft_config.platform)

        # Fast open cr50 and check if testlab is enabled.
        self.fast_open(enable_testlab=True)
        if self.servo.has_control('active_v4_device'):
            try:
                self.servo.set('active_v4_device', 'ccd_cr50')
            except error.TestFail as e:
                raise error.TestNAError('cannot change active_v4_device: %s' %
                                        str(e))

        host.firmware_install(build=value, rw_only=rw_only,
                              dest=self.resultsdir, verify_version=True)
