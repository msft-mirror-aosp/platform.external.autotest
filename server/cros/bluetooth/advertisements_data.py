# Lint as: python2, python3
# Copyright 2016 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""A list of advertisements data for testing purpose."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import copy
import random

from six.moves import range


_ADV_TEMPLATE0 = {
        'Path': '/org/bluez/test/advertisement1',
        'Type': 'peripheral',
        'ManufacturerData': {
                '0xff01': None  # To be filled by _gen_from_template
        },
        'ServiceUUIDs': ['180D', '180F'],
        'SolicitUUIDs': [],
        'ServiceData': {
                '9991': None  # To be filled by _gen_from_template
        },
        'ScanResponseData': {
                '0x16': [0xcd, 0xab]  # To be completed by _gen_from_template
        },
        'Discoverable': True,
        'IncludeTxPower': True,
        'MinInterval': 100,
        'MaxInterval': 100,
        'TxPower': 10
}

_ADV_TEMPLATE1 = {
        'Path': '/org/bluez/test/advertisement2',
        'Type': 'peripheral',
        'ManufacturerData': {
                '0xff02': None  # To be filled by _gen_from_template
        },
        'ServiceUUIDs': ['1821'],
        'SolicitUUIDs': [],
        'ServiceData': {
                '9992': None  # To be filled by _gen_from_template
        },
        'ScanResponseData': {
                '0x16': [0xcd, 0xab]  # To be completed by _gen_from_template
        },
        'Discoverable': True,
        'IncludeTxPower': True,
        'MinInterval': 100,
        'MaxInterval': 100,
        'TxPower': 7
}

_ADV_TEMPLATE2 = {
        'Path': '/org/bluez/test/advertisement3',
        'Type': 'peripheral',
        'ManufacturerData': {
                '0xff03': None  # To be filled by _gen_from_template
        },
        'ServiceUUIDs': ['1819', '180E'],
        'SolicitUUIDs': [],
        'ServiceData': {
                '9993': None  # To be filled by _gen_from_template
        },
        'Discoverable': True,
        'IncludeTxPower': True,
        'MinInterval': 100,
        'MaxInterval': 100,
        'TxPower': 4
}

_ADV_TEMPLATE3 = {
        'Path': '/org/bluez/test/advertisement4',
        'Type': 'peripheral',
        'ManufacturerData': {
                '0xff04': None  # To be filled by _gen_from_template
        },
        'ServiceUUIDs': ['1808', '1810'],
        'SolicitUUIDs': [],
        'ServiceData': {
                '9994': None  # To be filled by _gen_from_template
        },
        'Discoverable': True,
        'IncludeTxPower': True,
        'MinInterval': 100,
        'MaxInterval': 100,
        'TxPower': 1
}

_ADV_TEMPLATE4 = {
        'Path': '/org/bluez/test/advertisement5',
        'Type': 'peripheral',
        'ManufacturerData': {
                '0xff05': None  # To be filled by _gen_from_template
        },
        'ServiceUUIDs': ['1818', '181B'],
        'SolicitUUIDs': [],
        'ServiceData': {
                '9995': None  # To be filled by _gen_from_template
        },
        'Discoverable': True,
        'IncludeTxPower': True,
        'MinInterval': 100,
        'MaxInterval': 100,
        'TxPower': -2
}

_ADV_TEMPLATE5 = {
        'Path': '/org/bluez/test/advertisement6',
        'Type': 'peripheral',
        'ManufacturerData': {
                '0xff06': None  # To be filled by _gen_from_template
        },
        'ServiceUUIDs': ['1820'],
        'SolicitUUIDs': [],
        'ServiceData': {
                '9996': None  # To be filled by _gen_from_template
        },
        'Discoverable': True,
        'IncludeTxPower': True,
        'MinInterval': 100,
        'MaxInterval': 100,
        'TxPower': -5
}

_NEARBY_BROADCAST_ADV_TEMPLATE = {
        'Path': '/org/bluez/test/advertisement7',
        'Type': 'broadcast',
        'ManufacturerData': {
                '0xFE2C': None  # To be filled by _gen_from_template
        },
        'ServiceUUIDs': ['FE2C'],
        'SolicitUUIDs': [],
        'ServiceData': {
                'FE2C': None  # To be filled by _gen_from_template
        },
        'IncludeTxPower': True,
        'MinInterval': 100,
        'MaxInterval': 100
}


#
# Nearby Mediums Fast Advertisement requirement is to put Service UUIDs and
# flags in advertising payload, and 20 bytes of Service data in Scan response
#
_NEARBY_MEDIUMS_FAST_ADV_TEMPLATE = {
        'Path': '/org/bluez/test/advertisement8',
        'Type': 'peripheral',
        'ServiceUUIDs': ['FEF3'],
        'ScanResponseData': {
                '0x16': [0xf3, 0xfe]  # To be completed by _gen_from_template
        },
        'MinInterval': 100,
        'MaxInterval': 100
}


def _gen_from_template(template):
    adv = copy.deepcopy(template)
    for f in ['ServiceData', 'ManufacturerData']:
        if f in adv:
            for uuid in adv[f]:
                adv[f][uuid] = [random.randint(0x00, 0xff) for _ in range(5)]
    if 'ScanResponseData' in adv:
        for length, uuid in adv['ScanResponseData'].items():
            adv['ScanResponseData'][length] = uuid + [
                    random.randint(0x00, 0xff) for _ in range(20)
            ]
    return adv


def gen_advertisements(arg1=None, arg2=None):
    """Returns normal advertisements.

    There are 6 different advertisement templates. Callers can specify a range
    of templates to generate advertisements.

    The function provides three forms:
        1. gen_advertisements(): returns all six advertisements
        2. gen_advertisements(k): returns the k-th advertisement (zero-based)
        3. gen_advertisements(i, j): returns the list of advertisements starting
                                     from i-th and ends with (j-1)-th
                                     advertisements (zero-based)

    Note that the data of ManufacturerData, ServiceData, and ScanResponseData
    are assigned randomly when this function is called.

    @param arg1: See the usage above.
    @param arg2: See the usage above.

    @returns: List of advertisements if a range is specified (cases 1 and 3).
              Otherwise a single advertisement would be returned (case 2).

    @raises ValueError: If arg1 is None but arg2 is not None.
    """
    adv_templates = [
            _ADV_TEMPLATE0, _ADV_TEMPLATE1, _ADV_TEMPLATE2, _ADV_TEMPLATE3,
            _ADV_TEMPLATE4, _ADV_TEMPLATE5
    ]

    if arg1 is None and arg2 is not None:
        raise ValueError('unexpected non-None arg2')

    if arg1 is not None and arg2 is None:  # case 2
        return _gen_from_template(adv_templates[arg1])

    # cases 1 and 3
    return [_gen_from_template(t) for t in adv_templates[arg1:arg2]]


def gen_nearby_broadcast_adv():
    """Returns the advertisement for nearby broadcast test use.

    Note that the data of ManufacturerData, ServiceData, and ScanResponseData
    are assigned randomly when this function is called.
    """
    return _gen_from_template(_NEARBY_BROADCAST_ADV_TEMPLATE)


def gen_nearby_mediums_fast_adv():
    """Returns the advertisement for nearby mediums fast test use.

    Note that the data of ManufacturerData, ServiceData, and ScanResponseData
    are assigned randomly when this function is called.
    """
    return _gen_from_template(_NEARBY_MEDIUMS_FAST_ADV_TEMPLATE)
