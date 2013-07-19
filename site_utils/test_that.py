#!/usr/bin/python
# Copyright (c) 2013 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import argparse
import logging
import os
import re
import signal
import stat
import subprocess
import sys
import tempfile
import threading

import common
from autotest_lib.client.common_lib.cros import dev_server, retry
from autotest_lib.server.cros.dynamic_suite import suite
from autotest_lib.server.cros.dynamic_suite import constants
from autotest_lib.server import autoserv_utils

try:
    from chromite.lib import cros_build_lib
except ImportError:
    print 'Unable to import chromite.'
    print 'This script must be either:'
    print '  - Be run in the chroot.'
    print '  - (not yet supported) be run after running '
    print '    ../utils/build_externals.py'

_autoserv_proc = None
_sigint_handler_lock = threading.Lock()

_AUTOSERV_SIGINT_TIMEOUT_SECONDS = 5
_NO_BOARD = 'ad_hoc_board'
_NO_BUILD = 'ad_hoc_build'

_QUICKMERGE_SCRIPTNAME = '/mnt/host/source/chromite/bin/autotest_quickmerge'

_TEST_REPORT_SCRIPTNAME = '/usr/bin/generate_test_report'

_LATEST_RESULTS_DIRECTORY = '/tmp/test_that_latest'


def schedule_local_suite(autotest_path, suite_name, afe, build=_NO_BUILD,
                         board=_NO_BOARD, results_directory=None,
                         no_experimental=False):
    """
    Schedule a suite against a mock afe object, for a local suite run.
    @param autotest_path: Absolute path to autotest (in sysroot).
    @param suite_name: Name of suite to schedule.
    @param afe: afe object to schedule against (typically a directAFE)
    @param build: Build to schedule suite for.
    @param board: Board to schedule suite for.
    @param results_directory: Absolute path of directory to store results in.
                              (results will be stored in subdirectory of this).
    @param no_experimental: Skip experimental tests when scheduling a suite.
    @returns: The number of tests scheduled.
    """
    fs_getter = suite.Suite.create_fs_getter(autotest_path)
    devserver = dev_server.ImageServer('')
    my_suite = suite.Suite.create_from_name(suite_name, build, board,
            devserver, fs_getter, afe=afe, ignore_deps=True,
            results_dir=results_directory)
    if len(my_suite.tests) == 0:
        raise ValueError('Suite named %s does not exist, or contains no '
                         'tests.' % suite_name)
    # Schedule tests, discard record calls.
    return my_suite.schedule(lambda x: None,
                             add_experimental=not no_experimental)


def schedule_local_test(autotest_path, test_name, afe, build=_NO_BUILD,
                        board=_NO_BOARD, results_directory=None):
    #temporarily disabling pylint
    #pylint: disable-msg=C0111
    """
    Schedule an individual test against a mock afe object, for a local run.
    @param autotest_path: Absolute path to autotest (in sysroot).
    @param test_name: Name of test to schedule.
    @param afe: afe object to schedule against (typically a directAFE)
    @param build: Build to schedule suite for.
    @param board: Board to schedule suite for.
    @param results_directory: Absolute path of directory to store results in.
                              (results will be stored in subdirectory of this).
    @returns: The number of tests scheduled (may be >1 if there are
              multiple tests with the same name).
    """
    fs_getter = suite.Suite.create_fs_getter(autotest_path)
    devserver = dev_server.ImageServer('')
    predicates = [suite.Suite.test_name_equals_predicate(test_name)]
    suite_name = 'suite_' + test_name
    my_suite = suite.Suite.create_from_predicates(predicates, build, board,
            devserver, fs_getter, afe=afe, name=suite_name, ignore_deps=True,
            results_dir=results_directory)
    if len(my_suite.tests) == 0:
        raise ValueError('No tests named %s.' % test_name)
    # Schedule tests, discard record calls.
    return my_suite.schedule(lambda x: None)


