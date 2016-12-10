# Copyright (c) 2012 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

__author__ = 'cmasone@chromium.org (Chris Masone)'

import common
import datetime
import logging
import os

from autotest_lib.frontend.afe import models
from autotest_lib.client.common_lib import control_data
from autotest_lib.client.common_lib import error
from autotest_lib.client.common_lib import global_config
from autotest_lib.client.common_lib import priorities
from autotest_lib.client.common_lib import time_utils
from autotest_lib.client.common_lib.cros import dev_server
# TODO(akeshet): Replace with monarch.
from autotest_lib.client.common_lib.cros.graphite import autotest_stats
from autotest_lib.frontend.afe import rpc_utils
from autotest_lib.server import utils
from autotest_lib.server.cros import provision
from autotest_lib.server.cros.dynamic_suite import constants
from autotest_lib.server.cros.dynamic_suite import control_file_getter
from autotest_lib.server.cros.dynamic_suite import tools
from autotest_lib.server.cros.dynamic_suite import suite as SuiteBase
from autotest_lib.server.cros.dynamic_suite.suite import Suite
from autotest_lib.site_utils import host_history
from autotest_lib.site_utils import job_history
from autotest_lib.site_utils import server_manager_utils
from autotest_lib.site_utils import stable_version_utils


_CONFIG = global_config.global_config

# Relevant CrosDynamicSuiteExceptions are defined in client/common_lib/error.py.


def canonicalize_suite_name(suite_name):
    """Canonicalize the suite's name.

    @param suite_name: the name of the suite.
    """
    # Do not change this naming convention without updating
    # site_utils.parse_job_name.
    return 'test_suites/control.%s' % suite_name


def formatted_now():
    """Format the current datetime."""
    return datetime.datetime.now().strftime(time_utils.TIME_FMT)


def _get_control_file_contents_by_name(build, ds, suite_name):
    """Return control file contents for |suite_name|.

    Query the dev server at |ds| for the control file |suite_name|, included
    in |build| for |board|.

    @param build: unique name by which to refer to the image from now on.
    @param ds: a dev_server.DevServer instance to fetch control file with.
    @param suite_name: canonicalized suite name, e.g. test_suites/control.bvt.
    @raises ControlFileNotFound if a unique suite control file doesn't exist.
    @raises NoControlFileList if we can't list the control files at all.
    @raises ControlFileEmpty if the control file exists on the server, but
                             can't be read.

    @return the contents of the desired control file.
    """
    getter = control_file_getter.DevServerGetter.create(build, ds)
    devserver_name = ds.get_server_name(ds.url())
    timer = autotest_stats.Timer('control_files.parse.%s.%s' %
                                 (devserver_name.replace('.', '_'),
                                  suite_name.rsplit('.')[-1]))
    # Get the control file for the suite.
    try:
        with timer:
            control_file_in = getter.get_control_file_contents_by_name(
                    suite_name)
    except error.CrosDynamicSuiteException as e:
        raise type(e)('Failed to get control file for %s '
                      '(devserver: %s) (error: %s)' %
                      (build, devserver_name, e))
    if not control_file_in:
        raise error.ControlFileEmpty(
            "Fetching %s returned no data. (devserver: %s)" %
            (suite_name, devserver_name))
    # Force control files to only contain ascii characters.
    try:
        control_file_in.encode('ascii')
    except UnicodeDecodeError as e:
        raise error.ControlFileMalformed(str(e))

    return control_file_in


def _stage_build_artifacts(build, hostname=None):
    """
    Ensure components of |build| necessary for installing images are staged.

    @param build image we want to stage.
    @param hostname hostname of a dut may run test on. This is to help to locate
        a devserver closer to duts if needed. Default is None.

    @raises StageControlFileFailure: if the dev server throws 500 while staging
        suite control files.

    @return: dev_server.ImageServer instance to use with this build.
    @return: timings dictionary containing staging start/end times.
    """
    timings = {}
    # Ensure components of |build| necessary for installing images are staged
    # on the dev server. However set synchronous to False to allow other
    # components to be downloaded in the background.
    ds = dev_server.resolve(build, hostname=hostname)
    ds_name = ds.get_server_name(ds.url())
    timings[constants.DOWNLOAD_STARTED_TIME] = formatted_now()
    timer = autotest_stats.Timer('control_files.stage.%s' % (
            ds_name.replace('.', '_')))
    try:
        with timer:
            ds.stage_artifacts(image=build, artifacts=['test_suites'])
    except dev_server.DevServerException as e:
        raise error.StageControlFileFailure(
                "Failed to stage %s on %s: %s" % (build, ds_name, e))
    timings[constants.PAYLOAD_FINISHED_TIME] = formatted_now()
    return (ds, timings)


