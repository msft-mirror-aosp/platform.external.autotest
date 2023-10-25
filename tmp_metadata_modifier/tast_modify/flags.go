// Copyright 2023 The ChromiumOS Authors
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

package main

import (
	"flag"
	"fmt"
	"strings"

	"go.chromium.org/chromiumos/tast_metadata_modifier/action"
	"go.chromium.org/chromiumos/tast_metadata_modifier/filter"
)

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

func HandleInputFlags() (srcDir string, pathFilter *PathFilter,
	filters []filter.Filter, actions []action.Action,
	mode OutputMode) {
	// The chromiumos src/ directory relative to this file.
	const defaultSrcDir = "../../../../../"
	mode = ModeDryRunVerbose

	// Path flags.
	var packages string
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
	var setHwAgnostic, unsetHwAgnostic bool
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
	flag.BoolVar(&setHwAgnostic, "setHwAgnostic", false, "Action: Set HwAgnostic to true.")
	flag.BoolVar(&unsetHwAgnostic, "unsetHwAgnostic", false,
		"Action: Remove HwAgnostic field (defaults to false).")

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
	flag.BoolVar(&dryRunVerbose, "dryRunVerbose", false,
		"Mode: (Default) Print which tests would be moified AND print the file contents with these changes.")

	flag.Parse()

	// Handle path flags.
	if publicOnly && privateOnly {
		panic("Can only choose one of: publicOnly and privateOnly")
	}
	if localOnly && remoteOnly {
		panic("Can only choose one of: localOnly and remoteOnly")
	}
	pathFilter = &PathFilter{
		SkipPublic:  privateOnly,
		SkipPrivate: publicOnly,
		SkipLocal:   remoteOnly,
		SkipRemote:  localOnly,
		Packages:    splitInputStrings(packages),
	}

	// Handle action flags.
	if removeContacts != "" {
		actions = append(actions, action.RemoveContacts(splitInputStrings(removeContacts)))
		fmt.Println(splitInputStrings(removeContacts))
	}
	if replaceContact != "" {
		input := splitInputStrings(replaceContact)
		if len(input) != 2 {
			panic("replaceContact flag takes exactly two comma or newline separated arguments!")
		}
		actions = append(actions, action.ReplaceContact(input[0], input[1]))
	}
	if appendContacts != "" {
		actions = append(actions, action.AppendContacts(splitInputStrings(appendContacts)))
	}
	if prependContacts != "" {
		actions = append(actions, action.PrependContacts(splitInputStrings(prependContacts)))
	}

	if setHwAgnostic && unsetHwAgnostic {
		panic("Cannot both set and unset HwAgnostic field!")
	}
	if setHwAgnostic {
		actions = append(actions, action.SetHwAgnostic())
	}
	if unsetHwAgnostic {
		actions = append(actions, action.UnsetHwAgnostic())
	}

	if len(actions) == 0 {
		panic("Must define at least one action!")
	}

	// Handle filter flags.
	if testNames != "" {
		filters = append(filters, filter.TestNames(splitInputStrings(testNames)))
	}

	// Handle mode flags.
	if (write && dryRun) || (write && dryRunVerbose) || (dryRun && dryRunVerbose) {
		panic("Cannot specify more than one mode!")
	}
	if write {
		mode = ModeWrite
	} else if dryRun {
		mode = ModeDryRun
	}

	return
}
