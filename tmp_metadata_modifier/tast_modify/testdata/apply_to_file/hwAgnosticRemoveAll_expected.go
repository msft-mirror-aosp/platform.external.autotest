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
		Func:         Simple,
		LacrosStatus: testing.LacrosVariantUnneeded,
		Desc:         "testing description",
		Contacts:     []string{"contact@google.com"},
		BugComponent: "b:1234567",
	})
}

func not_init() {}
