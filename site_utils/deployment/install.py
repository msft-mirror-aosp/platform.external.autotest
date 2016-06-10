#!/usr/bin/env python
# Copyright 2015 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Install an initial test image on a set of DUTs.

The methods in this module are meant for two nominally distinct use
cases that share a great deal of code internally.  The first use
case is for deployment of DUTs that have just been placed in the lab
for the first time.  The second use case is for use after repairing
a servo.

Newly deployed DUTs may be in a somewhat anomalous state:
  * The DUTs are running a production base image, not a test image.
    By extension, the DUTs aren't reachable over SSH.
  * The DUTs are not necessarily in the AFE database.  DUTs that
    _are_ in the database should be locked.  Either way, the DUTs
    cannot be scheduled to run tests.
  * The servos for the DUTs need not be configured with the proper
    board.

More broadly, it's not expected that the DUT will be working at the
start of this operation.  If the DUT isn't working at the end of the
operation, an error will be reported.

The script performs the following functions:
  * Configure the servo for the target board, and test that the
    servo is generally in good order.
  * For the full deployment case, install dev-signed RO firmware
    from the designated stable test image for the DUTs.
  * For both cases, use servo to install the stable test image from
    USB.
  * If the DUT isn't in the AFE database, add it.

The script imposes these preconditions:
  * Every DUT has a properly connected servo.
  * Every DUT and servo have proper DHCP and DNS configurations.
  * Every servo host is up and running, and accessible via SSH.
  * There is a known, working test image that can be staged and
    installed on the target DUTs via servo.
  * Every DUT has the same board.
  * For the full deployment case, every DUT must be in dev mode,
    and configured to allow boot from USB with ctrl+U.

The implementation uses the `multiprocessing` module to run all
installations in parallel, separate processes.

