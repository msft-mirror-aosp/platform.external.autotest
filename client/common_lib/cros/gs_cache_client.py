# -*- coding: utf-8 -*-
# Copyright 2018 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""The client of GS Cache server.

GS Cache server is a server cache the responses from Google Storage to our lab.
It also provides some RPCs to serve files in an archive like tar, tgz, etc.

This client implements some functions used by autotest based on those RPCs.

For details of GS Cache server, see go/cros-gs-cache.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import json
import logging
import urllib
import urlparse

import requests

from autotest_lib.client.common_lib import error
from autotest_lib.client.common_lib import global_config
from autotest_lib.client.common_lib import utils
from autotest_lib.client.common_lib.cros import dev_server
from autotest_lib.client.common_lib.cros import retry

_CONFIG = global_config.global_config
_CONFIG_SECTION = 'GS_CACHE'

_PORT = _CONFIG.get_config_value(_CONFIG_SECTION, 'server_port', default=8888,
                                 type=int)
_CROS_IMAGE_ARCHIVE_BUCKET = _CONFIG.get_config_value(
        _CONFIG_SECTION, 'gs_image_archive_bucket',
        default="chromeos-image-archive")
_USE_SSH_CONNECTION = _CONFIG.get_config_value(
        'CROS', 'enable_ssh_connection_for_devserver', type=bool,
        default=False)
_SSH_CALL_TIMEOUT_SECONDS = 60


class CommunicationError(Exception):
    """Raised when has errors in communicate with GS Cache server."""


class ResponseContentError(Exception):
    """Error raised when response content has problems."""


class _GsCacheAPI(object):
    """A thin wrapper of the GS Cache server API.

    Useful for stubbing out GS Cache server calls for unittests.
    """
    def __init__(self, gs_cache_server_name):
        """Construct the instance by the information of reference server.

        @param gs_cache_server_name: A string of GS Cache server hostname.
        """
        self._hostname = gs_cache_server_name
        self._netloc = '%s:%s' % (gs_cache_server_name, _PORT)
        self._is_in_restricted_subnet = utils.get_restricted_subnet(
                gs_cache_server_name, utils.RESTRICTED_SUBNETS
        )

    def _ssh_call(self, url):
        """Helper function to make a 'SSH call'.

        @param url: The URL to be called.

        @return The output string of the call.
        @throws CommunicationError when the SSH command failed.
        """
        cmd = 'ssh %s \'curl "%s"\'' % (self._hostname, utils.sh_escape(url))
        try:
            result = utils.run(cmd, timeout=_SSH_CALL_TIMEOUT_SECONDS)
        except error.CmdError as err:
            raise CommunicationError('Error occurred: rc=%d, cmd=%s' %
                                     (err.result_obj.exit_status, err.command))

        return result.stdout

    @retry.retry(CommunicationError, timeout_min=3, delay_sec=5)
    def _call(self, action, bucket, path, queries):
        """Helper function to make a call to GS Cache server.

        There are two ways to call, i.e.
        1. via HTTP: We need this because all DUTs have and only have HTTP
        access to GS Cache server hosts.
        2. via SSH (ssh into the server and run a loopback `curl` call): We
        need this for the call from other services, e.g. drones, which have
        only SSH access to GS Cache servers.

        @param action: The name of RPC to be called, e.g. extract, etc.
        @param bucket: The bucket of the file on GS.
        @param path: The path of the file on GS. The bucket part is not
                     included. For example, if the GS path is
                     'gs://bucket/path/to/file', the `path` here is just
                     'path/to/file'.
        @param queries: A dict of queries (i.e. parameters).

        @return The http response content or SSH command output.
        @throws CommunicationError if there are errors while talking to GS Cache
            server.
        """
        url = urlparse.SplitResult(
                'http', self._netloc, '/'.join([action, bucket, path]),
                urllib.urlencode(queries, doseq=True), None).geturl()
        if _USE_SSH_CONNECTION and self._is_in_restricted_subnet:
            return self._ssh_call(url)
        else:
            # TODO(guocb): Re-use the TCP connection.
            rsp = requests.get(url)
            if not rsp.ok:
                msg = 'HTTP request: GET %s\nHTTP Response: %d: %s' % (
                        rsp.url, rsp.status_code, rsp.content)
                raise CommunicationError(msg)
            return rsp.content

    def extract(self, bucket, archive, files):
        """API binding of `extract`.

        @param bucket: The bucket of the file on GS.
        @param archive: The path of archive on GS (bucket part not included).
        @param files: A path, or a path list of files to be extracted.

        @return A dict of extracted files, in format of
                {filename: content, ...}.
        @throws ResponseContentError if the response is not in JSON format.
        """
        rsp_content = self._call('extract', bucket, archive, {'file': files})
        try:
            content_dict = json.loads(rsp_content)
        except ValueError as err:
            raise ResponseContentError(
                'Got ValueError "%s" when decoding to JSON format. The '
                'response content is: %s' % (err, rsp_content))

        return content_dict


