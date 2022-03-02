# Lint as: python2, python3
# Copyright 2016 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Server side bluetooth adapter subtests."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from datetime import datetime, timedelta
import errno
import functools
import six.moves.http_client
import inspect
import logging
import multiprocessing
import os
import re
import socket
import threading
import time

import common
from autotest_lib.client.bin import utils
from autotest_lib.client.bin.input import input_event_recorder as recorder
from autotest_lib.client.common_lib import error
from autotest_lib.client.common_lib.cros.bluetooth import bluetooth_socket
from autotest_lib.client.cros.chameleon import chameleon
from autotest_lib.server.cros.bluetooth import bluetooth_test_utils
from autotest_lib.server import test

from autotest_lib.client.bin.input.linux_input import (
        BTN_LEFT, BTN_RIGHT, EV_KEY, EV_REL, REL_X, REL_Y, REL_WHEEL,
        REL_WHEEL_HI_RES, KEY_PLAYCD, KEY_PAUSECD, KEY_STOPCD, KEY_NEXTSONG,
        KEY_PREVIOUSSONG)
from autotest_lib.server.cros.bluetooth.bluetooth_gatt_client_utils import (
        GATT_ClientFacade, GATT_Application, GATT_HIDApplication)
from autotest_lib.server.cros.multimedia import remote_facade_factory
import six
from six.moves import map
from six.moves import range
from six.moves import zip


Event = recorder.Event

CHIPSET_TO_VIDPID = {
        'MVL-8897': [(('0x02df', '0x912d'), 'SDIO')],
        'MVL-8997': [(('0x1b4b', '0x2b42'), 'USB')],
        'QCA-6174A-5-USB': [(('0x168c', '0x003e'), 'USB')],
        'QCA-6174A-3-UART': [(('0x0271', '0x050a'), 'UART')],
        'QCA-WCN6856': [(('0x17cb', '0x1103'), 'USB')],
        'Intel-AX200': [(('0x8086', '0x2723'), 'USB')],  # CcP2
        'Intel-AX201': [
                (('0x8086', '0x02f0'), 'USB'),
                (('0x8086', '0x4df0'), 'USB'),
                (('0x8086', '0xa0f0'), 'USB'),
        ],  # HrP2
        'Intel-AC9260': [(('0x8086', '0x2526'), 'USB')],  # ThP2
        'Intel-AC9560': [
                (('0x8086', '0x31dc'), 'USB'),  # JfP2
                (('0x8086', '0x9df0'), 'USB')
        ],
        'Intel-AC7260': [
                (('0x8086', '0x08b1'), 'USB'),  # WP2
                (('0x8086', '0x08b2'), 'USB')
        ],
        'Intel-AC7265': [
                (('0x8086', '0x095a'), 'USB'),  # StP2
                (('0x8086', '0x095b'), 'USB')
        ],
        'Realtek-RTL8822C-USB': [(('0x10ec', '0xc822'), 'USB')],
        'Realtek-RTL8822C-UART': [(('0x10ec', '0xc822'), 'UART')],
        'Realtek-RTL8852A-USB': [(('0x10ec', '0x8852'), 'USB')],
        'Mediatek-MTK7921-USB': [(('0x14c3', '0x7961'), 'USB')],
        'Mediatek-MTK7921-SDIO': [(('0x037a', '0x7901'), 'SDIO')]

        # The following doesn't expose vid:pid
        # 'WCN3991-UART'
}

# We have a number of chipsets that are no longer supported. Known issues
# related to firmware will be ignored on these devices (b/169328792).
UNSUPPORTED_CHIPSETS = ['MVL-8897', 'MVL-8997', 'Intel-AC7260', 'Intel-AC7265']

# Location of data traces relative to this (bluetooth_adapter_tests.py) file
BT_ADAPTER_TEST_PATH = os.path.dirname(__file__)
TRACE_LOCATION = os.path.join(BT_ADAPTER_TEST_PATH, 'input_traces/keyboard')

RESUME_DELTA = -5

# Delay binding the methods since host is only available at run time.
SUPPORTED_DEVICE_TYPES = {
        'MOUSE': lambda btpeer: btpeer.get_bluetooth_hid_mouse,
        'KEYBOARD': lambda btpeer: btpeer.get_bluetooth_hid_keyboard,
        'BLE_MOUSE': lambda btpeer: btpeer.get_ble_mouse,
        'BLE_KEYBOARD': lambda btpeer: btpeer.get_ble_keyboard,
        # Tester allows us to test DUT's discoverability, etc. from a peer
        'BLUETOOTH_TESTER': lambda btpeer: btpeer.get_bluetooth_tester,
        # This is a base object that does not emulate any Bluetooth device.
        # This object is preferred when only a pure XMLRPC server is needed
        # on the btpeer host, e.g., to perform servod methods.
        'BLUETOOTH_BASE': lambda btpeer: btpeer.get_bluetooth_base,
        # on the chameleon host, e.g., to perform servod methods.
        'BLUETOOTH_BASE': lambda chameleon: chameleon.get_bluetooth_base,
        # A phone device that supports Bluetooth
        'BLE_PHONE': lambda chameleon: chameleon.get_ble_phone,
        # A Bluetooth audio device emulating a headphone
        'BLUETOOTH_AUDIO': lambda chameleon: chameleon.get_bluetooth_audio,
        # A Bluetooth device that implements the Fast Pair protocol.
        'BLE_FAST_PAIR': lambda chameleon: chameleon.get_ble_fast_pair,
}

COMMON_FAILURES = {
        'Freeing adapter /org/bluez/hci': 'adapter_freed',
        '/var/spool/crash/bluetoothd': 'bluetoothd_crashed',
        'btintel_hw_error': 'intel hardware error detected',
        'qca_hw_error': 'qca hardware error detected',
        'cmd_cnt 0 cmd queued ([5-9]|[1-9][0-9]+)': 'controller cmd capacity',
}

# TODO(b/150898182) - Don't run some tests on tablet form factors
# This list was generated by looking for tablet models on Goldeneye and removing
# the ones that were not launched
TABLET_MODELS = ['kakadu', 'kodama', 'krane', 'dru', 'druwl', 'dumo']

# Some platforms do not have built-in I/O hardware, and so they are configured
# to automatically reconnect to paired HID devices on boot. We note these
# platform types here as there will be different behavior expectations around
# reboot.
RECONNECT_PLATFORM_TYPES = ['CHROMEBOX', 'CHROMEBIT', 'CHROMEBASE']

# TODO(b/158336394) Realtek: Powers down during suspend due to high power usage
#                            during S3.
# TODO(b/168152910) Marvell: Powers down during suspend due to flakiness when
#                            entering suspend.  This will also skip the tests
#                            for Veyron (which don't power down right now) but
#                            reconnect tests are still enabled for that platform
#                            to check for suspend stability.
SUSPEND_POWER_DOWN_CHIPSETS = ['Realtek-RTL8822C-USB', 'MVL-8897', 'MVL-8997']

# All realtek chipsets on USB will drop its firmware and reload on
# suspend-resume unless it is connected to a peer device. This doesn't
# include RTL8822, which would reset regardless of the peer.
SUSPEND_RESET_IF_NO_PEER_CHIPSETS = ['Realtek-RTL8852A-USB']

# Models to skip since they power down on suspend.
SUSPEND_POWER_DOWN_MODELS = ['dru', 'druwl', 'dumo']

# Chipsets which do not support Bluetooth Hardware Filtering.
UNSUPPORTED_BT_HW_FILTERING_CHIPSETS = [
        'MVL-8897', 'MVL-8997', 'QCA-6174A-5-USB', 'QCA-6174A-3-UART',
        'QCA-WCN6856', 'Intel-AC7260', 'Intel-AC7265', 'Realtek-RTL8822C-USB',
        'Realtek-RTL8822C-UART', 'Realtek-RTL8852A-USB',
        'Mediatek-MTK7921-USB', 'Mediatek-MTK7921-SDIO'
]

KERNEL_LOG_LEVEL = {
        'EMERG': 0,
        'ALERT': 1,
        'CRIT': 2,
        'ERR': 3,
        'WARNING': 4,
        'NOTICE': 5,
        'INFO': 6,
        'DEBUG': 7
}

# The benchmark criterion to determine whether HID device reconnection is fast
HID_RECONNECT_TIME_MAX_SEC = 3
LE_HID_RECONNECT_TIME_MAX_SEC = 3


def method_name():
    """Get the method name of a class.

    This function is supposed to be invoked inside a class and will
    return current method name who invokes this function.

    @returns: the string of the method name inside the class.
    """
    return inspect.getouterframes(inspect.currentframe())[1][3]


def _run_method(method, method_name, *args, **kwargs):
    """Run a target method and capture exceptions if any.

    This is just a wrapper of the target method so that we do not need to
    write the exception capturing structure repeatedly. The method could
    be either a device method or a facade method.

    @param method: the method to run
    @param method_name: the name of the method

    @returns: the return value of target method() if successful.
              False otherwise.

    """
    result = False
    try:
        result = method(*args, **kwargs)
    except Exception as e:
        logging.error('%s: %s', method_name, e)
    except:
        logging.error('%s: unexpected error', method_name)
    return result


def get_bluetooth_emulated_device(btpeer, device_type):
    """Get the bluetooth emulated device object.

    @param btpeer: the Bluetooth peer device
    @param device_type : the bluetooth device type, e.g., 'MOUSE'

    @returns: the bluetooth device object

    """

    def _retry_device_method(method_name, legal_falsy_values=[]):
        """retry the emulated device's method.

        The method is invoked as device.xxxx() e.g., device.GetAdvertisedName().

        Note that the method name string is provided to get the device's actual
        method object at run time through getattr(). The rebinding is required
        because a new device may have been created previously or during the
        execution of fix_serial_device().

        Given a device's method, it is not feasible to get the method name
        through __name__ attribute. This limitation is due to the fact that
        the device is a dotted object of an XML RPC server proxy.
        As an example, with the method name 'GetAdvertisedName', we could
        derive the correspoinding method device.GetAdvertisedName. On the
        contrary, given device.GetAdvertisedName, it is not feasible to get the
        method name by device.GetAdvertisedName.__name__

        Also note that if the device method fails, we would try remediation
        step and retry the device method. The remediation steps are
         1) re-creating the serial device.
         2) reset (powercycle) the bluetooth dongle.
         3) reboot Bluetooth peer.
        If the device method still fails after these steps, we fail the test

        The default values exist for uses of this function before the options
        were added, ideally we should change zero_ok to False.

        @param method_name: the string of the method name.
        @param legal_falsy_values: Values that are falsy but might be OK.

        @returns: the result returned by the device's method if the call was
                  successful

        @raises: TestError if the devices's method fails or if repair of
                 peripheral kit fails

        """

        action_table = [('recreate' , 'Fixing the serial device'),
                        ('reset', 'Power cycle the peer device'),
                        ('reboot', 'Reboot the chamleond host')]

        for i, (action, description) in enumerate(action_table):
            logging.info('Attempt %s : %s ', i+1, method_name)

            result = _run_method(getattr(device, method_name), method_name)
            if _is_successful(result, legal_falsy_values):
                return result

            logging.error('%s failed the %s time. Attempting to %s',
                          method_name,i,description)
            if not fix_serial_device(btpeer, device, action):
                logging.info('%s failed', description)
            else:
                logging.info('%s successful', description)

        #try it last time after fix it by last action
        result = _run_method(getattr(device, method_name), method_name)
        if _is_successful(result, legal_falsy_values):
            return result

        raise error.TestError('Failed to execute %s. Bluetooth peer device is'
                              'not working' % method_name)


    if device_type not in SUPPORTED_DEVICE_TYPES:
        raise error.TestError('The device type is not supported: %s',
                              device_type)

    # Get the bluetooth device object and query some important properties.
    device = SUPPORTED_DEVICE_TYPES[device_type](btpeer)()

    # Get some properties of the kit
    # NOTE: Strings updated here must be kept in sync with Btpeer.
    device._capabilities = _retry_device_method('GetCapabilities')
    device._transports = device._capabilities["CAP_TRANSPORTS"]
    device._is_le_only = ("TRANSPORT_LE" in device._transports and
                          len(device._transports) == 1)
    device._has_pin = device._capabilities["CAP_HAS_PIN"]
    device.can_init_connection = device._capabilities["CAP_INIT_CONNECT"]

    _retry_device_method('Init')
    logging.info('device type: %s', device_type)

    device.name = _retry_device_method('GetAdvertisedName')
    logging.info('device name: %s', device.name)

    device.address = _retry_device_method('GetLocalBluetoothAddress')
    logging.info('address: %s', device.address)

    pin_falsy_values = [] if device._has_pin else [None]
    device.pin = _retry_device_method('GetPinCode', pin_falsy_values)
    logging.info('pin: %s', device.pin)

    class_falsy_values = [None] if device._is_le_only else [0]

    # Class of service is None for LE-only devices. Don't fail or parse it.
    device.class_of_service = _retry_device_method('GetClassOfService',
                                                   class_falsy_values)
    if device._is_le_only:
        parsed_class_of_service = device.class_of_service
    else:
        parsed_class_of_service = "0x%04X" % device.class_of_service
    logging.info('class of service: %s', parsed_class_of_service)

    device.class_of_device = _retry_device_method('GetClassOfDevice',
                                                  class_falsy_values)
    # Class of device is None for LE-only devices. Don't fail or parse it.
    if device._is_le_only:
        parsed_class_of_device = device.class_of_device
    else:
        parsed_class_of_device = "0x%04X" % device.class_of_device
    logging.info('class of device: %s', parsed_class_of_device)

    device.device_type = _retry_device_method('GetDeviceType')
    logging.info('device type: %s', device.device_type)

    device.authentication_mode = None
    if not device._is_le_only:
        device.authentication_mode = _retry_device_method('GetAuthenticationMode')
        logging.info('authentication mode: %s', device.authentication_mode)

    device.port = _retry_device_method('GetPort')
    logging.info('serial port: %s\n', device.port)

    return device


def recreate_serial_device(device):
    """Create and connect to a new serial device.

    @param device: the bluetooth HID device

    @returns: True if the serial device is re-created successfully.

    """
    logging.info('Remove the old serial device and create a new one.')
    if device is not None:
        try:
            device.Close()
        except:
            logging.error('failed to close the serial device.')
            return False
    try:
        device.CreateSerialDevice()
        return True
    except:
        logging.error('failed to invoke CreateSerialDevice.')
        return False


def _check_device_init(device, operation):
    # Check if the serial device could initialize, connect, and
    # enter command mode correctly.
    logging.info('Checking device status...')
    if not _run_method(device.Init, 'Init'):
        logging.info('device.Init: failed after %s', operation)
        return False
    if not device.CheckSerialConnection():
        logging.info('device.CheckSerialConnection: failed after %s', operation)
        return False
    if not _run_method(device.EnterCommandMode, 'EnterCommandMode'):
        logging.info('device.EnterCommandMode: failed after %s', operation)
        return False
    logging.info('The device is created successfully after %s.', operation)
    return True

def _reboot_btpeer(btpeer, device):
    """ Reboot Bluetooth peer device.

    Also power cycle the device since reboot may not do that.."""

    # Chameleond fizz hosts should have write protect removed and
    # set_gbb_flags set to 0 to minimize boot time
    REBOOT_SLEEP_SECS = 10
    RESET_SLEEP_SECS = 1

    # Close the bluetooth peripheral device and reboot the chameleon board.
    device.Close()
    logging.info("Powercycling the device")
    device.PowerCycle()
    time.sleep(RESET_SLEEP_SECS)
    logging.info('rebooting Bluetooth peer...')
    btpeer.reboot()

    # Every btpeer reboot would take a bit more than REBOOT_SLEEP_SECS.
    # Sleep REBOOT_SLEEP_SECS and then begin probing the btpeer board.
    time.sleep(REBOOT_SLEEP_SECS)
    return _check_device_init(device, 'reboot')

def _reset_device_power(device):
    """Power cycle the device."""
    RESET_SLEEP_SECS = 1
    try:
        if not device.PowerCycle():
            logging.info('device.PowerCycle() failed')
            return False
    except:
        logging.error('exception in device.PowerCycle')
    else:
        logging.info('device powercycled')
    time.sleep(RESET_SLEEP_SECS)
    return _check_device_init(device, 'reset')

def _is_successful(result, legal_falsy_values=[]):
    """Is the method result considered successful?

    Some method results, for example that of class_of_service, may be 0 which is
    considered a valid result. Occassionally, None is acceptable.

    The default values exist for uses of this function before the options were
    added, ideally we should change zero_ok to False.

    @param result: a method result
    @param legal_falsy_values: Values that are falsy but might be OK.

    @returns: True if bool(result) is True, or if result is 0 and zero_ok, or if
              result is None and none_ok.
    """
    truthiness_of_result = bool(result)
    return truthiness_of_result or result in legal_falsy_values


def _flag_common_failures(instance):
    """Checks if a common failure has occurred during the test run

    Scans system logs for known signs of failure. If a failure is discovered,
    it is added to the test results, to make it easier to identify common root
    causes from Stainless
    """
    had_failure = False

    for fail_tag, fail_log in COMMON_FAILURES.items():
        if instance.bluetooth_facade.messages_find(fail_tag):
            had_failure = True
            logging.error('Detected failure tag: %s', fail_tag)
            # We mark this instance's results with the discovered failure
            if type(instance.results) is dict:
                instance.results[fail_log] = True

    return had_failure


def fix_serial_device(btpeer, device, operation='reset'):
    """Fix the serial device.

    This function tries to fix the serial device by
    (1) re-creating a serial device, or
    (2) power cycling the usb port to which device is connected
    (3) rebooting the Bluetooth peeer

    Argument operation determine which of the steps above are perform

    Note that rebooting the btpeer board or resetting the device will remove
    the state on the peripheral which might cause test failures. Please use
    reset/reboot only before or after a test.

    @param btpeer: the Bluetooth peer
    @param device: the bluetooth device.
    @param operation: Recovery operation to perform 'recreate/reset/reboot'

    @returns: True if the serial device is fixed. False otherwise.

    """

    if operation == 'recreate':
        # Check the serial connection. Fix it if needed.
        if device.CheckSerialConnection():
            # The USB serial connection still exists.
            # Re-connection suffices to solve the problem. The problem
            # is usually caused by serial port change. For example,
            # the serial port changed from /dev/ttyUSB0 to /dev/ttyUSB1.
            logging.info('retry: creating a new serial device...')
            return recreate_serial_device(device)
        else:
            # Recreate the bluetooth peer device
            return _check_device_init(device, operation)

    elif operation == 'reset':
        # Powercycle the USB port where the bluetooth peer device is connected.
        # RN-42 and RN-52 share the same vid:pid so both will be powercycled.
        # This will only work on fizz host with write protection removed.
        # Note that the state on the device will be lost.
        return _reset_device_power(device)

    elif operation == 'reboot':
        # Reboot the Bluetooth peer device.
        # The device is power cycled before rebooting Bluetooth peer device
        return _reboot_btpeer(btpeer, device)

    else:
        logging.error('fix_serial_device Invalid operation %s', operation)
        return False


def retry(test_method, instance, *args, **kwargs):
    """Execute the target facade test_method(). Retry if failing the first time.

    A test_method is something like self.test_xxxx() in BluetoothAdapterTests,
    e.g., BluetoothAdapterTests.test_bluetoothd_running().

    @param test_method: the test method to retry

    @returns: True if the return value of test_method() is successful.
              False otherwise.

    """
    if _is_successful(_run_method(test_method, test_method.__name__,
                                  instance, *args, **kwargs)):
        return True

    # Try to fix the serial device if applicable.
    logging.error('%s failed at the 1st time: (%s)', test_method.__name__,
                  str(instance.results))

    # If this test does not use any attached serial device, just re-run
    # the test.
    logging.info('%s: retry the 2nd time.', test_method.__name__)
    time.sleep(1)


    if not hasattr(instance, 'use_btpeer'):
        return _is_successful(_run_method(test_method, test_method.__name__,
                                          instance, *args, **kwargs))
    for device_type in SUPPORTED_DEVICE_TYPES:
        for device in getattr(instance, 'devices')[device_type]:
            #fix_serial_device in 'recreate' mode doesn't require btpeer
            #so just pass None for convenient.
            if not fix_serial_device(None, device, "recreate"):
                return False

    logging.info('%s: retry the 2nd time.', test_method.__name__)
    return _is_successful(_run_method(test_method, test_method.__name__,
                                      instance, *args, **kwargs))


