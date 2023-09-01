# Lint as: python2, python3
# Copyright 2022 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import logging

from autotest_lib.client.common_lib import error


def connect_to_wifi(host, ssid, password):
    """
    Performs steps needed to configure a CrOS device for Cross Device tests.

    @param host: Host to run the command on.
    @param ssid: SSID of the Wifi network to connect to
    @param password: password to connect to wifi network

    """
    host.run(
            'dbus-send --system --print-reply --dest=org.chromium.flimflam / org.chromium.flimflam.Manager.EnableTechnology string:wifi'
    )
    try:
        host.run('/usr/local/autotest/cros/scripts/wifi connect %s %s' %
                 (ssid, password))
    except error.AutoservRunError as e:
        if 'already connected' in str(e):
            logging.debug('Already connected to network. Ignoring error.')
        else:
            raise


def get_multi_companion_attributes(cros_hosts, cros_prefix, android_hosts,
                                   android_prefix, max_hosts):
    """Returns all valid attribute combinations for mixed android/CrOS testbeds.

        Example:
            get_multi_companion_attributes(2, 'cros_peers_', 1, 'android_peers_')

            ((("cros_peers_1" || "cros_peers_2") && !("android_peers_1" || "android_peers_2" || "android_peers_3"))
            || (("cros_peers_1" || "cros_peers_2") && ("android_peers_1"))
            || (("android_peers_1") && !("cros_peers_1" || "cros_peers_2" || "cros_peers_3")))

        Args:
            cros_hosts: The number of CrOS hosts.
            cros_prefix: The attribute prefix to use for CrOS peers.
            android_hosts: The number of android hosts.
            android_prefix: The attribute prefix to use for Android peers.
            max_hosts: The maximum number hosts supported.
    """
    def create_attr(count, prefix):
        attrs = ['"%s%d"' % (prefix, i + 1) for i in range(count)]
        return '(' + ' || '.join(attrs) + ')'

    if not cros_hosts and not android_hosts:
        raise ValueError(
                'Either cros_hosts or android_hosts must be greater than 0')

    has_cros = create_attr(cros_hosts, cros_prefix)
    no_cros = "!" + create_attr(max_hosts, cros_prefix)
    has_android = create_attr(android_hosts, android_prefix)
    no_android = '!' + create_attr(max_hosts, android_prefix)

    attrs = []
    # CrOS hosts with no android hosts.
    if cros_hosts:
        attrs.append('(%s && %s)' % (has_cros, no_android))
    # Android and CrOS hosts.
    if cros_hosts and android_hosts:
        attrs.append('(%s && %s)' % (has_cros, has_android))
    # Android hosts with no CrOS hosts.
    if android_hosts:
        attrs.append('(%s && %s)' % (has_android, no_cros))

    return '(' + ' || '.join(attrs) + ')'
