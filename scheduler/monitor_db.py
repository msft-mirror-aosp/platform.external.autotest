#!/usr/bin/python -u
#pylint: disable-msg=C0111

"""
Autotest scheduler
"""


import datetime, optparse, os, signal
import sys, time, traceback, urllib
import logging, gc

import common
from autotest_lib.frontend import setup_django_environment

import django.db

from autotest_lib.client.common_lib import global_config, logging_manager
from autotest_lib.client.common_lib import host_protections, utils
from autotest_lib.database import database_connection
from autotest_lib.frontend.afe import model_attributes
from autotest_lib.frontend.afe import models, rpc_utils, readonly_connection
from autotest_lib.scheduler import drone_manager, drones, email_manager
from autotest_lib.scheduler import gc_stats, host_scheduler, monitor_db_cleanup
from autotest_lib.scheduler import scheduler_logging_config
from autotest_lib.scheduler import scheduler_models
from autotest_lib.scheduler import status_server, scheduler_config
from autotest_lib.server import autoserv_utils
from autotest_lib.server.cros import provision
from autotest_lib.site_utils.graphite import stats

BABYSITTER_PID_FILE_PREFIX = 'monitor_db_babysitter'
PID_FILE_PREFIX = 'monitor_db'

RESULTS_DIR = '.'
AUTOSERV_NICE_LEVEL = 10
DB_CONFIG_SECTION = 'AUTOTEST_WEB'
AUTOTEST_PATH = os.path.join(os.path.dirname(__file__), '..')

if os.environ.has_key('AUTOTEST_DIR'):
    AUTOTEST_PATH = os.environ['AUTOTEST_DIR']
AUTOTEST_SERVER_DIR = os.path.join(AUTOTEST_PATH, 'server')
AUTOTEST_TKO_DIR = os.path.join(AUTOTEST_PATH, 'tko')

if AUTOTEST_SERVER_DIR not in sys.path:
    sys.path.insert(0, AUTOTEST_SERVER_DIR)

# error message to leave in results dir when an autoserv process disappears
# mysteriously
_LOST_PROCESS_ERROR = """\
Autoserv failed abnormally during execution for this job, probably due to a
system error on the Autotest server.  Full results may not be available.  Sorry.
"""

_db = None
_shutdown = False
_autoserv_directory = os.path.join(drones.AUTOTEST_INSTALL_DIR, 'server')
_autoserv_path = os.path.join(_autoserv_directory, 'autoserv')
_testing_mode = False
_drone_manager = None

def _parser_path_default(install_dir):
    return os.path.join(install_dir, 'tko', 'parse')
_parser_path_func = utils.import_site_function(
        __file__, 'autotest_lib.scheduler.site_monitor_db',
        'parser_path', _parser_path_default)
_parser_path = _parser_path_func(drones.AUTOTEST_INSTALL_DIR)


def _get_pidfile_timeout_secs():
    """@returns How long to wait for autoserv to write pidfile."""
    pidfile_timeout_mins = global_config.global_config.get_config_value(
            scheduler_config.CONFIG_SECTION, 'pidfile_timeout_mins', type=int)
    return pidfile_timeout_mins * 60


def _site_init_monitor_db_dummy():
    return {}


def _verify_default_drone_set_exists():
    if (models.DroneSet.drone_sets_enabled() and
            not models.DroneSet.default_drone_set_name()):
        raise host_scheduler.SchedulerError(
                'Drone sets are enabled, but no default is set')


def _sanity_check():
    """Make sure the configs are consistent before starting the scheduler"""
    _verify_default_drone_set_exists()


def main():
    try:
        try:
            main_without_exception_handling()
        except SystemExit:
            raise
        except:
            logging.exception('Exception escaping in monitor_db')
            raise
    finally:
        utils.delete_pid_file_if_exists(PID_FILE_PREFIX)


def main_without_exception_handling():
    setup_logging()

    usage = 'usage: %prog [options] results_dir'
    parser = optparse.OptionParser(usage)
    parser.add_option('--recover-hosts', help='Try to recover dead hosts',
                      action='store_true')
    parser.add_option('--test', help='Indicate that scheduler is under ' +
                      'test and should use dummy autoserv and no parsing',
                      action='store_true')
    (options, args) = parser.parse_args()
    if len(args) != 1:
        parser.print_usage()
        return

    scheduler_enabled = global_config.global_config.get_config_value(
        scheduler_config.CONFIG_SECTION, 'enable_scheduler', type=bool)

    if not scheduler_enabled:
        logging.error("Scheduler not enabled, set enable_scheduler to true in "
                      "the global_config's SCHEDULER section to enable it. "
                      "Exiting.")
        sys.exit(1)

    global RESULTS_DIR
    RESULTS_DIR = args[0]

    site_init = utils.import_site_function(__file__,
        "autotest_lib.scheduler.site_monitor_db", "site_init_monitor_db",
        _site_init_monitor_db_dummy)
    site_init()

    # Change the cwd while running to avoid issues incase we were launched from
    # somewhere odd (such as a random NFS home directory of the person running
    # sudo to launch us as the appropriate user).
    os.chdir(RESULTS_DIR)

    # This is helpful for debugging why stuff a scheduler launches is
    # misbehaving.
    logging.info('os.environ: %s', os.environ)

    if options.test:
        global _autoserv_path
        _autoserv_path = 'autoserv_dummy'
        global _testing_mode
        _testing_mode = True

    server = status_server.StatusServer()
    server.start()

    try:
        initialize()
        dispatcher = Dispatcher()
        dispatcher.initialize(recover_hosts=options.recover_hosts)

        while not _shutdown and not server._shutdown_scheduler:
            dispatcher.tick()
            time.sleep(scheduler_config.config.tick_pause_sec)
    except:
        email_manager.manager.log_stacktrace(
            "Uncaught exception; terminating monitor_db")

    email_manager.manager.send_queued_emails()
    server.shutdown()
    _drone_manager.shutdown()
    _db.disconnect()


def setup_logging():
    log_dir = os.environ.get('AUTOTEST_SCHEDULER_LOG_DIR', None)
    log_name = os.environ.get('AUTOTEST_SCHEDULER_LOG_NAME', None)
    logging_manager.configure_logging(
            scheduler_logging_config.SchedulerLoggingConfig(), log_dir=log_dir,
            logfile_name=log_name)


def handle_sigint(signum, frame):
    global _shutdown
    _shutdown = True
    logging.info("Shutdown request received.")


def initialize():
    logging.info("%s> dispatcher starting", time.strftime("%X %x"))
    logging.info("My PID is %d", os.getpid())

    if utils.program_is_alive(PID_FILE_PREFIX):
        logging.critical("monitor_db already running, aborting!")
        sys.exit(1)
    utils.write_pid(PID_FILE_PREFIX)

    if _testing_mode:
        global_config.global_config.override_config_value(
            DB_CONFIG_SECTION, 'database', 'stresstest_autotest_web')

    os.environ['PATH'] = AUTOTEST_SERVER_DIR + ':' + os.environ['PATH']
    global _db
    _db = database_connection.DatabaseConnection(DB_CONFIG_SECTION)
    _db.connect(db_type='django')

    # ensure Django connection is in autocommit
    setup_django_environment.enable_autocommit()
    # bypass the readonly connection
    readonly_connection.ReadOnlyConnection.set_globally_disabled(True)

    logging.info("Setting signal handler")
    signal.signal(signal.SIGINT, handle_sigint)

    initialize_globals()
    scheduler_models.initialize()

    drones = global_config.global_config.get_config_value(
        scheduler_config.CONFIG_SECTION, 'drones', default='localhost')
    drone_list = [hostname.strip() for hostname in drones.split(',')]
    results_host = global_config.global_config.get_config_value(
        scheduler_config.CONFIG_SECTION, 'results_host', default='localhost')
    _drone_manager.initialize(RESULTS_DIR, drone_list, results_host)

    logging.info("Connected! Running...")


def initialize_globals():
    global _drone_manager
    _drone_manager = drone_manager.instance()


def _autoserv_command_line(machines, extra_args, job=None, queue_entry=None,
                           verbose=True):
    """
    @returns The autoserv command line as a list of executable + parameters.

    @param machines - string - A machine or comma separated list of machines
            for the (-m) flag.
    @param extra_args - list - Additional arguments to pass to autoserv.
    @param job - Job object - If supplied, -u owner, -l name, --test-retry,
            and client -c or server -s parameters will be added.
    @param queue_entry - A HostQueueEntry object - If supplied and no Job
            object was supplied, this will be used to lookup the Job object.
    """
    return autoserv_utils.autoserv_run_job_command(_autoserv_directory,
            machines, results_directory=drone_manager.WORKING_DIRECTORY,
            extra_args=extra_args, job=job, queue_entry=queue_entry,
            verbose=verbose)


