# Lint as: python2, python3
# Copyright 2023 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import logging
import os
import re
import sys

from autotest_lib.client.bin import utils as client_utils
from autotest_lib.client.common_lib import error
from autotest_lib.server import utils
from autotest_lib.server.cros.bluetooth import bluetooth_adapter_tests
from autotest_lib.server.cros.tradefed import bundle_utils
from autotest_lib.server.cros.tradefed.tradefed_test import BundleSpecification
from autotest_lib.server.cros.tradefed.tradefed_test import TradefedTest

CTS_TARGET_MODULE = 'CtsBluetooth'
CTS_BUNDLE = 'arm'
CTS_URI = 'DEV'
CTS_TIMEOUT_SECONDS = 5400
CTS_CONFIG_RELATIVE_PATH = '../../cheets_CTS_{}/bundle_url_config.json'
ARC_FIELD_ID = 'CHROMEOS_ARC_ANDROID_SDK_VERSION'
ARC_VERSION_MAPPING = {'28': 'P', '30': 'R', '33': 'T'}
BT_ADDR_PATTERN = '([0-9A-F]{2}:){5}[0-9A-F]{2}'


class bluetooth_AdapterCTSHealth(TradefedTest,
                                 bluetooth_adapter_tests.BluetoothAdapterTests
                                 ):
    """Class to run Bluetooth CTS health tests"""

    def _tradefed_retry_command(self, template, session_id):
        """Needed by tradefed.

        Content is copy-pasted, except the forget device part.
        The reason is, we need to forget the device AFTER chrome is restarted,
        so that cannot be done earlier.
        """
        cmd = []
        for arg in template:
            cmd.append(arg.format(session_id=session_id))

        self.forget_bonded_devices()
        return cmd

    def _tradefed_run_command(self, template):
        """Needed by tradefed.

        Content is copy-pasted, except the forget device part.
        The reason is, we need to forget the device AFTER chrome is restarted,
        so that cannot be done earlier.
        """
        cmd = template[:]

        if self.arc_version == 'P':
            # Apply this PATH change only for chroot environment
            if not utils.is_in_container() and not client_utils.is_moblab():
                try:
                    os.environ['JAVA_HOME'] = '/opt/icedtea-bin-3.4.0'
                    os.environ['PATH'] = os.environ['JAVA_HOME']\
                                       + '/bin:' + os.environ['PATH']
                except OSError:
                    logging.error('Can\'t change current PATH directory')

            # Suppress redundant output from tradefed.
            cmd.append('--quiet-output=true')

        self.forget_bonded_devices()
        return cmd

    def _get_tradefed_base_dir(self):
        """Needed by tradefed. Content is copy-pasted."""
        return 'android-cts'

    def _tradefed_cmd_path(self):
        """Needed by tradefed. Content is copy-pasted."""
        return os.path.join(self._repository, 'tools', 'cts-tradefed')

    def _get_bundle_specification(self, uri, bundle):
        """Tradefed function to get the test bundle.

        This function is overrided to obtain the correct path for each arc
        versions.

        @param uri: determined by tradefed, could be 'DEV' or 'LATEST'
        @param bundle: always 'arm' in our case, but can also be 'x86'
        """
        test_path = sys.modules[self.__class__.__module__].__file__
        config_path = os.path.abspath(
                os.path.join(test_path,
                             CTS_CONFIG_RELATIVE_PATH.format(
                                     self.arc_version)))
        url_config = bundle_utils.load_config(config_path)
        bundle_password = bundle_utils.get_bundle_password(url_config)
        official_version_name = bundle_utils.get_official_version(url_config)
        suite_name = bundle_utils.get_suite_name(url_config)

        return BundleSpecification(
                bundle_utils.make_bundle_url(url_config, uri, bundle),
                bundle_password, official_version_name, suite_name)

    def probe_arc_version(self):
        """Detects the installed ARC version."""
        arc_version = ''
        cmd_result = self.host.run('cat', args=('/etc/lsb-release', ))
        output_text = cmd_result.stdout
        for line in output_text.splitlines():
            if ARC_FIELD_ID not in line:
                continue
            arc_version_num = line.split('=')[1].strip()
            arc_version = ARC_VERSION_MAPPING.get(arc_version_num)
            if not arc_version:
                raise error.TestFail('Unknown ARC version: %s; expected: %s',
                                     arc_version_num,
                                     ARC_VERSION_MAPPING.keys())
        if arc_version == '':
            raise error.TestFail('ARC version not found')

        self.arc_version = arc_version
        logging.info('ARC version %s detected', arc_version)

    def initialize_arc_templates(self):
        """Assigns the ARC templates.

        The templates are required by the tradefed test. The content is copy
        pasted from CTS test files.
        """
        if self.arc_version == 'P':
            self.run_template = [
                    'run', 'commandAndExit', 'cts', '--module',
                    'CtsBluetoothTestCases', '--logcat-on-failure',
                    '--dynamic-config-url='
            ]
            self.retry_template = [
                    'run', 'commandAndExit', 'retry', '--retry',
                    '{session_id}', '--dynamic-config-url='
            ]
        elif self.arc_version == 'R' or self.arc_version == 'T':
            self.run_template = [
                    'run', 'commandAndExit', 'cts', '--include-filter',
                    'CtsBluetoothTestCases', '--include-filter',
                    'CtsBluetoothTestCases[secondary_user]',
                    '--logcat-on-failure'
            ]
            self.retry_template = [
                    'run', 'commandAndExit', 'retry', '--retry', '{session_id}'
            ]

    def initialize(self, host):
        """Tradefed function to initialize the test.

        This function is overrided to store the arc_version, in order to
        avoid creating one test file for each of the arc versions.

        @param host: The DUT, usually a chromebook
        """
        if not host:
            raise error.TestFail('The host is unspecified')

        self.host = host
        self.probe_arc_version()
        self.initialize_arc_templates()

        TradefedTest.initialize(self,
                                bundle=CTS_BUNDLE,
                                uri=CTS_URI,
                                host=host)
        bluetooth_adapter_tests.BluetoothAdapterTests.initialize(self)

    def prepare_btpeers(self, args_dict):
        """Prepares the btpeers for the CTS test.

        We need two btpeers: a classic peer to be discoverable and an LE peer
        to advertise. We need to be able to receive both inquiry and
        advertisement to pass all CTS tests, therefore we require the two peers.

        It's ideal to use the same framework as the other BT adapter tests, but
        that is difficult to achieve since Tradefed tests has it's own quirks.
        Directly using both of them makes things complicated (such as both are
        trying to restart UI). Therefore, here we only reuse some methods and
        copy some parts of Bluetooth adapter tests.

        @param args_dict: The arguments passed from the command line
        """

        btpeer_args = self.host.get_btpeer_arguments(args_dict)
        self.host.initialize_btpeer(btpeer_args=btpeer_args)
        for btpeer in self.host.btpeer_list:
            btpeer.register_raspPi_log(self.outputdir)

        self.btpeer_group = dict()
        self.btpeer_group_copy = dict()
        self.group_btpeers_type()

        devices = {'KEYBOARD': 1, 'BLE_MOUSE': 1}
        is_enough_peer = self.get_device_rasp(devices)
        if not is_enough_peer:
            raise error.TestNAError('Not enough peers!')

        classic_peer = self.devices['KEYBOARD'][0]
        classic_peer.SetDiscoverable(True)
        ble_peer = self.devices['BLE_MOUSE'][0]
        ble_peer.SetDiscoverable(True)

    def stop_btpeers(self):
        """Stops the btpeers from being discoverable.

        This is just a courtesy to stop the scanning that is started on the
        prepare function. The outcome of the test is not impacted by anything
        inside this function, and it's safe not to call this at all.
        """

        classic_peer = self.devices['KEYBOARD'][0]
        classic_peer.SetDiscoverable(False)
        ble_peer = self.devices['BLE_MOUSE'][0]
        ble_peer.SetDiscoverable(False)

    def forget_bonded_devices(self):
        """Removes the bonded devices.

        We need to remove the bonded devices in order to prevent them
        interfering with the test result (e.g. DUT auto connects to them).
        This is done in the beginning of the test, similar to other Bluetooth
        tests. However, instead of calling test_reset_on_adapter(), we directly
        call some commands. This is done because test_reset_on_adapter needs
        bluetooth_facade with conflicts with the tradefed test.
        """
        if self.floss:
            # in btclient, peer address is enclosed with [], host address isn't.
            regex = re.compile('\[' + BT_ADDR_PATTERN + '\]')
            self.host.run('btclient',
                          args=('--command', 'adapter enable', '--timeout',
                                '5'))
            cmd_list = self.host.run('btclient',
                                     args=('--command', 'list bonded',
                                           '--timeout', '5'))
        else:
            regex = re.compile(BT_ADDR_PATTERN)
            self.host.run('bluetoothctl', args=('power', 'on'))
            cmd_list = self.host.run('bluetoothctl',
                                     args=('devices', 'Bonded'))

        output_list = cmd_list.stdout
        for line in output_list.splitlines():
            result = regex.search(line)
            if result is None:
                continue

            addr = result.group().strip('[]')
            if self.floss:
                self.host.run('btclient',
                              args=('--command', 'bond remove ' + addr,
                                    '--timeout', '5'))
            else:
                self.host.run('bluetoothctl', args=('remove', addr))

    def run_once(self, test_name=None, floss=False, args_dict=None):
        """Runs the batch of Bluetooth CTS health tests

        @param test_name: The name of the test
        @param floss: Is Bluetooth running Floss?
        @param args_dict: The arguments passed from the command line
        """
        self.floss = floss
        self.prepare_btpeers(args_dict)

        chrome_feature = None
        if floss:
            # A dirty way to disable floss prevention only for this test
            chrome_feature = 'Floss --disable-feature=FlossIsAvailabilityCheckNeeded'
        try:
            self._run_tradefed_with_retries(test_name=test_name,
                                            run_template=self.run_template,
                                            retry_template=self.retry_template,
                                            target_module=CTS_TARGET_MODULE,
                                            bundle=CTS_BUNDLE,
                                            timeout=CTS_TIMEOUT_SECONDS,
                                            chrome_feature=chrome_feature)
        finally:
            self.stop_btpeers()
