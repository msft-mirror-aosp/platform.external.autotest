# Lint as: python2, python3
from __future__ import division
from __future__ import print_function

import json
import os

from autotest_lib.server.hosts import file_store
from autotest_lib.client.common_lib import utils
from autotest_lib.tko import tast
from autotest_lib.tko import utils as tko_utils
import six


class HostKeyvalError(Exception):
    """Raised when the host keyval cannot be read."""


class job(object):
    """Represents a job."""

    def __init__(self, dir, user, label, machine, queued_time, started_time,
                 finished_time, machine_owner, machine_group, aborted_by,
                 aborted_on, keyval_dict):
        self.dir = dir
        self.tests = []
        self.user = user
        self.label = label
        self.machine = machine
        self.queued_time = queued_time
        self.started_time = started_time
        self.finished_time = finished_time
        self.machine_owner = machine_owner
        self.machine_group = machine_group
        self.aborted_by = aborted_by
        self.aborted_on = aborted_on
        self.keyval_dict = keyval_dict
        self.afe_parent_job_id = None
        self.build_version = None
        self.suite = None
        self.board = None
        self.job_idx = None
        # id of the corresponding tko_task_references entry.
        # This table is used to refer to skylab task / afe job corresponding to
        # this tko_job.
        self.task_reference_id = None

    @staticmethod
    def read_keyval(dir):
        """
        Read job keyval files.

        @param dir: String name of directory containing job keyval files.

        @return A dictionary containing job keyvals.

        """
        dir = os.path.normpath(dir)
        top_dir = tko_utils.find_toplevel_job_dir(dir)
        if not top_dir:
            top_dir = dir
        assert(dir.startswith(top_dir))

        # Pull in and merge all the keyval files, with higher-level
        # overriding values in the lower-level ones.
        keyval = {}
        while True:
            try:
                upper_keyval = utils.read_keyval(dir)
                # HACK: exclude hostname from the override - this is a special
                # case where we want lower to override higher.
                if 'hostname' in upper_keyval and 'hostname' in keyval:
                    del upper_keyval['hostname']
                keyval.update(upper_keyval)
            except IOError:
                pass  # If the keyval can't be read just move on to the next.
            if dir == top_dir:
                break
            else:
                assert(dir != '/')
                dir = os.path.dirname(dir)
        return keyval


class kernel(object):
    """Represents a kernel."""

    def __init__(self, base, patches, kernel_hash):
        self.base = base
        self.patches = patches
        self.kernel_hash = kernel_hash


    @staticmethod
    def compute_hash(base, hashes):
        """Compute a hash given the base string and hashes for each patch.

        @param base: A string representing the kernel base.
        @param hashes: A list of hashes, where each hash is associated with a
            patch of this kernel.

        @return A string representing the computed hash.

        """
        key_string = ','.join([base] + hashes)
        return utils.hash('md5', key_string).hexdigest()