class BaseDispatcher(object):


    def __init__(self):
        self._agents = []
        self._last_clean_time = time.time()
        self._host_scheduler = host_scheduler.HostScheduler(_db)
        user_cleanup_time = scheduler_config.config.clean_interval
        self._periodic_cleanup = monitor_db_cleanup.UserCleanup(
            _db, user_cleanup_time)
        self._24hr_upkeep = monitor_db_cleanup.TwentyFourHourUpkeep(_db)
        self._host_agents = {}
        self._queue_entry_agents = {}
        self._tick_count = 0
        self._last_garbage_stats_time = time.time()
        self._seconds_between_garbage_stats = 60 * (
                global_config.global_config.get_config_value(
                        scheduler_config.CONFIG_SECTION,
                        'gc_stats_interval_mins', type=int, default=6*60))
        self._tick_debug = global_config.global_config.get_config_value(
                scheduler_config.CONFIG_SECTION, 'tick_debug', type=bool,
                default=False)
        self._extra_debugging = global_config.global_config.get_config_value(
                scheduler_config.CONFIG_SECTION, 'extra_debugging', type=bool,
                default=False)


    def initialize(self, recover_hosts=True):
        self._periodic_cleanup.initialize()
        self._24hr_upkeep.initialize()

        # always recover processes
        self._recover_processes()

        if recover_hosts:
            self._recover_hosts()

        self._host_scheduler.recovery_on_startup()


    def _log_tick_msg(self, msg):
        if self._tick_debug:
            logging.debug(msg)


    def _log_extra_msg(self, msg):
        if self._extra_debugging:
            logging.debug(msg)


    def tick(self):
        """
        This is an altered version of tick() where we keep track of when each
        major step begins so we can try to figure out where we are using most
        of the tick time.
        """
        timer = stats.Timer('scheduler.tick')
        self._log_tick_msg('Calling new tick, starting garbage collection().')
        self._garbage_collection()
        self._log_tick_msg('Calling _drone_manager.refresh().')
        _drone_manager.refresh()
        self._log_tick_msg('Calling _run_cleanup().')
        self._run_cleanup()
        self._log_tick_msg('Calling _find_aborting().')
        self._find_aborting()
        self._log_tick_msg('Calling _find_aborted_special_tasks().')
        self._find_aborted_special_tasks()
        self._log_tick_msg('Calling _process_recurring_runs().')
        self._process_recurring_runs()
        self._log_tick_msg('Calling _schedule_delay_tasks().')
        self._schedule_delay_tasks()
        self._log_tick_msg('Calling _schedule_running_host_queue_entries().')
        self._schedule_running_host_queue_entries()
        self._log_tick_msg('Calling _schedule_special_tasks().')
        self._schedule_special_tasks()
        self._log_tick_msg('Calling _schedule_new_jobs().')
        self._schedule_new_jobs()
        self._log_tick_msg('Calling _handle_agents().')
        self._handle_agents()
        self._log_tick_msg('Calling _host_scheduler.tick().')
        self._host_scheduler.tick()
        self._log_tick_msg('Calling _drone_manager.execute_actions().')
        _drone_manager.execute_actions()
        self._log_tick_msg('Calling '
                           'email_manager.manager.send_queued_emails().')
        with timer.get_client('email_manager_send_queued_emails'):
            email_manager.manager.send_queued_emails()
        self._log_tick_msg('Calling django.db.reset_queries().')
        with timer.get_client('django_db_reset_queries'):
            django.db.reset_queries()
        self._tick_count += 1


    def _run_cleanup(self):
        self._periodic_cleanup.run_cleanup_maybe()
        self._24hr_upkeep.run_cleanup_maybe()


    def _garbage_collection(self):
        threshold_time = time.time() - self._seconds_between_garbage_stats
        if threshold_time < self._last_garbage_stats_time:
            # Don't generate these reports very often.
            return

        self._last_garbage_stats_time = time.time()
        # Force a full level 0 collection (because we can, it doesn't hurt
        # at this interval).
        gc.collect()
        logging.info('Logging garbage collector stats on tick %d.',
                     self._tick_count)
        gc_stats._log_garbage_collector_stats()


    def _register_agent_for_ids(self, agent_dict, object_ids, agent):
        for object_id in object_ids:
            agent_dict.setdefault(object_id, set()).add(agent)


    def _unregister_agent_for_ids(self, agent_dict, object_ids, agent):
        for object_id in object_ids:
            assert object_id in agent_dict
            agent_dict[object_id].remove(agent)


    def add_agent_task(self, agent_task):
        """
        Creates and adds an agent to the dispatchers list.

        In creating the agent we also pass on all the queue_entry_ids and
        host_ids from the special agent task. For every agent we create, we
        add it to 1. a dict against the queue_entry_ids given to it 2. A dict
        against the host_ids given to it. So theoritically, a host can have any
        number of agents associated with it, and each of them can have any
        special agent task, though in practice we never see > 1 agent/task per
        host at any time.

        @param agent_task: A SpecialTask for the agent to manage.
        """
        agent = Agent(agent_task)
        self._agents.append(agent)
        agent.dispatcher = self
        self._register_agent_for_ids(self._host_agents, agent.host_ids, agent)
        self._register_agent_for_ids(self._queue_entry_agents,
                                     agent.queue_entry_ids, agent)


    def get_agents_for_entry(self, queue_entry):
        """
        Find agents corresponding to the specified queue_entry.
        """
        return list(self._queue_entry_agents.get(queue_entry.id, set()))


    def host_has_agent(self, host):
        """
        Determine if there is currently an Agent present using this host.
        """
        return bool(self._host_agents.get(host.id, None))


    def remove_agent(self, agent):
        self._agents.remove(agent)
        self._unregister_agent_for_ids(self._host_agents, agent.host_ids,
                                       agent)
        self._unregister_agent_for_ids(self._queue_entry_agents,
                                       agent.queue_entry_ids, agent)


    def _host_has_scheduled_special_task(self, host):
        return bool(models.SpecialTask.objects.filter(host__id=host.id,
                                                      is_active=False,
                                                      is_complete=False))


    def _recover_processes(self):
        agent_tasks = self._create_recovery_agent_tasks()
        self._register_pidfiles(agent_tasks)
        _drone_manager.refresh()
        self._recover_tasks(agent_tasks)
        self._recover_pending_entries()
        self._check_for_unrecovered_verifying_entries()
        self._reverify_remaining_hosts()
        # reinitialize drones after killing orphaned processes, since they can
        # leave around files when they die
        _drone_manager.execute_actions()
        _drone_manager.reinitialize_drones()


    def _create_recovery_agent_tasks(self):
        return (self._get_queue_entry_agent_tasks()
                + self._get_special_task_agent_tasks(is_active=True))


    def _get_queue_entry_agent_tasks(self):
        """
        Get agent tasks for all hqe in the specified states.

        Loosely this translates to taking a hqe in one of the specified states,
        say parsing, and getting an AgentTask for it, like the FinalReparseTask,
        through _get_agent_task_for_queue_entry. Each queue entry can only have
        one agent task at a time, but there might be multiple queue entries in
        the group.

        @return: A list of AgentTasks.
        """
        # host queue entry statuses handled directly by AgentTasks (Verifying is
        # handled through SpecialTasks, so is not listed here)
        statuses = (models.HostQueueEntry.Status.STARTING,
                    models.HostQueueEntry.Status.RUNNING,
                    models.HostQueueEntry.Status.GATHERING,
                    models.HostQueueEntry.Status.PARSING,
                    models.HostQueueEntry.Status.ARCHIVING)
        status_list = ','.join("'%s'" % status for status in statuses)
        queue_entries = scheduler_models.HostQueueEntry.fetch(
                where='status IN (%s)' % status_list)

        agent_tasks = []
        used_queue_entries = set()
        for entry in queue_entries:
            if self.get_agents_for_entry(entry):
                # already being handled
                continue
            if entry in used_queue_entries:
                # already picked up by a synchronous job
                continue
            agent_task = self._get_agent_task_for_queue_entry(entry)
            agent_tasks.append(agent_task)
            used_queue_entries.update(agent_task.queue_entries)
        return agent_tasks


    def _get_special_task_agent_tasks(self, is_active=False):
        special_tasks = models.SpecialTask.objects.filter(
                is_active=is_active, is_complete=False)
        return [self._get_agent_task_for_special_task(task)
                for task in special_tasks]


    def _get_agent_task_for_queue_entry(self, queue_entry):
        """
        Construct an AgentTask instance for the given active HostQueueEntry.

        @param queue_entry: a HostQueueEntry
        @return: an AgentTask to run the queue entry
        """
        task_entries = queue_entry.job.get_group_entries(queue_entry)
        self._check_for_duplicate_host_entries(task_entries)

        if queue_entry.status in (models.HostQueueEntry.Status.STARTING,
                                  models.HostQueueEntry.Status.RUNNING):
            if queue_entry.is_hostless():
                return HostlessQueueTask(queue_entry=queue_entry)
            return QueueTask(queue_entries=task_entries)
        if queue_entry.status == models.HostQueueEntry.Status.GATHERING:
            return GatherLogsTask(queue_entries=task_entries)
        if queue_entry.status == models.HostQueueEntry.Status.PARSING:
            return FinalReparseTask(queue_entries=task_entries)
        if queue_entry.status == models.HostQueueEntry.Status.ARCHIVING:
            return ArchiveResultsTask(queue_entries=task_entries)

        raise host_scheduler.SchedulerError(
                '_get_agent_task_for_queue_entry got entry with '
                'invalid status %s: %s' % (queue_entry.status, queue_entry))


    def _check_for_duplicate_host_entries(self, task_entries):
        non_host_statuses = (models.HostQueueEntry.Status.PARSING,
                             models.HostQueueEntry.Status.ARCHIVING)
        for task_entry in task_entries:
            using_host = (task_entry.host is not None
                          and task_entry.status not in non_host_statuses)
            if using_host:
                self._assert_host_has_no_agent(task_entry)


    def _assert_host_has_no_agent(self, entry):
        """
        @param entry: a HostQueueEntry or a SpecialTask
        """
        if self.host_has_agent(entry.host):
            agent = tuple(self._host_agents.get(entry.host.id))[0]
            raise host_scheduler.SchedulerError(
                    'While scheduling %s, host %s already has a host agent %s'
                    % (entry, entry.host, agent.task))


    def _get_agent_task_for_special_task(self, special_task):
        """
        Construct an AgentTask class to run the given SpecialTask and add it
        to this dispatcher.

        A special task is create through schedule_special_tasks, but only if
        the host doesn't already have an agent. This happens through
        add_agent_task. All special agent tasks are given a host on creation,
        and a Null hqe. To create a SpecialAgentTask object, you need a
        models.SpecialTask. If the SpecialTask used to create a SpecialAgentTask
        object contains a hqe it's passed on to the special agent task, which
        creates a HostQueueEntry and saves it as it's queue_entry.

        @param special_task: a models.SpecialTask instance
        @returns an AgentTask to run this SpecialTask
        """
        self._assert_host_has_no_agent(special_task)

        special_agent_task_classes = (CleanupTask, VerifyTask, RepairTask,
                                      ResetTask, ProvisionTask)
        for agent_task_class in special_agent_task_classes:
            if agent_task_class.TASK_TYPE == special_task.task:
                return agent_task_class(task=special_task)

        raise host_scheduler.SchedulerError(
                'No AgentTask class for task', str(special_task))


    def _register_pidfiles(self, agent_tasks):
        for agent_task in agent_tasks:
            agent_task.register_necessary_pidfiles()


    def _recover_tasks(self, agent_tasks):
        orphans = _drone_manager.get_orphaned_autoserv_processes()

        for agent_task in agent_tasks:
            agent_task.recover()
            if agent_task.monitor and agent_task.monitor.has_process():
                orphans.discard(agent_task.monitor.get_process())
            self.add_agent_task(agent_task)

        self._check_for_remaining_orphan_processes(orphans)


    def _get_unassigned_entries(self, status):
        for entry in scheduler_models.HostQueueEntry.fetch(where="status = '%s'"
                                                           % status):
            if entry.status == status and not self.get_agents_for_entry(entry):
                # The status can change during iteration, e.g., if job.run()
                # sets a group of queue entries to Starting
                yield entry


    def _check_for_remaining_orphan_processes(self, orphans):
        if not orphans:
            return
        subject = 'Unrecovered orphan autoserv processes remain'
        message = '\n'.join(str(process) for process in orphans)
        email_manager.manager.enqueue_notify_email(subject, message)

        die_on_orphans = global_config.global_config.get_config_value(
            scheduler_config.CONFIG_SECTION, 'die_on_orphans', type=bool)

        if die_on_orphans:
            raise RuntimeError(subject + '\n' + message)


    def _recover_pending_entries(self):
        for entry in self._get_unassigned_entries(
                models.HostQueueEntry.Status.PENDING):
            logging.info('Recovering Pending entry %s', entry)
            entry.on_pending()


    def _check_for_unrecovered_verifying_entries(self):
        queue_entries = scheduler_models.HostQueueEntry.fetch(
                where='status = "%s"' % models.HostQueueEntry.Status.VERIFYING)
        unrecovered_hqes = []
        for queue_entry in queue_entries:
            special_tasks = models.SpecialTask.objects.filter(
                    task__in=(models.SpecialTask.Task.CLEANUP,
                              models.SpecialTask.Task.VERIFY),
                    queue_entry__id=queue_entry.id,
                    is_complete=False)
            if special_tasks.count() == 0:
                unrecovered_hqes.append(queue_entry)

        if unrecovered_hqes:
            message = '\n'.join(str(hqe) for hqe in unrecovered_hqes)
            raise host_scheduler.SchedulerError(
                    '%d unrecovered verifying host queue entries:\n%s' %
                    (len(unrecovered_hqes), message))


    def _get_prioritized_special_tasks(self):
        """
        Returns all queued SpecialTasks prioritized for repair first, then
        cleanup, then verify.

        @return: list of afe.models.SpecialTasks sorted according to priority.
        """
        queued_tasks = models.SpecialTask.objects.filter(is_active=False,
                                                         is_complete=False,
                                                         host__locked=False)
        # exclude hosts with active queue entries unless the SpecialTask is for
        # that queue entry
        queued_tasks = models.SpecialTask.objects.add_join(
                queued_tasks, 'afe_host_queue_entries', 'host_id',
                join_condition='afe_host_queue_entries.active',
                join_from_key='host_id', force_left_join=True)
        queued_tasks = queued_tasks.extra(
                where=['(afe_host_queue_entries.id IS NULL OR '
                       'afe_host_queue_entries.id = '
                               'afe_special_tasks.queue_entry_id)'])

        # reorder tasks by priority
        task_priority_order = [models.SpecialTask.Task.REPAIR,
                               models.SpecialTask.Task.CLEANUP,
                               models.SpecialTask.Task.VERIFY,
                               models.SpecialTask.Task.RESET,
                               models.SpecialTask.Task.PROVISION]
        def task_priority_key(task):
            return task_priority_order.index(task.task)
        return sorted(queued_tasks, key=task_priority_key)


    def _schedule_special_tasks(self):
        """
        Execute queued SpecialTasks that are ready to run on idle hosts.

        Special tasks include PreJobTasks like verify, reset and cleanup.
        They are created through _schedule_new_jobs and associated with a hqe
        This method translates SpecialTasks to the appropriate AgentTask and
        adds them to the dispatchers agents list, so _handle_agents can execute
        them.
        """
        for task in self._get_prioritized_special_tasks():
            if self.host_has_agent(task.host):
                continue
            self.add_agent_task(self._get_agent_task_for_special_task(task))


    def _reverify_remaining_hosts(self):
        # recover active hosts that have not yet been recovered, although this
        # should never happen
        message = ('Recovering active host %s - this probably indicates a '
                   'scheduler bug')
        self._reverify_hosts_where(
                "status IN ('Repairing', 'Verifying', 'Cleaning', 'Provisioning')",
                print_message=message)


    def _reverify_hosts_where(self, where,
                              print_message='Reverifying host %s'):
        full_where='locked = 0 AND invalid = 0 AND ' + where
        for host in scheduler_models.Host.fetch(where=full_where):
            if self.host_has_agent(host):
                # host has already been recovered in some way
                continue
            if self._host_has_scheduled_special_task(host):
                # host will have a special task scheduled on the next cycle
                continue
            if print_message:
                logging.info(print_message, host.hostname)
            models.SpecialTask.objects.create(
                    task=models.SpecialTask.Task.CLEANUP,
                    host=models.Host.objects.get(id=host.id))


    def _recover_hosts(self):
        # recover "Repair Failed" hosts
        message = 'Reverifying dead host %s'
        self._reverify_hosts_where("status = 'Repair Failed'",
                                   print_message=message)



    def _get_pending_queue_entries(self):
        # prioritize by job priority, then non-metahost over metahost, then FIFO
        return list(scheduler_models.HostQueueEntry.fetch(
            joins='INNER JOIN afe_jobs ON (job_id=afe_jobs.id)',
            where='NOT complete AND NOT active AND status="Queued"',
            order_by='afe_jobs.priority DESC, meta_host, job_id'))


    def _refresh_pending_queue_entries(self):
        """
        Lookup the pending HostQueueEntries and call our HostScheduler
        refresh() method given that list.  Return the list.

        @returns A list of pending HostQueueEntries sorted in priority order.
        """
        queue_entries = self._get_pending_queue_entries()
        if not queue_entries:
            return []

        self._host_scheduler.refresh(queue_entries)

        return queue_entries


    def _schedule_atomic_group(self, queue_entry):
        """
        Schedule the given queue_entry on an atomic group of hosts.

        Returns immediately if there are insufficient available hosts.

        Creates new HostQueueEntries based off of queue_entry for the
        scheduled hosts and starts them all running.
        """
        # This is a virtual host queue entry representing an entire
        # atomic group, find a group and schedule their hosts.
        group_hosts = self._host_scheduler.find_eligible_atomic_group(
                queue_entry)
        if not group_hosts:
            return

        logging.info('Expanding atomic group entry %s with hosts %s',
                     queue_entry,
                     ', '.join(host.hostname for host in group_hosts))

        for assigned_host in group_hosts[1:]:
            # Create a new HQE for every additional assigned_host.
            new_hqe = scheduler_models.HostQueueEntry.clone(queue_entry)
            new_hqe.save()
            new_hqe.set_host(assigned_host)
            self._run_queue_entry(new_hqe)

        # The first assigned host uses the original HostQueueEntry
        queue_entry.set_host(group_hosts[0])
        self._run_queue_entry(queue_entry)


    def _schedule_hostless_job(self, queue_entry):
        self.add_agent_task(HostlessQueueTask(queue_entry))
        queue_entry.set_status(models.HostQueueEntry.Status.STARTING)


    def _schedule_new_jobs(self):
        """
        Find any new HQEs and call schedule_pre_job_tasks for it.

        This involves setting the status of the HQE and creating a row in the
        db corresponding the the special task, through
        scheduler_models._queue_special_task. The new db row is then added as
        an agent to the dispatcher through _schedule_special_tasks and
        scheduled for execution on the drone through _handle_agents.
        """
        queue_entries = self._refresh_pending_queue_entries()
        if not queue_entries:
            return

        logging.debug('Processing %d queue_entries', len(queue_entries))
        for queue_entry in queue_entries:
            self._log_extra_msg('Processing queue_entry: %s' % queue_entry)
            is_unassigned_atomic_group = (
                    queue_entry.atomic_group_id is not None
                    and queue_entry.host_id is None)

            if queue_entry.is_hostless():
                self._log_extra_msg('Scheduling hostless job.')
                self._schedule_hostless_job(queue_entry)
            elif is_unassigned_atomic_group:
                self._schedule_atomic_group(queue_entry)
            else:
                assigned_host = self._host_scheduler.schedule_entry(queue_entry)
                if assigned_host and not self.host_has_agent(assigned_host):
                    assert assigned_host.id == queue_entry.host_id
                    self._run_queue_entry(queue_entry)


    def _schedule_running_host_queue_entries(self):
        """
        Adds agents to the dispatcher.

        Any AgentTask, like the QueueTask, is wrapped in an Agent. The
        QueueTask for example, will have a job with a control file, and
        the agent will have methods that poll, abort and check if the queue
        task is finished. The dispatcher runs the agent_task, as well as
        other agents in it's _agents member, through _handle_agents, by
        calling the Agents tick().

        This method creates an agent for each HQE in one of (starting, running,
        gathering, parsing, archiving) states, and adds it to the dispatcher so
        it is handled by _handle_agents.
        """
        for agent_task in self._get_queue_entry_agent_tasks():
            self.add_agent_task(agent_task)


    def _schedule_delay_tasks(self):
        for entry in scheduler_models.HostQueueEntry.fetch(
                where='status = "%s"' % models.HostQueueEntry.Status.WAITING):
            task = entry.job.schedule_delayed_callback_task(entry)
            if task:
                self.add_agent_task(task)


    def _run_queue_entry(self, queue_entry):
        self._log_extra_msg('Scheduling pre job tasks for queue_entry: %s' %
                            queue_entry)
        queue_entry.schedule_pre_job_tasks()


    def _find_aborting(self):
        """
        Looks through the afe_host_queue_entries for an aborted entry.

        The aborted bit is set on an HQE in many ways, the most common
        being when a user requests an abort through the frontend, which
        results in an rpc from the afe to abort_host_queue_entries.
        """
        jobs_to_stop = set()
        for entry in scheduler_models.HostQueueEntry.fetch(
                where='aborted=1 and complete=0'):
            logging.info('Aborting %s', entry)
            for agent in self.get_agents_for_entry(entry):
                agent.abort()
            entry.abort(self)
            jobs_to_stop.add(entry.job)
        logging.debug('Aborting %d jobs this tick.', len(jobs_to_stop))
        for job in jobs_to_stop:
            job.stop_if_necessary()


    def _find_aborted_special_tasks(self):
        """
        Find SpecialTasks that have been marked for abortion.

        Poll the database looking for SpecialTasks that are active
        and have been marked for abortion, then abort them.
        """

        # The completed and active bits are very important when it comes
        # to scheduler correctness. The active bit is set through the prolog
        # of a special task, and reset through the cleanup method of the
        # SpecialAgentTask. The cleanup is called both through the abort and
        # epilog. The complete bit is set in several places, and in general
        # a hanging job will have is_active=1 is_complete=0, while a special
        # task which completed will have is_active=0 is_complete=1. To check
        # aborts we directly check active because the complete bit is set in
        # several places, including the epilog of agent tasks.
        aborted_tasks = models.SpecialTask.objects.filter(is_active=True,
                                                          is_aborted=True)
        for task in aborted_tasks:
            # There are 2 ways to get the agent associated with a task,
            # through the host and through the hqe. A special task
            # always needs a host, but doesn't always need a hqe.
            for agent in self._host_agents.get(task.host.id, []):
                if isinstance(agent.task, SpecialAgentTask):

                    # The epilog preforms critical actions such as
                    # queueing the next SpecialTask, requeuing the
                    # hqe etc, however it doesn't actually kill the
                    # monitor process and set the 'done' bit. Epilogs
                    # assume that the job failed, and that the monitor
                    # process has already written an exit code. The
                    # done bit is a necessary condition for
                    # _handle_agents to schedule any more special
                    # tasks against the host, and it must be set
                    # in addition to is_active, is_complete and success.
                    agent.task.epilog()
                    agent.task.abort()


    def _can_start_agent(self, agent, num_started_this_cycle,
                         have_reached_limit):
        # always allow zero-process agents to run
        if agent.task.num_processes == 0:
            return True
        # don't allow any nonzero-process agents to run after we've reached a
        # limit (this avoids starvation of many-process agents)
        if have_reached_limit:
            return False
        # total process throttling
        max_runnable_processes = _drone_manager.max_runnable_processes(
                agent.task.owner_username,
                agent.task.get_drone_hostnames_allowed())
        if agent.task.num_processes > max_runnable_processes:
            return False
        # if a single agent exceeds the per-cycle throttling, still allow it to
        # run when it's the first agent in the cycle
        if num_started_this_cycle == 0:
            return True
        # per-cycle throttling
        if (num_started_this_cycle + agent.task.num_processes >
                scheduler_config.config.max_processes_started_per_cycle):
            return False
        return True


    def _handle_agents(self):
        """
        Handles agents of the dispatcher.

        Appropriate Agents are added to the dispatcher through
        _schedule_running_host_queue_entries. These agents each
        have a task. This method runs the agents task through
        agent.tick() leading to:
            agent.start
                prolog -> AgentTasks prolog
                          For each queue entry:
                            sets host status/status to Running
                            set started_on in afe_host_queue_entries
                run    -> AgentTasks run
                          Creates PidfileRunMonitor
                          Queues the autoserv command line for this AgentTask
                          via the drone manager. These commands are executed
                          through the drone managers execute actions.
                poll   -> AgentTasks/BaseAgentTask poll
                          checks the monitors exit_code.
                          Executes epilog if task is finished.
                          Executes AgentTasks _finish_task
                finish_task is usually responsible for setting the status
                of the HQE/host, and updating it's active and complete fileds.

            agent.is_done
                Removed the agent from the dispatchers _agents queue.
                Is_done checks the finished bit on the agent, that is
                set based on the Agents task. During the agents poll
                we check to see if the monitor process has exited in
                it's finish method, and set the success member of the
                task based on this exit code.
        """
        num_started_this_cycle = 0
        have_reached_limit = False
        # iterate over copy, so we can remove agents during iteration
        logging.debug('Handling %d Agents', len(self._agents))
        for agent in list(self._agents):
            self._log_extra_msg('Processing Agent with Host Ids: %s and '
                                'queue_entry ids:%s' % (agent.host_ids,
                                agent.queue_entry_ids))
            if not agent.started:
                if not self._can_start_agent(agent, num_started_this_cycle,
                                             have_reached_limit):
                    have_reached_limit = True
                    logging.debug('Reached Limit of allowed running Agents.')
                    continue
                num_started_this_cycle += agent.task.num_processes
                self._log_extra_msg('Starting Agent')
            agent.tick()
            self._log_extra_msg('Agent tick completed.')
            if agent.is_done():
                self._log_extra_msg("Agent finished")
                self.remove_agent(agent)
        logging.info('%d running processes. %d added this cycle.',
                     _drone_manager.total_running_processes(),
                     num_started_this_cycle)


    def _process_recurring_runs(self):
        recurring_runs = models.RecurringRun.objects.filter(
            start_date__lte=datetime.datetime.now())
        for rrun in recurring_runs:
            # Create job from template
            job = rrun.job
            info = rpc_utils.get_job_info(job)
            options = job.get_object_dict()

            host_objects = info['hosts']
            one_time_hosts = info['one_time_hosts']
            metahost_objects = info['meta_hosts']
            dependencies = info['dependencies']
            atomic_group = info['atomic_group']

            for host in one_time_hosts or []:
                this_host = models.Host.create_one_time_host(host.hostname)
                host_objects.append(this_host)

            try:
                rpc_utils.create_new_job(owner=rrun.owner.login,
                                         options=options,
                                         host_objects=host_objects,
                                         metahost_objects=metahost_objects,
                                         atomic_group=atomic_group)

            except Exception, ex:
                logging.exception(ex)
                #TODO send email

            if rrun.loop_count == 1:
                rrun.delete()
            else:
                if rrun.loop_count != 0: # if not infinite loop
                    # calculate new start_date
                    difference = datetime.timedelta(seconds=rrun.loop_period)
                    rrun.start_date = rrun.start_date + difference
                    rrun.loop_count -= 1
                    rrun.save()


