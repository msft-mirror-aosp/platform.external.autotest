# Lint as: python2, python3
# Copyright 2022 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import re


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


def tradefed_options(host):
    """ADB arguments for tradefed.

    These arguments are specific to using adb with tradefed.

    @param host: DUT that want to connect to. (None if the adb command is
                 intended to run in the server. eg. keygen)
    @return a tuple of arguments for adb command.
    """
    if host:
        host_port = get_adb_target(host)
        ret = ('-s', host_port)
        return ret
    # As of N, tradefed could not specify which adb socket to use, which use
    # tcp:localhost:5037 by default.
    return ('-H', 'localhost', '-P', '5037')
