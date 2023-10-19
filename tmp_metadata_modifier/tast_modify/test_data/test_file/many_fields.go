// Copyright 2023 The ChromiumOS Authors
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

package test

import (
	"imports"
)

type otherThings struct {
	foo string
}

func init() {
	testing.AddTest(&testing.Test{
		Func:         Many,
		LacrosStatus: testing.LacrosVariantUnneeded,
		Desc:         "testing description",
		Contacts: []string{
			"first@google.com",
			"second@google.com",
		},
		BugComponent: "b:1234567",
		Attr:         []string{"group:mainline"},
		HwAgnostic:   true,
		Requirements:     []string{"reqOne", "reqTwo"},
	})
}

func not_init() {}
