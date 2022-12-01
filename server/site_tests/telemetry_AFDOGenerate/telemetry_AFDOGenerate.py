# Copyright 2013 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""
Test to generate the AFDO profile for a set of ChromeOS benchmarks.

This will run a pre-determined set of benchmarks on the DUT under
the monitoring of the linux "perf" tool. The resulting perf.data
file will then be copied to Google Storage (GS) where it can be
used by the AFDO optimized build.

Given that the telemetry benchmarks are quite unstable on ChromeOS at
this point, this test also supports a mode where the benchmarks are
executed outside of the telemetry framework. It is not the same as
executing the benchmarks under telemetry because there is no telemetry
measurement taken but, for the purposes of profiling Chrome, it should
be pretty close.

Example invocation:
/usr/bin/test_that --debug --board=lumpy <DUT IP>
  --args="ignore_failures=True local=True gs_test_location=True"
  telemetry_AFDOGenerate
"""


import bz2
from contextlib import contextmanager
from contextlib import ExitStack
import logging
import os
import time

from autotest_lib.client.common_lib import error
from autotest_lib.server import autotest
from autotest_lib.server import test
from autotest_lib.server import utils
from autotest_lib.server.cros import filesystem_util
from autotest_lib.server.cros import telemetry_runner
from autotest_lib.site_utils import test_runner_utils


# These are arguments to the linux "perf" tool.
# The -e value is processor specific and comes from the Intel SDM vol 3b
INTEL_PROFILER_ARGS = 'record -a -e r20c4 -c 150001 -b'

ARM_PROFILER_ARGS = 'record -e cs_etm/autofdo/u -a -S'
ETM_STROBING_WINDOW = 1000
ETM_STROBING_PERIOD = 10000

# In practice, it takes >2min to copy the perf.data back from the DUT, set
# this timeout to 600 secs to be safe.
WAIT_FOR_CMD_TIMEOUT_SECS = 600

# Reuse ssh and scp settings from telemetry_Crosperf
RSA_KEY = '-i %s' % test_runner_utils.TEST_KEY_PATH
DUT_SCP_OPTIONS = ' '.join([
        '-o StrictHostKeyChecking=no', '-o UserKnownHostsFile=/dev/null',
        '-o BatchMode=yes', '-o ConnectTimeout=30',
        '-o ServerAliveInterval=900', '-o ServerAliveCountMax=3',
        '-o ConnectionAttempts=4', '-o Protocol=2'
])
DUT_CHROME_RESULTS_DIR = '/usr/local/telemetry/src/tools/perf'

_WAIT_CMD_TEMPLATE = """\
for _ in {1..%(timeout)d}; do \
  ps %(pid)d >/dev/null || break; \
  sleep 1; \
