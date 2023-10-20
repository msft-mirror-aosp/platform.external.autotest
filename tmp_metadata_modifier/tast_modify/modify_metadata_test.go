// Copyright 2023 The ChromiumOS Authors
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

package main

import (
	"bytes"
	"fmt"
	"os"
	"testing"

	"path/filepath"
)

type ApplyToFileTestcase struct {
	Actions []Action
	Filters []Filter
}

// TestApplyToFile covers usage of the ApplyToFile() function.
// To add a new end-to-end test, add an entry below for which actions will be applied
// to the input file and create two new test files: <id>_input.go and <id>_expected.go.
func TestApplyToFile(t *testing.T) {
	TestDirPath := "test_data/apply_to_file"

	// Set up temporary directory in which to apply the file-modifying function.
	tmpDirPath := t.TempDir()
	tmpDirName := filepath.Base(tmpDirPath)
	fmt.Println(fmt.Sprintf("tast.%s.FilteredAppend", tmpDirName))

	// Testcase declarations.
	Testcases := map[string]ApplyToFileTestcase{
		"noop":          {},
		"appendContact": {Actions: []Action{AppendContactsAction([]string{"name@email.com"})}},
		"filteredNoop": {Filters: []Filter{TestFilter([]string{"notAMatch"})},
			Actions: []Action{AppendContactsAction([]string{"name@email.com"})}},
		"filteredAppend": {Filters: []Filter{TestFilter([]string{
			fmt.Sprintf("tast.%s.FilteredAppend", tmpDirName)})},
			Actions: []Action{AppendContactsAction([]string{"name@email.com"})}},
	}

	// Iterate through testcases.
	for id, tc := range Testcases {
		inputPath := filepath.Join(TestDirPath, id+"_input.go")
		expectedPath := filepath.Join(TestDirPath, id+"_expected.go")
		tmpPath := filepath.Join(tmpDirPath, id)

		// Copy input file to temporary directory.
		input, err := os.ReadFile(inputPath)
		if err != nil {
			t.Fatal(err)
		}
		tmp, err := os.Create(tmpPath)
		if err != nil {
			t.Fatal(err)
		}
		_, err = tmp.Write(input)
		if err != nil {
			t.Fatal(err)
		}
		err = tmp.Close()
		if err != nil {
			t.Fatal(err)
		}

		// Run testcase against the temporary file.
		ApplyToFile(tmpPath, tc.Filters, tc.Actions, ModeWrite)

		expected, err := os.ReadFile(expectedPath)
		if err != nil {
			t.Fatal(err)
		}

		actual, err := os.ReadFile(tmpPath)
		if err != nil {
			t.Fatal(err)
		}

		// Compare actual results to expected.
		if !bytes.Equal(expected, actual) {
			t.Fatalf("%s returned:\n%s", id, actual)
		}
	}
}