class test(object):
    """Represents a test."""

    def __init__(self, subdir, testname, status, reason, test_kernel,
                 machine, started_time, finished_time, iterations,
                 attributes, perf_values, labels):
        self.subdir = subdir
        self.testname = testname
        self.status = status
        self.reason = reason
        self.kernel = test_kernel
        self.machine = machine
        self.started_time = started_time
        self.finished_time = finished_time
        self.iterations = iterations
        self.attributes = attributes
        self.perf_values = perf_values
        self.labels = labels


    @staticmethod
    def load_iterations(keyval_path):
        """Abstract method to load a list of iterations from a keyval file.

        @param keyval_path: String path to a keyval file.

        @return A list of iteration objects.

        """
        raise NotImplementedError


    @classmethod
    def parse_test(cls, job, subdir, testname, status, reason, test_kernel,
                   started_time, finished_time, existing_instance=None):
        """
        Parse test result files to construct a complete test instance.

        Given a job and the basic metadata about the test that can be
        extracted from the status logs, parse the test result files (keyval
        files and perf measurement files) and use them to construct a complete
        test instance.

        @param job: A job object.
        @param subdir: The string subdirectory name for the given test.
        @param testname: The name of the test.
        @param status: The status of the test.
        @param reason: The reason string for the test.
        @param test_kernel: The kernel of the test.
        @param started_time: The start time of the test.
        @param finished_time: The finish time of the test.
        @param existing_instance: An existing test instance.

        @return A test instance that has the complete information.

        """
        tko_utils.dprint("parsing test %s %s" % (subdir, testname))

        if tast.is_tast_test(testname):
            attributes, perf_values = tast.load_tast_test_aux_results(job,
                                                                      testname)
            iterations = []
        elif subdir:
            # Grab iterations from the results keyval.
            iteration_keyval = os.path.join(job.dir, subdir,
                                            'results', 'keyval')
            iterations = cls.load_iterations(iteration_keyval)

            # Grab perf values from the perf measurements file.
            perf_values_file = os.path.join(job.dir, subdir,
                                            'results', 'results-chart.json')
            perf_values = {}
            if os.path.exists(perf_values_file):
                with open(perf_values_file, 'r') as fp:
                    contents = fp.read()
                if contents:
                    perf_values = json.loads(contents)

            # Grab test attributes from the subdir keyval.
            test_keyval = os.path.join(job.dir, subdir, 'keyval')
            attributes = test.load_attributes(test_keyval)
        else:
            iterations = []
            perf_values = {}
            attributes = {}

        # Grab test+host attributes from the host keyval.
        host_keyval = cls.parse_host_keyval(job.dir, job.machine)
        attributes.update(dict(('host-%s' % k, v)
                               for k, v in six.iteritems(host_keyval)))

        if existing_instance:
            def constructor(*args, **dargs):
                """Initializes an existing test instance."""
                existing_instance.__init__(*args, **dargs)
                return existing_instance
        else:
            constructor = cls

        return constructor(subdir, testname, status, reason, test_kernel,
                           job.machine, started_time, finished_time,
                           iterations, attributes, perf_values, [])


    @classmethod
    def parse_partial_test(cls, job, subdir, testname, reason, test_kernel,
                           started_time):
        """
        Create a test instance representing a partial test result.

        Given a job and the basic metadata available when a test is
        started, create a test instance representing the partial result.
        Assume that since the test is not complete there are no results files
        actually available for parsing.

        @param job: A job object.
        @param subdir: The string subdirectory name for the given test.
        @param testname: The name of the test.
        @param reason: The reason string for the test.
        @param test_kernel: The kernel of the test.
        @param started_time: The start time of the test.

        @return A test instance that has partial test information.

        """
        tko_utils.dprint('parsing partial test %s %s' % (subdir, testname))

        return cls(subdir, testname, 'RUNNING', reason, test_kernel,
                   job.machine, started_time, None, [], {}, [], [])


    @staticmethod
    def load_attributes(keyval_path):
        """
        Load test attributes from a test keyval path.

        Load the test attributes into a dictionary from a test
        keyval path. Does not assume that the path actually exists.

        @param keyval_path: The string path to a keyval file.

        @return A dictionary representing the test keyvals.

        """
        if not os.path.exists(keyval_path):
            return {}
        return utils.read_keyval(keyval_path)


    @staticmethod
    def _parse_keyval(job_dir, sub_keyval_path):
        """
        Parse a file of keyvals.

        @param job_dir: The string directory name of the associated job.
        @param sub_keyval_path: Path to a keyval file relative to job_dir.

        @return A dictionary representing the keyvals.

        """
        # The "real" job dir may be higher up in the directory tree.
        job_dir = tko_utils.find_toplevel_job_dir(job_dir)
        if not job_dir:
            return {}  # We can't find a top-level job dir with job keyvals.

        # The keyval is <job_dir>/`sub_keyval_path` if it exists.
        keyval_path = os.path.join(job_dir, sub_keyval_path)
        if os.path.isfile(keyval_path):
            return utils.read_keyval(keyval_path)
        else:
            return {}


    @staticmethod
    def _is_multimachine(job_dir):
        """
        Determine whether the job is a multi-machine job.

        @param job_dir: The string directory name of the associated job.

        @return True, if the job is a multi-machine job, or False if not.

        """
        machines_path = os.path.join(job_dir, '.machines')
        if os.path.exists(machines_path):
            with open(machines_path, 'r') as fp:
                line_count = len(fp.read().splitlines())
                if line_count > 1:
                    return True
        return False


    @staticmethod
    def parse_host_keyval(job_dir, hostname):
        """
        Parse host keyvals.

        @param job_dir: The string directory name of the associated job.
        @param hostname: The string hostname.

        @return A dictionary representing the host keyvals.

        @raises HostKeyvalError if the host keyval is not found.

        """
        keyval_path = os.path.join('host_keyvals', hostname)
        hostinfo_path = os.path.join(job_dir, 'host_info_store',
                                     hostname + '.store')
        # Skylab uses hostinfo. If this is not present, try falling back to the
        # host keyval file (moblab), or an empty host keyval for multi-machine
        # tests (jetstream).
        if os.path.exists(hostinfo_path):
            tko_utils.dprint('Reading keyvals from hostinfo.')
            return _parse_hostinfo_keyval(hostinfo_path)
        elif os.path.exists(os.path.join(job_dir, keyval_path)):
            tko_utils.dprint('Reading keyvals from %s.' % keyval_path)
            return test._parse_keyval(job_dir, keyval_path)
        elif test._is_multimachine(job_dir):
            tko_utils.dprint('Multimachine job, no keyvals.')
            return {}
        raise HostKeyvalError('Host keyval not found')


    @staticmethod
    def parse_job_keyval(job_dir):
        """
        Parse job keyvals.

        @param job_dir: The string directory name of the associated job.

        @return A dictionary representing the job keyvals.

        """
        # The job keyval is <job_dir>/keyval if it exists.
        return test._parse_keyval(job_dir, 'keyval')


