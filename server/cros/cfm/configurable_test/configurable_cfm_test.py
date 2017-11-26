import logging

from autotest_lib.server.cros.cfm import cfm_base_test
from autotest_lib.server.cros.cfm.configurable_test import action_context

class TestRunner(object):
    """
    Runs a test.
    """
    def __init__(self, context):
        """
        Initializes.

        @param context ActionContext providing the dependencies for the test.
        """
        self.context = context

    def run_test(self, cfm_test):
        """
        Runs one test.

        @param cfm_test CfmTest instance to execute.
        """
        logging.info('RUNNING:\n%s', str(cfm_test))
        cfm_test.scenario.execute(self.context)

class HostFileContentsCollector(object):
    """
    File contents collector that executes commands against the host.
    """
    def __init__(self, host):
        """
        Initializes with a host.

        @param host a host object as available from CfmBaseTest.host
        """
        self.host = host

    def collect_file_contents(self, path):
        """
        Returns the file contents of the file at the specified path.

        @param path The path of the file.
        @returns The contents of the file
        """
        return self.host.run_output('cat "%s"' % path)

class ConfigurableCfmTest(cfm_base_test.CfmBaseTest):
    """
    Base class for the actual Autotests that execute configurable CFM tests.
    """
    version = 1

    def initialize(self, host, cfm_test):
        """
        Initializes the test.

        @param host The host the test is run against
        @param cfm_test CfmTest instance to execute.
        """
        (super(ConfigurableCfmTest, self)
            .initialize(host, cfm_test.configuration.run_test_only))
        self.cfm_test = cfm_test
        # self.cfm_facade is inherited from CfmBaseTest.
        context = action_context.ActionContext(
                cfm_facade=self.cfm_facade,
                file_contents_collector=HostFileContentsCollector(host),
                host=host)
        self.test_runner = TestRunner(context)

    def run_once(self):
        """
        Runs the test.
        """
        self.test_runner.run_test(self.cfm_test)

