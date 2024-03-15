# Lint as: python2, python3
# Copyright 2022 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# TODO(rkuroiwa): Rename this file to adb_utils.py to align with other utility
# modules. Also when class Adb is instantiated, the user is likely to call the
# instance "adb" which would collide with this file name (unless they always
# use "import adb as someothername".

import contextlib
import logging
import random
import re

from autotest_lib.client.common_lib import error
from autotest_lib.server import utils
from autotest_lib.server.cros.tradefed import tradefed_constants as constants

# The default ADB port.
_DEFAULT_ADB_PORT = 5037


class Adb:
    """Class for running adb commands."""

    def __init__(self):
        self._install_paths = set()
        self._port = _DEFAULT_ADB_PORT
        self._tunnel = NullAdbTunnel()

    def pick_random_port(
            self,
            max_retries=3,
            start_timeout=constants.ADB_SERVER_COMMAND_TIMEOUT_SECONDS):
        """Picks a random ADB server port for subsequent ADB commands.

        This is required by CFT where test containers share the same host
        network namespace. This function implements heuristics to detect if a
        port is already occupied by an ADB server in another test container, to
        prevent tests from breaking each other's state.

        TODO: Possibly remove the heuristics once go/cft-port-discovery is
        implemented; allow the caller to specify a safe port range or simply
        decide which port to use.

        @param max_retries: Try this many times until we find an available port.
        @param start_timeout: Seconds to wait until `adb start-server` returns.
        """
        num_tries = 0
        while num_tries < max_retries:
            self._port = random.randint(1024, 65535)
            if self._port == _DEFAULT_ADB_PORT:
                continue
            num_tries += 1

            # Run `adb start-server` on the candidate port. There are 4 possible
            # outcomes:
            # (1) The port is unused and ADB server starts successfully. The
            #     command would print a message containing "daemon started
            #     successfully" to stderr and return successfully.
            # (2) The port is occupied by another ADB server. The command would
            #     return successfully, but print nothing to stderr.
            # (3) The port is occupied by some process, and it returns an
            #     invalid response. The command would return a non-zero status.
            # (4) The port is occupied by some process, and it doesn't respond.
            #     The command would hang until timeout.
            try:
                result = self.run(None, verbose=True, args=('start-server',),
                                  timeout=start_timeout)
            except (error.CmdError, error.CmdTimeoutError):
                # Cases (3) and (4); try another port
                continue

            if 'daemon started successfully' not in result.stderr:
                # Case (2); try another port
                continue

            # Case (1)
            logging.info('adb using random port %s', self._port)
            return

        raise Exception('Failed to find available port for ADB server')

    def add_path(self, path):
        """Adds path for executing commands.

        Path to ADB and AAPT may have to be added it if is not in the path.
        Use this method to add it to the path before using run().
        """
        self._install_paths.add(path)

    def get_paths(self):
        return self._install_paths

    def get_socket(self):
        """Returns the ADB server socket string as in `adb -L <socket>`."""
        return f'tcp:localhost:{self._port}'

    def get_port(self):
        """Returns the ADB server port being used."""
        return self._port

    def set_tunnel(self, tunnel):
        """Sets the ADB tunnel to use.

        By default the "null" tunnel is used. This method allows setting ADB
        tunnel implementations for environments that require it.
        See: NullAdbTunnel, SshAdbTunnel
        """
        self._tunnel = tunnel

    def create_tunnel(self):
        """Returns a context manager that creates the ADB tunnel when entered.

        The tunnel has to be created before executing run() commands.
        """
        return self._tunnel.create()

    def get_adb_target(self, host):
        """Returns the ADB target corresponding to given host."""
        return self._tunnel.get_adb_target(host)

    def get_adb_targets(self, hosts):
        """Returns a list of adb targets."""
        return [self.get_adb_target(host) for host in hosts]

    def run(self, host, *args, **kwargs):
        """Runs an ADB command on the host.

        @param host: DUT to issue the adb command.
        @param args: Extra args passed to the adb command.
        @param kwargs: Extra arguments passed to utils.run().
        """
        additional_option = self._get_options(host)
        kwargs['args'] = additional_option + kwargs.get('args', ())

        # _install_paths should include the directory with adb.
        # utils.run() will append these to paths.
        kwargs['extra_paths'] = (kwargs.get('extra_paths', []) +
                                 list(self._install_paths))
        result = utils.run('adb', **kwargs)
        logging.info('adb %s:\n%s', ' '.join(kwargs.get('args')),
                     result.stdout + result.stderr)
        return result

    def _get_options(self, host):
        """Returns ADB options for executing commands.

        @param host: DUT that want to connect to. (None if the adb command is
                     intended to run in the server. eg. keygen)
        @return a tuple of arguments for adb command.
        """
        opts = ['-L', self.get_socket()]
        if host:
            host_port = self.get_adb_target(host)
            opts.extend(('-s', host_port))
        return tuple(opts)


class NullAdbTunnel:
    """Null tunnel allows direct ADB connection via network without a tunnel."""

    def create(self):
        """Returns a context manager that manages the tunnel connection.

        The null tunnel does nothing here.
        """
        return contextlib.nullcontext()

    def get_adb_target(self, host):
        """Returns the ADB target corresponding to given host.

        This method is slightly different from host.host_port as we need to
        explicitly specify the port so the serial name of adb target would
        match.
        """
        port = 22 if host.port is None else host.port
        if re.search(r':.*:', host.hostname):
            # Add [] for raw IPv6 addresses, stripped for ssh.
            # In the Python >= 3.3 future, 'import ipaddress' will parse
            # addresses.
            return '[{}]:{}'.format(host.hostname, port)
        return '{}:{}'.format(host.hostname, port)


class SshAdbTunnel:
    """Connects ADB via SSH tunnel to each host."""

    _BEGIN_PORT = 9222

    def __init__(self, hosts):
        self._hosts = hosts
        self._host_port_map = {}
        self._created = False

    @contextlib.contextmanager
    def create(self):
        """Returns a context manager that manages the tunnel connection.

        Entering the context creates SSH tunnels to each host's port 22 in the
        background, listening on local port 9222+n.
        """
        jobs = []
        for i, host in enumerate(self._hosts):
            local_port = self._BEGIN_PORT + i
            ssh_cmd = self._get_ssh_tunnel_command(host, local_port)
            jobs.append(
                    utils.
                    BgJob(ssh_cmd,
                          nickname=f'adb_tunnel:{host.hostname}:{local_port}',
                          stderr_level=logging.DEBUG,
                          stdout_tee=utils.TEE_TO_LOGS,
                          stderr_tee=utils.TEE_TO_LOGS))
            self._host_port_map[host.hostname] = local_port

        self._created = True
        try:
            yield
        finally:
            self._created = False
            for job in jobs:
                utils.nuke_subprocess(job.sp)
            utils.join_bg_jobs(jobs)

    def get_adb_target(self, host):
        """Returns the ADB target corresponding to given host.

        This is always localhost:9222 (+n if multiple hosts).
        """
        assert self._created
        return f'localhost:{self._host_port_map[host.hostname]}'

    @staticmethod
    def _get_ssh_tunnel_command(host, local_port):
        """Returns the SSH command to create a tunnel to the host."""
        return host.ssh_command(options=f'-v -N -L{local_port}:localhost:22')
