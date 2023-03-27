# Lint as:python3
# Copyright 2023 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Class to hold the Floss enums."""

from enum import IntEnum


class BtTransport(IntEnum):
    """Bluetooth transport type."""
    AUTO = 0
    BR_EDR = 1
    LE = 2


class GattWriteRequestStatus(IntEnum):
    """Gatt write request status."""
    SUCCESS = 0
    FAIL = 1
    BUSY = 2


class GattWriteType(IntEnum):
    """GATT write type."""
    INVALID = 0
    WRITE_NO_RSP = 1
    WRITE = 2
    WRITE_PREPARE = 3


class LePhy(IntEnum):
    """Bluetooth LE physical type."""
    INVALID = 0
    PHY1M = 1
    PHY2M = 2
    PHY_CODED = 3


class GattStatus(IntEnum):
    """Bluetooth GATT return status."""
    SUCCESS = 0x00
    INVALID_HANDLE = 0x01
    READ_NOT_PERMIT = 0x02
    WRITE_NOT_PERMIT = 0x03
    INVALID_PDU = 0x04
    INSUF_AUTHENTICATION = 0x05
    REQ_NOT_SUPPORTED = 0x06
    INVALID_OFFSET = 0x07
    INSUF_AUTHORIZATION = 0x08
    PREPARE_Q_FULL = 0x09
    NOT_FOUND = 0x0A
    NOT_LONG = 0x0B
    INSUF_KEY_SIZE = 0x0C
    INVALID_ATTRLEN = 0x0D
    ERR_UNLIKELY = 0x0E
    INSUF_ENCRYPTION = 0x0F
    UNSUPPORT_GRP_TYPE = 0x10
    INSUF_RESOURCE = 0x11
    DATABASE_OUT_OF_SYNC = 0x12
    VALUE_NOT_ALLOWED = 0x13
    ILLEGAL_PARAMETER = 0x87
    TOO_SHORT = 0x7F
    NO_RESOURCES = 0x80
    INTERNAL_ERROR = 0x81
    WRONG_STATE = 0x82
    DB_FULL = 0x83
    BUSY = 0x84
    ERROR = 0x85
    CMD_STARTED = 0x86
    PENDING = 0x88
    AUTH_FAIL = 0x89
    MORE = 0x8A
    INVALID_CFG = 0x8B
    SERVICE_STARTED = 0x8C
    ENCRYPTED_NO_MITM = 0x8D
    NOT_ENCRYPTED = 0x8E
    CONGESTED = 0x8F
    DUP_REG = 0x90
    ALREADY_OPEN = 0x91
    CANCEL = 0x92


class BtStatus(IntEnum):
    """Bluetooth return status."""
    SUCCESS = 0
    FAIL = 1
    NOT_READY = 2
    NO_MEMORY = 3
    BUSY = 4
    DONE = 5
    UNSUPPORTED = 6
    INVALID_PARAM = 7
    UNHANDLED = 8
    AUTH_FAILURE = 9
    REMOTE_DEVICE_DOWN = 10
    AUTH_REJECTED = 11
    JNI_ENVIRONMENT_ERROR = 12
    JNI_THREAD_ATTACH_ERROR = 13
    WAKE_LOCK_ERROR = 14


class SocketType(IntEnum):
    """Socket types."""
    GT_SOCK_ANY = 0
    GT_SOCK_STREAM = 1
    GT_SOCK_DGRAM = 2
    GT_SOCK_RAW = 3
    GT_SOCK_RDM = 4
    GT_SOCK_SEQPACKET = 5
    GT_SOCK_DCCP = 6
    GT_SOCK_PACKET = 10


class SuspendMode(IntEnum):
    """Bluetooth suspend mode."""
    NORMAL = 0
    SUSPENDING = 1
    SUSPENDED = 2
    RESUMING = 3


class ScanType(IntEnum):
    """Bluetooth scan type."""
    ACTIVE = 0
    PASSIVE = 1


class BondState(IntEnum):
    """Bluetooth bonding state."""
    NOT_BONDED = 0
    BONDING = 1
    BONDED = 2


class Transport(IntEnum):
    """Bluetooth transport type."""
    AUTO = 0
    BREDR = 1
    LE = 2


class SspVariant(IntEnum):
    """Bluetooth SSP variant type."""
    PASSKEY_CONFIRMATION = 0
    PASSKEY_ENTRY = 1
    CONSENT = 2
    PASSKEY_NOTIFICATION = 3