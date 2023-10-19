// Copyright 2023 The ChromiumOS Authors
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

package main

// Filter is a function which decides if a test file should be modified.
// It is applied to a TestFile object and returns true if actions should be
// run on this file (or an error if something goes wrong).
type Filter func(*TestFile) (bool, error)

func TestFilter(tests []string) Filter {
	return func(f *TestFile) (bool, error) {
		id := f.TestID()
		for _, t := range tests {
			if id == t {
				return true, nil
			}
		}
		return false, nil
	}
}
