# Copyright 2021 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import abc
import logging

from autotest_lib.client.common_lib import error


class _BaseMenuModeSwitcher:
    """Base class for mode switch with menu navigator."""

    __metaclass__ = abc.ABCMeta

    def __init__(self, faft_framework, menu_navigator):
        self.test = faft_framework
        self.faft_config = self.test.faft_config
        self.servo = self.test.servo
        self.menu = menu_navigator
        self.minidiag_enabled = self.faft_config.minidiag_enabled

    @abc.abstractmethod
    def trigger_rec_to_dev(self):
        """Trigger to-dev transition."""
        raise NotImplementedError

    @abc.abstractmethod
    def dev_boot_from_internal(self):
        """Boot from internal disk in developer mode."""
        raise NotImplementedError

    @abc.abstractmethod
    def trigger_dev_to_normal(self):
        """Trigger dev-to-norm transition."""
        raise NotImplementedError


class _TabletDetachableMenuModeSwitcher(_BaseMenuModeSwitcher):
    """Mode switcher with menu navigator for legacy menu UI.

    The "legacy menu UI" is an old menu-based UI, which has been replaced
    by the new one, called "menu UI".
    """

    def trigger_rec_to_dev(self):
        """Trigger to-dev transition."""
        self.test.switcher.trigger_rec_to_dev()

    def dev_boot_from_internal(self):
        """Boot from internal disk in developer mode.

        Menu items in developer warning screen:
            0. Developer Options
            1. Show Debug Info
            2. Enable OS Verification
           *3. Power Off
            4. Language

        (*) is the default selection.
        """
        self.test.wait_for('firmware_screen')
        self.menu.move_to(3, 0)
        self.menu.select('Selecting "Developer Options"...')
        self.test.wait_for('keypress_delay')
        self.menu.select('Selecting "Boot From Internal Disk"...')

    def trigger_dev_to_normal(self):
        """Trigger dev-to-norm transition.

        Menu items in developer warning screen:
            0. Developer Options
            1. Show Debug Info
            2. Enable OS Verification
           *3. Power Off
            4. Language

        Menu items in to-norm confirmation screen:
           *0. Confirm Enabling OS Verification
            1. Cancel
            2. Power Off
            3. Language

        (*) is the default selection.
        """
        self.test.wait_for('firmware_screen')
        self.menu.move_to(3, 2)
        self.menu.select('Selecting "Enable OS Verification"...')
        self.test.wait_for('keypress_delay')
        self.menu.select('Selecing "Confirm Enabling OS Verification"...')


