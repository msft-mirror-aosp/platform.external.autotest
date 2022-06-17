# Lint as: python2, python3
# Copyright 2022 The Chromium OS Authors. All rights reserved.
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
from autotest_lib.client.common_lib.cros import dev_server
from autotest_lib.server.cros import provisioner
from autotest_lib.server.cros.minios import minios_util
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

    def initialize(self, host):
        """
        Sets default variables for the test.

        @param host: The DUT we will be running on.

        """
        super(MiniOsTest, self).initialize(host)
        self._nebraska = None
        self._use_public_bucket = False
        self._servo = host.servo
        self._servo.initialize_dut()

    def warmup(self, running_at_desk=False, skip_provisioning=False):
        """
        Setup up minios autotests.

        MiniOS tests can have a failure condition that leaves the current
        active partition unbootable. To avoid this having an effect on other
        tests in a test suite, we provision and run the current installed
        version on the inactive partition to ensure the next test runs
        with the correct version of ChromeOS.

        @param running_at_desk: indicates test is run locally from a
            workstation.
        @param skip_provisioning: indicates test is run locally and provisioning
            of inactive partition should be skipped.

        """

        if skip_provisioning:
            logging.warning('Provisioning skipped.')
            return super(MiniOsTest, self).warmup()

        build_name = self._get_release_builder_path()

        # Install the matching build with quick provision.
        if running_at_desk:
            self._copy_quick_provision_to_dut()
            # Copy from gs://chromeos-image-archive instead of
            # gs://chromeos-release because of the format of build_name.
            # Ex: octopus-release/R102-14650.0.0
            update_url = self._get_provision_url_on_public_bucket(
                    build_name, is_release_bucket=False)
        else:
            if not self._autotest_devserver:
                self._autotest_devserver = dev_server.ImageServer.resolve(
                        build_name, self._host.hostname)
            update_url = self._autotest_devserver.get_update_url(build_name)

        logging.info('Provisioning inactive partition with update url: %s',
                     update_url)
        provisioner.ChromiumOSProvisioner(
                update_url,
                host=self._host,
                is_release_bucket=True,
                public_bucket=running_at_desk).run_provision()
        super(MiniOsTest, self).warmup()

    def cleanup(self):
        """Clean up minios autotests."""
        if self._nebraska:
            self._nebraska.stop()
        super(MiniOsTest, self).cleanup()
        # Make sure to reboot DUT into CroS in case of failures.
        self._host.reboot()
        # Restore the stateful partition.
        self._restore_stateful(public_bucket=self._use_public_bucket)

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
            pattern = r'\b%s\b' % self._MINIOS_KERNEL_FLAG
            if not re.search(pattern, self._host.get_cmdline()):
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
        statefuldev_url = self._stage_stateful(public_bucket)
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
                for dir in self._DEPENDENCY_DIRS
        ]
        try:
            self._download_and_extract_stateful(statefuldev_url,
                                                self._MINIOS_TEMP_STATEFUL_DIR,
                                                members=members,
                                                keep_symlinks=True)
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
