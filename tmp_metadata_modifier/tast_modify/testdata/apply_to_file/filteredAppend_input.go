// Copyright 2023 The ChromiumOS Authors
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

package test

import (
	"imports"
)

type otherThings struct {
	foo string
	weirdFormatting            string
}

func init() {
	testing.AddTest(&testing.Test{
		Func:         FilteredAppend,
		LacrosStatus: testing.LacrosVariantUnneeded,
		Desc:         "testing description",
		Contacts: []string{
			"first@google.com",
			"second@google.com",
			"third@google.com"},
		BugComponent: "b:1234567",
		Attr:         []string{"group:mainline"},
	})
}

func not_init() {}
