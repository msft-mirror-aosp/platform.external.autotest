class Configuration(object):
    """
    Configuration that can be changed for configurable CFM tests.
    """
    def __init__(self, run_test_only=False):
        """
        Initializes.

        @param run_test_only Whether to run only the test or to also perform
            deprovisioning, enrollment and system reboot. If set to 'True',
            the DUT must already be enrolled and past the OOB screen to be able
            to execute the test.
        """
        self.run_test_only = run_test_only
