# Copyright (c) 2011 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import os
import logging
import shutil

from autotest_lib.client.bin import test
from autotest_lib.client.common_lib import error
from autotest_lib.client.cros.cros_disks import CrosDisksTester
from autotest_lib.client.cros.cros_disks import FilesystemTestDirectory
from autotest_lib.client.cros.cros_disks import FilesystemTestFile
from autotest_lib.client.cros.cros_disks import VirtualFilesystemImage
from collections import deque


def utf8(s):
    """Converts a Unicode string to a UTF-8 bytestring."""
    return s.encode('utf8')


class CrosDisksArchiveTester(CrosDisksTester):
    """A tester to verify archive support in CrosDisks."""

    def __init__(self, test):
        super(CrosDisksArchiveTester, self).__init__(test)
        self._data_dir = os.path.join(test.bindir, 'data')

    def _find_all_files(self, root_dir):
        """Returns all files under a directory and its sub-directories.

           This is a generator that performs a breadth-first-search of
           all files under a specified directory and its sub-directories.

        Args:
            root_dir: The root directory where the search starts from.
        Yields:
            Path of any found file relative to the root directory.
        """
        dirs_to_explore = deque([''])
        while len(dirs_to_explore) > 0:
            current_dir = dirs_to_explore.popleft()
            for path in os.listdir(os.path.join(root_dir, current_dir)):
                expanded_path = os.path.join(root_dir, current_dir, path)
                relative_path = os.path.join(current_dir, path)
                if os.path.isdir(expanded_path):
                    dirs_to_explore.append(relative_path)
                else:
                    yield relative_path

    def _test_archive(self, archive_path, want_content, password=None):
        logging.info('Mounting archive %r', archive_path)
        archive_name = os.path.basename(archive_path)

        options = []
        if password is not None: options.append(b'password=' + utf8(password))

        # Mount archive file via CrosDisks.
        self.cros_disks.mount(archive_path,
                              os.path.splitext(archive_path)[1], options)
        mount_result = self.cros_disks.expect_mount_completion({
                'status': 0,
                'source_path': archive_path,
                'mount_path': os.path.join('/media/archive', archive_name),
        })

        mount_path = utf8(mount_result['mount_path'])
        logging.info('Archive mounted at %r', mount_path)

        # Verify the content of the mounted archive file.
        logging.info('Verifying mounted archive contents')
        if not want_content.verify(mount_path):
            raise error.TestFail(
                    'Mounted archive %r does not have expected contents' %
                    archive_name)

        logging.info('Unmounting archive')
        self.cros_disks.unmount(mount_path, [])

    def _test_unicode(self, mount_path):
        # Test RAR V4 with Unicode BMP characters in file and directory
        # names.
        want = [
                FilesystemTestFile(
                        utf8(u'File D79F \uD79F.txt'),
                        utf8(u'Char U+D79F is \uD79F HANGUL SYLLABLE HIC\n')),
                FilesystemTestFile(' Space Oddity ', 'Mind the gap\n'),
                FilesystemTestDirectory('Level 1', [
                        FilesystemTestFile('Empty', ''),
                        FilesystemTestFile('Digits', '0123456789'),
                        FilesystemTestFile('Small', 'Small file\n'),
                        FilesystemTestDirectory('Level 2', [
                                FilesystemTestFile('Big', 'a' * 65536),
                        ]),
                ]),
        ]

        self._test_archive(os.path.join(mount_path, 'Format V4.rar'),
                           FilesystemTestDirectory('', want))

        # Test RAR V5 with Unicode BMP and non-BMP characters in file
        # and directory names.
        want += [
                FilesystemTestDirectory(utf8(u'Dir 1F601 \U0001F601'), [
                        FilesystemTestFile(
                                utf8(u'File 1F602 \U0001F602.txt'),
                                utf8(u'Char U+1F602 is \U0001F602 ' +
                                     u'FACE WITH TEARS OF JOY\n')),
                ]),
                FilesystemTestFile(
                        utf8(u'File 1F600 \U0001F600.txt'),
                        utf8(u'Char U+1F600 is \U0001F600 GRINNING FACE\n')),
        ]

        self._test_archive(os.path.join(mount_path, 'Format V5.rar'),
                           FilesystemTestDirectory('', want))

        self._test_archive(os.path.join(mount_path, 'Unicode.zip'),
                           FilesystemTestDirectory('', want))

    def _test_symlinks(self, mount_path):
        self._test_archive(
                os.path.join(mount_path, 'Symlinks.zip'),
                FilesystemTestDirectory(
                        '', [FilesystemTestFile('textfile', 'sample text\n')],
                        strict=True))

    def _test_multipart(self, mount_path):
        # Test multipart RARs.
        want = FilesystemTestDirectory('', [
                FilesystemTestFile(
                        'Lines', ''.join(
                                ['Line %03i\n' % (i + 1) for i in range(200)]))
        ])

        for archive_name in [
                'Multipart Old Style.rar',
                'Multipart New Style 01.rar',
                'Multipart New Style 02.rar',
                'Multipart New Style 03.rar',
        ]:
            self._test_archive(os.path.join(mount_path, archive_name), want)

    def _test_invalid(self, mount_path):
        for archive_name in [
                'Invalid.rar',
                'Invalid.zip',
                'Not There.rar',
                'Not There.zip',
        ]:
            archive_path = os.path.join(mount_path, archive_name)
            logging.info('Mounting archive %r', archive_path)

            # Mount archive file via CrosDisks.
            self.cros_disks.mount(archive_path,
                                  os.path.splitext(archive_path)[1])
            mount_result = self.cros_disks.expect_mount_completion({
                    'status': 12,  # MOUNT_ERROR_MOUNT_PROGRAM_FAILED
                    'source_path': archive_path,
                    'mount_path': '',
            })

    def _test_need_password(self, mount_path):
        fs1 = FilesystemTestDirectory('', [
                FilesystemTestFile('Secret.txt', 'This is my little secret\n')
        ])

        fs2 = FilesystemTestDirectory('', [
                FilesystemTestFile('ClearText.txt',
                                   'This is not encrypted.\n'),
                FilesystemTestFile('Encrypted AES-128.txt',
                                   'This is encrypted with AES-128.\n'),
                FilesystemTestFile('Encrypted AES-192.txt',
                                   'This is encrypted with AES-192.\n'),
                FilesystemTestFile('Encrypted AES-256.txt',
                                   'This is encrypted with AES-256.\n'),
                FilesystemTestFile('Encrypted ZipCrypto.txt',
                                   'This is encrypted with ZipCrypto.\n'),
        ])

        for archive_name, want in [
                ('Encrypted Full V4.rar', fs1),
                ('Encrypted Full V5.rar', fs1),
                ('Encrypted Partial V4.rar', fs1),
                ('Encrypted Partial V5.rar', fs1),
                ('Encrypted AES-128.zip', fs1),
                ('Encrypted AES-192.zip', fs1),
                ('Encrypted AES-256.zip', fs1),
                ('Encrypted ZipCrypto.zip', fs1),
                ('Encrypted Various.zip', fs2),
        ]:
            archive_path = os.path.join(mount_path, archive_name)
            logging.info('Mounting archive %r', archive_path)

            # Trying to mount archive without providing password should fail.
            self.cros_disks.mount(archive_path,
                                  os.path.splitext(archive_path)[1])
            self.cros_disks.expect_mount_completion(
                    {'status': 13})  # MOUNT_ERROR_NEED_PASSWORD

            # Trying to mount archive with a wrong password should fail.
            for password in [b'', b'passwor', b'password ', b' password']:
                self.cros_disks.mount(archive_path,
                                      os.path.splitext(archive_path)[1],
                                      [b'password=' + password])
                self.cros_disks.expect_mount_completion(
                        {'status': 13})  # MOUNT_ERROR_NEED_PASSWORD

            # Mounting archive with right password should work.
            self._test_archive(os.path.join(mount_path, archive_name), want,
                               'password')

    def _test_strict_password(self, mount_path):
        """Tests that an invalid password is not accidentally accepted.
           https://crbug.com/1127752
        """
        archive_path = os.path.join(mount_path, 'Strict Password.zip')
        logging.info('Mounting archive %r', archive_path)

        # Trying to mount archive with a wrong password should fail.
        self.cros_disks.mount(archive_path,
                              os.path.splitext(archive_path)[1],
                              [b'password=sample'])
        self.cros_disks.expect_mount_completion(
                {'status': 13})  # MOUNT_ERROR_NEED_PASSWORD

    def _test_nested(self, incoming_mount_path):
        for archive_name in ['Nested.rar', 'Nested.zip']:
            archive_path = os.path.join(incoming_mount_path, archive_name)
            logging.info('Mounting archive %r', archive_path)

            # Mount archive file via CrosDisks.
            self.cros_disks.mount(archive_path,
                                  os.path.splitext(archive_path)[1])
            mount_result = self.cros_disks.expect_mount_completion({
                    'status': 0,
                    'source_path': archive_path,
                    'mount_path': os.path.join('/media/archive', archive_name),
            })

            mount_path = utf8(mount_result['mount_path'])
            logging.info('Archive mounted at %r', mount_path)

            self._test_unicode(mount_path)
            self._test_invalid(mount_path)

            logging.info('Unmounting archive')
            self.cros_disks.unmount(mount_path, [])

    def _test_duplicated_filenames(self, mount_path):
        want = [
                FilesystemTestFile(b'Simple.txt', b'Simple 1\n'),
                FilesystemTestFile(b'Simple (1).txt', b'Simple 2 \n'),
                FilesystemTestFile(b'Simple (2).txt', b'Simple 3  \n'),
                FilesystemTestFile(b'Suspense...', b'Suspense 1\n'),
                FilesystemTestFile(b'Suspense... (1)', b'Suspense 2 \n'),
                FilesystemTestFile(b'Suspense... (2)', b'Suspense 3  \n'),
                FilesystemTestFile(b'No Dot', b'No Dot 1\n'),
                FilesystemTestFile(b'No Dot (1)', b'No Dot 2 \n'),
                FilesystemTestFile(b'No Dot (2)', b'No Dot 3  \n'),
                FilesystemTestFile(b'.Hidden', b'Hidden 1\n'),
                FilesystemTestFile(b'.Hidden (1)', b'Hidden 2 \n'),
                FilesystemTestFile(b'.Hidden (2)', b'Hidden 3  \n'),
        ]

        self._test_archive(
                os.path.join(mount_path, 'Duplicate Filenames.zip'),
                FilesystemTestDirectory(
                        '',
                        [
                                FilesystemTestDirectory(
                                        'Folder', want, strict=True),
                                FilesystemTestDirectory(
                                        'With.Dot', want, strict=True)
                        ] + want,
                        strict=True))

    def _test_archives(self):
        # Create a FAT filesystem containing all our test archive files.
        logging.info('Creating FAT filesystem holding test archive files')
        with VirtualFilesystemImage(block_size=1024,
                                    block_count=65536,
                                    filesystem_type='vfat',
                                    mkfs_options=['-F', '32', '-n',
                                                  'ARCHIVE']) as image:
            image.format()
            image.mount(options=['sync'])

            logging.debug('Copying archive files to %r', image.mount_dir)
            for archive_name in [
                    'Duplicate Filenames.zip',
                    'Encrypted Full V4.rar',
                    'Encrypted Full V5.rar',
                    'Encrypted Partial V4.rar',
                    'Encrypted Partial V5.rar',
                    'Encrypted AES-128.zip',
                    'Encrypted AES-192.zip',
                    'Encrypted AES-256.zip',
                    'Encrypted ZipCrypto.zip',
                    'Encrypted Various.zip',
                    'Invalid.rar',
                    'Invalid.zip',
                    'Format V4.rar',
                    'Format V5.rar',
                    'Multipart Old Style.rar',
                    'Multipart Old Style.r00',
                    'Multipart New Style 01.rar',
                    'Multipart New Style 02.rar',
                    'Multipart New Style 03.rar',
                    'Nested.rar',
                    'Nested.zip',
                    'Strict Password.zip',
                    'Symlinks.zip',
                    'Unicode.zip',
            ]:
                logging.debug('Copying %r', archive_name)
                shutil.copy(os.path.join(self._data_dir, archive_name),
                            image.mount_dir)

            image.unmount()

            # Mount the FAT filesystem via CrosDisks. This simulates mounting
            # archive files on a removable drive, and ensures they are in a
            # location CrosDisks expects them to be in.
            loop_device = image.loop_device
            self.cros_disks.add_loopback_to_allowlist(loop_device)
            try:
                logging.info('Mounting FAT filesystem from %r via CrosDisks',
                             loop_device)
                self.cros_disks.mount(loop_device, '',
                                      ["ro", "nodev", "noexec", "nosuid"])
                mount_result = self.cros_disks.expect_mount_completion({
                        'status': 0,
                        'source_path': loop_device,
                })

                mount_path = utf8(mount_result['mount_path'])
                logging.info('FAT filesystem mounted at %r', mount_path)

                # Perform tests with the archive files in the mounted FAT
                # filesystem.
                self._test_unicode(mount_path)
                self._test_symlinks(mount_path)
                self._test_multipart(mount_path)
                self._test_invalid(mount_path)
                self._test_need_password(mount_path)
                self._test_strict_password(mount_path)
                self._test_nested(mount_path)
                self._test_duplicated_filenames(mount_path)

                logging.info('Unmounting FAT filesystem')
                self.cros_disks.unmount(mount_path, [])
            finally:
                self.cros_disks.remove_loopback_from_allowlist(loop_device)

    def get_tests(self):
        return [self._test_archives]


class platform_CrosDisksArchive(test.test):
    """Checks archive support in CrosDisks."""

    version = 1

    def run_once(self, *args, **kwargs):
        """Entry point of this test."""
        tester = CrosDisksArchiveTester(self)
        tester.run(*args, **kwargs)