def test_retry_and_log(test_method_or_retry_flag,
                       messages_start=True,
                       messages_stop=True):
    """A decorator that logs test results, collects error messages, and retries
       on request.

    @param test_method_or_retry_flag: either the test_method or a retry_flag.
        There are some possibilities of this argument:
        1. the test_method to conduct and retry: should retry the test_method.
            This occurs with
            @test_retry_and_log
        2. the retry flag is True. Should retry the test_method.
            This occurs with
            @test_retry_and_log(True)
        3. the retry flag is False. Do not retry the test_method.
            This occurs with
            @test_retry_and_log(False)

    @param messages_start: Start collecting messages before running the test
    @param messages_stop: Stop collecting messages after running the test and
                          analyze the results.

    @returns: a wrapper of the test_method with test log. The retry mechanism
        would depend on the retry flag.

    """

    def decorator(test_method):
        """A decorator wrapper of the decorated test_method.

        @param test_method: the test method being decorated.

        @returns the wrapper of the test method.

        """
        @functools.wraps(test_method)
        def wrapper(instance, *args, **kwargs):
            """A wrapper of the decorated method.

            @param instance: an BluetoothAdapterTests instance

            @returns the result of the test method

            """
            instance.results = None
            fail_msg = None
            test_result = False
            should_raise = hasattr(instance, 'fail_fast') and instance.fail_fast

            instance.last_test_method = test_method.__name__
            syslog_captured = False

            try:
                if messages_start:
                    # Grab /var/log/messages output during test run
                    instance.bluetooth_facade.messages_start()

                if callable(test_method_or_retry_flag
                            ) or test_method_or_retry_flag:
                    test_result = retry(test_method, instance, *args, **kwargs)
                else:
                    test_result = test_method(instance, *args, **kwargs)

                if messages_stop:
                    syslog_captured = instance.bluetooth_facade.messages_stop()

                if syslog_captured:
                    had_failure = _flag_common_failures(instance)
                    instance.had_known_common_failure = any(
                            [instance.had_known_common_failure, had_failure])

                logging.debug('instance._expected_result : %s',
                              instance._expected_result)
                if instance._expected_result:
                    if test_result:
                        logging.info('[*** passed: {}]'.format(
                                test_method.__name__))
                    else:
                        fail_msg = '[--- failed: {} ({})]'.format(
                                test_method.__name__, str(instance.results))
                        logging.error(fail_msg)
                        instance.fails.append(fail_msg)
                else:
                    if test_result:
                        # The test is expected to fail; but it passed.
                        reason = 'expected fail, actually passed'
                        fail_msg = '[--- failed: {} ({})]'.format(
                                test_method.__name__, reason)
                        logging.error(fail_msg)
                        instance.fails.append(fail_msg)
                    else:
                        # The test is expected to fail; and it did fail.
                        reason = 'expected fail, actually failed'
                        logging.info('[*** passed: {} ({})]'.format(
                                test_method.__name__, reason))

            # Reset _expected_result and let the quicktest wrapper catch it.
            # These errors should skip out of the testcase entirely.
            except (error.TestNAError, error.TestError, error.TestFail):
                instance._expected_result = True
                raise

            # Next test_method should pass by default.
            instance._expected_result = True

            # Check whether we should fail fast
            if fail_msg and should_raise:
                logging.info('Fail fast')
                raise error.TestFail(instance.fails)

            return test_result

        return wrapper

    if callable(test_method_or_retry_flag):
        # If the decorator function comes with no argument like
        # @test_retry_and_log
        return decorator(test_method_or_retry_flag)
    else:
        # If the decorator function comes with an argument like
        # @test_retry_and_log(False)
        return decorator


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
        """Log the name of the wrapped method before execution"""
        logging.info('\n<... %s ...>', method.__name__)
        method(instance, *args, **kwargs)
    return wrapper


