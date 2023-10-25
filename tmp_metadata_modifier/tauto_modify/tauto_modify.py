# Copyright 2023 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Helper script to parse autotest control files for data gathering."""

import argparse
import pathlib
import re

import actions
import cf_parse
import filters


# ChromeOS src/ dir relative to this file.
DEFAULT_SRC_DIR = pathlib.Path(__file__).joinpath('../../../../../..').resolve()

def modify_control_files(src_dir, actions_list, filters_list, dry_run=True,
                         public=True, private=True, client=True, server=True):
    """Apply the given actions to control files if they pass the given filters.

    Args:
        src_dir: Relative path to the chromium.org src/ directory.
        actions_list: List of action functions applied to a ControlFile object.
        filters_list: List of filter functions applied to a ControlFile object.
        dry_run: True if no files should be actually modified, just printed.
        public: True if public tests should be searched.
        private: True if private tests should be searched.
        client: True if client tests should be searched.
        server: True if server tests should be searched.
    """
    # Places to look for control files, relative to src_dir.
    PUBLIC_CLIENT_DIR = 'third_party/autotest/files/client/site_tests/'
    PUBLIC_SERVER_DIR = 'third_party/autotest/files/server/site_tests/'
    PRIVATE_CLIENT_DIR = 'third_party/autotest-private/client/site_tests/'

    autotest_dirs = []
    if public:
        if client:
            autotest_dirs.append(PUBLIC_CLIENT_DIR)
        if server:
            autotest_dirs.append(PUBLIC_SERVER_DIR)
    if private and client:
        autotest_dirs.append(PRIVATE_CLIENT_DIR)

    for tests_dir in [pathlib.Path(src_dir, d) for d in autotest_dirs]:
        for cf_path in tests_dir.glob('*/control*'):
            cf = cf_parse.ControlFile(cf_path)
            if not cf.is_valid:
                continue

            # Skip this control file if it doesn't match all the given filters.
            if not all(filter_func(cf) for filter_func in filters_list):
                continue

            # Apply the given actions to this control file.
            modified = False
            for action_func in actions_list:
                modified = action_func(cf) or modified
            cf.update_contents()

            if dry_run:
                print(f'Will modify {cf_path}:')
                print(cf.contents)
            else:
                print(f'Editing {cf_path}')
                with open(cf.path, 'w', encoding='utf-8') as f:
                    f.write(cf.contents)


def _set_up_args():
    """Define CLI arguments."""
    parser = argparse.ArgumentParser()
    parser.add_argument('--src_dir', default=DEFAULT_SRC_DIR,
                        help=('Path to the top-level chromiumos src/ directory '
                              'in your repo. Defaults to the path relative to '
                              'this file\'s location.'))
    parser.add_argument('--write_out', action='store_true',
                        help=('Write out changes to your local repo. Please '
                              'do a dry run first!'))
    public_private_group = parser.add_mutually_exclusive_group()
    public_private_group.add_argument(
            '--public_only', action='store_true',
            help='Limit filtering to only public autotest tests.')
    public_private_group.add_argument(
            '--private_only', action='store_true',
            help='Limit filtering to only autotest-private tests.')
    client_server_group = parser.add_mutually_exclusive_group()
    client_server_group.add_argument(
            '--client_only', action='store_true',
            help='Limit filtering to only client tests.')
    client_server_group.add_argument(
            '--server_only', action='store_true',
            help='Limit filtering to only server tests.')

    action_group = parser.add_argument_group(
            'actions', 'Actions which are performed on a control file.')
    action_group.add_argument(
            '--remove_contacts', required=False, action='append',
            metavar='EMAIL,EMAIL,...',
            help=('Remove the given (comma or newline-separated) '
                  'email addresses from Contacts.'))
    action_group.add_argument(
            '--append_contacts', required=False, action='append',
            metavar='EMAIL',
            help=('Add (or move) the given email addresses to the END of the '
                  'contacts list.'))
    action_group.add_argument(
            '--prepend_contacts', required=False, action='append',
            metavar='EMAIL',
            help=('Add (or move) the given email addresses to the START of the '
                  'contacts list.'))
    action_group.add_argument(
            '--set_hw_agnostic', required=False, action='store_true',
            help=('Set hw_agnostic to be True (or do nothing if it is already'
                  'set).'))
    action_group.add_argument(
            '--unset_hw_agnostic', required=False, action='store_true',
            help=('Remove hw_agnostic from the control file (or do nothing '
                  'if it is not present).'))

    filter_group = parser.add_argument_group(
            'filters', 'Filters to specify which control files are touched.')
    filter_group.add_argument(
            '--test_names', required=False, action='append',
            help=('Action: Modify only the given (comma or newline-separated) '
                  'test ids (i.e. inlcuding \'tauto.\' prefix).'))

    return parser.parse_args()

def _split_list_input(string_input):
    """Split the given string into comma or newline-separated values."""
    return [elt.strip() for elt in re.split(r',\s*|\n\s*', string_input)]

def _get_actions(args):
    """Given the arguments to the CLI, return a list of actions requested."""
    output = []
    if args.remove_contacts:
        for elt in args.remove_contacts:
            output.append(actions.remove_contacts(_split_list_input(elt)))
    if args.append_contacts:
        for elt in args.append_contact:
            output.append(actions.append_contacts(_split_list_input(elt)))
    if args.prepend_contacts:
        for elt in args.prepend_contact:
            output.append(actions.prepend_contacts(_split_list_input(elt)))
    if args.set_hw_agnostic:
        output.append(actions.set_hw_agnostic())
    if args.unset_hw_agnostic:
        output.append(actions.unset_hw_agnostic())
    return output


def _get_filters(args):
    """Given the arguments to the CLI, return a list of filters requested."""
    output = []
    if args.test_names:
        for elt in args.test_names:
            tests = [t.strip() for t in re.split(r',\s*|\n\s*', elt)]
            output.append(filters.test_list(tests))
    return output


def main():
    """Entry point."""
    args = _set_up_args()

    modify_control_files(
            args.src_dir, _get_actions(args), _get_filters(args),
            dry_run=not args.write_out,
            public=not args.private_only, private=not args.public_only,
            client=not args.server_only, server=not args.client_only)

if __name__ == '__main__':
    main()
