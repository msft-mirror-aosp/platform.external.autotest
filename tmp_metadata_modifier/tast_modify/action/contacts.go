// Copyright 2023 The ChromiumOS Authors
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

package action

import (
	"go.chromium.org/chromiumos/tast_metadata_modifier/file"
)

// SetContactsAction replaces the entire contacts for a test with
// the given values.
func SetContacts(emails []string) Action {
	return func(f *file.TestFile) (bool, error) {
		return f.SetContacts(emails)
	}
}

// removeMatchingEmails takes a list of contacts and a list of
// emails and returns a slice of the given contacts in the same
// order, minus any matching emails from the given emails.
func removeMatchingEmails(contacts, emails []string) []string {
	newContacts := []string{}
	for _, contact := range contacts {
		found := false
		for _, email := range emails {
			if email == contact {
				found = true
				break
			}
		}
		if !found {
			newContacts = append(newContacts, contact)
		}
	}
	return newContacts
}

// RemoveContactsAction returns an action that removes the given
// contact emails from the test declaration.
func RemoveContacts(emails []string) Action {
	return func(f *file.TestFile) (bool, error) {
		contacts := f.Contacts()
		newContacts := removeMatchingEmails(contacts, emails)
		if len(contacts) != len(newContacts) {
			return f.SetContacts(emails)
		}
		return false, nil
	}
}

// ReplaceContactAction returns an action that replaces the given oldEmail
// with the given newEmail in the test's contacts.
func ReplaceContact(oldEmail, newEmail string) Action {
	return func(f *file.TestFile) (bool, error) {
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
func AppendContacts(emails []string) Action {
	return func(f *file.TestFile) (bool, error) {
		contacts := f.Contacts()
		newContacts := removeMatchingEmails(contacts, emails)
		newContacts = append(newContacts, emails...)
		return f.SetContacts(newContacts)
	}
}

// PrependContactsAction returns an action that prepends the given emails to
// a test's contacts, deleting them elsewhere in the list if already present.
func PrependContacts(emails []string) Action {
	return func(f *file.TestFile) (bool, error) {
		contacts := f.Contacts()
		newContacts := removeMatchingEmails(contacts, emails)
		newContacts = append(emails, newContacts...)
		return f.SetContacts(newContacts)
	}
}
