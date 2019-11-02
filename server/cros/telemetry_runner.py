# Copyright (c) 2013 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import json
import logging
import numbers
import numpy
import os
import StringIO

from autotest_lib.client.common_lib import error, utils
from autotest_lib.client.common_lib.cros import dev_server


TELEMETRY_RUN_BENCHMARKS_SCRIPT = 'tools/perf/run_benchmark'
TELEMETRY_RUN_TESTS_SCRIPT = 'tools/telemetry/run_tests'
TELEMETRY_RUN_GPU_TESTS_SCRIPT = 'content/test/gpu/run_gpu_integration_test.py'
TELEMETRY_TIMEOUT_MINS = 150

DUT_CHROME_ROOT = '/usr/local/telemetry/src'

CHART_JSON_RESULT = 'results-chart.json'
HISTOGRAM_SET_RESULT = 'histograms.json'

# Result Statuses
SUCCESS_STATUS = 'SUCCESS'
WARNING_STATUS = 'WARNING'
FAILED_STATUS = 'FAILED'

# A list of telemetry tests that cannot run on dut.
ON_DUT_BLACKLIST = [
    'cros_ui_smoothness',           # crbug/976839
    'loading.desktop',              # crbug/882299
    'rendering.desktop',            # crbug/882291
    'system_health.memory_desktop', # crbug/874386
]

class TelemetryResult(object):
    """Class to represent the results of a telemetry run.

    This class represents the results of a telemetry run, whether it ran
    successful, failed or had warnings.
    """


    def __init__(self, exit_code=0, stdout='', stderr=''):
        """Initializes this TelemetryResultObject instance.

        @param status: Status of the telemtry run.
        @param stdout: Stdout of the telemetry run.
        @param stderr: Stderr of the telemetry run.
        """
        if exit_code == 0:
            self.status = SUCCESS_STATUS
        else:
            self.status = FAILED_STATUS

        self._stdout = stdout
        self._stderr = stderr
        self.output = '\n'.join([stdout, stderr])


