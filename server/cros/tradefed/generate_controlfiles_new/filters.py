# Copyright 2023 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Helper functions to generate filters to be used with passes."""

from typing import Callable, Iterable, Union

from .common import ModuleGroup


def has_modules(modules: Iterable[str]) -> Callable[[ModuleGroup], bool]:
    """Returns a filter to check if a group contains one of the given modules.

    Args:
        modules: a list of modules.

    Returns:
        The filter function.
    """
    modules = set(modules)

    def _filter(group: ModuleGroup) -> bool:
        return group['modules'] & modules

    return _filter


def filter_and(
        *filters: Iterable[Union[Callable[[ModuleGroup], bool], bool]]
) -> Callable[[ModuleGroup], bool]:
    """Combines two filter functions like a logical AND.

    Args:
        *filters: list of filter functions.

    Returns:
        A filter function combining all given filters.
    """
    def _filter(group):
        for f in filters:
            if not (f(group) if callable(f) else f):
                return False
        return True

    return _filter
