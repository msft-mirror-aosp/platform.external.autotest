# Copyright 2021 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import abc
import logging


class _BaseMenuModeSwitcher:
    """Base class for mode switch with menu navigator."""

    __metaclass__ = abc.ABCMeta

    def __init__(self, faft_framework, menu_navigator):
        self.test = faft_framework
        self.faft_config = self.test.faft_config
        self.servo = self.test.servo
        self.menu = menu_navigator

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
        for _ in range(3, 0, -1):
            self.menu.up()
            self.test.wait_for('keypress_delay')
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
        for _ in range(3, 2, -1):
            self.menu.up()
            self.test.wait_for('keypress_delay')
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
        for _ in range(0, 5):
            self.menu.down()
            self.test.wait_for('keypress_delay')
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
        for _ in range(5, 0, -1):
            self.menu.up()
            self.test.wait_for('keypress_delay')
        # Navigate to "Boot from internal disk"
        for _ in range(0, 2):
            self.menu.down()
            self.test.wait_for('keypress_delay')
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
        for _ in range(5, 0, -1):
            self.menu.up()
            self.test.wait_for('keypress_delay')
        # Navigate to "Return to secure mode"
        self.menu.down()
        self.test.wait_for('keypress_delay')
        self.menu.select('Selecting "Return to secure mode"...')
        self.test.wait_for('keypress_delay')
        self.menu.select('Selecing "Confirm"...')


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
