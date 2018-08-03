# Copyright 2018 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Module for CrOS dynamic test suite generation and execution."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import contextlib
import itertools
import json
import logging
import os
import time

from lucifer import autotest
from skylab_suite import cros_suite
from skylab_suite import swarming_lib


SKYLAB_SUITE_USER = 'skylab_suite_runner'
SKYLAB_LUCI_TAG = 'luci_project:chromiumos'
SKYLAB_DRONE_SWARMING_WORKER = '/opt/infra-tools/usr/bin/skylab_swarming_worker'

SUITE_WAIT_SLEEP_INTERVAL_SECONDS = 30


def run(test_specs, suite_handler, dry_run=False):
    """Run a CrOS dynamic test suite.

    @param test_specs: A list of cros_suite.TestSpec objects.
    @param suite_handler: A cros_suite.SuiteHandler object.
    @param dry_run: Whether to kick off dry runs of the tests.
    """
    if suite_handler.suite_id:
        # Resume an existing suite.
        _resume_suite(test_specs, suite_handler, dry_run)
    else:
        # Make a new suite.
        _run_suite(test_specs, suite_handler, dry_run)


def _resume_suite(test_specs, suite_handler, dry_run=False):
    """Resume a suite and its child tasks by given suite id."""
    suite_id = suite_handler.suite_id
    all_tasks = _fetch_child_tasks(suite_id)
    not_yet_scheduled = _get_unscheduled_test_specs(
            test_specs, suite_handler, all_tasks)

    logging.info('Not yet scheduled test_specs: %r', not_yet_scheduled)
    _schedule_test_specs(not_yet_scheduled, suite_handler, suite_id, dry_run)

    if suite_id is not None and suite_handler.should_wait():
        _wait_for_results(suite_handler, dry_run=dry_run)


def _get_unscheduled_test_specs(test_specs, suite_handler, all_tasks):
    not_yet_scheduled = []
    for test_spec in test_specs:
        if suite_handler.is_provision():
            # We cannot check bot_id because pending tasks do not have it yet.
            bot_id_tag = 'id:%s' % test_spec.bot_id
            tasks = [t for t in all_tasks if bot_id_tag in t['tags']]
        else:
            tasks = [t for t in all_tasks if t['name']==test_spec.test.name]

        if not tasks:
            not_yet_scheduled.append(test_spec)
            continue

        current_task = _get_current_task(tasks)
        test_task_id = (current_task['task_id'] if current_task
                        else tasks[0]['task_id'])
        remaining_retries = test_spec.test.job_retries - len(tasks)
        previous_retried_ids = [t['task_id'] for t in tasks
                                if t['task_id'] != test_task_id]
        suite_handler.add_test_by_task_id(
                test_task_id,
                cros_suite.TestHandlerSpec(
                        test_spec=test_spec,
                        remaining_retries=remaining_retries,
                        previous_retried_ids=previous_retried_ids))

    return not_yet_scheduled


def _get_current_task(tasks):
    """Get current running task.

    @param tasks: A list of task dicts including task_id, state, etc.

    @return a dict representing the current running task.
    """
    current_task = None
    for t in tasks:
        if t['state'] not in swarming_lib.TASK_FINISHED_STATUS:
            if current_task:
                raise ValueError(
                        'Parent task has 2 same running child tasks: %s, %s'
                        % (current_task['task_id'], t['task_id']))

            current_task = t

    return current_task


def _run_suite(test_specs, suite_handler, dry_run=False):
    """Make a new suite."""
    suite_id = os.environ.get('SWARMING_TASK_ID')
    _schedule_test_specs(test_specs, suite_handler, suite_id, dry_run)

    if suite_id is not None and suite_handler.should_wait():
        suite_handler.set_suite_id(suite_id)
        _wait_for_results(suite_handler, dry_run=dry_run)