SiteDispatcher = utils.import_site_class(
    __file__, 'autotest_lib.scheduler.site_monitor_db',
    'SiteDispatcher', BaseDispatcher)

class Dispatcher(SiteDispatcher):
    pass


class PidfileRunMonitor(object):
    """
    Client must call either run() to start a new process or
    attach_to_existing_process().
    """

    class _PidfileException(Exception):
        """
        Raised when there's some unexpected behavior with the pid file, but only
        used internally (never allowed to escape this class).
        """


    def __init__(self):
        self.lost_process = False
        self._start_time = None
        self.pidfile_id = None
        self._state = drone_manager.PidfileContents()


    def _add_nice_command(self, command, nice_level):
        if not nice_level:
            return command
        return ['nice', '-n', str(nice_level)] + command


    def _set_start_time(self):
        self._start_time = time.time()


    def run(self, command, working_directory, num_processes, nice_level=None,
            log_file=None, pidfile_name=None, paired_with_pidfile=None,
            username=None, drone_hostnames_allowed=None):
        assert command is not None
        if nice_level is not None:
            command = ['nice', '-n', str(nice_level)] + command
        self._set_start_time()
        self.pidfile_id = _drone_manager.execute_command(
            command, working_directory, pidfile_name=pidfile_name,
            num_processes=num_processes, log_file=log_file,
            paired_with_pidfile=paired_with_pidfile, username=username,
            drone_hostnames_allowed=drone_hostnames_allowed)


    def attach_to_existing_process(self, execution_path,
                                   pidfile_name=drone_manager.AUTOSERV_PID_FILE,
                                   num_processes=None):
        self._set_start_time()
        self.pidfile_id = _drone_manager.get_pidfile_id_from(
            execution_path, pidfile_name=pidfile_name)
        if num_processes is not None:
            _drone_manager.declare_process_count(self.pidfile_id, num_processes)


    def kill(self):
        if self.has_process():
            _drone_manager.kill_process(self.get_process())


    def has_process(self):
        self._get_pidfile_info()
        return self._state.process is not None


    def get_process(self):
        self._get_pidfile_info()
        assert self._state.process is not None
        return self._state.process


    def _read_pidfile(self, use_second_read=False):
        assert self.pidfile_id is not None, (
            'You must call run() or attach_to_existing_process()')
        contents = _drone_manager.get_pidfile_contents(
            self.pidfile_id, use_second_read=use_second_read)
        if contents.is_invalid():
            self._state = drone_manager.PidfileContents()
            raise self._PidfileException(contents)
        self._state = contents


    def _handle_pidfile_error(self, error, message=''):
        message = error + '\nProcess: %s\nPidfile: %s\n%s' % (
            self._state.process, self.pidfile_id, message)
        email_manager.manager.enqueue_notify_email(error, message)
        self.on_lost_process(self._state.process)


    def _get_pidfile_info_helper(self):
        if self.lost_process:
            return

        self._read_pidfile()

        if self._state.process is None:
            self._handle_no_process()
            return

        if self._state.exit_status is None:
            # double check whether or not autoserv is running
            if _drone_manager.is_process_running(self._state.process):
                return

            # pid but no running process - maybe process *just* exited
            self._read_pidfile(use_second_read=True)
            if self._state.exit_status is None:
                # autoserv exited without writing an exit code
                # to the pidfile
                self._handle_pidfile_error(
                    'autoserv died without writing exit code')


    def _get_pidfile_info(self):
        """\
        After completion, self._state will contain:
         pid=None, exit_status=None if autoserv has not yet run
         pid!=None, exit_status=None if autoserv is running
         pid!=None, exit_status!=None if autoserv has completed
        """
        try:
            self._get_pidfile_info_helper()
        except self._PidfileException, exc:
            self._handle_pidfile_error('Pidfile error', traceback.format_exc())


    def _handle_no_process(self):
        """\
        Called when no pidfile is found or no pid is in the pidfile.
        """
        message = 'No pid found at %s' % self.pidfile_id
        if time.time() - self._start_time > _get_pidfile_timeout_secs():
            email_manager.manager.enqueue_notify_email(
                'Process has failed to write pidfile', message)
            self.on_lost_process()


    def on_lost_process(self, process=None):
        """\
        Called when autoserv has exited without writing an exit status,
        or we've timed out waiting for autoserv to write a pid to the
        pidfile.  In either case, we just return failure and the caller
        should signal some kind of warning.

        process is unimportant here, as it shouldn't be used by anyone.
        """
        self.lost_process = True
        self._state.process = process
        self._state.exit_status = 1
        self._state.num_tests_failed = 0


    def exit_code(self):
        self._get_pidfile_info()
        return self._state.exit_status


    def num_tests_failed(self):
        """@returns The number of tests that failed or -1 if unknown."""
        self._get_pidfile_info()
        if self._state.num_tests_failed is None:
            return -1
        return self._state.num_tests_failed


    def try_copy_results_on_drone(self, **kwargs):
        if self.has_process():
            # copy results logs into the normal place for job results
            _drone_manager.copy_results_on_drone(self.get_process(), **kwargs)


    def try_copy_to_results_repository(self, source, **kwargs):
        if self.has_process():
            _drone_manager.copy_to_results_repository(self.get_process(),
                                                      source, **kwargs)


