#!/usr/bin/python3
# Copyright 2021 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Generate metadata for build from Autotest ctrl files."""

import argparse
import os
import six
import sys

# If running in Autotest dir, keep this.
os.environ["PY_VERSION"] = '3'

import common

# NOTE: this MUST be run in Python3, if we get configured back to PY2, exit.
if six.PY2:
    exit(1)

from autotest_lib.server.cros.dynamic_suite import control_file_getter
from autotest_lib.client.common_lib import control_data

from chromiumos.test.api import test_case_metadata_pb2 as tc_metadata_pb
from chromiumos.test.api import test_harness_pb2 as th_pb
from chromiumos.test.api import test_case_pb2 as tc_pb

HARNESS = th_pb.TestHarness.Tauto()


def parse_local_arguments(args):
    """Parse the CLI."""
    parser = argparse.ArgumentParser(
            description="Prep Autotest, Tast, & Services for DockerBuild.")
    parser.add_argument('-autotest_path',
                        dest='autotest_path',
                        default='../../../../third_party/autotest/files/',
                        help='path to autotest/files relative to this script.')
    parser.add_argument('-output_file',
                        dest='output_file',
                        default=None,
                        help='Where to write the serialized pb.')
    return parser.parse_args(args)


def read_file(filename):
    """Read the given file."""
    with open(filename, 'r') as f:
        return f.read()


def all_control_files(args):
    """Return all control files as control file objs."""
    subpaths = ['server/site_tests', 'client/site_tests']
    start_cwd = os.getcwd()
    try:
        os.chdir(args.autotest_path)

        # Might not be needed, but this resolves out the ../
        autotest_path = os.getcwd()

        directories = [os.path.join(autotest_path, p) for p in subpaths]
        f = control_file_getter.FileSystemGetter(directories)
    except Exception as e:
        raise Exception("Failed to find control files at path %s",
                        args.autotest_path)

    finally:
        os.chdir(start_cwd)
    return f._get_control_file_list()

def serialize_contacts(data):
    """Return a serialized Contact obj list"""
    serialized_contacts = []
    if hasattr(data, 'metadata') and 'contacts' in data.metadata:
        serialized_contacts = [tc_metadata_pb.Contact(email=e) for e in data.metadata['contacts']]
    elif hasattr(data, 'author'):
        serialized_contacts = [tc_metadata_pb.Contact(email=data.author)]
    else:
        raise Exception("Test had neither contacts nor (old) author field.")

    return serialized_contacts

def serialize_requirements(data):
    """Return a serialized Requirements obj list"""
    requirements = []
    if hasattr(data, 'metadata') and 'requirements' in data.metadata:
        requirements = [tc_metadata_pb.Requirement(value=r) for r in data.metadata['requirements']]

    return requirements

def serialize_bug_component(data):
    """Return a serialized BugComponent obj"""
    bug_component = None
    if hasattr(data, 'metadata') and 'bug_component' in data.metadata:
        bug_component = tc_metadata_pb.BugComponent(value=data.metadata['bug_component'])
    return bug_component


def serialize_variant_category(data):
    """Return a serialized VariantCategory obj"""
    variant_category = None
    if hasattr(data, 'metadata') and 'variant_category' in data.metadata:
        variant_category = tc_metadata_pb.DDDVariantCategory(
                value=data.metadata['variant_category'])
    return variant_category


def serialize_criteria(data):
    """Return a serialized Criteria obj"""
    criteria = None
    if hasattr(data, 'metadata') and 'criteria' in data.metadata:
        criteria = tc_metadata_pb.Criteria(value=data.metadata['criteria'])
    return criteria

def serialize_hw_agnostic(data):
    """Return a serialized HwAgnostic obj"""
    hw_agnostic = None
    if hasattr(data, 'metadata') and 'hw_agnostic' in data.metadata:
        hw_agnostic = tc_metadata_pb.HwAgnostic(value=data.metadata['hw_agnostic'])
    return hw_agnostic


