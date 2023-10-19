# Copyright 2023 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Functions which return "filters" for control files."""

# Each filter should take in a single ControlFile and return a boolean value
# of whether the control file matches the desired filter.

def all_tests():
    """Creates a filter which acts on all tests.

    Returns:
        A filter function which acts on a ControlFile and returns a boolean.
    """
    def output(cf):
        return cf.is_valid
    return output

def test_list(tests):
    """Creates a filter which acts on the given list of test ids.

    Args:
        tests: A list of test id prefixed with "tauto.", e.g.
               ["tauto.test1", "tauto.test2"].

    Returns:
        A filter function which acts on a ControlFile and returns a boolean.
    """
    def output(cf):
        prefixed_name = 'tauto.' + cf.name_value
        return (cf.name_value != '') and (prefixed_name in tests)
    return output
