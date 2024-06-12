# Lint as: python2, python3
# Copyright 2018 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import contextlib
import logging
import os

from autotest_lib.client.common_lib import error
from autotest_lib.client.common_lib.cros.network import interface
from autotest_lib.server import autotest
from autotest_lib.server.cros.tradefed import tradefed_constants as constants


class MulticastDisabler(object):
    """Support class for disabling multicast on the test device.

    This is for stabilizing the cpu load by suppressing excessive
    network activities in the test lab network. The functionality
    is similar to common_lib.cros.network.MulticastDisabler, but
    this class works from the remote host.
    """
    SERVICE_CONTROL_TIMELIMIT = 10  # seconds

    def __init__(self, host):
        self._host = host
        self._disabled_iface = None

    def disable(self):
        """Disables mutlicast and remembers info for reenabling later."""
        try:
            # Avahi-deamon might reenable multicast. Disabling the service.
            self._host.run('stop avahi',
                           ignore_status=True,
                           timeout=MulticastDisabler.SERVICE_CONTROL_TIMELIMIT)

            iface = interface.Interface.get_connected_ethernet_interface(
                    host=self._host)
            if iface.is_multicast_enabled:
                iface.disable_multicast()
                self._disabled_iface = iface
        except Exception as e:
            logging.error('Failed to disable multicast.', exc_info=e)

    def reenable(self):
        """Reenables the multicast disabled by disable()."""
        try:
            if self._disabled_iface != None:
                self._disabled_iface.enable_multicast()
                self._disabled_iface = None

            self._host.run('start avahi',
                           timeout=MulticastDisabler.SERVICE_CONTROL_TIMELIMIT)
        except Exception as e:
            logging.error('Failed to re-enable multicast.', exc_info=e)