class BluetoothAdapterTests(test.test):
    """Server side bluetooth adapter tests.

    This test class tries to thoroughly verify most of the important work
    states of a bluetooth adapter.

    The various test methods are supposed to be invoked by actual autotest
    tests such as server/cros/site_tests/bluetooth_Adapter*.

    """
    version = 1
    ADAPTER_ACTION_SLEEP_SECS = 1
    ADAPTER_PAIRING_TIMEOUT_SECS = 60
    ADAPTER_CONNECTION_TIMEOUT_SECS = 30
    # Wait after connect for input device to be ready for use
    ADAPTER_HID_INPUT_DELAY = 5
    ADAPTER_DISCONNECTION_TIMEOUT_SECS = 30
    ADAPTER_PAIRING_POLLING_SLEEP_SECS = 3
    ADAPTER_DISCOVER_TIMEOUT_SECS = 60          # 30 seconds too short sometimes
    ADAPTER_DISCOVER_POLLING_SLEEP_SECS = 1
    ADAPTER_DISCOVER_NAME_TIMEOUT_SECS = 30
    ADAPTER_WAKE_ENABLE_TIMEOUT_SECS = 30

    ADAPTER_WAIT_DEFAULT_TIMEOUT_SECS = 10
    ADAPTER_POLLING_DEFAULT_SLEEP_SECS = 1

    HID_REPORT_SLEEP_SECS = 1


    DEFAULT_START_DELAY_SECS = 0
    DEFAULT_HOLD_INTERVAL_SECS = 10
    DEFAULT_HOLD_TIMEOUT_SECS = 60
    DEFAULT_HOLD_SLEEP_SECS = 1

    # Default suspend time in seconds for suspend resume.
    SUSPEND_TIME_SECS=10
    SUSPEND_ENTER_SECS=10
    RESUME_TIME_SECS=30
    RESUME_INTERNAL_TIMEOUT_SECS = 180

    # Minimum RSSI required for peer devices during testing
    MIN_RSSI = -70

    # hci0 is the default hci device if there is no external bluetooth dongle.
    EXPECTED_HCI = 'hci0'

    CLASS_OF_SERVICE_MASK = 0xFFE000
    CLASS_OF_DEVICE_MASK = 0x001FFF

    # Constants about advertising.
    DEFAULT_MIN_ADVERTISEMENT_INTERVAL_MS = 200
    DEFAULT_MAX_ADVERTISEMENT_INTERVAL_MS = 200
    ADVERTISING_INTERVAL_UNIT = 0.625

    # Error messages about advertising dbus methods.
    ERROR_FAILED_TO_REGISTER_ADVERTISEMENT = (
            'org.bluez.Error.NotPermitted: Maximum advertisements reached')
    ERROR_INVALID_ADVERTISING_INTERVALS = (
            'org.bluez.Error.InvalidArguments: Invalid arguments')

    # Supported profiles by chrome os.
    SUPPORTED_UUIDS = {
            'GATT_UUID': '00001801-0000-1000-8000-00805f9b34fb',
            'A2DP_SOURCE_UUID': '0000110a-0000-1000-8000-00805f9b34fb',
            'HFP_AG_UUID': '0000111f-0000-1000-8000-00805f9b34fb',
            'PNP_UUID': '00001200-0000-1000-8000-00805f9b34fb',
            'GAP_UUID': '00001800-0000-1000-8000-00805f9b34fb'}

    # Board list for name/ID test check. These devices don't need to be tested
    REFERENCE_BOARDS = [
            'rambi', 'nyan', 'oak', 'reef', 'yorp', 'bip', 'volteer',
            'volteer2'
    ]

    # Path for btmon logs
    BTMON_DIR_LOG_PATH = '/var/log/btmon'

    # Path for usbmon logs
    USBMON_DIR_LOG_PATH = '/var/log/usbmon'

    # Parameters for usbmon log rotation
    USBMON_SINGLE_FILE_MAX_SIZE = '10M'  # 10M bytes
    USBMON_NUM_OF_ROTATE_FILE = 2

    # The agent capability of various device types.
    # Currently all non-Fast Pair are set to NoInputNoOutput since currently
    # we don't have a way to report the displayed passkey to the device in case
    # of Passkey Entry. Therefore, use 'Just Works'.
    # Fast Pair uses DisplayYesNo because this is expected by that protocol.
    # TODO(b/181945748) update the capabilities when Passkey Entry is supported.
    AGENT_CAPABILITY = {
            'BLE_MOUSE': 'NoInputNoOutput',
            'BLE_KEYBOARD': 'NoInputNoOutput',
            'BLE_PHONE': 'NoInputNoOutput',
            'BLUETOOTH_AUDIO': 'NoInputNoOutput',
            'FAST_PAIR': 'DisplayYesNo',
            'KEYBOARD': 'NoInputNoOutput',
            'MOUSE': 'NoInputNoOutput',
    }

    def assert_on_fail(self, result, raiseNA=False):
        """ If the called function returns a false-like value, raise an error.

        Call test methods (i.e. with @test_retry_and_log) wrapped with this
        function and failures will raise instead of continuing the test.

        For example:
            self.assert_on_fail(self.test_pairing(...))

        @param result: Result of test method called.
        @param raiseNA: Whether to raise TestNAError instead of TestFail

        @raises error.TestNAError
        @raises error.TestFail
        """
        if not result:
            failure_msg = 'Assert on fail: {}'.format(self.last_test_method)
            logging.error(failure_msg)
            if raiseNA:
                raise error.TestNAError(failure_msg)
            else:
                raise error.TestFail(failure_msg)


    def expect_fail(self, test_method, *args, **kwargs):
        """Run the test_method which is expected to fail.

        Here a test means one that comes with the @test_retry_and_log
        decorator.

        In most cases, a test is expected to pass by default. However, in
        some cases, we may expect a test to fail. As an example, a test is
        expected to fail if the behavior is disallowed by the policy. In
        this case, the failure is considered a pass. The example statements
        look like

            # Set an arbitrary UUID that disallows the HID device.
            self.test_check_set_allowlist('0xabcd', True)

            # Since the HID device is disallowed above,
            # the self.test_keyboard_input_from_trace test itself would
            # fail which is expected.
            self.expect_fail(self.test_keyboard_input_from_trace,
                             device, "simple_text")

        In the log, the message would show that the keyboard input failed as

            test_keyboard_input_from_trace: InputEventRecorderError: Failed to
            find the device node of KEYBD_REF.

        As a result, the log message shows that the test conceptually passed.

            [*** passed: test_keyboard_input_from_trace (expected fail,
                                                         actually failed)]

        @param test_method: the test method to run.

        @returns: True if the test method failed; False otherwise.
        """
        self._expected_result = False
        logging.debug('self._expected_result %s', self._expected_result)
        return test_method(*args, **kwargs)


    def expect_test(self, expected_result, test_method, *args, **kwargs):
        """Run the test method and expect the test result as expected_result.

        This little helper is used to make simple the following statements

            if expected_result:
                self.test_xxx(device)
            else:
                self.expect_fail(self.test_xxx, device)

        which can be converted to

            self.expect_test(expected_result, self.test_xxx, device)

        @param expected_result: True if the test is expected to pass;
                False otherwise.
        @param test_method: the test method to run.

        @returns: True if the test result matches expected_result;
                False otherwise.
        """
        if expected_result:
            # If the test is expected to pass, just run it normally.
            return test_method(*args, **kwargs)
        else:
            # If the test is expected to fail, run it throuigh self.expect_fail
            # to handle the failure.
            return self.expect_fail(test_method, *args, **kwargs)


    # TODO(b/131170539) remove when sarien/arcada no longer have _signed
    # postfix
    def get_base_platform_name(self):
        """Returns the DUT platform name

        If the DUT is a DVT device, _signed or _unsigned may be appended
            to the device name, which we should ignore in our BT tests

        @returns: String name of the DUT's platform with _signed or
                _unsigned removed
        """

        platform = self.host.get_platform()

        return platform.replace('_signed', '').replace('_unsigned', '')

    def platform_will_reconnect_on_boot(self):
        """Indicates if we should expect DUT to automatically reconnect on boot

        Some platforms do not have built-in I/O (i.e. ChromeBox) and will
        automatically reconnect to paired HID devices on boot.

        @returns: True if platform will reconnect on boot, else False
        """

        return self.host.get_board_type() in RECONNECT_PLATFORM_TYPES

    def group_btpeers_type(self):
        """Group all Bluetooth peers by the type of their detected device."""

        # Use previously created btpeer_group instead of creating new
        if len(self.btpeer_group_copy) > 0:
            logging.info('Using previously created btpeer group')
            for device_type in SUPPORTED_DEVICE_TYPES:
                self.btpeer_group[device_type] = \
                    self.btpeer_group_copy[device_type][:]
            return

        # Create new btpeer_group
        for device_type in SUPPORTED_DEVICE_TYPES:
            self.btpeer_group[device_type] = list()
            # Create copy of btpeer_group
            self.btpeer_group_copy[device_type] = list()

        for idx, btpeer in enumerate(self.host.btpeer_list):
            for device_type,gen_device_func in SUPPORTED_DEVICE_TYPES.items():
                try:
                    device = gen_device_func(btpeer)()
                    if device.CheckSerialConnection():
                        self.btpeer_group[device_type].append(btpeer)
                        logging.info('%d-th btpeer find device %s', \
                                     idx, device_type)
                        # Create copy of btpeer_group
                        self.btpeer_group_copy[device_type].append(btpeer)
                except:
                    logging.debug('Error with initializing %s on %d-th'
                                  'btpeer', device_type, idx)
            if len(self.btpeer_group[device_type]) == 0:
                logging.error('No device is detected on %d-th btpeer', idx)

        logging.debug("self.bt_group is %s",self.btpeer_group)


    def wait_for_device(self, device, timeout=10):
        """Waits for device to become available again

        We reset raspberry pi peer between tests. This method helps us wait to
        prevent us from trying to use the device before it comes back up again.

        @param device: proxy object of peripheral device
        """

        def is_device_ready():
            """Tries to use a service of the device

            @returns: True if device is available to provide service
                      False otherwise
            """

            try:
                # Call a simple (fast) function to determine if device is online
                # and reachable. If we can query this property, we know the
                # device is available for us to use
                getattr(device, 'GetCapabilities')()

            except Exception as e:
                return False

            return True


        try:
            utils.poll_for_condition(condition=is_device_ready,
                                     desc='wait_for_device',
                                     timeout=timeout)

        except utils.TimeoutError as e:
            raise error.TestError('Peer is not available after waiting')


    def clear_raspi_device(self, device, next_device_type=None):
        """Clears a device on a raspi peer by resetting bluetooth stack

        @param device: proxy object of peripheral device
        """

        try:
            device.ResetStack(next_device_type)

        except socket.error as e:
            # Ignore conn reset, expected during stack reset
            if e.errno != errno.ECONNRESET:
                raise

        except chameleon.ChameleonConnectionError as e:
            # Ignore chameleon conn reset, expected during stack reset
            if (str(errno.ECONNRESET) not in str(e) and
                    'ResetStack' not in str(e)):
                raise
            logging.info('Ignored exception due to ResetStack: %s', str(e))

        except six.moves.http_client.BadStatusLine as e:
            # BadStatusLine occurs occasionally when chameleon
            # is restarted. We ignore it here
            logging.error('Ignoring badstatusline exception')
            pass

        # Catch generic Fault exception by rpc server, ignore
        # method not available as it indicates platform didn't
        # support method and that's ok
        except Exception as e:
            if not (e.__class__.__name__ == 'Fault' and
                'is not supported' in str(e)):
                raise

        # Ensure device is back online before continuing
        self.wait_for_device(device, timeout=30)

    def device_set_powered(self, device, powered):
        """Set raspi BT powered state.

        @param powered: Powered state to set on Raspi.
        """
        if powered:
            device.AdapterPowerOn()
        else:
            device.AdapterPowerOff()

    def get_device_rasp(self, device_num, on_start=True):
        """Get all bluetooth device objects from Bluetooth peer devices
        This method should be called only after group_btpeers_type
        @param device_num : dict of {device_type:number}, to specify the number
                            of device needed for each device_type.

        @param on_start: boolean describing whether the requested clear is for a
                            new test, or in the middle of a current one

        @returns: True if Success.
        """

        logging.info("in get_device_rasp %s onstart %s", device_num, on_start)
        total_num_devices = sum(device_num.values())
        if total_num_devices > len(self.host.btpeer_list):
            logging.error(
                    'Total number of devices %s is greater than the'
                    ' number of Bluetooth peers %s', total_num_devices,
                    len(self.host.btpeer_list))
            return False

        for device_type, number in device_num.items():
            total_num_devices += number
            if len(self.btpeer_group[device_type]) < number:
                logging.error('Number of Bluetooth peers with device type'
                      '%s is %d, which is less then needed %d', device_type,
                      len(self.btpeer_group[device_type]), number)
                return False

            for btpeer in self.btpeer_group[device_type][:number]:
                logging.info("getting emulated %s", device_type)
                device = self.reset_btpeer(btpeer, device_type, on_start)

                self.devices[device_type].append(device)

                # Remove this btpeer from btpeer_group since it is already
                # configured as a specific device
                for temp_device in SUPPORTED_DEVICE_TYPES:
                    if btpeer in self.btpeer_group[temp_device]:
                        self.btpeer_group[temp_device].remove(btpeer)

        return True

    def get_peer_device_type(self, device):
        """Determine the type of peer a device is emulating

        Sometimes it is useful to be able to flexibly determine what type of
        peripheral a device is emulating. This helper function does a reverse
        look-up to determine what type it was registered as.

        @param device: the emulated peer device

        @returns: the emulated device type if found, e.g. 'MOUSE' or
            'BLE_KEYBOARD', else None
        """

        for device_type, device_list in self.devices.items():
            if device in device_list:
                return device_type

        return None

    def get_device(self, device_type, on_start=True):
        """Get the bluetooth device object.

        @param device_type : the bluetooth device type, e.g., 'MOUSE'

        @param on_start: boolean describing whether the requested clear is for a
                            new test, or in the middle of a current one

        @returns: the bluetooth device object

        """

        self.devices[device_type].append(
                self.reset_btpeer(self.host.btpeer, device_type, on_start))

        return self.devices[device_type][-1]


    def reset_emulated_device(self, device, device_type, clear_device=True):
        """Reset the emulated device in order to be used as a different type.

        @param device: the emulated peer device to reset with new device type
        @param device_type : the new bluetooth device type, e.g., 'MOUSE'
        @param clear_device: whether to clear the device state

        @returns: the bluetooth device object

        """
        # Re-fresh device to clean state if test is starting
        if clear_device:
            self.clear_raspi_device(device, next_device_type=device_type)

        try:
            # Tell generic chameleon to bind to this device type
            device.SpecifyDeviceType(device_type)

        # Catch generic Fault exception by rpc server, ignore method not
        # available as it indicates platform didn't support method and that's
        # ok
        except Exception as e:
            if not (e.__class__.__name__ == 'Fault' and
                    'is not supported' in str(e)):
                logging.error("got exception %s", str(e))
                raise

        return device

    def reset_btpeer(self, peer, device_type, clear_device=True):
        """Reset the btpeer device in order to be used as a different type.

        @param peer: the btpeer device to reset with new device type
        @param device_type : the new bluetooth device type, e.g., 'MOUSE'
        @param clear_device: whether to clear the device state

        @returns: the bluetooth device object

        """
        device = get_bluetooth_emulated_device(peer, device_type)

        return self.reset_emulated_device(device, device_type, clear_device)

    def is_device_available(self, btpeer, device_type):
        """Determines if the named device is available on the linked peer

        @param device_type: the bluetooth HID device type, e.g., 'MOUSE'

        @returns: True if it is able to resolve the device, false otherwise
        """

        device = SUPPORTED_DEVICE_TYPES[device_type](btpeer)()
        try:
            # The proxy prevents us from checking if the object is None directly
            # so instead we call a fast method that any peripheral must support.
            # This will fail if the object over the proxy doesn't exist
            getattr(device, 'GetCapabilities')()

        except Exception as e:
            return False

        return True


    def list_devices_available(self):
        """Queries which devices are available on btpeer(s)

        @returns: dict mapping HID device types to number of supporting peers
                  available, e.g. {'MOUSE':1, 'KEYBOARD':1}
        """
        devices_available = {}
        for device_type in SUPPORTED_DEVICE_TYPES:
            for btpeer in self.host.btpeer_list:
                if self.is_device_available(btpeer, device_type):
                    devices_available[device_type] = \
                        devices_available.get(device_type, 0) + 1

        logging.debug("devices available are %s", devices_available)
        return devices_available


    def suspend_resume(self, suspend_time=SUSPEND_TIME_SECS):
        """Suspend the DUT for a while and then resume.

        @param suspend_time: the suspend time in secs
        @raises errors.TestFail if the device reboots during suspend

        """
        boot_id = self.host.get_boot_id()
        suspend = self.suspend_async(suspend_time=suspend_time)
        start_time = self.bluetooth_facade.get_device_utc_time()

        # Give the system some time to enter suspend
        self.test_suspend_and_wait_for_sleep(
                suspend, sleep_timeout=self.SUSPEND_ENTER_SECS)

        # Wait for resume - since we're not testing suspend itself, we are
        # lenient with the resume time here
        self.test_wait_for_resume(boot_id,
                                  suspend,
                                  resume_timeout=suspend_time,
                                  test_start_time=start_time)


    def reboot(self):
        """Reboot the DUT and recreate necessary processes and variables"""
        self.host.reboot()

        # We need to recreate the bluetooth_facade after a reboot.
        # Delete the proxy first so it won't delete the old one, which
        # invokes disconnection, after creating the new one.
        if hasattr(self, 'factory'):
            del self.factory
        if hasattr(self, 'bluetooth_facade'):
            del self.bluetooth_facade
        if hasattr(self, 'input_facade'):
            del self.input_facade
        self.factory = remote_facade_factory.RemoteFacadeFactory(
                self.host,
                disable_arc=True,
                no_chrome=not self.start_browser,
                force_python3=True)
        self.bluetooth_facade = self.factory.create_bluetooth_facade(
                self.floss)
        self.input_facade = self.factory.create_input_facade()

        # Re-enable debugging verbose since Chrome will set it to
        # default(disable).
        self.enable_disable_debug_log(enable=True)

        # Re-disable cellular
        self.enable_disable_cellular(enable=False)

        # Re-disable ui
        self.enable_disable_ui(enable=False)

        self.start_new_btmon()
        self.start_new_usbmon(reboot=True)


    def _wait_till_condition_holds(self, func, method_name,
                                   timeout=DEFAULT_HOLD_TIMEOUT_SECS,
                                   sleep_interval=DEFAULT_HOLD_SLEEP_SECS,
                                   hold_interval=DEFAULT_HOLD_INTERVAL_SECS,
                                   start_delay=DEFAULT_START_DELAY_SECS):
        """ Wait for the func() to hold true for a period of time


        @param func: the function to wait for.
        @param method_name: the invoking class method.
        @param timeout: number of seconds to wait before giving up.
        @param sleep_interval: the interval in seconds to sleep between
                invoking func().
        @param hold_interval: the interval in seconds for the condition to
                             remain true
        @param start_delay: interval in seconds to wait before starting

        @returns: True if the condition is met,
                  False otherwise

        """
        if start_delay > 0:
            logging.debug('waiting for %s secs before checking %s',start_delay,
                          method_name)
            time.sleep(start_delay)

        try:
            utils.poll_till_condition_holds(condition=func,
                                            timeout=timeout,
                                            sleep_interval=sleep_interval,
                                            hold_interval = hold_interval,
                                            desc=('Waiting %s' % method_name))
            return True
        except utils.TimeoutError as e:
            logging.error('%s: %s', method_name, e)
        except Exception as e:
            logging.error('%s: %s', method_name, e)
            err = 'bluetoothd possibly crashed. Check out /var/log/messages.'
            logging.error(err)
        except:
            logging.error('%s: unexpected error', method_name)
        return False


    def _wait_for_condition(self, func, method_name,
                            timeout=ADAPTER_WAIT_DEFAULT_TIMEOUT_SECS,
                            sleep_interval=ADAPTER_POLLING_DEFAULT_SLEEP_SECS,
                            start_delay=DEFAULT_START_DELAY_SECS):
        """Wait for the func() to become True.

        @param func: the function to wait for.
        @param method_name: the invoking class method.
        @param timeout: number of seconds to wait before giving up.
        @param sleep_interval: the interval in seconds to sleep between
                invoking func().
        @param start_delay: interval in seconds to wait before starting

        @returns: True if the condition is met,
                  False otherwise

        """

        if start_delay > 0:
            logging.debug('waiting for %s secs before checking %s',start_delay,
                          method_name)
            time.sleep(start_delay)

        try:
            utils.poll_for_condition(condition=func,
                                     timeout=timeout,
                                     sleep_interval=sleep_interval,
                                     desc=('Waiting %s' % method_name))
            return True
        except utils.TimeoutError as e:
            logging.error('%s: %s', method_name, e)
        except Exception as e:
            logging.error('%s: %s', method_name, e)
            err = 'bluetoothd possibly crashed. Check out /var/log/messages.'
            logging.error(err)
        except:
            logging.error('%s: unexpected error', method_name)
        return False

    def ignore_failure(instance, test_method, *args, **kwargs):
        """ Wrapper to prevent a test_method failure from failing the test batch

        Sometimes a test method needs to be used as a normal function, for its
        result. This wrapper prevent test_method failure being recorded in
        instance.fails and causing a failure of the quick test batch.

        @param test_method: test_method
        @returns: result of the test_method
        """

        original_fails = instance.fails[:]
        test_result = test_method(*args, **kwargs)
        if not test_result:
            logging.info("%s failure is ignored",test_method.__name__)
            instance.fails = original_fails
        return test_result


    def start_agent(self, device):
        """Start the pairing agent of the device if applicable.

        @param device: the peer device
        """
        dev_type = device.GetDeviceType()
        capability = self.AGENT_CAPABILITY.get(dev_type)
        if capability:
            device.StartPairingAgent(capability)


    def stop_agent(self, device):
        """Stop the pairing agent of the device if applicable.

        @param device: the peer device
        """
        dev_type = device.GetDeviceType()
        capability = self.AGENT_CAPABILITY.get(dev_type)
        if capability:
            device.StopPairingAgent()


    # -------------------------------------------------------------------
    # Adater standalone tests
    # -------------------------------------------------------------------


    def service_exists(self, service_name):
        """Checks if a service exists on the DUT

        @param service_name: name of the service

        @returns: True if service status can be queried, else False
        """

        status_cmd = 'initctl status {}'.format(service_name)
        try:
            # Querying the status of a non-existent service throws an
            # AutoservRunError exception.  If no exception is thrown, we know
            # the service exists
            self.host.run(status_cmd)

        except error.AutoservRunError:
            return False

        return True


    def service_enabled(self, service_name):
        """Checks if a service is running on the DUT

        @param service_name: name of the service

        @throws: AutoservRunError is thrown if there is no service with the
                provided name installed on the DUT.

        @returns: True if service is currently running, else False
        """

        status_cmd = 'initctl status {}'.format(service_name)
        output = self.host.run(status_cmd).stdout

        return 'start/running' in output


    def _initctl_services(self, services, command):
        """Use initctl to control service on the DUT

        @param services: list of string service names
        @param command: initctl command on the services
                        'start': to start the service
                        'stop': to stop the service
                        'restart': to restart the service

        @returns: True if services were set successfully, else False
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
                    self.host.run('initctl {} {}'.format(command, service))

                if self.service_enabled(service) != enable:
                    logging.error('Failed to set initctl service to state %d',
                                  enable)
                    return False

                if enable:
                    logging.info('Service {} enabled'.format(service))
                else:
                    logging.info('Service {} disabled'.format(service))

            elif command == 'restart':
                if self.service_enabled(service):
                    self.host.run('initctl {} {}'.format(command, service))
                else:
                    # Just start a stopped job.
                    self.host.run('initctl {} {}'.format('start', service))
                logging.info('Service {} restarted'.format(service))

            else:
                logging.error('unknown command {} on services {}'.format(
                              command, services))
                return False

        return True


    def enable_disable_services(self, services, enable):
        """Enable or disable service on the DUT

        @param services: list of string service names
        @param enable: True to enable services, False to disable

        @returns: True if services were set successfully, else False
        """
        command = 'start' if enable else 'stop'
        return self._initctl_services(services, command)


    def enable_disable_cellular(self, enable):
        """Enable cellular services on the DUT

        @param enable: True to enable cellular services
                       False to disable cellular services

        @returns: True if services were set successfully, else False
        """
        cellular_services = ['modemmanager', 'modemfwd']

        return self.enable_disable_services(cellular_services, enable)


    def enable_disable_ui(self, enable):
        """Enable UI service on the DUT

        @param enable: True to enable UI services
                       False to disable UI services

        @returns: True if services were set successfully, else False
        """
        ui_services = ['ui']

        return self.enable_disable_services(ui_services, enable)


    def restart_services(self, services):
        """Restart a service on the DUT

        @param services: the services, e.g., ['cras',]

        @returns: True if services were set successfully, else False
        """
        return self._initctl_services(services, 'restart')


    def restart_cras(self):
        """Restart the cras service on the DUT

        @returns: True if cras was restart successfully, else False
        """
        return self.restart_services(['cras', ])


    def enable_disable_debug_log(self, enable):
        """Enable or disable debug log in DUT
        @param enable: True to enable all of the debug log,
                       False to disable all of the debug log.
        """
        level = int(enable)
        self.bluetooth_facade.set_debug_log_levels(level, level)


    def start_new_btmon(self):
        """ Start a new btmon process and save the log """

        # Kill all btmon process before creating a new one
        self.host.run('pkill btmon || true')

        # Make sure the directory exists
        self.host.run('mkdir -p %s' % self.BTMON_DIR_LOG_PATH)

        # Time format. Ex, 2020_02_20_17_52_45
        now = time.strftime("%Y_%m_%d_%H_%M_%S")
        file_name = 'btsnoop_%s' % now
        self.host.run_background('btmon -SAw %s/%s' % (self.BTMON_DIR_LOG_PATH,
                                                       file_name))

    def start_new_usbmon(self, reboot=False):
        """ Start a new USBMON process and save the log

        @param reboot: True to indicate we are starting new usbmon on reboot
                       False otherwise
        """

        # Kill all usbmon process before creating a new one
        self.host.run('pkill tcpdump || true')

        # Delete usbmon logs from previous tests unless we are starting another
        # usbmon because of reboot.
        if not reboot:
            self.host.run('rm -f %s/*' % (self.USBMON_DIR_LOG_PATH))

        # Make sure the directory exists
        self.host.run('mkdir -p %s' % self.USBMON_DIR_LOG_PATH)

        # Time format. Ex, 2020_02_20_17_52_45
        now = time.strftime("%Y_%m_%d_%H_%M_%S")
        file_name = 'usbmon_%s' % now
        self.host.run_background('tcpdump -i usbmon0 -w %s/%s -C %s -W %d' %
                                 (self.USBMON_DIR_LOG_PATH, file_name,
                                  self.USBMON_SINGLE_FILE_MAX_SIZE,
                                  self.USBMON_NUM_OF_ROTATE_FILE))


    def log_message(self, msg):
        """ Write a string to log."""
        self.bluetooth_facade.log_message(msg)

    def is_wrt_supported(self):
        """ Check if Bluetooth adapter support WRT logs. """
        return self.bluetooth_facade.is_wrt_supported()

    def enable_wrt_logs(self):
        """ Enable WRT logs from Intel Adapters."""
        return self.bluetooth_facade.enable_wrt_logs()

    def collect_wrt_logs(self):
        """ Collect WRT logs from Intel Adapters."""
        return self.bluetooth_facade.collect_wrt_logs()

    def get_num_connected_devices(self):
        """ Return number of remote devices currently connected to the DUT.

        @returns: The number of devices known to bluez with the Connected
            property active
        """

        num_connected_devices = 0
        for dev in self.bluetooth_facade.get_devices():
            if dev and dev.get('Connected', 0):
                num_connected_devices += 1

        return num_connected_devices

    @test_retry_and_log
    def test_bluetoothd_running(self):
        """Test that bluetoothd is running."""
        return self.bluetooth_facade.is_bluetoothd_running()


    @test_retry_and_log
    def test_start_bluetoothd(self):
        """Test that bluetoothd could be started successfully."""
        return self.bluetooth_facade.start_bluetoothd()


    @test_retry_and_log
    def test_stop_bluetoothd(self):
        """Test that bluetoothd could be stopped successfully."""
        return self.bluetooth_facade.stop_bluetoothd()


    @test_retry_and_log
    def test_has_adapter(self):
        """Verify that there is an adapter. This will return True only if both
        the kernel and bluetooth daemon see the adapter.
        """
        return self.bluetooth_facade.has_adapter()

    @test_retry_and_log
    def test_adapter_work_state(self):
        """Test that the bluetooth adapter is in the correct working state.

        This includes that the adapter is detectable, is powered on,
        and its hci device is hci0.
        """
        has_adapter = self.bluetooth_facade.has_adapter()
        is_powered_on = self._wait_for_condition(
                self.bluetooth_facade.is_powered_on, method_name())
        hci = self.bluetooth_facade.get_hci() == self.EXPECTED_HCI
        self.results = {
                'has_adapter': has_adapter,
                'is_powered_on': is_powered_on,
                'hci': hci}
        return all(self.results.values())

    @test_retry_and_log(False)
    def test_adapter_wake_enabled(self):
        """Test that the bluetooth adapter is wakeup enabled.
        """
        wake_enabled = self._wait_for_condition(
                self.bluetooth_facade.is_wake_enabled, method_name(),
                timeout=self.ADAPTER_WAKE_ENABLE_TIMEOUT_SECS)

        self.results = { 'wake_enabled': wake_enabled }
        return any(self.results.values())

    @test_retry_and_log(False)
    def test_device_wake_allowed(self, device_address):
        """Test that given device can wake the system."""
        self.results = {
                'Wake allowed':
                self.bluetooth_facade.get_device_property(
                        device_address, 'WakeAllowed')
        }

        return all(self.results.values())

    @test_retry_and_log(False)
    def test_device_wake_not_allowed(self, device_address):
        """Test that given device cannot wake the system."""
        self.results = {
                'Wake not allowed':
                not self.bluetooth_facade.get_device_property(
                        device_address, 'WakeAllowed')
        }

        return all(self.results.values())

    @test_retry_and_log(False)
    def test_adapter_set_wake_disabled(self):
        """Disable wake and verify it was written. """
        success = self.bluetooth_facade.set_wake_enabled(False)
        self.results = { 'disable_wake': success }
        return all(self.results.values())

    @test_retry_and_log
    def test_power_on_adapter(self):
        """Test that the adapter could be powered on successfully."""
        power_on = self.bluetooth_facade.set_powered(True)
        is_powered_on = self._wait_for_condition(
                self.bluetooth_facade.is_powered_on, method_name())

        self.results = {'power_on': power_on, 'is_powered_on': is_powered_on}
        return all(self.results.values())


    @test_retry_and_log
    def test_power_off_adapter(self):
        """Test that the adapter could be powered off successfully."""
        power_off = self.bluetooth_facade.set_powered(False)
        is_powered_off = self._wait_for_condition(
                lambda: not self.bluetooth_facade.is_powered_on(),
                method_name())

        self.results = {
                'power_off': power_off,
                'is_powered_off': is_powered_off}
        return all(self.results.values())


    @test_retry_and_log
    def test_reset_on_adapter(self):
        """Test that the adapter could be reset on successfully.

        This includes restarting bluetoothd, and removing the settings
        and cached devices.
        """
        reset_on = self.bluetooth_facade.reset_on()
        is_powered_on = self._wait_for_condition(
                self.bluetooth_facade.is_powered_on, method_name())

        self.results = {'reset_on': reset_on, 'is_powered_on': is_powered_on}
        return all(self.results.values())


    @test_retry_and_log
    def test_reset_off_adapter(self):
        """Test that the adapter could be reset off successfully.

        This includes restarting bluetoothd, and removing the settings
        and cached devices.
        """
        reset_off = self.bluetooth_facade.reset_off()
        is_powered_off = self._wait_for_condition(
                lambda: not self.bluetooth_facade.is_powered_on(),
                method_name())

        self.results = {
                'reset_off': reset_off,
                'is_powered_off': is_powered_off}
        return all(self.results.values())


    def test_is_powered_off(self):
        """Check if the adapter is powered off."""
        is_powered_off = not self.bluetooth_facade.is_powered_on()
        self.results = {'is_powered_off': is_powered_off}
        return all(self.results.values())


    @test_retry_and_log(False)
    def test_is_facade_valid(self):
        """Checks whether the bluetooth facade is in a good state.

        If bluetoothd restarts (i.e. due to a crash), the object proxies will no
        longer be valid (because the session will be closed). Check whether the
        session failed and wait for a new session if it did.
        """
        initially_ok = self.bluetooth_facade.is_bluetoothd_valid()
        bluez_started = initially_ok or self.bluetooth_facade.start_bluetoothd()

        if not initially_ok:
            self.bluetooth_facade.update_adapter_properties()

        self.results = {
                'initially_ok': initially_ok,
                'bluez_started': bluez_started
        }
        return all(self.results.values())


    @test_retry_and_log(False)
    def test_is_adapter_valid(self):
        """Verify the bluetooth adapter is retrievable at test start

        @raises: error.TestNAError if we fail to retrieve the adapter on
                    an unsupported chipset
                 error.TestFail if we fail to retrieve the adapter on any other
                    platform

        @returns: True if the adapter was located properly
        """

        if not self.bluetooth_facade.has_adapter():
            logging.error('No adapter available, rebooting to recover')

            self.reboot()

            chipset = self.get_chipset_name()

            if not chipset:
                raise error.TestFail('Unknown adapter is missing')

            # A missing adapter is a rare but known issue on several platforms
            # that have no vendor support (b/169328792). Since there is no fix
            # possible, we forgive these failures by raising a TestNA.
            if chipset in UNSUPPORTED_CHIPSETS:
                raise error.TestNAError('Unsupported adapter is missing')

            raise error.TestFail('Adapter is missing')

        return True

    @test_retry_and_log
    def test_UUIDs(self):
        """Test that basic profiles are supported."""
        adapter_UUIDs = self.bluetooth_facade.get_UUIDs()
        self.results = [uuid for uuid in self.SUPPORTED_UUIDS.values()
                        if uuid not in adapter_UUIDs]
        return not bool(self.results)


    @test_retry_and_log
    def test_start_discovery(self):
        """Test that the adapter could start discovery."""
        start_discovery, _ = self.bluetooth_facade.start_discovery()
        is_discovering = self._wait_for_condition(
                self.bluetooth_facade.is_discovering, method_name())

        self.results = {
                'start_discovery': start_discovery,
                'is_discovering': is_discovering}
        return all(self.results.values())

    @test_retry_and_log(False)
    def test_is_discovering(self):
        """Test that the adapter is already discovering."""
        is_discovering = self._wait_for_condition(
                self.bluetooth_facade.is_discovering, method_name())

        self.results = {'is_discovering': is_discovering}
        return all(self.results.values())

    @test_retry_and_log
    def test_stop_discovery(self):
        """Test that the adapter could stop discovery."""
        if not self.bluetooth_facade.is_discovering():
            return True

        stop_discovery, _ = self.bluetooth_facade.stop_discovery()
        is_not_discovering = self._wait_for_condition(
                lambda: not self.bluetooth_facade.is_discovering(),
                method_name())

        self.results = {
                'stop_discovery': stop_discovery,
                'is_not_discovering': is_not_discovering}
        return all(self.results.values())


    @test_retry_and_log
    def test_discoverable(self):
        """Test that the adapter could be set discoverable."""
        set_discoverable = self.bluetooth_facade.set_discoverable(True)
        is_discoverable = self._wait_for_condition(
                self.bluetooth_facade.is_discoverable, method_name())

        self.results = {
                'set_discoverable': set_discoverable,
                'is_discoverable': is_discoverable}
        return all(self.results.values())

    @test_retry_and_log(False)
    def test_is_discoverable(self):
        """Test that the adapter is discoverable."""
        is_discoverable = self._wait_for_condition(
                self.bluetooth_facade.is_discoverable, method_name())

        self.results = {'is_discoverable': is_discoverable}
        return all(self.results.values())


    def _test_timeout_property(self, set_property, check_property, set_timeout,
                              get_timeout, property_name,
                              timeout_values = [0, 60, 180]):
        """Common method to test (Discoverable/Pairable)Timeout .

        This is used to test
        - DiscoverableTimeout property
        - PairableTimeout property

        The test performs the following
           - Set PropertyTimeout
           - Read PropertyTimeout and make sure values match
           - Set adapter propety
           - In a loop check if property is active
           - Test fails property is false before timeout
           - Test fails property is True after timeout
           Repeat the test for different values for timeout

           Note : Value of 0 mean it never timeouts, so the test will
                 end after 30 seconds.
        """
        def check_timeout(timeout):
            """Check for timeout value in loop while recording failures."""
            actual_timeout = get_timeout()
            if timeout != actual_timeout:
                logging.debug('%s timeout value read %s does not '
                              'match value set %s, yet', property_name,
                              actual_timeout, timeout)
                return False
            else:
                return True

        def _test_timeout_property(timeout):
            # minium time after timeout before checking property
            MIN_DELTA_SECS = 3
            # Time between checking  property
            WAIT_TIME_SECS = 2

            # Set and read back the timeout value
            if not set_timeout(timeout):
                logging.error('Setting the %s timeout failed',property_name)
                return False


            if not self._wait_for_condition(lambda : check_timeout(timeout),
                                            'check_'+property_name):
                logging.error('checking %s_timeout value timed out',
                              property_name)
                return False

            #
            # Check that the timeout works
            # Check property is true until timeout
            # and then it is not

            property_set = set_property(True)
            property_is_true = self._wait_for_condition(check_property,
                                                        method_name())

            self.results = { 'set_%s' % property_name : property_set,
                             'is_%s' % property_name: property_is_true}
            logging.debug(self.results)

            if not all(self.results.values()):
                logging.error('Setting %s failed',property_name)
                return False

            start_time = time.time()
            while True:
                time.sleep(WAIT_TIME_SECS)
                cur_time = time.time()
                property_set = check_property()
                time_elapsed = cur_time - start_time

                # Ignore check_property results made near the timeout
                # to avoid spurious failures.
                if abs(int(timeout - time_elapsed)) < MIN_DELTA_SECS:
                    continue

                # Timeout of zero seconds mean that the adapter never times out
                # Check for 30 seconds and then exit the test.
                if timeout == 0:
                    if not property_set:
                        logging.error('Adapter is not %s after %.2f '
                                      'secs with a timeout of zero ',
                                      property_name, time_elapsed)
                        return False
                    elif time_elapsed > 30:
                        logging.debug('Adapter %s after %.2f seconds '
                                      'with timeout of zero as expected' ,
                                      property_name, time_elapsed)
                        return True
                    continue

                #
                # Check if property is true till timeout ends and
                # false afterwards
                #
                if time_elapsed < timeout:
                    if not property_set:
                        logging.error('Adapter is not %s after %.2f '
                                      'secs before timeout of %.2f',
                                      property_name, time_elapsed, timeout)
                        return False
                else:
                    if property_set:
                        logging.error('Adapter is still %s after '
                                      ' %.2f secs with timeout of %.2f',
                                      property_name, time_elapsed, timeout)
                        return False
                    else:
                        logging.debug('Adapter not %s after %.2f '
                                      'secs with timeout of %.2f as expected ',
                                      property_name, time_elapsed, timeout)
                        return True

        default_value = check_property()
        default_timeout = get_timeout()

        result = []
        try:
            for timeout in timeout_values:
                result.append(_test_timeout_property(timeout))
            logging.debug("Test returning %s", all(result))
            return all(result)
        except:
            logging.error("exception in test_%s_timeout",property_name)
            raise
        finally:
            # Set the property back to default value permanently before
            # exiting the test
            set_timeout(0)
            set_property(default_value)
            # Set the timeout back to default value before exiting the test
            set_timeout(default_timeout)


    @test_retry_and_log
    def test_discoverable_timeout(self, timeout_values = [0, 60, 180]):
        """Test adapter dbus property DiscoverableTimeout."""
        return self._test_timeout_property(
            set_property = self.bluetooth_facade.set_discoverable,
            check_property = self.bluetooth_facade.is_discoverable,
            set_timeout = self.bluetooth_facade.set_discoverable_timeout,
            get_timeout = self.bluetooth_facade.get_discoverable_timeout,
            property_name = 'discoverable',
            timeout_values = timeout_values)

    @test_retry_and_log
    def test_pairable_timeout(self, timeout_values = [0, 60, 180]):
        """Test adapter dbus property PairableTimeout."""
        return self._test_timeout_property(
            set_property = self.bluetooth_facade.set_pairable,
            check_property = self.bluetooth_facade.is_pairable,
            set_timeout = self.bluetooth_facade.set_pairable_timeout,
            get_timeout = self.bluetooth_facade.get_pairable_timeout,
            property_name = 'pairable',
            timeout_values = timeout_values)


    @test_retry_and_log
    def test_nondiscoverable(self):
        """Test that the adapter could be set non-discoverable."""
        set_nondiscoverable = self.bluetooth_facade.set_discoverable(False)
        is_nondiscoverable = self._wait_for_condition(
                lambda: not self.bluetooth_facade.is_discoverable(),
                method_name())

        self.results = {
                'set_nondiscoverable': set_nondiscoverable,
                'is_nondiscoverable': is_nondiscoverable}
        return all(self.results.values())


    @test_retry_and_log
    def test_pairable(self):
        """Test that the adapter could be set pairable."""
        set_pairable = self.bluetooth_facade.set_pairable(True)
        is_pairable = self._wait_for_condition(
                self.bluetooth_facade.is_pairable, method_name())

        self.results = {
                'set_pairable': set_pairable,
                'is_pairable': is_pairable}
        return all(self.results.values())


    @test_retry_and_log
    def test_nonpairable(self):
        """Test that the adapter could be set non-pairable."""
        set_nonpairable = self.bluetooth_facade.set_pairable(False)
        is_nonpairable = self._wait_for_condition(
                lambda: not self.bluetooth_facade.is_pairable(), method_name())

        self.results = {
                'set_nonpairable': set_nonpairable,
                'is_nonpairable': is_nonpairable}
        return all(self.results.values())


    @test_retry_and_log(False)
    def test_check_valid_adapter_id(self):
        """Fail if the Bluetooth ID is not in the correct format.

        @returns True if adapter ID follows expected format, False otherwise
        """

        device = self.get_base_platform_name()
        adapter_info = self.get_adapter_properties()

        # Don't complete test if this is a reference board
        if device in self.REFERENCE_BOARDS:
            return True

        modalias = adapter_info['Modalias']
        logging.debug('Saw Bluetooth ID of: %s', modalias)

        # Valid Device ID is:
        # <00E0(Google)>/<C405(Chrome OS)>/<non-zero versionNumber>
        bt_format = 'bluetooth:v00E0pC405d(?!0000)'

        if not re.match(bt_format, modalias):
            return False

        return True


    @test_retry_and_log(False)
    def test_check_valid_alias(self):
        """Fail if the Bluetooth alias is not in the correct format.

        @returns True if adapter alias follows expected format, False otherwise
        """

        device = self.get_base_platform_name()
        adapter_info = self.get_adapter_properties()

        # Don't complete test if this is a reference board
        if device in self.REFERENCE_BOARDS:
            return True

        alias = adapter_info['Alias']
        logging.debug('Saw Bluetooth Alias of: %s', alias)

        device_type = self.host.get_board_type().lower()
        alias_format = '%s_[a-z0-9]{4}' % device_type

        self.results = {}

        alias_was_correct = True
        if not re.match(alias_format, alias.lower()):
            alias_was_correct = False
            logging.info('unexpected alias %s found', alias)
            self.results['alias_found'] = alias

        self.results['alias_was_correct'] = alias_was_correct
        return all(self.results.values())


    # -------------------------------------------------------------------
    # Tests about general discovering, pairing, and connection
    # -------------------------------------------------------------------


    @test_retry_and_log(False)
    def test_discover_device(self,
                             device_address,
                             start_discovery=True,
                             stop_discovery=True):
        """Test that the adapter could discover the specified device address.

        @param device_address: Address of the device.
        @param start_discovery: Whether to start discovery. Set to False if you
                                call start_discovery before calling this.
        @param stop_discovery: Whether to stop discovery at the end. If this is
                               set to False, make sure to call
                               test_stop_discovery afterwards.

        @returns: True if the device is found. False otherwise.

        """
        discovery_stopped = False
        is_not_discovering = False
        device_discovered = False
        # If start discovery is not set, discovery must already be started
        discovery_started = not start_discovery
        has_device = self.bluetooth_facade.has_device

        if start_discovery:
            if has_device(device_address):
                # Before starting a new discovery, remove the found device since
                # it is likely to be a temporary device, and we don't know when
                # it will be removed by bluez. Therefore, remove it and re-find
                # the device to ensure the device object exists for the
                # following test, e.g. test_pairing.
                logging.debug('Removing device %s to restart temporary timer',
                              device_address)
                self.bluetooth_facade.remove_device_object(device_address)

            discovery_started = self.bluetooth_facade.start_discovery()

        if discovery_started:
            try:
                utils.poll_for_condition(
                        condition=(lambda: has_device(device_address)),
                        timeout=self.ADAPTER_DISCOVER_TIMEOUT_SECS,
                        sleep_interval=self.
                        ADAPTER_DISCOVER_POLLING_SLEEP_SECS,
                        desc='Waiting for discovering %s' % device_address)
                device_discovered = True
            except utils.TimeoutError as e:
                logging.error('test_discover_device: %s', e)
            except Exception as e:
                logging.error('test_discover_device: %s', e)
                err = ('bluetoothd probably crashed.'
                       'Check out /var/log/messages')
                logging.error(err)
            except:
                logging.error('test_discover_device: unexpected error')

        if start_discovery and stop_discovery:
            discovery_stopped, _ = self.bluetooth_facade.stop_discovery()
            is_not_discovering = self._wait_for_condition(
                    lambda: not self.bluetooth_facade.is_discovering(),
                    method_name())

        self.results = {
                'should_start_discovery': start_discovery,
                'should_stop_discovery': stop_discovery,
                'start_discovery': discovery_started,
                'stop_discovery': discovery_stopped,
                'is_not_discovering': is_not_discovering,
                'device_discovered': device_discovered}

        # Make sure a discovered device properly started and stopped discovery
        device_found = device_discovered and (discovery_stopped
                                              and is_not_discovering
                                              if stop_discovery else True)

        return device_found


    def _test_discover_by_device(self, device):
        return device.Discover(self.bluetooth_facade.address)

    @test_retry_and_log(False, messages_start=False, messages_stop=False)
    def test_discover_by_device(self, device):
        """Test that the device could discover the adapter address.

        @param device: Meta device to represent peer device.

        @returns: True if the adapter is found by the device.
        """
        adapter_discovered = False
        discover_by_device = self._test_discover_by_device
        discovered_initially = discover_by_device(device)

        if not discovered_initially:
            try:
                utils.poll_for_condition(
                        condition=(lambda: discover_by_device(device)),
                        timeout=self.ADAPTER_DISCOVER_TIMEOUT_SECS,
                        sleep_interval=
                        self.ADAPTER_DISCOVER_POLLING_SLEEP_SECS,
                        desc='Waiting for adapter to be discovered')
                adapter_discovered = True
            except utils.TimeoutError as e:
                logging.error('test_discover_by_device: %s', e)
            except Exception as e:
                logging.error('test_discover_by_device: %s', e)
                err = ('bluetoothd probably crashed.'
                       'Check out /var/log/messages')
                logging.error(err)
            except:
                logging.error('test_discover_by_device: unexpected error')

        self.results = {
            'adapter_discovered_initially': discovered_initially,
            'adapter_discovered': adapter_discovered
        }
        return any(self.results.values())

    @test_retry_and_log(False, messages_start=False, messages_stop=False)
    def test_discover_by_device_fails(self, device):
        """Test that the device could not discover the adapter address.

        @param device: Meta device to represent peer device.

        @returns False if the adapter is found by the device.
        """
        self.results = {
                'adapter_discovered': self._test_discover_by_device(device)
        }
        return not any(self.results.values())

    @test_retry_and_log(False, messages_start=False, messages_stop=False)
    def test_device_set_discoverable(self, device, discoverable):
        """Test that we could set the peer device to discoverable. """
        try:
            device.SetDiscoverable(discoverable)
        except:
            return False

        return True

    @test_retry_and_log
    def test_pairing(self, device_address, pin, trusted=True):
        """Test that the adapter could pair with the device successfully.

        @param device_address: Address of the device.
        @param pin: pin code to pair with the device.
        @param trusted: indicating whether to set the device trusted.

        @returns: True if pairing succeeds. False otherwise.

        """

        def _pair_device():
            """Pair to the device.

            @returns: True if it could pair with the device. False otherwise.

            """
            return self.bluetooth_facade.pair_legacy_device(
                    device_address, pin, trusted,
                    self.ADAPTER_PAIRING_TIMEOUT_SECS)


        def _verify_connection_info():
            """Verify that connection info to device is retrievable.

            @returns: True if the connection info is retrievable.
                      False otherwise.
            """
            return (self.bluetooth_facade.get_connection_info(device_address)
                    is not None)

        def _verify_connected():
            """Verify the device is connected.

            @returns: True if the device is connected, False otherwise.
            """
            return self.bluetooth_facade.device_is_connected(device_address)

        has_device = False
        paired = False
        connected = False
        connection_info_retrievable = False
        connected_devices = self.get_num_connected_devices()

        if self.bluetooth_facade.has_device(device_address):
            has_device = True
            try:
                utils.poll_for_condition(
                        condition=_pair_device,
                        timeout=self.ADAPTER_PAIRING_TIMEOUT_SECS,
                        sleep_interval=self.ADAPTER_PAIRING_POLLING_SLEEP_SECS,
                        desc='Waiting for pairing %s' % device_address)
                paired = True
            except utils.TimeoutError as e:
                logging.error('test_pairing: %s', e)
            except:
                logging.error('test_pairing: unexpected error')

            connection_info_retrievable = _verify_connection_info()
            connected = _verify_connected()

        self.results = {
                'has_device': has_device,
                'paired': paired,
                'connected': connected,
                'connection_info_retrievable': connection_info_retrievable,
                'connection_num': connected_devices + 1
        }

        return all(self.results.values())

    @test_retry_and_log
    def test_remove_pairing(self, device_address):
        """Test that the adapter could remove the paired device.

        @param device_address: Address of the device.

        @returns: True if the device is removed successfully. False otherwise.

        """
        device_is_paired_initially = self.bluetooth_facade.device_is_paired(
                device_address)
        remove_pairing = False
        pairing_removed = False

        if device_is_paired_initially:
            remove_pairing = self.bluetooth_facade.remove_device_object(
                    device_address)
            pairing_removed = not self.bluetooth_facade.device_is_paired(
                    device_address)

        self.results = {
                'device_is_paired_initially': device_is_paired_initially,
                'remove_pairing': remove_pairing,
                'pairing_removed': pairing_removed}
        return all(self.results.values())


    def test_set_trusted(self, device_address, trusted=True):
        """Test whether the device with the specified address is trusted.

        @param device_address: Address of the device.
        @param trusted : True or False indicating if trusted is expected.

        @returns: True if the device's "Trusted" property is as specified;
                  False otherwise.

        """

        set_trusted = self.bluetooth_facade.set_trusted(
                device_address, trusted)

        actual_trusted = self.bluetooth_facade.get_device_property(
                                device_address, 'Trusted')

        self.results = {
                'set_trusted': set_trusted,
                'actual trusted': actual_trusted,
                'expected trusted': trusted}
        return actual_trusted == trusted


    @test_retry_and_log
    def test_connection_by_adapter(self, device_address):
        """Test that the adapter of dut could connect to the device successfully

        It is the caller's responsibility to pair to the device before
        doing connection.

        @param device_address: Address of the device.

        @returns: True if connection is performed. False otherwise.

        """

        def _connect_device():
            """Connect to the device.

            @returns: True if it could connect to the device. False otherwise.

            """
            return self.bluetooth_facade.connect_device(device_address)


        has_device = False
        connected = False
        if self.bluetooth_facade.has_device(device_address):
            has_device = True
            try:
                utils.poll_for_condition(
                        condition=_connect_device,
                        timeout=self.ADAPTER_PAIRING_TIMEOUT_SECS,
                        sleep_interval=self.ADAPTER_PAIRING_POLLING_SLEEP_SECS,
                        desc='Waiting for connecting to %s' % device_address)
                connected = True
            except utils.TimeoutError as e:
                logging.error('test_connection_by_adapter: %s', e)
            except:
                logging.error('test_connection_by_adapter: unexpected error')

        self.results = {'has_device': has_device, 'connected': connected}
        return all(self.results.values())


    @test_retry_and_log
    def test_disconnection_by_adapter(self, device_address):
        """Test that the adapter of dut could disconnect the device successfully

        @param device_address: Address of the device.

        @returns: True if disconnection is performed. False otherwise.

        """
        return self.bluetooth_facade.disconnect_device(device_address)


    def _enter_command_mode(self, device):
        """Let the device enter command mode.

        Before using the device, need to call this method to make sure
        it is in the command mode.

        @param device: the bluetooth HID device

        @returns: True if successful. False otherwise.

        """
        result = _is_successful(_run_method(device.EnterCommandMode,
                                            'EnterCommandMode'))
        if not result:
            logging.error('EnterCommandMode failed')
        return result


    @test_retry_and_log
    def test_connection_by_device(
            self, device, post_connection_delay=ADAPTER_HID_INPUT_DELAY):
        """Test that the device could connect to the adapter successfully.

        This emulates the behavior that a device may initiate a
        connection request after waking up from power saving mode.

        @param device: the bluetooth HID device
        @param post_connection_delay: the delay introduced post connection to
                                      allow profile functionality to be ready

        @returns: True if connection is performed correctly by device and
                  the adapter also enters connection state.
                  False otherwise.

        """
        if not self._enter_command_mode(device):
            return False

        method_name = 'test_connection_by_device'
        connection_by_device = False
        adapter_address = self.bluetooth_facade.address
        try:
            connection_by_device = device.ConnectToRemoteAddress(
                adapter_address)
        except Exception as e:
            logging.error('%s (device): %s', method_name, e)
        except:
            logging.error('%s (device): unexpected error', method_name)

        connection_seen_by_adapter = False
        device_address = device.address
        device_is_connected = self.bluetooth_facade.device_is_connected
        try:
            utils.poll_for_condition(
                    condition=lambda: device_is_connected(device_address),
                    timeout=self.ADAPTER_CONNECTION_TIMEOUT_SECS,
                    desc=('Waiting for connection from %s' % device_address))
            connection_seen_by_adapter = True

            # Although the connect may be complete, it can take a few
            # seconds for the input device to be ready for use
            time.sleep(post_connection_delay)
        except utils.TimeoutError as e:
            logging.error('%s (adapter): %s', method_name, e)
        except:
            logging.error('%s (adapter): unexpected error', method_name)

        self.results = {
                'connection_by_device': connection_by_device,
                'connection_seen_by_adapter': connection_seen_by_adapter}
        return all(self.results.values())

    @test_retry_and_log(True, messages_start=False, messages_stop=False)
    def test_connection_by_device_only(self, device, adapter_address):
        """Test that the device could connect to adapter successfully.

        This is a modified version of test_connection_by_device that only
        communicates with the peer device and not the host (in case the host is
        suspended for example).

        @param device: the bluetooth peer device
        @param adapter_address: address of the adapter

        @returns: True if the connection was established by the device or False.
        """
        connected = device.ConnectToRemoteAddress(adapter_address)
        if connected:
            # Although the connect may be complete, it can take a few
            # seconds for the input device to be ready for use
            time.sleep(self.ADAPTER_HID_INPUT_DELAY)

        self.results = {
            'connection_by_device': connected
        }

        return all(self.results.values())


    @test_retry_and_log
    def test_disconnection_by_device(self, device):
        """Test that the device could disconnect the adapter successfully.

        This emulates the behavior that a device may initiate a
        disconnection request before going into power saving mode.

        Note: should not try to enter command mode in this method. When
              a device is connected, there is no way to enter command mode.
              One could just issue a special disconnect command without
              entering command mode.

        @param device: the bluetooth HID device

        @returns: True if disconnection is performed correctly by device and
                  the adapter also observes the disconnection.
                  False otherwise.

        """
        # TODO(b/182864322) - remove the following statement when the bug
        # is fixed.
        device.SetRemoteAddress(self.bluetooth_facade.address)

        method_name = 'test_disconnection_by_device'
        disconnection_by_device = False
        try:
            device.Disconnect()
            disconnection_by_device = True
        except Exception as e:
            logging.error('%s (device): %s', method_name, e)
        except:
            logging.error('%s (device): unexpected error', method_name)

        disconnection_seen_by_adapter = False
        device_address = device.address
        device_is_connected = self.bluetooth_facade.device_is_connected
        try:
            utils.poll_for_condition(
                    condition=lambda: not device_is_connected(device_address),
                    timeout=self.ADAPTER_DISCONNECTION_TIMEOUT_SECS,
                    desc=('Waiting for disconnection from %s' % device_address))
            disconnection_seen_by_adapter = True
        except utils.TimeoutError as e:
            logging.error('%s (adapter): %s', method_name, e)
        except:
            logging.error('%s (adapter): unexpected error', method_name)

        self.results = {
                'disconnection_by_device': disconnection_by_device,
                'disconnection_seen_by_adapter': disconnection_seen_by_adapter}
        return all(self.results.values())


    @test_retry_and_log(False)
    def test_device_is_connected(
            self,
            device_address,
            timeout=ADAPTER_CONNECTION_TIMEOUT_SECS,
            sleep_interval=ADAPTER_PAIRING_POLLING_SLEEP_SECS):
        """Test that device address given is currently connected.

        @param device_address: Address of the device.
        @param timeout: maximum number of seconds to wait
        @param sleep_interval: time to sleep between polls

        @returns: True if the device is connected.
                  False otherwise.
        """

        def _is_connected():
            """Test if device is connected.

            @returns: True if device is connected. False otherwise.

            """
            return self.bluetooth_facade.device_is_connected(device_address)

        method_name = 'test_device_is_connected'
        has_device = False
        connected = False
        if self.bluetooth_facade.has_device(device_address):
            has_device = True
            try:
                utils.poll_for_condition(
                        condition=_is_connected,
                        timeout=timeout,
                        sleep_interval=sleep_interval,
                        desc='Waiting to check connection to %s' %
                        device_address)
                connected = True
            except utils.TimeoutError as e:
                logging.error('%s: %s', method_name, e)
            except:
                logging.error('%s: unexpected error', method_name)
        self.results = {'has_device': has_device, 'connected': connected}
        return all(self.results.values())


    @test_retry_and_log(False)
    def test_device_is_not_connected(self, device_address):
        """Test that device address given is NOT currently connected.

        @param device_address: Address of the device.

        @returns: True if the device is NOT connected.
                  False otherwise.

        """

        def _is_not_connected():
            """Test if device is not connected.

            @returns: True if device is not connected. False otherwise.

            """
            return not self.bluetooth_facade.device_is_connected(
                    device_address)


        method_name = 'test_device_is_not_connected'
        not_connected = False
        if self.bluetooth_facade.has_device(device_address):
            try:
                utils.poll_for_condition(
                        condition=_is_not_connected,
                        timeout=self.ADAPTER_CONNECTION_TIMEOUT_SECS,
                        sleep_interval=self.ADAPTER_PAIRING_POLLING_SLEEP_SECS,
                        desc='Waiting to check connection to %s' %
                              device_address)
                not_connected = True
            except utils.TimeoutError as e:
                logging.error('%s: %s', method_name, e)
            except:
                logging.error('%s: unexpected error', method_name)
                raise
        else:
            not_connected = True
        self.results = {'not_connected': not_connected}
        return all(self.results.values())


    @test_retry_and_log
    def test_device_is_paired(self, device_address):
        """Test that the device address given is currently paired.

        @param device_address: Address of the device.

        @returns: True if the device is paired.
                  False otherwise.

        """
        def _is_paired():
            """Test if device is paired.

            @returns: True if device is paired. False otherwise.

            """
            return self.bluetooth_facade.device_is_paired(device_address)


        method_name = 'test_device_is_paired'
        has_device = False
        paired = False
        if self.bluetooth_facade.has_device(device_address):
            has_device = True
            try:
                utils.poll_for_condition(
                        condition=_is_paired,
                        timeout=self.ADAPTER_PAIRING_TIMEOUT_SECS,
                        sleep_interval=self.ADAPTER_PAIRING_POLLING_SLEEP_SECS,
                        desc='Waiting for connection to %s' % device_address)
                paired = True
            except utils.TimeoutError as e:
                logging.error('%s: %s', method_name, e)
            except:
                logging.error('%s: unexpected error', method_name)
        self.results = {'has_device': has_device, 'paired': paired}
        return all(self.results.values())


    def _get_device_name(self, device_address):
        """Get the device name.

        @returns: True if the device name is derived. None otherwise.

        """

        self.discovered_device_name = self.bluetooth_facade.get_device_property(
                                device_address, 'Name')

        return bool(self.discovered_device_name)


    @test_retry_and_log
    def test_device_name(self, device_address, expected_device_name):
        """Test that the device name discovered by the adapter is correct.

        @param device_address: Address of the device.
        @param expected_device_name: the bluetooth device name

        @returns: True if the discovered_device_name is expected_device_name.
                  False otherwise.

        """
        try:
            utils.poll_for_condition(
                    condition=lambda: self._get_device_name(device_address),
                    timeout=self.ADAPTER_DISCOVER_NAME_TIMEOUT_SECS,
                    sleep_interval=self.ADAPTER_DISCOVER_POLLING_SLEEP_SECS,
                    desc='Waiting for device name of %s' % device_address)
        except utils.TimeoutError as e:
            logging.error('test_device_name: %s', e)
        except:
            logging.error('test_device_name: unexpected error')

        self.results = {
                'expected_device_name': expected_device_name,
                'discovered_device_name': self.discovered_device_name}
        return self.discovered_device_name == expected_device_name


    @test_retry_and_log
    def test_device_class_of_service(self, device_address,
                                     expected_class_of_service):
        """Test that the discovered device class of service is as expected.

        @param device_address: Address of the device.
        @param expected_class_of_service: the expected class of service

        @returns: True if the discovered class of service matches the
                  expected class of service. False otherwise.

        """

        device_class = self.bluetooth_facade.get_device_property(device_address,
                                                                 'Class')
        discovered_class_of_service = (device_class & self.CLASS_OF_SERVICE_MASK
                                       if device_class else None)

        self.results = {
                'device_class': device_class,
                'expected_class_of_service': expected_class_of_service,
                'discovered_class_of_service': discovered_class_of_service}
        return discovered_class_of_service == expected_class_of_service


    @test_retry_and_log
    def test_device_class_of_device(self, device_address,
                                    expected_class_of_device):
        """Test that the discovered device class of device is as expected.

        @param device_address: Address of the device.
        @param expected_class_of_device: the expected class of device

        @returns: True if the discovered class of device matches the
                  expected class of device. False otherwise.

        """

        device_class = self.bluetooth_facade.get_device_property(device_address,
                                                                 'Class')
        discovered_class_of_device = (device_class & self.CLASS_OF_DEVICE_MASK
                                      if device_class else None)

        self.results = {
                'device_class': device_class,
                'expected_class_of_device': expected_class_of_device,
                'discovered_class_of_device': discovered_class_of_device}
        return discovered_class_of_device == expected_class_of_device


    def _get_btmon_log(self, method, logging_timespan=1):
        """Capture the btmon log when executing the specified method.

        @param method: the method to capture log.
                       The method would be executed only when it is not None.
                       This allows us to simply capture btmon log without
                       executing any command.
        @param logging_timespan: capture btmon log for logging_timespan seconds.

        """
        self.bluetooth_le_facade.btmon_start()
        self.advertising_msg = method() if method else ''
        time.sleep(logging_timespan)
        self.bluetooth_le_facade.btmon_stop()


    def convert_to_adv_jiffies(self, adv_interval_ms):
        """Convert adv interval in ms to jiffies, i.e., multiples of 0.625 ms.

        @param adv_interval_ms: an advertising interval

        @returns: the equivalent jiffies

        """
        return int(round(adv_interval_ms / self.ADVERTISING_INTERVAL_UNIT))


    def compute_duration(self, max_adv_interval_ms):
        """Compute duration from max_adv_interval_ms.

        Advertising duration is calculated approximately as
            duration = max_adv_interval_ms / 1000.0 * 1.1

        @param max_adv_interval_ms: max advertising interval in milliseconds.

        @returns: duration in seconds.

        """
        return max_adv_interval_ms / 1000.0 * 1.1


    def compute_logging_timespan(self, max_adv_interval_ms):
        """Compute the logging timespan from max_adv_interval_ms.

        The logging timespan is the time needed to record btmon log.

        @param max_adv_interval_ms: max advertising interval in milliseconds.

        @returns: logging_timespan in seconds.

        """
        duration = self.compute_duration(max_adv_interval_ms)
        logging_timespan = max(self.count_advertisements * duration, 1)
        return logging_timespan


    @test_retry_and_log(False)
    def test_check_duration_and_intervals(self, min_adv_interval_ms,
                                          max_adv_interval_ms,
                                          number_advertisements):
        """Verify that every advertisements are scheduled according to the
        duration and intervals.

        An advertisement would be scheduled at the time span of
             duration * number_advertisements

        @param min_adv_interval_ms: min advertising interval in milliseconds.
        @param max_adv_interval_ms: max advertising interval in milliseconds.
        @param number_advertisements: the number of existing advertisements

        @returns: True if all advertisements are scheduled based on the
                duration and intervals.

        """


        def within_tolerance(expected, actual, max_error=0.1):
            """Determine if the percent error is within specified tolerance.

            @param expected: The expected value.
            @param actual: The actual (measured) value.
            @param max_error: The maximum percent error acceptable.

            @returns: True if the percent error is less than or equal to
                      max_error.
            """
            return abs(expected - actual) / abs(expected) <= max_error


        start_str = 'Set Advertising Intervals:'
        search_strings = ['HCI Command: LE Set Advertising Data', 'Company']
        search_str = '|'.join(search_strings)

        contents = self.bluetooth_le_facade.btmon_get(search_str=search_str,
                                                      start_str=start_str)

        # Company string looks like
        #   Company: not assigned (65283)
        company_pattern = re.compile('Company:.*\((\d*)\)')

        # The string with timestamp looks like
        #   < HCI Command: LE Set Advertising Data (0x08|0x0008) [hci0] 3.799236
        set_adv_time_str = 'LE Set Advertising Data.*\[hci\d\].*(\d+\.\d+)'
        set_adv_time_pattern = re.compile(set_adv_time_str)

        adv_timestamps = {}
        timestamp = None
        manufacturer_id = None
        for line in contents:
            result = set_adv_time_pattern.search(line)
            if result:
                timestamp = float(result.group(1))

            result = company_pattern.search(line)
            if result:
                manufacturer_id = '0x%04x' % int(result.group(1))

            if timestamp and manufacturer_id:
                if manufacturer_id not in adv_timestamps:
                    adv_timestamps[manufacturer_id] = []
                adv_timestamps[manufacturer_id].append(timestamp)
                timestamp = None
                manufacturer_id = None

        duration = self.compute_duration(max_adv_interval_ms)
        expected_timespan = duration * number_advertisements

        check_duration = True
        for manufacturer_id, values in six.iteritems(adv_timestamps):
            logging.debug('manufacturer_id %s: %s', manufacturer_id, values)
            timespans = [values[i] - values[i - 1]
                         for i in range(1, len(values))]
            errors = [timespans[i] for i in range(len(timespans))
                      if not within_tolerance(expected_timespan, timespans[i])]
            logging.debug('timespans: %s', timespans)
            logging.debug('errors: %s', errors)
            if bool(errors):
                check_duration = False

        # Verify that the advertising intervals are also correct.
        min_adv_interval_ms_found, max_adv_interval_ms_found = (
                self._verify_advertising_intervals(min_adv_interval_ms,
                                                   max_adv_interval_ms))

        self.results = {
                'check_duration': check_duration,
                'min_adv_interval_ms_found': min_adv_interval_ms_found,
                'max_adv_interval_ms_found': max_adv_interval_ms_found,
        }
        return all(self.results.values())


    def _get_min_max_intervals_strings(self, min_adv_interval_ms,
                                       max_adv_interval_ms):
        """Get the min and max advertising intervals strings shown in btmon.

        Advertising intervals shown in the btmon log look like
            Min advertising interval: 1280.000 msec (0x0800)
            Max advertising interval: 1280.000 msec (0x0800)

        @param min_adv_interval_ms: min advertising interval in milliseconds.
        @param max_adv_interval_ms: max advertising interval in milliseconds.

        @returns: the min and max intervals strings.

        """
        min_str = ('Min advertising interval: %.3f msec (0x%04x)' %
                   (min_adv_interval_ms,
                    self.convert_to_adv_jiffies(min_adv_interval_ms)))
        logging.debug('min_adv_interval_ms: %s', min_str)

        max_str = ('Max advertising interval: %.3f msec (0x%04x)' %
                   (max_adv_interval_ms,
                    self.convert_to_adv_jiffies(max_adv_interval_ms)))
        logging.debug('max_adv_interval_ms: %s', max_str)

        return (min_str, max_str)


    def _verify_advertising_intervals(self, min_adv_interval_ms,
                                      max_adv_interval_ms):
        """Verify min and max advertising intervals.

        Advertising intervals look like
            Min advertising interval: 1280.000 msec (0x0800)
            Max advertising interval: 1280.000 msec (0x0800)

        @param min_adv_interval_ms: min advertising interval in milliseconds.
        @param max_adv_interval_ms: max advertising interval in milliseconds.

        @returns: a tuple of (True, True) if both min and max advertising
            intervals could be found. Otherwise, the corresponding element
            in the tuple if False.

        """
        min_str, max_str = self._get_min_max_intervals_strings(
                min_adv_interval_ms, max_adv_interval_ms)

        min_adv_interval_ms_found = self.bluetooth_le_facade.btmon_find(min_str)
        max_adv_interval_ms_found = self.bluetooth_le_facade.btmon_find(max_str)

        return min_adv_interval_ms_found, max_adv_interval_ms_found


    def _verify_scan_response_data(self, adv_data):
        """Verify advertisement's scan response data is correct

        Unlike the other fixed advertising fields, Scan Response Data is set
        in a tag-value data format. This function helps verify the data format
        for specific tag values to ensure scan response was propagated correctly

        @param adv_data: Dictionary defining advertising fields to be registered
                with bluetoothd daemon's RegisterAdvertisement interface

        @returns: True if all Registered Scan Response tags were located in
                btmon trace, False otherwise
        """

        scan_rsp = adv_data.get('ScanResponseData')
        if not scan_rsp:
            return True

        for tag, data in scan_rsp.items():
            # Validate 16 bit Service Data tag
            if int(tag, 16) == 0x16:
                # First two bytes of data are endian-corrected UUID, followed
                # by service data
                uuid = '%x%x' % (data[1], data[0])
                data_str = ''.join(
                        ['%02x' % data[i] for i in range(2, len(data))])

                # Service data has the following format in btmon trace:
                # Service Data (UUID 0xfef3): 01020304
                search_str = 'Service Data (UUID 0x{}): {}'.format(
                        uuid, data_str)

                # Fail if data can't be located in btmon trace
                if not self.bluetooth_le_facade.btmon_find(search_str):
                    return False

        return True

    def test_advertising_flags(self, flag_strs=[]):
        """Verify that advertising flags are set in registered advertisement

        Each flag has a specific descriptor that appears in btmon trace. This
        simple checker validates that the desired flag descriptors appear in
        btmon trace when the advertisement was registered.

        @param flag_strs: Flag string descriptors expected in btmon trace

        #returns: True if all flag descriptors were located, False otherwise
        """

        for flag_str in flag_strs:
            if not self.bluetooth_le_facade.btmon_find(flag_str):
                logging.info(
                        'Flag descriptor not located: {}'.format(flag_str))
                return False

        return True

    def ext_adv_enabled(self):
        """ Check if platform supports extended advertising

        @returns True if extended advertising is supported, else False
        """

        adv_features = self.bluetooth_facade.get_advertising_manager_property(
                'SupportedFeatures')

        return 'HardwareOffload' in adv_features

    def _verify_adv_tx_power(self, advertising_data):
        """ Verify that advertisement uses Tx Power correctly via the following:

            1. Confirm the correct Tx Power is propagated in both MGMT and
                HCI commands.
            2. Validate that the Tx Power selected by the controller is
                returned to the client via dbus.

        @param: advertising_data: dictionary of advertising data properties
            used to register the advertisement

        @returns: True if the above requirements are met, False otherwise
        """

        # If we aren't using TxPower in this advertisement, success
        if not self.ext_adv_enabled() or 'TxPower' not in advertising_data:
            return True

        # Make sure the correct Tx power was passed in both MGMT and HCI
        # commands by searching for two instances of search string
        search_str = 'TX power: {} dbm'.format(advertising_data['TxPower'])
        contents = self.bluetooth_le_facade.btmon_get(search_str=search_str,
                                                      start_str='')
        if len(contents) < 2:
            logging.error('Could not locate correct Tx power in MGMT and HCI')
            return False

        # Locate tx power selected by controller
        search_str = 'TX power \(selected\)'
        contents = self.bluetooth_le_facade.btmon_get(search_str=search_str,
                                                      start_str='')

        if not contents:
            logging.error('No Tx Power selected event found, failing')
            return False

        # The line we want has the following structure:
        # 'TX power (selected): -5 dbm (0x07)'
        # We locate the number before 'dbm'
        items = contents[0].split(' ')
        selected_tx_power = int(items[items.index('dbm') - 1])

        # Validate that client's advertisement was updated correctly.
        new_tx_prop = self.bluetooth_le_facade.get_advertisement_property(
                advertising_data['Path'], 'TxPower')

        return new_tx_prop == selected_tx_power

    @test_retry_and_log(False)
    def test_register_advertisement(self, advertisement_data, instance_id):
        """Verify that an advertisement is registered correctly.

        This test verifies the following data:
        - advertisement added
        - manufacturer data
        - service UUIDs
        - service data
        - advertising intervals
        - advertising enabled
        - Tx power set (if extended advertising available)

        @param advertisement_data: the data of an advertisement to register.
        @param instance_id: the instance id which starts at 1.

        @returns: True if the advertisement is registered correctly.
                  False otherwise.

        """

        # We need to know the intervals used to verify later. If advertisement
        # structure contains it, use them. Otherwise, use bluez's defaults
        if set(advertisement_data) >= {'MinInterval', 'MaxInterval'}:
            min_adv_interval_ms = advertisement_data['MinInterval']
            max_adv_interval_ms = advertisement_data['MaxInterval']

        else:
            min_adv_interval_ms = self.DEFAULT_MIN_ADVERTISEMENT_INTERVAL_MS
            max_adv_interval_ms = self.DEFAULT_MAX_ADVERTISEMENT_INTERVAL_MS

        # When registering a new advertisement, it is possible that another
        # instance is advertising. It may need to wait for all other
        # advertisements to complete advertising once.
        self.count_advertisements += 1
        logging_timespan = self.compute_logging_timespan(max_adv_interval_ms)
        self._get_btmon_log(
                lambda: self.bluetooth_le_facade.register_advertisement(
                        advertisement_data),
                logging_timespan=logging_timespan)

        # _get_btmon_log will store the return value of the registration request
        # in self.advertising_msg. If the request was successful, the return
        # value was an empty string
        registration_succeeded = (self.advertising_msg == '')

        # Verify that a new advertisement is added.
        advertisement_added = (
                self.bluetooth_le_facade.btmon_find('Advertising Added') and
                self.bluetooth_le_facade.btmon_find('Instance: %d' %
                                                    instance_id))

        # Verify that the manufacturer data could be found.
        manufacturer_data = advertisement_data.get('ManufacturerData', '')
        manufacturer_data_found = True
        for manufacturer_id in manufacturer_data:
            # The 'not assigned' text below means the manufacturer id
            # is not actually assigned to any real manufacturer.
            # For real 16-bit manufacturer UUIDs, refer to
            #  https://www.bluetooth.com/specifications/assigned-numbers/16-bit-UUIDs-for-Members
            manufacturer_data_found = self.bluetooth_le_facade.btmon_find(
                    'Company: not assigned (%d)' % int(manufacturer_id, 16))

        # Verify that all service UUIDs could be found.
        service_uuids_found = True
        for uuid in advertisement_data.get('ServiceUUIDs', []):
            # Service UUIDs looks like ['0x180D', '0x180F']
            #   Heart Rate (0x180D)
            #   Battery Service (0x180F)
            # For actual 16-bit service UUIDs, refer to
            #   https://www.bluetooth.com/specifications/gatt/services
            if not self.bluetooth_le_facade.btmon_find('0x%s' % uuid):
                service_uuids_found = False
                break

        # Verify service data.
        service_data_found = True
        for uuid, data in advertisement_data.get('ServiceData', {}).items():
            # A service data looks like
            #   Service Data (UUID 0x9999): 0001020304
            # while uuid is '9999' and data is [0x00, 0x01, 0x02, 0x03, 0x04]
            data_str = ''.join(['%02x' % n for n in data])
            if not self.bluetooth_le_facade.btmon_find(
                    'Service Data (UUID 0x%s): %s' % (uuid, data_str)):
                service_data_found = False
                break

        # Broadcast advertisements are overwritten in some kernel versions to
        # be more aggressive. Verify that the advertising intervals are correct
        # if this mode is not used
        if advertisement_data.get('Type') != 'broadcast':
            min_adv_interval_ms_found, max_adv_interval_ms_found = (
                    self._verify_advertising_intervals(min_adv_interval_ms,
                                                       max_adv_interval_ms))

        else:
            min_adv_interval_ms_found = True
            max_adv_interval_ms_found = True

        scan_rsp_correct = self._verify_scan_response_data(advertisement_data)

        # Verify advertising is enabled.
        advertising_enabled = self.bluetooth_le_facade.btmon_find(
                'Advertising: Enabled (0x01)')

        # Verify new APIs were used
        new_apis_used = self.bluetooth_le_facade.btmon_find(
                'Add Extended Advertising Parameters')

        tx_power_correct = self._verify_adv_tx_power(advertisement_data)

        self.results = {
                'registration_succeeded': registration_succeeded,
                'advertisement_added': advertisement_added,
                'manufacturer_data_found': manufacturer_data_found,
                'service_uuids_found': service_uuids_found,
                'service_data_found': service_data_found,
                'min_adv_interval_ms_found': min_adv_interval_ms_found,
                'max_adv_interval_ms_found': max_adv_interval_ms_found,
                'scan_rsp_correct': scan_rsp_correct,
                'advertising_enabled': advertising_enabled,
                'new_apis_used': new_apis_used,
                'tx_power_correct': tx_power_correct,
        }
        return all(self.results.values())


    @test_retry_and_log(False)
    def test_fail_to_register_advertisement(self, advertisement_data,
                                            min_adv_interval_ms,
                                            max_adv_interval_ms):
        """Verify that failure is incurred when max advertisements are reached.

        This test verifies that a registration failure is incurred when
        max advertisements are reached. The error message looks like:

            org.bluez.Error.Failed: Maximum advertisements reached

        @param advertisement_data: the advertisement to register.
        @param min_adv_interval_ms: min_adv_interval in milliseconds.
        @param max_adv_interval_ms: max_adv_interval in milliseconds.

        @returns: True if the error message is received correctly.
                  False otherwise.

        """
        logging_timespan = self.compute_logging_timespan(max_adv_interval_ms)
        self._get_btmon_log(
                lambda: self.bluetooth_le_facade.register_advertisement(
                        advertisement_data),
                logging_timespan=logging_timespan)

        # Verify that it failed to register advertisement due to the fact
        # that max advertisements are reached.
        failed_to_register_error = (self.ERROR_FAILED_TO_REGISTER_ADVERTISEMENT
                                    in self.advertising_msg)

        # Verify that no new advertisement is added.
        advertisement_not_added = not self.bluetooth_le_facade.btmon_find(
                'Advertising Added:')

        self.results = {
                'failed_to_register_error': failed_to_register_error,
                'advertisement_not_added': advertisement_not_added,
        }

        # If the registration fails and extended advertising is available,
        # there will be no events in btmon. Therefore, we only run this part of
        # the test if extended advertising is not available, indicating that
        # software advertisement rotation is being used.
        if not self.ext_adv_enabled():
            # Verify that the advertising intervals are correct.
            min_adv_interval_ms_found, max_adv_interval_ms_found = (
                    self._verify_advertising_intervals(min_adv_interval_ms,
                                                       max_adv_interval_ms))

            # Verify advertising remains enabled.
            advertising_enabled = self.bluetooth_le_facade.btmon_find(
                    'Advertising: Enabled (0x01)')

            self.results.update({
                'min_adv_interval_ms_found': min_adv_interval_ms_found,
                'max_adv_interval_ms_found': max_adv_interval_ms_found,
                'advertising_enabled': advertising_enabled,
            })

        return all(self.results.values())


    @test_retry_and_log(False)
    def test_unregister_advertisement(self, advertisement_data, instance_id,
                                      advertising_disabled):
        """Verify that an advertisement is unregistered correctly.

        This test verifies the following data:
        - advertisement removed
        - advertising status: enabled if there are advertisements left;
                              disabled otherwise.

        @param advertisement_data: the data of an advertisement to unregister.
        @param instance_id: the instance id of the advertisement to remove.
        @param advertising_disabled: is advertising disabled? This happens
                only when all advertisements are removed.

        @returns: True if the advertisement is unregistered correctly.
                  False otherwise.

        """
        self.count_advertisements -= 1
        self._get_btmon_log(
                lambda: self.bluetooth_le_facade.unregister_advertisement(
                        advertisement_data))

        # Verify that the advertisement is removed.
        advertisement_removed = (
                self.bluetooth_le_facade.btmon_find('Advertising Removed') and
                self.bluetooth_le_facade.btmon_find('Instance: %d' %
                                                    instance_id))

        # If advertising_disabled is True, there should be no log like
        #       'Advertising: Enabled (0x01)'
        # If advertising_disabled is False, there should be log like
        #       'Advertising: Enabled (0x01)'

        # Only need to check advertising status when the last advertisement
        # is removed. For any other advertisements prior to the last one,
        # we may or may not observe 'Advertising: Enabled (0x01)' message.
        # Hence, the test would become flaky if we insist to see that message.
        # A possible workaround is to sleep for a while and then check the
        # message. The drawback is that we may need to wait up to 10 seconds
        # if the advertising duration and intervals are long.
        # In a test case, we always run test_check_duration_and_intervals()
        # to check if advertising duration and intervals are correct after
        # un-registering one or all advertisements, it is safe to do so.
        advertising_enabled_found = self.bluetooth_le_facade.btmon_find(
                'Advertising: Enabled (0x01)')
        advertising_disabled_found = self.bluetooth_le_facade.btmon_find(
                'Advertising: Disabled (0x00)')
        advertising_status_correct = not advertising_disabled or (
                advertising_disabled_found and not advertising_enabled_found)

        self.results = {
                'advertisement_removed': advertisement_removed,
                'advertising_status_correct': advertising_status_correct,
        }
        return all(self.results.values())


    @test_retry_and_log(False)
    def test_set_advertising_intervals(self, min_adv_interval_ms,
                                       max_adv_interval_ms):
        """Verify that new advertising intervals are set correctly.

        Note that setting advertising intervals does not enable/disable
        advertising. Hence, there is no need to check the advertising
        status.

        @param min_adv_interval_ms: the min advertising interval in ms.
        @param max_adv_interval_ms: the max advertising interval in ms.

        @returns: True if the new advertising intervals are correct.
                  False otherwise.

        """
        self._get_btmon_log(
                lambda: self.bluetooth_le_facade.set_advertising_intervals(
                        min_adv_interval_ms, max_adv_interval_ms))

        # Verify the new advertising intervals.
        # With intervals of 200 ms and 200 ms, the log looks like
        #   bluetoothd: Set Advertising Intervals: 0x0140, 0x0140
        txt = 'bluetoothd: Set Advertising Intervals: 0x%04x, 0x%04x'
        adv_intervals_found = self.bluetooth_le_facade.btmon_find(
                txt % (self.convert_to_adv_jiffies(min_adv_interval_ms),
                       self.convert_to_adv_jiffies(max_adv_interval_ms)))

        self.results = {'adv_intervals_found': adv_intervals_found}
        return all(self.results.values())


    @test_retry_and_log(False)
    def test_fail_to_set_advertising_intervals(
            self, invalid_min_adv_interval_ms, invalid_max_adv_interval_ms,
            orig_min_adv_interval_ms, orig_max_adv_interval_ms):
        """Verify that setting invalid advertising intervals results in error.

        If invalid min/max advertising intervals are given, it would incur
        the error: 'org.bluez.Error.InvalidArguments: Invalid arguments'.
        Note that valid advertising intervals fall between 20 ms and 10,240 ms.

        @param invalid_min_adv_interval_ms: the invalid min advertising interval
                in ms.
        @param invalid_max_adv_interval_ms: the invalid max advertising interval
                in ms.
        @param orig_min_adv_interval_ms: the original min advertising interval
                in ms.
        @param orig_max_adv_interval_ms: the original max advertising interval
                in ms.

        @returns: True if it fails to set invalid advertising intervals.
                  False otherwise.

        """
        self._get_btmon_log(
                lambda: self.bluetooth_le_facade.set_advertising_intervals(
                        invalid_min_adv_interval_ms,
                        invalid_max_adv_interval_ms))

        # Verify that the invalid error is observed in the dbus error callback
        # message.
        invalid_intervals_error = (self.ERROR_INVALID_ADVERTISING_INTERVALS in
                                   self.advertising_msg)

        # Verify that the min/max advertising intervals remain the same
        # after setting the invalid advertising intervals.
        #
        # In btmon log, we would see the following message first.
        #    bluetoothd: Set Advertising Intervals: 0x0010, 0x0010
        # And then, we should check if "Min advertising interval" and
        # "Max advertising interval" remain the same.
        start_str = 'bluetoothd: Set Advertising Intervals: 0x%04x, 0x%04x' % (
                self.convert_to_adv_jiffies(invalid_min_adv_interval_ms),
                self.convert_to_adv_jiffies(invalid_max_adv_interval_ms))

        search_strings = ['Min advertising interval:',
                          'Max advertising interval:']
        search_str = '|'.join(search_strings)

        contents = self.bluetooth_le_facade.btmon_get(search_str=search_str,
                                                      start_str=start_str)

        # The min/max advertising intervals of all advertisements should remain
        # the same as the previous valid ones.
        min_max_str = '[Min|Max] advertising interval: (\d*\.\d*) msec'
        min_max_pattern = re.compile(min_max_str)
        correct_orig_min_adv_interval = True
        correct_orig_max_adv_interval = True
        for line in contents:
            result = min_max_pattern.search(line)
            if result:
                interval = float(result.group(1))
                if 'Min' in line and interval != orig_min_adv_interval_ms:
                    correct_orig_min_adv_interval = False
                elif 'Max' in line and interval != orig_max_adv_interval_ms:
                    correct_orig_max_adv_interval = False

        self.results = {
                'invalid_intervals_error': invalid_intervals_error,
                'correct_orig_min_adv_interval': correct_orig_min_adv_interval,
                'correct_orig_max_adv_interval': correct_orig_max_adv_interval}

        return all(self.results.values())


    @test_retry_and_log(False)
    def test_check_advertising_intervals(self, min_adv_interval_ms,
                                         max_adv_interval_ms):
        """Verify that the advertising intervals are as expected.

        @param min_adv_interval_ms: the min advertising interval in ms.
        @param max_adv_interval_ms: the max advertising interval in ms.

        @returns: True if the advertising intervals are correct.
                  False otherwise.

        """
        self._get_btmon_log(None)

        # Verify that the advertising intervals are correct.
        min_adv_interval_ms_found, max_adv_interval_ms_found = (
                self._verify_advertising_intervals(min_adv_interval_ms,
                                                   max_adv_interval_ms))

        self.results = {
                'min_adv_interval_ms_found': min_adv_interval_ms_found,
                'max_adv_interval_ms_found': max_adv_interval_ms_found,
        }
        return all(self.results.values())


    @test_retry_and_log(False)
    def test_reset_advertising(self, instance_ids=[]):
        """Verify that advertising is reset correctly.

        Note that reset advertising would set advertising intervals to
        the default values. However, we would not be able to observe
        the values change until new advertisements are registered.
        Therefore, it is required that a test_register_advertisement()
        test is conducted after this test.

        If instance_ids is [], all advertisements would still be removed
        if there are any. However, no need to check 'Advertising Removed'
        in btmon log since we may or may not be able to observe the message.
        This feature is needed if this test is invoked as the first one in
        a test case to reset advertising. In this situation, this test does
        not know how many advertisements exist.

        @param instance_ids: the list of instance IDs that should be removed.

        @returns: True if advertising is reset correctly.
                  False otherwise.

        """
        self.count_advertisements = 0
        self._get_btmon_log(
                lambda: self.bluetooth_le_facade.reset_advertising())

        # Verify that every advertisement is removed. When an advertisement
        # with instance id 1 is removed, the log looks like
        #   Advertising Removed
        #       instance: 1
        if len(instance_ids) > 0:
            advertisement_removed = self.bluetooth_le_facade.btmon_find(
                    'Advertising Removed')
            if advertisement_removed:
                for instance_id in instance_ids:
                    txt = 'Instance: %d' % instance_id
                    if not self.bluetooth_le_facade.btmon_find(txt):
                        advertisement_removed = False
                        break
        else:
            advertisement_removed = True

        if not advertisement_removed:
            logging.error('Failed to remove advertisement')

        # Verify the advertising is disabled.
        advertising_disabled_observied = self.bluetooth_le_facade.btmon_find(
                'Advertising: Disabled')
        # If there are no existing advertisements, we may not observe
        # 'Advertising: Disabled'.
        advertising_disabled = (instance_ids == [] or
                                advertising_disabled_observied)

        self.results = {
                'advertisement_removed': advertisement_removed,
                'advertising_disabled': advertising_disabled,
        }
        return all(self.results.values())


    @test_retry_and_log(False)
    def test_receive_advertisement(self, address=None, UUID=None, timeout=10):
        """Verifies that we receive an advertisement with specific contents

        Since test_discover_device only uses the existence of a device dbus path
        to indicate when a device is discovered, it is not adequate if we want
        to verify that we have received an advertisement from a device. This
        test monitors btmon around a discovery instance and searches for the
        relevant advertising report.

        @param address: String address of peer
        @param UUID: String of hex data
        @param timeout: seconds to listen for traffic

        @returns True if report was located, otherwise False
        """

        def _discover_devices():
            self.test_start_discovery()
            time.sleep(timeout)
            self.test_stop_discovery()

        # Run discovery, record btmon log
        self._get_btmon_log(_discover_devices)

        # Grab all logs received
        btmon_log = '\n'.join(self.bluetooth_le_facade.btmon_get('', ''))

        desired_strs = []

        if address is not None:
            desired_strs.append('Address: {}'.format(address))

        if UUID is not None:
            desired_strs.append('({})'.format(UUID))

        # Split btmon events by HCI and MGMT delimiters
        event_delimiter = '|'.join(['@ MGMT', '> HCI', '< HCI'])
        btmon_events = re.split(event_delimiter, btmon_log)

        features_located = False

        for event_str in btmon_events:
            if 'Advertising Report' not in event_str:
                continue

            for desired_str in desired_strs:
                if desired_str not in event_str:
                    break

            else:
                features_located = True

        self.results = {
                'features_located': features_located,
        }
        return all(self.results.values())


    def add_device(self, address, address_type, action):
        """Add a device to the Kernel action list."""
        return self.bluetooth_facade.add_device(address, address_type, action)


    def remove_device(self, address, address_type):
        """Remove a device from the Kernel action list."""
        return self.bluetooth_facade.remove_device(address,address_type)


    def read_supported_commands(self):
        """Read the set of supported commands from the Kernel."""
        return self.bluetooth_facade.read_supported_commands()


    def read_info(self):
        """Read the adapter information from the Kernel."""
        return self.bluetooth_facade.read_info()


    def get_adapter_properties(self):
        """Read the adapter properties from the Bluetooth Daemon."""
        return self.bluetooth_facade.get_adapter_properties()


    def get_dev_info(self):
        """Read raw HCI device information."""
        return self.bluetooth_facade.get_dev_info()

    def log_settings(self, msg, settings):
        """function convert MGMT_OP_READ_INFO settings to string

        @param msg: string to include in output
        @param settings: bitstring returned by MGMT_OP_READ_INFO
        @return : List of strings indicating different settings
        """
        strs = []
        if settings & bluetooth_socket.MGMT_SETTING_POWERED:
            strs.append("POWERED")
        if settings & bluetooth_socket.MGMT_SETTING_CONNECTABLE:
            strs.append("CONNECTABLE")
        if settings & bluetooth_socket.MGMT_SETTING_FAST_CONNECTABLE:
            strs.append("FAST-CONNECTABLE")
        if settings & bluetooth_socket.MGMT_SETTING_DISCOVERABLE:
            strs.append("DISCOVERABLE")
        if settings & bluetooth_socket.MGMT_SETTING_PAIRABLE:
            strs.append("PAIRABLE")
        if settings & bluetooth_socket.MGMT_SETTING_LINK_SECURITY:
            strs.append("LINK-SECURITY")
        if settings & bluetooth_socket.MGMT_SETTING_SSP:
            strs.append("SSP")
        if settings & bluetooth_socket.MGMT_SETTING_BREDR:
            strs.append("BR/EDR")
        if settings & bluetooth_socket.MGMT_SETTING_HS:
            strs.append("HS")
        if settings & bluetooth_socket.MGMT_SETTING_LE:
            strs.append("LE")
        logging.debug('%s : %s', msg, " ".join(strs))
        return strs

    def log_flags(self, msg, flags):
        """Function to convert HCI state configuration to a string

        @param msg: string to include in output
        @param settings: bitstring returned by get_dev_info
        @return : List of strings indicating different flags
        """
        strs = []
        if flags & bluetooth_socket.HCI_UP:
            strs.append("UP")
        else:
            strs.append("DOWN")
        if flags & bluetooth_socket.HCI_INIT:
            strs.append("INIT")
        if flags & bluetooth_socket.HCI_RUNNING:
            strs.append("RUNNING")
        if flags & bluetooth_socket.HCI_PSCAN:
            strs.append("PSCAN")
        if flags & bluetooth_socket.HCI_ISCAN:
            strs.append("ISCAN")
        if flags & bluetooth_socket.HCI_AUTH:
            strs.append("AUTH")
        if flags & bluetooth_socket.HCI_ENCRYPT:
            strs.append("ENCRYPT")
        if flags & bluetooth_socket.HCI_INQUIRY:
            strs.append("INQUIRY")
        if flags & bluetooth_socket.HCI_RAW:
            strs.append("RAW")
        logging.debug('%s [HCI]: %s', msg, " ".join(strs))
        return strs


    @test_retry_and_log(False)
    def test_service_resolved(self, address):
        """Test that the services under device address can be resolved

        @param address: MAC address of a device

        @returns: True if the ServicesResolved property is changed before
                 timeout, False otherwise.

        """
        is_resolved_func = self.bluetooth_facade.device_services_resolved
        return self._wait_for_condition(lambda : is_resolved_func(address),\
                                        method_name())


    @test_retry_and_log(False)
    def test_gatt_browse(self, address):
        """Test that the GATT client can get the attributes correctly

        @param address: MAC address of a device

        @returns: True if the attribute map received by GATT client is the same
                  as expected. False otherwise.

        """

        gatt_client_facade = GATT_ClientFacade(self.bluetooth_facade)
        actual_app = gatt_client_facade.browse(address)
        expected_app = GATT_HIDApplication()
        diff = GATT_Application.diff(actual_app, expected_app)

        self.result = {
            'actural_result': actual_app,
            'expected_result': expected_app
        }

        gatt_attribute_hierarchy = ['Device', 'Service', 'Characteristic',
                                    'Descriptor']
        # Remove any difference in object path
        for parent, child in zip(gatt_attribute_hierarchy,
                                 gatt_attribute_hierarchy[1:]):
            pattern = re.compile('^%s .* is different in %s' % (child, parent))
            for diff_str in diff[::]:
                if pattern.search(diff_str):
                    diff.remove(diff_str)

        if len(diff) != 0:
            logging.error('Application Diff: %s', diff)
            return False
        return True


    def _record_input_events(self, device, gesture, address=None):
        """Record the input events.

        @param device: the bluetooth HID device.
        @param gesture: the gesture method to perform.

        @returns: the input events received on the DUT.

        """
        self.input_facade.initialize_input_recorder(device.name, uniq=address)
        self.input_facade.start_input_recorder(device.name)
        time.sleep(self.HID_REPORT_SLEEP_SECS)
        gesture()
        time.sleep(self.HID_REPORT_SLEEP_SECS)
        self.input_facade.stop_input_recorder(device.name)
        time.sleep(self.HID_REPORT_SLEEP_SECS)
        event_values = self.input_facade.get_input_events(device.name)
        events = [Event(*ev) for ev in event_values]
        return events


    # -------------------------------------------------------------------
    # Bluetooth mouse related tests
    # -------------------------------------------------------------------


    def _test_mouse_click(self, device, button):
        """Test that the mouse click events could be received correctly.

        @param device: the meta device containing a bluetooth HID device
        @param button: which button to test, 'LEFT' or 'RIGHT'

        @returns: True if the report received by the host matches the
                  expected one. False otherwise.

        """
        if button == 'LEFT':
            gesture = device.LeftClick
        elif button == 'RIGHT':
            gesture = device.RightClick
        else:
            raise error.TestError('Button (%s) is not valid.' % button)

        actual_events = self._record_input_events(device,
                                                  gesture,
                                                  address=device.address)

        linux_input_button = {'LEFT': BTN_LEFT, 'RIGHT': BTN_RIGHT}
        expected_events = [
                # Button down
                recorder.MSC_SCAN_BTN_EVENT[button],
                Event(EV_KEY, linux_input_button[button], 1),
                recorder.SYN_EVENT,
                # Button up
                recorder.MSC_SCAN_BTN_EVENT[button],
                Event(EV_KEY, linux_input_button[button], 0),
                recorder.SYN_EVENT]

        self.results = {
                'actual_events': list(map(str, actual_events)),
                'expected_events': list(map(str, expected_events))}
        return actual_events == expected_events


    @test_retry_and_log
    def test_mouse_left_click(self, device):
        """Test that the mouse left click events could be received correctly.

        @param device: the meta device containing a bluetooth HID device

        @returns: True if the report received by the host matches the
                  expected one. False otherwise.

        """
        return self._test_mouse_click(device, 'LEFT')


    @test_retry_and_log
    def test_mouse_right_click(self, device):
        """Test that the mouse right click events could be received correctly.

        @param device: the meta device containing a bluetooth HID device

        @returns: True if the report received by the host matches the
                  expected one. False otherwise.

        """
        return self._test_mouse_click(device, 'RIGHT')


    def _test_mouse_move(self, device, delta_x=0, delta_y=0):
        """Test that the mouse move events could be received correctly.

        @param device: the meta device containing a bluetooth HID device
        @param delta_x: the distance to move cursor in x axis
        @param delta_y: the distance to move cursor in y axis

        @returns: True if the report received by the host matches the
                  expected one. False otherwise.

        """
        gesture = lambda: device.Move(delta_x, delta_y)
        actual_events = self._record_input_events(device,
                                                  gesture,
                                                  address=device.address)

        events_x = [Event(EV_REL, REL_X, delta_x)] if delta_x else []
        events_y = [Event(EV_REL, REL_Y, delta_y)] if delta_y else []
        expected_events = events_x + events_y + [recorder.SYN_EVENT]

        self.results = {
                'actual_events': list(map(str, actual_events)),
                'expected_events': list(map(str, expected_events))}
        return actual_events == expected_events


    @test_retry_and_log
    def test_mouse_move_in_x(self, device, delta_x):
        """Test that the mouse move events in x could be received correctly.

        @param device: the meta device containing a bluetooth HID device
        @param delta_x: the distance to move cursor in x axis

        @returns: True if the report received by the host matches the
                  expected one. False otherwise.

        """
        return self._test_mouse_move(device, delta_x=delta_x)


    @test_retry_and_log
    def test_mouse_move_in_y(self, device, delta_y):
        """Test that the mouse move events in y could be received correctly.

        @param device: the meta device containing a bluetooth HID device
        @param delta_y: the distance to move cursor in y axis

        @returns: True if the report received by the host matches the
                  expected one. False otherwise.

        """
        return self._test_mouse_move(device, delta_y=delta_y)


    @test_retry_and_log
    def test_mouse_move_in_xy(self, device, delta_x=-60, delta_y=100):
        """Test that the mouse move events could be received correctly.

        @param device: the meta device containing a bluetooth HID device
        @param delta_x: the distance to move cursor in x axis
        @param delta_y: the distance to move cursor in y axis

        @returns: True if the report received by the host matches the
                  expected one. False otherwise.

        """
        return self._test_mouse_move(device, delta_x=delta_x, delta_y=delta_y)


    def _test_mouse_scroll(self, device, units):
        """Test that the mouse wheel events could be received correctly.

        @param device: the meta device containing a bluetooth HID device
        @param units: the units to scroll in y axis

        @returns: True if the report received by the host matches the
                  expected one. False otherwise.

        """
        gesture = lambda: device.Scroll(units)
        recorded_events = self._record_input_events(device,
                                                    gesture,
                                                    address=device.address)

        # Since high-speed scrolling events are inserted after they are passed
        # through bluetooth module, we ignore these events since they are
        # irrelevant for us
        scroll_events = [ev for ev in recorded_events
                            if ev.code != REL_WHEEL_HI_RES]

        expected_events = [Event(EV_REL, REL_WHEEL, units), recorder.SYN_EVENT]
        self.results = {
                'scroll_events': list(map(str, scroll_events)),
                'expected_events': list(map(str, expected_events))}
        return scroll_events == expected_events


    @test_retry_and_log
    def test_mouse_scroll_down(self, device, delta_y):
        """Test that the mouse wheel events could be received correctly.

        @param device: the meta device containing a bluetooth HID device
        @param delta_y: the units to scroll down in y axis;
                        should be a postive value

        @returns: True if the report received by the host matches the
                  expected one. False otherwise.

        """
        if delta_y > 0:
            return self._test_mouse_scroll(device, delta_y)
        else:
            raise error.TestError('delta_y (%d) should be a positive value',
                                  delta_y)


    @test_retry_and_log
    def test_mouse_scroll_up(self, device, delta_y):
        """Test that the mouse wheel events could be received correctly.

        @param device: the meta device containing a bluetooth HID device
        @param delta_y: the units to scroll up in y axis;
                        should be a postive value

        @returns: True if the report received by the host matches the
                  expected one. False otherwise.

        """
        if delta_y > 0:
            return self._test_mouse_scroll(device, -delta_y)
        else:
            raise error.TestError('delta_y (%d) should be a positive value',
                                  delta_y)


    @test_retry_and_log
    def test_mouse_click_and_drag(self, device, delta_x, delta_y):
        """Test that the mouse click-and-drag events could be received
        correctly.

        @param device: the meta device containing a bluetooth HID device
        @param delta_x: the distance to drag in x axis
        @param delta_y: the distance to drag in y axis

        @returns: True if the report received by the host matches the
                  expected one. False otherwise.

        """
        gesture = lambda: device.ClickAndDrag(delta_x, delta_y)
        actual_events = self._record_input_events(device,
                                                  gesture,
                                                  address=device.address)

        button = 'LEFT'
        expected_events = (
                [# Button down
                 recorder.MSC_SCAN_BTN_EVENT[button],
                 Event(EV_KEY, BTN_LEFT, 1),
                 recorder.SYN_EVENT] +
                # cursor movement in x and y
                ([Event(EV_REL, REL_X, delta_x)] if delta_x else []) +
                ([Event(EV_REL, REL_Y, delta_y)] if delta_y else []) +
                [recorder.SYN_EVENT] +
                # Button up
                [recorder.MSC_SCAN_BTN_EVENT[button],
                 Event(EV_KEY, BTN_LEFT, 0),
                 recorder.SYN_EVENT])

        self.results = {
                'actual_events': list(map(str, actual_events)),
                'expected_events': list(map(str, expected_events))}
        return actual_events == expected_events


    # -------------------------------------------------------------------
    # Bluetooth keyboard related tests
    # -------------------------------------------------------------------

    @test_retry_and_log
    def test_keyboard_input_from_trace(self, device, trace_name):
        """ Tests that keyboard events can be transmitted and received correctly

        @param device: the meta device containing a bluetooth HID device
        @param trace_name: string name for keyboard activity trace to be used
                           in the test i.e. "simple_text"

        @returns: true if the recorded output matches the expected output
                  false otherwise
        """
        length_correct = True
        content_correct = True

        # Read data from trace I/O files
        input_trace = bluetooth_test_utils.parse_trace_file(os.path.join(
                      TRACE_LOCATION, '{}_input.txt'.format(trace_name)))
        output_trace = bluetooth_test_utils.parse_trace_file(os.path.join(
                      TRACE_LOCATION, '{}_output.txt'.format(trace_name)))

        if not input_trace or not output_trace:
            logging.error('Failure in using trace')
            return False

        # Disregard timing data for now
        input_scan_codes = [tup[1] for tup in input_trace]
        predicted_events = [Event(*tup[1]) for tup in output_trace]

        # Create and run this trace as a gesture
        gesture = lambda: device.KeyboardSendTrace(input_scan_codes)
        rec_events = self._record_input_events(device,
                                               gesture,
                                               address=device.address)

        # Filter out any input events that were not from the keyboard
        rec_key_events = [ev for ev in rec_events if ev.type == EV_KEY]

        # Fail if we didn't record the correct number of events
        if len(rec_key_events) != len(input_scan_codes):
            logging.info('Expected {} events, received {}'.format(
                    len(input_scan_codes), len(rec_key_events)))
            length_correct = False

        for idx, predicted in enumerate(predicted_events):
            recorded = rec_key_events[idx]

            if not predicted == recorded:
                content_correct = False
                break

        self.results = {
            'received_events': len(rec_key_events) > 0,
            'length_correct': length_correct,
            'content_correct': content_correct,
        }

        return all(self.results)


    def is_newer_kernel_version(self, version, minimum_version):
        """ Check if given kernel version is newer than unsupported version."""

        return utils.compare_versions(version, minimum_version) >= 0


    def is_supported_kernel_version(self, kernel_version, minimum_version,
                                    msg=None):
        """ Check if kernel version is greater than minimum version.

            Check if given kernel version is greater than or equal to minimum
            version. Raise TEST_NA if given kernel version is lower than the
            minimum version.

            Note: Kernel version may have suffixes, so ensure that minimum
            version should be the smallest version that is permissible.
            Ex: If minimum version is 3.8.11 then 3.8.11-<random> will
            pass the check.

            @param kernel_version: kernel version to be checked as a string
            @param: minimum_version: minimum kernel version requried

            @returns: None

            @raises: TEST_NA if kernel version is not greater than the minimum
                     version
        """

        logging.debug('kernel version is {} minimum version'
                      'is {}'.format(kernel_version,minimum_version))

        if msg is None:
            msg = 'Test not supported on this kernel version'

        if not self.is_newer_kernel_version(kernel_version, minimum_version):
            logging.info('Kernel version check failed: %s', msg)
            raise error.TestNAError(msg)

        logging.debug('Kernel version check passed')


    # -------------------------------------------------------------------
    # Bluetooth AVRCP related test
    # -------------------------------------------------------------------


    @test_retry_and_log
    def test_avrcp_event(self, device, generator, avrcp_event):
        """Tests that AVRCP events can be transmitted and received correctly

        @param device: the meta device containing a Bluetooth AVRCP capable
                       audio device.
        @param generator: the peer device generator/function which trigger
                          the AVRCP event.
        @param avrcp_event: the AVRCP event to test.

        @returns: true if the recorded output matches the expected output
                  false otherwise
        """
        logging.debug('AVRCP Event Test, Event: %s', avrcp_event)
        linux_input_button = {'play': KEY_PLAYCD, 'pause': KEY_PAUSECD,
                              'stop': KEY_STOPCD, 'next': KEY_NEXTSONG,
                              'previous': KEY_PREVIOUSSONG}
        expected_event = [
                # Button down
                Event(EV_KEY, linux_input_button[avrcp_event], 1),
                recorder.SYN_EVENT,
                # Button up
                Event(EV_KEY, linux_input_button[avrcp_event], 0),
                recorder.SYN_EVENT]

        gesture = lambda: generator(avrcp_event)
        actual_event = self._record_input_events(device, gesture)

        return actual_event == expected_event


    # -------------------------------------------------------------------
    # Enterprise policy tests
    # -------------------------------------------------------------------

    def _test_check_set_allowlist(self, uuids, expected_result):
        """The test to set valid and invalid allowlists test.

        @param uuids: the uuids in the allowlist to set.
        @param expected_result: True if the test is expected to pass.
        """
        create_uuid = bluetooth_test_utils.Bluetooth_UUID.create_valid_uuid
        exp_res_str = 'valid' if expected_result else 'invalid'
        logging.info('%s uuids: "%s"', exp_res_str, uuids)

        result, err_msg = self.bluetooth_facade.policy_set_service_allow_list(
                uuids)
        logging.debug('result %s (%s)', result, err_msg)

        if expected_result:
            check_set_allowlist = result
        else:
            check_set_allowlist = ('org.bluez.Error.InvalidArguments' in err_msg
                                   and not result)

        # Query bluez to read the allow list.
        actual_uuids_list = [
                create_uuid(uuid) for uuid in
                self.bluetooth_facade.policy_get_service_allow_list()]
        actual_uuids_list.sort()

        # Convert the original UUIDs into a list of full-length UUIDs and
        # remove duplicate UUIDs in order to compare the original UUIDs
        # with the actual UUIDs set by bluez.
        orig_uuids_list = []
        if expected_result and uuids != '':
            for uuid in uuids.split(','):
                u = create_uuid(uuid)
                if u is None:
                    raise error.TestFail('uuid %s in uuids %s is not valid' %
                                         (uuid, uuids))
                orig_uuids_list.append(u)
        orig_dedup_uuids = list(set(orig_uuids_list))
        orig_dedup_uuids.sort()
        uuids_comp_result = actual_uuids_list == orig_dedup_uuids

        self.results = {'uuids': uuids,
                        'expected_set_allowlist_result': expected_result,
                        'actual_set_allowlist_result': result,
                        'orig_dedup_uuids': orig_dedup_uuids,
                        'actual_uuids_list': actual_uuids_list,
                        'check_set_allowlist': check_set_allowlist,
                        'uuids_comp_result': uuids_comp_result}
        logging.debug('actual_uuids_list %s', actual_uuids_list)
        logging.debug('orig_uuids_list %s', orig_uuids_list)

        return (check_set_allowlist and uuids_comp_result)


    @test_retry_and_log(False)
    def test_check_set_allowlist(self, uuids, expected_result):
        """The test to set valid and invalid allowlists test.

        @param uuids: the uuids in the allowlist to set.
        @param expected_result: True if the test is expected to pass.
        """
        return self._test_check_set_allowlist(uuids, expected_result)


    @test_retry_and_log(False)
    def test_reset_allowlist(self):
        """The test to reset the allowlists.

        The test is used to clean up the allowlist.
        """
        return self._test_check_set_allowlist('', True)


    def policy_is_affected(self, device):
        """Check if the device is affected by policy.

        @param device: the connected device.

        @returns: True if the device is affected by the enterprise policy.
                  False if not. None if the device is not found.
        """
        return self.bluetooth_facade.policy_get_device_affected(device.address)


    @test_retry_and_log(False)
    def test_affected_by_policy(self, device):
        """A test that the device is affected by policy

        @param device: the peripheral device
        @returns: True if the device is affected; False otherwise.
        """
        result = self.policy_is_affected(device)
        logging.debug('policy_is_affected(%s): %s', device.address, result)
        self.results = {
                'expected_result': 'True (affected)',
                'actual_result': result
        }
        return result is True


    @test_retry_and_log(False)
    def test_not_affected_by_policy(self, device):
        """A test that the device is not affected by policy

        @param device: the peripheral device
        @returns: True if the device is not affected; False otherwise.
        """
        result = self.policy_is_affected(device)
        logging.debug('policy_is_affected(%s): %s', device.address, result)
        self.results = {
                'expected_result': 'False (not affected)',
                'actual_result': result
        }
        return result is False

    def check_if_affected_by_policy(self, device, expected_result):
        """A test that the device policy is enforced correctly

        @param device: the peripheral device
        @param expected_result: True if the test is expected to pass.

        @returns: True if the device is affected or not affected per
                  expected_result; False otherwise.
        """
        if expected_result:
            return self.test_affected_by_policy(device)
        else:
            return self.test_not_affected_by_policy(device)


    # -------------------------------------------------------------------
    # Servod related tests
    # -------------------------------------------------------------------

    @test_retry_and_log
    def test_power_consumption(self, device, max_power_mw):
        """Test the average power consumption."""
        power_mw = device.servod.MeasurePowerConsumption()
        self.results = {'power_mw': power_mw}

        if (power_mw is None):
            logging.error('Failed to measure power consumption')
            return False

        power_mw = float(power_mw)
        logging.info('power consumption (mw): %f (max allowed: %f)',
                     power_mw, max_power_mw)

        return power_mw <= max_power_mw


    @test_retry_and_log
    def test_start_notify(self, object_path, cccd_value):
        """Test that a notification can be started on a characteristic

        @param object_path: the object path of the characteristic.
        @param cccd_value: Possible CCCD values include
               0x00 - inferred from the remote characteristic's properties
               0x01 - notification
               0x02 - indication

        @returns: The test results.

        """
        if object_path is None:
            logging.error('Invalid object path')
            return False

        start_notify = self.bluetooth_facade.start_notify(
            object_path, cccd_value)
        is_notifying = self._wait_for_condition(
            lambda: self.bluetooth_facade.is_notifying(
                object_path), method_name())

        self.results = {
            'start_notify': start_notify,
            'is_notifying': is_notifying}

        return all(self.results.values())


    @test_retry_and_log
    def test_stop_notify(self, object_path):
        """Test that a notification can be stopped on a characteristic

        @param object_path: the object path of the characteristic.

        @returns: The test results.

        """
        if object_path is None:
            logging.error('Invalid object path')
            return False

        stop_notify = self.bluetooth_facade.stop_notify(object_path)
        is_not_notifying = self._wait_for_condition(
            lambda: not self.bluetooth_facade.is_notifying(
                object_path), method_name())

        self.results = {
            'stop_notify': stop_notify,
            'is_not_notifying': is_not_notifying}

        return all(self.results.values())


    @test_retry_and_log(False)
    def test_set_discovery_filter(self, filter):
        """Test set discovery filter"""

        return self.bluetooth_facade.set_discovery_filter(filter)


    @test_retry_and_log(False)
    def test_set_le_connection_parameters(self, address, parameters):
        """Test set LE connection parameters"""

        return self.bluetooth_facade.set_le_connection_parameters(
            address, parameters)


    @test_retry_and_log(False)
    def test_get_connection_info(self, address):
        """Test that connection info to device is retrievable."""

        return (self.bluetooth_facade.get_connection_info(address)
                is not None)


    @test_retry_and_log(False, messages_stop=False)
    def test_suspend_and_wait_for_sleep(self, suspend, sleep_timeout):
        """ Suspend the device and wait until it is sleeping.

        @param suspend: Sub-process that does the actual suspend call.
        @param sleep_timeout time limit in seconds to allow the host sleep.

        @return True if host is asleep within a short timeout, False otherwise.
        """
        suspend.start()
        try:
            self.host.test_wait_for_sleep(sleep_timeout)
        except Exception as e:
            suspend.join()
            self.results = {'exception': str(e)}
            return False

        return True


    @test_retry_and_log(False, messages_start=False)
    def test_wait_for_resume(self,
                             boot_id,
                             suspend,
                             resume_timeout,
                             test_start_time,
                             resume_slack=RESUME_DELTA,
                             fail_on_timeout=False,
                             fail_early_wake=True,
                             collect_resume_time=False):
        """ Wait for device to resume from suspend.

        @param boot_id: Current boot id
        @param suspend: Sub-process that does actual suspend call.
        @param resume_timeout: Expect device to resume in given timeout.
        @param test_start_time: When was this test started? (device time)
        @param resume_slack: Allow some slack on resume timeout.
        @param fail_on_timeout: Fails if timeout is reached
        @param fail_early_wake: Fails if timeout isn't reached
        @param collect_resume_time: Collect time to resume as perf keyval.

        @return True if suspend sub-process completed without error.
        """
        success = False
        results = {}

        def _check_timeout(delta):
            if delta > timedelta(seconds=resume_timeout):
                return not fail_on_timeout
            else:
                return not fail_early_wake

        def _check_suspend_attempt_or_raise(test_start, wake_at):
            """Make sure suspend attempt was recent or raise TestNA.

            If we're looking at a previous suspend attempt, it means the test
            didn't trigger a suspend properly (i.e. no powerd call)

            @param test_start: When we started the test.
            @param wake_at: When powerd suspend resumed.

            @raises: error.TestNAError if found suspend occurred before we
                     started the test.
            """
            # If the last suspend attempt was before we started the test, it's
            # probably not a recent attempt.
            if wake_at < test_start:
                raise error.TestNAError(
                        'No recent suspend attempt found. '
                        'Started test at {} but last suspend ended at {}'.
                        format(test_start, wake_at))

            # If the last suspend attempt recorded time is some time in the
            # future, probably a time conversion error occurred.
            current_time = self.bluetooth_facade.get_device_utc_time()
            if current_time < wake_at:
                raise error.TestFail(
                        'Timezone conversion error found. '
                        'Last suspend ended at {} but current time is {}'.
                        format(wake_at, current_time))

            return True

        def _check_retcode_or_raise(retcode):
            """Make sure powerd return was successful.

            @param retcode: Return code of powerd_suspend.

            @raises: error.TestNAError if failed suspend due to non-BT
            @return: False if BT woke us, True otherwise
            """
            if retcode:
                if self.bluetooth_facade.bt_caused_last_resume():
                    return False
                else:
                    raise error.TestNAError(
                            'Failed suspend due to non-BT wake')

            return True

        # Sometimes it takes longer to resume from suspend; give some leeway
        resume_timeout = resume_timeout + resume_slack
        results['resume timeout'] = resume_timeout
        try:
            start = datetime.now()

            # Wait for resume needs to wait longer in case device rebooted.
            # Otherwise, the test will fail with errno 111 (connection refused)
            self.host.test_wait_for_resume(
                boot_id, resume_timeout=self.RESUME_INTERNAL_TIMEOUT_SECS)

            results['device accessible on resume'] = True

            # As of now, a timeout in test_wait_for_resume doesn't raise. Start
            # by first measuring the delta until network is back up to the dut.
            network_delta = datetime.now() - start

            # Use powerd logs to see how much time we actually spent in suspend
            # If the network went down during suspend, we will have spent less
            # time in suspend than expected. If we can't find info via powerd,
            # we can use measured time instead.
            info = self.bluetooth_facade.find_last_suspend_via_powerd_logs()
            if info:
                (start_suspend_at, end_suspend_at, retcode) = info
                actual_delta = end_suspend_at - start_suspend_at
                results['powerd time to resume'] = actual_delta.total_seconds()
                results['powerd retcode'] = retcode

                # Resume is successful if suspend occurred correctly and woke up
                # within the timeout. One significant caveat is that we only
                # fail here if BT blocked suspend, not if we woke spuriously.
                # This is by design (we depend on the timeout to check for
                # spurious wakeup).
                success = _check_suspend_attempt_or_raise(
                        test_start_time,
                        end_suspend_at) and _check_retcode_or_raise(
                                retcode) and _check_timeout(actual_delta)
            else:
                results['time to resume'] = network_delta.total_seconds()
                success = _check_timeout(network_delta)
        except error.TestFail as e:
            results['device accessible on resume'] = False
            success = False
            logging.error('wait_for_resume: %s', e)

            # If the resume failed due to a reboot, raise the testFail and exit
            # early from the test
            if 'client rebooted' in str(e):
                raise
        finally:
            suspend.join()

        # Log wake performance
        if collect_resume_time:
            test_desc = '{}_wake_time'.format(self.test_name.replace(' ', '_'))
            wake_time = results.get('powerd time to resume',
                                    results.get('time to resume', 0))
            # Only write perf if wake time exists (non-zero)
            if wake_time:
                self.write_perf_keyval({test_desc: wake_time})

        results['success'] = success
        results['suspend exit code'] = suspend.exitcode
        self.results = results

        return all([success, suspend.exitcode == 0])


    def suspend_async(self, suspend_time, expect_bt_wake=False):
        """ Suspend asynchronously and return process for joining

        @param suspend_time: how long to stay in suspend
        @param expect_bt_wake: Whether we expect bluetooth to wake us from
            suspend. If true, we expect this resume will occur early

        @returns multiprocessing.Process object with suspend task
        """

        def _action_suspend():
            try:
                self.bluetooth_facade.do_suspend(suspend_time, expect_bt_wake)
            except socket.error as e:
                # Socket errors may occur after suspend if the underlying
                # connection is lost during suspend (happens if usb-ethernet
                # disconnects and reconnects on resume). Catch all these errors
                # and swallow them.
                logging.warning(
                        'Socket error on suspend. Swallowing error: %s',
                        str(e))
            return 0

        proc = multiprocessing.Process(target=_action_suspend)
        proc.daemon = True
        return proc


    def device_connect_async(self,
                             device_type,
                             device,
                             adapter_address,
                             delay_wake=1,
                             should_wake=True):
        """ Connects peer device asynchronously with DUT.

        This function uses a thread instead of a subprocess so that the test
        result is stored for the test. Otherwise, the test connection was
        sometimes failing but the test itself was passing.

        @param device_type: The device type (used to check if it's LE)
        @param device: the meta device with the peer device
        @param adapter_address: the address of the adapter
        @param delay_wake: delay wakeup by this many seconds
        @param should_wake: Should this cause a wakeup?

        @returns threading.Thread object with device connect task
        """

        def _action_device_connect():
            time.sleep(delay_wake)
            if 'BLE' in device_type:
                # LE reconnects by advertising (dut controller will create LE
                # connection, not the peer device)
                self.test_device_set_discoverable(device, True)
            else:
                # Classic requires peer to initiate a connection to wake up the
                # dut
                connect_func = self.test_connection_by_device_only
                if should_wake:
                    connect_func(device, adapter_address)
                else:
                    # If we're not expecting wake, this connect attempt will
                    # probably fail.
                    self.ignore_failure(connect_func, device, adapter_address)

        thread = threading.Thread(target=_action_device_connect)
        return thread


    @test_retry_and_log(False)
    def test_hid_device_created(self, device_address):
        """ Tests that the hid device is created before using it for tests.

        @param device_address: Address of peripheral device
        """
        device_found = self.bluetooth_facade.wait_for_hid_device(
                device_address)
        self.results = {
                'device_found': device_found
        }
        return all(self.results.values())


    @test_retry_and_log(False)
    def test_hid_device_created_speed(self, device):
        """ Tests that the hid device is created with faster polling.

        @param device: Peripheral device
        """
        device_found = self.bluetooth_facade.wait_for_hid_device(
                device_address=device.address, sleep_interval=0.1)
        self.results = {'device_found': device_found}
        return all(self.results.values())


    @test_retry_and_log(False)
    def test_hid_device_reconnect_time(self, duration, device_type):
        """ Tests that the hid device reconnection is fast enough.

        @param duration: The averaged duration of HID reconnection
        @param device_type: Specified the type of the device
        """

        if 'BLE' in device_type:
            max_duration = LE_HID_RECONNECT_TIME_MAX_SEC
        else:
            max_duration = HID_RECONNECT_TIME_MAX_SEC

        self.results = {
                'hid_reconnect_time': duration,
                'max_passing_time': max_duration
        }
        return duration < max_duration


    @test_retry_and_log
    def test_battery_reporting(self, device):
        """ Tests that battery reporting through GATT can be received

        @param device: the meta device containing a Bluetooth device

        @returns: true if battery reporting is received
        """

        percentage = self.bluetooth_facade.get_battery_property(
                device.address, 'Percentage')

        return percentage > 0

    def _apply_new_adapter_alias(self, alias):
        """ Sets new system alias and applies discoverable setting

        @param alias: string alias to be applied to Adapter->Alias property
        """

        # Set Adapter's Alias property
        self.bluetooth_facade.set_adapter_alias(alias)

        # Set discoverable setting on
        self.bluetooth_facade.set_discoverable(True)

    @test_retry_and_log(False)
    def test_set_adapter_alias(self, alias):
        """ Validates that a new adapter alias is applied correctly

        @param alias: string alias to be applied to Adapter->Alias property

        @returns: True if the applied alias is properly applied in btmon trace
        """

        orig_alias = self.get_adapter_properties()['Alias']
        self.bluetooth_le_facade = self.bluetooth_facade

        # 1. Capture btmon logs around alias set operation
        self._get_btmon_log(lambda: self._apply_new_adapter_alias(alias))

        # 2. Verify that name appears in btmon trace with the following format:
        # "Name (complete): Chromebook_BA0E" as appears in EIR data set
        expected_alias_str = 'Name (complete): ' + alias
        alias_found = self.bluetooth_facade.btmon_find(expected_alias_str)

        # 3. Re-apply previous bluez alias as other tests expect default
        self.bluetooth_facade.set_adapter_alias(orig_alias)

        self.results = {'alias_found': alias_found}
        return all(self.results.values())

    # -------------------------------------------------------------------
    # Autotest methods
    # -------------------------------------------------------------------


    def initialize(self):
        """Initialize bluetooth adapter tests."""
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

        # Some tests may instantiate a peripheral device for testing.
        self.devices = dict()
        self.shared_peers = []
        for device_type in SUPPORTED_DEVICE_TYPES:
            self.devices[device_type] = list()

        # The count of registered advertisements.
        self.count_advertisements = 0


    def get_chipset_name(self):
        """ Get the name of BT/WiFi chipset on this host

        @returns chipset name if successful else ''
        """
        (vid,pid) = self.bluetooth_facade.get_wlan_vid_pid()
        logging.debug('Bluetooth module vid pid is %s %s', vid, pid)
        transport = self.bluetooth_facade.get_bt_transport()
        logging.debug('Bluetooth transport is %s', transport)
        if vid is None or pid is None:
            # Controllers that aren't WLAN+BT combo chips does not expose
            # Vendor ID/Product ID. Use alternate method.
            # This will return one of ['WCN3991', ''] or a string containing
            # the name of chipset read from DUT
            return self.bluetooth_facade.get_bt_module_name()
        for name, l in CHIPSET_TO_VIDPID.items():
            if ((vid, pid), transport) in l:
                return name
        return ''


    def get_device_sample_rssi(self, device, use_cached_value=True):
        """ Get one RSSI value of the given device.

        @param device: the peer device to be examined RSSI
        @param use_cached_value: Use the cached value

        @returns: rssi value if the device is found,
                  None otherwise
        """

        # Maximum retry attempts of RSSI query
        MAX_RETRY = 3
        # Time between each RSSI query
        WAIT_TIME = 2
        rssi = None

        # device could have tested RSSI if we enable check_rssi, if so, reuse it
        #
        # Note:
        # device is special in that hasattr(device, xxx) will evaluate to
        # the _Method class if xxx does not physically exist. Hence,
        # isinstance(device.rssi, int) instead of hasattr(device, 'rssi')
        # is used as the condition below.
        # Refer to class _Method in client/cros/chameleon/chameleon.py
        if isinstance(device.rssi, int) and use_cached_value:
            return device.rssi

        try:
            self.test_start_discovery()

            # The RSSI property is only maintained while discovery is
            # enabled.  Stopping discovery removes the property. Thus, look
            # up the RSSI without modifying discovery state.
            found = self.test_discover_device(device.address,
                                              start_discovery=False,
                                              stop_discovery=False)

            if not found:
                logging.info('Device %s not found', device.address)
                return None

            for i in range(MAX_RETRY):
                rssi = self.bluetooth_facade.get_device_property(
                        device.address, 'RSSI')
                if rssi:
                    break
                time.sleep(WAIT_TIME)

            if not rssi:
                logging.info('RSSI of device %s not found', device.address)
                return None

            device.rssi = rssi
            logging.info('Peer {} RSSI {}'.format(device.address, rssi))

        finally:
            self.test_stop_discovery()
            logging.info('Clearing device for test: {}'.format(device.address))
            self.bluetooth_facade.remove_device_object(device.address)

        return rssi

    def verify_device_rssi(self, device_list):
        """ Test device rssi is over required threshold.

        @param device_list: List of peer devices to verify rssi

        @raises error.TestNA if any device isn't found or RSSI is too low
        """
        try:
            self.test_start_discovery()
            for device in device_list:
                # The RSSI property is only maintained while discovery is
                # enabled.  Stopping discovery removes the property. Thus, look
                # up the RSSI without modifying discovery state.
                found = self.test_discover_device(device.address,
                                                  start_discovery=False,
                                                  stop_discovery=False)
                rssi = self.bluetooth_facade.get_device_property(
                        device.address, 'RSSI')

                if not found:
                    # Not clearing self.fails will result in test
                    # failing with test_discover_device failure
                    self.fails = []
                    logging.info(
                            'Failing with TEST_NA as peer %s was not'
                            ' discovered during RSSI check', device.address)
                    raise error.TestNAError(
                            'Peer {} not discovered during RSSI check'.format(
                                    device.address))

                if not rssi or rssi < self.MIN_RSSI:
                    logging.info('Failing with TEST_NA since RSSI (%s) is low ',
                                  rssi)
                    raise error.TestNAError(
                            'Peer {} RSSI is too low: {}'.format(
                                    device.address, rssi))
                device.rssi = rssi

                logging.info('Peer {} RSSI {}'.format(device.address, rssi))
        finally:
            self.test_stop_discovery()

            for device in device_list:
                logging.info('Clearing device for test: {}'.format(
                        device.address))
                self.bluetooth_facade.remove_device_object(device.address)

    def verify_controller_capability(self, required_roles=[],
                                     test_type=''):
        """Raise an exception if required role support isn't present

        @param required_roles: List of test role requirements in
                               ["central", "peripheral", "central-peripheral"]

        @raises: error.TestFail if device does not meet requirements
                                AND test_type is 'AVL'
                 error.TestNA if device does not meet requirements
                                and test_type is not 'AVL'
        """

        adapter_props = self.get_adapter_properties()

        supported_roles = adapter_props.get('Roles', [])

        for req in required_roles:
            if req not in supported_roles:
                # We don't meet requirements, throw error
                msg = 'Role requirement {} not in supported modes {}'.format(
                      req, supported_roles)

                if test_type == 'AVL':
                    raise error.TestFail(msg)

                logging.info('Failing with TEST_NA due to %s', msg)
                raise error.TestNAError(msg)


    def set_fail_fast(self, args_dict, default=False):
        """Set whether the test should fail fast if running into any problem

        By default it should not fail fast so that a batch test can continue
        running the rest after a failure in one test

        :param args_dict: the arguments passed int from the command line
        :param default: the default value when the flag is missing from the
                        args_dict

        """
        flag_name = 'fail_fast'
        if args_dict and flag_name in args_dict:
            self.fail_fast = bool(args_dict[flag_name].lower() == 'true')
        else:
            self.fail_fast = default


    def assert_discover_and_pair(self, device):
        """ Discovers and pairs given device. Automatically connects too.

        If any of the test expressions fail, it will raise an error so only call
        this function as a setup for a test.
        """
        self.assert_on_fail(self.test_device_set_discoverable(device, True))
        self.assert_on_fail(self.test_discover_device(device.address))
        self.assert_on_fail(
                self.test_pairing(device.address, device.pin, trusted=True))

    def identify_platform_failure_reasons(self):
        """ Identifies platform failure reasons to watch for in logs """
        s = self.bluetooth_facade.get_bt_usb_disconnect_str()
        if s:
            COMMON_FAILURES[s] = 'USB disconnect detected'

    def clean_bluetooth_kernel_log(self, level_name):
        """Remove Bluetooth kernel logs in /var/log/messages with equal or lower
        prioity than level_name

        @param level_name: name of the log level, e.x. 'INFO', 'DEBUG'...
        """
        self.bluetooth_facade.clean_bluetooth_kernel_log(
                KERNEL_LOG_LEVEL[level_name])

    def run_once(self, *args, **kwargs):
        """This method should be implemented by children classes.

        Typically, the run_once() method would look like:

        factory = remote_facade_factory.RemoteFacadeFactory(host)
        self.bluetooth_facade = factory.create_bluetooth_facade(self.floss)

        self.test_bluetoothd_running()
        # ...
        # invoke more self.test_xxx() tests.
        # ...

        if self.fails:
            raise error.TestFail(self.fails)

        """
        raise NotImplementedError


    def cleanup_bt_test(self, test_state='END'):
        """Clean up bluetooth adapter tests.

        @param test_state: string describing the requested clear is for
                           a new test(NEW), the middle of the test(MID),
                           or the end of the test(END).
        """

        if test_state == 'END':
            # Disable all the bluetooth debug logs
            self.enable_disable_debug_log(enable=False)

            # Re-enable cellular services
            self.enable_disable_cellular(enable=True)

            # Re-enable ui
            self.enable_disable_ui(enable=True)

            if hasattr(self, 'host'):
                # Stop btmon process
                self.host.run('pkill btmon || true')

                #Stop tcpdump usbmon process
                self.host.run('pkill tcpdump || true')


        # Close the device properly if a device is instantiated.
        # Note: do not write something like the following statements
        #           if self.devices[device_type]:
        #       or
        #           if bool(self.devices[device_type]):
        #       Otherwise, it would try to invoke bluetooth_mouse.__nonzero__()
        #       which just does not exist.
        for device_name, device_list  in self.devices.items():
            for device in device_list:
                if device is not None:
                    device.Close()

                    # Power cycle BT device if we're in the middle of a test
                    if test_state == 'MID':
                        device.PowerCycle()

        self.devices = dict()
        for device_type in SUPPORTED_DEVICE_TYPES:
            self.devices[device_type] = list()

    # Called only by test.test
    def cleanup(self):
        """Cleanup test.test instance"""

        self.cleanup_bt_test()
