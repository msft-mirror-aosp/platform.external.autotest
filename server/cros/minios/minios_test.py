# Lint as: python2, python3
# Copyright 2022 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import json
import logging
import os
import re
import time

from autotest_lib.client.common_lib import error
from autotest_lib.client.common_lib.cros.network import xmlrpc_datatypes
from autotest_lib.server.cros.minios import minios_util
from autotest_lib.server.cros.network import wifi_test_context_manager
from autotest_lib.server.cros.update_engine import update_engine_test


class MiniOsTest(update_engine_test.UpdateEngineTest):
    """
    Base class that sets up helper objects/functions for NBR tests.

    """

    _ETHERNET_LABEL = 'Ethernet'
    _MINIOS_CLIENT_CMD = 'minios_client'
    _MINIOS_KERNEL_FLAG = 'cros_minios'

    # Period to wait for firmware screen in seconds.
    # Value based on Brya, which is the slowest so far.
    _FIRMWARE_SCREEN_TIMEOUT = 30

    # Number of times to attempt booting into MiniOS.
    _MINIOS_BOOT_MAX_ATTEMPTS = 3

    # Timeout periods, given in seconds.
    _MINIOS_SHUTDOWN_TIMEOUT = 30

    # Number of seconds to wait for the host to boot into MiniOS. Should always
    # be greater than `_FIRMWARE_SCREEN_TIMEOUT`.
    _MINIOS_WAIT_UP_TIME_SECONDS = 120

    # Version reported to OMAHA/NEBRASKA for recovery.
    _RECOVERY_VERSION = '0.0.0.0'

    # Files used by the tests.
    _DEPENDENCY_DIRS = ['bin', 'lib', 'lib64', 'libexec']
    _DEPENDENCY_INSTALL_DIR = '/usr/local'
    _MINIOS_TEMP_STATEFUL_DIR = '/usr/local/tmp/stateful'
    _STATEFUL_DEV_IMAGE_NAME = 'dev_image_new'

    # Wildcards form of '_DEPENDENCY_DIRS' used for robust extraction from
    # stateful archive given that the contents of the stateful archive varies
    # based on DUT CPU architecture.
    _DEPENDENCY_DIRS_PATTERN = ['bin', 'lib*']

    # Additional log files to be extracted from MiniOS.
    _MESSAGES_LOG = '/var/log/messages'
    _NET_LOG = '/var/log/net.log'
    _UPSTART_LOG = '/var/log/upstart.log'

    # MiniOS State values from platform/system_api/dbus/minios/minios.proto.
    _MINIOS_STATE_ERROR = 'ERROR'
    _MINIOS_STATE_IDLE = 'IDLE'
    _MINIOS_STATE_NETWORK_SELECTION = 'NETWORK_SELECTION'
    _MINIOS_STATE_NETWORK_CONNECTED = 'CONNECTED'
    _MINIOS_STATE_NETWORK_CREDENTIALS = 'NETWORK_CREDENTIALS'
    _MINIOS_STATE_RECOVERING = 'RECOVERING'

    # Arrays used to build iptables commands.
    _DROP_OUTGOING_PACKETS = ['OUTPUT', '-p', 'tcp', '-j', 'DROP']
    # Filter DEVSERVER(8082) and GS-CACHE(8888) for when running in the lab.
    # Also filter HTTP(80) and HTTPS(443) ports for when running at desk.
    _PORTS_TO_FILTER = ['80', '443', '8082', '8888']

    _GET_STATE_EXTRACTOR = re.compile(r'State is (\w+)')

    def initialize(self, host, wifi_configs=None, running_at_desk=None,
                   skip_provisioning=None):
        """
        Sets default variables for the test.

        @param host: The DUT we will be running on.
        @param wifi_configs: List containing access point configuration dict and
            wifi client configuration dict.
        @param running_at_desk: indicates test is run locally from a
            workstation.
        @param skip_provisioning: indicates test is run locally and provisioning
            of inactive partition should be skipped.

        """
        super(MiniOsTest, self).initialize(host)
        self._nebraska = None
        self._use_public_bucket = minios_util.to_bool(running_at_desk)
        self._skip_provisioning = minios_util.to_bool(skip_provisioning)
        self._servo = host.servo
        self._servo.initialize_dut()
        self._minios_resultsdir = os.path.join(self.resultsdir, 'minios')
        os.mkdir(self._minios_resultsdir)
        self._wifi_configs = wifi_configs
        self._wifi_context = None

    def warmup(self, host, **kwargs):
        """
        Setup up minios autotests.

        MiniOS tests can have a failure condition that leaves the current
        active partition unbootable. To avoid this having an effect on other
        tests in a test suite, we provision and run the current installed
        version on the inactive partition to ensure the next test runs
        with the correct version of ChromeOS.
        Additionally, if wifi_configs is provided, we setup and validate the
        wifi context.

        @param host: The DUT we will be running on.
        @param **kwargs: Dict of key, value settings from command line to passed
            on to the wifi context manager.
            See `cros.network.WiFiTestContextManager` for relevant arguments.

        """
        if not self._skip_provisioning:
            self.provision_dut(build_name=self._get_release_builder_path(),
                               public_bucket=self._use_public_bucket)
        if self._wifi_configs:
            self._setup_wifi_context(host, kwargs)
        super(MiniOsTest, self).warmup()

    def cleanup(self):
        """Clean up minios autotests."""
        # Our wifi context is configured to only run the client and the
        # router. Since, we booted into MiniOS and lost the client
        # (xmlrpc server) running on the DUT. We therefore cannot use the
        # teardown method on the wifi_context. We therefore only close the
        # router.
        if self._wifi_context:
            self._wifi_context.router.close()
        if self._nebraska:
            self._nebraska.stop()
        if self._is_running_minios():
            # Make sure to reboot DUT into CroS in case of failures.
            self._minios_cleanup()
            self._host.reboot()
        # Restore the stateful partition.
        self._restore_stateful(public_bucket=self._use_public_bucket)
        super(MiniOsTest, self).cleanup()

    @property
    def wifi_context(self):
        """@return the WiFi context for this test."""
        return self._wifi_context

    def _minios_cleanup(self):
        """
        Perform any cleanup operations before we exit MiniOS.

        MiniOS runs purely from ramfs and thus all data is lost when we exit
        MiniOS. We therefore need to perform any cleanup functions like grabbing
        logs before MiniOS exits. This function should be called just before
        rebooting out of MiniOS.
        """
        if self._host:
            self._host.get_file(self._MESSAGES_LOG, self._minios_resultsdir)
            self._host.get_file(self._NET_LOG, self._minios_resultsdir)
            self._host.get_file(self._UPDATE_ENGINE_LOG_DIR,
                                self._minios_resultsdir)
            self._host.get_file(self._UPSTART_LOG, self._minios_resultsdir)
        if self._nebraska:
            self._host.get_file(os.path.join('/tmp', self._NEBRASKA_LOG),
                                self._minios_resultsdir)

    def _is_running_minios(self):
        """Returns True if the DUT is booted into MiniOS."""
        pattern = r'\b%s\b' % self._MINIOS_KERNEL_FLAG
        return re.search(pattern, self._host.get_cmdline())

    def _boot_minios(self):
        """Boot the DUT into MiniOS."""
        # Turn off usbkey to avoid booting into usb-recovery image.
        self._servo.switch_usbkey('off')
        psc = self._servo.get_power_state_controller()
        psc.power_off()
        psc.power_on(psc.REC_ON)
        self._host.test_wait_for_shutdown(self._MINIOS_SHUTDOWN_TIMEOUT)
        logging.info('Waiting for firmware screen')
        time.sleep(self._FIRMWARE_SCREEN_TIMEOUT)

        # Attempt multiple times to boot into MiniOS. If all attempts fail then
        # this is some kind of firmware issue. Since we failed to boot an OS use
        # servo to reset the unit and then report test failure.
        attempts = 0
        minios_is_up = False
        while not minios_is_up and attempts < self._MINIOS_BOOT_MAX_ATTEMPTS:
            # Use Ctrl+R shortcut to boot 'MiniOS
            logging.info('Try to boot MiniOS')
            self._servo.ctrl_r()
            minios_is_up = self._host.wait_up(
                    timeout=self._MINIOS_WAIT_UP_TIME_SECONDS,
                    host_is_down=True)
            attempts += 1

        if minios_is_up:
            # If mainfw_type is recovery then we are in MiniOS.
            mainfw_type = self._host.run_output('crossystem mainfw_type')
            if mainfw_type != 'recovery':
                raise error.TestError(
                        'Boot to MiniOS - invalid firmware: %s.' % mainfw_type)
            # There are multiple types of recovery images, make sure we booted
            # into minios.
            if not self._is_running_minios():
                raise error.TestError(
                        'Boot to MiniOS - recovery image is not minios.')
        else:
            # Try to not leave unit on recovery firmware screen.
            self._host.power_cycle()
            raise error.TestError('Boot to MiniOS failed.')

    def _create_minios_hostlog(self):
        """Create the minios hostlog file.

        To ensure the recovery was successful we need to compare the update
        events against expected update events. This function creates the hostlog
        for minios before the recovery reboots the DUT.

        """
        # Check that update logs exist.
        if len(self._get_update_engine_logs()) < 1:
            err_msg = 'update_engine logs are missing. Cannot verify recovery.'
            raise error.TestFail(err_msg)

        # Download the logs instead of reading it over the network since it will
        # disappear after MiniOS reboots the DUT.
        logfile = os.path.join(self.resultsdir, 'minios_update_engine.log')
        self._host.get_file(self._UPDATE_ENGINE_LOG, logfile)
        logfile_content = None
        with open(logfile) as f:
            logfile_content = f.read()
        minios_hostlog = os.path.join(self.resultsdir, 'hostlog_minios')
        with open(minios_hostlog, 'w') as fp:
            # There are four expected hostlog events during recovery.
            extract_logs = self._extract_request_logs(logfile_content)
            json.dump(extract_logs[-4:], fp)
        return minios_hostlog

    def _install_test_dependencies(self, public_bucket=False):
        """
        Install test dependencies from a downloaded stateful archive.

        @param public_bucket: True to download stateful from a public bucket.

        """
        statefuldev_url = self._get_stateful_url(public_bucket)
        logging.info('Installing dependencies from %s', statefuldev_url)

        # Create destination directories.
        minios_dev_image_dir = os.path.join(self._MINIOS_TEMP_STATEFUL_DIR,
                                            self._STATEFUL_DEV_IMAGE_NAME)
        install_dirs = [
                os.path.join(self._DEPENDENCY_INSTALL_DIR, dir)
                for dir in self._DEPENDENCY_DIRS
        ]
        self._run(['mkdir', '-p', minios_dev_image_dir] + install_dirs)
        # Symlink the install dirs into the staging destination.
        for dir in install_dirs:
            self._run(['ln', '-s', dir, minios_dev_image_dir])

        # Generate the list of stateful archive members that we want to extract.
        members = [
                os.path.join(self._STATEFUL_DEV_IMAGE_NAME, dir)
                for dir in self._DEPENDENCY_DIRS_PATTERN
        ]
        try:
            self._download_and_extract_stateful(statefuldev_url,
                                                self._MINIOS_TEMP_STATEFUL_DIR,
                                                members=members,
                                                keep_symlinks=True,
                                                wildcards=True)
        except error.AutoservRunError as e:
            err_str = 'Failed to install the test dependencies'
            raise error.TestFail('%s: %s' % (err_str, str(e)))

        self._setup_python_symlinks()

        # Clean-up unused files to save memory.
        self._run(['rm', '-rf', self._MINIOS_TEMP_STATEFUL_DIR])

    def _setup_python_symlinks(self):
        """
        Create symlinks in the root to point to all python paths in /usr/local
        for stateful installed python to work. This is needed because Gentoo
        creates wrappers with hardcoded paths to the root (e.g. python-exec).

        """
        for path in self._DEPENDENCY_DIRS:
            self._run([
                    'find',
                    os.path.join(self._DEPENDENCY_INSTALL_DIR, path),
                    '-maxdepth', '1', '\(', '-name', 'python*', '-o', '-name',
                    'portage', '\)', '-exec', 'ln', '-s', '{}',
                    os.path.join('/usr', path), '\;'
            ])

    def _start_nebraska(self, payload_url=None):
        """
        Initialize and start nebraska on the DUT.

        @param payload_url: The payload to served by nebraska.

        """
        if not self._nebraska:
            self._nebraska = minios_util.NebraskaService(
                    self, self._host, payload_url)
        self._nebraska.start()

    def _verify_reboot(self, old_boot_id):
        """
        Verify that the unit rebooted using the boot_id.

        @param old_boot_id A boot id value obtained before the
                               reboot.

        """
        self._host.test_wait_for_shutdown(self._MINIOS_SHUTDOWN_TIMEOUT)
        self._host.test_wait_for_boot(old_boot_id)
        self._should_restore_stateful = True

    def _drop_download_traffic(self):
        """
        Insert Iptables rules to drop outgoing HTTP(S) packets. This simulates
        a dropped network connection.

        """
        iptables_add_rule = ['iptables', '-I']
        for port in self._PORTS_TO_FILTER:
            self._run(iptables_add_rule + self._DROP_OUTGOING_PACKETS +
                      ['--dport', port])

    def _restore_download_traffic(self):
        """
        Attempt to remove Iptables rules that drop outgoing HTTP(S) packets if
        any. This simulates restoration of a dropped network connection.

        """
        iptables_delete_rule = ['iptables', '-D']
        for port in self._PORTS_TO_FILTER:
            self._run(iptables_delete_rule + self._DROP_OUTGOING_PACKETS +
                      ['--dport', port],
                      ignore_status=True)

    def _next_screen(self):
        """
        Advance MiniOS recovery to the next screen (next step).

        """
        self._run([self._MINIOS_CLIENT_CMD, '--next_screen'])

    def _prev_screen(self):
        """
        Advance MiniOS recovery to the previous screen (previous step).

        """
        self._run([self._MINIOS_CLIENT_CMD, '--prev_screen'])

    def _set_network_credentials(self, network_name, network_password=None):
        """
        Set the network and optional password that MiniOS should connect to.

        @param network_name: The name of the network to connect to for recovery.
        @param network_password: Optional password for the network.

        """
        cmd = [
                self._MINIOS_CLIENT_CMD, '--set_credentials',
                '--network_name=%s' % network_name
        ]
        if network_password:
            cmd += ['--network_password=%s' % network_password]
        logging.info('Setting network credentials for %s.', network_name)
        self._run(cmd)

    def _get_minios_state(self):
        """
        Get the current state of MiniOS from the command
        'minios_client --get_state'.

        @return The string value of the current MiniOS state.

        """
        result = self._run([self._MINIOS_CLIENT_CMD,
                            '--get_state']).stderr.rstrip()
        state_match = self._GET_STATE_EXTRACTOR.search(result)
        return state_match.group(1) if state_match else None

    def _validate_minios_state(self, expected_state):
        """
        Check if MiniOS is in the expected state.

        @param expected_state: The expected state that we want to validate.

        """
        state = self._get_minios_state()
        if expected_state != state:
            raise error.TestFail('%s not found. State is %s' %
                                 (expected_state, state))

    def _wait_for_minios_state(self, state_to_wait_for, timeout=3600):
        """
        Wait for the MiniOS to reach a certain state.

        @param state_to_wait_for: The MiniOS state to wait for.
        @param timeout: How long to wait before giving in seconds.

        """
        expiration = time.time() + timeout
        while True:
            state = self._get_minios_state()
            if state_to_wait_for == state:
                break
            time.sleep(1)
            if time.time() > expiration:
                raise error.TestFail('MiniOS did not achieve state: %s before'
                                     'timeout. Current state: %s.' %
                                     (state_to_wait_for, state))

    def _setup_wifi_context(self, host, cmdline_args):
        """
        Setup Wifi context with a router but no packet capture or attenuator.

        @param host: The DUT that will be using the wifi context.
        @param cmdline_args: Dict of key, value settings from command line to
            be passed on to the wifi context manager.
            See `cros.network.WiFiTestContextManager` for relevant arguments.


        """
        logging.debug('Running MiniOS wifi test with arguments: %r.',
                      cmdline_args)
        self._wifi_context = wifi_test_context_manager.WiFiTestContextManager(
            self.__class__.__name__,
            host,
            cmdline_args,
            self.debugdir)

        self._wifi_context.setup(include_pcap=False, include_attenuator=False)

        msg = '======= MiniOS wifi setup complete. Starting test... ======='
        self._wifi_context.client.shill_debug_log(msg)

    def _configure_network_for_test(self):
        """
        Configures the appropriate network for the test.

        For tests that do not use Wifi, this is a no-op.
        For tests that use Wifi, we setup the AP and verify that we can connect
        to it.

        @return a tuple containing the network name and network password if any.

        """
        # Not a wifi test, thus no-op.
        if not self._wifi_configs:
            return (MiniOsTest._ETHERNET_LABEL, None)
        for ap_config, client_conf in self._wifi_configs:
            client_conf.ssid = self._configure_and_connect_to_ap(ap_config)
            return (client_conf.ssid, client_conf.security_config.psk)

    def _configure_and_connect_to_ap(self, ap_config):
        """
        Configure the router as an AP with the given config and connect
        the DUT to it.

        @param ap_config HostapConfig object.

        @return ssid of the configured AP.

        """
        if not self._wifi_context:
            raise error.TestError(
                'Cannot configure access point - no wifi context provided.')
        self._wifi_context.configure(ap_config)
        ap_ssid = self._wifi_context.router.get_ssid()
        assoc_params = xmlrpc_datatypes.AssociationParameters(
                ssid=ap_ssid, security_config=ap_config.security_config)
        self._wifi_context.assert_connect_wifi(assoc_params)
        return ap_ssid
