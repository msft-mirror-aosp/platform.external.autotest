# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Kludges to support legacy Autotest code.

Autotest imports should be done by calling patch() first and then
calling load().  patch() should only be called once from a script's main
function.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import imp
import importlib
import logging
import os
import site
import sys

import autotest_lib

_AUTOTEST_DIR = autotest_lib.__path__[0]
_SITEPKG_DIR = os.path.join(_AUTOTEST_DIR, 'site-packages')

_setup_done = False

logger = logging.getLogger(__name__)


def patch():
    """Monkeypatch everything needed to get Autotest working.

    This should be called before any calls to load().  Only the main
    function in scripts should call this function.

    Unlike monkeypatch() which is more low-level, this patches not just
    imports, but also other things in Autotest what would generally be
    needed to use it.
    """
    monkeypatch()

    # Needed to set up Django environment variables.
    load('frontend.setup_django_environment')

    # Monkey patch package paths that Django uses to be absolute.
    settings = load('frontend.settings')
    settings.INSTALLED_APPS = (
            'autotest_lib.frontend.afe',
            'autotest_lib.frontend.tko',
            'django.contrib.admin',
            'django.contrib.auth',
            'django.contrib.contenttypes',
            'django.contrib.sessions',
            'django.contrib.sites',
    )


def monkeypatch():
    """Monkeypatch Autotest imports.

    This should be called before any calls to load().  Only the main
    function in scripts should call this function.

    This should be called no more than once.

    This adds Autotest's site-packages to the import path and modifies
    sys.meta_path so that all common.py imports are no-ops.
    """
    global _setup_done
    assert not _setup_done
    site.addsitedir(_SITEPKG_DIR)
    sys.meta_path.insert(0, _CommonRemovingFinder())
    _setup_done = True


class _CommonRemovingFinder(object):
    """Python import finder that neuters Autotest's common.py

    The common module is replaced with an empty module everywhere it is
    imported.  common.py should have only been imported for side
    effects, so nothing should actually use the imported module.

    See also https://www.python.org/dev/peps/pep-0302/
    """

    def find_module(self, fullname, path=None):
        """Find module."""
        del path  # unused
        if not self._is_autotest_common(fullname):
            return None
        logger.debug('Dummying out %s import', fullname)
        return self

    def _is_autotest_common(self, fullname):
        return (fullname.partition('.')[0] == 'autotest_lib'
                and fullname.rpartition('.')[-1] == 'common')

    def load_module(self, fullname):
        """Load module."""
        if fullname in sys.modules:  # pragma: no cover
            return sys.modules[fullname]
        mod = imp.new_module(fullname)
        mod.__file__ = '<removed>'
        mod.__loader__ = self
        mod.__package__ = fullname.rpartition('.')[0]
        sys.modules[fullname] = mod
        return mod


def load(name):
    """Import module from autotest.

    This enforces that monkeypatch() is called first.

    @param name: name of module as string, e.g., 'frontend.afe.models'
    """
    if not _setup_done:
        raise ImportError('cannot load Autotest modules before monkeypatching')
    relpath = name.lstrip('.')
    return importlib.import_module('.%s' % relpath, package='autotest_lib')
