// Copyright 2023 The ChromiumOS Authors
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

package main

import ()

// Action is a function which modifies a test file.
// It is applied to a TestFile object and returns true if the file was modified
// as a result of the action (or an error if something goes wrong).
type Action func(*TestFile) (bool, error)

// SetContactsAction replaces the entire contacts for a test with
// the given values.
func SetContactsAction(emails []string) Action {
	return func(f *TestFile) (bool, error) {
		f.SetContacts(emails)
		return true, nil
	}
}

// RemoveContactsAction returns an action that removes the given
// contact emails from the test declaration.
func RemoveContactsAction(emails []string) Action {
	return func(f *TestFile) (bool, error) {
		modified := false
		for _, email := range emails {
			modified = modified || f.RemoveContact(email)
		}
		return modified, nil
	}
}

// ReplaceContactAction returns an action that replaces the given oldEmail
// with the given newEmail in the test's contacts.
func ReplaceContactAction(oldEmail, newEmail string) Action {
	return func(f *TestFile) (bool, error) {
		contacts := f.Contacts()
		for i, elt := range contacts {
			if elt == oldEmail {
				contacts[i] = newEmail
				f.SetContacts(contacts)
				return true, nil
			}
		}
		return false, nil
	}
}

// AppendContactsAction returns an action that appends the given emails to
// a test's contacts, deleting them elsewhere in the list if already present.
func AppendContactsAction(emails []string) Action {
	return func(f *TestFile) (bool, error) {
		for _, email := range emails {
			_ = f.RemoveContact(email)
		}
		contacts := append(f.Contacts(), emails...)
		f.SetContacts(contacts)
		return true, nil
	}
}

// PrependContactsAction returns an action that prepends the given emails to
// a test's contacts, deleting them elsewhere in the list if already present.
func PrependContactsAction(emails []string) Action {
	return func(f *TestFile) (bool, error) {
		for _, email := range emails {
			_ = f.RemoveContact(email)
		}
		contacts := append(emails, f.Contacts()...)
		f.SetContacts(contacts)
		return true, nil
	}
}
