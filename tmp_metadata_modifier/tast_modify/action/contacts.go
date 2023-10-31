// Copyright 2023 The ChromiumOS Authors
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

package action

import (
	"go.chromium.org/chromiumos/tast_metadata_modifier/file"
)

const contactsFieldName = "Contacts"

// setContactsInFile is a helper function to set the contacts.
func setContactsInFile(f *file.TestFile, emails []string) (bool, error) {
	return f.SetTestField(
		contactsFieldName, file.FormatStrings(file.FormatManyLines, emails))
}

// contactsFromFile is a helper function to get the contacts.
func contactsFromFile(f *file.TestFile) ([]string, error) {
	contactsField := f.FindTestField(contactsFieldName)
	if contactsField == nil {
		return []string{}, nil
	}
	return contactsField.Strings()
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

// SetContacts returns an action which replaces the entire
// contacts for a test with the given values.
func SetContacts(emails []string) Action {
	return func(f *file.TestFile) (bool, error) {
		return setContactsInFile(f, emails)
	}
}

// RemoveContacts returns an action that removes the given
// contact emails from the test declaration.
func RemoveContacts(emails []string) Action {
	return func(f *file.TestFile) (bool, error) {
		return f.RemoveStringsFromTest(
			contactsFieldName, emails, file.FormatManyLines)
	}
}

// ReplaceContact returns an action that replaces the given oldEmail
// with the given newEmail in the test's contacts.
func ReplaceContact(oldEmail, newEmail string) Action {
	return func(f *file.TestFile) (bool, error) {
		contacts, err := contactsFromFile(f)
		if err != nil {
			return false, err
		}
		for i, elt := range contacts {
			if elt == oldEmail {
				contacts[i] = newEmail
				return setContactsInFile(f, contacts)
			}
		}
		return false, nil
	}
}

// AppendContacts returns an action that appends the given emails to
// a test's contacts, deleting them elsewhere in the list if already present.
func AppendContacts(emails []string) Action {
	return func(f *file.TestFile) (bool, error) {
		contacts, err := contactsFromFile(f)
		if err != nil {
			return false, err
		}
		newContacts := removeMatchingEmails(contacts, emails)
		newContacts = append(newContacts, emails...)
		return setContactsInFile(f, newContacts)
	}
}

// PrependContacts returns an action that prepends the given emails to
// a test's contacts, deleting them elsewhere in the list if already present.
func PrependContacts(emails []string) Action {
	return func(f *file.TestFile) (bool, error) {
		contacts, err := contactsFromFile(f)
		if err != nil {
			return false, err
		}
		newContacts := removeMatchingEmails(contacts, emails)
		newContacts = append(emails, newContacts...)
		return setContactsInFile(f, newContacts)
	}
}
