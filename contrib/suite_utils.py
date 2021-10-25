import common
import os
import subprocess

import graphviz

from server.cros.dynamic_suite.control_file_getter import FileSystemGetter
from server.cros.dynamic_suite.suite_common import retrieve_for_suite
import argparse, ast, re


class TestSuite(object):
    def __init__(self, cf_object, name, file_path):
        self.name = name
        self.cf_object = cf_object
        self.tests = []
        self.file_path = file_path

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

    def get_attributes(self):
        return self.cf_object.attributes

    def is_tast(self):
        if (self.type == 'tast'):
            return True
        else:
            return False

    # use the python syntax tree library to parse the run function
    # and grab the test_expr from the 'tast' run command
    def parse_cf_for_tast_string(self):
        with open(self.file_path, 'r') as cf:
            mod = ast.parse(cf.read())
            for n in mod.body:
                if (n.__class__ != ast.FunctionDef):
                    continue
                if (n.name != 'run'):
                    continue
                for sub_node in n.body:
                    if (sub_node.__class__ != ast.Expr):
                        continue
                    if (sub_node.value.func.value.id != 'job'):
                        continue
                    if (sub_node.value.func.attr != 'run_test'):
                        continue
                    for keyword in sub_node.value.keywords:
                        if (keyword.arg == 'test_exprs'):
                            test_exprs = []
                            regex_list = False
                            for elem in keyword.value.elts:
                                try:
                                    test_exprs.append(elem.s)
                                    regex_list = ("(" in elem.s
                                                  or regex_list == True)
                                except AttributeError:
                                    print("WARNING: Non-standard test found, check"
                                          + self.file_path + " manually")
                                    break
                            if regex_list:
                                self.tast_string = ' '.join(test_exprs)
                            else:
                                for it in range(len(test_exprs) - 1):
                                    test_exprs[it] = test_exprs[it] + ","
                                self.tast_string = ' '.join(test_exprs)

    def enumerate_tast_from_test_expr(self):
        self.parse_cf_for_tast_string()
        try:
            self.tast_exprs = self.tast_string.split(', ')
        except AttributeError:
            print("WARNING: Non-standard test found, check" + self.file_path +
                  " manually")

    def enumerate_tests_from_tast_exprs(self, dut):
        tests = []
        for expr in self.tast_exprs:
            en = subprocess.check_output(["tast", "list", str(dut), str(expr)])
            for t in en.split('\n'):
                if t is '':
                    continue
                tests.append(t)
            en = subprocess.check_output([
                    "tast", "list", "-buildbundle=crosint",
                    str(dut),
                    str(expr)
            ])
            for t in en.split('\n'):
                if t is '':
                    continue
                tests.append(t)

        return tests

    def describe(self):
        return "test named " + self.name + " of type " + self.type


class TestParser(object):
    def get_all_test_objects(self, locations):
        tests = {}
        suites = {}

        cf_getter = FileSystemGetter(locations)
        for (file_path, cf_object) in retrieve_for_suite(cf_getter,
                                                         "").items():
            if cf_object.test_class == "suite":
                suites[cf_object.name] = (TestSuite(cf_object, cf_object.name,
                                                    file_path))
            else:
                tests[cf_object.name] = (TestObject(cf_object, file_path))
                if tests[cf_object.name].is_tast():
                    tests[cf_object.name].enumerate_tast_from_test_expr()

        return tests, suites


