#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright 2021 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import argparse
import ast
from functools import partial
import logging
import os
import re
import subprocess
import sys
import common

from server.cros.dynamic_suite.control_file_getter import FileSystemGetter
from server.cros.dynamic_suite.suite_common import retrieve_for_suite
from autotest_lib.client.common_lib import control_data
from chromiumos.test.api import test_case_metadata_pb2 as tc_metadata_pb


def make_chroot_path_relative(path):
    return re.sub("^.*?/src/", "~/chromiumos/src/", path)


class TestSuite(object):
    def __init__(self, cf_object, name, file_path):
        self.name = name
        self.cf_object = cf_object
        self.tests = []
        self.file_path = file_path

    def relative_path(self):
        # allows user to have filepath which works in/out of chroot
        norm = os.path.normpath(self.file_path)
        return make_chroot_path_relative(norm)

    def add_test(self, test_object):
        self.tests.append(test_object)

    def get_tests(self):
        return self.tests


class TestObject(object):
    def __init__(self, cf_object, file_path):
        self.name = cf_object.name
        self.type = 'tast' if ('tast' in self.name) else 'tauto'
        self.cf_object = cf_object
        self.file_path = file_path
        self.tast_exprs = ''
        self.tast_string = ''

    def get_attributes(self):
        return self.cf_object.attributes

    def relative_path(self):
        # allows user to have filepath which works in/out of chroot
        norm = os.path.normpath(self.file_path)
        return make_chroot_path_relative(norm)

    def is_tast(self):
        return self.type == 'tast'

    # use the python syntax tree library to parse the run function
    # and grab the test_expr from the 'tast' run command
    def parse_cf_for_tast_string(self):
        with open(self.file_path, 'r') as cf:
            mod = ast.parse(cf.read())
            for n in mod.body:
                if n.__class__ != ast.FunctionDef:
                    continue
                if n.name != 'run':
                    continue
                for sub_node in n.body:
                    if sub_node.__class__ != ast.Expr:
                        continue
                    try:
                        fn_name = sub_node.value.func.value.id
                        if fn_name != 'job':
                            continue
                    except:
                        continue
                    if sub_node.value.func.attr != 'run_test':
                        continue
                    for keyword in sub_node.value.keywords:
                        if keyword.arg == 'test_exprs' and keyword.value.__class__ == ast.List:
                            test_exprs = []
                            regex_list = False
                            for elem in keyword.value.elts:
                                try:
                                    test_exprs.append(elem.s)
                                    regex_list = ('(' in elem.s or regex_list)
                                except AttributeError:
                                    logging.warning(
                                            'Non-standard test found, check %s manually',
                                            self.relative_path())
                                    break
                            if regex_list:
                                self.tast_string = ' '.join(test_exprs)
                            else:
                                for it in range(len(test_exprs) - 1):
                                    test_exprs[it] = test_exprs[it] + ','
                                self.tast_string = ' '.join(test_exprs)

    def enumerate_tast_from_test_expr(self):
        self.parse_cf_for_tast_string()
        try:
            self.tast_exprs = self.tast_string.split(', ')
        except AttributeError:
            logging.warning('Non-standard test found, check %s manually',
                            self.relative_path())
        if len(self.mapped_requirements()) > 0:
            logging.error(
                    '%s mapped to a requirement, autotest tast wrappers cannot be mapped to requiremnts, please mapp directly to the tast tests themselves',
                    self.name)

    def enumerate_tests_from_tast_exprs(self, dut):
        tests = []
        logging.info('Enumerating tast tests from test %s: expression: %s' %
                     (self.name, self.tast_exprs))
        for expr in self.tast_exprs:
            en = subprocess.check_output(
                    ['tast', 'list', str(dut),
                     str(expr)], encoding='utf-8')
            for t in en.split('\n'):
                if t == '':
                    continue
                tests.append(t)
            en = subprocess.check_output([
                    'tast', 'list', '-buildbundle=crosint',
                    str(dut),
                    str(expr)
            ],
                                         encoding='utf-8')
            for t in en.split('\n'):
                if t == '':
                    continue
                tests.append(t)

        return tests

    def describe(self):
        return 'test named ' + self.name + ' of type ' + self.type

    def mapped_requirements(self):
        with open(self.file_path, 'r') as cf:
            contents = cf.read()
            test = control_data.parse_control_string(contents,
                                                     raise_warnings=True,
                                                     path=self.file_path)
            return test.metadata.get('requirements', [])
        return []