def run_job(job, host, sysroot_autotest_path, results_directory, fast_mode,
            id_digits=1, args=None, pretend=False):
    """
    Shell out to autoserv to run an individual test job.

    @param job: A Job object containing the control file contents and other
                relevent metadata for this test.
    @param host: Hostname of DUT to run test against.
    @param sysroot_autotest_path: Absolute path of autotest directory.
    @param results_directory: Absolute path of directory to store results in.
                              (results will be stored in subdirectory of this).
    @param fast_mode: bool to use fast mode (disables slow autotest features).
    @param id_digits: The minimum number of digits that job ids should be
                      0-padded to when formatting as a string for results
                      directory.
    @param args: String that should be passed as args parameter to autoserv,
                 and then ultimitely to test itself.
    @param pretend: If True, will print out autoserv commands rather than
                    running them.
    @returns: Absolute path of directory where results were stored.
    """
    with tempfile.NamedTemporaryFile() as temp_file:
        temp_file.write(job.control_file)
        temp_file.flush()
        results_directory = os.path.join(results_directory,
                                         'results-%0*d' % (id_digits, job.id))
        extra_args = [temp_file.name]
        if args:
            extra_args.extend(['--args', args])

        command = autoserv_utils.autoserv_run_job_command(
                os.path.join(sysroot_autotest_path, 'server'),
                machines=host, job=job, verbose=False,
                results_directory=results_directory,
                fast_mode=fast_mode,
                extra_args=extra_args)

        if not pretend:
            global _autoserv_proc
            _autoserv_proc = subprocess.Popen(command)
            _autoserv_proc.wait()
            _autoserv_proc = None
            return results_directory
        else:
            logging.info('Pretend mode. Would run autoserv command: %s',
                         ' '.join(command))


def setup_local_afe():
    """
    Setup a local afe database and return a direct_afe object to access it.

    @returns: A autotest_lib.frontend.afe.direct_afe instance.
    """
    # This import statement is delayed until now rather than running at
    # module load time, because it kicks off a local sqlite :memory: backed
    # database, and we don't need that unless we are doing a local run.
    from autotest_lib.frontend import setup_django_lite_environment
    from autotest_lib.frontend.afe import direct_afe
    return direct_afe.directAFE()


def perform_local_run(afe, autotest_path, tests, remote, fast_mode,
                      build=_NO_BUILD, board=_NO_BOARD, args=None,
                      pretend=False, no_experimental=False):
    """
    @param afe: A direct_afe object used to interact with local afe database.
    @param autotest_path: Absolute path of sysroot installed autotest.
    @param tests: List of strings naming tests and suites to run. Suite strings
                  should be formed like "suite:smoke".
    @param remote: Remote hostname.
    @param fast_mode: bool to use fast mode (disables slow autotest features).
    @param build: String specifying build for local run.
    @param board: String specifyinb board for local run.
    @param args: String that should be passed as args parameter to autoserv,
                 and then ultimitely to test itself.
    @param pretend: If True, will print out autoserv commands rather than
                    running them.
    @param no_experimental: Skip experimental tests when scheduling a suite.

    @returns: directory in which results are stored.
    """
    afe.create_label(constants.VERSION_PREFIX + build)
    afe.create_label(board)
    afe.create_host(remote)

    results_directory = tempfile.mkdtemp(prefix='test_that_results_')
    os.chmod(results_directory, stat.S_IWOTH | stat.S_IROTH | stat.S_IXOTH)
    logging.info('Running jobs. Results will be placed in %s',
                 results_directory)
    # Schedule tests / suites in local afe
    for test in tests:
        suitematch = re.match(r'suite:(.*)', test)
        if suitematch:
            suitename = suitematch.group(1)
            logging.info('Scheduling suite %s...', suitename)
            ntests = schedule_local_suite(autotest_path, suitename, afe,
                                          build=build, board=board,
                                          results_directory=results_directory,
                                          no_experimental=no_experimental)
        else:
            logging.info('Scheduling test %s...', test)
            ntests = schedule_local_test(autotest_path, test, afe,
                                         build=build, board=board,
                                         results_directory=results_directory)
        logging.info('... scheduled %s tests.', ntests)

    if not afe.get_jobs():
        logging.info('No jobs scheduled. End of local run.')
        return results_directory

    last_job_id = afe.get_jobs()[-1].id
    job_id_digits=len(str(last_job_id))
    for job in afe.get_jobs():
        run_job(job, remote, autotest_path, results_directory, fast_mode,
                job_id_digits, args, pretend)

    return results_directory


