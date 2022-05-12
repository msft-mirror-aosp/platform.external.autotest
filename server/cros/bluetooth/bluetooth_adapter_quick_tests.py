# Lint as: python2, python3
# Copyright 2019 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""
This class provides wrapper functions for Bluetooth quick health test
batches or packages
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import functools
import logging
import tempfile
import threading
import time

import common
from autotest_lib.client.common_lib import error
from autotest_lib.server import site_utils
from autotest_lib.server.cros.bluetooth import bluetooth_peer_update
from autotest_lib.server.cros.bluetooth import bluetooth_adapter_tests
from autotest_lib.server.cros.bluetooth import bluetooth_attenuator
from autotest_lib.server.cros.multimedia import remote_facade_factory
from autotest_lib.client.bin import utils
from six.moves import range

PROFILE_CONNECT_WAIT = 15
SUSPEND_SEC = 15
EXPECT_NO_WAKE_SUSPEND_SEC = 30
EXPECT_PEER_WAKE_SUSPEND_SEC = 60
EXPECT_PEER_WAKE_RESUME_BY = 30


class BluetoothAdapterQuickTests(bluetooth_adapter_tests.BluetoothAdapterTests):
    """This class provide wrapper function for Bluetooth quick health test
    batches or packages.
    The Bluetooth quick test infrastructure provides a way to quickly run a set
    of tests. As for today, auto-test ramp up time per test is about 90-120
    seconds, where a typical Bluetooth test may take ~30-60 seconds to run.

    The quick test infra, implemented in this class, saves this huge overhead
    by running only the minimal reset and cleanup operations required between
    each set of tests (takes a few seconds).

    This class provides wrapper functions to start and end a test, a batch or a
    package. A batch is defined as a set of tests, preferably with a common
    subject. A package is a set of batches.
    This class takes care of tests, batches, and packages test results, and
    prints out summaries to results. The class also resets and cleans up
    required states between tests, batches and packages.

    A batch can also run as a separate auto-test. There is a place holder to
    add a way to run a specific test of a batch autonomously.

    A batch can be implemented by inheriting from this class, and using its
    wrapper functions. A package can be implemented by inheriting from a set of
    batches.

    Adding a test to one of the batches is as easy as adding a method to the
    class of the batch.
    """

    # Some delay is needed between tests. TODO(yshavit): investigate and remove
    TEST_SLEEP_SECS = 3
    GCS_MTBF_BUCKET = 'gs://chromeos-mtbf-bt-results/'


    def restart_peers(self):
        """Restart and clear peer devices"""
        # Restart the link to device
        logging.info('Restarting peer devices...')

        # Grab current device list for initialization
        connected_devices = self.devices
        self.cleanup_bt_test(test_state='MID')

        for device_type, device_list in connected_devices.items():
            for device in device_list:
                if device is not None:
                    logging.info('Restarting %s', device_type)
                    self.get_device(device_type, on_start=False)


    def start_peers(self, devices):
        """Start peer devices"""
        # Start the link to devices
        if self.use_btpeer:
            logging.info('Starting peer devices...')
            self.get_device_rasp(devices)

            # Grab all the devices to verify RSSI
            devices = []
            for device_type, device_list in self.devices.items():
                # Skip bluetooth_tester since it won't be discoverable
                if 'TESTER' in device_type:
                    continue

                for device in device_list:
                    devices.append(device)
                    self.start_agent(device)

            if self.rssi_check:
                # Make sure device RSSI is sufficient
                self.verify_device_rssi(devices)
            else:
                logging.info('Skip RSSI check.')

    def _print_delimiter(self):
        logging.info('=======================================================')

    @staticmethod
    def _get_bool_arg(arg, args_dict, default_value):
        """Get the target bool argument from args_dict.

        @param arg: the target argument to query
        @param args_dict: the argument dictionary
        @param default_value: the default value of the argument
                if the arg is not in args_dict or
                if arg is neither 'true' nor 'false'

        @returns: the bool value of the target argument
        """
        if args_dict is not None and arg in args_dict:
            arg_value = args_dict[arg].lower()
            if arg_value == 'true':
                return True
            elif arg_value == 'false':
                return False
        return default_value

    @staticmethod
    def _get_clean_kernel_log_arguments(args_dict=None):
        """Parse the clean_kernel_log argument"""
        key = 'clean_kernel_log'
        if args_dict is not None and key in args_dict:
            return args_dict[key].upper()
        return 'DEBUG'

    def quick_test_init(self,
                        host,
                        use_btpeer=True,
                        flag='Quick Health',
                        args_dict=None,
                        start_browser=False,
                        floss=False):
        """Inits the test batch"""
        self.host = host
        self.start_browser = start_browser
        self.use_btpeer = use_btpeer
        self.floss = floss
        self.local_host_ip = None

        logging.debug('args_dict %s', args_dict)
        update_btpeers = self._get_bool_arg('update_btpeers', args_dict, True)
        self.rssi_check = self._get_bool_arg('rssi_check', args_dict, True)
        clean_log = self._get_clean_kernel_log_arguments(args_dict)
        btpeer_args = []
        if args_dict is not None:
            btpeer_args = self.host.get_btpeer_arguments(args_dict)
            ip_args = self.host.get_local_host_ip(args_dict)
            if ip_args:
                self.local_host_ip = ip_args['local_host_ip']

        #factory can not be declared as local variable, otherwise
        #factory._proxy.__del__ will be invoked, which shutdown the xmlrpc
        # server, which log out the user.

        self.factory = remote_facade_factory.RemoteFacadeFactory(
                host,
                no_chrome=not self.start_browser,
                disable_arc=True,
                force_python3=True)
        try:
            self.bluetooth_facade = self.factory.create_bluetooth_facade(
                    self.floss)
        except Exception as e:
            logging.error('Exception %s while creating bluetooth_facade',
                          str(e))
            raise error.TestFail('Unable to create bluetooth_facade')

        if clean_log is not 'FALSE':
            # Clean Bluetooth kernel logs in the DUT to prevent
            # /var/log/messages occupying too much space
            self.clean_bluetooth_kernel_log(clean_log)

        # Some test beds has a attenuator for Bluetooth. If Bluetooth
        # attenuator is present, set its attenuation to 0
        self.bt_attenuator = bluetooth_attenuator.init_btattenuator(
                self.host, args_dict)

        logging.debug("Bluetooth attenuator is %s", self.bt_attenuator)

        # Check whether this device supports floss
        if self.floss:
            self.check_floss_support()

        if self.use_btpeer:
            self.input_facade = self.factory.create_input_facade()

            self.host.initialize_btpeer(btpeer_args=btpeer_args)
            logging.info('%s Bluetooth peers found',
                         len(self.host.btpeer_list))
            logging.info('labels: %s', self.host.get_labels())

            if len(self.host.btpeer_list) == 0:
                raise error.TestFail('Unable to find a Bluetooth peer')

            # Check the chameleond version on the peer and update if necessary
            if update_btpeers:
                if not bluetooth_peer_update.update_all_peers(self.host):
                    logging.error('Updating btpeers failed. Ignored')
            else:
                logging.info('No attempting peer update.')

            # Query connected devices on our btpeer at init time
            self.available_devices = self.list_devices_available()

            for btpeer in self.host.btpeer_list:
                btpeer.register_raspPi_log(self.outputdir)

            self.btpeer_group = dict()
            # Create copy of btpeer_group
            self.btpeer_group_copy = dict()
            self.group_btpeers_type()

        # Clear the active devices for this test
        self.active_test_devices = {}

        self.enable_disable_debug_log(enable=True)

        # Disable cellular services, as they can sometimes interfere with
        # suspend/resume, i.e. b/161920740
        self.enable_disable_cellular(enable=False)

        self.enable_disable_ui(enable=False)

        # Delete files created in previous run
        self.host.run('[ ! -d {0} ] || rm -rf {0} || true'.format(
                                                    self.BTMON_DIR_LOG_PATH))
        self.host.run('[ ! -d {0} ] || rm -rf {0} || true'.format(
                                                    self.USBMON_DIR_LOG_PATH))

        self.dut_btmon_log_path = self.start_new_btmon()
        self.start_new_usbmon()

        self.identify_platform_failure_reasons()

        self.flag = flag
        self.test_iter = None

        self.bat_tests_results = []
        self.bat_pass_count = 0
        self.bat_fail_count = 0
        self.bat_testna_count = 0
        self.bat_warn_count = 0
        self.bat_name = None
        self.bat_iter = None

        self.pkg_tests_results = []
        self.pkg_pass_count = 0
        self.pkg_fail_count = 0
        self.pkg_testna_count = 0
        self.pkg_warn_count = 0
        self.pkg_name = None
        self.pkg_iter = None
        self.pkg_is_running = False
        self.mtbf_end = False
        self.mtbf_end_lock = threading.Lock()


    @staticmethod
    def quick_test_test_decorator(test_name,
                                  devices={},
                                  flags=['All'],
                                  model_testNA=[],
                                  model_testWarn=[],
                                  skip_models=[],
                                  skip_chipsets=[],
                                  skip_common_errors=False,
                                  supports_floss=False,
                                  use_all_peers=False):
        """A decorator providing a wrapper to a quick test.
           Using the decorator a test method can implement only the core
           test and let the decorator handle the quick test wrapper methods
           (test_start and test_end).

           @param test_name: the name of the test to log.
           @param devices:   list of device names which are going to be used
                             in the following test.
           @param flags: list of string to describe who should run the
                         test. The string could be one of the following:
                         ['AVL', 'Quick Health', 'All'].
           @param model_testNA: If the current platform is in this list,
                                failures are emitted as TestNAError.
           @param model_testWarn: If the current platform is in this list,
                                  failures are emitted as TestWarn.
           @param skip_models: Raises TestNA on these models and doesn't attempt
                               to run the tests.
           @param skip_chipsets: Raises TestNA on these chipset and doesn't
                                 attempt to run the tests.
           @param skip_common_errors: If the test encounters a common error
                                      (such as USB disconnect or daemon crash),
                                      mark the test as TESTNA instead.
                                      USE THIS SPARINGLY, it may mask bugs. This
                                      is available for tests that require state
                                      to be properly retained throughout the
                                      whole test (i.e. advertising) and any
                                      outside failure will cause the test to
                                      fail.
          @param supports_floss: Does this test support running on Floss?
          @param use_all_peers: Set number of devices to be used to the
                                maximum available. This is used for tests
                                like bluetooth_PeerVerify which uses all
                                available peers. Specify only one device type
                                if this is set to true
        """

        def decorator(test_method):
            """A decorator wrapper of the decorated test_method.
               @param test_method: the test method being decorated.
               @returns the wrapper of the test method.
            """

            def _check_runnable(self):
                """Check if the test could be run"""

                # Check that the test is runnable in current setting
                if not(self.flag in flags or 'All' in flags):
                    logging.info('SKIPPING TEST %s', test_name)
                    logging.info('flag %s not in %s', self.flag, flags)
                    self._print_delimiter()
                    return False

                # If the current test was to run with Floss, the test must
                # support running with Floss.
                if self.floss:
                    return supports_floss

                return True

            def _is_enough_peers_present(self):
                """Check if enough peer devices are available."""

                # Check that btpeer has all required devices before running
                for device_type, number in devices.items():
                    if self.available_devices.get(device_type, 0) < number:
                        logging.info('SKIPPING TEST %s', test_name)
                        logging.info('%s not available', device_type)
                        self._print_delimiter()
                        return False

                # Check if there are enough peers
                total_num_devices = sum(devices.values())
                if total_num_devices > len(self.host.btpeer_list):
                    logging.info('SKIPPING TEST %s', test_name)
                    logging.info(
                            'Number of devices required %s is greater'
                            'than number of peers available %d',
                            total_num_devices, len(self.host.btpeer_list))
                    self._print_delimiter()
                    return False
                return True

            @functools.wraps(test_method)
            def wrapper(self):
                """A wrapper of the decorated method."""
                # Set test name before exiting so batches correctly identify
                # failing tests
                self.test_name = test_name

                # Every test_method should pass by default.
                # This should be placed in the beginning of the wrapper before
                # executing any self.test_xxx tests. This statement should not
                # be placed inside quick_test_test_start(). If there are any
                # exceptions raised in the try block below, the
                # quick_test_test_end() which contains self.test_xxx tests
                # would be executed without the _expected_result attribute
                # getting populated.
                self._expected_result = True

                if not _check_runnable(self):
                    return

                try:
                    if use_all_peers:
                        if devices != {}:
                            devices[list(devices.keys())[0]] = len(
                                    self.host.btpeer_list)

                    if not _is_enough_peers_present(self):
                        logging.info('Not enough peer available')
                        raise error.TestNAError('Not enough peer available')

                    model = self.get_base_platform_name()
                    if model in skip_models:
                        logging.info('SKIPPING TEST %s', test_name)
                        raise error.TestNAError(
                                'Test not supported on this model')

                    chipset = self.bluetooth_facade.get_chipset_name()
                    logging.debug('Bluetooth module name is %s', chipset)
                    if chipset in skip_chipsets:
                        logging.info('SKIPPING TEST %s on chipset %s',
                                     test_name, chipset)
                        raise error.TestNAError(
                                'Test not supported on this chipset')

                    self.quick_test_test_start(test_name, devices)

                    test_method(self)
                except error.TestError as e:
                    fail_msg = '[--- error {} ({})]'.format(
                            test_method.__name__, str(e))
                    logging.error(fail_msg)
                    self.fails.append(fail_msg)
                except error.TestFail as e:
                    fail_msg = '[--- failed {} ({})]'.format(
                            test_method.__name__, str(e))
                    logging.error(fail_msg)
                    self.fails.append(fail_msg)
                except error.TestNAError as e:
                    fail_msg = '[--- SKIPPED {} ({})]'.format(
                            test_method.__name__, str(e))
                    logging.error(fail_msg)
                    self.fails.append(fail_msg)
                except Exception as e:
                    fail_msg = '[--- unknown error {} ({})]'.format(
                            test_method.__name__, str(e))
                    logging.exception(fail_msg)
                    self.fails.append(fail_msg)

                self.quick_test_test_end(model_testNA=model_testNA,
                                         model_testWarn=model_testWarn,
                                         skip_common_errors=skip_common_errors)

            return wrapper

        return decorator


    def quick_test_test_start(
            self, test_name=None, devices={}):
        """Start a quick test. The method clears and restarts adapter on DUT
           as well as peer devices. In addition the methods prints test start
           traces.
        """
        # Bluetoothd could have crashed behind the scenes; check to see if
        # everything is still ok and recover if needed.
        self.test_is_facade_valid()
        self.test_is_adapter_valid()

        # Reset the adapter
        self.test_reset_on_adapter()

        # Reset the policy allowlist so that all UUIDs are allowed.
        self.test_reset_allowlist()

        # Reset power/wakeup to disabled.
        self.test_adapter_set_wake_disabled()

        # Initialize bluetooth_adapter_tests class (also clears self.fails)
        self.initialize()
        # Start and peer HID devices
        self.start_peers(devices)

        if test_name is not None:
            time.sleep(self.TEST_SLEEP_SECS)
            self._print_delimiter()
            logging.info('Starting test: %s', test_name)
            self.log_message('Starting test: %s'% test_name)

    def quick_test_test_end(self,
                            model_testNA=[],
                            model_testWarn=[],
                            skip_common_errors=False):
        """Log and track the test results"""
        result_msgs = []
        model = self.get_base_platform_name()

        if self.test_iter is not None:
            result_msgs += ['Test Iter: ' + str(self.test_iter)]

        if self.bat_iter is not None:
            result_msgs += ['Batch Iter: ' + str(self.bat_iter)]

        if self.pkg_is_running is True:
            result_msgs += ['Package iter: ' + str(self.pkg_iter)]

        if self.bat_name is not None:
            result_msgs += ['Batch Name: ' + self.bat_name]

        if self.test_name is not None:
            result_msgs += ['Test Name: ' + self.test_name]

        result_msg = ", ".join(result_msgs)

        if not bool(self.fails):
            result_msg = 'PASSED | ' + result_msg
            self.bat_pass_count += 1
            self.pkg_pass_count += 1
        # The test should be marked as TESTNA if any of the test expressions
        # were SKIPPED (they threw their own TESTNA error) or the model is in
        # the list of NA models (so any failure is considered NA instead)
        elif model in model_testNA or any(['SKIPPED' in x
                                           for x in self.fails]):
            result_msg = 'TESTNA | ' + result_msg
            self.bat_testna_count += 1
            self.pkg_testna_count += 1
        elif model in model_testWarn:
            result_msg = 'WARN   | ' + result_msg
            self.bat_warn_count += 1
            self.pkg_warn_count += 1
        # Some tests may fail due to known common failure reasons (like usb
        # disconnect during suspend, bluetoothd crashes, etc). Skip those tests
        # with TESTNA when that happens.
        #
        # This should be used sparingly because it may hide legitimate errors.
        elif bool(self.had_known_common_failure) and skip_common_errors:
            result_msg = 'TESTNA | ' + result_msg
            self.bat_testna_count += 1
            self.pkg_testna_count += 1
        else:
            result_msg = 'FAIL   | ' + result_msg
            self.bat_fail_count += 1
            self.pkg_fail_count += 1

        logging.info(result_msg)
        self.log_message(result_msg)
        self._print_delimiter()
        self.bat_tests_results.append(result_msg)
        self.pkg_tests_results.append(result_msg)

        if self.test_name is not None:
            logging.info('Cleanning up and restarting towards next test...')


        # Bluetoothd could have crashed behind the scenes; check if everything
        # is ok and recover if needed. This is done as part of clean-up as well
        # to make sure we can fully remove pairing info between tests
        self.test_is_facade_valid()

        self.bluetooth_facade.stop_discovery()

        # Catch possible exceptions in test_reset_allowlist().
        # Refer to b/184947150 for more context.
        try:
            # Reset the policy allowlist so that all UUIDs are allowed.
            self.test_reset_allowlist()
        except:
            msg = ('Failed to reset the policy allowlist.\n'
                   '### Note: reset the allowlist manually if needed. ###\n\n'
                   'dbus-send --system --print-reply --dest=org.bluez '
                   '/org/bluez/hci0 org.bluez.AdminPolicy1.SetServiceAllowList '
                   'array:string:"" \n')
            logging.error(msg)

        # Store a copy of active devices for raspi reset in the final step
        self.active_test_devices = self.devices

        # Disconnect devices used in the test, and remove the pairing.
        for device_list in self.devices.values():
            for device in device_list:
                if device is not None:
                    self.stop_agent(device)
                    logging.info('Clear device %s from DUT', device.name)
                    self.bluetooth_facade.disconnect_device(device.address)
                    device_is_paired = self.bluetooth_facade.device_is_paired(
                            device.address)
                    if device_is_paired:
                        self.bluetooth_facade.remove_device_object(
                                device.address)

                    # Also remove pairing on Peer
                    logging.info('Clearing DUT from %s', device.name)
                    try:
                        device.RemoveDevice(self.bluetooth_facade.address)
                    except Exception as e:
                        # If peer doesn't expose RemoveDevice, ignore failure
                        if not (e.__class__.__name__ == 'Fault' and
                                'is not supported' in str(e)):
                            logging.info('Couldn\'t Remove: {}'.format(e))
                            raise


        # Repopulate btpeer_group for next tests
        # Clear previous tets's leftover entries. Don't delete the
        # btpeer_group dictionary though, it'll be used as it is.
        if self.use_btpeer:
            for device_type in self.btpeer_group:
                if len(self.btpeer_group[device_type]) > 0:
                    del self.btpeer_group[device_type][:]

            # Repopulate
            self.group_btpeers_type()

        # Close the connection between peers
        self.cleanup_bt_test(test_state='NEW')

    @staticmethod
    def quick_test_batch_decorator(batch_name):
        """A decorator providing a wrapper to a batch.
           Using the decorator a test batch method can implement only its
           core tests invocations and let the decorator handle the wrapper,
           which is taking care for whether to run a specific test or the
           batch as a whole and and running the batch in iterations

           @param batch_name: the name of the batch to log
        """

        def decorator(batch_method):
            """A decorator wrapper of the decorated test_method.
               @param test_method: the test method being decorated.
               @returns the wrapper of the test method.
            """

            @functools.wraps(batch_method)
            def wrapper(self, num_iterations=1, test_name=None):
                """A wrapper of the decorated method.
                  @param num_iterations: how many interations to run
                  @param test_name: specifc test to run otherwise None to run
                                    the whole batch
                """
                if test_name is not None:
                    single_test_method = getattr(self,  test_name)
                    for iter in range(1,num_iterations+1):
                        self.test_iter = iter
                        single_test_method()

                    if self.fails:
                        # If failure is marked as TESTNA, prioritize that over
                        # a failure. Same with WARN.
                        if self.bat_testna_count > 0:
                            raise error.TestNAError(self.fails)
                        elif self.bat_warn_count > 0:
                            raise error.TestWarn(self.fails)
                        else:
                            raise error.TestFail(self.fails)
                else:
                    for iter in range(1,num_iterations+1):
                        self.quick_test_batch_start(batch_name, iter)
                        batch_method(self, num_iterations, test_name)
                        self.quick_test_batch_end()
            return wrapper

        return decorator


    def quick_test_batch_start(self, bat_name, iteration=1):
        """Start a test batch. The method clears and set batch variables"""
        self.bat_tests_results = []
        self.bat_pass_count = 0
        self.bat_fail_count = 0
        self.bat_testna_count = 0
        self.bat_warn_count = 0
        self.bat_name = bat_name
        self.bat_iter = iteration


    def quick_test_batch_end(self):
        """Print results summary of a test batch """
        logging.info(
                '%s Test Batch Summary: total pass %d, total fail %d, '
                'warn %d, NA %d', self.bat_name, self.bat_pass_count,
                self.bat_fail_count, self.bat_warn_count,
                self.bat_testna_count)
        for result in self.bat_tests_results:
            logging.info(result)
        self._print_delimiter();
        if self.bat_fail_count > 0:
            logging.error('===> Test Batch Failed! More than one failure')
            self._print_delimiter();
            if self.pkg_is_running is False:
                raise error.TestFail(self.bat_tests_results)
        elif self.bat_testna_count > 0:
            logging.error('===> Test Batch Passed! Some TestNA results')
            self._print_delimiter();
            if self.pkg_is_running is False:
                raise error.TestNAError(self.bat_tests_results)
        elif self.bat_warn_count > 0:
            logging.error('===> Test Batch Passed! Some WARN results')
            self._print_delimiter();
            if self.pkg_is_running is False:
                raise error.TestWarn(self.bat_tests_results)
        else:
            logging.info('===> Test Batch Passed! zero failures')
            self._print_delimiter();


    def quick_test_package_start(self, pkg_name):
        """Start a test package. The method clears and set batch variables"""
        self.pkg_tests_results = []
        self.pkg_pass_count = 0
        self.pkg_fail_count = 0
        self.pkg_name = pkg_name
        self.pkg_is_running = True


    def quick_test_print_summary(self):
        """Print results summary of a test package"""
        logging.info(
                '%s Test Package Summary: total pass %d, total fail %d, '
                'Warn %d, NA %d', self.pkg_name, self.pkg_pass_count,
                self.pkg_fail_count, self.pkg_warn_count,
                self.pkg_testna_count)
        for result in self.pkg_tests_results:
            logging.info(result)
        self._print_delimiter();


    def quick_test_package_update_iteration(self, iteration):
        """Update state and print log per package iteration.
           Must be called to have a proper package test result tracking.
        """
        self.pkg_iter = iteration
        if self.pkg_name is None:
            logging.error('Error: no quick package is running')
            raise error.TestFail('Error: no quick package is running')
        logging.info('Starting %s Test Package iteration %d',
                     self.pkg_name, iteration)


    def quick_test_package_end(self):
        """Print final result of a test package"""
        if self.pkg_fail_count > 0:
            logging.error('===> Test Package Failed! More than one failure')
            self._print_delimiter();
            raise error.TestFail(self.bat_tests_results)
        elif self.pkg_testna_count > 0:
            logging.error('===> Test Package Passed! Some TestNA results')
            self._print_delimiter();
            raise error.TestNAError(self.bat_tests_results)
        elif self.pkg_warn_count > 0:
            logging.error('===> Test Package Passed! Some WARN results')
            self._print_delimiter();
            raise error.TestWarn(self.bat_tests_results)
        else:
            logging.info('===> Test Package Passed! zero failures')
            self._print_delimiter();
        self.pkg_is_running = False


    def quick_test_cleanup(self):
        """ Cleanup any state test server and all device"""

        # Clear any raspi devices at very end of test
        for device_list in self.active_test_devices.values():
            for device in device_list:
                if device is not None:
                    self.clear_raspi_device(device)
                    self.device_set_powered(device, False)

        # Reset the adapter
        self.test_reset_on_adapter()
        # Initialize bluetooth_adapter_tests class (also clears self.fails)
        self.initialize()


    @staticmethod
    def quick_test_mtbf_decorator(timeout_mins, test_name):
        """A decorator enabling a test to be run as a MTBF test, it will run
           the underlying test in a infinite loop until it fails or timeout is
           reached, in both cases the time elapsed time will be reported.

           @param timeout_mins: the max execution time of the test, once the
                                time is up the test will report success and exit
           @param test_name: the MTBF test name to be output to the dashboard
        """

        def decorator(batch_method):
            """A decorator wrapper of the decorated batch_method.
               @param batch_method: the batch method being decorated.
               @returns the wrapper of the batch method.
            """

            @functools.wraps(batch_method)
            def wrapper(self, *args, **kwargs):
                """A wrapper of the decorated method"""
                self.mtbf_end = False
                mtbf_timer = threading.Timer(
                    timeout_mins * 60, self.mtbf_timeout)
                mtbf_timer.start()
                start_time = time.time()
                board = self.host.get_board().split(':')[1]
                model = self.host.get_model_from_cros_config()
                build = self.host.get_release_version()
                milestone = 'M' + self.host.get_chromeos_release_milestone()
                in_lab = site_utils.host_in_lab(self.host.hostname)
                while True:
                    with self.mtbf_end_lock:
                        # The test ran the full duration without failure
                        if self.mtbf_end:
                            self.report_mtbf_result(
                                True, start_time, test_name, model, build,
                                milestone, board, in_lab)
                            break
                    try:
                        batch_method(self, *args, **kwargs)
                    except Exception as e:
                        logging.info("Caught a failure: %r", e)
                        self.report_mtbf_result(
                            False, start_time, test_name, model, build,
                            milestone, board, in_lab)
                        # Don't report the test run as failed for MTBF
                        self.fails = []
                        break

                mtbf_timer.cancel()

            return wrapper

        return decorator


    def mtbf_timeout(self):
        """Handle time out event of a MTBF test"""
        with self.mtbf_end_lock:
            self.mtbf_end = True


    def report_mtbf_result(self, success, start_time, test_name, model, build,
        milestone, board, in_lab):
        """Report MTBF result by uploading it to GCS"""
        duration_secs = int(time.time() - start_time)
        start_time = int(start_time)
        gm_time_struct = time.localtime(start_time)
        output_file_name = self.GCS_MTBF_BUCKET + \
                           time.strftime('%Y-%m-%d/', gm_time_struct) + \
                           time.strftime('%H-%M-%S.csv', gm_time_struct)

        mtbf_result = '{0},{1},{2},{3},{4},{5},{6},{7}'.format(
            model, build, milestone, start_time * 1000000, duration_secs,
            success, test_name, board)
        with tempfile.NamedTemporaryFile() as tmp_file:
            tmp_file.write(mtbf_result.encode('utf-8'))
            tmp_file.flush()
            cmd = 'gsutil cp {0} {1}'.format(tmp_file.name, output_file_name)
            logging.info('Result to upload %s %s', mtbf_result, cmd)
            # Only upload the result when running in the lab.
            if in_lab:
                logging.info('Uploading result')
                utils.run(cmd)


    # ---------------------------------------------------------------
    # Wake from suspend tests
    # ---------------------------------------------------------------

    def run_peer_wakeup_device(self,
                               device_type,
                               device,
                               device_test=None,
                               iterations=1,
                               should_wake=True,
                               should_pair=True,
                               keep_paired=False):
        """ Uses paired peer device to wake the device from suspend.

        @param device_type: the device type (used to determine if it's LE)
        @param device: the meta device with the paired device
        @param device_test: What to test to run after waking and connecting the
                            adapter/host
        @param iterations: Number of suspend + peer wake loops to run
        @param should_wake: Whether wakeup should occur on this test. With HID
                            peers, this should be True. With non-HID peers, this
                            should be false.
        @param should_pair: Pair and connect the device first before running
                            the wakeup test.
        @param keep_paired: Keep the paried devices after test.
        """
        boot_id = self.host.get_boot_id()

        if should_wake:
            sleep_time = EXPECT_PEER_WAKE_SUSPEND_SEC
            resume_time = EXPECT_PEER_WAKE_RESUME_BY
            resume_slack = 5  # Allow 5s slack for resume timeout
            measure_resume = True
        else:
            sleep_time = EXPECT_NO_WAKE_SUSPEND_SEC
            resume_time = EXPECT_NO_WAKE_SUSPEND_SEC
            # Negative resume slack lets us wake a bit earlier than expected
            # If suspend takes a while to enter, this may be necessary to get
            # the timings right.
            resume_slack = -5
            measure_resume = False

        try:
            if should_pair:
                # Clear wake before testing
                self.test_adapter_set_wake_disabled()
                self.assert_discover_and_pair(device)
                self.assert_on_fail(
                        self.test_device_set_discoverable(device, False))

                # Confirm connection completed
                self.assert_on_fail(
                        self.test_device_is_connected(device.address))

            # Profile connection may not have completed yet and this will
            # race with a subsequent disconnection (due to suspend). Use the
            # device test to force profile connect or wait if no test was
            # given.
            if device_test is not None:
                self.assert_on_fail(device_test(device))
            else:
                time.sleep(PROFILE_CONNECT_WAIT)

            for it in range(iterations):
                logging.info(
                        'Running iteration {}/{} of suspend peer wake'.format(
                                it + 1, iterations))

                # Start a new suspend instance
                suspend = self.suspend_async(suspend_time=sleep_time,
                                             expect_bt_wake=should_wake)
                start_time = self.bluetooth_facade.get_device_utc_time()

                if should_wake:
                    self.test_device_wake_allowed(device.address)
                    # Also wait until powerd marks adapter as wake enabled
                    self.test_adapter_wake_enabled()
                else:
                    self.test_device_wake_not_allowed(device.address)

                # Trigger suspend, asynchronously wake and wait for resume
                adapter_address = self.bluetooth_facade.address
                self.test_suspend_and_wait_for_sleep(suspend,
                                                     sleep_timeout=SUSPEND_SEC)

                # Trigger peer wakeup
                peer_wake = self.device_connect_async(device_type,
                                                      device,
                                                      adapter_address,
                                                      delay_wake=5,
                                                      should_wake=should_wake)
                peer_wake.start()

                # Expect a quick resume. If a timeout occurs, test fails. Since
                # we delay sending the wake signal, we should accommodate that
                # in our expected timeout.
                self.test_wait_for_resume(boot_id,
                                          suspend,
                                          resume_timeout=resume_time,
                                          test_start_time=start_time,
                                          resume_slack=resume_slack,
                                          fail_on_timeout=should_wake,
                                          fail_early_wake=not should_wake,
                                          collect_resume_time=measure_resume)

                # Finish peer wake process
                peer_wake.join()

                # Only check peer device connection state if we expected to wake
                # from it. Otherwise, we may or may not be connected based on
                # the specific profile's reconnection policy.
                if should_wake:
                    # Make sure we're actually connected
                    self.test_device_is_connected(device.address)

                    # Verify the profile is working
                    if device_test is not None:
                        device_test(device)

        finally:
            if should_pair and not keep_paired:
                self.test_remove_pairing(device.address)