@rpc_utils.route_rpc_to_master
def create_suite_job(
        name='',
        board='',
        pool='',
        control_file='',
        check_hosts=True,
        num=None,
        file_bugs=False,
        timeout=24,
        timeout_mins=None,
        priority=priorities.Priority.DEFAULT,
        suite_args=None,
        wait_for_results=True,
        job_retry=False,
        max_retries=None,
        max_runtime_mins=None,
        suite_min_duts=0,
        offload_failures_only=False,
        builds=None,
        test_source_build=None,
        run_prod_code=False,
        delay_minutes=0,
        is_cloning=False,
        **kwargs
):
    """
    Create a job to run a test suite on the given device with the given image.

    When the timeout specified in the control file is reached, the
    job is guaranteed to have completed and results will be available.

    @param name: The test name if control_file is supplied, otherwise the name
                 of the test suite to run, e.g. 'bvt'.
    @param board: the kind of device to run the tests on.
    @param builds: the builds to install e.g.
                   {'cros-version:': 'x86-alex-release/R18-1655.0.0',
                    'fwrw-version:':  'x86-alex-firmware/R36-5771.50.0',
                    'fwro-version:':  'x86-alex-firmware/R36-5771.49.0'}
                   If builds is given a value, it overrides argument build.
    @param test_source_build: Build that contains the server-side test code.
    @param pool: Specify the pool of machines to use for scheduling
            purposes.
    @param control_file: the control file of the job.
    @param check_hosts: require appropriate live hosts to exist in the lab.
    @param num: Specify the number of machines to schedule across (integer).
                Leave unspecified or use None to use default sharding factor.
    @param file_bugs: File a bug on each test failure in this suite.
    @param timeout: The max lifetime of this suite, in hours.
    @param timeout_mins: The max lifetime of this suite, in minutes. Takes
                         priority over timeout.
    @param priority: Integer denoting priority. Higher is more important.
    @param suite_args: Optional arguments which will be parsed by the suite
                       control file. Used by control.test_that_wrapper to
                       determine which tests to run.
    @param wait_for_results: Set to False to run the suite job without waiting
                             for test jobs to finish. Default is True.
    @param job_retry: Set to True to enable job-level retry. Default is False.
    @param max_retries: Integer, maximum job retries allowed at suite level.
                        None for no max.
    @param max_runtime_mins: Maximum amount of time a job can be running in
                             minutes.
    @param suite_min_duts: Integer. Scheduler will prioritize getting the
                           minimum number of machines for the suite when it is
                           competing with another suite that has a higher
                           priority but already got minimum machines it needs.
    @param offload_failures_only: Only enable gs_offloading for failed jobs.
    @param run_prod_code: If True, the suite will run the test code that
                          lives in prod aka the test code currently on the
                          lab servers. If False, the control files and test
                          code for this suite run will be retrieved from the
                          build artifacts.
    @param delay_minutes: Delay the creation of test jobs for a given number of
                          minutes.
    @param is_cloning: True if creating a cloning job.
    @param kwargs: extra keyword args. NOT USED.

    @raises ControlFileNotFound: if a unique suite control file doesn't exist.
    @raises NoControlFileList: if we can't list the control files at all.
    @raises StageControlFileFailure: If the dev server throws 500 while
                                     staging test_suites.
    @raises ControlFileEmpty: if the control file exists on the server, but
                              can't be read.

    @return: the job ID of the suite; -1 on error.
    """
    if type(num) is not int and num is not None:
        raise error.SuiteArgumentException('Ill specified num argument %r. '
                                           'Must be an integer or None.' % num)
    if num == 0:
        logging.warning("Can't run on 0 hosts; using default.")
        num = None

    if builds is None:
        builds = {}

    # Default test source build to CrOS build if it's not specified and
    # run_prod_code is set to False.
    if not run_prod_code:
        test_source_build = Suite.get_test_source_build(
                builds, test_source_build=test_source_build)

    # If 'prefer_local_devserver' is True in global setting, and both board
    # and pool are specified, pick a dut in the given board and pool, and
    # use that to help to pick a devserver in the same subnet of the duts
    # to be used to run tests.
    if dev_server.PREFER_LOCAL_DEVSERVER and pool and board:
        sample_dut = rpc_utils.get_sample_dut(board, pool)
    else:
        sample_dut = None

    suite_name = canonicalize_suite_name(name)
    if run_prod_code:
        ds = dev_server.resolve(test_source_build, hostname=sample_dut)
        keyvals = {}
        getter = control_file_getter.FileSystemGetter(
                [_CONFIG.get_config_value('SCHEDULER',
                                          'drone_installation_directory')])
        control_file = getter.get_control_file_contents_by_name(suite_name)
    else:
        (ds, keyvals) = _stage_build_artifacts(
                test_source_build, hostname=sample_dut)
    keyvals[constants.SUITE_MIN_DUTS_KEY] = suite_min_duts

    if not control_file:
        # No control file was supplied so look it up from the build artifacts.
        suite_name = canonicalize_suite_name(name)
        control_file = _get_control_file_contents_by_name(test_source_build,
                                                          ds, suite_name)
    # Do not change this naming convention without updating
    # site_utils.parse_job_name.
    if run_prod_code:
        # If run_prod_code is True, test_source_build is not set, use the
        # first build in the builds list for the sutie job name.
        name = '%s-%s' % (builds.values()[0], suite_name)
    else:
        name = '%s-%s' % (test_source_build, suite_name)

    timeout_mins = timeout_mins or timeout * 60
    max_runtime_mins = max_runtime_mins or timeout * 60

    if not board:
        board = utils.ParseBuildName(builds[provision.CROS_VERSION_PREFIX])[0]

    # Prepend builds and board to the control file.
    if is_cloning:
        control_file = tools.remove_injection(control_file)

    inject_dict = {
        'board': board,
        # `build` is needed for suites like AU to stage image inside suite
        # control file.
        'build': test_source_build,
        'builds': builds,
        'check_hosts': check_hosts,
        'pool': pool,
        'num': num,
        'file_bugs': file_bugs,
        'timeout': timeout,
        'timeout_mins': timeout_mins,
        'devserver_url': ds.url(),
        'priority': priority,
        'suite_args' : suite_args,
        'wait_for_results': wait_for_results,
        'job_retry': job_retry,
        'max_retries': max_retries,
        'max_runtime_mins': max_runtime_mins,
        'offload_failures_only': offload_failures_only,
        'test_source_build': test_source_build,
        'run_prod_code': run_prod_code,
        'delay_minutes': delay_minutes,
    }
    control_file = tools.inject_vars(inject_dict, control_file)

    return rpc_utils.create_job_common(name,
                                       priority=priority,
                                       timeout_mins=timeout_mins,
                                       max_runtime_mins=max_runtime_mins,
                                       control_type='Server',
                                       control_file=control_file,
                                       hostless=True,
                                       keyvals=keyvals)


