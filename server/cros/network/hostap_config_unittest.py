#!/usr/bin/python3
#
# Lint as: python2, python3
# Copyright (c) 2022 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import unittest

import common

from autotest_lib.server.cros.network import hostap_config


class HostapConfigTest(unittest.TestCase):
    """Unit test for the HostapConfig object."""

    _N_CAP_HT20 = [hostap_config.HostapConfig.N_CAPABILITY_HT20]
    _AC_CAPS = [hostap_config.HostapConfig.AC_CAPABILITY_MAX_A_MPDU_LEN_EXP7]
    _AX_CAPS = [hostap_config.HostapConfig.AX_CAPABILITY_HE160]

    def _make_hostap_config_11ax(self, mode, he_chwidth, channel=36):
        config = hostap_config.HostapConfig(channel=channel,
                                            mode=mode,
                                            n_capabilities=self._N_CAP_HT20,
                                            ac_capabilities=self._AC_CAPS,
                                            ax_capabilities=self._AX_CAPS,
                                            he_channel_width=he_chwidth)

        hostap_dict = config.generate_dict('dontcare1', 'dontcare2',
                                           'dontcare3')
        return (config, hostap_dict)

    def _assert_11ax(self, config, hostap_dict):
        self.assertEquals(hostap_dict.get('ieee80211ax'), 1)
        if config.frequency > 5000:
            self.assertEquals(hostap_dict.get('hw_mode'), config.MODE_11A)
        else:
            self.assertEquals(hostap_dict.get('hw_mode'), config.MODE_11G)

    def test_hostap_he160(self):
        """Test for HE 160MHz pure mode.
        """
        config, hostap_dict = self._make_hostap_config_11ax(
                hostap_config.HostapConfig.MODE_11AX_PURE,
                hostap_config.HostapConfig.HE_CHANNEL_WIDTH_160)

        self._assert_11ax(config, hostap_dict)
        self.assertEquals(hostap_dict.get('he_oper_chwidth'), 2)
        self.assertEquals(config.require_he, True)
        self.assertEquals(config.channel_width, config.HE_CHANNEL_WIDTH_160)

    def test_hostap_he20_mixed(self):
        """Test for HE 20MHz mixed mode.
        """
        config, hostap_dict = self._make_hostap_config_11ax(
                hostap_config.HostapConfig.MODE_11AX_MIXED,
                hostap_config.HostapConfig.HE_CHANNEL_WIDTH_20)

        self._assert_11ax(config, hostap_dict)
        self.assertEquals(hostap_dict.get('he_oper_chwidth'), 0)
        self.assertEquals(config.require_he, False)
        self.assertEquals(config.channel_width, config.HE_CHANNEL_WIDTH_20)

    def test_hostap_he40_ht20(self):
        """Test for HE 40MHz with HT 20MHz.
           In this case it should fallback to 20MHz channel bandwidth
        """
        config, hostap_dict = self._make_hostap_config_11ax(
                hostap_config.HostapConfig.MODE_11AX_PURE,
                hostap_config.HostapConfig.HE_CHANNEL_WIDTH_40)

        self._assert_11ax(config, hostap_dict)
        self.assertEquals(hostap_dict.get('he_oper_chwidth'), 0)
        self.assertEquals(config.require_he, True)
        self.assertEquals(config.channel_width, config.HE_CHANNEL_WIDTH_20)

    def test_hostap_he20_24G(self):
        """Test for HE 20MHz on 2.4GHz
        """
        config, hostap_dict = self._make_hostap_config_11ax(
                hostap_config.HostapConfig.MODE_11AX_PURE,
                hostap_config.HostapConfig.HE_CHANNEL_WIDTH_20,
                channel=1)

        self._assert_11ax(config, hostap_dict)
        self.assertEquals(hostap_dict.get('he_oper_chwidth'), 0)
        self.assertEquals(config.require_he, True)
        self.assertEquals(config.channel_width, config.HE_CHANNEL_WIDTH_20)

    @unittest.expectedFailure
    def test_hostap_he80_24G(self):
        """Test for expected to fail case: HE 80MHz on 2.4G
        """
        config, hostap_dict = self._make_hostap_config_11ax(
                hostap_config.HostapConfig.MODE_11AX_PURE,
                hostap_config.HostapConfig.HE_CHANNEL_WIDTH_80,
                channel=1)
