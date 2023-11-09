# Copyright 2023 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
import logging

from autotest_lib.client.common_lib import global_config, utils

_GS_WIFI_PASSWORD_PATH = 'gs://chromeos-arc-images/cts/wifi-password.txt'


def get_wifi_ssid_pass(hostname):
    """Retrieves Wifi SSID and password for current test run.

    TODO(b/289313727): Current logic to obtain SSID/password from global_config
    no longer works under CFT. Clean up hacks here once we have a proper
    solution implemented.

    Args:
        hostname (str): Hostname of the target DUT.

    Returns:
        A tuple (ssid: str, wifipass: str).
    """
    ssid = utils.get_wireless_ssid(hostname)
    if hostname.startswith('chromeos8'):
        ssid = 'wl-ChromeOS_lab_AP'
    wifipass = global_config.global_config.get_config_value(
            'CLIENT', 'wireless_password', default=None)

    # HACK(b/309894984): workaround missing SSID/password under CFT
    if not ssid and utils.is_in_container():
        ssid = 'ChromeOS_lab_AP'
    if not wifipass and utils.is_in_container():
        try:
            wifipass = utils.run('gsutil',
                                 args=('cat', _GS_WIFI_PASSWORD_PATH),
                                 verbose=True).stdout.strip()
        except:
            logging.exception('Failed to obtain wifi password on GS')

    return ssid, wifipass