done; \
! ps %(pid)d >/dev/null \
"""


def _wait_for_process(host, pid, timeout=-1):
    """Waits for a process on the DUT to terminate.

    @param host: A host object representing the DUT.
    @param pid: The process ID (integer).
    @param timeout: Number of seconds to wait; default is wait forever.
    """
    wait_cmd = _WAIT_CMD_TEMPLATE % {'pid': pid, 'timeout': timeout}
    return host.run(wait_cmd, ignore_status=True).exit_status


# List of benchmarks to run to capture profile information. This is
# based on the "superhero" list and other telemetry benchmarks. Goal is
# to have a short list that is as representative as possible and takes a
# short time to execute. At this point the list of benchmarks is in flux.
TELEMETRY_AFDO_BENCHMARKS = (
        {
            'name': 'loading.desktop',
            'args': ('--pageset-repeat=1', '--story-tag-filter=typical'),
            'archs': ('amd64',)
        },
        # TODO(b:203556061): Replace loading.desktop on arm.
        # {
        #     'name': 'loading.desktop',
        #     'args': ('--pageset-repeat=1',
        #              '--story-tag-filter=intl_es_fr_pt_BR'),
        #     'archs': ('arm',)
        # },
        {
            'name': 'tab_switching.typical_25',
            'archs': ('arm',)
        },
        {
            'name': 'rendering.desktop',
            'args': ('--pageset-repeat=1', '--story-tag-filter=tough_canvas'),
            'archs': ('amd64',)
        },
        {
            'name': 'octane',
            'archs': ('amd64', 'arm')
        },
        {
            'name': 'kraken',
            'archs': ('amd64', 'arm')
        },
        {
            'name': 'speedometer2',
            'archs': ('amd64', 'arm')
        },
)

# Supported <board>: <architecture>.
LLVM_BOARDS = {'chell': 'amd64',
               'trogdor': 'arm'}


class telemetry_AFDOGenerate(test.test):
    """Telemetry tests wrapper to collect profiles for AFDO.

    Run one or more telemetry benchmarks under the "perf" monitoring
    tool, generate a "perf.data" file and upload to GS for comsumption
    by the AFDO optimized build.
    """
    version = 1

    def _scp_perf_data(self, dut, host_dir):
        """Copy perf data from dut.

        @param dut: The autotest host object representing DUT.
        @param host_dir: The directory on host to put the file .

        @returns status code for scp command.
        """
        cmd = []
        src = f'root@{dut.hostname}:{DUT_CHROME_RESULTS_DIR}/perf.data'
        cmd.extend([
            'scp', DUT_SCP_OPTIONS, RSA_KEY,
            '-P %s' % str(dut.port) if dut.port else '', '-v', src,
            host_dir
        ])
        command = ' '.join(cmd)

        logging.debug('Retrieving Perf Data: %s', command)
        try:
            result = utils.run(command, timeout=WAIT_FOR_CMD_TIMEOUT_SECS)
            exit_code = result.exit_status
        except Exception as e:
            logging.error('Failed to retrieve results: %s', e)
            raise

        logging.debug('command return value: %d', exit_code)
        return exit_code

    @contextmanager
    def _perf_on_dut(self):
        """Start and kill perf process on DUT."""
        logging.info('Starting perf process in background.')
        if self._is_arm():
            profile_args = ARM_PROFILER_ARGS
            perf_data = 'perf-etm.data'
        else:
            profile_args = INTEL_PROFILER_ARGS
            perf_data = 'perf.data'

        perf_cmd = (f'nohup perf {profile_args} '
                    f'-o {DUT_CHROME_RESULTS_DIR}/{perf_data}')
        perf_pid = self._host.run_background(perf_cmd)

        if self._is_arm():
            # Send signals to perf_pid to trigger ETM data collection.
            # Period 100ms.
            # It will automatically terminate with perf.
            ping_cmd = f'while kill -USR2 {perf_pid} ; do sleep 4 ; done'
            self._host.run_background(ping_cmd)

        try:
            # Use `kill -0` to check whether the perf process is alive
            verify_cmd = f'kill -0 {perf_pid}'
            if self._host.run(verify_cmd, ignore_status=True).exit_status != 0:
                logging.error('Perf process not started correctly on DUT')
                raise RuntimeError
            logging.info('Perf PID: %s\nPerf command: %s', perf_pid, perf_cmd)
            yield
        finally:
            # Check if process is still alive after benchmark run, if yes,
            # then kill it with -2 (which is SIGINT).
            kill_cmd = f'kill -0 {perf_pid} && killall -2 perf'
            if self._host.run(kill_cmd, ignore_status=True).exit_status != 0:
                logging.error('Perf process is not killed correctly on DUT.')
                raise RuntimeError
            # Perf process may not be terminated right after the kill command,
            # wait until perf process finishes.
            status = _wait_for_process(self._host, int(perf_pid),
                                       WAIT_FOR_CMD_TIMEOUT_SECS)
            if status != 0:
                logging.error('Error waiting for perf process to be killed.')
                raise RuntimeError
            logging.info('Perf has been killed on DUT.')

        if self._is_arm():
            # Now we need to convert ETM data into Intel's LBR format
            # which allows us to re-use the same AFDO pipeline.
            perf_inject_cmd = ('perf inject --itrace=i1000il --strip '
                               f'-i {DUT_CHROME_RESULTS_DIR}/perf-etm.data '
                               f'-o {DUT_CHROME_RESULTS_DIR}/perf.data')
            if self._host.run(perf_inject_cmd).exit_status != 0:
                logging.error(
                    'Perf inject failed to convert ETM trace into LBR format.')
                raise RuntimeError

        status = self._scp_perf_data(self._host, self.profdir)
        if status != 0:
            logging.error('Cannot copy perf.data file to host.')
            raise RuntimeError

    @contextmanager
    def _disable_cpuidle(self):
        """Disable CPU idle states in a context. See b/185490945."""
        cpuidle_states = '/sys/devices/system/cpu/cpu*/cpuidle/state*/disable'
        # Disable CPU Idle states to reduce ETM performance overhead.
        disable_cmd = f'echo 1 | tee {cpuidle_states}'
        if self._host.run(disable_cmd).exit_status != 0:
            logging.error('Failed to disable CPU idle states before perf run.')
            raise RuntimeError
        try:
            yield
        finally:
            # Re-enable CPU idle.
            enable_cmd = f'echo 0 | tee {cpuidle_states}'
            if self._host.run(enable_cmd).exit_status != 0:
                logging.error(
                    'Failed to re-enable CPU idle states after perf run.')
                raise RuntimeError

    def _set_strobing(self, window, period):
        """Set ETM strobing settings."""
        stat1 = self._host.run(
            f'echo {window} > /sys/kernel/config/cs-syscfg/features/strobing/'
            'params/window/value')
        stat2 = self._host.run(
            f'echo {period} > /sys/kernel/config/cs-syscfg/features/strobing/'
            'params/period/value')
        if stat1.exit_status != 0 or stat2.exit_status != 0:
            logging.error(
                'Failed to set up ETM strobing settings. '
                'W/o strobing perf profiles can have 100x increase in size.')
            raise RuntimeError

    def run_once(self, host, args):
        """Run a set of telemetry benchmarks.

        @param host: Host machine where test is run
        @param args: A dictionary of the arguments that were passed
                to this test.
        @returns None.
        """
        self._host = host
        self._board = host.get_board().split(':')[1]

        self._parse_args(args)

        # Remove write protection on host, as now telemetry code will
        # try to remove write protection that causes the machine to
        # reboot and remount during run_benchmark. We want to avoid it.
        filesystem_util.make_rootfs_writable(self._host)

        with ExitStack() as stack:
            if self._is_arm():
                self._set_strobing(ETM_STROBING_WINDOW, ETM_STROBING_PERIOD)
                stack.enter_context(self._disable_cpuidle())
            stack.enter_context(self._perf_on_dut())

            if self._minimal_telemetry:
                self._run_tests_minimal_telemetry()
            else:
                tr = stack.enter_context(
                    telemetry_runner.TelemetryRunnerFactory().get_runner(
                        self._host, self._local, telemetry_on_dut=False))
                for benchmark_info in TELEMETRY_AFDO_BENCHMARKS:
                    if self._arch not in benchmark_info['archs']:
                        continue
                    benchmark = benchmark_info['name']
                    args = benchmark_info.setdefault('args', [])
                    try:
                        self._run_test_with_retry(tr, benchmark, *args)
                    except error.TestBaseException:
                        if not self._ignore_failures:
                            raise
                        logging.info('Ignoring failure from benchmark %s.',
                                     benchmark)
        self._passed = True

    def after_run_once(self):
        """After the profile information has been collected, compress it
        and upload it to GS
        """
        if not self._passed:
            return

        PERF_FILE = 'perf.data'
        COMP_PERF_FILE = 'chromeos-chrome-{arch}-{ver}.perf.data'
        perf_data = os.path.join(self.profdir, PERF_FILE)
        comp_data = os.path.join(self.profdir, COMP_PERF_FILE.format(
            arch=self._arch, ver=self._version))
        compressed = self._compress_file(perf_data, comp_data)
        self._gs_upload(compressed, os.path.basename(compressed))

        # Also create copy of this file using "LATEST" as version so
        # it can be found in case the builder is looking for a version
        # number that does not match. It is ok to use a slighly old
        # version of the this file for the optimized build
        latest_data = COMP_PERF_FILE.format(arch=self._arch, ver='LATEST')
        latest_compressed = self._get_compressed_name(latest_data)
        self._gs_upload(compressed, latest_compressed)

        # So that they are not uploaded along with the logs.
        os.remove(compressed)
        os.remove(perf_data)

    def _parse_args(self, args):
        """Parses and validates input arguments to this autotest.

        @param args: Options->values dictionary.
        @raises error.TestFail if a bad option is passed.
        """
        # Set default values for the options.

        # Architecture for which we are collecting afdo data
        # is based on the board.
        if self._board not in LLVM_BOARDS:
            raise error.TestFail(
                f'This test cannot be run on board {self._board}. '
                f'Try one of {sorted(LLVM_BOARDS)}')
        self._arch = LLVM_BOARDS[self._board]
        # Use an alternate GS location where everyone can write.
        # Set default depending on whether this is executing in
        # the lab environment or not
        self._gs_test_location = not utils.host_is_in_lab_zone(
            self._host.hostname)
        # Ignore individual test failures.
        self._ignore_failures = False
        # Use local copy of telemetry instead of using the dev server copy.
        self._local = False
        # Chrome version to which the AFDO data corresponds.
        self._version, _ = self._host.get_chrome_version()
        # Try to use the minimal support from Telemetry. The Telemetry
        # benchmarks in ChromeOS are too flaky at this point. So, initially,
        # this will be set to True by default.
        self._minimal_telemetry = False
        # Set when the telemetry test pass.
        self._passed = False

        # Ignored servo arguments.
        ignored_options = ('servo_host', 'servo_port')

        for option_name, value in args.items():
            if option_name == 'arch':
                # Verify board: arch.
                if self._arch != value:
                    raise error.TestFail(
                        'Mismatch of the board and architecture: '
                        f'board: {self._board}, arch: {value}. '
                        f'Did you mean "arch={self._arch}"?')
            elif option_name == 'gs_test_location':
                self._gs_test_location = (value == 'True')
            elif option_name == 'ignore_failures':
                self._ignore_failures = (value == 'True')
            elif option_name == 'local':
                self._local = (value == 'True')
            elif option_name == 'minimal_telemetry':
                self._minimal_telemetry = (value == 'True')
            elif option_name == 'version':
                self._version = value
            elif option_name in ignored_options:
                continue
            else:
                raise error.TestFail('Unknown option passed: %s' % option_name)

    def _is_arm(self):
        """Return true if arch is arm."""
        return self._arch == 'arm'

    def _run_test(self, tr, benchmark, *args):
        """Run the benchmark using Telemetry.

        @param tr: Instance of the TelemetryRunner subclass.
        @param benchmark: Name of the benchmark to run.
        @param args: Additional arguments to pass to the telemetry execution
                     script.
        @raises Raises error.TestFail if execution of test failed.
                Also re-raise any exceptions thrown by run_telemetry benchmark.
        """
        try:
            logging.info('Starting run for Telemetry benchmark %s', benchmark)
            start_time = time.time()
            result = tr.run_telemetry_benchmark(benchmark, None, *args)
            end_time = time.time()
            logging.info('Completed Telemetry benchmark %s in %f seconds',
                         benchmark, end_time - start_time)
        except error.TestBaseException as e:
            end_time = time.time()
            logging.info(
                'Got exception from Telemetry benchmark %s '
                'after %f seconds. Exception: %s', benchmark,
                end_time - start_time, str(e))
            raise

        # We dont generate any keyvals for this run. This is not
        # an official run of the benchmark. We are just running it to get
        # a profile from it.

        if result.status is telemetry_runner.SUCCESS_STATUS:
            logging.info('Benchmark %s succeeded', benchmark)
        else:
            raise error.TestFail(
                f'An error occurred while executing benchmark: {benchmark}')

    def _run_test_with_retry(self, tr, benchmark, *args):
        """Run the benchmark using Telemetry. Retry in case of failure.

        @param tr: An instance of the TelemetryRunner subclass.
        @param benchmark: Name of the benchmark to run.
        @param args: Additional arguments to pass to the telemetry execution
                     script.
        @raises Re-raise any exceptions thrown by _run_test.
        """

        tried = False
        while True:
            try:
                self._run_test(tr, benchmark, *args)
                logging.info('Benchmark %s succeeded on %s try', benchmark,
                             'first' if not tried else 'second')
                break
            except error.TestBaseException:
                if not tried:
                    tried = True
                    logging.info('Benchmark %s failed. Retrying ...',
                                 benchmark)
                else:
                    logging.info('Benchmark %s failed twice. Not retrying',
                                 benchmark)
                    raise

    def _run_tests_minimal_telemetry(self):
        """Run the benchmarks using the minimal support from Telemetry.

        The benchmarks are run using a client side autotest test. This test
        will control Chrome directly using the chrome.Chrome support and it
        will ask Chrome to display the benchmark pages directly instead of
        using the "page sets" and "measurements" support from Telemetry.
        In this way we avoid using Telemetry benchmark support which is not
        stable on ChromeOS yet.
        """
        AFDO_GENERATE_CLIENT_TEST = 'telemetry_AFDOGenerateClient'

        # Execute the client side test.
        client_at = autotest.Autotest(self._host)
        client_at.run_test(AFDO_GENERATE_CLIENT_TEST, args='')

    @staticmethod
    def _get_compressed_name(name):
        """Given a file name, return bz2 compressed name.

        @param name: Name of uncompressed file.
        @returns name of compressed file.
        """
        return name + '.bz2'

    @staticmethod
    def _compress_file(unc_file, com_file):
        """Compresses specified file with bz2.

        @param unc_file: name of file to compress.
        @param com_file: prefix name of compressed file.
        @raises error.TestFail if compression failed
        @returns Name of compressed file.
        """
        dest = ''
        with open(unc_file, 'rb') as inp:
            dest = telemetry_AFDOGenerate._get_compressed_name(com_file)
            with bz2.BZ2File(dest, 'wb') as out:
                for data in inp:
                    out.write(data)
        if not dest or not os.path.isfile(dest):
            raise error.TestFail(f'Could not compress {unc_file}')
        return dest

    def _gs_upload(self, local_file, remote_basename):
        """Uploads file to google storage specific location.

        @param local_file: name of file to upload.
        @param remote_basename: basename of remote file.
        @raises error.TestFail if upload failed.
        @returns nothing.
        """
        GS_LLVM_DEST = ('gs://chromeos-toolchain-artifacts/afdo/unvetted/'
                        f'benchmark/{remote_basename}')
        GS_TEST_DEST = ('gs://chromeos-throw-away-bucket/afdo-job/canonicals/'
                        f'{remote_basename}')
        GS_ACL = 'project-private'

        if self._gs_test_location:
            remote_file = GS_TEST_DEST
        elif self._board in LLVM_BOARDS:
            remote_file = GS_LLVM_DEST
        else:
            raise error.TestFail(
                f'This test cannot be run on board {self._board}')

        logging.info('About to upload to GS: %s', remote_file)
        if not utils.gs_upload(
                local_file, remote_file, GS_ACL, result_dir=self.resultsdir):
            logging.info('Failed upload to GS: %s', remote_file)
            raise error.TestFail(
                f'Unable to gs upload {local_file} to {remote_file}')

        logging.info('Successfull upload to GS: %s', remote_file)
