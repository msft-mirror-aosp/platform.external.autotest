class ActionContext(object):
    """
    Provides the dependencies actions might need to execute.
    """
    def __init__(self,
                 cfm_facade=None,
                 file_contents_collector=None,
                 host=None):
        """
        Initializes.

        @param cfm_facade CFM facade to use, an instance of
                CFMFacadeRemoteAdapter.
        @param file_contents_collector object with a
                collect_file_contents(file_name) method to get file contents
                from the specified file on the DUT.
        @param host a Host object.
        """
        self.cfm_facade = cfm_facade
        self.file_contents_collector = file_contents_collector
        # TODO(kerl) consider using a facade to the Host to only provide an
        # interface with what we need.
        self.host = host