class ChromeLogin(object):
    """Context manager to handle Chrome login state."""

    def need_reboot(self, hard_reboot=False):
        """Marks state as "dirty" - reboot needed during/after test."""
        logging.info('Will reboot DUT when Chrome stops.')
        self._need_reboot = True
        if hard_reboot and self._host.servo:
            self._hard_reboot_on_failure = True

    def __init__(self,
                 host,
                 board=None,
                 dont_override_profile=False,
                 enable_default_apps=False,
                 toggle_ndk=False,
                 vm_force_max_resolution=False,
                 log_dir=None,
                 feature=None):
        """Initializes the ChromeLogin object.

        @param board: optional parameter to extend timeout for login for slow
                      DUTs. Used in particular for virtual machines.
        @param dont_override_profile: reuses the existing test profile if any
        @param enable_default_apps: enables default apps (like Files app)
        @param toggle_ndk: toggles native bridge engine switch.
        @param log_dir: Any log files for this Chrome session is written to this
               directory.
        """
        self._host = host
        self._timeout = constants.LOGIN_BOARD_TIMEOUT.get(
            board, constants.LOGIN_DEFAULT_TIMEOUT)
        self._dont_override_profile = dont_override_profile
        self._enable_default_apps = enable_default_apps
        self._need_reboot = False
        self._hard_reboot_on_failure = False
        self._toggle_ndk = toggle_ndk
        self._vm_force_max_resolution = vm_force_max_resolution
        self._log_dir = log_dir
        self._feature = feature
        self._multicast_disabler = MulticastDisabler(self._host)

    def _cmd_builder(self, verbose=False):
        """Gets remote command to start browser with ARC enabled."""
        # If autotest is not installed on the host, as with moblab at times,
        # getting the autodir will raise an exception.
        cmd = autotest.Autotest.get_installed_autodir(self._host)
        cmd += '/bin/autologin.py --arc'

        # We want to suppress the Google doodle as it is not part of the image
        # and can be different content every day interacting with testing.
        cmd += ' --no-startup-window'
        # Disable CPU restriction to de-flake perf sensitive tests.
        cmd += ' --disable-arc-cpu-restriction'
        # Disable several forms of auto-installation to stablize the tests.
        cmd += ' --no-arc-syncs'
        # Disable popup notifications to stabilize the tests.
        cmd += ' --no-popup-notification'
        # Always disable external storage for ARC
        cmd += ' --disable-feature=ArcExternalStorageAccess'
        # TODO(b/346689363): Revert this before M128 branch cut.
        cmd += ' --feature=NotificationWidthIncrease'
        # Toggle the translation from houdini to ndk
        if self._toggle_ndk:
            cmd += ' --toggle_ndk'
        if self._dont_override_profile:
            logging.info('Starting Chrome with a possibly reused profile.')
            cmd += ' --dont_override_profile'
        else:
            logging.info('Starting Chrome with a fresh profile.')
        if self._enable_default_apps:
            logging.info('Using --enable_default_apps to start Chrome.')
            cmd += ' --enable_default_apps'
        if self._vm_force_max_resolution:
            cmd += ' --vm_force_max_resolution'
        if self._feature:
            cmd += ' --feature=' + self._feature
        if not verbose:
            cmd += ' > /dev/null 2>&1'
        return cmd

    def _login_by_script(self, timeout, verbose):
        """Runs the autologin.py script on the DUT to log in."""
        self._host.run(
            self._cmd_builder(verbose=verbose),
            ignore_status=False,
            verbose=verbose,
            timeout=timeout)

    def _login(self, timeout, verbose=False, install_autotest=False):
        """Logs into Chrome. Raises an exception on failure."""
        if not install_autotest:
            try:
                # Assume autotest to be already installed.
                self._login_by_script(timeout=timeout, verbose=verbose)
            except autotest.AutodirNotFoundError:
                logging.warning('Autotest not installed, forcing install...')
                install_autotest = True

        if install_autotest:
            # Installs the autotest client to the DUT by running a no-op test.
            autotest.Autotest(self._host).run_timed_test(
                    'stub_Pass', timeout=2 * timeout, check_client_result=True)
            # The (re)run the login script.
            self._login_by_script(timeout=timeout, verbose=verbose)

        # Quick check if Android has really started. When autotest client
        # installed on the DUT was partially broken, the script may succeed
        # without actually logging into Chrome/Android. See b/129382439.
        self._host.run(
            # "/data/anr" is an arbitrary directory accessible only after
            # proper login and data mount.
            'android-sh -c "ls /data/anr"',
            ignore_status=False, timeout=9)

    def enter(self):
        """Logs into Chrome with retry."""
        timeout = self._timeout
        try:
            logging.info('Ensure Android is running (timeout=%d)...', timeout)
            self._login(timeout=timeout)
        except Exception as e:
            logging.error('Login failed.', exc_info=e)
            # Retry with more time, with refreshed client autotest installation,
            # and the DUT cleanup by rebooting. This can hide some failures.
            self._reboot()
            timeout *= 2
            logging.info('Retrying failed login (timeout=%d)...', timeout)
            try:
                self._login(timeout=timeout,
                            verbose=True,
                            install_autotest=True)
            except Exception as e2:
                logging.error('Failed to login to Chrome', exc_info=e2)

                # b/327969092: Provide more precise failure reason for analysis
                grep = self._host.run(
                        'grep "migrated to dircrypto" /var/log/chrome/chrome',
                        ignore_status=True,
                        timeout=10)
                if grep.exit_status == 0:
                    raise error.TestError(
                            'Failed to login to Chrome (b/327969092)')

                raise error.TestError('Failed to login to Chrome')

        # Disable multicast for stable testing. This is done after the login,
        # because Chrome boot can reenable multicast.
        self._multicast_disabler.disable()

    def exit(self):
        """On exit restart the browser or reboot the machine.

        If self._log_dir is set, the VM kernel log is written
        to a file.

        """
        if self._log_dir:
            self._write_kernel_log()

        # Recover the disabled multicast
        self._multicast_disabler.reenable()

        if not self._need_reboot:
            try:
                self._restart()
            except:
                logging.error('Restarting browser has failed.')
                self.need_reboot()
        if self._need_reboot:
            self._reboot()

    def _write_kernel_log(self):
        """Writes ARCVM kernel logs."""
        if not os.path.exists(self._log_dir):
            os.makedirs(self._log_dir)

        output_path = os.path.join(
                self._log_dir, '%s_vm_pstore_dump.txt' % self._host.hostname)

        with open(output_path, 'w') as f:
            try:
                logging.info('Getting VM kernel logs.')
                self._host.run('/usr/bin/vm_pstore_dump', stdout_tee=f)
            except Exception as e:
                logging.error('vm_pstore_dump command failed: %s', e)
            else:
                logging.info('Wrote VM kernel logs.')

    def _restart(self):
        """Restart Chrome browser."""
        # We clean up /tmp (which is memory backed) from crashes and
        # other files. A reboot would have cleaned /tmp as well.
        # TODO(ihf): Remove "start ui" which is a nicety to non-ARC tests (i.e.
        # now we wait on login screen, but login() above will 'stop ui' again
        # before launching Chrome with ARC enabled).
        logging.info('Skipping reboot, restarting browser.')
        script = 'stop ui'
        script += '&& find /tmp/ -mindepth 1 -delete '
        script += '&& start ui'
        self._host.run(script, ignore_status=False, verbose=False, timeout=120)

    def _reboot(self):
        """Reboot the machine."""
        if self._hard_reboot_on_failure:
            logging.info('Powering OFF the DUT: %s', self._host)
            self._host.servo.get_power_state_controller().power_off()
            logging.info('Powering ON the DUT: %s', self._host)
            self._host.servo.get_power_state_controller().power_on()
        else:
            logging.info('Rebooting...')
            self._host.reboot()


@contextlib.contextmanager
def login_chrome(hosts, **kwargs):
    """Returns Chrome log-in context manager for multiple hosts. """
    # TODO(pwang): Chromelogin takes 10+ seconds for it to successfully
    #              enter. Parallelize if this becomes a bottleneck.
    instances = [ChromeLogin(host, **kwargs) for host in hosts]
    for instance in instances:
        instance.enter()
    yield instances
    for instance in instances:
        instance.exit()