def serialize_life_cycle_stage(data):
    """Return a serialized LifeCycle obj"""
    lc_pb = tc_metadata_pb.LifeCycleStage.LifeCycle
    conversions = {
            'production': lc_pb.LIFE_CYCLE_PRODUCTION_READY,
            'disabled': lc_pb.LIFE_CYCLE_DISABLED,
            'in_development': lc_pb.LIFE_CYCLE_IN_DEVELOPMENT,
            'manual_only': lc_pb.LIFE_CYCLE_MANUAL_ONLY,
            'owner_monitored': lc_pb.LIFE_CYCLE_OWNER_MONITORED,
    }
    test_value = 'production'
    if (hasattr(data, 'metadata') and 'life_cycle_stage' in data.metadata
                and data.metadata['life_cycle_stage'] in conversions):
        test_value = data.metadata['life_cycle_stage']

    return tc_metadata_pb.LifeCycleStage(value=conversions[test_value])


def serialize_test_case_info(data):
    """Return a serialized TestCaseInfo obj."""

    return tc_metadata_pb.TestCaseInfo(
            owners=serialize_contacts(data),
            requirements=serialize_requirements(data),
            bug_component=serialize_bug_component(data),
            criteria=serialize_criteria(data),
            hw_agnostic=serialize_hw_agnostic(data),
            life_cycle_stage=serialize_life_cycle_stage(data),
            variant_category=serialize_variant_category(data))


def serialized_deps(data):
    """Return a serialized deps obj (list)."""
    serialized_deps = []
    for value in data.dependencies:
        serialized_deps.append(tc_pb.TestCase.Dependency(value=value))
    return serialized_deps


def serialized_build_deps(data):
    """Return a serialized build_deps obj (list)."""
    serialized_build_deps = []
    for value in data.hw_deps:
        serialized_build_deps.append(tc_pb.TestCase.BuildDeps(value=value))
    return serialized_build_deps


def serialize_tags(data):
    """Return a serialized tags obj (list)."""
    serialized_tags = []
    for value in data.attributes:
        serialized_tags.append(tc_pb.TestCase.Tag(value=value))
    if data.test_class:
        serialized_tags.append(
                tc_pb.TestCase.Tag(
                        value="test_class:{}".format(data.test_class)))
    return serialized_tags


def serialize_test_case(data):
    """Return a serialized api.TestCase obj."""
    serialized_testcase_id = tc_pb.TestCase.Id(value="tauto." + data.name)
    tags = serialize_tags(data)
    deps = serialized_deps(data)
    build_deps = serialized_build_deps(data)
    return tc_pb.TestCase(id=serialized_testcase_id,
                          name=data.name,
                          tags=tags,
                          dependencies=deps,
                          build_dependencies=build_deps)


def serialized_test_case_exec(data):
    """Return a serialized TestCaseExec obj."""
    serialized_test_harness = th_pb.TestHarness(tauto=HARNESS)
    return tc_metadata_pb.TestCaseExec(test_harness=serialized_test_harness)


def serialized_test_case_metadata(data):
    """Return a TestCaseMetadata obj from a given control file."""
    serialized_meta_data = tc_metadata_pb.TestCaseMetadata(
            test_case_exec=serialized_test_case_exec(data),
            test_case=serialize_test_case(data),
            test_case_info=serialize_test_case_info(data))
    return serialized_meta_data


def serialized_test_case_metadata_list(data):
    """Return a TestCaseMetadataList obj from a list of TestCaseMetadata pb."""
    serialized_meta_data_list = tc_metadata_pb.TestCaseMetadataList(
            values=data)
    return serialized_meta_data_list


def main():
    """Generate the metadata, and if an output path is given, save it."""
    args = parse_local_arguments(sys.argv[1:])
    ctrlfiles = all_control_files(args)
    serialized_metadata = []
    for file_path in ctrlfiles:
        text = read_file(file_path)
        path = ctrlfiles[1]

        test = control_data.parse_control_string(text,
                                                 raise_warnings=True,
                                                 path=path)
        serialized_metadata.append(serialized_test_case_metadata(test))

    serialized = serialized_test_case_metadata_list(serialized_metadata)
    if args.output_file:
        with open(args.output_file, 'wb') as wf:
            wf.write(serialized.SerializeToString())


if __name__ == '__main__':
    main()