"""

import functools
import json
import logging
import multiprocessing
import os
import shutil
import subprocess
import sys
import tempfile
import time

import common
from autotest_lib.client.common_lib import error
from autotest_lib.client.common_lib import host_states
from autotest_lib.client.common_lib import time_utils
from autotest_lib.client.common_lib import utils
from autotest_lib.server import frontend
from autotest_lib.server import hosts
from autotest_lib.server.hosts import servo_host
from autotest_lib.server.cros.dynamic_suite.constants import VERSION_PREFIX
from autotest_lib.server.hosts import servo_host
from autotest_lib.site_utils.deployment import commandline
from autotest_lib.site_utils.suite_scheduler.constants import Labels


_LOG_FORMAT = '%(asctime)s | %(levelname)-10s | %(message)s'

_DEFAULT_POOL = Labels.POOL_PREFIX + 'suites'

_DIVIDER = '\n============\n'

_OMAHA_STATUS = 'gs://chromeos-build-release-console/omaha_status.json'

# Lock reasons we'll pass when locking DUTs, depending on the
# host's prior state.
_LOCK_REASON_EXISTING = 'Repairing or deploying an existing host'
_LOCK_REASON_NEW_HOST = 'Repairing or deploying a new host'


def _report_write(report_log, message):
    """Write a message to the report log.

    Report output goes both to stdout, and to a given report
    file.

    @param report_log   Write the message here and to stdout.
    @param message      Write this message.
    """
    report_log.write(message)
    sys.stdout.write(message)


def _get_omaha_build(board):
    """Get the currently preferred Beta channel build for `board`.

    Open and read through the JSON file provided by GoldenEye that
    describes what version Omaha is currently serving for all boards
    on all channels.  Find the entry for `board` on the Beta channel,
    and return that version string.

    @param board  The board to look up from GoldenEye.

    @return Returns a Chrome OS version string in standard form
            R##-####.#.#.  Will return `None` if no Beta channel
            entry is found.
    """
    omaha_board = board.replace('_', '-')
    sp = subprocess.Popen(['gsutil', 'cat', _OMAHA_STATUS],
                          stdout=subprocess.PIPE)
    omaha_status = json.load(sp.stdout)
    for e in omaha_status['omaha_data']:
        if (e['channel'] == 'beta' and
                e['board']['public_codename'] == omaha_board):
            milestone = e['chrome_version'].split('.')[0]
            build = e['chrome_os_version']
            return 'R%s-%s' % (milestone, build)
    return None


def _update_build(afe, report_log, arguments):
    """Update the stable_test_versions table.

    This calls the `set_stable_version` RPC call to set the stable
    test version selected by this run of the command.  The
    version is selected from three possible versions:
      * The stable test version currently in the AFE database.
      * The version Omaha is currently serving as the Beta channel
        build.
      * The version supplied by the user.
    The actual version selected will be whichever of these three is
    the most up-to-date version.

    This function will log information about the available versions
    prior to selection.

    @param afe          AFE object for RPC calls.
    @param report_log   File-like object for logging report output.
    @param arguments    Command line arguments with options.

    @return Returns the version selected.
    """
    afe_version = afe.run('get_stable_version',
                          board=arguments.board)
    omaha_version = _get_omaha_build(arguments.board)
    _report_write(report_log, 'AFE   version is %s.\n' % afe_version)
    _report_write(report_log, 'Omaha version is %s.\n' % omaha_version)
    if (omaha_version is not None and
            utils.compare_versions(afe_version, omaha_version) < 0):
        version = omaha_version
    else:
        version = afe_version
    if arguments.build:
        if utils.compare_versions(arguments.build, version) >= 0:
            version = arguments.build
        else:
            _report_write(report_log,
                          'Selected version %s is too old.\n' %
                          arguments.build)
    if version != afe_version and not arguments.nostable:
        afe.run('set_stable_version',
                version=version,
                board=arguments.board)
    return version


def _create_host(hostname, afe_host):
    """Create a CrosHost object for a DUT to be installed.

    @param hostname  Hostname of the target DUT.
    @param afe_host  AFE Host object for the DUT.
    """
    machine_dict = {'hostname': hostname, 'afe_host': afe_host}
    servo_args = hosts.CrosHost.get_servo_arguments({})
    return hosts.create_host(machine_dict, servo_args=servo_args)


def _configure_install_logging(log_name):
    """Configure the logging module for `_install_dut()`.

    @param log_name  Name of the log file for all output.
    """
    # In some cases, autotest code that we call during install may
    # put stuff onto stdout with 'print' statements.  Most notably,
    # the AFE frontend may print 'FAILED RPC CALL' (boo, hiss).  We
    # want nothing from this subprocess going to the output we
    # inherited from our parent, so redirect stdout and stderr here,
    # before we make any AFE calls.  Note that this does what we
    # want only because we're in a subprocess.
    sys.stdout = open(log_name, 'w')
    sys.stderr = sys.stdout
    handler = logging.StreamHandler(sys.stderr)
    formatter = logging.Formatter(_LOG_FORMAT, time_utils.TIME_FMT)
    handler.setFormatter(formatter)
    root_logger = logging.getLogger()
    for h in root_logger.handlers:
        root_logger.removeHandler(h)
    root_logger.addHandler(handler)


def _try_lock_host(afe_host):
    """Lock a host in the AFE, and report whether it succeeded.

    The lock action is logged regardless of success; failures are
    logged if they occur.

    @param afe_host AFE Host instance to be locked.

    @return `True` on success, or `False` on failure.
    """
    try:
        logging.warning('Locking host now.')
        afe_host.modify(locked=True,
                        lock_reason=_LOCK_REASON_EXISTING)
    except Exception as e:
        logging.exception('Failed to lock: %s', e)
        return False
    return True


def _try_unlock_host(afe_host):
    """Unlock a host in the AFE, and report whether it succeeded.

    The unlock action is logged regardless of success; failures are
    logged if they occur.

    @param afe_host AFE Host instance to be unlocked.

    @return `True` on success, or `False` on failure.
    """
    try:
        logging.warning('Unlocking host.')
        afe_host.modify(locked=False, lock_reason='')
    except Exception as e:
        logging.exception('Failed to unlock: %s', e)
        return False
    return True


def _get_afe_host(afe, hostname, arguments):
    """Get an AFE Host object for the given host.

    If the host is found in the database, return the object
    from the RPC call.

    If no host is found, create one with appropriate servo
    attributes and the given board label.

    @param afe        AFE from which to get the host.
    @param hostname   Name of the host to look up or create.
    @param arguments  Command line arguments with options.

    @return A tuple of the afe_host, plus a flag. The flag indicates
            whether the Host should be unlocked if subsequent operations
            fail.  (Hosts are always unlocked after success).
    """
    hostlist = afe.get_hosts([hostname])
    unlock_on_failure = False
    if hostlist:
        afe_host = hostlist[0]
        if not afe_host.locked:
            if _try_lock_host(afe_host):
                unlock_on_failure = True
            else:
                raise Exception('Failed to lock host')
        if afe_host.status not in host_states.IDLE_STATES:
            if unlock_on_failure and not _try_unlock_host(afe_host):
                raise Exception('Host is in use, and failed to unlock it')
            raise Exception('Host is in use by Autotest')
    else:
        afe_host = afe.create_host(hostname,
                                   locked=True,
                                   lock_reason=_LOCK_REASON_NEW_HOST)
        servo_hostname = servo_host.make_servo_hostname(hostname)
        servo_port = str(servo_host.ServoHost.DEFAULT_PORT)
        afe.set_host_attribute(servo_host.SERVO_HOST_ATTR,
                               servo_hostname,
                               hostname=hostname)
        afe.set_host_attribute(servo_host.SERVO_PORT_ATTR,
                               servo_port,
                               hostname=hostname)
        afe_host.add_labels([Labels.BOARD_PREFIX + arguments.board])
        afe_host = afe.get_hosts([hostname])[0]
    return afe_host, unlock_on_failure


def _install_firmware(host):
    """Install dev-signed firmware after removing write-protect.

    At start, it's assumed that hardware write-protect is disabled,
    the DUT is in dev mode, and the servo's USB stick already has a
    test image installed.

    The firmware is installed by powering on and typing ctrl+U on
    the keyboard in order to boot the the test image from USB.  Once
    the DUT is booted, we run a series of commands to install the
    read-only firmware from the test image.  Then we clear debug
    mode, and shut down.

    @param host   Host instance to use for servo and ssh operations.
    """
    servo = host.servo
    # First power on.  We sleep to allow the firmware plenty of time
    # to display the dev-mode screen; some boards take their time to
    # be ready for the ctrl+U after power on.
    servo.get_power_state_controller().power_off()
    servo.switch_usbkey('dut')
    servo.get_power_state_controller().power_on()
    time.sleep(10)
    # Dev mode screen should be up now:  type ctrl+U and wait for
    # boot from USB to finish.
    servo.ctrl_u()
    if not host.wait_up(timeout=host.USB_BOOT_TIMEOUT):
        raise Exception('DUT failed to boot in dev mode for '
                        'firmware update')
    # Disable software-controlled write-protect for both FPROMs, and
    # install the RO firmware.
    for fprom in ['host', 'ec']:
        host.run('flashrom -p %s --wp-disable' % fprom,
                 ignore_status=True)
    host.run('chromeos-firmwareupdate --mode=factory')
    # Get us out of dev-mode and clear GBB flags.  GBB flags are
    # non-zero because boot from USB was enabled.
    host.run('/usr/share/vboot/bin/set_gbb_flags.sh 0',
             ignore_status=True)
    host.run('crossystem disable_dev_request=1',
             ignore_status=True)
    host.halt()


def _install_test_image(host, arguments):
    """Install a test image to the DUT.

    Install a stable test image on the DUT using the full servo
    repair flow.

    @param host       Host instance for the DUT being installed.
    @param arguments  Command line arguments with options.
    """
    if not host.servo.probe_host_usb_dev():
        raise Exception('No USB stick detected on Servo host')
    try:
        if not arguments.noinstall:
            if not arguments.nostage:
                host.servo.image_to_servo_usb(
                        host.stage_image_for_servo())
            if arguments.full_deploy:
                _install_firmware(host)
            host.servo_install()
    except error.AutoservRunError as e:
        logging.exception('Failed to install: %s', e)
        raise Exception('chromeos-install failed')
    finally:
        host.close()


def _install_and_update_afe(afe, hostname, arguments):
    """Perform all installation and AFE updates.

    First, lock the host if it exists and is unlocked.  Then,
    install the test image on the DUT.  At the end, unlock the
    DUT, unless the installation failed and the DUT was locked
    before we started.

    If installation succeeds, make sure the DUT is in the AFE,
    and make sure that it has basic labels.

    @param afe          AFE object for RPC calls.
    @param hostname     Host name of the DUT.
    @param arguments    Command line arguments with options.
    """
    afe_host, unlock_on_failure = _get_afe_host(afe, hostname, arguments)

    try:
        host = _create_host(hostname, afe_host)
        _install_test_image(host, arguments)
        host.labels.update_labels(host)
        platform_labels = afe.get_labels(
                host__hostname=hostname, platform=True)
        if not platform_labels:
            platform = host.get_platform()
            new_labels = afe.get_labels(name=platform)
            if not new_labels:
                afe.create_label(platform, platform=True)
            afe_host.add_labels([platform])
        version = [label for label in afe_host.labels
                       if label.startswith(VERSION_PREFIX)]
        if version:
            afe_host.remove_labels(version)
    except Exception as e:
        if unlock_on_failure and not _try_unlock_host(afe_host):
            logging.error('Failed to unlock host!')
        raise

    if not _try_unlock_host(afe_host):
        raise Exception('Install succeeded, but failed to unlock the DUT.')


def _install_dut(arguments, hostname):
    """Deploy or repair a single DUT.

    Implementation note: This function is expected to run in a
    subprocess created by a multiprocessing Pool object.  As such,
    it can't (shouldn't) write to shared files like `sys.stdout`.

    @param hostname   Host name of the DUT to install on.
    @param arguments  Command line arguments with options.

    @return On success, return `None`.  On failure, return a string
            with an error message.
    """
    _configure_install_logging(
            os.path.join(arguments.dir, hostname + '.log'))
    afe = frontend.AFE(server=arguments.web)
    try:
        _install_and_update_afe(afe, hostname, arguments)
    except Exception as e:
        logging.exception('Original exception: %s', e)
        return str(e)
    return None


def _report_hosts(report_log, heading, host_results_list):
    """Report results for a list of hosts.

    To improve visibility, results are preceded by a header line,
    followed by a divider line.  Then results are printed, one host
    per line.

    @param report_log         File-like object for logging report
                              output.
    @param heading            The header string to be printed before
                              results.
    @param host_results_list  A list of (hostname, message) tuples
                              to be printed one per line.
    """
    if not host_results_list:
        return
    _report_write(report_log, heading)
    _report_write(report_log, _DIVIDER)
    for t in host_results_list:
        _report_write(report_log, '%-30s %s\n' % t)
    _report_write(report_log, '\n')


def _report_results(afe, report_log, hostnames, results):
    """Gather and report a summary of results from installation.

    Segregate results into successes and failures, reporting
    each separately.  At the end, report the total of successes
    and failures.

    @param afe          AFE object for RPC calls.
    @param report_log   File-like object for logging report output.
    @param hostnames    List of the hostnames that were tested.
    @param results      List of error messages, in the same order
                        as the hostnames.  `None` means the
                        corresponding host succeeded.
    """
    success_hosts = []
    success_reports = []
    failure_reports = []
    for r, h in zip(results, hostnames):
        if r is None:
            success_hosts.append(h)
        else:
            failure_reports.append((h, r))
    if success_hosts:
        afe_host_list = afe.get_hosts(hostnames=success_hosts)
        afe.reverify_hosts(hostnames=success_hosts)
        for h in afe.get_hosts(hostnames=success_hosts):
            for label in h.labels:
                if label.startswith(Labels.POOL_PREFIX):
                    success_reports.append(
                            (h.hostname, 'Host already in %s' % label))
                    break
            else:
                h.add_labels([_DEFAULT_POOL])
                success_reports.append(
                        (h.hostname, 'Host added to %s' % _DEFAULT_POOL))
    _report_write(report_log, _DIVIDER)
    _report_hosts(report_log, 'Successes', success_reports)
    _report_hosts(report_log, 'Failures', failure_reports)
    _report_write(report_log,
                  'Installation complete:  '
                  '%d successes, %d failures.\n' %
                  (len(success_reports), len(failure_reports)))


def install_duts(argv, full_deploy):
    """Install a test image on DUTs, and deploy them.

    This handles command line parsing for both the repair and
    deployment commands.  The two operations are largely identical;
    the main difference is that full deployment includes flashing
    dev-signed firmware on the DUT prior to installing the test
    image.

    @param argv         Command line arguments to be parsed.
    @param full_deploy  If true, do the full deployment that includes
                        flashing dev-signed RO firmware onto the DUT.
    """
    # Override tempfile.tempdir.  Some of the autotest code we call
    # will create temporary files that don't get cleaned up.  So, we
    # put the temp files in our results directory, so that we can
    # clean up everything in one fell swoop.
    tempfile.tempdir = tempfile.mkdtemp()

    arguments = commandline.parse_command(argv, full_deploy)
    if not arguments:
        sys.exit(1)
    sys.stderr.write('Installation output logs in %s\n' % arguments.dir)
    report_log = open(os.path.join(arguments.dir, 'report.log'), 'w')
    afe = frontend.AFE(server=arguments.web)
    current_build = _update_build(afe, report_log, arguments)
    _report_write(report_log, _DIVIDER)
    _report_write(report_log,
                  'Repair version for board %s is now %s.\n' %
                  (arguments.board, current_build))
    install_pool = multiprocessing.Pool(len(arguments.hostnames))
    install_function = functools.partial(_install_dut, arguments)
    results_list = install_pool.map(install_function,
                                    arguments.hostnames)
    _report_results(afe, report_log, arguments.hostnames, results_list)

    # MacDuff:
    #   [ ... ]
    #   Did you say all? O hell-kite! All?
    #   What, all my pretty chickens and their dam
    #   At one fell swoop?
    shutil.rmtree(tempfile.tempdir)
