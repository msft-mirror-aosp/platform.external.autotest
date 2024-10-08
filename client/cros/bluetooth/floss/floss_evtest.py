# Lint as: python2, python3
# Copyright 2024 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Helper class to open UHID connection in autotest."""

import subprocess
import re

from autotest_lib.client.cros.udev_helpers import UdevadmMonitor


class FlossEvtest():
    """Starts evtest for new devices.

    UHID always sends UHID_CLOSE following a UHID_OPEN if UI is stopped. OTOH
    floss disconnects when UHID is not reopened in 2 seconds. UI is always
    stopped in autotests but not in normal use case.
    This utility helps by opening evtest, so UHID_OPEN will be emitted for new
    devices, thus emulating the normal use case under autotest situation.
    """

    PATH_REGEX = '.*event([0-9]+)'

    def __init__(self):
        """Constructor. We start the process to monitor input devices here."""

        def _monitor_callback(source, time, event, path, subsystem):
            match = self.pattern.match(path)
            if not match or len(match.groups()) != 1:
                return

            event_num = match.group(1)
            if event == 'add':
                self._on_input_added(event_num)
            elif event == 'remove':
                self._on_input_removed(event_num)

        self.pattern = re.compile(self.PATH_REGEX)
        self.evtest_dict = {}
        self.udev_monitor = UdevadmMonitor(udev=True, subsystems=['input'])
        self.udev_monitor.start(_monitor_callback)

    def _on_input_added(self, num):
        """When new input device is detected, start evtest that does nothing."""
        if num in self.evtest_dict:
            self.evtest_dict[num].terminate()

        cmd = ['evtest', '/dev/input/event{}'.format(num)]
        self.evtest_dict[num] = subprocess.Popen(cmd,
                                                 stdout=subprocess.DEVNULL,
                                                 stderr=subprocess.DEVNULL)

    def _on_input_removed(self, num):
        """When an input device is removed, stop evtest."""
        if num in self.evtest_dict:
            self.evtest_dict[num].terminate()
            del self.evtest_dict[num]

    def cleanup(self):
        """Stops monitoring and terminate all evtest processes."""
        self.udev_monitor.stop()
        for num, proc in self.evtest_dict.items():
            proc.terminate()
        self.evtest_dict.clear()
