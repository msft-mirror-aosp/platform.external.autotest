# Lint as: python2, python3
# Copyright 2019 The ChromiumOS Authors
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
import multiprocessing
import tempfile
import threading
import time

import common
from autotest_lib.client.common_lib import error
from autotest_lib.client.common_lib.cros.bluetooth import bluetooth_quick_tests_base
from autotest_lib.server import site_utils
from autotest_lib.server.cros.bluetooth import bluetooth_peer_update
from autotest_lib.server.cros.bluetooth import bluetooth_adapter_tests
from autotest_lib.server.cros.bluetooth import bluetooth_attenuator
from autotest_lib.server.cros.dark_resume_utils import DarkResumeUtils
from autotest_lib.server.cros.multimedia import remote_facade_factory
from autotest_lib.server.cros.servo import chrome_ec
from autotest_lib.client.bin import utils
from six.moves import range

PROFILE_CONNECT_WAIT = 15
SUSPEND_SEC = 15
EXPECT_NO_WAKE_SUSPEND_SEC = 30
EXPECT_PEER_WAKE_SUSPEND_SEC = 60
EXPECT_PEER_WAKE_RESUME_BY = 30


get_num_devices = bluetooth_adapter_tests.get_num_devices
calc_total_num_devices = bluetooth_adapter_tests.calc_total_num_devices


