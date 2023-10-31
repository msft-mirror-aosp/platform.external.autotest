// Copyright 2023 The ChromiumOS Authors
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

package filter

import (
	"go.chromium.org/chromiumos/tast_metadata_modifier/file"
)

// Filter is a function which decides if a test file should be modified.
// It is applied to a file.TestFile object and returns true if actions should be
// run on this file (or an error if something goes wrong).
type Filter func(*file.TestFile) (bool, error)

// TestNames returns a Filter which flags whether or not a matching
// file has a test name in the given list of ids.
// e.g. "tast.packageName.TestName".
func TestNames(tests file.TestIDSet) Filter {
	return func(f *file.TestFile) (bool, error) {
		ids := f.TestIDs()
		if overlap := tests.Overlap(ids); len(overlap) != 0 {
			return true, nil
		}
		return false, nil
	}
}
