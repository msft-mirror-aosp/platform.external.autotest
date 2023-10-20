// Copyright 2023 The ChromiumOS Authors
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

package main

import (
	"flag"
	"fmt"
	"os"
	"path/filepath"
	"strings"
)

// OutputMode represents how the function should behave with regards to overwriting data.
type OutputMode int

const (
	ModeDryRun OutputMode = iota
	ModeDryRunVerbose
	ModeWrite
)

// PathFilter represents which test files should be touched, based on the path to the file.
type PathFilter struct {
	SkipPublic  bool
	SkipPrivate bool
	SkipLocal   bool
	SkipRemote  bool
	Packages    []string
}

// WalkAllKnownTests looks for test packages in all known locations relative to the chromiumos
// src/ directory. These locations can be restricted through the given pathFilter.
// Calls ApplyToPackageDirs() on allowed locations with the given filters, actions, and outputMode.
func WalkAllKnownTests(srcDir string, pathFilter *PathFilter, filters []Filter,
	actions []Action, outputMode OutputMode) error {
	publicCrosDir := srcDir + "platform/tast-tests/src/go.chromium.org/tast-tests/cros/"
	privateCrosDir := srcDir + "platform/tast-tests-private/src/go.chromium.org/tast-tests-private/crosint/"

	dirsToSearch := []string{}
	if !pathFilter.SkipPublic {
		if !pathFilter.SkipLocal {
			dirsToSearch = append(dirsToSearch, publicCrosDir+"local/bundles/cros/")
		}
		if !pathFilter.SkipRemote {
			dirsToSearch = append(dirsToSearch, publicCrosDir+"remote/bundles/cros/")
		}
	}
	if !pathFilter.SkipPrivate {
		if !pathFilter.SkipLocal {
			dirsToSearch = append(dirsToSearch, privateCrosDir+"local/bundles/cros/")
		}
		if !pathFilter.SkipRemote {
			dirsToSearch = append(dirsToSearch, privateCrosDir+"remote/bundles/cros/")
		}
	}

	for _, dir := range dirsToSearch {
		if err := ApplyToPackageDirs(dir, pathFilter.Packages, filters,
			actions, outputMode); err != nil {
			return err
		}
	}
	return nil
}

// ApplyToPackageDirs applies the given actions and filters to package directories
// in the given directory. Only packages one directory deep from the given dir are searched.
// If names are given in allowedPackages slice, only these packages will
// be modified. Otherwise, all packages will be modified.
func ApplyToPackageDirs(dir string, allowedPackages []string, filters []Filter,
	actions []Action, outputMode OutputMode) error {
	if len(allowedPackages) == 0 {
		allowedPackages = append(allowedPackages, "*")
	}

	for _, p := range allowedPackages {
		matches, err := filepath.Glob(filepath.Join(dir, p, "*.go"))
		if err != nil {
			return err
		}
		for _, m := range matches {
			_, err := ApplyToFile(m, filters, actions, outputMode)
			if err != nil {
				return err
			}
		}
	}
	return nil
}

// ApplyToFile applies the given actions to the given file, if it matches the given filters.
// It returns a boolean on whether any action was taken, or an error.
// The output and whether files are actually modified depends on outputMode.
func ApplyToFile(filePath string, filters []Filter, actions []Action, outputMode OutputMode) (bool, error) {
	testFile, err := NewTestFile(filePath)
	if err != nil {
		return false, err
	} else if testFile == nil {
		// This file wasn't actually a test file.
		return false, nil
	}

	shouldModify := true
	for _, filter := range filters {
		fOutput, err := filter(testFile)
		if err != nil {
			fmt.Printf("Could not filter %s: %v\n", filePath, err)
			return false, err
		}
		shouldModify = shouldModify && fOutput
	}
	if !shouldModify {
		// One or more filters did not return true.
		return false, nil
	}

	modified := false
	for _, action := range actions {
		aOutput, err := action(testFile)
		if err != nil {
			fmt.Printf("Could not modify %s: %v\n", filePath, err)
			return false, err
		}
		modified = modified || aOutput
	}
	if !modified {
		// No edits were needed in this file.
		return false, nil
	}

	testFile.Format()
	switch outputMode {
	case ModeDryRun:
		fmt.Printf("Would write to %s:\n", filePath)
	case ModeDryRunVerbose:
		fmt.Printf("Would write to %s:\n%s", filePath, testFile.contents)
	case ModeWrite:
		err := os.WriteFile(filePath, testFile.contents, 0644)
		if err != nil {
			fmt.Printf("Failed writing changes to %s: %v\n", filePath, err)
			return false, err
		}
		fmt.Printf("Wrote changes to %s", filePath)
	}
	return true, nil
}

// splitInputStrings takes the given user input and breaks it into separate strings.
// Valid separators are newlines or commas. Any excess whitespace is trimmed.
func splitInputStrings(s string) []string {
	splitFunc := func(r rune) bool {
		return r == '\n' || r == ','
	}
	output := []string{}
	for _, elt := range strings.FieldsFunc(s, splitFunc) {
		if elt != "" {
			output = append(output, strings.TrimSpace(elt))
		}
	}
	return output
}