class TelemetryRunner(object):
    """Class responsible for telemetry for a given build.

    This class will extract and install telemetry on the devserver and is
    responsible for executing the telemetry benchmarks and returning their
    output to the caller.
    """

    def __init__(self, host, local=False, telemetry_on_dut=True):
        """Initializes this telemetry runner instance.

        If telemetry is not installed for this build, it will be.

        Basically, the following commands on the local pc on which test_that
        will be executed, depending on the 4 possible combinations of
        local x telemetry_on_dut:

        local=True, telemetry_on_dut=False:
        run_benchmark --browser=cros-chrome --remote=[dut] [test]

        local=True, telemetry_on_dut=True:
        ssh [dut] run_benchmark --browser=system [test]

        local=False, telemetry_on_dut=False:
        ssh [devserver] run_benchmark --browser=cros-chrome --remote=[dut] [test]

        local=False, telemetry_on_dut=True:
        ssh [devserver] ssh [dut] run_benchmark --browser=system [test]

        @param host: Host where the test will be run.
        @param local: If set, no devserver will be used, test will be run
                      locally.
                      If not set, "ssh [devserver] " will be appended to test
                      commands.
        @param telemetry_on_dut: If set, telemetry itself (the test harness)
                                 will run on dut.
                                 It decides browser=[system|cros-chrome]
        """
        self._host = host
        self._devserver = None
        self._telemetry_path = None
        self._telemetry_on_dut = telemetry_on_dut
        # TODO (llozano crbug.com/324964). Remove conditional code.
        # Use a class hierarchy instead.
        if local:
            self._setup_local_telemetry()
        else:
            self._setup_devserver_telemetry()

        logging.debug('Telemetry Path: %s', self._telemetry_path)


    def _setup_devserver_telemetry(self):
        """Setup Telemetry to use the devserver."""
        logging.debug('Setting up telemetry for devserver testing')
        logging.debug('Grabbing build from AFE.')
        info = self._host.host_info_store.get()
        if not info.build:
            logging.error('Unable to locate build label for host: %s.',
                          self._host.host_port)
            raise error.AutotestError('Failed to grab build for host %s.' %
                                      self._host.host_port)

        logging.debug('Setting up telemetry for build: %s', info.build)

        self._devserver = dev_server.ImageServer.resolve(
                info.build, hostname=self._host.hostname)
        self._devserver.stage_artifacts(info.build, ['autotest_packages'])
        self._telemetry_path = self._devserver.setup_telemetry(build=info.build)


    def _setup_local_telemetry(self):
        """Setup Telemetry to use local path to its sources.

        First look for chrome source root, either externally mounted, or inside
        the chroot.  Prefer chrome-src-internal source tree to chrome-src.
        """
        TELEMETRY_DIR = 'src'
        CHROME_LOCAL_SRC = '/var/cache/chromeos-cache/distfiles/target/'
        CHROME_EXTERNAL_SRC = os.path.expanduser('~/chrome_root/')

        logging.debug('Setting up telemetry for local testing')

        sources_list = ('chrome-src-internal', 'chrome-src')
        dir_list = [CHROME_EXTERNAL_SRC]
        dir_list.extend(
                [os.path.join(CHROME_LOCAL_SRC, x) for x in sources_list])
        if 'CHROME_ROOT' in os.environ:
            dir_list.insert(0, os.environ['CHROME_ROOT'])

        telemetry_src = ''
        for dir in dir_list:
            if os.path.exists(dir):
                telemetry_src = os.path.join(dir, TELEMETRY_DIR)
                break
        else:
            raise error.TestError('Telemetry source directory not found.')

        self._devserver = None
        self._telemetry_path = telemetry_src


    def _get_telemetry_cmd(self, script, test_or_benchmark, output_format,
                           *args, **kwargs):
        """Build command to execute telemetry based on script and benchmark.

        @param script: Telemetry script we want to run. For example:
                       [path_to_telemetry_src]/src/tools/telemetry/run_tests.
        @param test_or_benchmark: Name of the test or benchmark we want to run,
                                  with the page_set (if required) as part of
                                  the string.
        @param args: additional list of arguments to pass to the script.
        @param kwargs: additional list of keyword arguments to pass to the
                       script.

        @returns Full telemetry command to execute the script.
        """
        telemetry_cmd = []
        if self._devserver:
            devserver_hostname = self._devserver.hostname
            telemetry_cmd.extend(['ssh', devserver_hostname])

        results_dir = kwargs.get('results_dir', '')
        no_verbose = kwargs.get('no_verbose', False)

        if self._telemetry_on_dut:
            telemetry_cmd.extend(
                    [self._host.ssh_command(alive_interval=900,
                                            connection_attempts=4),
                     'python',
                     script,
                     '--output-format=%s' % output_format,
                     '--output-dir=%s' % DUT_CHROME_ROOT,
                     '--browser=system'])
        else:
            telemetry_cmd.extend(
                    ['python',
                     script,
                     '--browser=cros-chrome',
                     '--output-format=%s' % output_format,
                     '--output-dir=%s' %
                        (results_dir if results_dir else self._telemetry_path),
                     '--remote=%s' % self._host.host_port])
        if not no_verbose:
            telemetry_cmd.append('--verbose')
        telemetry_cmd.extend(args)
        telemetry_cmd.append(test_or_benchmark)

        return ' '.join(telemetry_cmd)


    def _scp_telemetry_results_cmd(self, perf_results_dir, output_format):
        """Build command to copy the telemetry results from the devserver.

        @param perf_results_dir: directory path where test output is to be
                                 collected.
        @returns SCP command to copy the results json to the specified directory.
        """
        if not perf_results_dir:
            return ''

        output_filename = CHART_JSON_RESULT
        if output_format == 'histograms':
            output_filename = HISTOGRAM_SET_RESULT
        scp_cmd = ['scp']
        if self._telemetry_on_dut:
            scp_cmd.append(self._host.make_ssh_options(alive_interval=900,
                                                       connection_attempts=4))
            if not self._host.is_default_port:
                scp_cmd.append('-P %d' % self._host.port)
            src = 'root@%s:%s/%s' % (self._host.hostname, DUT_CHROME_ROOT,
                                     output_filename)
        else:
            devserver_hostname = ''
            if self._devserver:
                devserver_hostname = self._devserver.hostname + ':'
            src = '%s%s/%s' % (devserver_hostname, self._telemetry_path,
                               output_filename)

        scp_cmd.extend([src, perf_results_dir])
        return ' '.join(scp_cmd)


    def _run_cmd(self, cmd):
        """Execute an command in a external shell and capture the output.

        @param cmd: String of is a valid shell command.

        @returns The standard out, standard error and the integer exit code of
                 the executed command.
        """
        logging.debug('Running: %s', cmd)

        output = StringIO.StringIO()
        error_output = StringIO.StringIO()
        exit_code = 0
        try:
            result = utils.run(cmd, stdout_tee=output,
                               stderr_tee=error_output,
                               timeout=TELEMETRY_TIMEOUT_MINS*60)
            exit_code = result.exit_status
        except error.CmdError as e:
            logging.debug('Error occurred executing.')
            exit_code = e.result_obj.exit_status

        stdout = output.getvalue()
        stderr = error_output.getvalue()
        logging.debug('Completed with exit code: %d.\nstdout:%s\n'
                      'stderr:%s', exit_code, stdout, stderr)
        return stdout, stderr, exit_code


    def _run_telemetry(self, script, test_or_benchmark, output_format,
                       *args, **kwargs):
        """Runs telemetry on a dut.

        @param script: Telemetry script we want to run. For example:
                       [path_to_telemetry_src]/src/tools/telemetry/run_tests.
        @param test_or_benchmark: Name of the test or benchmark we want to run,
                                 with the page_set (if required) as part of the
                                 string.
        @param args: additional list of arguments to pass to the script.
        @param kwargs: additional list of keyword arguments to pass to the
                       script.

        @returns A TelemetryResult Instance with the results of this telemetry
                 execution.
        """
        # TODO (sbasi crbug.com/239933) add support for incognito mode.

        telemetry_cmd = self._get_telemetry_cmd(script,
                                                test_or_benchmark,
                                                output_format,
                                                *args,
                                                **kwargs)
        logging.info('Running Telemetry: %s', telemetry_cmd)

        stdout, stderr, exit_code = self._run_cmd(telemetry_cmd)

        return TelemetryResult(exit_code=exit_code, stdout=stdout,
                               stderr=stderr)


    def _run_scp(self, perf_results_dir, output_format):
        """Runs telemetry on a dut.

        @param perf_results_dir: The local directory that results are being
                                 collected.
        """
        scp_cmd = self._scp_telemetry_results_cmd(perf_results_dir,
                                                  output_format)
        logging.debug('Retrieving Results: %s', scp_cmd)
        _, _, exit_code = self._run_cmd(scp_cmd)
        if exit_code != 0:
            raise error.TestFail('Unable to retrieve results.')

        if output_format == 'histograms':
            # Converts to chart json format.
            input_filename = os.path.join(perf_results_dir,
                                          HISTOGRAM_SET_RESULT)
            output_filename = os.path.join(perf_results_dir,
                                           CHART_JSON_RESULT)
            histograms = json.loads(open(input_filename).read())
            chartjson = TelemetryRunner.convert_chart_json(histograms)
            with open(output_filename, 'w') as fout:
                fout.write(json.dumps(chartjson, indent=2))

    def _run_test(self, script, test, *args):
        """Runs a telemetry test on a dut.

        @param script: Which telemetry test script we want to run. Can be
                       telemetry's base test script or the Chrome OS specific
                       test script.
        @param test: Telemetry test we want to run.
        @param args: additional list of arguments to pass to the script.

        @returns A TelemetryResult Instance with the results of this telemetry
                 execution.
        """
        logging.debug('Running telemetry test: %s', test)
        telemetry_script = os.path.join(self._telemetry_path, script)
        result = self._run_telemetry(telemetry_script, test, 'chartjson', *args)
        if result.status is FAILED_STATUS:
            raise error.TestFail('Telemetry test %s failed.' % test)
        return result


    def run_telemetry_test(self, test, *args):
        """Runs a telemetry test on a dut.

        @param test: Telemetry test we want to run.
        @param args: additional list of arguments to pass to the telemetry
                     execution script.

        @returns A TelemetryResult Instance with the results of this telemetry
                 execution.
        """
        return self._run_test(TELEMETRY_RUN_TESTS_SCRIPT, test, *args)


    def run_telemetry_benchmark(self,
                                benchmark,
                                perf_value_writer=None,
                                *args,
                                **kwargs):
        """Runs a telemetry benchmark on a dut.

        @param benchmark: Benchmark we want to run.
        @param perf_value_writer: Should be an instance with the function
                                  output_perf_value(), if None, no perf value
                                  will be written. Typically this will be the
                                  job object from an autotest test.
        @param args: additional list of arguments to pass to the telemetry
                     execution script.
        @param kwargs: additional list of keyword arguments to pass to the
                       telemetry execution script.

        @returns A TelemetryResult Instance with the results of this telemetry
                 execution.
        """
        logging.debug('Running telemetry benchmark: %s', benchmark)

        if benchmark in ON_DUT_BLACKLIST:
            self._telemetry_on_dut = False

        output_format = kwargs.get('ex_output_format', '')

        if not output_format:
            output_format = 'histograms'

        if self._telemetry_on_dut:
            telemetry_script = os.path.join(DUT_CHROME_ROOT,
                                            TELEMETRY_RUN_BENCHMARKS_SCRIPT)
            self._ensure_deps(self._host, benchmark)
        else:
            telemetry_script = os.path.join(self._telemetry_path,
                                            TELEMETRY_RUN_BENCHMARKS_SCRIPT)

        result = self._run_telemetry(telemetry_script, benchmark,
                                     output_format, *args, **kwargs)

        if result.status is WARNING_STATUS:
            raise error.TestWarn('Telemetry Benchmark: %s'
                                 ' exited with Warnings.\nOutput:\n%s\n' %
                                 (benchmark, result.output))
        elif result.status is FAILED_STATUS:
            raise error.TestFail('Telemetry Benchmark: %s'
                                 ' failed to run.\nOutput:\n%s\n' %
                                 (benchmark, result.output))
        elif '[  PASSED  ] 0 tests.' in result.output:
            raise error.TestWarn('Telemetry Benchmark: %s exited successfully,'
                                 ' but no test actually passed.\nOutput\n%s\n'
                                 % (benchmark, result.output))
        if perf_value_writer:
            self._run_scp(perf_value_writer.resultsdir, output_format)
        return result


    def run_gpu_integration_test(self, test, *args):
        """Runs a gpu test on a dut.

        @param test: Gpu test we want to run.
        @param args: additional list of arguments to pass to the telemetry
                     execution script.

        @returns A TelemetryResult instance with the results of this telemetry
                 execution.
        """
        script = os.path.join(DUT_CHROME_ROOT,
                              TELEMETRY_RUN_GPU_TESTS_SCRIPT)
        cmd = []
        if self._devserver:
            devserver_hostname = self._devserver.hostname
            cmd.extend(['ssh', devserver_hostname])

        cmd.extend(
            [self._host.ssh_command(alive_interval=900, connection_attempts=4),
             'python', script])
        cmd.extend(args)
        cmd.append(test)
        cmd = ' '.join(cmd)
        stdout, stderr, exit_code = self._run_cmd(cmd)

        if exit_code:
            raise error.TestFail('Gpu Integration Test: %s'
                                 ' failed to run.' % test)

        return TelemetryResult(exit_code=exit_code, stdout=stdout,
                               stderr=stderr)


    def _ensure_deps(self, dut, test_name):
        """
        Ensure the dependencies are locally available on DUT.

        @param dut: The autotest host object representing DUT.
        @param test_name: Name of the telemetry test.
        """
        # Get DEPs using host's telemetry.
        # Example output, fetch_benchmark_deps.py --output-deps=deps octane:
        # {'octane': ['tools/perf/page_sets/data/octane_002.wprgo']}
        perf_path = os.path.join(self._telemetry_path, 'tools', 'perf')
        deps_path = os.path.join(perf_path, 'fetch_benchmark_deps_result.json')
        fetch_path = os.path.join(perf_path, 'fetch_benchmark_deps.py')
        format_fetch = ('python %s --output-deps=%s %s')
        command_fetch = format_fetch % (fetch_path, deps_path, test_name)
        command_get = 'cat %s' % deps_path

        if self._devserver:
            devserver_hostname = self._devserver.url().split(
                    'http://')[1].split(':')[0]
            command_fetch = 'ssh %s %s' % (devserver_hostname, command_fetch)
            command_get = 'ssh %s %s' % (devserver_hostname, command_get)

        logging.info('Getting DEPs: %s', command_fetch)
        _, _, exit_code = self._run_cmd(command_fetch)
        if exit_code != 0:
            raise error.TestFail('Error occurred while fetching DEPs.')
        stdout, _, exit_code = self._run_cmd(command_get)
        if exit_code != 0:
            raise error.TestFail('Error occurred while getting DEPs.')

        # Download DEPs to DUT.
        # send_file() relies on rsync over ssh. Couldn't be better.
        deps = json.loads(stdout)
        for dep in deps[test_name]:
            src = os.path.join(self._telemetry_path, dep)
            dst = os.path.join(DUT_CHROME_ROOT, dep)
            if self._devserver:
                logging.info('Copying: %s -> %s', src, dst)
                rsync_cmd = utils.sh_escape('rsync %s %s %s:%s' %
                                            (self._host.rsync_options(), src,
                                            self._host.hostname, dst))
                utils.run('ssh %s "%s"' % (devserver_hostname, rsync_cmd))
            else:
                if not os.path.isfile(src):
                    raise error.TestFail('Error occurred while saving DEPs.')
                logging.info('Copying: %s -> %s', src, dst)
                dut.send_file(src, dst)

    @staticmethod
    def convert_chart_json(histogram_set):
        """
        Convert from histogram set to chart json format.

        @param histogram_set: result in histogram set format.

        @returns result in chart json format.
        """
        value_map = {}

        # Gets generic set values.
        for obj in histogram_set:
            if 'type' in obj and obj['type'] == 'GenericSet':
                value_map[obj['guid']] = obj['values']

        charts = {}
        benchmark_name = ''
        benchmark_desc = ''

        # Checks the unit test for how this conversion works.
        for obj in histogram_set:
            if 'name' not in obj or 'sampleValues' not in obj:
                continue
            metric_name = obj['name']
            diagnostics = obj['diagnostics']
            if diagnostics.has_key('stories'):
                story_name = value_map[diagnostics['stories']][0]
            else:
                story_name = 'default'
            local_benchmark_name = value_map[diagnostics['benchmarks']][0]
            if benchmark_name == '':
                benchmark_name = local_benchmark_name
                if diagnostics.has_key('benchmarkDescriptions'):
                    benchmark_desc = value_map[
                        diagnostics['benchmarkDescriptions']][0]
            if benchmark_name != local_benchmark_name:
                logging.warning('There are more than 1 benchmark names in the'
                                'result. old: %s, new: %s' %
                                (benchmark_name, local_benchmark_name))
                continue

            unit = obj['unit']
            smaller_postfixes = ('_smallerIsBetter', '-')
            bigger_postfixes = ('_biggerIsBetter', '+')
            all_postfixes = smaller_postfixes + bigger_postfixes

            improvement = 'up'
            for postfix in smaller_postfixes:
              if unit.endswith(postfix):
                improvement = 'down'
            for postfix in all_postfixes:
              if unit.endswith(postfix):
                unit = unit[:-len(postfix)]
                break

            if unit == 'unitless':
              unit = 'score'

            values = [x for x in obj['sampleValues']
                      if isinstance(x, numbers.Number)]
            if metric_name not in charts:
                charts[metric_name] = {}
            charts[metric_name][story_name] = {
                'improvement_direction': improvement,
                'name': metric_name,
                'std': numpy.std(values),
                'type': 'list_of_scalar_values',
                'units': unit,
                'values': values
            }

        # Adds summaries.
        for metric_name in charts:
            values = []
            metric_content = charts[metric_name]
            for story_name in metric_content:
                story_content = metric_content[story_name]
                values += story_content['values']
                metric_type = story_content['type']
                units = story_content['units']
                improvement = story_content['improvement_direction']
            values.sort()
            std = numpy.std(values)
            metric_content['summary'] = {
                'improvement_direction': improvement,
                'name': metric_name,
                'std': std,
                'type': metric_type,
                'units': units,
                'values': values
            }

        benchmark_metadata = {
            'description': benchmark_desc,
            'name': benchmark_name,
            'type': 'telemetry_benchmark'
        }
        return {
            'benchmark_description': benchmark_desc,
            'benchmark_metadata': benchmark_metadata,
            'benchmark_name': benchmark_name,
            'charts': charts,
            'format_version': 1.0
        }

