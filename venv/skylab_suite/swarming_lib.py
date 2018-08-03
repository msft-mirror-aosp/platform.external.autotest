# Copyright 2018 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Module for swarming execution."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import collections
import json
import logging
import operator
import os
import urllib

from lucifer import autotest


SERVICE_ACCOUNT = '/creds/skylab_swarming_bot/skylab_bot_service_account.json'
SKYLAB_DRONE_POOL = 'ChromeOSSkylab'
SKYLAB_SUITE_POOL = 'ChromeOSSkylab-suite'

TASK_COMPLETED = 'COMPLETED'
TASK_COMPLETED_SUCCESS = 'COMPLETED (SUCCESS)'
TASK_COMPLETED_FAILURE = 'COMPLETED (FAILURE)'
TASK_EXPIRED = 'EXPIRED'
TASK_CANCELED = 'CANCELED'
TASK_TIMEDOUT = 'TIMED_OUT'
TASK_RUNNING = 'RUNNING'
TASK_PENDING = 'PENDING'
TASK_BOT_DIED = 'BOT_DIED'
TASK_NO_RESOURCE = 'NO_RESOURCE'
TASK_FINISHED_STATUS = [TASK_COMPLETED,
                        TASK_EXPIRED,
                        TASK_CANCELED,
                        TASK_TIMEDOUT,
                        TASK_BOT_DIED,
                        TASK_NO_RESOURCE]
# The swarming task failure status to retry. TASK_CANCELED won't get
# retried since it's intentionally aborted.
TASK_STATUS_TO_RETRY = [TASK_EXPIRED, TASK_TIMEDOUT, TASK_BOT_DIED,
                        TASK_NO_RESOURCE]

DEFAULT_EXPIRATION_SECS = 10 * 60
DEFAULT_TIMEOUT_SECS = 60 * 60

# A mapping of priorities for skylab hwtest tasks. In swarming,
# lower number means high priorities. Priority lower than 48 will
# be special tasks. The upper bound for priority is 255.
# Use the same priorities mapping as chromite/lib/constants.py
SKYLAB_HWTEST_PRIORITIES_MAP = {
    'Weekly': 230,
    'Daily': 200,
    'PostBuild': 170,
    'Default': 140,
    'Build': 110,
    'PFQ': 80,
    'CQ': 50,
    'Super': 49,
}
SORTED_SKYLAB_HWTEST_PRIORITY = sorted(
        SKYLAB_HWTEST_PRIORITIES_MAP.items(),
        key=operator.itemgetter(1))

# TODO (xixuan): Use proto library or some future APIs instead of hardcoding.
SWARMING_DUT_POOL_MAP = {
        'cq': 'DUT_POOL_CQ',
        'bvt': 'DUT_POOL_BVT',
        'suites': 'DUT_POOL_SUITES',
        'cts': 'DUT_POOL_CTS',
        'arc-presubmit': 'DUT_POOL_CTS_PERBUILD',
}
SWARMING_DUT_READY_STATUS = 'ready'

# The structure of fallback swarming task request is:
# NewTaskRequest:
#     ...
#     task_slices  ->  NewTaskSlice:
#                          ...
#                          properties  ->  TaskProperties
#                                              ...
TaskProperties = collections.namedtuple(
        'TaskProperties',
        [
                'command',
                'dimensions',
                'execution_timeout_secs',
                'grace_period_secs',
                'io_timeout_secs',
        ])

NewTaskSlice = collections.namedtuple(
        'NewTaskSlice',
        [
                'expiration_secs',
                'properties',
        ])

NewTaskRequest = collections.namedtuple(
        'NewTaskRequest',
        [
                'name',
                'parent_task_id',
                'priority',
                'tags',
                'user',
                'task_slices',
        ])


def _get_client():
    return os.path.join(
            os.path.expanduser('~'),
            'chromiumos/chromite/third_party/swarming.client/swarming.py')


def get_basic_swarming_cmd(command):
    return [_get_client(), command,
            '--auth-service-account-json', SERVICE_ACCOUNT,
            '--swarming', os.environ.get('SWARMING_SERVER')]


def make_fallback_request_dict(cmds, slices_dimensions, task_name, priority,
                               tags, user,
                               parent_task_id='',
                               expiration_secs=DEFAULT_EXPIRATION_SECS,
                               grace_period_secs=DEFAULT_TIMEOUT_SECS,
                               execution_timeout_secs=DEFAULT_TIMEOUT_SECS,
                               io_timeout_secs=DEFAULT_TIMEOUT_SECS):
    """Form a json-compatible dict for fallback swarming call.

    @param cmds: A list of cmd to run on swarming bots.
    @param slices_dimensions: A list of dict to indicates different tries'
        dimensions.
    @param task_name: The request's name.
    @param priority: The request's priority. An integer.
    @param expiration_secs: The expiration seconds for the each cmd to wait
        to be expired.
    @param grace_period_secs: The seconds to send a task after a SIGTERM before
        sending it a SIGKILL.
    @param execution_timeout_secs: The seconds to run before a task gets
        terminated.
    @param io_timeout_secs: The seconds to wait before a task is considered
        hung.

    @return a json-compatible dict, as a request for swarming call.
    """
    assert len(cmds) == len(slices_dimensions)
    task_slices = []
    for cmd, dimensions in zip(cmds, slices_dimensions):
        properties = TaskProperties(
                command=cmd,
                dimensions=dimensions,
                execution_timeout_secs=execution_timeout_secs,
                grace_period_secs=grace_period_secs,
                io_timeout_secs=io_timeout_secs)
        task_slices.append(
                NewTaskSlice(
                        expiration_secs=expiration_secs,
                        properties=properties))

    task_request = NewTaskRequest(
        name=task_name,
        parent_task_id=parent_task_id,
        priority=priority,
        tags=tags,
        user=user,
        task_slices=task_slices)

    return _to_raw_request(task_request)