class Agent(object):
    """
    An agent for use by the Dispatcher class to perform a task.  An agent wraps
    around an AgentTask mainly to associate the AgentTask with the queue_entry
    and host ids.

    The following methods are required on all task objects:
        poll() - Called periodically to let the task check its status and
                update its internal state.  If the task succeeded.
        is_done() - Returns True if the task is finished.
        abort() - Called when an abort has been requested.  The task must
                set its aborted attribute to True if it actually aborted.

    The following attributes are required on all task objects:
        aborted - bool, True if this task was aborted.
        success - bool, True if this task succeeded.
        queue_entry_ids - A sequence of HostQueueEntry ids this task handles.
        host_ids - A sequence of Host ids this task represents.
    """


    def __init__(self, task):
        """
        @param task: An instance of an AgentTask.
        """
        self.task = task

        # This is filled in by Dispatcher.add_agent()
        self.dispatcher = None

        self.queue_entry_ids = task.queue_entry_ids
        self.host_ids = task.host_ids

        self.started = False
        self.finished = False


    def tick(self):
        self.started = True
        if not self.finished:
            self.task.poll()
            if self.task.is_done():
                self.finished = True


    def is_done(self):
        return self.finished


    def abort(self):
        if self.task:
            self.task.abort()
            if self.task.aborted:
                # tasks can choose to ignore aborts
                self.finished = True