def validate_arguments(arguments):
    """
    Validates parsed arguments.

    @param arguments: arguments object, as parsed by ParseArguments
    @raises: ValueError if arguments were invalid.
    """
    if arguments.build:
        raise ValueError('-i/--build flag not yet supported.')

    if not arguments.board:
        raise ValueError('Board autodetection not yet supported. '
                         '--board required.')

    if arguments.remote == ':lab:':
        raise ValueError('Running tests in test lab not yet supported.')
        if arguments.args:
            raise ValueError('--args flag not supported when running against '
                             ':lab:')
        if arguments.pretend:
            raise ValueError('--pretend flag not supported when running '
                             'against :lab:')


def parse_arguments(argv):
    """
    Parse command line arguments

    @param argv: argument list to parse
    @returns:    parsed arguments.
    """
    parser = argparse.ArgumentParser(description='Run remote tests.')

    parser.add_argument('remote', metavar='REMOTE',
                        help='hostname[:port] for remote device. Specify '
                        ':lab: to run in test lab, or :vm:PORT_NUMBER to '
                        'run in vm.')
    parser.add_argument('tests', nargs='+', metavar='TEST',
                        help='Run given test(s). Use suite:SUITE to specify '
                        'test suite.')
    parser.add_argument('-b', '--board', metavar='BOARD',
                        action='store',
                        help='Board for which the test will run.')
    parser.add_argument('-i', '--build', metavar='BUILD',
                        help='Build to test. Device will be reimaged if '
                        'necessary. Omit flag to skip reimage and test '
                        'against already installed DUT image.')
    parser.add_argument('--fast', action='store_true', dest='fast_mode',
                        default=False,
                        help='Enable fast mode.  This will cause test_that to '
                             'skip time consuming steps like sysinfo and '
                             'collecting crash information.')
    parser.add_argument('--args', metavar='ARGS',
                        help='Argument string to pass through to test. Only '
                        'supported for runs against a local DUT.')
    parser.add_argument('--pretend', action='store_true', default=False,
                        help='Print autoserv commands that would be run, '
                             'rather than running them.')
    parser.add_argument('--no-quickmerge', action='store_true', default=False,
                        dest='no_quickmerge',
                        help='Skip the quickmerge step and use the sysroot '
                             'as it currently is. May result in un-merged '
                             'source tree changes not being reflected in run.')
    parser.add_argument('--no-experimental', action='store_true',
                        default=False, dest='no_experimental',
                        help='When scheduling a suite, skip any tests marked '
                             'as experimental. Applies only to tests scheduled'
                             ' via suite:[SUITE].')

    return parser.parse_args(argv)


