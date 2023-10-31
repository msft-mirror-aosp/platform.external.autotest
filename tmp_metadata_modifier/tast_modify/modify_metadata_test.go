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

	"go.chromium.org/chromiumos/tast_metadata_modifier/action"
	"go.chromium.org/chromiumos/tast_metadata_modifier/file"
	"go.chromium.org/chromiumos/tast_metadata_modifier/filter"
)

type ApplyToFileTestcase struct {
	Actions []action.Action
	Filters []filter.Filter
}

// TestApplyToFile covers usage of the ApplyToFile() function.
// To add a new end-to-end test, add an entry below for which actions will be applied
// to the input file and create two new test files: <id>_input.go and <id>_expected.go.
func TestApplyToFile(t *testing.T) {
	TestDirPath := "testdata/apply_to_file"

	// Set up temporary directory in which to apply the file-modifying function.
	tmpDirPath := t.TempDir()
	tmpDirName := filepath.Base(tmpDirPath)

	// Testcase declarations.
	Testcases := map[string]ApplyToFileTestcase{
		"noop":          {},
		"appendContact": {Actions: []action.Action{action.AppendContacts([]string{"name@email.com"})}},
		"filteredNoop": {Filters: []filter.Filter{filter.TestNames(file.NewTestIDSet([]string{"notAMatch"}))},
			Actions: []action.Action{action.AppendContacts([]string{"name@email.com"})}},
		"filteredAppend": {Filters: []filter.Filter{filter.TestNames(file.NewTestIDSet([]string{
			fmt.Sprintf("tast.%s.FilteredAppend", tmpDirName)}))},
			Actions: []action.Action{action.AppendContacts([]string{"name@email.com"})}},
		"hwAgnosticModify":    {Actions: []action.Action{action.SetHwAgnostic(nil)}},
		"hwAgnosticAdd":       {Actions: []action.Action{action.SetHwAgnostic(nil)}},
		"hwAgnosticRemove":    {Actions: []action.Action{action.UnsetHwAgnostic(nil)}},
		"hwAgnosticRemoveAll": {Actions: []action.Action{action.UnsetHwAgnostic(nil)}},
		"hwAgnosticParam":     {Actions: []action.Action{action.SetHwAgnostic(nil)}},
		"hwAgnosticParamAll": {Actions: []action.Action{action.SetHwAgnostic(
			file.NewTestIDSet([]string{
				"tast." + tmpDirName + ".Simple.variant1",
				"tast." + tmpDirName + ".Simple.variant2",
			}))}},
		"hwAgnosticParamSome": {Actions: []action.Action{action.SetHwAgnostic(
			file.NewTestIDSet([]string{"tast." + tmpDirName + ".Simple.variant2"}))}},
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
		if _, err := ApplyToFile(tmpPath, tc.Filters, tc.Actions, ModeWrite); err != nil {
			t.Fatal(err)
		}

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
