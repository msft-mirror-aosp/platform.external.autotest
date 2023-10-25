// Copyright 2023 The ChromiumOS Authors
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

package action

import (
	"go.chromium.org/chromiumos/tast_metadata_modifier/file"
)

// SetHwAgnosticAction returns an action that explicitly sets hw_agnostic
// to true.
func SetHwAgnostic() Action {
	return func(f *file.TestFile) (bool, error) {
		return f.SetFieldValue("HwAgnostic", "true")
	}
}

// UnsetHwAgnosticAction returns an action that removes the hw_agnostic
// definition, if any.
func UnsetHwAgnostic() Action {
	return func(f *file.TestFile) (bool, error) {
		return f.RemoveField("HwAgnostic")
	}
}