def sigint_handler(signum, stack_frame):
    #pylint: disable-msg=C0111
    """Handle SIGINT or SIGTERM to a local test_that run.

    This handler sends a SIGINT to the running autoserv process,
    if one is running, giving it up to 5 seconds to clean up and exit. After
    the timeout elapses, autoserv is killed. In either case, after autoserv
    exits then this process exits with status 1.
    """
    # If multiple signals arrive before handler is unset, ignore duplicates
    if not _sigint_handler_lock.acquire(False):
        return
    try:
        # Ignore future signals by unsetting handler.
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        signal.signal(signal.SIGTERM, signal.SIG_IGN)

        logging.warning('Received SIGINT or SIGTERM. Cleaning up and exiting.')
        if _autoserv_proc:
            logging.warning('Sending SIGINT to autoserv process. Waiting up '
                            'to %s seconds for cleanup.',
                            _AUTOSERV_SIGINT_TIMEOUT_SECONDS)
            _autoserv_proc.send_signal(signal.SIGINT)
            timed_out, _ = retry.timeout(_autoserv_proc.wait,
                    timeout_sec=_AUTOSERV_SIGINT_TIMEOUT_SECONDS)
            if timed_out:
                _autoserv_proc.kill()
                logging.warning('Timed out waiting for autoserv to handle '
                                'SIGINT. Killed autoserv.')
    finally:
        _sigint_handler_lock.release() # this is not really necessary?
        sys.exit(1)


def main(argv):
    """
    Entry point for test_that script.
    @param argv: arguments list
    """
    if not cros_build_lib.IsInsideChroot():
        logging.error('Script must be invoked inside the chroot.')
        return 1

    logging.getLogger('').setLevel(logging.INFO)

    arguments = parse_arguments(argv)
    try:
        validate_arguments(arguments)
    except ValueError as err:
        logging.error('Invalid arguments. %s', err.message)
        return 1

    # TODO: Determine the following string programatically.
    # (same TODO applied to autotest_quickmerge)
    sysroot_path = os.path.join('/build', arguments.board, '')
    sysroot_autotest_path = os.path.join(sysroot_path, 'usr', 'local',
                                         'autotest', '')
    sysroot_site_utils_path = os.path.join(sysroot_autotest_path,
                                            'site_utils')

    if not os.path.exists(sysroot_path):
        logging.error('%s does not exist. Have you run setup_board?',
                      sysroot_path)
        return 1
    if not os.path.exists(sysroot_autotest_path):
        logging.error('%s does not exist. Have you run build_packages?',
                      sysroot_autotest_path)
        return 1

    # If we are not running the sysroot version of script, perform
    # a quickmerge if necessary and then re-execute
    # the sysroot version of script with the same arguments.
    realpath = os.path.realpath(__file__)
    if os.path.dirname(realpath) != sysroot_site_utils_path:
        if arguments.no_quickmerge:
            logging.info('Skipping quickmerge step as requested.')
        else:
            subprocess.call([_QUICKMERGE_SCRIPTNAME,
                             '--board='+arguments.board])

        script_command = os.path.join(sysroot_site_utils_path,
                                      os.path.basename(realpath))
        proc = None
        def resend_sig(signum, stack_frame):
            #pylint: disable-msg=C0111
            if proc:
                proc.send_signal(signum)
        signal.signal(signal.SIGINT, resend_sig)
        signal.signal(signal.SIGTERM, resend_sig)

        proc = subprocess.Popen([script_command] + argv)

        return proc.wait()

    # Hard coded to True temporarily. This will eventually be parsed to false
    # if we are doing a run in the test lab.
    local_run = True

    signal.signal(signal.SIGINT, sigint_handler)
    signal.signal(signal.SIGTERM, sigint_handler)

    if local_run:
        afe = setup_local_afe()
        res_dir= perform_local_run(afe, sysroot_autotest_path, arguments.tests,
                                   arguments.remote, arguments.fast_mode,
                                   args=arguments.args,
                                   pretend=arguments.pretend,
                                   no_experimental=arguments.no_experimental)
        if arguments.pretend:
            logging.info('Finished pretend run. Exiting.')
            return 0

        final_result = subprocess.call([_TEST_REPORT_SCRIPTNAME, res_dir])
        logging.info('Finished running tests. Results can be found in %s',
                     res_dir)
        try:
            os.unlink(_LATEST_RESULTS_DIRECTORY)
        except OSError:
            pass
        os.symlink(res_dir, _LATEST_RESULTS_DIRECTORY)
        return final_result


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