func main() {
	// The chromiumos src/ directory relative to this file.
	const defaultSrcDir = "../../../../"

	actions := []Action{}
	filters := []Filter{}
	mode := ModeDryRunVerbose

	// Path flags.
	var srcDir, packages string
	var privateOnly, publicOnly, localOnly, remoteOnly bool
	flag.StringVar(&srcDir, "path_SrcDir", defaultSrcDir,
		"Paths: Custom path to the src/ directory where tests will be modified.")
	flag.BoolVar(&privateOnly, "privateOnly", false, "Paths: Look at paths for private tests only.")
	flag.BoolVar(&publicOnly, "publicOnly", false, "Paths: Look at paths for public tests only.")
	flag.BoolVar(&localOnly, "localOnly", false, "Paths: Look at paths for local tests only.")
	flag.BoolVar(&remoteOnly, "remoteOnly", false, "Paths: Look at paths for remote tests only.")
	flag.StringVar(&packages, "packages", "", "Paths: Look at paths for the given packges only. "+
		"Input as a quoted string, e.g. 'packageFoo, packageBar'.")

	// Action flags.
	var removeContacts, replaceContact, appendContacts, prependContacts string
	flag.StringVar(&removeContacts, "removeContacts", "",
		"Action: Remove the given email addresses from Contacts. "+
			"Input as a quoted string, e.g. 'foo@google.com, bar@google.com'.")
	flag.StringVar(&replaceContact, "replaceContact", "",
		"Action: Replace the first email address with the second in Contacts. "+
			"Input as a quoted string, e.g. 'foo@google.com, bar@google.com'.")
	flag.StringVar(&appendContacts, "appendContacts", "",
		"Action: Append the given emails to the end of the Contacts list "+
			"(removing them if they already appear). "+
			"Input as a quoted string, e.g. 'foo@google.com, bar@google.com'.")
	flag.StringVar(&prependContacts, "prependContacts", "",
		"Action: Prepend the given emails to the start of the Contacts list "+
			"(removing them if they already appear). "+
			"Input as a quoted string, e.g. 'foo@google.com, bar@google.com'.")

	// Filter flags.
	var testNames string
	flag.StringVar(&testNames, "testNames", "",
		"Filter: Modify only tests with the given ids. "+
			"Input as a quoted string, e.g. 'tast.packageName.TestName, tast.packageName.OtherTestName'.")

	// Mode flags.
	var write, dryRun, dryRunVerbose bool
	flag.BoolVar(&write, "write", false,
		"Mode: Make changes to test files. Print which files have been modified.")
	flag.BoolVar(&dryRun, "dryRun", false,
		"Mode: Print which tests would be modified but do not make changes.")
	flag.BoolVar(&dryRunVerbose, "dryRunVerbose", true,
		"Mode: (Default) Print which tests would be moified AND print the file contents with these changes.")

	flag.Parse()

	// Handle path flags.
	if publicOnly && privateOnly {
		panic("Can only choose one of: publicOnly and privateOnly")
	}
	if localOnly && remoteOnly {
		panic("Can only choose one of: localOnly and remoteOnly")
	}
	pathFilter := &PathFilter{
		SkipPublic:  privateOnly,
		SkipPrivate: publicOnly,
		SkipLocal:   remoteOnly,
		SkipRemote:  localOnly,
		Packages:    splitInputStrings(packages),
	}

	// Handle action flags.
	if removeContacts != "" {
		actions = append(actions, RemoveContactsAction(splitInputStrings(removeContacts)))
		fmt.Println(splitInputStrings(removeContacts))
	}
	if replaceContact != "" {
		input := splitInputStrings(replaceContact)
		if len(input) != 2 {
			panic("replaceContact flag takes exactly two comma or newline separated arguments!")
		}
		actions = append(actions, ReplaceContactAction(input[0], input[1]))
	}
	if appendContacts != "" {
		actions = append(actions, AppendContactsAction(splitInputStrings(appendContacts)))
	}
	if prependContacts != "" {
		actions = append(actions, PrependContactsAction(splitInputStrings(prependContacts)))
	}
	if len(actions) == 0 {
		panic("Must define at least one action!")
	}

	// Handle filter flags.
	if testNames != "" {
		filters = append(filters, TestFilter(splitInputStrings(testNames)))
	}

	// Handle mode flags.
	if write && dryRun || write && dryRunVerbose || dryRun && dryRunVerbose {
		panic("Cannot specify more than one mode!")
	}
	if write {
		mode = ModeWrite
	} else if dryRun {
		mode = ModeDryRun
	}

	// Execute script with flag inputs.
	err := WalkAllKnownTests(srcDir, pathFilter, filters, actions, mode)
	if err != nil {
		fmt.Println(err)
		return
	}
}
