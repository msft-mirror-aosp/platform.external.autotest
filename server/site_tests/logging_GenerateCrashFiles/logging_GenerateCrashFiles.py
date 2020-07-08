# Copyright 2016 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import logging
import time
import os

from autotest_lib.client.common_lib import error
from autotest_lib.client.cros.crash.crash_test import CrashTest
from autotest_lib.server import autotest, test


class logging_GenerateCrashFiles(test.test):
    """Tests if crash files are generated when crash is invoked."""
    version = 2
    SHORT_WAIT = 10
    SLEEP_FOR_CRASH_FILES = 30
    REBOOT_TIMEOUT = 60
    CRASH_DIR = CrashTest._SYSTEM_CRASH_DIR
    CHROME_CRASH_DIR = CrashTest._FALLBACK_USER_CRASH_DIR


    def check_missing_crash_files(self, expected_extensions, existing_files,
                                  prefix, location):
        """Find if the crash dumps with appropriate extensions are created.
        @param expected_extensions: matching crash file extensions.
        @param existing files: state of crash dir before induced crash.
        @param prefix: matching crash file prefix.
        @raises TestFail error if crash files are not generated.
        """
        crash_extensions = list()

        out = self.host.run('ls %s' % location, ignore_status=True)
        current_files = out.stdout.strip().split('\n')

        file_diff = set(current_files) - set(existing_files)
        logging.info("Crash files diff: %s" % file_diff)

        # Check empty files, prefix, and extension of crash files.
        for crash_file in file_diff:
            if crash_file.split('.')[0] != prefix:
                continue
            file_path = location + '/' + crash_file
            if '0' == self.host.run("du -h %s" % file_path).stdout[:1]:
                raise error.TestFail('Crash file is empty: %s' % crash_file)
            crash_extensions.append(crash_file.split('.')[-1])

        # Check for presence of all crash file extensions.
        extension_diff = set(expected_extensions) - set(crash_extensions)
        if len(extension_diff) > 0:
            raise error.TestFail('%s files not generated.' % extension_diff)

        # Remove existing file crash files, if any.
        for crash_file in file_diff:
            self.host.run('rm %s' % location + '/' + crash_file)

    def open_browser_crash_url(self, start_url):
        """ Logs in and Opens crash url in browser tab
        param@ start_url URL to induce the browser crash
        """
        autotest_client = autotest.Autotest(self.host)
        autotest_client.run_test('desktopui_SimpleLogin',
                                  start_url=start_url,
                                  exit_without_logout=True)


    def run_once(self, host, crash_cmd, crash_files, prefix):
        self.host = host

        # Sync the file system.
        self.host.run('sync', ignore_status=True)
        time.sleep(self.SHORT_WAIT)
        file_list = self.host.run('ls %s' % self.CRASH_DIR, ignore_status=True)
        existing_files = file_list.stdout.strip().split('\n')
        location = self.CRASH_DIR

        # Execute crash command.
        if (prefix == 'chrome'):
            logging.info("OPENING BROWSER for %s" % crash_cmd)
            self.open_browser_crash_url(crash_cmd)
            location = self.CHROME_CRASH_DIR
        else:
            boot_id = host.get_boot_id()
            self.host.run(crash_cmd, ignore_status=True,
                          timeout=30, ignore_timeout=True)
            logging.debug('Crash invoked!')

            # To check If the device has rebooted after kernel crash
            if(prefix == 'kernel'):
                host.ping_wait_down(self.SHORT_WAIT)
                # In case of kernel crash the reboot will take some time.
                host.ping_wait_up(self.REBOOT_TIMEOUT)
                if(boot_id == host.get_boot_id()):
                    raise error.TestFail('Device not rebooted')

        # Sync the file system.
        self.host.run('sync', ignore_status=True)
        time.sleep(self.SLEEP_FOR_CRASH_FILES)

        self.check_missing_crash_files(crash_files, existing_files,
                                       prefix, location)
