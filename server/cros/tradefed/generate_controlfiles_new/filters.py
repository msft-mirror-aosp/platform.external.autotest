# Copyright 2023 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from typing import Callable, Iterable, Union

from .common import ModuleGroup


def has_modules(modules: Iterable[str]) -> Callable[[ModuleGroup], bool]:
    modules = set(modules)

    def _filter(group: ModuleGroup) -> bool:
        return group['modules'] & modules

    return _filter


def filter_and(
        *filters: Iterable[Union[Callable[[ModuleGroup], bool], bool]]
) -> Callable[[ModuleGroup], bool]:
    def _filter(group):
        for f in filters:
            if not (f(group) if callable(f) else f):
                return False
        return True

    return _filter