class BaseAgentTask(object):
    class _NullMonitor(object):
        pidfile_id = None

        def has_process(self):
            return True


    def __init__(self, log_file_name=None):
        """
        @param log_file_name: (optional) name of file to log command output to
        """
        self.done = False
        self.started = False
        self.success = None
        self.aborted = False
        self.monitor = None
        self.queue_entry_ids = []
        self.host_ids = []
        self._log_file_name = log_file_name


    def _set_ids(self, host=None, queue_entries=None):
        if queue_entries and queue_entries != [None]:
            self.host_ids = [entry.host.id for entry in queue_entries]
            self.queue_entry_ids = [entry.id for entry in queue_entries]
        else:
            assert host
            self.host_ids = [host.id]


    def poll(self):
        if not self.started:
            self.start()
        if not self.done:
            self.tick()


    def tick(self):
        assert self.monitor
        exit_code = self.monitor.exit_code()
        if exit_code is None:
            return

        success = (exit_code == 0)
        self.finished(success)


    def is_done(self):
        return self.done


    def finished(self, success):
        if self.done:
            assert self.started
            return
        self.started = True
        self.done = True
        self.success = success
        self.epilog()


    def prolog(self):
        """
        To be overridden.
        """
        assert not self.monitor
        self.register_necessary_pidfiles()


    def _log_file(self):
        if not self._log_file_name:
            return None
        return os.path.join(self._working_directory(), self._log_file_name)


    def cleanup(self):
        log_file = self._log_file()
        if self.monitor and log_file:
            self.monitor.try_copy_to_results_repository(log_file)


    def epilog(self):
        """
        To be overridden.
        """
        self.cleanup()
        logging.info("%s finished with success=%s", type(self).__name__,
                     self.success)



    def start(self):
        if not self.started:
            self.prolog()
            self.run()

        self.started = True


    def abort(self):
        if self.monitor:
            self.monitor.kill()
        self.done = True
        self.aborted = True
        self.cleanup()


    def _get_consistent_execution_path(self, execution_entries):
        first_execution_path = execution_entries[0].execution_path()
        for execution_entry in execution_entries[1:]:
            assert execution_entry.execution_path() == first_execution_path, (
                '%s (%s) != %s (%s)' % (execution_entry.execution_path(),
                                        execution_entry,
                                        first_execution_path,
                                        execution_entries[0]))
        return first_execution_path


    def _copy_results(self, execution_entries, use_monitor=None):
        """
        @param execution_entries: list of objects with execution_path() method
        """
        if use_monitor is not None and not use_monitor.has_process():
            return

        assert len(execution_entries) > 0
        if use_monitor is None:
            assert self.monitor
            use_monitor = self.monitor
        assert use_monitor.has_process()
        execution_path = self._get_consistent_execution_path(execution_entries)
        results_path = execution_path + '/'
        use_monitor.try_copy_to_results_repository(results_path)


    def _parse_results(self, queue_entries):
        for queue_entry in queue_entries:
            queue_entry.set_status(models.HostQueueEntry.Status.PARSING)


    def _archive_results(self, queue_entries):
        for queue_entry in queue_entries:
            queue_entry.set_status(models.HostQueueEntry.Status.ARCHIVING)


    def _command_line(self):
        """
        Return the command line to run.  Must be overridden.
        """
        raise NotImplementedError


    @property
    def num_processes(self):
        """
        Return the number of processes forked by this BaseAgentTask's process.
        It may only be approximate.  To be overridden if necessary.
        """
        return 1


    def _paired_with_monitor(self):
        """
        If this BaseAgentTask's process must run on the same machine as some
        previous process, this method should be overridden to return a
        PidfileRunMonitor for that process.
        """
        return self._NullMonitor()


    @property
    def owner_username(self):
        """
        Return login of user responsible for this task.  May be None.  Must be
        overridden.
        """
        raise NotImplementedError


    def _working_directory(self):
        """
        Return the directory where this BaseAgentTask's process executes.
        Must be overridden.
        """
        raise NotImplementedError


    def _pidfile_name(self):
        """
        Return the name of the pidfile this BaseAgentTask's process uses.  To be
        overridden if necessary.
        """
        return drone_manager.AUTOSERV_PID_FILE


    def _check_paired_results_exist(self):
        if not self._paired_with_monitor().has_process():
            email_manager.manager.enqueue_notify_email(
                    'No paired results in task',
                    'No paired results in task %s at %s'
                    % (self, self._paired_with_monitor().pidfile_id))
            self.finished(False)
            return False
        return True


    def _create_monitor(self):
        assert not self.monitor
        self.monitor = PidfileRunMonitor()


    def run(self):
        if not self._check_paired_results_exist():
            return

        self._create_monitor()
        self.monitor.run(
                self._command_line(), self._working_directory(),
                num_processes=self.num_processes,
                nice_level=AUTOSERV_NICE_LEVEL, log_file=self._log_file(),
                pidfile_name=self._pidfile_name(),
                paired_with_pidfile=self._paired_with_monitor().pidfile_id,
                username=self.owner_username,
                drone_hostnames_allowed=self.get_drone_hostnames_allowed())


    def get_drone_hostnames_allowed(self):
        if not models.DroneSet.drone_sets_enabled():
            return None

        hqes = models.HostQueueEntry.objects.filter(id__in=self.queue_entry_ids)
        if not hqes:
            # Only special tasks could be missing host queue entries
            assert isinstance(self, SpecialAgentTask)
            return self._user_or_global_default_drone_set(
                    self.task, self.task.requested_by)

        job_ids = hqes.values_list('job', flat=True).distinct()
        assert job_ids.count() == 1, ("BaseAgentTask's queue entries "
                                      "span multiple jobs")

        job = models.Job.objects.get(id=job_ids[0])
        drone_set = job.drone_set
        if not drone_set:
            return self._user_or_global_default_drone_set(job, job.user())

        return drone_set.get_drone_hostnames()


    def _user_or_global_default_drone_set(self, obj_with_owner, user):
        """
        Returns the user's default drone set, if present.

        Otherwise, returns the global default drone set.
        """
        default_hostnames = models.DroneSet.get_default().get_drone_hostnames()
        if not user:
            logging.warn('%s had no owner; using default drone set',
                         obj_with_owner)
            return default_hostnames
        if not user.drone_set:
            logging.warn('User %s has no default drone set, using global '
                         'default', user.login)
            return default_hostnames
        return user.drone_set.get_drone_hostnames()


    def register_necessary_pidfiles(self):
        pidfile_id = _drone_manager.get_pidfile_id_from(
                self._working_directory(), self._pidfile_name())
        _drone_manager.register_pidfile(pidfile_id)

        paired_pidfile_id = self._paired_with_monitor().pidfile_id
        if paired_pidfile_id:
            _drone_manager.register_pidfile(paired_pidfile_id)


    def recover(self):
        if not self._check_paired_results_exist():
            return

        self._create_monitor()
        self.monitor.attach_to_existing_process(
                self._working_directory(), pidfile_name=self._pidfile_name(),
                num_processes=self.num_processes)
        if not self.monitor.has_process():
            # no process to recover; wait to be started normally
            self.monitor = None
            return

        self.started = True
        logging.info('Recovering process %s for %s at %s',
                     self.monitor.get_process(), type(self).__name__,
                     self._working_directory())


    def _check_queue_entry_statuses(self, queue_entries, allowed_hqe_statuses,
                                    allowed_host_statuses=None):
        class_name = self.__class__.__name__
        for entry in queue_entries:
            if entry.status not in allowed_hqe_statuses:
                raise host_scheduler.SchedulerError(
                        '%s attempting to start entry with invalid status %s: '
                        '%s' % (class_name, entry.status, entry))
            invalid_host_status = (
                    allowed_host_statuses is not None
                    and entry.host.status not in allowed_host_statuses)
            if invalid_host_status:
                raise host_scheduler.SchedulerError(
                        '%s attempting to start on queue entry with invalid '
                        'host status %s: %s'
                        % (class_name, entry.host.status, entry))


SiteAgentTask = utils.import_site_class(
    __file__, 'autotest_lib.scheduler.site_monitor_db',
    'SiteAgentTask', BaseAgentTask)

class AgentTask(SiteAgentTask):
    pass


class TaskWithJobKeyvals(object):
    """AgentTask mixin providing functionality to help with job keyval files."""
    _KEYVAL_FILE = 'keyval'
    def _format_keyval(self, key, value):
        return '%s=%s' % (key, value)


    def _keyval_path(self):
        """Subclasses must override this"""
        raise NotImplementedError


    def _write_keyval_after_job(self, field, value):
        assert self.monitor
        if not self.monitor.has_process():
            return
        _drone_manager.write_lines_to_file(
            self._keyval_path(), [self._format_keyval(field, value)],
            paired_with_process=self.monitor.get_process())


    def _job_queued_keyval(self, job):
        return 'job_queued', int(time.mktime(job.created_on.timetuple()))


    def _write_job_finished(self):
        self._write_keyval_after_job("job_finished", int(time.time()))


    def _write_keyvals_before_job_helper(self, keyval_dict, keyval_path):
        keyval_contents = '\n'.join(self._format_keyval(key, value)
                                    for key, value in keyval_dict.iteritems())
        # always end with a newline to allow additional keyvals to be written
        keyval_contents += '\n'
        _drone_manager.attach_file_to_execution(self._working_directory(),
                                                keyval_contents,
                                                file_path=keyval_path)


    def _write_keyvals_before_job(self, keyval_dict):
        self._write_keyvals_before_job_helper(keyval_dict, self._keyval_path())


    def _write_host_keyvals(self, host):
        keyval_path = os.path.join(self._working_directory(), 'host_keyvals',
                                   host.hostname)
        platform, all_labels = host.platform_and_labels()
        all_labels = [ urllib.quote(label) for label in all_labels ]
        keyval_dict = dict(platform=platform, labels=','.join(all_labels))
        self._write_keyvals_before_job_helper(keyval_dict, keyval_path)