class TestParser(object):
    def get_all_test_objects(self, locations):
        tests = {}
        suites = {}

        cf_getter = FileSystemGetter(locations)
        for (file_path, cf_object) in retrieve_for_suite(cf_getter,
                                                         '').items():
            if cf_object.test_class == 'suite' or self.in_suites_dir(
                    file_path):
                if cf_object.test_class != 'suite':
                    logging.warn(
                            'Treating unmarked suite %s as a suite based on control file path, expected TEST_CLASS = \'suite\' in the control file',
                            cf_object.name)
                suites[cf_object.name] = (TestSuite(cf_object, cf_object.name,
                                                    file_path))
            else:
                tests[cf_object.name] = (TestObject(cf_object, file_path))
                if tests[cf_object.name].is_tast():
                    tests[cf_object.name].enumerate_tast_from_test_expr()

        return tests, suites

    def in_suites_dir(self, file_path):
        split = os.path.split(file_path)
        split = os.path.split(split[0])
        return len(split) > 0 and split[1] == 'test_suites'


class TestManager(object):
    def __init__(self):
        self.tests = {}
        self.suites = {}
        self.dut = None
        self.log_functions = [partial(print)]
        self.test_parser = TestParser()

    def log(self, log_text, *args):
        for fn in self.log_functions:
            fn(log_text, *args)

    def csv_logger(self, log_text, file_path):
        with open(file_path, 'a') as log:
            log.write(log_text)

    def register_csv_logger(self, file_path):
        if os.path.exists(file_path):
            os.remove(file_path)
        print_to_csv = partial(self.csv_logger, file_path=file_path)
        self.log_functions.append(print_to_csv)
        print_to_csv('suite,test\n')

    def initialize_from_fs(self, locations):
        self.tests, self.suites = self.test_parser.get_all_test_objects(
                locations)

    def process_all_tests(self):
        for test, test_object in self.tests.items():
            for suite in test_object.get_attributes():
                target_suite = self.find_suite_named(suite)
                if target_suite is not None:
                    target_suite.add_test(test)

    def set_dut(self, target):
        self.dut = target

    def get_dut(self):
        if self.dut is not None:
            return self.dut
        else:
            raise AttributeError(
                    'DUT Address not set, please use the --dut flag to indicate the ip address of the DUT'
            )

    def find_test_named(self, test_name):
        try:
            queried_test = self.tests[test_name]
            return queried_test
        except KeyError:
            return None

    def find_suite_named(self, suite_name):
        try:
            if suite_name[0:6] == 'suite.':
                queried_suite = self.suites[suite_name[6:]]
            elif suite_name[0:6] == 'suite:':
                queried_suite = self.suites[suite_name[6:]]
            else:
                queried_suite = self.suites[suite_name]
            return queried_suite
        except KeyError:
            return None

    def list_suite_named(self, suite_name, pretty=False):
        suite_tests = []
        suite = self.find_suite_named(suite_name)

        if suite is None:
            if pretty:
                return '\n'
            return suite_tests

        for test in suite.get_tests():
            if self.tests[test].is_tast():
                found_tests = self.tests[test].enumerate_tests_from_tast_exprs(
                        self.get_dut())
                for t in found_tests:
                    if t == '':
                        continue
                    suite_tests.append('tast.' + str(t))
            else:
                suite_tests.append(test)

        if pretty:
            out_as_string = ''
            for test in suite_tests:
                out_as_string += suite_name + ',' + str(test) + '\n'
            return out_as_string
        return suite_tests

    def gs_query_link(self, suite_name):
        test_names = ','.join([
                test for test in self.list_suite_named(suite_name)
                if test != ''
        ])

        query = 'https://dashboards.corp.google.com/'
        query += '_86acf8a8_50a5_48e0_829e_fbf1033d3ac6'
        query += '?f=test_name:in:' + test_names
        query += '&f=create_date_7_day_filter:in:Past%207%20Days'
        query += '&f=test_type:in:Tast,Autotest'

        return query

    def graph_suite_named(self, suite_name, dot_graph=None):
        # import here to allow running other functionality without needing PIP
        # in chroot
        import graphviz
        suite_tests = self.list_suite_named(suite_name)
        nodes_at_rank = 0

        if dot_graph is None:
            dot_graph = graphviz.Digraph(comment=suite_name)

        dot_graph.node(suite_name, suite_name)
        last_level = suite_name
        child_graph = None

        for test_name in suite_tests:
            if nodes_at_rank == 0:
                child_graph = graphviz.Digraph()
                dot_graph.edge(last_level, test_name)
                last_level = test_name

            child_graph.node(test_name, test_name)
            dot_graph.edge(suite_name, test_name)

            if nodes_at_rank == 6:
                dot_graph.subgraph(child_graph)

            nodes_at_rank += 1
            nodes_at_rank %= 7

        dot_graph.subgraph(child_graph)

        return dot_graph

    def diff_test_suites(self, suite_a, suite_b):
        res = ''
        suite_a_set = set(self.list_suite_named(suite_a))
        suite_b_set = set(self.list_suite_named(suite_b))
        res = res + ('Suite B (+)' + str(list(suite_b_set - suite_a_set)))
        res = res + '\n'
        res = res + ('Suite B (-)' + str(list(suite_a_set - suite_b_set)))
        return res


