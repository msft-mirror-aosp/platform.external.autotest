# Copyright 2024 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import unittest
from autotest_lib.client.cros.cellular import labels_utils
from autotest_lib.client.common_lib import error

TEST_LABELS = [
        'sim_slot_id:2', 'sim_2_type:SIM_PHYSICAL', 'sim_2_num_profiles:1',
        'sim_2_0_iccid:123456', 'sim_2_0_pin:12345', 'sim_2_0_puk:12345',
        'sim_2_0_carrier_name:NETWORK_TMOBILE', 'sim_2_0_own_number:123456789',
        'sim_slot_id:1', 'sim_1_type:SIM_DIGITAL', 'sim_1_eid:123456',
        'sim_1_num_profiles:1', 'sim_1_0_iccid:123456', 'sim_1_0_pin:12345',
        'sim_1_0_puk:12345', 'sim_1_0_carrier_name:NETWORK_ATT',
        'sim_1_0_own_number:123456789'
]


class TestLabelsUtils(unittest.TestCase):
    """Verifies functionality of label parsing utils."""

    def test_parse_all_labels(self):
        slots = labels_utils.parse_starfish_slot_labels(TEST_LABELS)
        slots = tuple(slots)
        self.assertEqual(slots, ((1, 'tmobile'), (0, 'att')))

    def test_missing_slot_labels(self):
        self.assertRaises(error.TestError,
                          labels_utils.parse_starfish_slot_labels, [''])

    def test_missing_carrier_labels(self):
        self.assertRaises(error.TestError,
                          labels_utils.parse_starfish_slot_labels,
                          ['sim_slot_id:2'])


if __name__ == '__main__':
    unittest.main()
