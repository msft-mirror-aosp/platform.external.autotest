// Copyright 2023 The ChromiumOS Authors
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

package action

import (
	"go.chromium.org/chromiumos/tast_metadata_modifier/file"
)

// Action is a function which modifies a test file.
// It is applied to a TestFile object and returns true if the file was modified
// as a result of the action (or an error if something goes wrong).
type Action func(*file.TestFile) (bool, error)