def get_job_history(**filter_data):
    """Get history of the job, including the special tasks executed for the job

    @param filter_data: filter for the call, should at least include
                        {'job_id': [job id]}
    @returns: JSON string of the job's history, including the information such
              as the hosts run the job and the special tasks executed before
              and after the job.
    """
    job_id = filter_data['job_id']
    job_info = job_history.get_job_info(job_id)
    return rpc_utils.prepare_for_serialization(job_info.get_history())


def get_host_history(start_time, end_time, hosts=None, board=None, pool=None):
    """Get history of a list of host.

    The return is a JSON string of host history for each host, for example,
    {'172.22.33.51': [{'status': 'Resetting'
                       'start_time': '2014-08-07 10:02:16',
                       'end_time': '2014-08-07 10:03:16',
                       'log_url': 'http://autotest/reset-546546/debug',
                       'dbg_str': 'Task: Special Task 19441991 (host ...)'},
                       {'status': 'Running'
                       'start_time': '2014-08-07 10:03:18',
                       'end_time': '2014-08-07 10:13:00',
                       'log_url': 'http://autotest/reset-546546/debug',
                       'dbg_str': 'HQE: 15305005, for job: 14995562'}
                     ]
    }
    @param start_time: start time to search for history, can be string value or
                       epoch time.
    @param end_time: end time to search for history, can be string value or
                     epoch time.
    @param hosts: A list of hosts to search for history. Default is None.
    @param board: board type of hosts. Default is None.
    @param pool: pool type of hosts. Default is None.
    @returns: JSON string of the host history.
    """
    return rpc_utils.prepare_for_serialization(
            host_history.get_history_details(
                    start_time=start_time, end_time=end_time,
                    hosts=hosts, board=board, pool=pool,
                    process_pool_size=4))


