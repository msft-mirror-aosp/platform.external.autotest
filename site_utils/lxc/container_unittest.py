#!/usr/bin/python
# Copyright 2017 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import argparse
import logging
import os
import tempfile
import shutil
import sys
import unittest
from contextlib import contextmanager

import common
from autotest_lib.client.bin import utils
from autotest_lib.client.common_lib import error
from autotest_lib.site_utils import lxc
from autotest_lib.site_utils.lxc import constants
from autotest_lib.site_utils.lxc import unittest_http
from autotest_lib.site_utils.lxc import unittest_logging
from autotest_lib.site_utils.lxc import utils as lxc_utils
from autotest_lib.site_utils.lxc.unittest_container_bucket \
        import FastContainerBucket


options = None

class ContainerTests(unittest.TestCase):
    """Unit tests for the Container class."""

    @classmethod
    def setUpClass(cls):
        cls.test_dir = tempfile.mkdtemp(dir=lxc.DEFAULT_CONTAINER_PATH,
                                        prefix='container_unittest_')
        cls.shared_host_path = os.path.join(cls.test_dir, 'host')

        # Use a container bucket just to download and set up the base image.
        cls.bucket = FastContainerBucket(cls.test_dir, cls.shared_host_path)

        if cls.bucket.base_container is None:
            logging.debug('Base container not found - reinitializing')
            cls.bucket.setup_base()
        else:
            logging.debug('base container found')
        cls.base_container = cls.bucket.base_container
        assert(cls.base_container is not None)


    @classmethod
    def tearDownClass(cls):
        cls.base_container = None
        if not options.skip_cleanup:
            cls.bucket.destroy_all()
            shutil.rmtree(cls.test_dir)


    def testInit(self):
        """Verifies that containers initialize correctly."""
        # Make a container that just points to the base container.
        container = lxc.Container.create_from_existing_dir(
            self.base_container.container_path,
            self.base_container.name)
        # Calling is_running triggers an lxc-ls call, which should verify that
        # the on-disk container is valid.
        self.assertFalse(container.is_running())


    def testInitInvalid(self):
        """Verifies that invalid containers can still be instantiated,
        if not used.
        """
        with tempfile.NamedTemporaryFile(dir=self.test_dir) as tmpfile:
            name = os.path.basename(tmpfile.name)
            container = lxc.Container.create_from_existing_dir(self.test_dir,
                                                               name)
            with self.assertRaises(error.ContainerError):
                container.refresh_status()


    def testDefaultHostname(self):
        """Verifies that the zygote starts up with a default hostname that is
        the lxc container name."""
        test_name = 'testHostname'
        with self.createContainer(name=test_name) as container:
            container.start(wait_for_network=True)
            hostname = container.attach_run('hostname').stdout.strip()
            self.assertEqual(test_name, hostname)


    def testSetHostnameRunning(self):
        """Verifies that the hostname can be set on a running container."""
        with self.createContainer() as container:
            expected_hostname = 'my-new-hostname'
            container.start(wait_for_network=True)
            container.set_hostname(expected_hostname)
            hostname = container.attach_run('hostname -f').stdout.strip()
            self.assertEqual(expected_hostname, hostname)


    def testSetHostnameNotRunningRaisesException(self):
        """Verifies that set_hostname on a stopped container raises an error.

        The lxc.utsname config setting is unreliable (it only works if the
        original container name is not a valid RFC-952 hostname, e.g. if it has
        underscores).

        A more reliable method exists for setting the hostname but it requires
        the container to be running.  To avoid confusion, setting the hostname
        on a stopped container is disallowed.

        This test verifies that the operation raises a ContainerError.
        """
        with self.createContainer() as container:
            with self.assertRaises(error.ContainerError):
                # Ensure the container is not running
                if container.is_running():
                    raise RuntimeError('Container should not be running.')
                container.set_hostname('foobar')


    def testClone(self):
        """Verifies that cloning a container works as expected."""
        clone = lxc.Container.clone(src=self.base_container,
                                    new_name="testClone",
                                    new_path=self.test_dir,
                                    snapshot=True)
        try:
            # Throws an exception if the container is not valid.
            clone.refresh_status()
        finally:
            clone.destroy()


    def testCloneWithoutCleanup(self):
        """Verifies that cloning a container to an existing name will fail as
        expected.
        """
        lxc.Container.clone(src=self.base_container,
                            new_name="testCloneWithoutCleanup",
                            new_path=self.test_dir,
                            snapshot=True)
        with self.assertRaises(error.ContainerError):
            lxc.Container.clone(src=self.base_container,
                                new_name="testCloneWithoutCleanup",
                                new_path=self.test_dir,
                                snapshot=True)


    def testCloneWithCleanup(self):
        """Verifies that cloning a container with cleanup works properly."""
        clone0 = lxc.Container.clone(src=self.base_container,
                                     new_name="testClone",
                                     new_path=self.test_dir,
                                     snapshot=True)
        clone0.start(wait_for_network=False)
        tmpfile = clone0.attach_run('mktemp').stdout
        # Verify that our tmpfile exists
        clone0.attach_run('test -f %s' % tmpfile)

        # Clone another container in place of the existing container.
        clone1 = lxc.Container.clone(src=self.base_container,
                                     new_name="testClone",
                                     new_path=self.test_dir,
                                     snapshot=True,
                                     cleanup=True)
        with self.assertRaises(error.CmdError):
            clone1.attach_run('test -f %s' % tmpfile)


    def testInstallSsp(self):
        """Verifies that installing the ssp in the container works."""
        # Hard-coded path to some golden data for this test.
        test_ssp = os.path.join(
                common.autotest_dir,
                'site_utils', 'lxc', 'test', 'test_ssp.tar.bz2')
        # Create a container, install the self-served ssp, then check that it is
        # installed into the container correctly.
        with self.createContainer() as container:
            with unittest_http.serve_locally(test_ssp) as url:
                container.install_ssp(url)
            container.start(wait_for_network=False)

            # The test ssp just contains a couple of text files, in known
            # locations.  Verify the location and content of those files in the
            # container.
            cat = lambda path: container.attach_run('cat %s' % path).stdout
            test0 = cat(os.path.join(constants.CONTAINER_AUTOTEST_DIR,
                                     'test.0'))
            test1 = cat(os.path.join(constants.CONTAINER_AUTOTEST_DIR,
                                     'dir0', 'test.1'))
            self.assertEquals('the five boxing wizards jumped quickly',
                              test0)
            self.assertEquals('the quick brown fox jumps over the lazy dog',
                              test1)


    def testInstallControlFile(self):
        """Verifies that installing a control file in the container works."""
        _unused, tmpfile = tempfile.mkstemp()
        with self.createContainer() as container:
            container.install_control_file(tmpfile)
            container.start(wait_for_network=False)
            # Verify that the file is found in the container.
            container.attach_run(
                'test -f %s' % os.path.join(lxc.CONTROL_TEMP_PATH,
                                            os.path.basename(tmpfile)))


    def testCopyFile(self):
        """Verifies that files are correctly copied into the container."""
        control_string = 'amazingly few discotheques provide jukeboxes'
        with tempfile.NamedTemporaryFile() as tmpfile:
            tmpfile.write(control_string)
            tmpfile.flush()

            with self.createContainer() as container:
                dst = os.path.join(constants.CONTAINER_AUTOTEST_DIR,
                                   os.path.basename(tmpfile.name))
                container.copy(tmpfile.name, dst)
                container.start(wait_for_network=False)
                # Verify the file content.
                test_string = container.attach_run('cat %s' % dst).stdout
                self.assertEquals(control_string, test_string)


    def testCopyDirectory(self):
        """Verifies that directories are correctly copied into the container."""
        control_string = 'pack my box with five dozen liquor jugs'
        with lxc_utils.TempDir() as tmpdir:
            fd, tmpfile = tempfile.mkstemp(dir=tmpdir)
            f = os.fdopen(fd, 'w')
            f.write(control_string)
            f.close()

            with self.createContainer() as container:
                dst = os.path.join(constants.CONTAINER_AUTOTEST_DIR,
                                   os.path.basename(tmpdir))
                container.copy(tmpdir, dst)
                container.start(wait_for_network=False)
                # Verify the file content.
                test_file = os.path.join(dst, os.path.basename(tmpfile))
                test_string = container.attach_run('cat %s' % test_file).stdout
                self.assertEquals(control_string, test_string)


    def testMountDirectory(self):
        """Verifies that read-write mounts work."""
        with lxc_utils.TempDir() as tmpdir, self.createContainer() as container:
            dst = '/testMountDirectory/testMount'
            container.mount_dir(tmpdir, dst, readonly=False)
            container.start(wait_for_network=False)

            # Verify that the mount point is correctly bound, and is read-write.
            self.verifyBindMount(container, dst, tmpdir)
            container.attach_run('test -r %s -a -w %s' % (dst, dst))


    def testMountDirectoryReadOnly(self):
        """Verifies that read-only mounts work."""
        with lxc_utils.TempDir() as tmpdir, self.createContainer() as container:
            dst = '/testMountDirectoryReadOnly/testMount'
            container.mount_dir(tmpdir, dst, readonly=True)
            container.start(wait_for_network=False)

            # Verify that the mount point is correctly bound, and is read-only.
            self.verifyBindMount(container, dst, tmpdir)
            container.attach_run('test -r %s -a ! -w %s' % (dst, dst))


    def testMountDirectoryRelativePath(self):
        """Verifies that relative-path mounts work."""
        with lxc_utils.TempDir() as tmpdir, self.createContainer() as container:
            dst = 'testMountDirectoryRelativePath/testMount'
            container.mount_dir(tmpdir, dst, readonly=True)
            container.start(wait_for_network=False)

            # Verify that the mount points is correctly bound..
            self.verifyBindMount(container, dst, tmpdir)


    @contextmanager
    def createContainer(self, name=None):
        """Creates a container from the base container, for testing.
        Use this to ensure that containers get properly cleaned up after each
        test.

        @param name: An optional name for the new container.
        """
        if name is None:
            name = self.id().split('.')[-1]
        container = lxc.Container.clone(src=self.base_container,
                                        new_name=name,
                                        new_path=self.test_dir,
                                        snapshot=True)
        try:
            yield container
        finally:
            if not options.skip_cleanup:
                container.destroy()


    def verifyBindMount(self, container, container_path, host_path):
        """Verifies that a given path in a container is bind-mounted to a given
        path in the host system.

        @param container: The Container instance to be tested.
        @param container_path: The path in the container to compare.
        @param host_path: The path in the host system to compare.
        """
        container_inode = (container.attach_run('ls -id %s' % container_path)
                           .stdout.split()[0])
        host_inode = utils.run('ls -id %s' % host_path).stdout.split()[0]
        # Compare the container and host inodes - they should match.
        self.assertEqual(container_inode, host_inode)


def parse_options():
    """Parse command line inputs.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='Print out ALL entries.')
    parser.add_argument('--skip_cleanup', action='store_true',
                        help='Skip deleting test containers.')
    args, argv = parser.parse_known_args()

    # Hack: python unittest also processes args.  Construct an argv to pass to
    # it, that filters out the options it won't recognize.
    if args.verbose:
        argv.insert(0, '-v')
    argv.insert(0, sys.argv[0])

    return args, argv


if __name__ == '__main__':
    options, unittest_argv = parse_options()

    log_level=(logging.DEBUG if options.verbose else logging.INFO)
    unittest_logging.setup(log_level)

    unittest.main(argv=unittest_argv)