class TastManager(object):
    def __init__(self):
        # hack to get metadata including local changes to tast files
        # use fastbuild and then export to proto and parse the proto
        basepath = os.path.dirname(os.path.abspath(__file__))
        tast_path = os.path.normpath(
                os.path.join(basepath, '../../../../platform/tast'))
        cwd = os.getcwd()
        os.chdir(tast_path)
        if os.system(
                './fast_build.sh -b chromiumos/tast/local/bundles/cros -o local-tests'
        ):
            raise Exception(
                    "cannot build tast local bundle for tast metadata reading")
        if os.system(
                './fast_build.sh -b chromiumos/tast/remote/bundles/cros -o remote-tests'
        ):
            raise Exception(
                    "cannot build tast remote bundle for tast metadata reading"
            )
        data = subprocess.check_output(['./local-tests', '-exportmetadata'])
        self.metadata = tc_metadata_pb.TestCaseMetadataList()
        self.metadata.ParseFromString(data)
        data = subprocess.check_output(['./remote-tests', '-exportmetadata'])
        self.metadata.MergeFromString(data)
        os.chdir(cwd)

    def find_test_named(self, name):
        for metadata in self.metadata.values:
            if metadata.test_case.id.value == name:
                return TastTest(name, metadata)
        return None


class TastTest(object):
    def __init__(self, name, metadata):
        self.name = name
        self.metadata = metadata

    def mapped_requirements(self):
        ret = []
        for req in self.metadata.test_case_info.requirements:
            ret.append(req.value)
        return ret

    def relative_path(self):
        # use grep to find a tast source based on test name
        basepath = os.path.dirname(os.path.abspath(__file__))
        tast_src = os.path.normpath(
                os.path.join(
                        basepath,
                        '../../../../platform/tast-tests/src/chromiumos/tast'))
        parts = self.name.split('.')[1:]
        for i in range(len(parts) - 1, 0, -1):
            for subdir in ['remote', 'local']:
                search_dir = os.path.join(tast_src, subdir, 'bundles', 'cros',
                                          *parts[0:i])
                regex = 'Func: *%s,' % (parts[i])
                try:
                    out = subprocess.check_output(
                            ['grep', '-IRl', regex, search_dir],
                            stderr=subprocess.DEVNULL)
                    path = out.decode('utf-8').strip('\n')
                    return make_chroot_path_relative(path)
                except subprocess.CalledProcessError:
                    pass
            # os.system('grep -IR "Func: *%s" %s,' % (part, tast_src))
        return "Unknown path for tast test"


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
    # pass in the url for the DUT via ssh
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
