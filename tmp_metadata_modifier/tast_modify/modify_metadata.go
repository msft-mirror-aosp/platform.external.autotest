// Copyright 2023 The ChromiumOS Authors
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

package main

import (
	"fmt"
	"os"
	"path/filepath"

	"go.chromium.org/chromiumos/tast_metadata_modifier/action"
	"go.chromium.org/chromiumos/tast_metadata_modifier/file"
	"go.chromium.org/chromiumos/tast_metadata_modifier/filter"
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
func WalkAllKnownTests(srcDir string, pathFilter *PathFilter, filters []filter.Filter,
	actions []action.Action, outputMode OutputMode) error {
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
func ApplyToPackageDirs(dir string, allowedPackages []string, filters []filter.Filter,
	actions []action.Action, outputMode OutputMode) error {
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
func ApplyToFile(filePath string, filters []filter.Filter, actions []action.Action,
	outputMode OutputMode) (bool, error) {
	testFile, err := file.NewTestFile(filePath)
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
		fmt.Printf("Would write to %s:%s\n", filePath, testFile.Contents())
	case ModeWrite:
		err := os.WriteFile(filePath, testFile.Contents(), 0644)
		if err != nil {
			fmt.Printf("Failed writing changes to %s: %v\n", filePath, err)
			return false, err
		}
		fmt.Printf("Wrote changes to %s\n", filePath)
	}
	return true, nil
}

func main() {
	srcDir, pathFilter, filters, actions, mode := HandleInputFlags()

	// Execute script with flag inputs.
	err := WalkAllKnownTests(srcDir, pathFilter, filters, actions, mode)
	if err != nil {
		fmt.Println(err)
		return
	}
}