def shard_heartbeat(shard_hostname, jobs=(), hqes=(), known_job_ids=(),
                    known_host_ids=(), known_host_statuses=()):
    """Receive updates for job statuses from shards and assign hosts and jobs.

    @param shard_hostname: Hostname of the calling shard
    @param jobs: Jobs in serialized form that should be updated with newer
                 status from a shard.
    @param hqes: Hostqueueentries in serialized form that should be updated with
                 newer status from a shard. Note that for every hostqueueentry
                 the corresponding job must be in jobs.
    @param known_job_ids: List of ids of jobs the shard already has.
    @param known_host_ids: List of ids of hosts the shard already has.
    @param known_host_statuses: List of statuses of hosts the shard already has.

    @returns: Serialized representations of hosts, jobs, suite job keyvals
              and their dependencies to be inserted into a shard's database.
    """
    # The following alternatives to sending host and job ids in every heartbeat
    # have been considered:
    # 1. Sending the highest known job and host ids. This would work for jobs:
    #    Newer jobs always have larger ids. Also, if a job is not assigned to a
    #    particular shard during a heartbeat, it never will be assigned to this
    #    shard later.
    #    This is not true for hosts though: A host that is leased won't be sent
    #    to the shard now, but might be sent in a future heartbeat. This means
    #    sometimes hosts should be transfered that have a lower id than the
    #    maximum host id the shard knows.
    # 2. Send the number of jobs/hosts the shard knows to the master in each
    #    heartbeat. Compare these to the number of records that already have
    #    the shard_id set to this shard. In the normal case, they should match.
    #    In case they don't, resend all entities of that type.
    #    This would work well for hosts, because there aren't that many.
    #    Resending all jobs is quite a big overhead though.
    #    Also, this approach might run into edge cases when entities are
    #    ever deleted.
    # 3. Mixtures of the above: Use 1 for jobs and 2 for hosts.
    #    Using two different approaches isn't consistent and might cause
    #    confusion. Also the issues with the case of deletions might still
    #    occur.
    #
    # The overhead of sending all job and host ids in every heartbeat is low:
    # At peaks one board has about 1200 created but unfinished jobs.
    # See the numbers here: http://goo.gl/gQCGWH
    # Assuming that job id's have 6 digits and that json serialization takes a
    # comma and a space as overhead, the traffic per id sent is about 8 bytes.
    # If 5000 ids need to be sent, this means 40 kilobytes of traffic.
    # A NOT IN query with 5000 ids took about 30ms in tests made.
    # These numbers seem low enough to outweigh the disadvantages of the
    # solutions described above.
    timer = autotest_stats.Timer('shard_heartbeat')
    with timer:
        shard_obj = rpc_utils.retrieve_shard(shard_hostname=shard_hostname)
        rpc_utils.persist_records_sent_from_shard(shard_obj, jobs, hqes)
        assert len(known_host_ids) == len(known_host_statuses)
        for i in range(len(known_host_ids)):
            host_model = models.Host.objects.get(pk=known_host_ids[i])
            if host_model.status != known_host_statuses[i]:
                host_model.status = known_host_statuses[i]
                host_model.save()

        hosts, jobs, suite_keyvals = rpc_utils.find_records_for_shard(
                shard_obj, known_job_ids=known_job_ids,
                known_host_ids=known_host_ids)
        return {
            'hosts': [host.serialize() for host in hosts],
            'jobs': [job.serialize() for job in jobs],
            'suite_keyvals': [kv.serialize() for kv in suite_keyvals],
        }


