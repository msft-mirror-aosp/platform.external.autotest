# Copyright 2018 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import json
import logging
import os
import requests
import shutil

from autotest_lib.client.bin import test, utils
from autotest_lib.client.common_lib import error
from autotest_lib.client.cros.update_engine import update_engine_util

class UpdateEngineTest(test.test, update_engine_util.UpdateEngineUtil):
    """Base class for update engine client tests."""

    _NETWORK_INTERFACES = ['eth0', 'eth1', 'eth2']


    def initialize(self):
        """Initialize for this test."""
        self._create_update_engine_variables()
        self._internet_was_disabled = False


    def cleanup(self):
        """Cleanup for this test."""
        # Make sure to grab the update engine log for every test run.
        shutil.copy(self._UPDATE_ENGINE_LOG, self.resultsdir)

        # Ensure ethernet adapters are back on
        self._enable_internet()


    def _enable_internet(self, ping_server='google.com'):
        """
        Re-enables the internet connection.

        @param ping_server: The server to ping to check we are online.

        """
        if not self._internet_was_disabled:
            return

        self._internet_was_disabled = False
        logging.debug('Before reconnect: %s', utils.run('ifconfig'))
        for eth in self._NETWORK_INTERFACES:
            utils.run('ifconfig %s up' % eth, ignore_status=True)
        utils.start_service('recover_duts', ignore_status=True)

        # Print ifconfig to help debug DUTs that stay offline.
        logging.debug('After reconnect: %s', utils.run('ifconfig'))

        # We can't return right after reconnecting the network or the server
        # test may not receive the message. So we wait a bit longer for the
        # DUT to be reconnected.
        utils.poll_for_condition(lambda: utils.ping(ping_server,
                                                    tries=3, timeout=10) == 0,
                                 timeout=120,
                                 sleep_interval=1,
                                 exception=error.TestFail(
                                     'Ping failed after reconnecting network'))


    def _disable_internet(self, ping_server='google.com'):
        """Disable the internet connection"""
        self._internet_was_disabled = True
        try:
            logging.debug('Before disconnect: %s', utils.run('ifconfig'))
            # DUTs in the lab have a service called recover_duts that is used to
            # check that the DUT is online and if it is not it will bring it
            # back online. We will need to stop this service for the length
            # of this test.
            utils.stop_service('recover_duts', ignore_status=True)
            for eth in self._NETWORK_INTERFACES:
                result = utils.run('ifconfig %s down' % eth, ignore_status=True)
                logging.debug(result)

            # Print ifconfig to help debug DUTs that stay online.
            logging.debug('After disconnect: %s', utils.run('ifconfig'))

            # Make sure we are offline
            utils.poll_for_condition(lambda: utils.ping(ping_server,
                                                        deadline=5,
                                                        timeout=5) != 0,
                                     timeout=60,
                                     sleep_interval=1,
                                     desc='Ping failure while offline.')
        except (error.CmdError, utils.TimeoutError):
            logging.exception('Failed to disconnect one or more interfaces.')
            logging.debug(utils.run('ifconfig', ignore_status=True))
            raise error.TestFail('Disabling the internet connection failed.')

    def _get_payload_properties_file(self, payload_url, target_dir, **kwargs):
        """
        Downloads the payload properties file into a directory.

        @param payload_url: The URL to the update payload file.
        @param target_dir: The directory to download the file into.
        @param kwargs: A dictionary of key/values that needs to be overridden on
                the payload properties file.

        """
        payload_props_url = payload_url + '.json'
        _, _, file_name = payload_props_url.rpartition('/')
        try:
            response = json.loads(requests.get(payload_props_url).text)

            # Override existing keys if any.
            for k, v in kwargs.iteritems():
                # Don't set default None values. We don't want to override good
                # values to None.
                if v is not None:
                    response[k] = v

            with open(os.path.join(target_dir, file_name), 'w') as fp:
                json.dump(response, fp)

        except (requests.exceptions.RequestException,
                IOError,
                ValueError) as err:
            raise error.TestError(
                'Failed to get update payload properties: %s with error: %s' %
                (payload_props_url, err))
