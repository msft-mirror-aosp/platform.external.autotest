# Lint as: python2, python3
# Copyright 2013 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
# Lint as: python3
""" Udevadm helper classes and functions.
"""

import re
import subprocess
import threading

class UdevadmInfo():
    """ Use udevadm info on a specific path.
    """

    @classmethod
    def GetProperties(cls, syspath):
        """ Get all properties of given syspath as a dict.

        Args:
            syspath: System path to get properties for.

        Returns:
            Dict with attribute/property as key and it's value. All keys are
            converted to lowercase. Example: {'subsystem': 'input'}
        """
        props = {}
        rawprops = subprocess.check_output(' '.join(
                ['udevadm', 'info', '-q', 'property', '-p', syspath]),
                                           shell=True)

        for line in rawprops.splitlines():
            upper_key, value = line.split(b'=', 1)
            props[upper_key.lower()] = value.strip(b'"')

        return props


class UdevadmTrigger():
    """ Use udevadm trigger with specific rules.
    """

    def __init__(self,
                 verbose=True,
                 event_type=None,
                 attr_match=[],
                 attr_nomatch=[],
                 subsystem_match=[],
                 subsystem_nomatch=[]):
        """ Constructor

        Args:
            verbose: Whether to output triggered syspaths
            event_type: What type of events to trigger (device or subsystem)
            attr_match: What attributes to match
            attr_nomatch: What attributes not to match
            subsystem_match: What subsystems to match
            subsystem_nomatch: What subsystems not to match
        """
        cmd = ['udevadm', 'trigger']

        if verbose:
            cmd.append('-v')

        if event_type:
            cmd.append('-t')
            cmd.append('"{}"'.format(event_type))

        for attr in attr_match:
            cmd.append('-a')
            cmd.append('"{}"'.format(attr))

        for attr in attr_nomatch:
            cmd.append('-A')
            cmd.append('"{}"'.format(attr))

        for subsystem in subsystem_match:
            cmd.append('-s')
            cmd.append('"{}"'.format(subsystem))

        for subsystem in subsystem_nomatch:
            cmd.append('-S')
            cmd.append('"{}"'.format(subsystem))

        self.cmd = cmd

    def DryRun(self):
        """ Do a dry run using initialized trigger rules.

        Returns:
            List of syspaths that would be triggered.
        """
        cmd = self.cmd + ['-n']
        lines = subprocess.check_output(' '.join(cmd), shell=True)
        return lines.splitlines() if lines else []


class UdevadmMonitor():
    """Use udevadm monitor to observe events.

    The output of udevadm monitor looks like this:
    KERNEL[71007.533873] change   /devices/LNXSYSTM:00/LNXSYBUS:00/PNP0A08:00/device:07/PNP0C09:00/PNP0C0A:00/power_supply/BAT0 (power_supply)
    UDEV  [71338.774623] remove   /devices/pci0000:00/0000:00:14.0/usb3/3-10/wakeup/wakeup55 (wakeup)
    UDEV  [71338.789266] add      /devices/virtual/misc/uhid/0005:1D6B:0246.003D/input/input70/event11 (input)
    """

    # Regex to extract 5 groups: source, timestamp, event, path, subsystem.
    MONITOR_REGEX = '(KERNEL|UDEV)[\s]*\[([0-9\.]+)\][\s]*([\S]*)[\s]*([\S]*)[\s]*\(([\S]*)\)'

    def __init__(self, udev=False, kernel=False, subsystems=[], tags=[]):
        """Constructor.

        @param udev: should we track udev events?
        @param kernel: should we track kernel events?
        @param subsystems: list of subsystems to monitor.
        @param tags: list of tags to monitor.
        """
        self.cmd = ['udevadm', 'monitor']
        self.thread = None
        self.proc = None
        self.pattern = re.compile(self.MONITOR_REGEX)

        if udev:
            self.cmd.append('--udev')

        if kernel:
            self.cmd.append('--kernel')

        for subsystem in subsystems:
            self.cmd.append('--subsystem-match')
            self.cmd.append('{}'.format(subsystem))

        for tag in tags:
            self.cmd.append('--tag-match')
            self.cmd.append('{}'.format(tag))

    def start(self, callback):
        """Starts the monitoring process.

        @param callback: function to be called when monitor reports an event.
                         it should accept 5 parameters all in string:
                         (1) source (possible values: 'UDEV' or 'KERNEL')
                         (2) timestamp (e.g. '123.456789')
                         (3) event (e.g. 'add', 'change', 'remove')
                         (4) path (e.g. '/devices/virtual/misc/uhid/0005:1D6B:
                             0246.003D/input/input70/event11')
                         (5) subsystem (e.g. 'input', 'wakeup')
        """

        def _monitoring_thread(proc, pattern, callback):
            for line in proc.stdout:
                match = pattern.match(line.decode('utf-8'))
                if not match or len(match.groups()) != 5:
                    continue
                callback(match.group(1), match.group(2), match.group(3),
                         match.group(4), match.group(5))

        self.proc = subprocess.Popen(self.cmd, stdout=subprocess.PIPE)
        self.thread = threading.Thread(target=_monitoring_thread,
                                       args=(
                                               self.proc,
                                               self.pattern,
                                               callback,
                                       ))
        self.thread.start()

    def stop(self):
        """Stops the monitoring process."""
        if self.proc is not None:
            self.proc.terminate()
            self.thread.join()
            self.proc = None
            self.thread = None