def get_shards(**filter_data):
    """Return a list of all shards.

    @returns A sequence of nested dictionaries of shard information.
    """
    shards = models.Shard.query_objects(filter_data)
    serialized_shards = rpc_utils.prepare_rows_as_nested_dicts(shards, ())
    for serialized, shard in zip(serialized_shards, shards):
        serialized['labels'] = [label.name for label in shard.labels.all()]

    return serialized_shards


def _assign_board_to_shard_precheck(labels):
    """Verify whether board labels are valid to be added to a given shard.

    First check whether board label is in correct format. Second, check whether
    the board label exist. Third, check whether the board has already been
    assigned to shard.

    @param labels: Board labels separated by comma.

    @raises error.RPCException: If label provided doesn't start with `board:`
            or board has been added to shard already.
    @raises models.Label.DoesNotExist: If the label specified doesn't exist.

    @returns: A list of label models that ready to be added to shard.
    """
    labels = labels.split(',')
    label_models = []
    for label in labels:
        # Check whether the board label is in correct format.
        if not label.startswith('board:'):
            raise error.RPCException('Sharding only supports `board:.*` label.')
        # Check whether the board label exist. If not, exception will be thrown
        # by smart_get function.
        label = models.Label.smart_get(label)
        label_id = models.Label.list_objects({'name':label})[0].get('id')
        # Check whether the board has been sharded already
        try:
            shard = models.Shard.objects.get(labels=label)
            raise error.RPCException(
                    '%s is already on shard %s' % (label, shard.hostname))
        except models.Shard.DoesNotExist as e:
            # board is not on any shard, so it's valid.
            label_models.append(label)
    return label_models


def add_shard(hostname, labels):
    """Add a shard and start running jobs on it.

    @param hostname: The hostname of the shard to be added; needs to be unique.
    @param labels: Board labels separated by comma. Jobs of one of the labels
                   will be assigned to the shard.

    @raises error.RPCException: If label provided doesn't start with `board:` or
            board has been added to shard already.
    @raises model_logic.ValidationError: If a shard with the given hostname
            already exist.
    @raises models.Label.DoesNotExist: If the label specified doesn't exist.

    @returns: The id of the added shard.
    """
    labels = _assign_board_to_shard_precheck(labels)
    shard = models.Shard.add_object(hostname=hostname)
    for label in labels:
        shard.labels.add(label)
    return shard.id


def add_board_to_shard(hostname, labels):
    """Add boards to a given shard

    @param hostname: The hostname of the shard to be changed.
    @param labels: Board labels separated by comma.

    @raises error.RPCException: If label provided doesn't start with `board:` or
            board has been added to shard already.
    @raises models.Label.DoesNotExist: If the label specified doesn't exist.

    @returns: The id of the changed shard.
    """
    labels = _assign_board_to_shard_precheck(labels)
    shard = models.Shard.objects.get(hostname=hostname)
    for label in labels:
        shard.labels.add(label)
    return shard.id


