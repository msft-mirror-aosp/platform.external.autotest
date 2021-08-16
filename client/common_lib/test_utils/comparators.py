# Lint as: python2, python3
# Copyright 2021 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Comparators that be used inplace of mox.<comparator>."""


class IsA():
    """Helper class to check whether a substring exists in a string parameter.


    Class to help replace mox.IsA. Defines the __eq__ and equals.
    Use to compare to str to see if the other string contains this substr.
    Example:
        foo = IsA(host)
        print(host == foo)
        >>> True
    """

    def __init__(self, arg):
        self.arg = arg

    def __eq__(self, other):
        return self.arg == other

    def equals(self, other):
        """Wrapper for __eq__."""
        return self.__eq__(other)
