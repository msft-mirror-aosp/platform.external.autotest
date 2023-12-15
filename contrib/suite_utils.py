#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright 2023 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
#
# suite_utils.py will enumerate tests from a suite

import argparse
import logging
import os
import sys


from suite_lib import TastManager
from suite_lib import TestManager


def main(args):
    if args.q:
        args.log = 'ERROR'
    root = logging.getLogger()
    root.setLevel(args.log.upper())
    root_handler = root.handlers[0]
    root_handler.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
    tests = TestManager()

    basepath = os.path.dirname(os.path.abspath(__file__))
    tests.initialize_from_fs([(basepath + '/../test_suites'),
                              (basepath + '/../server/site_tests'),
                              (basepath + '/../client/site_tests')])
    tests.process_all_tests()

    if args.csv is not None:
        tests.register_csv_logger(args.csv)
    if args.dut is not None:
        tests.set_dut(args.dut)
    if args.find_test is not None:
        test = tests.find_test_named(args.find_test)
        if test is not None:
            tests.log(test.relative_path())
        else:
            tests.log('Queried test not found')
    if args.find_suite is not None:
        suite = tests.find_suite_named(args.find_suite)
        if suite is not None:
            tests.log(suite.relative_path())
        else:
            tests.log('Queried suite not found')
    if args.list_suite is not None:
        tast_tests = TastManager()
        tests.log(tests.list_suite_named(args.list_suite, pretty=True))
    if args.list_multiple_suites is not None:
        for suite_name in args.list_multiple_suites:
            tests.log(tests.list_suite_named(suite_name, pretty=True))
    if args.diff is not None:
        tests.log(tests.diff_test_suites(args.diff[0], args.diff[1]))
    if args.graph_suite is not None:
        graph = tests.graph_suite_named(args.graph_suite)
        graph.render('./suite_data/suite_viz.gv', format='png')
    if args.gs_dashboard is not None:
        link = tests.gs_query_link(args.gs_dashboard)
        tests.log(link)
    if args.check_requirements:
        tast_tests = TastManager()
        suite = args.check_requirements[0]
        req_id = None
        if len(args.check_requirements) > 1:
            req_id = args.check_requirements[1]
        for test_name in tests.list_suite_named(suite):
            manager = tests
            if test_name.startswith('tast.'):
                manager = tast_tests
            test = manager.find_test_named(test_name)
            if test is None:
                logging.error('error could not find any info on test: %s',
                              test_name)
                continue
            if req_id is None and len(test.mapped_requirements()) == 0:
                print('%s: is not mapped to any requirements, source: %s' %
                      (test.name, test.relative_path()))
            elif req_id is not None and req_id not in test.mapped_requirements(
            ):
                print('%s: is not mapped to requirement %s, source: %s' %
                      (test.name, req_id, test.relative_path()))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--csv',
                        help='supply csv file path for logging output')
    parser.add_argument(
            '--diff',
            nargs=2,
            help=
            'show diff between two suites. Ex: --diff bvt-tast-cq pvs-tast-cq')
    parser.add_argument('--find_test',
                        help='find control file for test_name')
    parser.add_argument('--find_suite',
                        help='find control file for suite_name')
    parser.add_argument(
            '--graph_suite',
            help=
            'graph test dependencies of suite_name, will output to contrib/suite_data'
    )
    parser.add_argument('--list_suite',
                        help='list units in suite_name')
    parser.add_argument(
            '--list_multiple_suites',
            nargs='*',
            help='list units in suite_name_1 suite_name_2 suite_name_n')
    parser.add_argument('--dut',
                        help='ip address and port for tast enumeration')
    parser.add_argument(
            '--gs_dashboard',
            help='generate green stainless dashboard for suite_name')
    parser.add_argument(
            '--check-requirements',
            nargs='*',
            help=
            'check if there are requirements mapped to all tests in the suite takes a suite_name and an optional requirement ID'
    )
    parser.add_argument('-q',
                        action='store_true',
                        help='quiet mode (same as --log error)',
                        default=False)
    parser.add_argument(
            "--log",
            help=
            "Provide logging level. Example --log debug (debug,info,warn,error)'",
            default='info')
    parsed_args = parser.parse_args()

    main(parsed_args)