def delete_shard(hostname):
    """Delete a shard and reclaim all resources from it.

    This claims back all assigned hosts from the shard. To ensure all DUTs are
    in a sane state, a Reboot task with highest priority is scheduled for them.
    This reboots the DUTs and then all left tasks continue to run in drone of
    the master.

    The procedure for deleting a shard:
        * Lock all unlocked hosts on that shard.
        * Remove shard information .
        * Assign a reboot task with highest priority to these hosts.
        * Unlock these hosts, then, the reboot tasks run in front of all other
        tasks.

    The status of jobs that haven't been reported to be finished yet, will be
    lost. The master scheduler will pick up the jobs and execute them.

    @param hostname: Hostname of the shard to delete.
    """
    shard = rpc_utils.retrieve_shard(shard_hostname=hostname)
    hostnames_to_lock = [h.hostname for h in
                         models.Host.objects.filter(shard=shard, locked=False)]

    # TODO(beeps): Power off shard
    # For ChromeOS hosts, a reboot test with the highest priority is added to
    # the DUT. After a reboot it should be ganranteed that no processes from
    # prior tests that were run by a shard are still running on.

    # Lock all unlocked hosts.
    dicts = {'locked': True, 'lock_time': datetime.datetime.now()}
    models.Host.objects.filter(hostname__in=hostnames_to_lock).update(**dicts)

    # Remove shard information.
    models.Host.objects.filter(shard=shard).update(shard=None)
    models.Job.objects.filter(shard=shard).update(shard=None)
    shard.labels.clear()
    shard.delete()

    # Assign a reboot task with highest priority: Super.
    t = models.Test.objects.get(name='platform_BootPerfServer:shard')
    c = utils.read_file(os.path.join(common.autotest_dir, t.path))
    if hostnames_to_lock:
        rpc_utils.create_job_common(
                'reboot_dut_for_shard_deletion',
                priority=priorities.Priority.SUPER,
                control_type='Server',
                control_file=c, hosts=hostnames_to_lock)

    # Unlock these shard-related hosts.
    dicts = {'locked': False, 'lock_time': None}
    models.Host.objects.filter(hostname__in=hostnames_to_lock).update(**dicts)


def get_servers(hostname=None, role=None, status=None):
    """Get a list of servers with matching role and status.

    @param hostname: FQDN of the server.
    @param role: Name of the server role, e.g., drone, scheduler. Default to
                 None to match any role.
    @param status: Status of the server, e.g., primary, backup, repair_required.
                   Default to None to match any server status.

    @raises error.RPCException: If server database is not used.
    @return: A list of server names for servers with matching role and status.
    """
    if not server_manager_utils.use_server_db():
        raise error.RPCException('Server database is not enabled. Please try '
                                 'retrieve servers from global config.')
    servers = server_manager_utils.get_servers(hostname=hostname, role=role,
                                               status=status)
    return [s.get_details() for s in servers]


@rpc_utils.route_rpc_to_master
def get_stable_version(board=stable_version_utils.DEFAULT, android=False):
    """Get stable version for the given board.

    @param board: Name of the board.
    @param android: If True, the given board is an Android-based device. If
                    False, assume its a Chrome OS-based device.

    @return: Stable version of the given board. Return global configure value
             of CROS.stable_cros_version if stable_versinos table does not have
             entry of board DEFAULT.
    """
    return stable_version_utils.get(board=board, android=android)


@rpc_utils.route_rpc_to_master
def get_all_stable_versions():
    """Get stable versions for all boards.

    @return: A dictionary of board:version.
    """
    return stable_version_utils.get_all()


@rpc_utils.route_rpc_to_master
def set_stable_version(version, board=stable_version_utils.DEFAULT):
    """Modify stable version for the given board.

    @param version: The new value of stable version for given board.
    @param board: Name of the board, default to value `DEFAULT`.
    """
    stable_version_utils.set(version=version, board=board)


@rpc_utils.route_rpc_to_master
def delete_stable_version(board):
    """Modify stable version for the given board.

    Delete a stable version entry in afe_stable_versions table for a given
    board, so default stable version will be used.

    @param board: Name of the board.
    """
    stable_version_utils.delete(board=board)


def _initialize_control_file_getter(build):
    """Get the remote control file getter.

    @param build: unique name by which to refer to a remote build image.

    @return: A control file getter object.
    """
    # Stage the test artifacts.
    try:
        ds = dev_server.ImageServer.resolve(build)
        ds_name = ds.get_server_name(ds.url())
        build = ds.translate(build)
    except dev_server.DevServerException as e:
        raise ValueError('Could not resolve build %s: %s' %
                         (build, e))

    try:
        ds.stage_artifacts(image=build, artifacts=['test_suites'])
    except dev_server.DevServerException as e:
        raise error.StageControlFileFailure(
                'Failed to stage %s on %s: %s' % (build, ds_name, e))

    # Collect the control files specified in this build
    return control_file_getter.DevServerGetter.create(build, ds)


