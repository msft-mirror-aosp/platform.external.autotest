# Copyright 2022 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import logging
import random

from autotest_lib.client.common_lib import error
from autotest_lib.server.cros.faft.cr50_test import Cr50Test


class firmware_Cr50Counter(Cr50Test):
    """Verify orderly counters."""
    version = 1

    CLEAR_TPM_OWNER = 'crossystem clear_tpm_owner_request=1'
    TPM_MANAGERD_CONF = '/etc/init/tpm_managerd.conf'
    TRUNKSD_CONF = '/etc/init/trunksd.conf'
    # Comment out the start line in tpm_managerd to prevent it from running.
    # Inject a string that won't be in any start scripts, so it's easy to
    # remove.
    COMMENT_BLOCK = '#faft_cr50_block_t3st '
    START_SERVICE = 'start on'
    BLOCK_SERVICE_CMD = "sed 's/^%s/%s/g' -i " % (
            START_SERVICE, COMMENT_BLOCK + START_SERVICE)
    RESTORE_SERVICE_CMD = "sed 's/^%s//g' -i " % COMMENT_BLOCK

    # Spaces used to create the two counters
    COUNTER_START = 3003
    # The max is a lot less. It should be around 8.
    MAXIMUM_COUNTERS = 20
    RAND_MIN = 0
    RAND_MAX = 100
    # ORDERLY + COUNTER + AUTHREAD + AUTHWRITE
    ATTR = '4040014'
    COUNTER_SIZE = 8
    # tpmc raw. Supply the COUNTER twice.
    # format the counter string 'COUNTER[2:] COUNTER[:2]'
    TPMC_INC = ('tpmc raw 80 02 00 00 00 1f 00 00 01 34 01 00 %s 01 '
                '00 %s 00 00 00 09 40 00 00 09 00 00 00 00 00')
    # Run a for loop on the dut to increment the counter instead of sshing
    # into the dut every time.
    ERR_INC = 'inc_failure'
    RUN_INCREMENT = ("for i in {1..%d}; do echo $i; " + TPMC_INC +
                     " && continue; echo " + ERR_INC + " $i ; break; done")
    # tpmc def COUNTER COUNTER_SIZE COUNTER_ATTR
    TPMC_DEF = 'tpmc def %d %d %s'
    # tpmc read COUNTER COUNTER_SIZE
    TPMC_READ = 'tpmc read %d %d'

    ERR_UNINIT = '0x18b'
    ERR_INSUFFICIENT_SPACE = '0x14b'

    def initialize(self, host, cmdline_args, full_args):
        """Initialize firmware_Cr50Counter."""
        # The test needs to restore the cr50 image during cleanup.
        super(firmware_Cr50Counter,
              self).initialize(host,
                               cmdline_args,
                               full_args)
        self.added_counters = 0
        self.inc_logs = {}

    def def_counter(self, counter):
        """Create a counter, increment it once, and return the value."""
        # Verify the space doesn't already exist.
        if self.read_counter(counter) != None:
            raise error.TestFail('%r already defined.' % counter)
        logging.info('Creating %s', counter)
        def_cmd = self.TPMC_DEF % (counter, self.COUNTER_SIZE, self.ATTR)
        result = self.host.run(def_cmd, ignore_status=True)
        if self.ERR_INSUFFICIENT_SPACE in result.stderr:
            return self.ERR_INSUFFICIENT_SPACE
        if result.exit_status:
            raise error.TestFail('Unable to create %r counter: %r' %
                                 (counter, result))
        self.increment_counter(counter, 1)
        logging.info('Created %s', counter)
        return self.read_counter(counter)

    def read_counter(self, counter):
        """Get the int value from the counter or None if uninitialized."""
        read_cmd = 'tpmc read %s %s' % (counter, self.COUNTER_SIZE)
        result = self.host.run(read_cmd, ignore_status=True)
        # Counter is uninitialized.
        if self.ERR_UNINIT in result.stderr:
            return None
        if result.exit_status:
            raise error.TestError('Unexpected counter read error: %r' % result)
        val = 0
        logging.info('Res: %s', result.stdout.strip())
        for i, s in enumerate(result.stdout.strip().split()):
            val = val << 8 | int(s, 16)
        logging.info('%s val: %s', counter, val)
        return val

    def increment_counter(self, counter, increment):
        """Increment the counter"""
        counter_str = str(counter)
        if not isinstance(counter_str, str) or len(counter_str) != 4:
            raise error.TestError('Invalid counter %r. Must be string with '
                                  'length 4.')
        # Format the counter for the increment command
        spaced_counter = '%s %s' % (counter_str[:2], counter_str[2:])
        increment_cmd = self.RUN_INCREMENT % (increment, spaced_counter,
                                              spaced_counter)
        logging.debug('Incrementing counter %r', increment_cmd)
        result = self.host.run(increment_cmd)
        logging.debug('%d increment %s: %r', increment, counter, result)
        self.inc_logs[counter] = '%r\n%r' % (increment_cmd, result)
        if self.ERR_INC in result.stdout:
            raise error.TestFail("Increment error %s: %r" % (counter, result))

    def add_test_counter(self, increment):
        """Create a counter and store the info in counter_info.

        Returns
            True if the counter was successfully created.
        """
        counter = self.COUNTER_START + self.added_counters
        self.added_counters += 1
        val = self.def_counter(counter)
        if val == self.ERR_INSUFFICIENT_SPACE:
            logging.info("Insufficient space creating the counter %s", counter)
            return False
        increment = increment or random.randint(self.RAND_MIN, self.RAND_MAX)
        self.counter_info.append((counter, val, increment))
        return True

    def block_service(self, service):
        """Inject a string to prevent the service from starting on reboot."""
        logging.info('Block %s', service)
        self.host.run(self.BLOCK_SERVICE_CMD + service)
        new_line = self.host.run('grep "%s" %s' %
                                 (self.START_SERVICE, service)).stdout
        logging.info('Modified %s %r', service, new_line)

    def restore_service(self, service):
        """Remove the string the test used to stop the service from starting."""
        logging.info('Restoring %s', service)
        self.host.run(self.RESTORE_SERVICE_CMD + service)
        new_line = self.host.run('grep "%s" %s' %
                                 (self.START_SERVICE, service)).stdout
        logging.info('Modified %s %r', service, new_line)

    def restore_tpm_services(self):
        """Copy the original tpm_mangerd.conf file back to the dut."""
        result = self.host.run('grep %r /etc/init/*' % self.COMMENT_BLOCK,
                               ignore_status=True)
        if result.exit_status == 1:
            return
        logging.info("Restoring %r", result.stdout)
        self.make_rootfs_writeable()
        self.restore_service(self.TRUNKSD_CONF)
        self.restore_service(self.TPM_MANAGERD_CONF)
        self.host.run('sync')
        logging.info('Restored tpm_managerd and trunksd')
        self.host.reboot()

    def block_tpm_services(self):
        """Modify tpm_managerd and trunksd so they don't start on reboot."""
        self.make_rootfs_writeable()
        logging.info('Replace start line in tpm_managerd and trunksd')
        self.block_service(self.TRUNKSD_CONF)
        self.block_service(self.TPM_MANAGERD_CONF)
        self.host.run('sync')

    # Try to copy tpm_managerd back to the dut after run once and during cleanup
    # to give the test the best chance of restoring it.
    def after_run_once(self):
        """Restore tpm_managerd after running the test."""
        super(firmware_Cr50Counter, self).after_run_once()
        self.restore_tpm_services()

    def cleanup(self):
        """Restore tpm_managerd after running the test."""
        try:
            self.restore_tpm_services()
            # Clear the tpm owner to remove the counters the test created.
            self.host.run(self.CLEAR_TPM_OWNER)
            self.host.reboot()
        finally:
            super(firmware_Cr50Counter, self).cleanup()

    def run_once(self, host):
        """Verify orderly counters."""
        # Remove tpm_managerd, so the test can run tpmc commands.
        self.block_tpm_services()

        # Run the commands to clear the tpm owner. ClearTPMOwnerRequest won't
        # work correctly, because it can't get the tpm status without
        # tpm_managerd running.
        self.host.run(self.CLEAR_TPM_OWNER)
        self.host.reboot()

        self.counter_info = []

        # Create the counters.
        self.add_test_counter(256)
        for i in range(self.MAXIMUM_COUNTERS):
            if not self.add_test_counter(None):
                break
        logging.info("Counter info %r", self.counter_info)

        # Increment all of the counters.
        for counter, val, increment in self.counter_info:
            logging.info('Incrementing %r by %d. start val: %d', counter,
                         increment, val)
            self.increment_counter(counter, increment)

        # Verify the counters match the expected value.
        for i, info in enumerate(self.counter_info):
            counter, val, increment = info
            exp = val + increment
            act = self.read_counter(counter)
            logging.info('Counter counter %s : act %d exp %d', counter, act,
                         exp)
            if exp != act:
                logging.info('Failed increment %r: %s', counter,
                             self.inc_logs[counter])
                raise error.TestFail(
                        'Error in counter %d %s: exp %d act %d' %
                        (i, counter, exp, act))
