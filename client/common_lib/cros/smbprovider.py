# Copyright 2018 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import logging
import os
import sys

import dbus

from autotest_lib.client.cros import upstart

def _proto_to_blob(proto):
    return dbus.ByteArray(proto.SerializeToString())

class SmbProvider(object):
    """
    Wrapper for D-Bus calls to SmbProvider Daemon

    The SmbProvider daemon handles calling the libsmbclient to communicate with
    an SMB server. This class is a wrapper to the D-Bus interface to the daemon.

    """

    _DBUS_SERVICE_NAME = "org.chromium.SmbProvider"
    _DBUS_SERVICE_PATH = "/org/chromium/SmbProvider"
    _DBUS_INTERFACE_NAME = "org.chromium.SmbProvider"

    # Default timeout in seconds for D-Bus calls.
    _DEFAULT_TIMEOUT = 120

    # Chronos user ID.
    _CHRONOS_UID = 1000

    def __init__(self, bus_loop, proto_binding_location):
        """
        Constructor.

        Creates and D-Bus connection to smbproviderd.

        @param bus_loop: Glib main loop object
        @param proto_binding_location: The location of generated python bindings
        for smbprovider protobufs.

        """

        sys.path.append(proto_binding_location)
        self._bus_loop = bus_loop
        self.restart()

    def restart(self):
        """
        Restarts smbproviderd and rebinds to D-Bus interface.

        """

        logging.info('restarting smbproviderd')
        upstart.restart_job('smbproviderd')

        try:
            # Get the interface as Chronos since only they are allowed to send
            # D-Bus messages to smbproviderd.
            os.setresuid(self._CHRONOS_UID, self._CHRONOS_UID, 0)

            bus = dbus.SystemBus(self._bus_loop)
            proxy = bus.get_object(self._DBUS_SERVICE_NAME,
                                   self._DBUS_SERVICE_PATH)
            self._smbproviderd = dbus.Interface(proxy,
                                                self._DBUS_INTERFACE_NAME)

        finally:
            os.setresuid(0, 0, 0)

    def stop(self):
        """
        Stops smbproviderd.

        """

        logging.info('stopping smbproviderd')

        try:
            upstart.stop_job('smbproviderd')

        finally:
            self._smbproviderd = None

    def mount(self, mount_path, workgroup, username, password):
        """
        Mounts a share.

        @param mount_path: Path of the share to mount.
        @param workgroup: Workgroup for the mount.
        @param username: Username for the mount.
        @param password: Password for the mount.

        @return A tuple with the ErrorType and the mount id returned the D-Bus
        call.

        """

        logging.info("Mounting: %s", mount_path)

        from directory_entry_pb2 import MountOptionsProto

        proto = MountOptionsProto()
        proto.path = mount_path
        proto.workgroup = workgroup
        proto.username = username

        with self.PasswordFd(password) as password_fd:
            return self._smbproviderd.Mount(_proto_to_blob(proto),
                                            dbus.types.UnixFd(password_fd),
                                            timeout=self._DEFAULT_TIMEOUT,
                                            byte_arrays=True)

    def unmount(self, mount_id):
        """
        Unmounts a share.

        @param mount_id: Mount ID to be umounted.

        @return: ErrorType from the returned D-Bus call.

        """

        logging.info("Unmounting: %s", mount_id)

        from directory_entry_pb2 import UnmountOptionsProto

        proto = UnmountOptionsProto()
        proto.mount_id = mount_id

        return self._smbproviderd.Unmount(_proto_to_blob(proto))

    def read_directory(self, mount_id, directory_path):
        """
        Reads a directory.

        @param mount_id: Mount ID corresponding to the share.
        @param directory_path: Path of the directory to read.

        @return A tuple with the ErrorType and the DirectoryEntryListProto blob
        string returned by the D-Bus call.

        """

        logging.info("Reading directory: %s", directory_path)

        from directory_entry_pb2 import ReadDirectoryOptionsProto
        from directory_entry_pb2 import DirectoryEntryListProto
        from directory_entry_pb2 import ERROR_OK

        proto = ReadDirectoryOptionsProto()
        proto.mount_id = mount_id
        proto.directory_path = directory_path

        error, entries_blob = self._smbproviderd.ReadDirectory(
                _proto_to_blob(proto),
                timeout=self._DEFAULT_TIMEOUT,
                byte_arrays=True)

        entries = DirectoryEntryListProto()
        if error == ERROR_OK:
            entries.ParseFromString(entries_blob)

        return error, entries

    def get_metadata(self, mount_id, entry_path):
        """
        Gets metadata for an entry.

        @param mount_id: Mount ID from the mounted share.
        @param entry_path: Path of the entry.

        @return A tuple with the ErrorType and the GetMetadataEntryOptionsProto
        blob string returned by the D-Bus call.

        """

        logging.info("Getting metadata for %s", entry_path)

        from directory_entry_pb2 import GetMetadataEntryOptionsProto
        from directory_entry_pb2 import DirectoryEntryProto
        from directory_entry_pb2 import ERROR_OK

        proto = GetMetadataEntryOptionsProto()
        proto.mount_id = mount_id
        proto.entry_path = entry_path

        error, entry_blob = self._smbproviderd.GetMetadataEntry(
                _proto_to_blob(proto),
                timeout=self._DEFAULT_TIMEOUT,
                byte_arrays=True)

        entry = DirectoryEntryProto()
        if error == ERROR_OK:
            entry.ParseFromString(entry_blob)

        return error, entry

    def open_file(self, mount_id, file_path, writeable):
        """
        Opens a file.

        @param mount_id: Mount ID from the mounted share.
        @param file_path: Path of the file to be opened.
        @param writeable: Whether the file should be opened with write access.

        @return A tuple with the ErrorType and the File ID of the opened file.

        """

        logging.info("Opening file: %s", file_path)

        from directory_entry_pb2 import OpenFileOptionsProto

        proto = OpenFileOptionsProto()
        proto.mount_id = mount_id
        proto.file_path = file_path
        proto.writeable = writeable

        return self._smbproviderd.OpenFile(_proto_to_blob(proto),
                                           timeout=self._DEFAULT_TIMEOUT,
                                           byte_arrays=True)

    def close_file(self, mount_id, file_id):
        """
        Closes a file.

        @param mount_id: Mount ID from the mounted share.
        @param file_id: ID of the file to be closed.

        @return ErrorType returned from the D-Bus call.

        """

        logging.info("Closing file: %s", file_id)

        from directory_entry_pb2 import CloseFileOptionsProto

        proto = CloseFileOptionsProto()
        proto.mount_id = mount_id
        proto.file_id = file_id

        return self._smbproviderd.CloseFile(_proto_to_blob(proto),
                                            timeout=self._DEFAULT_TIMEOUT,
                                            byte_arrays=True)

    def read_file(self, mount_id, file_id, offset, length):
        """
        Reads a file.

        @param mount_id: Mount ID from the mounted share.
        @param file_id: ID of the file to be read.
        @param offset: Offset to start reading.
        @param length: Length in bytes to read.

        @return A tuple with ErrorType and and a buffer containing the data
        read.

        """

        logging.info("Reading file: %s", file_id)

        from directory_entry_pb2 import ReadFileOptionsProto
        from directory_entry_pb2 import ERROR_OK

        proto = ReadFileOptionsProto()
        proto.mount_id = mount_id
        proto.file_id = file_id
        proto.offset = offset
        proto.length = length

        error, fd = self._smbproviderd.ReadFile(_proto_to_blob(proto),
                                                timeout=self._DEFAULT_TIMEOUT,
                                                byte_arrays=True)

        data = ''
        if error == ERROR_OK:
            data = os.read(fd.take(), length)

        return error, data

    def create_file(self, mount_id, file_path):
        """
        Creates a file.

        @param mount_id: Mount ID from the mounted share.
        @param file_path: Path of the file to be created.

        @return ErrorType returned from the D-Bus call.

        """

        logging.info("Creating file: %s", file_path)

        from directory_entry_pb2 import CreateFileOptionsProto

        proto = CreateFileOptionsProto()
        proto.mount_id = mount_id
        proto.file_path = file_path

        return self._smbproviderd.CreateFile(_proto_to_blob(proto),
                                             timeout=self._DEFAULT_TIMEOUT,
                                             byte_arrays=True)

    class PasswordFd(object):
        """
        Writes password into a file descriptor.

        Use in a 'with' statement to automatically close the returned file
        descriptor.

        @param password: Plaintext password string.

        @return A file descriptor (pipe) containing the password.

        """

        def __init__(self, password):
            self._password = password
            self._read_fd = None

        def __enter__(self):
            """Creates the password file descriptor."""

            self._read_fd, write_fd = os.pipe()
            os.write(write_fd, self._password)
            os.close(write_fd)
            return self._read_fd

        def __exit__(self, mytype, value, traceback):
            """Closes the password file descriptor again."""

            if self._read_fd:
                os.close(self._read_fd)