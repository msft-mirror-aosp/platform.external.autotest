#!/usr/bin/python3
#
# Copyright 2019 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""
Call `cros_config` from the DUT.
"""

from autotest_lib.client.common_lib import error


def call_cros_config_get_output(cros_config_args, run, **run_kwargs):
    """
    Get the stdout from cros_config.

    @param cros_config_args: '$path $property', as used by cros_config
    @param run: A function which passes a command to the DUT, and
               returns a client.common_lib.utils.CmdResult object.
    @param **run_kwargs: Any kwargs to be passed into run()
    @return: The string stdout of either cros_config or its fallback,
             or empty string in the case of error.

    @type cros_config: string
    @type run: func(string, **kwargs) -> CmdResult
    @rtype: string

    """
    cros_config_cmd = 'cros_config %s' % cros_config_args
    try:
        result = run(cros_config_cmd, **run_kwargs)
    except error.CmdError:
        return ''
    if result.exit_status:
        return ''
    return result.stdout
