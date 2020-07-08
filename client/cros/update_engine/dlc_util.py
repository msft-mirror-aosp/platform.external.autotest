# Copyright 2020 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import json
import logging

from autotest_lib.client.common_lib import utils

_DEFAULT_RUN = utils.run

class DLCUtil(object):
    """
    Wrapper around dlcservice_util for tests that require DLC management.

    For dlc_util to work seamlessly in both client and server tests, we need
    those tests to define the _run() function:
    server side: host.run
    client side: utils.run

    """
    _DLCSERVICE_UTIL_CMD = "dlcservice_util"
    _DUMMY_DLC_ID = "dummy-dlc"

    def __init__(self, run_func=_DEFAULT_RUN):
        """
        Initialize this class with _run() function.

        @param run_func: The function to use to run commands on the client.
                         Defaults for use by client tests, but can be
                         overwritten to run remotely from a server test.

        """
        self._run = run_func


    def list(self):
        """
        List DLCs that are installed on the DUT and additional information
        about them such as name, version, root_mount, and size. The output is
        a dictionary containing the result of dlcservice_util --list, which
        looks like:
        {
           "dummy-dlc": [ {
              "fs-type": "squashfs",
              "id": "dummy-dlc",
              "image_type": "dlc",
              "manifest": "/opt/google/dlc/dummy-dlc/package/imageloader.json",
              "name": "Dummy DLC",
              "package": "package",
              "preallocated_size": "4194304",
              "root_mount": "/run/imageloader/dummy-dlc/package",
              "size": "53248",
              "version": "1.0.0-r10"
           } ]
        }

        @return Dictionary containing information about the installed DLCs,
                whose keys are the DLC IDs.

        """
        status = self._run([self._DLCSERVICE_UTIL_CMD, '--list'])
        logging.info(status)

        return json.loads(status.stdout)


    def install(self, dlc_id, omaha_url, timeout=900):
        """
        Install a DLC on the stateful partition.

        @param dlc_id: The id of the DLC to install.
        @param omaha_url: The Omaha URL to send the install request to.

        """
        cmd = [self._DLCSERVICE_UTIL_CMD, '--install', '--id=%s' % dlc_id,
               '--omaha_url=%s' % omaha_url]
        self._run(cmd, timeout=timeout)


    def uninstall(self, dlc_id, ignore_status=False):
        """
        Uninstall a DLC. The DLC will remain on the DUT in an un-mounted state
        and can be reinstalled without requiring an install request. To
        completely remove a DLC, purge it instead.

        @param dlc_id: The id of the DLC to uninstall.
        @param ignore_status: Whether or not to ignore the return status when
                              running the uninstall command.

        """
        cmd = [self._DLCSERVICE_UTIL_CMD, '--uninstall', '--id=%s' % dlc_id]
        self._run(cmd, ignore_status=ignore_status)


    def purge(self, dlc_id, ignore_status=False):
        """
        Purge a DLC. This will completely remove the DLC from the device.

        @param dlc_id: The id of the DLC to purge.
        @param ignore_status: Whether or not to ignore the return status when
                              running the purge command.

        """
        cmd = [self._DLCSERVICE_UTIL_CMD, '--purge', '--id=%s' % dlc_id]
        self._run(cmd, ignore_status=ignore_status)
