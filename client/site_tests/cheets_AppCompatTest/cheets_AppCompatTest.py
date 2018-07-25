# Copyright 2018 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import logging
import os
import time

from autotest_lib.client.bin import utils
from autotest_lib.client.common_lib import error
from autotest_lib.client.common_lib.cros import arc


class cheets_AppCompatTest(arc.ArcTest):
    """
    Autotest wrapper class for the AppCompat's team UIAutomator test cases.

    It is used to call the apk that runs the test. It then copies logcat,
    bugreport and screenshots to the autotest resultsdir.

    It parses logcat to get the test results.

    """
    version = 1

    _PLAY_STORE_ACTIVITY = 'com.android.vending'
    _TEST_FILES_LOCATION = ('https://storage.googleapis.com/chromeos-throw'
                            '-away-bucket/app_compat/')
    _TEST_FILES = ['app-debug.apk', 'app-debug-androidTest.apk',
                   'autresources.xml']
    _TMP_LOCATION = '/tmp/app_compat/'
    _LOG_TAG = '~APPCOM_TEST_AUTO~'


    def initialize(self, pkg_name, touch_view_mode):
        self._pkg_name = pkg_name
        browser_args = None
        self._touch_view_mode = touch_view_mode
        if self._touch_view_mode:
            browser_args = ['--force-tablet-mode=touch_view']

        super(cheets_AppCompatTest, self).initialize(
            disable_arc_opt_in=False, extra_browser_args=browser_args,
            username='crosarcappcompat@gmail.com',
            password='appcompatautotest')


    def arc_setup(self):
        super(cheets_AppCompatTest, self).arc_setup()


    def cleanup(self):
        arc.adb_cmd('uninstall com.hcl.actframework')
        arc.adb_cmd('uninstall com.hcl.actframework.test')
        arc.adb_cmd('uninstall %s' % self._pkg_name)
        arc.adb_shell('rm -f /sdcard/autresources.xml > /dev/null')
        arc.adb_shell('rm -f /sdcard/touchView.txt > /dev/null',
                      ignore_status=True)
        utils.run('rm -rf %s' % self._TMP_LOCATION)
        super(cheets_AppCompatTest, self).cleanup()


    def _grant_storage_permission(self):
        """Grant the UIAutomator tests storage permission."""
        arc.adb_shell('am instrument -w -r -e debug false -e '
                      '"grant_permissions_only" "Y" '
                      'com.hcl.actframework.test/android.support.test.runner'
                      '.AndroidJUnitRunner')

    def _start_test(self):
        """Kick off the UIAutomator tests."""
        arc.adb_shell('am instrument -w -r -e debug false -e '
                      '"device_model" "Google~Pixelbook" -e '
                      '"app_packagename" %s -e "app_version" "TBD" -e '
                      '"device_os_build_version" 7.1.1 -e '
                      '"clear_recents" "N" -e "check_wifi_connection" '
                      '"N" -e "check_location_on" "N" -e '
                      '"check_auto_rotate_off" "N" '
                      'com.hcl.actframework.test/android.support.test'
                      '.runner.AndroidJUnitRunner' % self._pkg_name)


    def _copy_resources_to_dut(self):
        """Copy the apks & xml file needed for the UIAutomator tests."""
        if not os.path.exists(self._TMP_LOCATION):
            os.mkdir(self._TMP_LOCATION)
        for test_file in self._TEST_FILES:
            uri = self._TEST_FILES_LOCATION + test_file
            utils.run('wget -O %s %s' % (os.path.join(self._TMP_LOCATION,
                                                      test_file), uri))

        for test_file in os.listdir(self._TMP_LOCATION):
            if test_file == 'app-debug.apk':
                arc.adb_cmd('push %s /data/local/tmp/com.hcl.actframework' %
                            os.path.join(self._TMP_LOCATION, test_file))
                arc.adb_shell('pm install -t -r '
                              '"/data/local/tmp/com.hcl.actframework"')
            elif test_file == 'app-debug-androidTest.apk':
                arc.adb_cmd('push %s '
                            '/data/local/tmp/com.hcl.actframework.test' %
                            os.path.join(self._TMP_LOCATION, test_file))
                arc.adb_shell('pm install -t -r '
                              '"/data/local/tmp/com.hcl.actframework.test"')
            else:
                arc.adb_cmd('push %s /sdcard/' % os.path.join(
                            self._TMP_LOCATION, test_file))
        if self._touch_view_mode:
            arc.adb_shell('touch /sdcard/touchView.txt')


    def _capture_bugreport(self):
        """Captures a bugreport and saves into resultsdir."""
        arc.adb_cmd('bugreport > %s' % os.path.join(self.resultsdir,
                                                    'bugreport.txt'))


    def _grab_screenshots(self):
        """Captures screenshots that are created by the UIAutomator tests."""
        for screenshot in arc.adb_shell('find /sdcard/*.png').splitlines():
            logging.debug('Screenshot is %s.', screenshot)
            arc.adb_cmd('pull %s %s' % (screenshot, self.resultsdir),
                        ignore_status=True)
            arc.adb_shell('rm -r %s' % screenshot, ignore_status=True)


    def _save_logcat(self):
        """Saves the logcat for the test run to the resultsdir."""
        arc.adb_cmd('logcat -d > %s' % os.path.join(self.resultsdir,
                                                    'logcat.txt'))


    def _parse_results(self):
        """Parse the pass/fail/skipped entries from logcat. """
        passed = self._get_log_entry_count(",PASS,")
        failed = self._get_log_entry_count(",FAIL,")
        nt = self._get_log_entry_count(",NT,")
        blocked = self._get_log_entry_count(",BLOCKED,")
        skipped = self._get_log_entry_count(",SKIPPED,")
        ft = self._get_failed_test_cases()

        result = ('Test results for %s(%s): Passed %s, Failed %s, Not Tested '
                  '%s, Blocked %s, Skipped %s. Failed tests: [%s]' % (
                  self._pkg_name, self._app_version, passed, failed, nt,
                  blocked, skipped, ft))
        logging.info(result)
        if int(failed) > 0:
            raise error.TestFail(result)


    def _get_log_entry_count(self, entry):
        """Get the total number of times a string appears in logcat."""
        logcat = os.path.join(self.resultsdir, 'logcat.txt')
        return utils.run('grep "%s" %s | grep -c "%s"' %
                        (self._LOG_TAG, logcat, entry),
                         ignore_status=True).stdout.strip()


    def _get_failed_test_cases(self):
        """Get the list of test cases that failed from logcat."""
        logcat = os.path.join(self.resultsdir, 'logcat.txt')
        failed_tests = []
        failed_tests_list = utils.run('grep "%s" %s | grep ",FAIL,"' %
                            (self._LOG_TAG, logcat),
                            ignore_status=True).stdout.strip().splitlines()
        for line in failed_tests_list:
            failed_tests.append(line.split(',')[-4:])
        return failed_tests


    def _increase_logcat_buffer(self):
        """Increase logcat buffer so all UIAutomator test entries appear."""
        arc.adb_cmd('logcat -G 16M')


    def _wait_for_play_store_ready(self):
        """
        Wait for the Play Store to update.

        When you log into a device for the first time Play Store will
        sometimes restart itself to update if it is in the background. This
        brings it back to the front repeatedly.

        """
        count = 0
        while count < 30:
            arc.adb_shell('am start %s' % self._PLAY_STORE_ACTIVITY)
            time.sleep(1)
            count += 1


    def _get_app_version(self):
        """Grab the version of the application we are testing."""
        self._app_version = arc.adb_shell('dumpsys package %s | grep '
                                          'versionName| cut -d"=" -f2' %
                                          self._pkg_name)


    def run_once(self):
        self._increase_logcat_buffer()
        self._wait_for_play_store_ready()
        self._copy_resources_to_dut()
        self._grant_storage_permission()
        self._start_test()
        self._get_app_version()
        self._capture_bugreport()
        self._grab_screenshots()
        self._save_logcat()
        self._parse_results()