class _MenuModeSwitcher(_BaseMenuModeSwitcher):
    """Mode switcher with menu navigator for menu UI.

    The "menu UI" aims to replace both "legacy clamshell UI" and "legacy
    menu UI". See chromium:1033815 for the discussion about the naming.
    """

    def _confirm_to_dev(self):
        if self.faft_config.rec_button_dev_switch:
            logging.info('Confirm to-dev by RECOVERY button')
            self.servo.toggle_recovery_switch()
        elif self.faft_config.power_button_dev_switch:
            logging.info('Confirm to-dev by POWER button')
            self.servo.power_normal_press()
        else:
            self.menu.select('Confirm to-dev by menu selection')

    def trigger_rec_to_dev(self):
        """Trigger to-dev transition.

        Menu items in recovery select screen:
            0. Language
            1. Recovery using phone
            2. Recovery using external disk
            3. Launch diagnostics
            4. Advanced options
            5. Power off

        Menu items in advanced options screen:
            0. Language
           *1. Enable developer mode
            2. Back
            3. Power off

        Menu items in to-dev screen:
            0. Language
           *1. Confirm
            2. Cancel
            3. Power off

        (*) is the default selection.
        """
        self.test.wait_for('firmware_screen')
        # Since the default selection is unknown, navigate to item 5 first
        self.menu.move_to(0, 5)
        # Navigate to "Advanced options"
        self.menu.up()
        self.test.wait_for('keypress_delay')
        self.menu.select('Selecting "Advanced options"...')
        self.test.wait_for('keypress_delay')
        self.menu.select('Selecting "Enable developer mode"...')
        self.test.wait_for('keypress_delay')
        # Confirm to-dev transition
        self._confirm_to_dev()

    def dev_boot_from_internal(self):
        """Boot from internal disk in developer mode.

        Menu items in developer mode screen:
            0. Language
            1. Return to secure mode
            2. Boot from internal disk
            3. Boot from external disk
            4. Advanced options
            5. Power off
        """
        self.test.wait_for('firmware_screen')
        # Since the default selection is unknown, navigate to item 0 first
        self.menu.move_to(5, 0)
        # Navigate to "Boot from internal disk"
        self.menu.move_to(0, 2)
        self.menu.select('Selecting "Boot from internal disk"...')

    def trigger_dev_to_normal(self):
        """Trigger dev-to-norm transition.

        Menu items in developer mode screen:
            0. Language
            1. Return to secure mode
            2. Boot from internal disk
            3. Boot from external disk
            4. Advanced options
            5. Power off

        Menu items in to-norm screen:
            0. Language
           *1. Confirm
            2. Cancel
            3. Power off

        (*) is the default selection.
        """
        self.test.wait_for('firmware_screen')
        # Since the default selection is unknown, navigate to item 0 first
        self.menu.move_to(5, 0)
        # Navigate to "Return to secure mode"
        self.menu.down()
        self.test.wait_for('keypress_delay')
        self.menu.select('Selecting "Return to secure mode"...')
        self.test.wait_for('keypress_delay')
        self.menu.select('Selecing "Confirm"...')

    def trigger_rec_to_minidiag(self):
        """
        Trigger to-minidiag.
        Menu items in recovery select screen:
            0. Language
            1. Recovery using phone
            2. Recovery using external disk
            3. Launch diagnostics
            4. Advanced options
            5. Power off
        """

        # Validity check; this only applicable for minidiag enabled devices.
        if not self.minidiag_enabled:
            raise error.TestError('Minidiag is not enabled for this board')

        self.test.wait_for('firmware_screen')
        # Since the default selection is unknown, navigate to item 5 first
        self.menu.move_to(0, 5)
        # Navigate to "Launch diagnostics"
        self.menu.up()
        self.test.wait_for('keypress_delay')
        self.menu.up()
        self.test.wait_for('keypress_delay')
        self.menu.select('Selecting "Launch diagnostics"...')
        self.test.wait_for('firmware_screen')

    def navigate_minidiag_storage(self):
        """
        Navigate to storage screen.
        Menu items in storage screen:
            0. Language
            1. Page up (disabled)
            2. Page down
            3. Back
            4. Power off
        """

        # Validity check; this only applicable for minidiag enabled devices.
        if not self.minidiag_enabled:
            raise error.TestError('Minidiag is not enabled for this board')

        # From root screen to storage screen
        self.menu.select('Selecting "Storage"...')
        self.test.wait_for('keypress_delay')
        # Since the default selection is unknown, navigate to item 4 first
        self.menu.move_to(0, 4)
        # Navigate to "Back"
        self.menu.up()
        self.test.wait_for('keypress_delay')
        self.menu.select('Back to minidiag root screen...')
        self.test.wait_for('keypress_delay')

    def navigate_minidiag_quick_memory_check(self):
        """
        Navigate to quick memory test screen.
        Menu items in quick memory test screen:
            0. Language
            1. Page up (disabled)
            2. Page down (disabled
            3. Back
            4. Power off
        """

        # Validity check; this only applicable for minidiag enabled devices.
        if not self.minidiag_enabled:
            raise error.TestError('Minidiag is not enabled for this board')

        # From root screen to quick memory test screen
        # Since there might be self test items, navigate to the last item first
        self.menu.move_to(0, 5)
        self.menu.up()  # full memory test
        self.test.wait_for('keypress_delay')
        self.menu.up()  # quick memory test
        self.test.wait_for('keypress_delay')
        self.menu.select('Selecting "Quick memory test"...')
        self.test.wait_for('keypress_delay')
        # Wait for quick memory test
        self.menu.select('Back to minidiag root screen...')
        self.test.wait_for('keypress_delay')

    def reset_and_leave_minidiag(self):
        """Reset the DUT and normal boot to leave minidiag."""

        # Validity check; this only applicable for minidiag enabled devices.
        if not self.minidiag_enabled:
            raise error.TestError('Minidiag is not enabled for this board')

        # Since we want to keep the cbmem log, we need an AP reset and reboot to
        # normal mode
        if self.test.ec.has_command('apreset'):
            logging.info('Trigger apreset')
            self.test.ec.send_command('apreset')
        else:
            raise error.TestError('No apreset support')
        self.test.switcher.wait_for_client()


_MENU_MODE_SWITCHER_CLASSES = {
        'menu_switcher': _MenuModeSwitcher,
        'tablet_detachable_switcher': _TabletDetachableMenuModeSwitcher,
}


def create_menu_mode_switcher(faft_framework, menu_navigator):
    """Create a proper navigator based on its mode switcher type.

    @param faft_framework: The main FAFT framework object.
    @param menu_navigator: The menu navigator for base logic of navigation.
    """
    switcher_type = faft_framework.faft_config.mode_switcher_type
    switcher_class = _MENU_MODE_SWITCHER_CLASSES.get(switcher_type, None)
    if switcher_class is None:
        # Not all devices support menu-based UI, so it is fine to return None.
        logging.info('Switcher type %s is menuless, return None',
                     switcher_type)
        return None
    return switcher_class(faft_framework, menu_navigator)
