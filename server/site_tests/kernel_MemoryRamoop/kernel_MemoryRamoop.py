# Copyright (c) 2014 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import logging, random, re, string, traceback
from autotest_lib.client.common_lib import error
from autotest_lib.server import autotest
from autotest_lib.server import hosts
from autotest_lib.server import test

class kernel_MemoryRamoop(test.test):
    """
    This test verifies that /sys/fs/pstore/console-ramoops is preserved
    after system reboot/kernel crash and also verifies that there is no memory
    corruption in that log.

    There is also platform_KernelErrorPaths test that tests kernel crashes. But
    this test focuses on verifying that the kernel creates the console-ramoops
    file correctly and its content is not corrupt. Contrary to the other test
    that tests a bigger scope, i.e. the whole error reporting mechanism.
    """
    version = 1

    # The name of this file has changed starting with linux-3.19.
    # Use a glob to match all existing records.
    _RAMOOP_PATH_GLOB = '/sys/fs/pstore/console-ramoops*'
    _KMSG_PATH = '/dev/kmsg'
    _LKDTM_PATH = '/sys/kernel/debug/provoke-crash/DIRECT'

    # ramoops have a max size of 128K, so we will generate about 100K of random
    # messages.
    _MSG_LINE_COUNT = 1000
    _MSG_LINE_LENGTH = 80
    _MSG_MAGIC = 'ramoop_test'

    def run_once(self, client_ip):
        """
        Run the test.
        """
        if not client_ip:
            error.TestError("Must provide client's IP address to test")

        self._client = hosts.create_host(client_ip)
        self._client_at = autotest.Autotest(self._client)

        self._run_test(self._do_reboot, '.*Restarting system.*$')

        if self._client.check_for_lkdtm():
            self._run_test(self._do_kernel_panic, '.*lkdtm:.*PANIC$')
            self._run_test(self._do_kernel_bug, '.*lkdtm:.*BUG$')
        else:
            logging.warning('DUT did not have kernel dump test module')

        self._run_test(self._do_reboot_with_suspend, '.*Restarting system.*$')

    def _run_test(self, test_function, sig_pattern):
        """
        Run the test using by write random message to kernel log. Then
        restart/crash the kernel and then verify integrity of console-ramoop

        @param test_function: fuction to call to reboot / crash DUT
        @param sig_pattern: regex of kernel log message generate when reboot
                            or crash by test_function
        """

        msg = self._generate_random_msg()

        for line in msg:
            cmd = 'echo "%s" > %s' % (line, self._KMSG_PATH)
            self._client.run(cmd)

        test_function()

        cmd = 'cat %s' % self._RAMOOP_PATH_GLOB
        ramoop = self._client.run(cmd).stdout

        self._verify_random_msg(ramoop, msg, sig_pattern)

    def _do_reboot(self):
        """
        Reboot host machine
        """
        logging.info('Server: reboot client')
        try:
            self._client.reboot()
        except error.AutoservRebootError as err:
            raise error.TestFail('%s.\nTest failed with error %s' % (
                    traceback.format_exc(), str(err)))

    def _do_reboot_with_suspend(self):
        """
        Reboot host machine after suspend once
        """
        self._client.suspend(suspend_time=15)

        logging.info('Server: reboot client')
        try:
            self._client.reboot()
        except error.AutoservRebootError as err:
            raise error.TestFail('%s.\nTest failed with error %s' % (
                    traceback.format_exc(), str(err)))

    def _do_kernel_panic(self):
        """
        Cause kernel panic using kernel dump test module
        """
        logging.info('Server: make client kernel panic')

        cmd = 'echo PANIC > %s' % self._LKDTM_PATH
        boot_id = self._client.get_boot_id()
        self._client.run(cmd, ignore_status=True)
        self._client.wait_for_restart(old_boot_id=boot_id)

    def _do_kernel_bug(self):
        """
        Cause kernel bug using kernel dump test module
        """
        logging.info('Server: make client kernel bug')

        cmd = 'echo BUG > %s' % self._LKDTM_PATH
        boot_id = self._client.get_boot_id()
        self._client.run(cmd, ignore_status=True)
        self._client.wait_for_restart(old_boot_id=boot_id)

    def _generate_random_msg(self):
        """
        Generate random message to put in kernel log
        The message format is [magic string]: [3 digit id] [random char/digit]
        """
        valid_char = string.letters + string.digits
        ret = []
        for i in range(self._MSG_LINE_COUNT):
            line = '%s: %03d ' % (self._MSG_MAGIC, i)
            for _ in range(self._MSG_LINE_LENGTH):
                line += random.choice(valid_char)
            ret += [line]
        return ret

    def _verify_random_msg(self, ramoop, src_msg, sig_pattern):
        """
        Verify random message generated by _generate_random_msg

        There are 3 things to verify.
        1. At least one random message exist. (earlier random message may be
           cutoff because console-ramoops has limited size.
        2. Integrity of random message.
        3. Signature of reboot / kernel crash

        @param ramoop: console-ramoops file in DUT
        @param src_msg: message write to kernel log
        @param sig_patterm: regex of kernel log to verify
        """
        #                   time stamp     magic   id      random
        pattern = str("\\[ *(\\d+\\.\\d+)\\].*(%s: (\\d{3}) \\w{%d})" %
            (self._MSG_MAGIC, self._MSG_LINE_LENGTH))
        matcher = re.compile(pattern)

        logging.info('%s', pattern)

        state = 'find_rand_msg'

        last_timestamp = 0
        for line in ramoop.split('\n'):
            if state == 'find_rand_msg':
                if not matcher.match(line):
                    continue
                last_id = int(matcher.split(line)[3]) - 1
                state = 'match_rand_pattern'
                logging.info("%s: %s", state, line)

            if state == 'match_rand_pattern':
                if not matcher.match(line):
                    continue
                components = matcher.split(line)
                timestamp = float(components[1])
                msg = components[2]
                id = int(components[3])

                if timestamp < last_timestamp:
                    logging.info("last_timestamp: %f, timestamp: %d",
                                 last_timestamp, timestamp)
                    raise error.TestFail('Found reverse time stamp.')
                last_timestamp = timestamp

                if id != last_id + 1:
                    logging.info("last_id: %d, id: %d", last_id, id)
                    raise error.TestFail('Found missing message.')
                last_id = id

                if msg != src_msg[id]:
                    logging.info("cur_msg: '%s'", msg)
                    logging.info("src_msg: '%s'", src_msg[id])
                    raise error.TestFail('Found corrupt message.')

                if id == self._MSG_LINE_COUNT - 1:
                    state = 'find_signature'

            if state == 'find_signature':
                if re.match(sig_pattern, line):
                    logging.info("%s: %s", state, line)
                    break

        # error case: successful run must break in find_sigature state
        else:
            raise error.TestFail(str('Verify failed at state %s' % state))
