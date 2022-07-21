# Copyright (c) 2012 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from autotest_lib.client.cros.video import device_capability


def has_builtin_or_vivid_camera():
    """Check if there is a built-in USB camera or MIPI camera by capability."""
    return device_capability.DeviceCapability().have_capability(
            'builtin_or_vivid_camera')