class TestManager(object):
    def __init__(self):
        self.tests = {}
        self.suites = {}
        self.dut = None

    def initialize_from_fs(self, locations):
        self.test_parser = TestParser()
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
            if suite_name[0:6] == "suite.":
                queried_suite = self.suites[suite_name[6:]]
            elif suite_name[0:6] == "suite:":
                queried_suite = self.suites[suite_name[6:]]
            else:
                queried_suite = self.suites[suite_name]
            return queried_suite
        except KeyError:
            return None

    def list_suite_named(self, suite_name):
        suite_tests = []
        suite = self.find_suite_named(suite_name)

        if suite is None:
            return suite_tests

        for test in suite.get_tests():
            if self.tests[test].is_tast():
                found_tests = self.tests[test].enumerate_tests_from_tast_exprs(
                        self.get_dut())
                for t in range(len(found_tests)):
                    suite_tests.append("tast." + str(found_tests[t]))
            else:
                suite_tests.append(test)
        return suite_tests

    def gs_query_link(self, suite_name):
        test_names = ""
        for test in self.list_suite_named(suite_name):
            if test_names != "":
                test_names += ","
            test_names += test

        query = "https://dashboards.corp.google.com/"
        query += "_86acf8a8_50a5_48e0_829e_fbf1033d3ac6"
        query += "?f=test_name:in:" + test_names
        query += "&f=create_date_7_day_filter:in:Past%207%20Days"
        query += "&f=test_type:in:Tast,Autotest"

        return query

    def graph_suite_named(self, suite_name, dot_graph=None):
        suite_tests = self.list_suite_named(suite_name)

        nodes_at_rank = 0
        rank_num = 0

        if dot_graph == None:
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
        res = ""
        suite_a_set = set(self.list_suite_named(suite_a))
        suite_b_set = set(self.list_suite_named(suite_b))
        res = res + ("Suite B (+)" + str(list(suite_b_set - suite_a_set)))
        res = res + "\n"
        res = res + ("Suite B (-)" + str(list(suite_a_set - suite_b_set)))
        return res


def main(args):

    args = vars(args)

    tests = TestManager()

    basepath = os.path.dirname(os.path.abspath(__file__))
    tests.initialize_from_fs([(basepath + "/../test_suites"),
                              (basepath + "/../server/site_tests"),
                              (basepath + "/../client/site_tests")])
    tests.process_all_tests()

    if args['dut'] is not None:
        tests.set_dut(args['dut'][0])
    if args['find_test'] is not None:
        test = tests.find_test_named(args['find_test'][0])
        if test is not None:
            print(test.file_path)
        else:
            print("Queried test not found")
    if args['find_suite'] is not None:
        suite = tests.find_suite_named(args['find_suite'][0])
        if suite is not None:
            print(suite.file_path)
        else:
            print("Queried suite not found")
    if args['list_suite'] is not None:
        print(tests.list_suite_named(args['list_suite'][0]))
    if args['diff'] is not None:
        print(tests.diff_test_suites(args['diff'][0], args['diff'][1]))
    if args['graph_suite'] is not None:
        graph = tests.graph_suite_named(args['graph_suite'][0])
        graph.render('./suite_data/suite_viz.gv', format='png')
    if args['gs_dashboard'] is not None:
        if len(args['gs_dashboard']) > 1:
            link = tests.gs_query_link(args['gs_dashboard'][0],
                                       args['gs_dashboard'][1])
        else:
            link = tests.gs_query_link(args['gs_dashboard'][0])

        print(link)


if __name__ == "__main__":
    # pass in the url for the DUT via ssh
    parser = argparse.ArgumentParser()
    parser.add_argument(
            '--diff',
            nargs=2,
            help=
            'show diff between two suites. Ex: --diff bvt-tast-cq pvs-tast-cq')
    parser.add_argument('--find_test',
                        nargs=1,
                        help='find control file for test_name')
    parser.add_argument('--find_suite',
                        nargs=1,
                        help='find control file for suite_name')
    parser.add_argument(
            '--graph_suite',
            nargs=1,
            help=
            'graph test dependencies of suite_name, will output to contrib/suite_data'
    )
    parser.add_argument('--list_suite',
                        nargs=1,
                        help='list units in suite_name')
    parser.add_argument('--dut',
                        nargs=1,
                        help='ip address and port for tast enumeration')
    parser.add_argument(
            '--gs_dashboard',
            nargs='+',
            help='generate green stainless dashboard for suite_name')
    args = parser.parse_args()

    main(args)