def _parse_hostinfo_keyval(hostinfo_path):
    """
    Parse host keyvals from hostinfo.

    @param hostinfo_path: The string path to the host info store file.

    @return A dictionary representing the host keyvals.

    """
    store = file_store.FileStore(hostinfo_path)
    hostinfo = store.get()
    # TODO(ayatane): Investigate if urllib.quote is better.
    label_string = ','.join(label.replace(':', '%3A')
                            for label in hostinfo.labels)
    return {
            'labels': label_string,
            'platform': hostinfo.model,
            'board': hostinfo.board
    }


class patch(object):
    """Represents a patch."""

    def __init__(self, spec, reference, hash):
        self.spec = spec
        self.reference = reference
        self.hash = hash


class iteration(object):
    """Represents an iteration."""

    def __init__(self, index, attr_keyval, perf_keyval):
        self.index = index
        self.attr_keyval = attr_keyval
        self.perf_keyval = perf_keyval


    @staticmethod
    def parse_line_into_dicts(line, attr_dict, perf_dict):
        """
        Abstract method to parse a keyval line and insert it into a dictionary.

        @param line: The string line to parse.
        @param attr_dict: Dictionary of generic iteration attributes.
        @param perf_dict: Dictionary of iteration performance results.

        """
        raise NotImplementedError


    @classmethod
    def load_from_keyval(cls, keyval_path):
        """
        Load a list of iterations from an iteration keyval file.

        Keyval data from separate iterations is separated by blank
        lines. Makes use of the parse_line_into_dicts method to
        actually parse the individual lines.

        @param keyval_path: The string path to a keyval file.

        @return A list of iteration objects.

        """
        if not os.path.exists(keyval_path):
            return []

        iterations = []
        index = 1
        attr, perf = {}, {}
        with open(keyval_path, 'r') as kp:
            lines = kp.readlines()
        for line in lines:
            line = line.strip()
            if line:
                cls.parse_line_into_dicts(line, attr, perf)
            else:
                iterations.append(cls(index, attr, perf))
                index += 1
                attr, perf = {}, {}
        if attr or perf:
            iterations.append(cls(index, attr, perf))
        return iterations


class perf_value_iteration(object):
    """Represents a perf value iteration."""

    def __init__(self, index, perf_measurements):
        """
        Initializes the perf values for a particular test iteration.

        @param index: The integer iteration number.
        @param perf_measurements: A list of dictionaries, where each dictionary
            contains the information for a measured perf metric from the
            current iteration.

        """
        self.index = index
        self.perf_measurements = perf_measurements


    @staticmethod
    def parse_line_into_dict(line):
        """
        Abstract method to parse an individual perf measurement line.

        @param line: A string line from the perf measurement output file.

        @return A dicionary representing the information for a measured perf
            metric from one line of the perf measurement output file, or an
            empty dictionary if the line cannot be parsed successfully.

        """
        raise NotImplementedError