class SpecialAgentTask(AgentTask, TaskWithJobKeyvals):
    """
    Subclass for AgentTasks that correspond to a SpecialTask entry in the DB.
    """

    TASK_TYPE = None
    host = None
    queue_entry = None

    def __init__(self, task, extra_command_args):
        super(SpecialAgentTask, self).__init__()

        assert self.TASK_TYPE is not None, 'self.TASK_TYPE must be overridden'

        self.host = scheduler_models.Host(id=task.host.id)
        self.queue_entry = None
        if task.queue_entry:
            self.queue_entry = scheduler_models.HostQueueEntry(
                    id=task.queue_entry.id)

        self.task = task
        self._extra_command_args = extra_command_args


    def _keyval_path(self):
        return os.path.join(self._working_directory(), self._KEYVAL_FILE)


    def _command_line(self):
        return _autoserv_command_line(self.host.hostname,
                                      self._extra_command_args,
                                      queue_entry=self.queue_entry)


    def _working_directory(self):
        return self.task.execution_path()


    @property
    def owner_username(self):
        if self.task.requested_by:
            return self.task.requested_by.login
        return None


    def prolog(self):
        super(SpecialAgentTask, self).prolog()
        self.task.activate()
        self._write_host_keyvals(self.host)


    def _fail_queue_entry(self):
        assert self.queue_entry

        if self.queue_entry.meta_host:
            return # don't fail metahost entries, they'll be reassigned

        self.queue_entry.update_from_database()
        if self.queue_entry.status != models.HostQueueEntry.Status.QUEUED:
            return # entry has been aborted

        self._actually_fail_queue_entry()


    # TODO(milleral): http://crbug.com/268607
    # All this used to be a part of _fail_queue_entry.  The
    # exact semantics of when one should and should not be failing a queue
    # entry need to be worked out, because provisioning has placed us in a
    # case where we want to fail a queue entry that could be requeued,
    # which makes us fail the two above if statements, and thus
    # _fail_queue_entry() would exit early and have no effect.
    # What's left here with _actually_fail_queue_entry is a hack to be able to
    # bypass the checks and unconditionally execute the code.
    def _actually_fail_queue_entry(self):
        self.queue_entry.set_execution_subdir()
        queued_key, queued_time = self._job_queued_keyval(
            self.queue_entry.job)
        self._write_keyval_after_job(queued_key, queued_time)
        self._write_job_finished()

        # copy results logs into the normal place for job results
        self.monitor.try_copy_results_on_drone(
                source_path=self._working_directory() + '/',
                destination_path=self.queue_entry.execution_path() + '/')

        pidfile_id = _drone_manager.get_pidfile_id_from(
                self.queue_entry.execution_path(),
                pidfile_name=drone_manager.AUTOSERV_PID_FILE)
        _drone_manager.register_pidfile(pidfile_id)

        if self.queue_entry.job.parse_failed_repair:
            self._parse_results([self.queue_entry])
        else:
            self._archive_results([self.queue_entry])

        # Also fail all other special tasks that have not yet run for this HQE
        pending_tasks = models.SpecialTask.objects.filter(
                queue_entry__id=self.queue_entry.id,
                is_complete=0)
        for task in pending_tasks:
            task.finish(False)


    def cleanup(self):
        super(SpecialAgentTask, self).cleanup()

        # We will consider an aborted task to be "Failed"
        self.task.finish(bool(self.success))

        if self.monitor:
            if self.monitor.has_process():
                self._copy_results([self.task])
            if self.monitor.pidfile_id is not None:
                _drone_manager.unregister_pidfile(self.monitor.pidfile_id)


    def remove_special_tasks(self, special_task_to_remove, keep_last_one=False):
        """Remove a type of special task in all tasks, keep last one if needed.

        @param special_task_to_remove: type of special task to be removed, e.g.,
            models.SpecialTask.Task.VERIFY.
        @param keep_last_one: True to keep the last special task if its type is
            the same as of special_task_to_remove.

        """
        queued_special_tasks = models.SpecialTask.objects.filter(
            host__id=self.host.id,
            task=special_task_to_remove,
            is_active=False, is_complete=False, queue_entry=None)
        if keep_last_one:
            queued_special_tasks = queued_special_tasks.exclude(id=self.task.id)
        queued_special_tasks.delete()


class RepairTask(SpecialAgentTask):
    TASK_TYPE = models.SpecialTask.Task.REPAIR


    def __init__(self, task):
        """\
        queue_entry: queue entry to mark failed if this repair fails.
        """
        protection = host_protections.Protection.get_string(
                task.host.protection)
        # normalize the protection name
        protection = host_protections.Protection.get_attr_name(protection)

        super(RepairTask, self).__init__(
                task, ['-R', '--host-protection', protection])

        # *don't* include the queue entry in IDs -- if the queue entry is
        # aborted, we want to leave the repair task running
        self._set_ids(host=self.host)


    def prolog(self):
        super(RepairTask, self).prolog()
        logging.info("repair_task starting")
        self.host.set_status(models.Host.Status.REPAIRING)


    def epilog(self):
        super(RepairTask, self).epilog()

        if self.success:
            self.host.set_status(models.Host.Status.READY)
        else:
            self.host.set_status(models.Host.Status.REPAIR_FAILED)
            if self.queue_entry:
                self._fail_queue_entry()


class PreJobTask(SpecialAgentTask):
    def _copy_to_results_repository(self):
        if not self.queue_entry or self.queue_entry.meta_host:
            return

        self.queue_entry.set_execution_subdir()
        log_name = os.path.basename(self.task.execution_path())
        source = os.path.join(self.task.execution_path(), 'debug',
                              'autoserv.DEBUG')
        destination = os.path.join(
                self.queue_entry.execution_path(), log_name)

        self.monitor.try_copy_to_results_repository(
                source, destination_path=destination)


    def epilog(self):
        super(PreJobTask, self).epilog()

        if self.success:
            return

        self._copy_to_results_repository()

        if self.host.protection == host_protections.Protection.DO_NOT_VERIFY:
            # effectively ignore failure for these hosts
            self.success = True
            return

        if self.queue_entry:
            self.queue_entry.requeue()
            # If we requeue a HQE, we should cancel any remaining pre-job
            # tasks against this host, otherwise we'll be left in a state
            # where a queued HQE has special tasks to run against a host.
            models.SpecialTask.objects.filter(
                    queue_entry__id=self.queue_entry.id,
                    host__id=self.host.id,
                    is_complete=0).update(is_complete=1, success=0)

            if models.SpecialTask.objects.filter(
                    task=models.SpecialTask.Task.REPAIR,
                    queue_entry__id=self.queue_entry.id):
                self.host.set_status(models.Host.Status.REPAIR_FAILED)
                self._fail_queue_entry()
                return

            queue_entry = models.HostQueueEntry.objects.get(
                    id=self.queue_entry.id)
        else:
            queue_entry = None

        models.SpecialTask.objects.create(
                host=models.Host.objects.get(id=self.host.id),
                task=models.SpecialTask.Task.REPAIR,
                queue_entry=queue_entry,
                requested_by=self.task.requested_by)


    def _should_pending(self):
        """
        Decide if we should call the host queue entry's on_pending method.
        We should if:
        1) There exists an associated host queue entry.
        2) The current special task completed successfully.
        3) There do not exist any more special tasks to be run before the
           host queue entry starts.

        @returns: True if we should call pending, false if not.

        """
        if not self.queue_entry or not self.success:
            return False

        # We know if this is the last one when we create it, so we could add
        # another column to the database to keep track of this information, but
        # I expect the overhead of querying here to be minimal.
        queue_entry = models.HostQueueEntry.objects.get(id=self.queue_entry.id)
        queued = models.SpecialTask.objects.filter(
                host__id=self.host.id, is_active=False,
                is_complete=False, queue_entry=queue_entry)
        queued = queued.exclude(id=self.task.id)
        return queued.count() == 0


class VerifyTask(PreJobTask):
    TASK_TYPE = models.SpecialTask.Task.VERIFY


    def __init__(self, task):
        super(VerifyTask, self).__init__(task, ['-v'])
        self._set_ids(host=self.host, queue_entries=[self.queue_entry])


    def prolog(self):
        super(VerifyTask, self).prolog()

        logging.info("starting verify on %s", self.host.hostname)
        if self.queue_entry:
            self.queue_entry.set_status(models.HostQueueEntry.Status.VERIFYING)
        self.host.set_status(models.Host.Status.VERIFYING)

        # Delete any queued manual reverifies for this host.  One verify will do
        # and there's no need to keep records of other requests.
        self.remove_special_tasks(models.SpecialTask.Task.VERIFY,
                                  keep_last_one=True)


    def epilog(self):
        super(VerifyTask, self).epilog()
        if self.success:
            if self._should_pending():
                self.queue_entry.on_pending()
            else:
                self.host.set_status(models.Host.Status.READY)


class CleanupTask(PreJobTask):
    # note this can also run post-job, but when it does, it's running standalone
    # against the host (not related to the job), so it's not considered a
    # PostJobTask

    TASK_TYPE = models.SpecialTask.Task.CLEANUP


    def __init__(self, task, recover_run_monitor=None):
        super(CleanupTask, self).__init__(task, ['--cleanup'])
        self._set_ids(host=self.host, queue_entries=[self.queue_entry])


    def prolog(self):
        super(CleanupTask, self).prolog()
        logging.info("starting cleanup task for host: %s", self.host.hostname)
        self.host.set_status(models.Host.Status.CLEANING)
        if self.queue_entry:
            self.queue_entry.set_status(models.HostQueueEntry.Status.CLEANING)


    def _finish_epilog(self):
        if not self.queue_entry or not self.success:
            return

        do_not_verify_protection = host_protections.Protection.DO_NOT_VERIFY
        should_run_verify = (
                self.queue_entry.job.run_verify
                and self.host.protection != do_not_verify_protection)
        if should_run_verify:
            entry = models.HostQueueEntry.objects.get(id=self.queue_entry.id)
            models.SpecialTask.objects.create(
                    host=models.Host.objects.get(id=self.host.id),
                    queue_entry=entry,
                    task=models.SpecialTask.Task.VERIFY)
        else:
            if self._should_pending():
                self.queue_entry.on_pending()


    def epilog(self):
        super(CleanupTask, self).epilog()

        if self.success:
            self.host.update_field('dirty', 0)
            self.host.set_status(models.Host.Status.READY)

        self._finish_epilog()


