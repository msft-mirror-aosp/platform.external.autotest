#!/usr/bin/python
#
# Copyright 2016 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

'''Make Chrome automatically log in.'''

# This sets up import paths for autotest.
import common

import argparse
import getpass
import sys

from autotest_lib.client.common_lib.cros import chrome


def main(args):
    '''The main function.

    @param args: list of string args passed to program
    '''

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('-a', '--arc', action='store_true',
                        help='Enable ARC and wait for it to start.')
    parser.add_argument('-d', '--dont_override_profile', action='store_true',
                        help='Keep files from previous sessions.')
    parser.add_argument('-u', '--username',
                        help='Log in as provided username.')
    parser.add_argument('--enable_default_apps', action='store_true',
                        help='Enable default applications.')
    parser.add_argument('-p', '--password',
                        help='Log in with provided password.')
    parser.add_argument('-w', '--no-startup-window', action='store_true',
                        help='Prevent startup window from opening (no doodle).')
    args = parser.parse_args(args)

    if args.password:
        password = args.password
    elif args.username:
        password = getpass.getpass()

    browser_args = []
    if args.no_startup_window:
        browser_args.append('--no-startup-window')

    # Avoid calling close() on the Chrome object; this keeps the session active.
    chrome.Chrome(
        extra_browser_args=browser_args,
        arc_mode=('enabled' if args.arc else None),
        username=args.username,
        password=(password if args.username else None),
        gaia_login=(args.username is not None),
        disable_default_apps=(not args.enable_default_apps),
        dont_override_profile=args.dont_override_profile)


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