class GsCacheClient(object):
    """A client of Google Storage Cache server."""

    _CONTROL_FILE_PREFIX = 'autotest/'
    _CONTROL_FILE_PREFIX_LEN = len(_CONTROL_FILE_PREFIX)

    def __init__(self, fallback_dev_server, api=None):
        """Constructor.

        @param fallback_dev_server: An instance of dev_server.DevServer which
                                    is only used for fallback to old path in
                                    case GS Cache server call fails.
        @param api: A _GsCacheAPI object (to stub out calls for tests).
        """
        self._fallback_server = fallback_dev_server
        self._api = api or _GsCacheAPI(fallback_dev_server.hostname)

    def list_suite_controls(self, build, suite_name=None):
        """Get the list of all control files for |build|.

        It tries to get control files from GS Cache server first. If failed,
        fall back to devserver.

        @param build: A string of build name (e.g. coral-release/R65-10300.0.0).
        @param suite_name: The name of the suite for which we require control
                           files. Pass None to get control files of all suites
                           of the build.
        @return the control files content as a dict, in format of
                {path1: content1, path2: content2}.
        @throws error.SuiteControlFileException when there is an error while
                listing.
        """
        try:
            return self._list_suite_controls(build, suite_name)
        except (requests.ConnectionError, CommunicationError,
                ResponseContentError) as err:
            logging.warn('GS Cache Error: %s', err)
            logging.warn(
                    'Falling back to devserver call of "list_suite_controls".')

        try:
            return self._fallback_server.list_suite_controls(
                    build, suite_name=suite_name if suite_name else '')
        except dev_server.DevServerException as err:
            raise error.SuiteControlFileException(err)

    def _list_suite_controls(self, build, suite_name=''):
        """'GS Cache' version of list_suite_controls."""
        test_suites = '%s/test_suites.tar.bz2' % build
        map_file_name = 'autotest/test_suites/suite_to_control_file_map'
        content_dict = self._api.extract(_CROS_IMAGE_ARCHIVE_BUCKET,
                                         test_suites, map_file_name)
        try:
            map_file_content = content_dict[map_file_name]
        except KeyError:
            raise ResponseContentError("File '%s' isn't in response: %s" %
                                       (map_file_name, content_dict))
        try:
            suite_to_control_files = json.loads(map_file_content)
        except ValueError as err:
            raise ResponseContentError(
                'Got ValueError "%s" when decoding to JSON format. The '
                'map file content is: %s' % (err, map_file_content))
        try:
            control_files = suite_to_control_files[suite_name]
            # The control files in control_files.tar have 'autotest/' prefix.
            control_files = [self._CONTROL_FILE_PREFIX + p
                             for p in control_files]
        except KeyError:
            control_files = ['*/control', '*/control.*']

        result_dict = self._api.extract(
                _CROS_IMAGE_ARCHIVE_BUCKET, '%s/control_files.tar' % build,
                control_files)
        # Remove the prefix of 'autotest/' from the control file names.
        return {k[self._CONTROL_FILE_PREFIX_LEN:]: v
                for k, v in result_dict.items()
                if k.startswith(self._CONTROL_FILE_PREFIX)}
