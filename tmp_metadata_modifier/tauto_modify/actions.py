# Copyright 2023 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Functions which return "actions" that modify a given ControlFile object."""

# Each action should take in a single ControlFile and return a boolean value
# of whether the control file was modified or not.

def remove_contacts(emails):
    """Return an action which removes the given list of emails from 'contacts'.

    Args:
        emails: A list of string emails, e.g. ['foo@google.com'].

    Returns:
        An action function that acts on a ControlFile and returns a boolean.
    """
    def output(cf):
        if 'contacts' not in cf.metadata:
            return False
        modified = False
        for email in emails:
            if email in cf.metadata['contacts']:
                cf.metadata['contacts'].remove(email)
                modified = True
        return modified
    return output


def append_contacts(emails):
    """Return an action which appends the given emails to 'contacts'.

    Args:
        emails: A list of string emails, e.g. ['foo@google.com'].

    Returns:
        An action function that acts on a ControlFile and returns a boolean.
    """
    def output(cf):
        if 'contacts' not in cf.metadata:
            return False
        for email in emails:
            if email in cf.metadata['contacts']:
                cf.metadata['contacts'].remove(email)
        cf.metadata['contacts'] += emails
        return True
    return output


def prepend_contacts(emails):
    """Return an action which prepends the given emails to 'contacts'.

    Args:
        emails: A list of string emails, e.g. ['foo@google.com'].

    Returns:
        An action function that acts on a ControlFile and returns a boolean.
    """
    def output(cf):
        if 'contacts' not in cf.metadata:
            return False
        for email in emails:
            if email in cf.metadata['contacts']:
                cf.metadata['contacts'].remove(email)
        cf.metadata['contacts'] = emails + cf.metadata['contacts']
        return True
    return output
