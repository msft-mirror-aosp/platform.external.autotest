# Copyright 2021 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# TODO(b/356484951): Remove from PVS testplans and remove this file.

import array
import fcntl
import os
import struct
import uuid
import logging
from enum import Enum

from autotest_lib.client.bin import test, utils
from autotest_lib.client.common_lib import error

EOP_CMD = Enum('EOP_CMD', ['GEN_GET_BOOT_STATE','GEN_GET_EOP_STATE'])

class firmware_CheckEOPState(test.test):
    """Validates that the ME has been told by firmware that POST is done"""
    # Needed by autotest
    version = 1

    def read_post_boot_state(self):
        """Fail if the ME should be capable of reporting EOP but doesn't."""
        HECI_MKHI = uuid.UUID('{8e6a6715-9abc-4043-88ef-9e39c6f63e0f}')
        IOCTL_MEI_CONNECT_CLIENT = 0xc0104801  # _IOWR('H', 1, 16);

        logging.info("Opening ME device : /dev/mei0")
        try:
            mei_dev = os.open('/dev/mei0', os.O_RDWR)
            logging.info("Successfully opened ME device")
        except OSError:
            raise error.TestFail('ME device not found, probably old kernel.')

        # Connect to MKHI
        logging.info("Connecting to MKHI by sending IOCTL_MEI_CONNECT_CLIENT command")
        buf = array.array('B', 16 * [0])
        struct.pack_into('<16s', buf, 0, HECI_MKHI.bytes_le)
        fcntl.ioctl(mei_dev, IOCTL_MEI_CONNECT_CLIENT, buf)
        max_msg_length, protocol_version = struct.unpack_from('<IB', buf)

        logging.info("ME protocol version : %d"%(protocol_version))

        # Protocol 2 appears to be the minimum version that allows querying EOP
        if protocol_version < 2:
            os.close(mei_dev)
            raise error.TestNAError(
                    'ME protocol too old. Not checking for EOP.')

        if self.use_boot_state_cmd == EOP_CMD.GEN_GET_BOOT_STATE:
            # Query EOP Info with GEN_GET_BOOT_STATE command
            logging.info("Getting EOP info from ME with GEN_GET_BOOT_STATE command")
            group_id = 0xff
            command = 0x0a
            os.write(mei_dev, struct.pack('<BBBB', group_id, command, 0, 0))
            inb = os.read(mei_dev, max_msg_length)
            os.close(mei_dev)
            if len(inb) != 12:
                raise error.TestFail('Unknown response by ME.')

            group_id_resp, command_plus_80, rsvd, result, eop_state,rsvd_32 = struct.unpack(
                    '<BBBBII', inb)
            logging.info("Command Response: GroupID=%x\tCmdPlus0x80=%x\tResult=%x\tBootState=%x"%(
                           group_id_resp,command_plus_80,result,eop_state))
            eop_mask = 0x1
        else:
            # Query EOP Info with GEN_GET_EOP_STATE command
            logging.info("Getting EOP info from ME with GEN_GET_EOP_STATE command")
            group_id = 0xff
            command = 0x1d
            os.write(mei_dev, struct.pack('<BBBB', group_id, command, 0, 0))
            inb = os.read(mei_dev, max_msg_length)
            os.close(mei_dev)

            if len(inb) != 8:
                raise error.TestFail('Unknown response by ME.')

            group_id_resp, command_plus_80, rsvd, result, eop_state = struct.unpack(
                    '<BBBBI', inb)
            logging.info("Command Response: GroupID=%x\tCmdPlus0x80=%x\tResult=%x\tEOPState=%x"%(
                           group_id_resp,command_plus_80,result,eop_state))
            eop_mask = 0xff

        if (group_id_resp != group_id) or (command_plus_80 != command | 0x80):
            raise error.TestFail('ME didn\'t respond to Query EOP State.')
        if result == 0x8d:
            raise error.TestFail('ME didn\'t understand Query EOP State.')
        if result == 0x8e:
            raise error.TestFail('ME reported failure on Query EOP State.')
        if result != 0:
            raise error.TestFail(
                    'ME gave unknown response to Query EOP State.')

        # if True, EOP has been issued by firmware and we're in Post-Boot State
        eop_state = (eop_state & eop_mask) == 0
        logging.info("EOP State: %s"%eop_state)

        return eop_state

    def run_once(self):
        """Fail unless ME returns Post-Boot State"""
        self.use_boot_state_cmd = EOP_CMD.GEN_GET_BOOT_STATE
        cpu_family = utils.get_cpu_soc_family()
        if cpu_family not in ('intel',):
            raise error.TestNAError(
                    'This test is not applicable, '
                    'because a non-Intel device has been detected. '
                    'Such devices do not have an ME (Management Engine)')

        if utils.is_intel_uarch_older_than('Tiger Lake'):
            raise error.TestNAError('Skipping test on pre-TGL')
        if utils.is_intel_uarch_older_than('Gracemont'):
            raise error.TestNAError('Skipping test on production Atom designs')
        if utils.is_intel_uarch_older_than('Meteor Lake'):
            self.use_boot_state_cmd = EOP_CMD.GEN_GET_EOP_STATE
        self.read_post_boot_state()
