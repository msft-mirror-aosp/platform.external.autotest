# Lint as: python2, python3
"""Client for Autotest side communcations to the TLS SSH Server."""


import grpc
import logging
import six
import time

from autotest_lib.server.hosts.drone_api_client import autotest_common_pb2
from autotest_lib.server.hosts.drone_api_client import autotest_common_pb2_grpc

from autotest_lib.client.common_lib import error
from autotest_lib.client.common_lib import utils

TLS_PORT = 7152
TLS_IP = '10.254.254.254'

class TLSClient(object):
    """The client side connection to Common-TLS service running in a drone."""

    def __init__(self, hostname):
        """Configure the grpc channel."""
        self.hostname = hostname
        self.channel = grpc.insecure_channel('{}:{}'.format(TLS_IP, TLS_PORT))
        self.stub = autotest_common_pb2_grpc.CommonStub(self.channel)
        logging.debug('TLS Client Started. Connected to: {}'.format(hostname))

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    def run_cmd(self,
                cmd,
                timeout=120,
                stdout_tee=None,
                stderr_tee=None,
                ignore_timeout=False):
        """
        Run a command on the host configured during init.

        @param cmd: shell cmd to execute on the DUT
        @param: stdout_tee/stderr_tee: objects to write the data from the
            respective streams to
        @param timeout int(seconds): how long to allow the command to run
            before forcefully killing it.
        @param ignore_timeout: if True, do not raise err on timeouts.
        """
        res = utils.CmdResult(command=cmd)
        try:
            self._run(cmd, stdout_tee, stderr_tee, res, timeout)
        except grpc.RpcError as e:
            if e.code().name == "DEADLINE_EXCEEDED":
                if ignore_timeout:
                    return None
                raise error.CmdTimeoutError(
                    cmd, res,
                    "Command(s) did not complete within %d seconds" % timeout)
            raise e
        except Exception as e:
            raise e
        return res

    def _run(self, cmd, stdout_tee, stderr_tee, res, timeout):
        """Run the provided cmd, populate the res and return it."""
        start_time = time.time()
        response = self._send_cmd(cmd, timeout)

        stdout_buf = six.StringIO()
        stderr_buf = six.StringIO()
        last_status = 0

        if response:
            for item in response:
                last_status = item.exit_info.status
                _parse_item_and_log(item.stdout, stdout_buf, stdout_tee)
                _parse_item_and_log(item.stderr, stderr_buf, stderr_tee)

        res.stdout = stdout_buf.getvalue()
        res.stderr = stderr_buf.getvalue()
        res.exit_status = last_status
        res.duration = time.time() - start_time

    def _send_cmd(self, cmd, timeout):
        """Serialize and send the cmd to the TLS service."""
        formatted_cmd = autotest_common_pb2.ExecDutCommandRequest(name=self.hostname,
                                                         command=cmd)
        return self.stub.ExecDutCommand(formatted_cmd, timeout=timeout)

    def close(self):
        """Close the grpc channel."""
        self.channel.close()
        logging.debug("TLS Client closed.")


def _parse_item_and_log(item, buf, tee):
    """
    Parse the provided item.

    If the item exists, append the provided arr with the item & write to
        the provided tee if provided.

    """
    if not item:
        return
    buf.write(item)
    if tee is not None and tee is not utils.TEE_TO_LOGS:
        tee.write(item)
