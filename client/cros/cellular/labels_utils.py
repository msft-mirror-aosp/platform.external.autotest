# Copyright 2024 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from autotest_lib.client.common_lib import error
from autotest_lib.utils import labellib

CARRIER_PREFIX = "network_"


def parse_starfish_slot_labels(labels):
    """Parses sim slot labels to determine starfish slot mapping.

    @param labels: Host info labels.
    @returns: tuple containing (slot_id, carrier)
    @raises: error.TestError if no slots are found or failing to parase a carrier.
    """
    # Collect all sim_slot_id labels since there may be multiple, e.g.
    # sim_slot_id:1, sim_slot_id:2
    slots = []
    for l in labels:
        if not l.startswith('sim_slot_id:'):
            continue
        slot = l.split(':')[1]
        try:
            slots.append(int(slot))
        except:
            raise error.TestError(f'failed to parse slot id from {slot}')

    if not slots:
        raise error.TestError(f'unable to find any sim_slot_id')

    res = []
    for slot in slots:
        carrier = labellib.LabelsMapping(labels).get(
                f'sim_{slot}_0_carrier_name')
        if not carrier:
            raise error.TestError(f'carrier not found for slot {slot}')

        carrier = carrier.lower()
        carrier = carrier.strip()
        if not carrier.startswith(CARRIER_PREFIX):
            raise error.TestError(f'unknown carrier format {carrier}')
        carrier = carrier[len(CARRIER_PREFIX):]

        # SIMs are 1 indexed, while starfish slots start at 0.
        res.append((slot - 1, carrier))

    return res