class BluetoothAdapterQuickTests(
        bluetooth_adapter_tests.BluetoothAdapterTests,
        bluetooth_quick_tests_base.BluetoothQuickTestsBase):
    """Bluetooth quick test implementation for server tests."""

    GCS_MTBF_BUCKET = 'gs://chromeos-mtbf-bt-results/'


    def restart_peers(self):
        """Restart and clear peer devices

        This method is called when the peers have to be restarted in
        the middle of a test. For example, auto_reconnect_loop() in
        bluetooth_adapter_pairing_tests.py calls this method to
        restart peers to verify reconnection.
        """
        # Restart the link to device
        logging.info('Restarting peer devices...')

        # Grab current device list for initialization
        connected_devices = self.devices
        self.cleanup_bt_test(test_state='MID')

        for device_type, device_list in connected_devices.items():
            for device in device_list:
                if device is not None:
                    logging.info('Restarting %s', device_type)
                    self.get_device(device_type, device.cap_reqs,
                                    on_start=False)


    def start_peers(self, device_configs):
        """Start peer devices

        This method is called when a test is just started in the beginning.

        @param device_configs: a dict which specifies either the number of
                devices needed for each device_type, or the capability
                requirements of the btpeer.
        """
        # Start the link to devices
        if self.use_btpeer:
            logging.info('Starting peer devices...')
            self.get_device_rasp(device_configs)

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
                        floss=False,
                        llprivacy=False,
                        floss_lm_quirk=False,
                        enable_cellular=False,
                        enable_ui=False):
        """Inits the test batch

        @param floss_lm_quirk True to enable the quirk for b/260539322 to
                mitigate the interoperability issue between Intel and Cypress.
                TODO(b/260539322): remove the flag once the issue is solved.
        """

        super().quick_test_init(flag)

        self.host = host
        self.start_browser = start_browser
        self.use_btpeer = use_btpeer
        self.floss = floss
        self.local_host_ip = None
        self.llprivacy = llprivacy
        self.floss_lm_quirk = floss_lm_quirk
        self.args_dict = args_dict if args_dict else {}

        logging.info("Initialize dark resume utils.")
        self._dr_utils = DarkResumeUtils(self.host)
        # Bluetooth should lead to a full resume, but if dark resume is on,
        # it may go into dark suspend again in case the test fails, so the
        # DUT may not wake up.
        # This function is to prevent the DUT from dark suspend.
        self._dr_utils.stop_resuspend_on_dark_resume()
        self._ec = chrome_ec.ChromeEC(self.host.servo)

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

        if clean_log != 'FALSE':
            # Clean Bluetooth kernel logs in the DUT to prevent
            # /var/log/messages occupying too much space
            self.bluetooth_facade.cleanup_syslogs()

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
                raise error.TestNAError('Unable to find a Bluetooth peer')

            # Check the chameleond version on the peer and update if necessary
            if update_btpeers:
                if not bluetooth_peer_update.update_all_btpeers(self.host):
                    logging.error('Updating btpeers failed. Ignored')
            else:
                logging.info('No attempting peer update.')

            # Query connected devices on our btpeer at init time
            self.available_devices = self.list_devices_available()

            for btpeer in self.host.btpeer_list:
                btpeer.register_raspPi_log(self.outputdir)
                # TODO(b/260539322) Remove the quirk after fixing the
                # interoperability issue between Intel and Cypress. This quirk
                # used the hciconfig tool to force the Raspberry Pi to use
                # CENTRAL link mode rather than PERIPHERAL. The additional role
                # negotiation/switching helped mitigate the interoperability
                # mentioned above issue.
                if self.floss and self.floss_lm_quirk:
                    btpeer.set_bluetooth_link_mode("MASTER")

            self.btpeer_group = dict()
            # Create copy of btpeer_group
            self.btpeer_group_copy = dict()
            self.group_btpeers_type()

        try:
            self.audio_facade = self.factory.create_audio_facade()
        except Exception as e:
            logging.error('Exception %s while creating audio_facade',
                          str(e))
            raise error.TestFail('Unable to create audio_facade')

        # Clear the active devices for this test
        self.active_test_devices = {}

        self.enable_disable_debug_log(enable=True)

        # Disable cellular services, as they can sometimes interfere with
        # suspend/resume, i.e. b/161920740
        self.enable_disable_cellular(enable=enable_cellular)

        self.enable_disable_ui(enable=enable_ui)

        # Delete files created in previous run
        self.host.run('[ ! -d {0} ] || rm -rf {0} || true'.format(
                                                    self.BTMON_DIR_LOG_PATH))
        self.host.run('[ ! -d {0} ] || rm -rf {0} || true'.format(
                                                    self.USBMON_DIR_LOG_PATH))

        self.dut_btmon_log_path = self.start_new_btmon()
        self.start_new_usbmon()

        self.identify_platform_failure_reasons()

        self.mtbf_end = False
        self.mtbf_end_lock = threading.Lock()

    def quick_test_get_board(self):
        """Returns the board.

           Needed by BluetoothQuickTestsBase.quick_test_test_decorator.
        """
        return self.get_board()

    def quick_test_get_model_name(self):
        """Returns the model name.

           Needed by BluetoothQuickTestsBase.quick_test_test_decorator.
        """
        return self.get_base_platform_name()

    def quick_test_get_chipset_name(self):
        """Returns the chipset name.

           Needed by BluetoothQuickTestsBase.quick_test_test_decorator.
        """
        return self.bluetooth_facade.get_chipset_name()

    def quick_test_get_kernel_version(self):
        """Returns the kernel's version.

           Needed by BluetoothQuickTestsBase.quick_test_test_decorator.
        """
        return self.bluetooth_facade.get_kernel_version()

    @staticmethod
    def quick_test_test_decorator(test_name,
                                  devices={},
                                  flags=['All'],
                                  allowed_boards=None,
                                  model_testNA=[],
                                  model_testWarn=[],
                                  skip_models=[],
                                  skip_chipsets=[],
                                  skip_common_errors=False,
                                  supports_floss=False,
                                  use_all_peers=False,
                                  minimum_kernel_version=''):
        """A decorator providing a wrapper to a quick test.
           Using the decorator a test method can implement only the core
           test and let the decorator handle the quick test wrapper methods
           (reset/cleanup/logging).

           @param test_name: the name of the test to log.
           @param devices: map of the device types and the quantities needed for
                           the test.
                           For example, {'BLE_KEYBOARD':1, 'BLE_MOUSE':1}.
           @param flags: list of string to describe who should run the
                         test. The string could be one of the following:
                         ['AVL', 'Quick Health', 'All'].
           @param allowed_boards: If not None, raises TestNA on boards that are
                                  not in this set.
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
           @param minimum_kernel_version: Raises TestNA on less than this
                                          kernel's version and doesn't attempt
                                          to run the tests.
        """

        base_class = bluetooth_quick_tests_base.BluetoothQuickTestsBase
        return base_class.quick_test_test_decorator(
                test_name,
                flags=flags,
                pretest_func=lambda self: self.quick_test_test_pretest(
                        test_name, devices, use_all_peers, supports_floss),
                posttest_func=lambda self: self.quick_test_test_posttest(),
                allowed_boards=allowed_boards,
                model_testNA=model_testNA,
                model_testWarn=model_testWarn,
                skip_models=skip_models,
                skip_chipsets=skip_chipsets,
                skip_common_errors=skip_common_errors,
                minimum_kernel_version=minimum_kernel_version)

    def quick_test_test_pretest(self,
                                test_name=None,
                                device_configs={},
                                use_all_peers=False,
                                supports_floss=False):
        """Runs pretest checks and resets DUT's adapter and peer devices.

           @param test_name: the name of the test to log.
           @param device_configs: map of the device types and values
                           There are two possibilities of the values
                           (1) the quantities needed for the test.
                               For example, {'BLE_KEYBOARD':1, 'BLE_MOUSE':1}.
                           (2) a tuple of tuples of required capabilities, e.g.,
                               devices={'BLUETOOTH_AUDIO':
                                            (('PIPEWIRE', 'LE_AUDIO'),)}
                               which requires a BLUETOOTH_AUDIO device with
                               the capabilities of support PIPEWIRE and LE_AUDIO
                               adapter.
           @param use_all_peers: Set number of devices to be used to the
                                 maximum available. This is used for tests
                                 like bluetooth_PeerVerify which uses all
                                 available peers. Specify only one device type
                                 if this is set to true
           @param supports_floss: Does this test support running on Floss?
        """

        def _is_enough_peers_present(self):
            """Checks if enough peer devices are available."""

            # Check that btpeer has all required devices before running
            for device_type, cap_reqs in device_configs.items():
                number = get_num_devices(cap_reqs)
                if self.available_devices.get(device_type, 0) < number:
                    logging.info('SKIPPING TEST %s', test_name)
                    logging.info('%s not available', device_type)
                    self._print_delimiter()
                    return False

            # Check if there are enough peers
            total_num_devices = calc_total_num_devices(device_configs)
            if total_num_devices > len(self.host.btpeer_list):
                logging.info('SKIPPING TEST %s', test_name)
                logging.info(
                        'Number of devices required %s is greater'
                        'than number of peers available %d', total_num_devices,
                        len(self.host.btpeer_list))
                self._print_delimiter()
                return False
            return True

        if use_all_peers:
            if device_configs != {}:
                device_configs[list(device_configs.keys())[0]] = len(
                        self.host.btpeer_list)

        if not _is_enough_peers_present(self):
            logging.info('Not enough peer available')
            raise error.TestNAError('Not enough peer available')

        if self.floss and not supports_floss:
            raise error.TestNAError('Test ' + test_name +
                                    ' does not support Floss')

        # Every test_method should pass by default.
        self._expected_result = True

        # Bluetoothd could have crashed behind the scenes; check to see if
        # everything is still ok and recover if needed.
        # This also ensures BT daemon is running prior to setting LL privacy.
        self.test_is_facade_valid()
        self.test_is_adapter_valid()

        # The test_set_ll_privacy() call will persist the LL privacy status in
        # the config file, so when the adapter is reset, unless the config file
        # is explicitly updated, the new LL privacy status is still valid.
        if not self.test_set_ll_privacy(self.llprivacy):
            raise error.TestError('Failed to set LL privacy to {}'.format(
                    self.llprivacy))

        # Reset the adapter
        self.test_reset_on_adapter()

        # Reset the policy allowlist so that all UUIDs are allowed.
        self.test_reset_allowlist()

        # Reset power/wakeup to disabled.
        self.test_adapter_set_wake_disabled()

        # Initialize bluetooth_adapter_tests class (also clears self.fails)
        self.initialize()
        # Start and peer HID devices
        self.start_peers(device_configs)

        time.sleep(self.TEST_SLEEP_SECS)
        self.log_message('Starting test: %s' % test_name)


    def quick_test_test_posttest(self):
        """Runs posttest cleanups.

        """

        logging.info('Cleanning up and restarting towards next test...')
        self.log_message(self.bat_tests_results[-1])

        # Every test_method should pass by default.
        self._expected_result = True

        # Bluetoothd could have crashed behind the scenes; check if everything
        # is ok and recover if needed. This is done as part of clean-up as well
        # to make sure we can fully remove pairing info between tests
        self.test_is_facade_valid()

        # Set ll privacy to false because default is false
        if self.llprivacy:
            if not self.test_set_ll_privacy(False):
                logging.error("Failed to reset ll privacy.")
            else:
                logging.info("Reset ll privacy to False.")

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

        dut_adapter_address = ''
        if self.bluetooth_facade.address:
            dut_adapter_address = self.bluetooth_facade.address
        elif hasattr(self, '_dut_address_cache'):
            dut_adapter_address = self._dut_address_cache

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

                    # If DUT's adapter address is empty, likely the adapter is
                    # dead. Skip clearing DUT from peers.
                    if not dut_adapter_address:
                        continue

                    # Also remove pairing on Peer
                    logging.info('Clearing DUT from %s', device.name)
                    try:
                        device.RemoveDevice(dut_adapter_address)
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


    def quick_test_cleanup(self):
        """ Cleanup any state test server and all device"""

        logging.info("Clean up dark resume utils.")
        try:
            self._dr_utils.stop_resuspend_on_dark_resume(False)
            self._dr_utils.teardown()
        # Unhandled exception would cause test failure.
        except (OSError, ConnectionRefusedError) as e:
            # The error "errno 99" means "Cannot assign requested address".
            # The error "errno 111" means "Connection Refused".
            if e.errno != 99 and e.errno != 111:
                logging.error("Unexpected OSError with code ", e.errno)
            else:
                logging.error(
                        "Safe to ignore connection error for cleaning dark resume."
                )
        except Exception as e:
            logging.error(
                    "Unknown error while restart resuspend on dark resume: ",
                    str(e))

        # Clear any raspi devices at very end of test
        for device_list in self.active_test_devices.values():
            for device in device_list:
                if device is not None:
                    self.clear_raspi_device(device)
                    self.device_set_powered(device, False)

        # Set the link mode as ACCEPT on all btpeers.
        for btpeer in self.host.btpeer_list:
            # TODO(b/260539322) Remove the quirk after fixing the
            # interoperability issue between Intel and Cypress. This quirk
            # used the hciconfig tool to force the Raspberry Pi to use
            # CENTRAL link mode rather than PERIPHERAL. The additional role
            # negotiation/switching helped mitigate the interoperability
            # mentioned above issue.
            if self.floss and self.floss_lm_quirk:
                btpeer.set_bluetooth_link_mode("ACCEPT")

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

    def suspend_dr_async(self, suspend_time):
        """Suspend with dark resume enabled."""
        def _action_suspend():
            self._dr_utils.suspend(suspend_time)
            return 0

        proc = multiprocessing.Process(target=_action_suspend)
        proc.daemon = True
        return proc

    def run_peer_wakeup_device(self,
                               device_type,
                               device,
                               device_test=None,
                               iterations=1,
                               should_wake=True,
                               should_pair=True,
                               keep_paired=False,
                               dark_resume=False):
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
        @param dark_resume: Enable dark resume.
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
                if dark_resume:
                    suspend = self.suspend_dr_async(sleep_time)
                else:
                    suspend = self.suspend_async(suspend_time=sleep_time,
                                                 expect_bt_wake=should_wake)

                start_time = self.bluetooth_facade.get_device_utc_time()

                if should_wake:
                    self.test_device_wake_allowed(device.address)
                    # Also wait until powerd marks adapter as wake enabled
                    self.test_adapter_wake_enabled()
                else:
                    self.test_device_wake_not_allowed(device.address)

                if dark_resume:
                    dark_resume_before = self._dr_utils.count_dark_resumes()

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

                if dark_resume:
                    dark_resume_after = self._dr_utils.count_dark_resumes()
                    # Apply key press to guarantee full resume
                    self._ec.key_press('<ctrl_l>')
                    logging.info("Dark resume before %d after %d",
                                 dark_resume_before, dark_resume_after)
                    if dark_resume_after != dark_resume_before:
                        raise error.TestFail(
                                "Dark resume detected while full resume expected."
                        )

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
