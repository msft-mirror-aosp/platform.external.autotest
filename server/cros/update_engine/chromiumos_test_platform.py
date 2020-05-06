# Copyright 2017 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import logging
import urlparse

from chromite.lib import auto_updater_transfer
from chromite.scripts import cros_update


class ChromiumOSTestPlatform(object):
    """Represents a CrOS device during autoupdate.

    This class is used with autoupdate_EndToEndTest. It has functions for all
    the device specific things that we need during an update: reboot,
    check active slot, login, get logs, start an update etc.
    """

    def __init__(self, host, autotest_devserver, results_dir):
        """Initialize the class.

        @param: host: The DUT host.
        @param: autotest_devserver: The devserver to stage payloads on.
        @param: results_dir: Where to save the autoupdate logs files.
        """
        self._host = host
        self._autotest_devserver = autotest_devserver
        self._results_dir = results_dir

    def install_version_without_cros_au_rpc(self, payload_uri,
                                            clobber_stateful=False):
        """Installs the specified payload onto the DUT.

        This method calls the cros_update.CrOSUpdateTrigger directly which in
        turn calls the auto_updater.ChromiumOSUpdater that updates the device
        using nebraska.py. This method requires the payload_uri to be already
        staged on a devserver.

        TODO(crbug.com/1071483): Eventually, the call to
        cros_update.CrOSUpdateTrigger should be replaced by a call to
        auto_updater.ChromiumOSUpdater for a much cleaner update process. At
        this time, cros_update.CrOSUpdateTrigger is being called because cros_au
        ends up triggering the update process via cros_update.CrOSUpdateTrigger
        which does not call the RunUpdate() method in
        auto_updater.ChromiumOSUpdater, but calls the individual update methods
        to perform the autoupdate. Since changing the call to cros_au is
        disruptive enough, it was decided that only the cros_au call will be
        taken out but rest of the flow will be kept as is to minimize the number
        of potential fallouts.

        @param payload_uri: GS URI of the payload to install.
        @param clobber_stateful: force a reinstall of the stateful image.

        @return path to the directory where the auto_updater stores its logs.
        """
        build_name, payload_file = self._get_update_parameters_from_uri(
            payload_uri)
        logging.info('Installing %s on the DUT', payload_uri)
        cros_updater = cros_update.CrOSUpdateTrigger(
            host_name=self._host.hostname,
            build_name=build_name,
            static_dir='',
            force_update=True,
            full_update=True,
            payload_filename=payload_file,
            clobber_stateful=clobber_stateful,
            staging_server=self._autotest_devserver.url(),
            transfer_class=auto_updater_transfer.LabEndToEndPayloadTransfer)
        cros_updater.TriggerAU()
        return cros_updater.request_logs_dir

    def _install_version(self, payload_uri, clobber_stateful=False):
        """Install the specified payload.

        This method calls the cros_au RPC on the devserver that in turn calls
        the auto_updater.ChromiumOSUpdater via cros_update script.

        TODO(crbug.com/1067394): Delete this method once all usages of
        cros_AU RPC have been deprecated.

        @param payload_uri: GS URI of the payload to install.
        @param clobber_stateful: force a reinstall of the stateful image.
        """
        build_name, payload_file = self._get_update_parameters_from_uri(
            payload_uri)
        logging.info('Installing %s on the DUT', payload_uri)

        try:
            ds = self._autotest_devserver
            _, pid = ds.auto_update(host_name=self._host.hostname,
                                    build_name=build_name,
                                    force_update=True,
                                    full_update=True,
                                    log_dir=self._results_dir,
                                    payload_filename=payload_file,
                                    clobber_stateful=clobber_stateful)
        except:
            logging.fatal('ERROR: Failed to install image on the DUT.')
            raise
        return pid


    @staticmethod
    def _get_update_parameters_from_uri(payload_uri):
        """Extract vars needed to update with a Google Storage payload URI.

        The two values we need are:
        (1) A build_name string e.g samus-release/R60-9583.0.0
        (2) A filename of the exact payload file to use for the update. This
        payload needs to have already been staged on the devserver.

        This function extracts those two values from a Google Storage URI.

        @param payload_uri: Google Storage URI to extract values from
        """
        archive_url, _, payload_file = payload_uri.rpartition('/')
        build_name = urlparse.urlsplit(archive_url).path.strip('/')

        # This test supports payload uris from two Google Storage buckets.
        # They store their payloads slightly differently. One stores them in
        # a separate payloads directory. E.g
        # gs://chromeos-image-archive/samus-release/R60-9583.0.0/blah.bin
        # gs://chromeos-releases/dev-channel/samus/9334.0.0/payloads/blah.bin
        if build_name.endswith('payloads'):
            build_name = build_name.rpartition('/')[0]
            payload_file = 'payloads/' + payload_file

        logging.debug('Extracted build_name: %s, payload_file: %s from %s.',
                      build_name, payload_file, payload_uri)
        return build_name, payload_file


    def install_source_image(self, source_payload_uri):
        """Install source payload on device.

        TODO(crbug.com/1067394): Delete this method once all usages of
        cros_AU RPC have been deprecated.
        """
        if source_payload_uri:
            self._install_version(source_payload_uri, clobber_stateful=True)


    def install_target_image(self, target_payload_uri):
        """Install target payload on the device.

        TODO(crbug.com/1067394): Delete this method once all usages of
        cros_AU RPC have been deprecated.
        """
        logging.info('Updating device to target image.')
        return self._install_version(target_payload_uri)
