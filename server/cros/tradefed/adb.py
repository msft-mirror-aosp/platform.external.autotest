# Lint as: python2, python3
# Copyright 2022 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# TODO(rkuroiwa): Rename this file to adb_utils.py to align with other utility
# modules. Also when class Adb is instantiated, the user is likely to call the
# instance "adb" which would collide with this file name (unless they always
# use "import adb as someothername".

import logging
import random
import re

from autotest_lib.server import utils


class Adb:
    """Class for running adb commands."""

    def __init__(self, random_port=False):
        self._install_paths = set()
        if random_port:
            self._port = random.randint(1024, 65535)
        else:
            self._port = 5037
        logging.info('adb using port %s', self._port)

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
            host_port = get_adb_target(host)
            opts.extend(('-s', host_port))
        return tuple(opts)


def get_adb_target(host):
    """Get the adb target format.

    This method is slightly different from host.host_port as we need to
    explicitly specify the port so the serial name of adb target would
    match.

    @param host: a DUT accessible via adb.
    @return a string for specifying the host using adb command.
    """
    port = 22 if host.port is None else host.port
    if re.search(r':.*:', host.hostname):
        # Add [] for raw IPv6 addresses, stripped for ssh.
        # In the Python >= 3.3 future, 'import ipaddress' will parse
        # addresses.
        return '[{}]:{}'.format(host.hostname, port)
    return '{}:{}'.format(host.hostname, port)


def get_adb_targets(hosts):
    """Get a list of adb targets."""
    return [get_adb_target(host) for host in hosts]
