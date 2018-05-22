# Copyright 2018 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import json
import logging
import os
import time

import dateutil.parser

from autotest_lib.client.common_lib import base_job
from autotest_lib.client.common_lib import error
from autotest_lib.server import test
from autotest_lib.server import utils


# A datetime.DateTime representing the Unix epoch in UTC.
_UNIX_EPOCH = dateutil.parser.parse('1970-01-01T00:00:00Z')


class tast(test.test):
    """Autotest server test that runs a Tast test suite.

    Tast is an integration-testing framework analagous to the test-running
    portion of Autotest. See
    https://chromium.googlesource.com/chromiumos/platform/tast/ for more
    information.

    This class runs the "tast" command locally to execute a Tast test suite on a
    remote DUT.
    """
    version = 1

    # Maximum time to wait for various tast commands to complete, in seconds.
    _VERSION_TIMEOUT_SEC = 10
    _SUBCOMMAND_TIMEOUT_SEC = {
        'list': 30,
        'run': 600,
    }

    # File written by the tast command containing test results, as
    # newline-terminated JSON TestResult objects.
    _STREAMED_RESULTS_FILENAME = 'streamed_results.jsonl'

    # Maximum number of failing tests to include in error message.
    _MAX_TEST_NAMES_IN_ERROR = 3

    # Default paths where Tast files are installed.
    _TAST_PATH = '/usr/bin/tast'
    _REMOTE_BUNDLE_DIR = '/usr/libexec/tast/bundles/remote'
    _REMOTE_DATA_DIR = '/usr/share/tast/data/remote'
    _REMOTE_TEST_RUNNER_PATH = '/usr/bin/remote_test_runner'

    # When Tast is deployed from CIPD packages in the lab, it's installed under
    # this prefix rather than under the root directory.
    _CIPD_INSTALL_ROOT = '/opt/infra-tools'

    # Prefix added to Tast test names when writing their results to TKO
    # status.log files.
    _TEST_NAME_PREFIX = 'tast.'

    # Job start/end TKO event status codes from base_client_job._rungroup in
    # client/bin/job.py.
    _JOB_STATUS_START = 'START'
    _JOB_STATUS_END_GOOD = 'END GOOD'
    _JOB_STATUS_END_FAIL = 'END FAIL'
    _JOB_STATUS_END_ABORT = 'END ABORT'

    # In-job TKO event status codes from base_client_job._run_test_base in
    # client/bin/job.py and client/common_lib/error.py.
    _JOB_STATUS_GOOD = 'GOOD'
    _JOB_STATUS_FAIL = 'FAIL'

    def initialize(self, host, test_exprs):
        """
        @param host: remote.RemoteHost instance representing DUT.
        @param test_exprs: Array of strings describing tests to run.

        @raises error.TestFail if the Tast installation couldn't be found.
        """
        self._host = host
        self._test_exprs = test_exprs

        # List of JSON objects describing tests that will be run. See Test in
        # src/platform/tast/src/chromiumos/tast/testing/test.go for details.
        self._tests_to_run = []

        # List of JSON objects corresponding to tests from a Tast results.json
        # file. See TestResult in
        # src/platform/tast/src/chromiumos/cmd/tast/run/results.go for details.
        self._test_results = []

        # The data dir can be missing if no remote tests registered data files,
        # but all other files must exist.
        self._tast_path = self._get_path(self._TAST_PATH)
        self._remote_bundle_dir = self._get_path(self._REMOTE_BUNDLE_DIR)
        self._remote_data_dir = self._get_path(self._REMOTE_DATA_DIR,
                                               allow_missing=True)
        self._remote_test_runner_path = self._get_path(
                self._REMOTE_TEST_RUNNER_PATH)

        # Register a hook to write the results of individual Tast tests as
        # top-level entries in the TKO status.log file.
        self.job.add_post_run_hook(self._log_all_tests)

    def run_once(self):
        """Runs a single iteration of the test."""
        self._log_version()
        self._get_tests_to_run()
        try:
            self._run_tests()
        finally:
            # Parse partial results even if the tast command didn't finish.
            self._parse_results()

    def _get_path(self, path, allow_missing=False):
        """Returns the path to an installed Tast-related file or directory.

        @param path: Absolute path in root filesystem, e.g. "/usr/bin/tast".
        @param allow_missing: True if it's okay for the path to be missing.

        @return: Absolute path within install root, e.g.
            "/opt/infra-tools/usr/bin/tast", or an empty string if the path
            wasn't found and allow_missing is True.

        @raises error.TestFail if the path couldn't be found and allow_missing
            is False.
        """
        if os.path.exists(path):
            return path

        cipd_path = os.path.join(self._CIPD_INSTALL_ROOT,
                                 os.path.relpath(path, '/'))
        if os.path.exists(cipd_path):
            return cipd_path

        if allow_missing:
            return ''
        raise error.TestFail('Neither %s nor %s exists' % (path, cipd_path))

    def _log_version(self):
        """Runs the tast command locally to log its version."""
        try:
            utils.run([self._tast_path, '-version'],
                      timeout=self._VERSION_TIMEOUT_SEC,
                      stdout_tee=utils.TEE_TO_LOGS,
                      stderr_tee=utils.TEE_TO_LOGS,
                      stderr_is_expected=True,
                      stdout_level=logging.INFO,
                      stderr_level=logging.ERROR)
        except error.CmdError as e:
            logging.error('Failed to log tast version: %s', str(e))

    def _run_tast(self, subcommand, extra_subcommand_args, log_stdout=False):
        """Runs the tast command locally to e.g. list available tests or perform
        testing against the DUT.

        @param subcommand: Subcommand to pass to the tast executable, e.g. 'run'
            or 'list'.
        @param extra_subcommand_args: List of additional subcommand arguments.
        @param log_stdout: If true, write stdout to log.

        @returns client.common_lib.utils.CmdResult object describing the result.

        @raises error.TestFail if the tast command fails or times out.
        """
        cmd = [
            self._tast_path,
            '-verbose',
            '-logtime=false',
            subcommand,
            '-build=false',
            '-remotebundledir=' + self._remote_bundle_dir,
            '-remotedatadir=' + self._remote_data_dir,
            '-remoterunner=' + self._remote_test_runner_path,
        ]
        cmd.extend(extra_subcommand_args)
        cmd.append('%s:%d' % (self._host.hostname, self._host.port))
        cmd.extend(self._test_exprs)

        logging.info('Running ' +
                     ' '.join([utils.sh_quote_word(a) for a in cmd]))
        try:
            return utils.run(cmd,
                             ignore_status=False,
                             timeout=self._SUBCOMMAND_TIMEOUT_SEC[subcommand],
                             stdout_tee=(utils.TEE_TO_LOGS if log_stdout
                                         else None),
                             stderr_tee=utils.TEE_TO_LOGS,
                             stderr_is_expected=True,
                             stdout_level=logging.INFO,
                             stderr_level=logging.ERROR)
        except error.CmdError as e:
            # The tast command's output generally ends with a line describing
            # the error that was encountered; include it in the first line of
            # the TestFail exception.
            lines = e.result_obj.stdout.strip().split('\n')
            msg = (' (last line: %s)' % lines[-1].strip()) if lines else ''
            raise error.TestFail('Failed to run tast%s: %s' % (msg, str(e)))
        except error.CmdTimeoutError as e:
            raise error.TestFail('Got timeout while running tast: %s' % str(e))

    def _get_tests_to_run(self):
        """Runs the tast command to update the list of tests that will be run.

        @raises error.TestFail if the tast command fails or times out.
        """
        logging.info('Getting list of tests that will be run')
        result = self._run_tast('list', ['-json'])
        try:
            self._tests_to_run = json.loads(result.stdout.strip())
        except ValueError as e:
            raise error.TestFail('Failed to parse tests: %s' % str(e))
        if len(self._tests_to_run) == 0:
            expr = ' '.join([utils.sh_quote_word(a) for a in self._test_exprs])
            raise error.TestFail('No tests matched by %s' % expr)

        logging.info('Expect to run %d test(s)', len(self._tests_to_run))

    def _run_tests(self):
        """Runs the tast command to perform testing.

        @raises error.TestFail if the tast command fails or times out (but not
            if individual tests fail).
            """
        logging.info('Running tests')
        self._run_tast('run', ['-resultsdir=' + self.resultsdir],
                       log_stdout=True)

    def _parse_results(self):
        """Parses results written by the tast command.

        @raises error.TestFail if one or more tests failed.
        """
        path = os.path.join(self.resultsdir, self._STREAMED_RESULTS_FILENAME)
        if not os.path.exists(path):
            raise error.TestFail('Results file %s not found' % path)

        failed = []
        with open(path, 'r') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    test = json.loads(line)
                except ValueError as e:
                    raise error.TestFail('Failed to parse %s: %s' % (path, e))
                self._test_results.append(test)
                if test.get('errors'):
                    name = test['name']
                    for err in test['errors']:
                        logging.warning('%s: %s', name, err['reason'])
                    # TODO(derat): Report failures in flaky tests in some other
                    # way.
                    if 'flaky' not in test.get('attr', []):
                        failed.append(name)

        if failed:
            msg = '%d failed: ' % len(failed)
            msg += ' '.join(sorted(failed)[:self._MAX_TEST_NAMES_IN_ERROR])
            if len(failed) > self._MAX_TEST_NAMES_IN_ERROR:
                msg += ' ...'
            raise error.TestFail(msg)

    def _log_all_tests(self):
        """Writes entries to the TKO status.log file describing the results of
        all tests.
        """
        seen_test_names = set()
        for test in self._test_results:
            self._log_test(test)
            seen_test_names.add(test['name'])

        # Report any tests that unexpectedly weren't run.
        for test in self._tests_to_run:
            if test['name'] not in seen_test_names:
                self._log_missing_test(test['name'])

    def _log_test(self, test):
        """Writes events to the TKO status.log file describing the results from
        a Tast test.

        @param test: A JSON object corresponding to a single test from a Tast
            results.json file. See TestResult in
            src/platform/tast/src/chromiumos/cmd/tast/run/results.go for
            details.
        """
        name = self._TEST_NAME_PREFIX + test['name']
        start_time = _rfc3339_time_to_timestamp(test['start'])
        end_time = _rfc3339_time_to_timestamp(test['end'])

        test_reported_errors = bool(test.get('errors'))
        test_skipped = bool(test.get('skipReason'))
        # The test will have a zero (i.e. 0001-01-01 00:00:00 UTC) end time
        # (preceding the Unix epoch) if it didn't report completion.
        test_finished = end_time > 0

        # Avoid reporting tests that were skipped.
        if test_skipped and not test_reported_errors:
            return

        self._log_test_event(self._JOB_STATUS_START, name, start_time)

        if test_finished and not test_reported_errors:
            self._log_test_event(self._JOB_STATUS_GOOD, name, end_time)
            end_status = self._JOB_STATUS_END_GOOD
        else:
            # The previous START event automatically increases the log
            # indentation level until the following END event.
            if test_reported_errors:
                for err in test['errors']:
                    error_time = _rfc3339_time_to_timestamp(err['time'])
                    self._log_test_event(self._JOB_STATUS_FAIL, name,
                                         error_time, err['reason'])
            if not test_finished:
                self._log_test_event(self._JOB_STATUS_FAIL, name, start_time,
                                     'Test did not finish')
                end_time = start_time

            end_status = self._JOB_STATUS_END_FAIL

        self._log_test_event(end_status, name, end_time)

    def _log_missing_test(self, test_name):
        """Writes events to the TKO status.log file describing a Tast test that
        unexpectedly wasn't run.

        @param test_name: Name of the Tast test that wasn't run.
        """
        now = time.time()
        self._log_test_event(self._JOB_STATUS_START, test_name, now)
        self._log_test_event(self._JOB_STATUS_FAIL, test_name, now,
                             'Test was not run')
        self._log_test_event(self._JOB_STATUS_END_FAIL, test_name, now)

    def _log_test_event(self, status_code, test_name, timestamp, message=''):
        """Logs a single event to the TKO status.log file.

        @param status_code: Event status code, e.g. 'END GOOD'. See
            client/common_lib/log.py for accepted values.
        @param test_name: Tast test name, e.g. 'ui.ChromeSanity'.
        @param timestamp: Event timestamp (as seconds since Unix epoch).
        @param message: Optional human-readable message.
        """
        # The TKO parser code chokes on floating-point timestamps.
        entry = base_job.status_log_entry(status_code, None, test_name, message,
                                          None, timestamp=int(timestamp))
        self.job.record_entry(entry, False)


class _LessBrokenParserInfo(dateutil.parser.parserinfo):
    """dateutil.parser.parserinfo that interprets years before 100 correctly.

    Our version of dateutil.parser.parse misinteprets an unambiguous string like
    '0001-01-01T00:00:00Z' as having a two-digit year, which it then converts to
    2001. This appears to have been fixed by
    https://github.com/dateutil/dateutil/commit/fc696254. This parserinfo
    implementation always honors the provided year to prevent this from
    happening.
    """
    def convertyear(self, year):
        return int(year)


def _rfc3339_time_to_timestamp(time_str):
    """Converts an RFC3339 time into a Unix timestamp.

    @param time_str: RFC3339-compatible time, e.g.
        '2018-02-25T07:45:35.916929332-07:00'.

    @returns Float number of seconds since the Unix epoch. Negative if the time
        precedes the epoch.
    """
    dt = dateutil.parser.parse(time_str, parserinfo=_LessBrokenParserInfo())
    return (dt - _UNIX_EPOCH).total_seconds()