def _schedule_test_specs(test_specs, suite_handler, suite_id, dry_run=False):
    """Schedule a list of tests (TestSpecs).

    Given a list of TestSpec object, this function will schedule them on
    swarming one by one, and add them to the swarming_task_id-to-test map
    of suite_handler to keep monitoring them.

    @param test_specs: A list of cros_suite.TestSpec objects to schedule.
    @param suite_handler: A cros_suite.SuiteHandler object to monitor the
        test_specs' progress.
    @param suite_id: A string ID for a suite task, it's the parent task id for
        these to-be-scheduled test_specs.
    @param dry_run: Whether to kick off dry runs of the tests.
    """
    for test_spec in test_specs:
        test_task_id = _schedule_test(
                test_spec,
                suite_handler.is_provision(),
                suite_id=suite_id,
                dry_run=dry_run)
        suite_handler.add_test_by_task_id(
                test_task_id,
                cros_suite.TestHandlerSpec(
                        test_spec=test_spec,
                        remaining_retries=test_spec.test.job_retries - 1,
                        previous_retried_ids=[]))


def _make_provision_swarming_cmd():
    basic_swarming_cmd = swarming_lib.get_basic_swarming_cmd('post')
    return basic_swarming_cmd + ['tasks/new']


def _make_trigger_swarming_cmd(cmd, dimensions, test_spec,
                               temp_json_path, suite_id):
    """Form the swarming cmd.

    @param cmd: The raw command to run in lab.
    @param dimensions: A dict of dimensions used to form the swarming cmd.
    @param test_spec: a cros_suite.TestSpec object.
    @param temp_json_path: The json file to dump the swarming output.
    @param suite_id: The suite id of the test to kick off.

    @return a string swarming command to kick off.
    """
    basic_swarming_cmd = swarming_lib.get_basic_swarming_cmd('trigger')
    swarming_cmd = basic_swarming_cmd + [
            '--task-name', test_spec.test.name,
            '--priority', str(test_spec.priority),
            '--dump-json', temp_json_path,
            '--hard-timeout', str(test_spec.execution_timeout_secs),
            '--io-timeout', str(test_spec.io_timeout_secs),
            '--raw-cmd']

    swarming_cmd += ['--tags=%s' % SKYLAB_LUCI_TAG]
    for k, v in dimensions.iteritems():
        swarming_cmd += ['--dimension', k, v]

    if suite_id is not None:
        swarming_cmd += ['--tags=%s:%s' % ('parent_task_id', suite_id)]

    swarming_cmd += ['--raw-cmd', '--']
    swarming_cmd += cmd
    return swarming_cmd


def _get_suite_cmd(test_spec, suite_id, is_provision=False):
    """Get the command for running a suite.

    @param test_spec: a cros_suite.TestSpec object.
    @param suite_id: a string of parent suite's swarming task id.
    @param is_provision: whether the command is for provision.
    """
    constants = autotest.load('server.cros.dynamic_suite.constants')
    job_keyvals = test_spec.keyvals.copy()
    job_keyvals[constants.JOB_EXPERIMENTAL_KEY] = test_spec.test.experimental
    if suite_id is not None:
        job_keyvals[constants.PARENT_JOB_ID] = suite_id

    cmd = [SKYLAB_DRONE_SWARMING_WORKER]
    if test_spec.test.test_type == 'client':
      cmd += ['-client-test']

    cmd += ['-keyvals', _convert_dict_to_string(job_keyvals)]
    cmd += ['-task-name', test_spec.test.name]
    if is_provision:
        cmd += ['-provision-labels', 'cros-version:%s' % test_spec.build]

    return cmd


