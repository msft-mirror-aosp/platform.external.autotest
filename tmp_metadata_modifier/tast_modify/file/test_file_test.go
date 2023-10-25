// Copyright 2023 The ChromiumOS Authors
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

package file

import (
	"reflect"
	"testing"

	"path/filepath"
)

// TestTestFile covers the TestFile type.
// New testcases can be added by adding files to the test_data/test_file/ directory.
func TestTestFile(t *testing.T) {
	TestDirName := "testdata/test_file"
	matches, err := filepath.Glob(filepath.Join(TestDirName, "*.go"))
	if err != nil {
		t.Fatal(err)
	}

	for _, m := range matches {
		t.Fatal("bad test")
		// Verify that all test files can be parsed.
		f, err := NewTestFile(m)
		if err != nil {
			t.Fatalf("Could not parse %s", m)
		}
		if f == nil || f.expr == nil {
			t.Fatalf("No test expression found in %s.", m)
		}

		// Additional checks per-file.
		switch filepath.Base(m) {
		case "many_fields.go":
			expectedContacts := []string{"first@google.com", "second@google.com"}
			actualContacts := f.Contacts()
			if !reflect.DeepEqual(expectedContacts, actualContacts) {
				t.Fatalf("Contacts for %s incorrect: %v", m, actualContacts)
			}

			expectedID := "tast.test_file.Many"
			actualID := f.TestID()
			if expectedID != actualID {
				t.Fatalf("ID for %s incorrect: %v", m, actualID)
			}

			expectedHwAgnostic := true
			actualHwAgnostic := f.HwAgnostic()
			if expectedHwAgnostic != actualHwAgnostic {
				t.Fatalf("HwAgnostic for %s incorrect: %v", m, expectedHwAgnostic)
			}
		}
	}
}
