# Copyright (c) 2020 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""These are convenience functions that ideally are never run, but in case of
problems collect additional information about some part of the system (both
DUT and test-driving host.

Given this sporadic nature, this is not wrapped in a class but merely a
collection of functions that get the necessary inputs at the time when they're
called and need them.

The functions return a (multi-line) string that can be attached to test errors
and similar places that end up in the logs."""


def collect_usb_state(servo):
    """Collect status on USB ports and attached devices, USB mass storage in
    particular.

    _servo is a server.cros.servo object that can call into the DUT and query
    elements.

    collects the DUT-side output of :
     - `lsusb` and `lsusb -t` output to learn about the topology;
     - `ls -l /dev/sd*` to learn which storage devices are known to the OS and
       what partition scheme is assumed by the kernel;
     - `fdisk -l` for the partitioning as reported in GPT/MBR
    """
    lsusb = servo.system_output('lsusb', ignore_status=True)
    lsusb_t = servo.system_output('lsusb -t', ignore_status=True)
    lssdx = servo.system_output('ls -l /dev/sd*', ignore_status=True)
    fdisk = servo.system_output('fdisk -l', ignore_status=True)
    return """lsusb:
        %s

        lsusb -t:
        %s

        ls -l /dev/sd*:
        %s

        fdisk -l:
        %s
        """ % (lsusb, lsusb_t, lssdx, fdisk)

# Add more collect functions here as necessary