class ResetTask(PreJobTask):
    """Task to reset a DUT, including cleanup and verify."""
    # note this can also run post-job, but when it does, it's running standalone
    # against the host (not related to the job), so it's not considered a
    # PostJobTask

    TASK_TYPE = models.SpecialTask.Task.RESET


    def __init__(self, task, recover_run_monitor=None):
        super(ResetTask, self).__init__(task, ['--reset'])
        self._set_ids(host=self.host, queue_entries=[self.queue_entry])


    def prolog(self):
        super(ResetTask, self).prolog()
        logging.info('starting reset task for host: %s',
                     self.host.hostname)
        self.host.set_status(models.Host.Status.RESETTING)
        if self.queue_entry:
            self.queue_entry.set_status(models.HostQueueEntry.Status.RESETTING)

        # Delete any queued cleanups for this host.
        self.remove_special_tasks(models.SpecialTask.Task.CLEANUP,
                                  keep_last_one=False)

        # Delete any queued reverifies for this host.
        self.remove_special_tasks(models.SpecialTask.Task.VERIFY,
                                  keep_last_one=False)

        # Only one reset is needed.
        self.remove_special_tasks(models.SpecialTask.Task.RESET,
                                  keep_last_one=True)


    def epilog(self):
        super(ResetTask, self).epilog()

        if self.success:
            self.host.update_field('dirty', 0)

            if self._should_pending():
                self.queue_entry.on_pending()
            else:
                self.host.set_status(models.Host.Status.READY)


class ProvisionTask(PreJobTask):
    TASK_TYPE = models.SpecialTask.Task.PROVISION

    def __init__(self, task):
        # Provisioning requires that we be associated with a job/queue entry
        assert task.queue_entry, "No HQE associated with provision task!"
        # task.queue_entry is an afe model HostQueueEntry object.
        # self.queue_entry is a scheduler models HostQueueEntry object, but
        # it gets constructed and assigned in __init__, so it's not available
        # yet.  Therefore, we're stuck pulling labels off of the afe model
        # so that we can pass the --provision args into the __init__ call.
        labels = {x.name for x in task.queue_entry.job.dependency_labels.all()}
        _, provisionable = provision.filter_labels(labels)
        extra_command_args = ['--provision', ','.join(provisionable)]
        super(ProvisionTask, self).__init__(task, extra_command_args)
        self._set_ids(host=self.host, queue_entries=[self.queue_entry])


    def _command_line(self):
        # If we give queue_entry to _autoserv_command_line, then it will append
        # -c for this invocation if the queue_entry is a client side test. We
        # don't want that, as it messes with provisioning, so we just drop it
        # from the arguments here.
        # Note that we also don't verify job_repo_url as provisioining tasks are
        # required to stage whatever content we need, and the job itself will
        # force autotest to be staged if it isn't already.
        return _autoserv_command_line(self.host.hostname,
                                      self._extra_command_args)


    def prolog(self):
        super(ProvisionTask, self).prolog()
        # add check for previous provision task and abort if exist.
        logging.info("starting provision task for host: %s", self.host.hostname)
        self.queue_entry.set_status(
                models.HostQueueEntry.Status.PROVISIONING)
        self.host.set_status(models.Host.Status.PROVISIONING)


    def epilog(self):
        # TODO(milleral) Here, we override the PreJobTask's epilog, because
        # it's written with the idea that pre-job special task failures are a
        # problem with the host and not with something about the HQE.
        # In our case, the HQE's DEPENDENCIES specify what the provision task
        # does, so if the provision fails, it can be the fault of the HQE, and
        # thus we fail the HQE.  This difference is handled only here for now,
        # but some refactoring of PreJobTask should likely happen sometime in
        # the future?
        # This call is needed to log the status and call into self.cleanup(),
        # which is PreJobTasks's cleanup, which marks is_complete=1.
        AgentTask.epilog(self)

        if not self.success:
            # TODO(milleral) http://crbug.com/231452
            # In our own setup, we don't really use the results
            # repository, so I *think* this call can be elided.  However, I'd
            # like to limit what I can possibly break for now, and it would be
            # called if I called PreJobTask's epilog, so I'm keeping the call
            # to it for now.
            self._copy_to_results_repository()
            # _actually_fail_queue_entry() is a hack around the fact that we do
            # indeed want to abort the queue entry here, but the rest of the
            # scheduler code expects that we will reschedule onto some other
            # host.
            self._actually_fail_queue_entry()
            # This abort will mark the aborted bit on the HQE itself, to
            # signify that we're killing it.  Technically it also will do
            # the recursive aborting of all child jobs, but that shouldn't
            # matter here, as only suites have children, and those
            # are hostless and thus don't have provisioning.
            # TODO(milleral) http://crbug.com/188217
            # However, we can't actually do this yet, as if we set the abort bit
            # the FinalReparseTask will set the status of the HQE to ABORTED,
            # which then means that we don't show the status in run_suite.
            # So in the meantime, don't mark the HQE as aborted.
            queue_entry = models.HostQueueEntry.objects.get(
                    id=self.queue_entry.id)
            # queue_entry.abort()

            # The machine is in some totally unknown state, so let's kick off
            # a repair task to get it back to some known sane state.
            models.SpecialTask.objects.create(
                    host=models.Host.objects.get(id=self.host.id),
                    task=models.SpecialTask.Task.REPAIR,
                    queue_entry=queue_entry,
                    requested_by=self.task.requested_by)
        elif self._should_pending():
            self.queue_entry.on_pending()
        else:
            self.host.set_status(models.Host.Status.READY)


class AbstractQueueTask(AgentTask, TaskWithJobKeyvals):
    """
    Common functionality for QueueTask and HostlessQueueTask
    """
    def __init__(self, queue_entries):
        super(AbstractQueueTask, self).__init__()
        self.job = queue_entries[0].job
        self.queue_entries = queue_entries


    def _keyval_path(self):
        return os.path.join(self._working_directory(), self._KEYVAL_FILE)


    def _write_control_file(self, execution_path):
        control_path = _drone_manager.attach_file_to_execution(
                execution_path, self.job.control_file)
        return control_path


    # TODO: Refactor into autoserv_utils. crbug.com/243090
    def _command_line(self):
        execution_path = self.queue_entries[0].execution_path()
        control_path = self._write_control_file(execution_path)
        hostnames = ','.join(entry.host.hostname
                             for entry in self.queue_entries
                             if not entry.is_hostless())

        execution_tag = self.queue_entries[0].execution_tag()
        params = _autoserv_command_line(
            hostnames,
            ['-P', execution_tag, '-n',
             _drone_manager.absolute_path(control_path)],
            job=self.job, verbose=False)
        if self.job.is_image_update_job():
            params += ['--image', self.job.update_image_path]

        return params


    @property
    def num_processes(self):
        return len(self.queue_entries)


    @property
    def owner_username(self):
        return self.job.owner


    def _working_directory(self):
        return self._get_consistent_execution_path(self.queue_entries)


    def prolog(self):
        queued_key, queued_time = self._job_queued_keyval(self.job)
        keyval_dict = self.job.keyval_dict()
        keyval_dict[queued_key] = queued_time
        group_name = self.queue_entries[0].get_group_name()
        if group_name:
            keyval_dict['host_group_name'] = group_name
        self._write_keyvals_before_job(keyval_dict)
        for queue_entry in self.queue_entries:
            queue_entry.set_status(models.HostQueueEntry.Status.RUNNING)
            queue_entry.set_started_on_now()


    def _write_lost_process_error_file(self):
        error_file_path = os.path.join(self._working_directory(), 'job_failure')
        _drone_manager.write_lines_to_file(error_file_path,
                                           [_LOST_PROCESS_ERROR])


    def _finish_task(self):
        if not self.monitor:
            return

        self._write_job_finished()

        if self.monitor.lost_process:
            self._write_lost_process_error_file()


    def _write_status_comment(self, comment):
        _drone_manager.write_lines_to_file(
            os.path.join(self._working_directory(), 'status.log'),
            ['INFO\t----\t----\t' + comment],
            paired_with_process=self.monitor.get_process())


    def _log_abort(self):
        if not self.monitor or not self.monitor.has_process():
            return

        # build up sets of all the aborted_by and aborted_on values
        aborted_by, aborted_on = set(), set()
        for queue_entry in self.queue_entries:
            if queue_entry.aborted_by:
                aborted_by.add(queue_entry.aborted_by)
                t = int(time.mktime(queue_entry.aborted_on.timetuple()))
                aborted_on.add(t)

        # extract some actual, unique aborted by value and write it out
        # TODO(showard): this conditional is now obsolete, we just need to leave
        # it in temporarily for backwards compatibility over upgrades.  delete
        # soon.
        assert len(aborted_by) <= 1
        if len(aborted_by) == 1:
            aborted_by_value = aborted_by.pop()
            aborted_on_value = max(aborted_on)
        else:
            aborted_by_value = 'autotest_system'
            aborted_on_value = int(time.time())

        self._write_keyval_after_job("aborted_by", aborted_by_value)
        self._write_keyval_after_job("aborted_on", aborted_on_value)

        aborted_on_string = str(datetime.datetime.fromtimestamp(
            aborted_on_value))
        self._write_status_comment('Job aborted by %s on %s' %
                                   (aborted_by_value, aborted_on_string))


    def abort(self):
        super(AbstractQueueTask, self).abort()
        self._log_abort()
        self._finish_task()


    def epilog(self):
        super(AbstractQueueTask, self).epilog()
        self._finish_task()


