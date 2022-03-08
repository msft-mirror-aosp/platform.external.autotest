# Copyright 2021 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import logging
import random
import string

# Shell command to force unmount a mount point if it is mounted
FORCED_UMOUNT_DIR_IF_MOUNTPOINT_CMD = (
        'if mountpoint -q %(dir)s; then umount -l %(dir)s; fi')
# Shell command to set exec and suid flags
SET_MOUNT_FLAGS_CMD = 'mount -o remount,exec,suid %s'
# Shell command to send SIGHUP to dbus daemon
DBUS_RELOAD_COMMAND = 'killall -HUP dbus-daemon'


def extract_from_image(host, image_name, dest_dir):
    """
    Extract contents of an image to a directory.

    @param host: The DUT to execute the command on
    @param image_name: Name of image
    @param dest_dir: directory where contents of image will be placed.

    """

    if not host.path_exists('/var/lib/imageloader/%s' % image_name):
        raise Exception('Image %s not found on host %s' % (image_name, host))

    def gen_random_str(length):
        """
        Generate random string

        @param length: Length of the string

        @return random string of specified length

        """
        return ''.join(
                [random.choice(string.hexdigits) for _ in range(length)])

    image_mount_point = '/tmp/image_%s' % gen_random_str(8)

    # Create directories from scratch
    host.run(['rm', '-rf', dest_dir])
    host.run(['mkdir', '-p', '--mode', '0755', dest_dir, image_mount_point])

    try:
        # Mount image and copy content to the destination directory
        host.run([
                'imageloader', '--mount',
                '--mount_component=%s' % image_name,
                '--mount_point=%s' % image_mount_point
        ])

        host.run(['cp', '-r', '%s/*' % image_mount_point, '%s/' % dest_dir])
    except Exception as e:
        raise Exception(
                'Error extracting content from image %s on host %s ' %
                (image_name, host), e)
    finally:
        # Unmount image and remove the temporary directory
        host.run([
                'imageloader', '--unmount',
                '--mount_point=%s' % image_mount_point
        ])
        host.run(['rm', '-rf', image_mount_point])


def _stop_chrome_if_necessary(host):
    """
    Stop chrome if it is running.

    @param host: The DUT to execute the command on

    @return True if chrome was stopped. False otherwise.

    """
    status = host.run_output('status ui')
    if 'start' in status:
        return host.run('stop ui', ignore_status=True).exit_status == 0

    return False


def _mount_chrome(host, chrome_dir, chrome_mount_point):
    """
    Mount chrome to a mount point

    @param host: The DUT to execute the command on
    @param chrome_dir: directory where the chrome binary and artifacts
                       will be placed.
    @param chrome_mount_point: Chrome mount point

    """
    chrome_stopped = _stop_chrome_if_necessary(host)
    _umount_chrome(host, chrome_mount_point)

    # Mount chrome to the desired chrome directory
    # Upon restart, this version of chrome will be used instead.
    host.run(['mount', '--rbind', chrome_dir, chrome_mount_point])

    # Chrome needs partition to have exec and suid flags set
    host.run(SET_MOUNT_FLAGS_CMD % chrome_mount_point)

    # Send SIGHUP to dbus-daemon to tell it to reload its configs. This won't
    # pick up major changes (bus type, logging, etc.), but all we care about is
    # getting the latest policy from /opt/google/chrome/dbus so that Chrome will
    # be authorized to take ownership of its service names.
    host.run(DBUS_RELOAD_COMMAND, ignore_status=True)

    if chrome_stopped:
        host.run('start ui', ignore_status=True)


def _umount_chrome(host, chrome_mount_point):
    """
    Unmount chrome

    @param host: The DUT to execute the command on
    @param chrome_mount_point: Chrome mount point

    """
    chrome_stopped = _stop_chrome_if_necessary(host)
    # Unmount chrome. Upon restart, the default version of chrome
    # under the root partition will be used.
    try:
        host.run(FORCED_UMOUNT_DIR_IF_MOUNTPOINT_CMD %
                 {'dir': chrome_mount_point})
    except Exception as e:
        raise Exception('Exception during cleanup on host %s' % host, e)

    if chrome_stopped:
        host.run('start ui', ignore_status=True)


def setup_host(host, chrome_dir, chrome_mount_point):
    """
    Perform setup on host.

    Mount chrome to point to the version provisioned by TLS.
    The provisioning mechanism of chrome from the chrome builder is
    based on Lacros Tast Test on Skylab (go/lacros-tast-on-skylab).

    The lacros image provisioned by TLS contains the chrome binary
    and artifacts.

    @param host: The DUT to execute the command on
    @param chrome_dir: directory where the chrome binary and artifacts
                       will be placed.
    @param chrome_mount_point: Chrome mount point

    """
    logging.info("Setting up host:%s", host)
    try:
        extract_from_image(host, 'lacros', chrome_dir)
        if chrome_mount_point:
            _mount_chrome(host, '%s/out/Release' % chrome_dir,
                          chrome_mount_point)
    except Exception as e:
        raise Exception(
                'Exception while mounting %s on host %s' %
                (chrome_mount_point, host), e)


def cleanup_host(host, chrome_dir, chrome_mount_point):
    """
    Umount chrome and perform cleanup.

    @param host: The DUT to execute the command on
    @param chrome_dir: directory where the chrome binary and artifacts
                       is placed.
    @param chrome_mount_point: Chrome mount point

    """
    logging.info("Unmounting chrome on host: %s", host)
    try:
        if chrome_mount_point:
            _umount_chrome(host, chrome_mount_point)
        host.run(['rm', '-rf', chrome_dir])
    except Exception as e:
        raise Exception('Exception during cleanup on host %s' % host, e)
