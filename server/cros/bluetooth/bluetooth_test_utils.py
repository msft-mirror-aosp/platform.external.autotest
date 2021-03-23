"""Provides utilities to support bluetooth adapter tests"""

from __future__ import absolute_import

import logging
import re
import uuid

import common
from autotest_lib.client.bin.input.linux_input import EV_KEY
from autotest_lib.server.cros.bluetooth.debug_linux_keymap import (
        linux_input_keymap)
from ast import literal_eval as make_tuple


def reconstruct_string(events):
    """ Tries to reconstruct a string from linux input in a simple way

    @param events: list of event objects received over the BT channel

    @returns: reconstructed string
    """
    recon = []

    for ev in events:
        # If it's a key pressed event
        if ev.type == EV_KEY and ev.value == 1:
            recon.append(linux_input_keymap.get(ev.code, "_"))

    return "".join(recon)


def parse_trace_file(filename):
    """ Reads contents of trace file

    @param filename: location of trace file on disk

    @returns: structure containing contents of filename
    """

    contents = []

    try:
        with open(filename, 'r') as mf:
            for line in mf:
                # Reconstruct tuple and add to trace
                contents.append(make_tuple(line))
    except EnvironmentError:
        logging.error('Unable to open file %s', filename)
        return None

    return contents


class Bluetooth_UUID(uuid.UUID):
    """A class to manipulate Bluetooth UUIDs."""

    BLUETOOTH_BASE_UUID_FORMAT = '%s-0000-1000-8000-00805F9B34FB'

    def __init__(self, hex_str):
        super(Bluetooth_UUID, self).__init__(hex_str)


    @classmethod
    def create_valid_uuid(cls, hex_str):
        """Create valid long UUIDs based on Bluetooth short UUIDs.

        @param hex_str: the hex string that represents a short or long UUID.

        @returns: the UUID object if successful; or None otherwise.
        """
        h = re.sub('^0x', '', hex_str).replace('-', '')

        # The Bluetooth spec only allowed short UUIDs in 16 bits or 32 bits.
        # The long UUID takes 128 bits.
        # Reference:
        # www.bluetooth.com/specifications/assigned-numbers/service-discovery
        hlen = len(h)
        if hlen not in (4, 8, 32):
            return None

        # Convert the short UUIDs to the full UUID.
        if hlen in (4, 8):
            h = cls.BLUETOOTH_BASE_UUID_FORMAT % h.zfill(8)

        return cls(h)


class BluetoothPolicy(object):
    """A helper class to keep popular bluetooth service lists.

    Refer to
    https://www.bluetooth.com/specifications/assigned-numbers/service-discovery/
    """
    UUID_HID = '0x1124'
    UUID_HOG = '0x1812'
    UUID_DIS = '0x180a'
    UUID_BATT = '0x180f'

    ALLOWLIST_CLASSIC_HID = UUID_HID
    ALLOWLIST_BLE_HID = ','.join([UUID_HOG, UUID_DIS, UUID_BATT])
    ALLOWLIST_BLE_HID_INCOMPLETE = ','.join([UUID_HOG, UUID_BATT])
