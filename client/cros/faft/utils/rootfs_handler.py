# Copyright 2014 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""A module containing rootfs handler class."""

import os
import re

KERNEL_TMP_FILE_NAME = 'kernel_dump'
ROOTFS_TMP_FILE_NAME = 'rootfs_dump'
ROOTFS_OFFSET_TMP_FILE_NAME = 'rootfs_offset'

_KERNEL_MAP = {'A': '2', 'B': '4'}
_ROOTFS_MAP = {'A': '3', 'B': '5'}
_DM_DEVICE = 'verifyroot'
_DM_DEV_PATH = os.path.join('/dev/mapper', _DM_DEVICE)


class RootfsHandler(object):
    """An object to provide ChromeOS root FS related actions.

    It provides functions to verify the integrity of the root FS.

    @type os_if: autotest_lib.client.cros.faft.utils.os_interface.OSInterface
    """

    def __init__(self, os_if):
        self.os_if = os_if
        self.root_dev = None
        self.kernel_dump_file = None
        self.initialized = False

    def verify_rootfs(self, section):
        """Verifies the integrity of the root FS.

        @param section: The rootfs to verify. May be A or B.
        """
        kernel_path = self.os_if.join_part(self.root_dev,
                                           _KERNEL_MAP[section.upper()])
        rootfs_path = self.os_if.join_part(self.root_dev,
                                           _ROOTFS_MAP[section.upper()])
        (table, partition_size) = self._verity_table(kernel_path)

        if table.find('PARTUUID=%U/PARTNROFF=1') < 0:
            return False
        table = table.replace('PARTUUID=%U/PARTNROFF=1', rootfs_path)
        # Cause I/O error on invalid bytes
        table += ' error_behavior=eio'

        self._remove_mapper()
        assert not self.os_if.path_exists(_DM_DEV_PATH)
        self.os_if.run_shell_command(
                "dmsetup create -r %s --table '%s'" % (_DM_DEVICE, table))
        assert self.os_if.path_exists(_DM_DEV_PATH)
        try:
            count = self.os_if.get_file_size(_DM_DEV_PATH)
            return count == partition_size
        except:
            return False
        finally:
            self._remove_mapper()

    def corrupt_rootfs_verity(self, section):
        """Corrupts verity hashes of the root Fs.

        @param section: The rootfs to corrupt. May be A or B.
        """
        kernel_path = self.os_if.join_part(self.root_dev,
                                           _KERNEL_MAP[section.upper()])
        rootfs_path = self.os_if.join_part(self.root_dev,
                                           _ROOTFS_MAP[section.upper()])
        (offset, count) = self._verity_range(kernel_path)

        self.os_if.run_shell_command(
                'dd if=/dev/zero of=%s seek=%d count=%d bs=1M '
                'iflag=count_bytes oflag=seek_bytes' %
                (rootfs_path, offset, count))

    def dump_rootfs_verity(self, section):
        """Dumps verity hashes of the root FS.

        @param section: The rootfs to dump. May be A or B.
        """
        kernel_path = self.os_if.join_part(self.root_dev,
                                           _KERNEL_MAP[section.upper()])
        rootfs_path = self.os_if.join_part(self.root_dev,
                                           _ROOTFS_MAP[section.upper()])
        (offset, count) = self._verity_range(kernel_path)

        self._dump_rootfs_verity(rootfs_path, offset, count)

    def restore_rootfs_verity(self, section):
        """Restores verity hashes of the root FS.

        @param section: The rootfs to restore. May be A or B.
        """
        rootfs_path = self.os_if.join_part(self.root_dev,
                                           _ROOTFS_MAP[section.upper()])

        self.os_if.run_shell_command(
                'dd if=%s of=%s seek=`cat %s` bs=1M '
                'oflag=seek_bytes' %
                (self.rootfs_dump_file, rootfs_path, self.rootfs_offset_file))

    def _verity_table(self, kernel_path):
        """Returns verity table of a kernel.

        @param kernel_path: The path to a kernel device.
        """
        # vbutil_kernel won't operate on a device, only a file.
        self.os_if.run_shell_command('dd if=%s of=%s' %
                                     (kernel_path, self.kernel_dump_file))
        vbutil_kernel = self.os_if.run_shell_command_get_output(
                'vbutil_kernel --verify %s --verbose' % self.kernel_dump_file)
        DM_REGEXP = re.compile(
                r'dm="(?:1 )?vroot none ro(?: 1)?,(0 (\d+) .+)"')
        match = DM_REGEXP.search('\n'.join(vbutil_kernel))
        return (match.group(1), int(match.group(2)) * 512)

    def _verity_range(self, kernel_path):
        """Returns (offset, count) of the rootfs verity hashes of the kernel.

        @param kernel_path: The path to a kernel device.
        """
        (table, partition_size) = self._verity_table(kernel_path)
        hash_size = partition_size / 4096 * 64 + 512
        return (partition_size, hash_size)

    def _dump_rootfs_verity(self, rootfs_path, offset, count):
        """Dumps verity hashes of the root FS.

        @param rootfs_path: The path to a root FS device.
        @param offset: The offset of hashes of the rootfs in bytes.
        @param count: The amount of bytes to dump.
        """
        self.os_if.run_shell_command(
                'dd if=%s of=%s skip=%d count=%d bs=1M '
                'iflag=count_bytes,skip_bytes' %
                (rootfs_path, self.rootfs_dump_file, offset, count))
        self.os_if.run_shell_command('echo %d > %s' %
                                     (offset, self.rootfs_offset_file))

    def _remove_mapper(self):
        """Removes the dm device mapper used by this class."""
        if self.os_if.path_exists(_DM_DEV_PATH):
            self.os_if.run_shell_command_get_output(
                    'dmsetup remove %s' % _DM_DEVICE)

    def init(self):
        """Initialize the rootfs handler object."""
        self.root_dev = self.os_if.get_root_dev()
        self.kernel_dump_file = self.os_if.state_dir_file(KERNEL_TMP_FILE_NAME)
        self.rootfs_dump_file = self.os_if.state_dir_file(ROOTFS_TMP_FILE_NAME)
        self.rootfs_offset_file = self.os_if.state_dir_file(
                ROOTFS_OFFSET_TMP_FILE_NAME)
        self.initialized = True