def _run_provision_cmd(cmd, dimensions, test_spec, suite_id):
    """Kick off a provision swarming cmd.

    @param cmd: The raw command to run in lab.
    @param dimensions: A dict of dimensions used to form the swarming cmd.
    @param test_spec: a cros_suite.TestSpec object.
    @param suite_id: The suite id of the test to kick off.
    """
    fallback_dimensions = dimensions.copy()
    if test_spec.bot_id:
        fallback_dimensions['id'] = test_spec.bot_id

    normal_dimensions = fallback_dimensions.copy()
    normal_dimensions['provisionable-cros-version'] = test_spec.build
    all_dimensions = [normal_dimensions, fallback_dimensions]
    tags = [SKYLAB_LUCI_TAG, 'build:%s' % test_spec.build]
    if suite_id is not None:
        tags += ['parent_task_id:%s' % suite_id]

    json_request = swarming_lib.make_fallback_request_dict(
            cmds=[cmd] * len(all_dimensions),
            slices_dimensions=all_dimensions,
            task_name=test_spec.test.name,
            priority=test_spec.priority,
            tags=tags,
            user=SKYLAB_SUITE_USER,
            parent_task_id=suite_id,
            expiration_secs=test_spec.expiration_secs,
            grace_period_secs=test_spec.grace_period_secs,
            execution_timeout_secs=test_spec.execution_timeout_secs,
            io_timeout_secs=test_spec.io_timeout_secs)

    cros_build_lib = autotest.chromite_load('cros_build_lib')
    provision_cmd = _make_provision_swarming_cmd()
    result = cros_build_lib.RunCommand(provision_cmd,
                                       input=json.dumps(json_request),
                                       env=os.environ.copy(),
                                       capture_output=True)
    logging.info('Input: %r', json_request)
    return json.loads(result.output)['task_id']


def _run_swarming_cmd(cmd, dimensions, test_spec, temp_json_path, suite_id):
    """Kick off a swarming cmd.

    @param cmd: The raw command to run in lab.
    @param dimensions: A dict of dimensions used to form the swarming cmd.
    @param test_spec: a cros_suite.TestSpec object.
    @param temp_json_path: The json file to dump the swarming output.
    @param suite_id: The suite id of the test to kick off.

    @return the swarming task id of this task.
    """
    # TODO (xixuan): Add this to provision cmd when cron job for special task
    # is working.
    dimensions['dut_state'] = swarming_lib.SWARMING_DUT_READY_STATUS
    dimensions['provisionable-cros-version'] = test_spec.build
    trigger_cmd = _make_trigger_swarming_cmd(cmd, dimensions, test_spec,
                                             temp_json_path, suite_id)
    cros_build_lib = autotest.chromite_load('cros_build_lib')
    new_env = os.environ.copy()
    # Set SWARMING_TASK_ID so swarming command knows the suite task id:
    # https://chromium.googlesource.com/infra/luci/luci-py/+/
    # 78083f5977c302721b17ad689b1465871c0c587b/client/swarming.py#1158
    new_env['SWARMING_TASK_ID'] = suite_id
    cros_build_lib.RunCommand(trigger_cmd, env=new_env)
    with open(temp_json_path) as f:
        result = json.load(f)
        return result['tasks'][test_spec.test.name]['task_id']


def _schedule_test(test_spec, is_provision, suite_id=None,
                   dry_run=False):
    """Schedule a CrOS test.

    @param test_spec: A cros_suite.TestSpec object.
    @param is_provision: A boolean, whether to kick off a provision test.
    @param suite_id: the suite task id of the test.
    @param dry_run: Whether to kick off a dry run of a swarming cmd.

    @return the swarming task id of this task.
    """
    logging.info('Scheduling test %s', test_spec.test.name)
    cmd = _get_suite_cmd(test_spec, suite_id, is_provision=is_provision)
    if dry_run:
        cmd = ['/bin/echo'] + cmd
        test_spec.test.name = 'Echo ' + test_spec.test.name

    dimensions = {'pool': swarming_lib.SKYLAB_DRONE_POOL,
                  'label-pool': swarming_lib.SWARMING_DUT_POOL_MAP.get(
                          test_spec.pool),
                  'label-board': test_spec.board}

    osutils = autotest.chromite_load('osutils')
    with osutils.TempDir() as tempdir:
        temp_json_path = os.path.join(tempdir, 'temp_summary.json')
        if is_provision:
            return _run_provision_cmd(cmd, dimensions, test_spec,
                                      suite_id)
        else:
            return _run_swarming_cmd(cmd, dimensions, test_spec,
                                     temp_json_path, suite_id)