class QueueTask(AbstractQueueTask):
    def __init__(self, queue_entries):
        super(QueueTask, self).__init__(queue_entries)
        self._set_ids(queue_entries=queue_entries)


    def prolog(self):
        self._check_queue_entry_statuses(
                self.queue_entries,
                allowed_hqe_statuses=(models.HostQueueEntry.Status.STARTING,
                                      models.HostQueueEntry.Status.RUNNING),
                allowed_host_statuses=(models.Host.Status.PENDING,
                                       models.Host.Status.RUNNING))

        super(QueueTask, self).prolog()

        for queue_entry in self.queue_entries:
            self._write_host_keyvals(queue_entry.host)
            queue_entry.host.set_status(models.Host.Status.RUNNING)
            queue_entry.host.update_field('dirty', 1)


    def _finish_task(self):
        super(QueueTask, self)._finish_task()

        for queue_entry in self.queue_entries:
            queue_entry.set_status(models.HostQueueEntry.Status.GATHERING)
            queue_entry.host.set_status(models.Host.Status.RUNNING)


    def _command_line(self):
         invocation = super(QueueTask, self)._command_line()
         return invocation + ['--verify_job_repo_url']


class HostlessQueueTask(AbstractQueueTask):
    def __init__(self, queue_entry):
        super(HostlessQueueTask, self).__init__([queue_entry])
        self.queue_entry_ids = [queue_entry.id]


    def prolog(self):
        self.queue_entries[0].update_field('execution_subdir', 'hostless')
        super(HostlessQueueTask, self).prolog()


    def _finish_task(self):
        super(HostlessQueueTask, self)._finish_task()
        self.queue_entries[0].set_status(models.HostQueueEntry.Status.PARSING)


class PostJobTask(AgentTask):
    def __init__(self, queue_entries, log_file_name):
        super(PostJobTask, self).__init__(log_file_name=log_file_name)

        self.queue_entries = queue_entries

        self._autoserv_monitor = PidfileRunMonitor()
        self._autoserv_monitor.attach_to_existing_process(
                self._working_directory())


    def _command_line(self):
        if _testing_mode:
            return 'true'
        return self._generate_command(
                _drone_manager.absolute_path(self._working_directory()))


    def _generate_command(self, results_dir):
        raise NotImplementedError('Subclasses must override this')


    @property
    def owner_username(self):
        return self.queue_entries[0].job.owner


    def _working_directory(self):
        return self._get_consistent_execution_path(self.queue_entries)


    def _paired_with_monitor(self):
        return self._autoserv_monitor


    def _job_was_aborted(self):
        was_aborted = None
        for queue_entry in self.queue_entries:
            queue_entry.update_from_database()
            if was_aborted is None: # first queue entry
                was_aborted = bool(queue_entry.aborted)
            elif was_aborted != bool(queue_entry.aborted): # subsequent entries
                entries = ['%s (aborted: %s)' % (entry, entry.aborted)
                           for entry in self.queue_entries]
                email_manager.manager.enqueue_notify_email(
                        'Inconsistent abort state',
                        'Queue entries have inconsistent abort state:\n' +
                        '\n'.join(entries))
                # don't crash here, just assume true
                return True
        return was_aborted


    def _final_status(self):
        if self._job_was_aborted():
            return models.HostQueueEntry.Status.ABORTED

        # we'll use a PidfileRunMonitor to read the autoserv exit status
        if self._autoserv_monitor.exit_code() == 0:
            return models.HostQueueEntry.Status.COMPLETED
        return models.HostQueueEntry.Status.FAILED


    def _set_all_statuses(self, status):
        for queue_entry in self.queue_entries:
            queue_entry.set_status(status)


    def abort(self):
        # override AgentTask.abort() to avoid killing the process and ending
        # the task.  post-job tasks continue when the job is aborted.
        pass


    def _pidfile_label(self):
        # '.autoserv_execute' -> 'autoserv'
        return self._pidfile_name()[1:-len('_execute')]


class GatherLogsTask(PostJobTask):
    """
    Task responsible for
    * gathering uncollected logs (if Autoserv crashed hard or was killed)
    * copying logs to the results repository
    * spawning CleanupTasks for hosts, if necessary
    * spawning a FinalReparseTask for the job
    """
    def __init__(self, queue_entries, recover_run_monitor=None):
        self._job = queue_entries[0].job
        super(GatherLogsTask, self).__init__(
            queue_entries, log_file_name='.collect_crashinfo.log')
        self._set_ids(queue_entries=queue_entries)


    # TODO: Refactor into autoserv_utils. crbug.com/243090
    def _generate_command(self, results_dir):
        host_list = ','.join(queue_entry.host.hostname
                             for queue_entry in self.queue_entries)
        return [_autoserv_path , '-p',
                '--pidfile-label=%s' % self._pidfile_label(),
                '--use-existing-results', '--collect-crashinfo',
                '-m', host_list, '-r', results_dir]


    @property
    def num_processes(self):
        return len(self.queue_entries)


    def _pidfile_name(self):
        return drone_manager.CRASHINFO_PID_FILE


    def prolog(self):
        self._check_queue_entry_statuses(
                self.queue_entries,
                allowed_hqe_statuses=(models.HostQueueEntry.Status.GATHERING,),
                allowed_host_statuses=(models.Host.Status.RUNNING,))

        super(GatherLogsTask, self).prolog()


    def epilog(self):
        super(GatherLogsTask, self).epilog()
        self._parse_results(self.queue_entries)
        self._reboot_hosts()


    def _reboot_hosts(self):
        if self._autoserv_monitor.has_process():
            final_success = (self._final_status() ==
                             models.HostQueueEntry.Status.COMPLETED)
            num_tests_failed = self._autoserv_monitor.num_tests_failed()
        else:
            final_success = False
            num_tests_failed = 0
        reboot_after = self._job.reboot_after
        do_reboot = (
                # always reboot after aborted jobs
                self._final_status() == models.HostQueueEntry.Status.ABORTED
                or reboot_after == model_attributes.RebootAfter.ALWAYS
                or (reboot_after == model_attributes.RebootAfter.IF_ALL_TESTS_PASSED
                    and final_success and num_tests_failed == 0)
                or num_tests_failed > 0)

        for queue_entry in self.queue_entries:
            if do_reboot:
                # don't pass the queue entry to the CleanupTask. if the cleanup
                # fails, the job doesn't care -- it's over.
                models.SpecialTask.objects.create(
                        host=models.Host.objects.get(id=queue_entry.host.id),
                        task=models.SpecialTask.Task.CLEANUP,
                        requested_by=self._job.owner_model())
            else:
                queue_entry.host.set_status(models.Host.Status.READY)


    def run(self):
        autoserv_exit_code = self._autoserv_monitor.exit_code()
        # only run if Autoserv exited due to some signal. if we have no exit
        # code, assume something bad (and signal-like) happened.
        if autoserv_exit_code is None or os.WIFSIGNALED(autoserv_exit_code):
            super(GatherLogsTask, self).run()
        else:
            self.finished(True)


class SelfThrottledPostJobTask(PostJobTask):
    """
    Special AgentTask subclass that maintains its own global process limit.
    """
    _num_running_processes = 0


    @classmethod
    def _increment_running_processes(cls):
        cls._num_running_processes += 1


    @classmethod
    def _decrement_running_processes(cls):
        cls._num_running_processes -= 1


    @classmethod
    def _max_processes(cls):
        raise NotImplementedError


    @classmethod
    def _can_run_new_process(cls):
        return cls._num_running_processes < cls._max_processes()


    def _process_started(self):
        return bool(self.monitor)


    def tick(self):
        # override tick to keep trying to start until the process count goes
        # down and we can, at which point we revert to default behavior
        if self._process_started():
            super(SelfThrottledPostJobTask, self).tick()
        else:
            self._try_starting_process()


    def run(self):
        # override run() to not actually run unless we can
        self._try_starting_process()


    def _try_starting_process(self):
        if not self._can_run_new_process():
            return

        # actually run the command
        super(SelfThrottledPostJobTask, self).run()
        if self._process_started():
            self._increment_running_processes()


    def finished(self, success):
        super(SelfThrottledPostJobTask, self).finished(success)
        if self._process_started():
            self._decrement_running_processes()


class FinalReparseTask(SelfThrottledPostJobTask):
    def __init__(self, queue_entries):
        super(FinalReparseTask, self).__init__(queue_entries,
                                               log_file_name='.parse.log')
        # don't use _set_ids, since we don't want to set the host_ids
        self.queue_entry_ids = [entry.id for entry in queue_entries]


    def _generate_command(self, results_dir):
        return [_parser_path, '--write-pidfile', '-l', '2', '-r', '-o',
                results_dir]


    @property
    def num_processes(self):
        return 0 # don't include parser processes in accounting


    def _pidfile_name(self):
        return drone_manager.PARSER_PID_FILE


    @classmethod
    def _max_processes(cls):
        return scheduler_config.config.max_parse_processes


    def prolog(self):
        self._check_queue_entry_statuses(
                self.queue_entries,
                allowed_hqe_statuses=(models.HostQueueEntry.Status.PARSING,))

        super(FinalReparseTask, self).prolog()


    def epilog(self):
        super(FinalReparseTask, self).epilog()
        self._archive_results(self.queue_entries)


class ArchiveResultsTask(SelfThrottledPostJobTask):
    _ARCHIVING_FAILED_FILE = '.archiver_failed'

    def __init__(self, queue_entries):
        super(ArchiveResultsTask, self).__init__(queue_entries,
                                                 log_file_name='.archiving.log')
        # don't use _set_ids, since we don't want to set the host_ids
        self.queue_entry_ids = [entry.id for entry in queue_entries]


    def _pidfile_name(self):
        return drone_manager.ARCHIVER_PID_FILE


    # TODO: Refactor into autoserv_utils. crbug.com/243090
    def _generate_command(self, results_dir):
        return [_autoserv_path , '-p',
                '--pidfile-label=%s' % self._pidfile_label(), '-r', results_dir,
                '--use-existing-results', '--control-filename=control.archive',
                os.path.join(drones.AUTOTEST_INSTALL_DIR, 'scheduler',
                             'archive_results.control.srv')]


    @classmethod
    def _max_processes(cls):
        return scheduler_config.config.max_transfer_processes


    def prolog(self):
        self._check_queue_entry_statuses(
                self.queue_entries,
                allowed_hqe_statuses=(models.HostQueueEntry.Status.ARCHIVING,))

        super(ArchiveResultsTask, self).prolog()


    def epilog(self):
        super(ArchiveResultsTask, self).epilog()
        if not self.success and self._paired_with_monitor().has_process():
            failed_file = os.path.join(self._working_directory(),
                                       self._ARCHIVING_FAILED_FILE)
            paired_process = self._paired_with_monitor().get_process()
            _drone_manager.write_lines_to_file(
                    failed_file, ['Archiving failed with exit code %s'
                                  % self.monitor.exit_code()],
                    paired_with_process=paired_process)
        self._set_all_statuses(self._final_status())


if __name__ == '__main__':
    main()
