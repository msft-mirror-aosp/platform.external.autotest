#!/usr/bin/python
#
# Copyright 2016 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

'''Make Chrome automatically log in.'''

# This sets up import paths for autotest.
import common
import argparse
import getpass
import logging
import subprocess
import sys
import time

from autotest_lib.client.common_lib import error
from autotest_lib.client.common_lib import ui_utils
from autotest_lib.client.common_lib.cros import chrome
from autotest_lib.client.cros import constants
from autotest_lib.client.cros.multimedia import display_facade as display_facade_lib
from autotest_lib.client.cros.multimedia import facade_resource


def is_vm_display():
    '''Returns whether Chrome OS is running on a VM virtual display.'''
    lsmod_output = subprocess.check_output(['lsmod']).decode('ascii')
    for mod in ['vkms', 'virtio_gpu_dummy']:
        if mod in lsmod_output:
            return True
    return False


def set_max_display_resolution(display_facade, cr):
    '''Sets the display to maximum supported resolution.

    @param display_facade: DisplayFacadeLocal object.
    @param cr: chrome.Chrome object.
    @raise TestError when the operation fails.
    '''
    display_id = display_facade.get_first_external_display_id()
    if display_id == -1:
        raise error.TestError('Failed to get external display id')

    (old_width, old_height) = display_facade.get_external_resolution()

    modes = display_facade.get_available_resolutions(display_id=display_id)
    if len(modes) <= 1:
        raise error.TestError('Display does not support more than 1 modes')

    max_area = 0
    max_mode_width = 0
    max_mode_height = 0
    for (width, height) in modes:
        if max_area < width * height:
            max_area = width * height
            (max_mode_width, max_mode_height) = (width, height)

    if max_area == 0:
        raise error.TestError('Failed to get maximum resolution mode')

    if max_area <= old_width * old_height:
        raise error.TestError(
                'Max resolution %dx%d is not higher than old resolution %dx%d'
                % (max_mode_width, max_mode_height, old_width, old_height))

    logging.info('Set display resolution to %dx%d', max_mode_width,
                 max_mode_height)
    display_facade.set_resolution(display_id=display_id,
                                  width=max_mode_width,
                                  height=max_mode_height)

    # Dismiss confirm dialog
    ui = ui_utils.UI_Handler()
    ui.start_ui_root(cr)
    ui.wait_for_ui_obj('Confirm Display Configuration')
    ui.wait_for_ui_obj('Confirm', role='button')
    attempt = 0
    while ui.item_present('Confirm Display Configuration'):
        attempt += 1
        if attempt >= 10:
            raise error.TestError(
                    'Failed to dismiss new resolution confirmation')
        ui.doDefault_on_obj('Confirm', role='button')
        time.sleep(1)

    (new_width, new_height) = display_facade.get_external_resolution()
    if new_width != max_mode_width or new_height != max_mode_height:
        raise error.TestError(
                'New display resolution %dx%d does not matche expected %dx%d' %
                (new_width, new_height, max_mode_width, max_mode_height))


def main(args):
    '''The main function.

    @param args: list of string args passed to program
    '''

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('-a', '--arc', action='store_true',
                        help='Enable ARC and wait for it to start.')
    parser.add_argument('--arc_timeout', type=int, default=None,
                        help='Enable ARC and wait for it to start.')
    parser.add_argument('-d', '--dont_override_profile', action='store_true',
                        help='Keep files from previous sessions.')
    parser.add_argument('-u', '--username',
                        help='Log in as provided username.')
    parser.add_argument('--enable_default_apps', action='store_true',
                        help='Enable default applications.')
    parser.add_argument('--vm_force_max_resolution',
                        action='store_true',
                        help='Force set maximum supported resolution in VM.')
    parser.add_argument('-p', '--password',
                        help='Log in with provided password.')
    parser.add_argument('-w', '--no-startup-window', action='store_true',
                        help='Prevent startup window from opening (no doodle).')
    parser.add_argument('--disable-arc-cpu-restriction',
                        action='store_true',
                        help='Disables ARC CPU restriction.')
    parser.add_argument('--no-arc-syncs', action='store_true',
                        help='Prevent ARC sync behavior as much as possible.')
    parser.add_argument('--no-popup-notification',
                        action='store_true',
                        help='Prevent showing notification popups.')
    parser.add_argument('--toggle_ndk',
                        action='append_const',
                        dest='feature',
                        const='ArcNativeBridgeExperiment',
                        help='Toggle the translation from houdini to ndk')
    parser.add_argument('-f',
                        '--feature',
                        action='append',
                        help='Enables the specified Chrome feature flag')
    parser.add_argument('--disable-feature',
                        action='append',
                        help='Disable the specified Chrome feature flag')

    parser.add_argument('--url', help='Navigate to URL.')

    # Parse the remaining "unknown" args (those appearing after `--`),
    # as additional args for the browser.
    parser.add_argument('browser_args', nargs='*')
    args = parser.parse_args(args)

    if args.password:
        password = args.password
    elif args.username:
        password = getpass.getpass()

    browser_args = args.browser_args
    if args.no_popup_notification:
        browser_args.append('--suppress-message-center-popups')
    if args.no_startup_window:
        browser_args.append('--no-startup-window')
    if args.feature:
        browser_args.append('--enable-features=%s' % ','.join(args.feature))
    if args.disable_feature:
        browser_args.append('--disable-features=%s' % ','.join(args.disable_feature))

    extension_paths = None
    # Load display test extension if vm_force_max_resolution is enabled.
    if args.vm_force_max_resolution:
        if is_vm_display():
            browser_args.append('--drm-virtual-connector-is-external')
            extension_paths = [constants.DISPLAY_TEST_EXTENSION]
        else:
            raise error.TestError(
                    'Setting resolution is only supported on VM displays')

    # Avoid calling close() on the Chrome object; this keeps the session active.
    cr = chrome.Chrome(
            extra_browser_args=browser_args,
            extension_paths=extension_paths,
            arc_mode=('enabled' if args.arc else None),
            arc_timeout=args.arc_timeout,
            autotest_ext=args.vm_force_max_resolution,
            disable_arc_cpu_restriction=args.disable_arc_cpu_restriction,
            disable_app_sync=args.no_arc_syncs,
            disable_play_auto_install=args.no_arc_syncs,
            username=args.username,
            password=(password if args.username else None),
            gaia_login=(args.username is not None),
            disable_default_apps=(not args.enable_default_apps),
            dont_override_profile=args.dont_override_profile)

    # Change display resolution
    if args.vm_force_max_resolution:
        facade = facade_resource.FacadeResource(cr)
        display_facade = display_facade_lib.DisplayFacadeLocal(facade)
        set_max_display_resolution(display_facade, cr)

    if args.url:
        tab = cr.browser.tabs[0]
        tab.Navigate(args.url)


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