def _fetch_child_tasks(parent_task_id):
    """Get the child tasks based on a parent swarming task id.

    @param parent_task_id: The parent swarming task id.

    @return a list of dicts, each dict refers to the whole stats of a task,
        keys include 'name', 'bot_dimensions', 'tags', 'bot_id', 'state', etc.
    """
    swarming_cmd = swarming_lib.get_basic_swarming_cmd('query')
    swarming_cmd += ['tasks/list?tags=parent_task_id:%s' % parent_task_id]
    timeout_util = autotest.chromite_load('timeout_util')
    cros_build_lib = autotest.chromite_load('cros_build_lib')
    with timeout_util.Timeout(60):
        child_tasks = cros_build_lib.RunCommand(
                swarming_cmd, capture_output=True)
        return json.loads(child_tasks.output)['items']


@contextlib.contextmanager
def disable_logging(logging_level):
    """Context manager for disabling logging of a given logging level."""
    try:
        logging.disable(logging_level)
        yield
    finally:
        logging.disable(logging.NOTSET)


def _loop_and_wait_forever(suite_handler, dry_run):
    """Wait for child tasks to finish or break."""
    for iterations in itertools.count(0):
        # Log progress every 300 seconds.
        no_logging = bool(iterations * SUITE_WAIT_SLEEP_INTERVAL_SECONDS % 300)
        with disable_logging(logging.INFO if no_logging else logging.NOTSET):
            all_tasks = _fetch_child_tasks(suite_handler.suite_id)
            suite_handler.handle_results(all_tasks)
            for t in suite_handler.retried_tasks:
                _retry_test(suite_handler, t['task_id'], dry_run=dry_run)

            if suite_handler.is_finished_waiting():
                break

        time.sleep(SUITE_WAIT_SLEEP_INTERVAL_SECONDS)


def _wait_for_results(suite_handler, dry_run=False):
    """Wait for child tasks to finish and return their results.

    @param suite_handler: a cros_suite.SuiteHandler object.
    """
    timeout_util = autotest.chromite_load('timeout_util')
    try:
        with timeout_util.Timeout(suite_handler.timeout_mins * 60):
            _loop_and_wait_forever(suite_handler, dry_run)
    except timeout_util.TimeoutError:
        logging.error('Timeout in waiting for child tasks.')
        return

    logging.info('Finished to wait for child tasks.')


def _retry_test(suite_handler, task_id, dry_run=False):
    """Retry test for a suite.

    We will execute the following actions for retrying a test:
        1. Schedule the test.
        2. Add the test with the new swarming task id to the suite's
           retry handler, but reduce its remaining retries by 1.
        3. Reduce the suite-level max retries by 1.
        4. Remove prevous failed test from retry handler since it's not
           actively monitored by the suite.

    @param suite_handler: a cros_suite.SuiteHandler object.
    @param task_id: The swarming task id for the retried test.
    @param dry_run: Whether to retry a dry run of the test.
    """
    last_retry_spec = suite_handler.get_test_by_task_id(task_id)
    logging.info('Retrying test %s, remaining %d retries.',
                 last_retry_spec.test_spec.test.name,
                 last_retry_spec.remaining_retries - 1)
    retried_task_id = _schedule_test(
            last_retry_spec.test_spec,
            suite_handler.is_provision(),
            suite_id=suite_handler.suite_id,
            dry_run=dry_run)
    previous_retried_ids = last_retry_spec.previous_retried_ids + [task_id]
    suite_handler.add_test_by_task_id(
            retried_task_id,
            cros_suite.TestHandlerSpec(
                    test_spec=last_retry_spec.test_spec,
                    remaining_retries=last_retry_spec.remaining_retries - 1,
                    previous_retried_ids=previous_retried_ids))
    suite_handler.set_max_retries(suite_handler.max_retries - 1)
    suite_handler.remove_test_by_task_id(task_id)


def _convert_dict_to_string(input_dict):
    """Convert dictionary to a string.

    @param input_dict: A dictionary.
    """
    for k, v in input_dict.iteritems():
        if isinstance(v, dict):
            input_dict[k] = _convert_dict_to_string(v)
        else:
            input_dict[k] = str(v)

    return json.dumps(input_dict)
