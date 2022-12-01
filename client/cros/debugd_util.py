# Copyright 2017 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import dbus


def iface():
  """Returns the interface object for debugd."""
  bus = dbus.SystemBus()
  proxy = bus.get_object('org.chromium.debugd', '/org/chromium/debugd')
  return dbus.Interface(proxy, dbus_interface='org.chromium.debugd')
