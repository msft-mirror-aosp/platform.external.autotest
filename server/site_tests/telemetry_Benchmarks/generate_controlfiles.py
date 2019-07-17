#!/usr/bin/env python

"""
This file generates all telemetry_Benchmarks control files from a master list.
"""

from datetime import datetime
import os
import re

# This test list is a subset of telemetry benchmark tests. The full list can be
# obtained by executing
# /build/${BOARD}/usr/local/telemetry/src/tools/perf/list_benchmarks

# PLEASE READ THIS:

# PERF_TESTS: these tests run on each build: tot, tot-1, tot-2 and expensive to
# run.

# PERF_DAILY_RUN_TESTS: these tests run on a nightly build: tot. If you are
# trying to gain confidence for a new test, adding your test in this list is a
# good start.

# For adding a new test to any of these lists, please add rohitbm, lafeenstra,
# haddowk in the change.

PERF_PER_BUILD_TESTS = (
    'cros_ui_smoothness',
    'jetstream',
    'kraken',
    'loading.desktop',
    'octane',
    'rendering.desktop',
    'speedometer',
    'speedometer2',
)

PERF_DAILY_RUN_TESTS = (
    'blink_perf.image_decoder',
    'cros_tab_switching.typical_24',
    'dromaeo',
    'media.desktop',
    'memory.desktop',
    'smoothness.tough_pinch_zoom_cases',
    'system_health.memory_desktop',
    'webrtc',
)

PERF_WEEKLY_RUN_TESTS = (
)

ALL_TESTS = (PERF_PER_BUILD_TESTS +
             PERF_DAILY_RUN_TESTS +
             PERF_WEEKLY_RUN_TESTS)

EXTRA_ARGS_MAP = {
    'loading.desktop': '--story-tag-filter=typical',
    'rendering.desktop': '--story-tag-filter=top_real_world_desktop',
    'system_health.memory_desktop': '--pageset-repeat=1',
}

DEFAULT_YEAR = str(datetime.now().year)

DEFAULT_AUTHOR = 'Chrome OS Team'

CONTROLFILE_TEMPLATE = (
"""# Copyright {year} The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# Do not edit this file! It was created by generate_controlfiles.py.

from autotest_lib.client.common_lib import utils

AUTHOR = '{author}'
NAME = 'telemetry_Benchmarks.{test}'
{attributes}
TIME = 'LONG'
TEST_CATEGORY = 'Benchmark'
TEST_CLASS = 'performance'
TEST_TYPE = 'server'

DOC = '''
This server side test suite executes the Telemetry Benchmark:
{test}
This is part of Chrome for Chrome OS performance testing.

Pass local=True to run with local telemetry and no AFE server.
'''

def run_benchmark(machine):
    host = hosts.create_host(machine)
    dargs = utils.args_to_dict(args)
    dargs['extra_args'] = '{extra_args}'.split()
    job.run_test('telemetry_Benchmarks', host=host,
                 benchmark='{test}',
                 tag='{test}',
                 args=dargs)

parallel_simple(run_benchmark, machines)""")


def _get_suite(test):
    if test in PERF_PER_BUILD_TESTS:
        return 'ATTRIBUTES = \'suite:crosbolt_perf_perbuild\''
    elif test in PERF_DAILY_RUN_TESTS:
        return 'ATTRIBUTES = \'suite:crosbolt_perf_nightly\''
    elif test in PERF_WEEKLY_RUN_TESTS:
        return 'ATTRIBUTES = \'suite:crosbolt_perf_weekly\''
    return ''


def get_existing_fields(filename):
    """Returns the existing copyright year and author of the control file."""
    if not os.path.isfile(filename):
        return (DEFAULT_YEAR, DEFAULT_AUTHOR)

    copyright_year = DEFAULT_YEAR
    author = DEFAULT_AUTHOR
    copyright_pattern = re.compile(
            '# Copyright (\d+) The Chromium OS Authors.')
    author_pattern = re.compile("AUTHOR = '(.+)'")
    with open(filename) as f:
        for line in f:
            match_year = copyright_pattern.match(line)
            if match_year:
                copyright_year = match_year.group(1)
            match_author = author_pattern.match(line)
            if match_author:
                author = match_author.group(1)
    return (copyright_year, author)


def generate_control(test):
    """Generates control file from the template."""
    filename = 'control.%s' % test
    copyright_year, author = get_existing_fields(filename)
    extra_args = EXTRA_ARGS_MAP.get(test, '')

    with open(filename, 'w+') as f:
        content = CONTROLFILE_TEMPLATE.format(
                attributes=_get_suite(test),
                author=author,
                extra_args=extra_args,
                test=test,
                year=copyright_year)
        f.write(content)


def check_unmanaged_control_files():
    """Prints warning if there is unmanaged control file."""
    for filename in os.listdir('.'):
        if not filename.startswith('control.'):
            continue
        test = filename[len('control.'):]
        if test not in ALL_TESTS:
            print 'warning, unmanaged control file:', test


def main():
    """The main function."""
    for test in ALL_TESTS:
        generate_control(test)
    check_unmanaged_control_files()


if __name__ == "__main__":
    main()