def get_tests_by_build(build, ignore_invalid_tests=True):
    """Get the tests that are available for the specified build.

    @param build: unique name by which to refer to the image.
    @param ignore_invalid_tests: flag on if unparsable tests are ignored.

    @return: A sorted list of all tests that are in the build specified.
    """
    # Collect the control files specified in this build
    cfile_getter = _initialize_control_file_getter(build)
    if SuiteBase.ENABLE_CONTROLS_IN_BATCH:
        control_file_info_list = cfile_getter.get_suite_info()
        control_file_list = control_file_info_list.keys()
    else:
        control_file_list = cfile_getter.get_control_file_list()

    test_objects = []
    _id = 0
    for control_file_path in control_file_list:
        # Read and parse the control file
        if SuiteBase.ENABLE_CONTROLS_IN_BATCH:
            control_file = control_file_info_list[control_file_path]
        else:
            control_file = cfile_getter.get_control_file_contents(
                    control_file_path)
        try:
            control_obj = control_data.parse_control_string(control_file)
        except:
            logging.info('Failed to parse control file: %s', control_file_path)
            if not ignore_invalid_tests:
                raise

        # Extract the values needed for the AFE from the control_obj.
        # The keys list represents attributes in the control_obj that
        # are required by the AFE
        keys = ['author', 'doc', 'name', 'time', 'test_type', 'experimental',
                'test_category', 'test_class', 'dependencies', 'run_verify',
                'sync_count', 'job_retries', 'retries', 'path']

        test_object = {}
        for key in keys:
            test_object[key] = getattr(control_obj, key) if hasattr(
                    control_obj, key) else ''

        # Unfortunately, the AFE expects different key-names for certain
        # values, these must be corrected to avoid the risk of tests
        # being omitted by the AFE.
        # The 'id' is an additional value used in the AFE.
        # The control_data parsing does not reference 'run_reset', but it
        # is also used in the AFE and defaults to True.
        test_object['id'] = _id
        test_object['run_reset'] = True
        test_object['description'] = test_object.get('doc', '')
        test_object['test_time'] = test_object.get('time', 0)
        test_object['test_retry'] = test_object.get('retries', 0)

        # Fix the test name to be consistent with the current presentation
        # of test names in the AFE.
        testpath, subname = os.path.split(control_file_path)
        testname = os.path.basename(testpath)
        subname = subname.split('.')[1:]
        if subname:
            testname = '%s:%s' % (testname, ':'.join(subname))

        test_object['name'] = testname

        # Correct the test path as parse_control_string sets an empty string.
        test_object['path'] = control_file_path

        _id += 1
        test_objects.append(test_object)

    test_objects = sorted(test_objects, key=lambda x: x.get('name'))
    return rpc_utils.prepare_for_serialization(test_objects)


def get_test_control_files_by_build(tests, build, ignore_invalid_tests=False):
    """Get the test control files that are available for the specified build.

    @param tests A sequence of test objects to run.
    @param build: unique name by which to refer to the image.
    @param ignore_invalid_tests: flag on if unparsable tests are ignored.

    @return: A sorted list of all tests that are in the build specified.
    """
    raw_control_files = []
    # shortcut to avoid staging the image.
    if not tests:
        return raw_control_files

    cfile_getter = _initialize_control_file_getter(build)
    if SuiteBase.ENABLE_CONTROLS_IN_BATCH:
        control_file_info_list = cfile_getter.get_suite_info()

    for test in tests:
        # Read and parse the control file
        if SuiteBase.ENABLE_CONTROLS_IN_BATCH:
            control_file = control_file_info_list[test.path]
        else:
            control_file = cfile_getter.get_control_file_contents(
                    test.path)
        raw_control_files.append(control_file)
    return raw_control_files
