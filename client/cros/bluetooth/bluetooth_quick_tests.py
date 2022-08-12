# Lint as: python3
# Copyright 2022 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Wrapper functions for client Bluetooth quick test"""

import time

import functools
import logging
import os
from autotest_lib.client.bin import test
from autotest_lib.client.bin import utils
from autotest_lib.client.common_lib import error
from autotest_lib.client.common_lib.cros.bluetooth import (
        bluetooth_quick_tests_base)
from autotest_lib.client.cros.multimedia import bluetooth_facade


class BluetoothQuickTests(test.test,
                          bluetooth_quick_tests_base.BluetoothQuickTestsBase):
    """Provides helper functions for client Bluetooth quick test"""
    version = 1
    # Path for btmon logs
    BTMON_DIR_LOG_PATH = '/var/log/btmon'

    # Path for usbmon logs
    USBMON_DIR_LOG_PATH = '/var/log/usbmon'

    # Parameters for usbmon log rotation
    USBMON_SINGLE_FILE_MAX_SIZE = '10M'  # 10M bytes
    USBMON_NUM_OF_ROTATE_FILE = 2

    def quick_test_init(self, flag='Quick Health'):
        """Initializes Bluetooth facade, BTMON and USBMON."""
        super().quick_test_init(flag=flag)
        # Run through every tests and collect failed tests in self.fails.
        self.fails = []

        # If a test depends on multiple conditions, write the results of
        # the conditions in self.results so that it is easy to know
        # what conditions failed by looking at the log.
        self.results = None

        # If any known failures were seen in the logs at any time during this
        # test execution, we capture that here. This includes daemon crashes,
        # usb disconnects or any of the other known common failure reasons
        self.had_known_common_failure = False

        # Init bluetooth facade
        self.bluetooth_facade = bluetooth_facade.BluezFacadeLocal()

        # Make sure adapter is available
        if not self.bluetooth_facade.has_adapter():
            raise error.TestNAError('Adapter is missing')

        self.enable_disable_debug_log(enable=True)

        # Disable cellular services, as they can sometimes interfere with
        # suspend/resume, i.e. b/161920740
        self.enable_disable_cellular(enable=False)

        self.enable_disable_ui(enable=False)

        # Delete files created in previous run
        utils.run('[ ! -d {0} ] || rm -rf {0} || true'.format(
                self.BTMON_DIR_LOG_PATH))
        utils.run('[ ! -d {0} ] || rm -rf {0} || true'.format(
                self.USBMON_DIR_LOG_PATH))

        self.dut_btmon_log_path = self.start_new_btmon()
        self.start_new_usbmon()
        self.common_failures = {
                'Freeing adapter /org/bluez/hci': 'adapter_freed',
                '/var/spool/crash/bluetoothd': 'bluetoothd_crashed',
                'btintel_hw_error': 'intel hardware error detected',
                'qca_hw_error': 'qca hardware error detected',
                'cmd_cnt 0 cmd queued ([5-9]|[1-9][0-9]+)':
                'controller cmd capacity',
        }

        self.identify_platform_failure_reasons()

    def enable_disable_cellular(self, enable):
        """Enable cellular services on the DUT.

        @param enable: True to enable cellular services,
                       False to disable cellular services.

        @returns: True if services were set successfully, else False.
        """
        cellular_services = ['modemmanager', 'modemfwd']

        return self.enable_disable_services(cellular_services, enable)

    def enable_disable_ui(self, enable):
        """Enable UI service on the DUT.

        @param enable: True to enable UI services,
                       False to disable UI services.

        @returns: True if services were set successfully, else False.
        """
        ui_services = ['ui']

        return self.enable_disable_services(ui_services, enable)

    def enable_disable_debug_log(self, enable):
        """Enable or disable debug log in DUT.
        @param enable: True to enable all the debug log,
                       False to disable all of the debug log.
        """
        level = int(enable)
        self.bluetooth_facade.set_debug_log_levels(level, level)

    def enable_disable_services(self, services, enable):
        """Enable or disable service on the DUT.

        @param services: list of string service names.
        @param enable: True to enable services, False to disable.

        @returns: True if services were set successfully, else False.
        """
        command = 'start' if enable else 'stop'
        return self._initctl_services(services, command)

    def _initctl_services(self, services, command):
        """Use initctl to control service on the DUT.

        @param services: list of string service names.
        @param command: initctl command on the services
                        'start': to start the service
                        'stop': to stop the service
                        'restart': to restart the service.

        @returns: True if services were set successfully, else False.
        """
        for service in services:
            # Some platforms will not support all services. In these cases,
            # no need to fail, since they won't interfere with our tests
            if not self.service_exists(service):
                logging.debug('Service %s does not exist on DUT', service)
                continue

            # A sample call to enable or disable a service is as follows:
            # "initctl stop modemfwd"
            if command in ['start', 'stop']:
                enable = command == 'start'
                if self.service_enabled(service) != enable:
                    utils.run('initctl {} {}'.format(command, service))

                    if self.service_enabled(service) != enable:
                        logging.error('Failed to %s service %s', command,
                                      service)
                        return False

                if enable:
                    logging.info('Service {} enabled'.format(service))
                else:
                    logging.info('Service {} disabled'.format(service))

            elif command == 'restart':
                if self.service_enabled(service):
                    utils.run('initctl {} {}'.format(command, service))
                else:
                    # Just start a stopped job.
                    utils.run('initctl {} {}'.format('start', service))
                logging.info('Service {} restarted'.format(service))

            else:
                logging.error('unknown command {} on services {}'.format(
                        command, services))
                return False

        return True

    def service_exists(self, service_name):
        """Checks if a service exists on the DUT.

        @param service_name: name of the service.

        @returns: True if service status can be queried, else False.
        """

        status_cmd = 'initctl status {}'.format(service_name)
        try:
            # Querying the status of a non-existent service throws an
            # CmdError exception.  If no exception is thrown, we know
            # the service exists.
            utils.run(status_cmd)

        except error.CmdError:
            return False

        return True

    def service_enabled(self, service_name):
        """Checks if a service is running on the DUT.

        @param service_name: name of the service.

        @throws: AutoservRunError is thrown if there is no service with the
                 provided name installed on the DUT.

        @returns: True if service is currently running, else False.
        """

        status_cmd = 'initctl status {}'.format(service_name)
        output = utils.run(status_cmd).stdout

        return 'start/running' in output

    def start_new_btmon(self):
        """Starts a new btmon process and saves the log."""

        # Kill all btmon process before creating a new one.
        utils.run('pkill btmon || true')

        # Make sure the directory exists.
        utils.run('mkdir -p %s' % self.BTMON_DIR_LOG_PATH)

        # Time format. Ex, 2020_02_20_17_52_45.
        now = time.strftime("%Y_%m_%d_%H_%M_%S")
        file_name = 'btsnoop_%s' % now

        path = os.path.join(self.BTMON_DIR_LOG_PATH, file_name)
        utils.BgJob('btmon -SAw %s' % path)
        return path

    def start_new_usbmon(self, reboot=False):
        """Starts a new USBMON process and saves the log.

        @param reboot: True to indicate we are starting new usbmon on reboot
                       False otherwise.
        """

        # Kill all usbmon process before creating a new one.
        utils.run('pkill tcpdump || true')

        # Delete usbmon logs from previous tests unless we are starting another.
        # usbmon because of reboot.
        if not reboot:
            utils.run('rm -f %s/*' % (self.USBMON_DIR_LOG_PATH))

        # Make sure the directory exists.
        utils.run('mkdir -p %s' % self.USBMON_DIR_LOG_PATH)

        # Time format. Ex, 2022_05_20_17_52_45
        now = time.strftime("%Y_%m_%d_%H_%M_%S")
        file_name = 'usbmon_%s' % now
        utils.BgJob('tcpdump -i usbmon0 -w %s/%s -C %s -W %d' %
                    (self.USBMON_DIR_LOG_PATH, file_name,
                     self.USBMON_SINGLE_FILE_MAX_SIZE,
                     self.USBMON_NUM_OF_ROTATE_FILE))

    def identify_platform_failure_reasons(self):
        """Identifies platform failure reasons to watch for in logs."""
        s = self.bluetooth_facade.get_bt_usb_disconnect_str()
        if s:
            self.common_failures[s] = 'USB disconnect detected'

    def _flag_common_failures(self):
        """Checks if a common failure has occurred during the test run

        Scans system logs for known signs of failure. If a failure is
        discovered, it is added to the test results, to make it easier to
        identify common root causes from Stainless
        """
        had_failure = False

        for fail_tag, fail_log in self.common_failures.items():
            if self.bluetooth_facade.messages_find(fail_tag):
                had_failure = True
                logging.error('Detected failure tag: %s', fail_tag)
                # We mark this instance's results with the discovered failure
                if type(self.results) is dict:
                    self.results[fail_log] = True

        return had_failure

    def cleanup(self):
        """Cleans up any state of the client test."""

        # Reset the adapter.
        self.bluetooth_facade.reset_on()

        self.enable_disable_debug_log(enable=False)

        self.enable_disable_cellular(enable=True)

        self.enable_disable_ui(enable=True)

        # Stop btmon process.
        utils.run('pkill btmon || true')
        # Stop tcpdump usbmon process.
        utils.run('pkill tcpdump || true')

    def quick_test_test_decorator(test_name,
                                  flags=None,
                                  model_testNA=None,
                                  model_testWarn=None,
                                  skip_models=None,
                                  skip_chipsets=None,
                                  skip_common_errors=False):
        """A decorator providing a wrapper to a quick test.

        Using the decorator a test method can implement only the core
        test and let the decorator handle the quick test wrapper methods
        (reset/cleanup/logging).

        @param test_name: The name of the test to log.
        @param flags: List of string to describe who should run the test. The
                      string could be one of the following:
                          ['AVL', 'Quick Health', 'All'].
        @param model_testNA: If the current platform is in this list, failures
                             are emitted as TestNAError.
        @param model_testWarn: If the current platform is in this list, failures
                               are emitted as TestWarn.
        @param skip_models: Raises TestNA on these models and doesn't attempt to
                            run the tests.
        @param skip_chipsets: Raises TestNA on these chipset and doesn't attempt
                              to run the tests.
        @param skip_common_errors: If the test encounters a common error (such
                                   as USB disconnect or daemon crash), mark the
                                   test as TESTNA instead. USE THIS SPARINGLY,
                                   it may mask bugs. This is available for tests
                                   that require state to be properly retained
                                   throughout the whole test (i.e. advertising)
                                   and any outside failure will cause the test
                                   to fail.
        """

        if flags is None:
            flags = ['All']
        base_class = bluetooth_quick_tests_base.BluetoothQuickTestsBase
        return base_class.quick_test_test_decorator(
                test_name,
                flags=flags,
                pretest_func=lambda self: self.pretest_function(),
                posttest_func=lambda self: self.bluetooth_facade.reset_on(),
                model_testNA=model_testNA,
                model_testWarn=model_testWarn,
                skip_models=skip_models,
                skip_chipsets=skip_chipsets,
                skip_common_errors=skip_common_errors)

    def pretest_function(self):
        """Runs before each test."""
        if not self.bluetooth_facade.has_adapter():
            raise error.TestNAError('Adapter is missing')

        self.bluetooth_facade.reset_on()
        time.sleep(self.TEST_SLEEP_SECS)

    @staticmethod
    def test_log_result(test_method=None,
                        messages_start=True,
                        messages_stop=True):
        """A decorator that logs test results and collects error messages.

        @param messages_start: Start collecting messages before running the test
        @param messages_stop: Stop collecting messages after running the test
                and analyze the results.

        @returns: a wrapper of the test_method with test log.

        """

        def decorator(test_method):
            """A decorator wrapper of the decorated test_method.

            @param test_method: the test method being decorated.

            @returns the wrapper of the test method.

            """

            @functools.wraps(test_method)
            def wrapper(self, *args, **kwargs):
                """A wrapper of the decorated method.

                @returns the result of the test method.

                """
                self.results = {}

                logging.info('[>>> running: {}]'.format(test_method.__name__))
                start_time = time.time()
                if messages_start:
                    # Grab /var/log/messages output during test run
                    self.bluetooth_facade.messages_start()

                test_result = test_method(self, *args, **kwargs)
                syslog_captured = False
                if messages_stop:
                    syslog_captured = self.bluetooth_facade.messages_stop()

                if syslog_captured:
                    had_failure = self._flag_common_failures()
                    self.had_known_common_failure = any(
                            [self.had_known_common_failure, had_failure])

                elapsed_time = 'elapsed_time: {:.3f}s'.format(time.time() -
                                                              start_time)
                if test_result:
                    logging.info('[*** passed: {} ({})] {}'.format(
                            test_method.__name__, str(self.results),
                            elapsed_time))
                else:
                    fail_msg = '[--- failed: {} ({})]'.format(
                            test_method.__name__, str(self.results))
                    logging.error('{} {}'.format(fail_msg, elapsed_time))
                    self.fails.append(fail_msg)

                return test_result

            return wrapper

        if test_method is not None:
            # If the decorator function comes with no argument like
            # @test_log_result
            return decorator(test_method)
        else:
            # If the decorator function comes with arguments like
            # @test_log_result(messages_start=False, messages_stop=False)
            return decorator

    @staticmethod
    def test_case_log(method):
        """A decorator for test case methods.

        The main purpose of this decorator is to display the test case name
        in the test log which looks like

            <... test_case_RA3_CD_SI200_CD_PC_CD_UA3 ...>

        @param method: the test case method to decorate.

        @returns: a wrapper function of the decorated method.

        """

        @functools.wraps(method)
        def wrapper(instance, *args, **kwargs):
            """Logs the name of the wrapped method before execution."""
            logging.info('\n<... %s ...>', method.__name__)
            method(instance, *args, **kwargs)

        return wrapper

    def quick_test_get_model_name(self):
        """Returns the model name.

        Needed by BluetoothQuickTestsBase.quick_test_test_decorator.
        """
        return utils.get_platform()

    def quick_test_get_chipset_name(self):
        """Returns the chipset name.

        Needed by BluetoothQuickTestsBase.quick_test_test_decorator.
        """
        return self.bluetooth_facade.get_chipset_name()
