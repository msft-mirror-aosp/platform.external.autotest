# Lint as: python2, python3
# Copyright 2014 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# Most of this code is based on login_GuestAndActualSession, which performs
# similar ownership clearing/checking tasks.

from dbus.mainloop.glib import DBusGMainLoop
# AU tests use ToT client code, but ToT -3 client version.
try:
    from gi.repository import GObject
except ImportError:
    import gobject as GObject

from autotest_lib.client.bin import test
from autotest_lib.client.common_lib import error
from autotest_lib.client.common_lib.cros import session_manager, chrome
from autotest_lib.client.cros import cryptohome, ownership

class login_CryptohomeOwnerQuery(test.test):
    """Verify that the cryptohome owner user query works properly."""
    version = 1


    def initialize(self):
        super(login_CryptohomeOwnerQuery, self).initialize()
        # Ensure a clean beginning.
        ownership.restart_ui_to_clear_ownership_files()

        bus_loop = DBusGMainLoop(set_as_default=True)
        self._listener = session_manager.OwnershipSignalListener(
                GObject.MainLoop())
        self._listener.listen_for_new_key_and_policy()


    def run_once(self):
        owner = 'first_user@nowhere.com'

        if cryptohome.get_login_status()['owner_user_exists']:
            raise error.TestFail('Owner existed before login')

        cryptohome.ensure_clean_cryptohome_for(owner)

        with chrome.Chrome(logged_in=True, username=owner):
            self._listener.wait_for_signals(desc='Device ownership complete.')

            if not cryptohome.get_login_status()['owner_user_exists']:
                raise error.TestFail('Owner does not exist after login')
