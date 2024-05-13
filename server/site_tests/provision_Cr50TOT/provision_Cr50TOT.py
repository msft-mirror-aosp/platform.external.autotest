# Copyright 2019 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.


""" The autotest performing Cr50 update to the TOT image."""


import logging
import os
import re

from autotest_lib.client.common_lib.cros import cr50_utils
from autotest_lib.client.common_lib import error
from autotest_lib.server import utils
from autotest_lib.server.cros import gsutil_wrapper
from autotest_lib.server.cros.faft.cr50_test import Cr50Test


# TOT cr50 images are built as part of the reef image builder.
CR50_BUILDER = 'reef'
CR50_GS_URL = 'gs://chromeos-releases/dev-channel/' + CR50_BUILDER
# Firmware artifacts are stored in files like this.
#   ChromeOS-firmware-R79-12519.0.0-reef.tar.bz2
CR50_FIRMWARE_TARBALL = 'ChromeOS-firmware-%s-%s.tar.bz2'
CR50_IMAGE_PATH = 'cr50/ec.bin'

# Ti50 file info
TI50_GS_URL = 'gs://chromeos-releases/firmware-ti50-postsubmit/%s-*/ti50.tar.bz2'
TI50_FILENAME = 'ti50_Unknown_*_ti50-accessory-nodelocked-ro-premp.bin'

REMOTE_TMPDIR = '/tmp/gsc_tot_update'
VER_RE = r'R(\d*)-(\d*).(\d*).(\d*)'


def get_gs_paths(path):
    """Return a list of gs paths."""
    cmd = 'gsutil ls -- %s' % path
    return utils.system_output(cmd).splitlines()

# Wait 10 seconds for the update to take effect.
class provision_Cr50TOT(Cr50Test):
    """Update cr50 to TOT.

    The reef builder builds cr50. Fetch the image from the latest reef build
    and update cr50 to that image. This expects that the DUT is running node
    locked RO.
    """
    version = 1

    def get_latest_builds(self, board='reef-release',
                          bucket='chromeos-image-archive',
                          num_builds=5):
        """Gets the latest build for the given board.

        Args:
          board: The board for which the latest build needs to be fetched.
          bucket: The GS bucket name.
          num_builds: Number of builds to return.

        Raises:
          error.TestFail() if the List() method is unable to retrieve the
              contents of the path gs://<bucket>/<board> for any reason.
        """
        path = 'gs://%s/%s' % (bucket, board)
        try:
            contents = get_gs_paths(path)
            builds = []
            for content in contents:
                m = re.search(VER_RE, content)
                if not m:
                    continue
                builds.append(m.group())
            if not builds:
                return error.TestError('No builds found %r' % contents)
            latest_builds = sorted(builds, key=lambda x:
                    [int(v or 0) for v in re.search(VER_RE, x).groups()])
            latest_builds = latest_builds[(num_builds * -1):]
            latest_builds.reverse()
            logging.info('Checking latest builds %s', latest_builds)
            return latest_builds
        except Exception as e:
            raise error.TestFail('Could not determine the latest build due '
                                 'to exception: %s' % e)

    def get_ti50_build(self, latest_ver, remote_dir):
        """Download the TOT ti50 image from the postsubmit builder."""
        path = get_gs_paths(
                os.path.join(TI50_GS_URL % latest_ver, TI50_FILENAME))[0]
        logging.info('Using ti50 image from %s', path)
        bucket = os.path.dirname(path)
        filename = os.path.basename(path)
        # Download the firmware artifacts from google storage.
        gsutil_wrapper.copy_private_bucket(host=self.host,
                                           bucket=bucket,
                                           filename=filename,
                                           destination=remote_dir)
        return os.path.join(remote_dir, filename)


    def get_cr50_build(self, latest_ver, remote_dir):
        """Download the TOT cr50 image from the reef artifacts."""
        bucket = os.path.join(CR50_GS_URL, latest_ver.split('-')[-1])
        filename = CR50_FIRMWARE_TARBALL % (latest_ver, CR50_BUILDER)
        logging.info('Using cr50 image from %s', latest_ver)

        # Download the firmware artifacts from google storage.
        gsutil_wrapper.copy_private_bucket(host=self.host,
                                           bucket=bucket,
                                           filename=filename,
                                           destination=remote_dir)

        # Extract the cr50 image.
        dut_path = os.path.join(remote_dir, filename)
        result = self.host.run('tar xfv %s -C %s' % (dut_path, remote_dir))
        return os.path.join(remote_dir, CR50_IMAGE_PATH)


    def get_latest_gsc_build(self):
        self.host.run('mkdir -p %s' % (REMOTE_TMPDIR))
        latest_builds = self.get_latest_builds()
        for latest_build in latest_builds:
            try:
                if self.gsc.NAME == 'ti50':
                    return self.get_ti50_build(latest_build, REMOTE_TMPDIR)
                return self.get_cr50_build(latest_build, REMOTE_TMPDIR)
            except Exception as e:
                logging.warning('Unable to find %s gsc image %s', latest_build,
                                e)
        raise error.TestFail('Unable to find latest gsc image in %s' %
                             latest_builds)


    def run_once(self, host, force=False):
        """Update GSC to a recent TOT image."""
        # TODO(mruthven): remove once the test is successfully scheduled.
        logging.info('SUCCESSFULLY SCHEDULED PROVISION CR50 TOT UPDATE')
        if not force:
            logging.info('skipping update')
            return
        self._provision_update = True
        logging.info('%s version %s', self.gsc.NAME,
                     host.servo.get('cr50_version'))
        self.host = host
        gsc_path = self.get_latest_gsc_build()
        logging.info('%s image is at %s', self.gsc.NAME, gsc_path)
        local_path = os.path.join(self.resultsdir, 'gsc.bin.tot')
        self.host.get_file(gsc_path, local_path)

        cr50_utils.GSCTool(self.host, ['-a', gsc_path])

        self.gsc.wait_for_reboot(
                timeout=self.faft_config.gsc_update_wait_for_reboot)
        gsc_version = self.gsc.get_active_version_info()[3].split('/')[-1]
        logging.info('%s running %s after update', self.gsc.NAME, gsc_version)
        self.make_rootfs_writable()
        cr50_utils.InstallImage(self.host, local_path, self.gsc.DUT_PREPVT)
