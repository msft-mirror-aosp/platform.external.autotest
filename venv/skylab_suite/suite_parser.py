# Copyright 2018 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Parse & Validate CLI arguments for run_suite_skylab.py."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import argparse
import ast
import sys

from lucifer import autotest
from skylab_suite import cros_suite
from skylab_suite import swarming_lib


def make_parser():
    """Make ArgumentParser instance for run_suite_skylab.py."""
    parser = argparse.ArgumentParser(prog='run_suite_skylab',
                                     description=__doc__)

    # Suite-related parameters.
    parser.add_argument('--board', required=True)
    parser.add_argument(
            '--model',
            help=('The device model to run tests against. For non-unified '
                  'builds, model and board are synonymous, but board is more '
                  'accurate in some cases. Only pass this option if your build '
                  'is a unified build.'))
    parser.add_argument(
        '--pool', default='suites',
        help=('Specify the pool of DUTs to run this suite. If you want no '
              'pool, you can specify it with --pool="". USE WITH CARE.'))
    parser.add_argument(
        '--suite_name', required=True,
        help='Specify the suite to run.')
    parser.add_argument(
        '--build', required=True,
        help='Specify the build to run the suite with.')
    parser.add_argument(
        '--cheets_build', default=None,
        help='ChromeOS Android build to be installed on dut.')
    parser.add_argument(
        '--firmware_rw_build', default=None,
        help='Firmware build to be installed in dut RW firmware.')
    parser.add_argument(
        '--firmware_ro_build', default=None,
        help='Firmware build to be installed in dut RO firmware.')
    parser.add_argument(
        '--test_source_build', default=None,
        help=('Build that contains the test code. It can be the value '
              'of arguments "--build", "--firmware_rw_build" or '
              '"--firmware_ro_build". Default is to use test code from '
              'the "--build" version (CrOS image)'))
    parser.add_argument(
        '--priority', type=int,
        default=swarming_lib.SKYLAB_HWTEST_PRIORITIES_MAP['Default'],
        choices=[value for name, value in
                 swarming_lib.SORTED_SKYLAB_HWTEST_PRIORITY],
        help=('The priority to run the suite. A high value means this suite '
              'will be executed in a low priority, e.g. being delayed to '
              'execute. Each numerical value represents: '+ ', '.join([
                  '(%s: %d)' % (name, value) for name, value in
                  swarming_lib.SORTED_SKYLAB_HWTEST_PRIORITY])))
    parser.add_argument(
        "--suite_args", type=ast.literal_eval, default=None,
        action="store",
        help="A dict of args passed to the suite control file.")
    parser.add_argument(
        "--job_keyvals", type=ast.literal_eval, default={},
        action="store",
        help="A dict of job keyvals to be passed to child jobs.")
    parser.add_argument(
        "--minimum_duts", type=int, default=1, action="store",
        help="A minimum required numbers of DUTs to run this suite.")
    parser.add_argument(
        "--use_fallback", action="store_true",
        help=('Whether to kick off the child tests with fallback request. '
              'If it is enabled, the suite will be kicked off no matter '
              'whether there are well-provisioned DUTs. If not, '
              'provision will be executed before each test first.'))

    # Swarming-related parameters.
    parser.add_argument(
        '--swarming', default=None,
        help='The swarming server to call.')
    parser.add_argument(
        '--execution_timeout_seconds', type=int, default=30,
        help='Seconds to allow a task to complete, once execution beings.')

    # logic-related parameters.
    parser.add_argument(
        '--create_and_return', action='store_true',
        help='Create the child jobs of a suite, then finish immediately.')
    parser.add_argument(
        '--suite_id', default=None,
        help='A suite ID, wait for whose child tests to finish.')
    parser.add_argument(
        '--test_retry', default=False, action='store_true',
        help='Enable test-level retry.')
    parser.add_argument(
        '--max_retries', default=0, type=int, action='store',
        help='Maximum retries allowed at suite level. No retry if it is 0.')
    parser.add_argument(
        '--timeout_mins', default=90, type=int, action='store',
        help='Maximum minutes to wait for a suite to finish.')
    parser.add_argument(
        '--run_prod_code', action='store_true', default=False,
        help='Run the test code that lives in prod aka the test '
        'code currently on the lab servers.')
    parser.add_argument(
        '--dry_run', action='store_true',
        help=('Used for kicking off a run of suite with fake commands.'))
    parser.add_argument(
        '--do_nothing', action='store_true',
        help=('Used for monitoring purposes, to measure no-op swarming proxy '
              'latency or create a dummy run_suite_skylab run.'))

    # Abort-related parameters.
    parser.add_argument(
        '--abort_limit', default=sys.maxint, type=int, action='store',
        help=('Only abort first N parent tasks which fulfill the search '
              'requirements.'))
    parser.add_argument(
        '--suite_task_ids', nargs='*', default=[],
        help=('Specify the parent swarming task id to abort.'))

    return parser


def verify_and_clean_options(options):
    """Validate options."""
    if options.suite_args is None:
        options.suite_args = {}

    return True


def parse_suite_spec(options):
    """Parse options to suite_spec."""
    suite_common = autotest.load('server.cros.dynamic_suite.suite_common')
    builds = suite_common.make_builds_from_options(options)
    return cros_suite.SuiteSpec(
            builds=builds,
            suite_name=options.suite_name,
            suite_file_name=suite_common.canonicalize_suite_name(
                    options.suite_name),
            test_source_build=suite_common.get_test_source_build(
                    builds, test_source_build=options.test_source_build),
            suite_args=options.suite_args,
            priority=options.priority,
            board=options.board,
            pool=options.pool,
            job_keyvals=options.job_keyvals,
            minimum_duts=options.minimum_duts,
            timeout_mins=options.timeout_mins,
    )