def _namedtuple_to_dict(value):
    """Recursively converts a namedtuple to a dict.

    Args:
      value: a namedtuple object.

    Returns:
      A dict object with the same value.
    """
    out = dict(value._asdict())
    for k, v in out.iteritems():
      if hasattr(v, '_asdict'):
        out[k] = _namedtuple_to_dict(v)
      elif isinstance(v, (list, tuple)):
        l = []
        for elem in v:
          if hasattr(elem, '_asdict'):
            l.append(_namedtuple_to_dict(elem))
          else:
            l.append(elem)
        out[k] = l

    return out


def _to_raw_request(request):
    """Returns the json-compatible dict expected by the server.

    Args:
      request: a NewTaskRequest object.

    Returns:
      A json-compatible dict, which could be parsed by swarming proxy
      service.
    """
    out = _namedtuple_to_dict(request)
    for task_slice in out['task_slices']:
        task_slice['properties']['dimensions'] = [
                {'key': k, 'value': v}
                for k, v in task_slice['properties']['dimensions'].iteritems()
        ]
        task_slice['properties']['dimensions'].sort(key=lambda x: x['key'])
    return out


def get_task_link(task_id):
    return '%s/user/task/%s' % (os.environ.get('SWARMING_SERVER'), task_id)


def get_task_final_state(task):
    """Get the final state of a swarming task.

    @param task: the json output of a swarming task fetched by API tasks.list.
    """
    state = task['state']
    if state == TASK_COMPLETED:
        state = (TASK_COMPLETED_FAILURE if task['failure'] else
                 TASK_COMPLETED_SUCCESS)

    return state


def get_task_dut_name(task_dimensions):
    """Get the DUT name of running this task.

    @param task_dimensions: a list of dict, e.g. [{'key': k, 'value': v}, ...]
    """
    for dimension in task_dimensions:
        if dimension['key'] == 'dut_name':
            return dimension['value'][0]

    return ''


def query_bots_count(dimensions):
    """Get bots count for given requirements.

    @param dimensions: A dict of dimensions for swarming bots.

    @return a dict, which contains counts for different status of bots.
    """
    basic_swarming_cmd = get_basic_swarming_cmd('query')
    conditions = [('dimensions', '%s:%s' % (k, v))
                  for k, v in dimensions.iteritems()]
    swarming_cmd = basic_swarming_cmd + ['bots/count?%s' %
                                         urllib.urlencode(conditions)]
    cros_build_lib = autotest.chromite_load('cros_build_lib')
    result = cros_build_lib.RunCommand(swarming_cmd, capture_output=True)
    return json.loads(result.output)


def get_idle_bots_count(outputs):
    """Get the idle bots count.

    @param outputs: The outputs of |query_bots_count|.
    """
    return (int(outputs['count']) - int(outputs['busy']) - int(outputs['dead'])
            - int(outputs['quarantined']))


def query_task_by_tags(tags):
    """Get tasks for given tags.

    @param tags: A dict of tags for swarming tasks.

    @return a list, which contains all tasks queried by the given tags.
    """
    basic_swarming_cmd = get_basic_swarming_cmd('query')
    conditions = [('tags', '%s:%s' % (k, v)) for k, v in tags.iteritems()]
    swarming_cmd = basic_swarming_cmd + ['tasks/list?%s' %
                                         urllib.urlencode(conditions)]
    cros_build_lib = autotest.chromite_load('cros_build_lib')
    result = cros_build_lib.RunCommand(swarming_cmd, capture_output=True)
    json_output = json.loads(result.output)
    return json_output.get('items', [])


def query_task_by_id(task_id):
    """Get task for given id.

    @param task_id: A string to indicate a swarming task id.

    @return a dict, which contains the task with the given task_id.
    """
    basic_swarming_cmd = get_basic_swarming_cmd('query')
    swarming_cmd = basic_swarming_cmd + ['task/%s/result' % task_id]
    cros_build_lib = autotest.chromite_load('cros_build_lib')
    result = cros_build_lib.RunCommand(swarming_cmd, capture_output=True)
    return json.loads(result.output)


def abort_task(task_id):
    """Abort a swarming task by its id.

    @param task_id: A string swarming task id.
    """
    basic_swarming_cmd = get_basic_swarming_cmd('cancel')
    swarming_cmd = basic_swarming_cmd + ['--kill-running', task_id]
    cros_build_lib = autotest.chromite_load('cros_build_lib')
    try:
        cros_build_lib.RunCommand(swarming_cmd, log_output=True)
    except cros_build_lib.RunCommandError:
        logging.error('Task %s probably already gone, skip canceling it.',
                      task_id)


def query_bots_list(dimensions):
    """Get bots list for given requirements.

    @param dimensions: A dict of dimensions for swarming bots.

    @return a list of bot dicts.
    """
    basic_swarming_cmd = get_basic_swarming_cmd('query')
    conditions = [('dimensions', '%s:%s' % (k, v))
                  for k, v in dimensions.iteritems()]
    swarming_cmd = basic_swarming_cmd + ['bots/list?%s' %
                                         urllib.urlencode(conditions)]
    cros_build_lib = autotest.chromite_load('cros_build_lib')
    result = cros_build_lib.RunCommand(swarming_cmd, capture_output=True)
    return json.loads(result.output)['items']


def bot_available(bot):
    """Check whether a bot is available.

    @param bot: A dict describes a bot's dimensions, i.e. an element in return
        list of |query_bots_list|.

    @return True if a bot is available to run task, otherwise False.
    """
    return not (bot['is_dead'] or bot['quarantined'])
