# Copyright (c) 2011 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""
Utility classes used by server_job.distribute_across_machines().

test_item: extends the basic test tuple to add include/exclude attributes.

machine_worker: is a thread that manages running tests on a host.  It
    verifies test are valid for a host using the test attributes from test_item
    and the host attributes from host_attributes.
"""


import logging, os, Queue, threading
from autotest_lib.client.common_lib import error, utils
from autotest_lib.server import autotest, hosts, host_attributes, subcommand


class test_item(object):
    """Adds machine verification logic to the basic test tuple.

    Tests can either be tuples of the existing form ('testName', {args}) or the
    extended for of ('testname', {args}, ['include'], ['exclude']) where include
    and exclude are lists of attributes. A machine must have all the attributes
    in include and must not have any of the attributes in exclude to be valid
    for the test.
    """

    def __init__(self, test_name, test_args, include_attribs=None,
                 exclude_attribs=None):
        """Creates an instance of test_item.

        Args:
            test_name: string, name of test to execute.
            test_args: dictionary, arguments to pass into test.
            include_attribs: attributes a machine must have to run test.
            exclude_attribs: attributes preventing a machine from running test.
        """
        self.test_name = test_name
        self.test_args = test_args
        self.inc_set = None
        if include_attribs is not None:
            self.inc_set = set(include_attribs)
        self.exc_set = None
        if exclude_attribs is not None:
            self.exc_set = set(exclude_attribs)

    def __str__(self):
        """Return an info string of this test."""
        params = ['%s=%s' % (k, v) for k, v in self.test_args.items()]
        msg = '%s(%s)' % (self.test_name, params)
        if self.inc_set: msg += ' include=%s' % [s for s in self.inc_set]
        if self.exc_set: msg += ' exclude=%s' % [s for s in self.exc_set]
        return msg

    def validate(self, machine_attributes):
        """Check if this test can run on machine with machine_attributes.

        If the test has include attributes, a candidate machine must have all
        the attributes to be valid.

        If the test has exclude attributes, a candidate machine cannot have any
        of the attributes to be valid.

        Args:
            machine_attributes: set, True attributes of candidate machine.

        Returns:
            True/False if the machine is valid for this test.
        """
        if self.inc_set is not None:
            if not self.inc_set <= machine_attributes: return False
        if self.exc_set is not None:
            if self.exc_set & machine_attributes: return False
        return True


class machine_worker(threading.Thread):
    """Thread that runs tests on a remote host machine."""

    def __init__(self, server_job, machine, work_dir, test_queue, queue_lock):
        """Creates an instance of machine_worker to run tests on a remote host.

        Retrieves that host attributes for this machine and creates the set of
        True attributes to validate against test include/exclude attributes.

        Creates a directory to hold the log files for tests run and writes the
        hostname and tko parser version into keyvals file.

        Args:
            server_job: run tests for this server_job.
            machine: name of remote host.
            work_dir: directory server job is using.
            test_queue: queue of tests.
            queue_lock: lock protecting test_queue.
        """
        threading.Thread.__init__(self)
        self._server_job = server_job
        self._test_queue = test_queue
        self._test_queue_lock = queue_lock
        self._tests_run = 0
        self._machine = machine
        self._host = hosts.create_host(self._machine)
        self._client_at = autotest.Autotest(self._host)
        client_attributes = host_attributes.host_attributes(machine)
        self.attribute_set = set([key for key, value in
                                  client_attributes.__dict__.items() if value])
        self._results_dir = os.path.join(work_dir, self._machine)
        if not os.path.exists(self._results_dir):
            os.makedirs(self._results_dir)
        machine_data = {'hostname': self._machine,
                        'status_version': str(1)}
        utils.write_keyval(self._results_dir, machine_data)

    def __str__(self):
        attributes = [a for a in self.attribute_set]
        return '%s attributes=%s' % (self._machine, attributes)

    def get_test(self):
        """Return a test from the queue to run on this host.

        The test queue can be non-empty, but still not contain a test that is
        valid for this machine. This function will take exclusive access to
        the queue via _test_queue_lock and repeatedly pop tests off the queue
        until finding a valid test or depleting the queue.  In either case if
        invalid tests have been popped from the queue, they are pushed back
        onto the queue before returning.

        Returns:
            test_item, or None if no more tests exist for this machine.
        """
        good_test = None
        skipped_tests = []

        with self._test_queue_lock:
            while True:
                try:
                    canidate_test = self._test_queue.get_nowait()
                    # Check if test is valid for this machine.
                    if canidate_test.validate(self.attribute_set):
                        good_test = canidate_test
                        break
                    skipped_tests.append(canidate_test)

                except Queue.Empty:
                    break

            # Return any skipped tests to the queue.
            for st in skipped_tests:
                self._test_queue.put(st)

        return good_test

    def run_subcommand(self, active_test):
        """Use subcommand to fork process and execute test."""
        sub_cmd = subcommand.subcommand(self.subcommand_wrapper,
                                        [active_test],
                                        self._results_dir)
        sub_cmd.fork_start()
        sub_cmd.fork_waitfor()

    def subcommand_wrapper(self, active_test):
        """Callback for subcommand to call into with the test parameter.

        When this function executes it has forked from the main process so it
        is safe to modify state on the server_job object. These changes enable
        continuous parsing which communicates results back to the database
        while the server_job is running instead of only when the server_job is
        complete.
        """
        self._server_job._parse_job += "/" + self._machine
        self._server_job._using_parser = True
        self._server_job.machines = [self._machine]
        self._server_job.push_execution_context(self._machine)
        self._server_job.init_parser()
        self._client_at.run_test(active_test.test_name,
                                 results_dir=self._results_dir,
                                 **active_test.test_args)
        self._server_job.cleanup_parser()

    def run(self):
        """Executes tests on host machine.

        Uses subprocess to fork the process when running tests so unique client
        jobs talk to unique server jobs which prevents log files from
        simultaneous tests interweaving with each other.
        """
        while True:
            active_test = self.get_test()
            if active_test is None:
                break

            # Install autoest on host before running tests.  Do this before
            # the subcommand fork so all future forks see that it has been
            # installed on the host.
            if not self._client_at.installed:
                self._client_at.install()

            logging.info('%s running %s', self._machine, active_test)
            try:
                self.run_subcommand(active_test)
            except (error.AutoservError, error.AutotestError):
                logging.exception('Error running test "%s".', active_test)
            except Exception:
                logging.exception('Exception running test "%s".', active_test)
                raise
            finally:
                self._test_queue.task_done()
                self._tests_run += 1

        logging.info('%s completed %d tests.', self._machine, self._tests_run)
