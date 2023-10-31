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
// New testcases can be added by adding files to the testdata/parse_file directory.
func TestTestFile(t *testing.T) {
	matches, err := filepath.Glob(filepath.Join("testdata", "parse_file", "*.go"))
	if err != nil {
		t.Fatal(err)
	}

	for _, m := range matches {
		// Verify that all test files can be parsed.
		f, err := NewTestFile(m)
		if err != nil {
			t.Fatalf("Could not parse %s", m)
		}
		if f == nil || f.testExpr == nil {
			t.Fatalf("No test expression found in %s.", m)
		}

		// Additional checks per-file.
		switch filepath.Base(m) {
		case "many_fields.go":
			expectedContacts := []string{"first@google.com", "second@google.com"}
			actualContacts, err := f.FindTestField("Contacts").Strings()
			if err != nil {
				t.Fatalf("Could not read contacts: %v", err)
			}
			if !reflect.DeepEqual(expectedContacts, actualContacts) {
				t.Fatalf("Contacts for %s incorrect: %v", m, actualContacts)
			}

			expectedIDs := []string{"tast.parse_file.Many"}
			actualIDs := f.TestIDs().Values()
			if !reflect.DeepEqual(expectedIDs, actualIDs) {
				t.Fatalf("ID for %s incorrect: %v", m, actualIDs)
			}

			expectedHwAgnostic := true
			actualHwAgnostic, err := f.FindTestField("HwAgnostic").Bool()
			if err != nil {
				t.Fatalf("Could not read hw_agnostic: %v", err)
			}
			if expectedHwAgnostic != actualHwAgnostic {
				t.Fatalf("HwAgnostic for %s incorrect: %v", m, expectedHwAgnostic)
			}
		case "params.go":
			expectedIDs := []string{"tast.parse_file.HasParams",
				"tast.parse_file.HasParams.variant1",
				"tast.parse_file.HasParams.variant2"}
			actualIDs := f.TestIDs().Values()
			if !reflect.DeepEqual(expectedIDs, actualIDs) {
				t.Fatalf("IDs for %s incorrect: %v", m, actualIDs)
			}
		}
	}
}
