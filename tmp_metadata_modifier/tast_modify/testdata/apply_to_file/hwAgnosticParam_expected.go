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
		Attr:         []string{"group:mainline"},
		Timeout:      chrome.GAIALoginTimeout + time.Minute,
		HwAgnostic:   true,
		Params: []testing.Param{
			{
				Name:              "variant1",
				ExtraHardwareDeps: hwdep.D(pre.AppsStableModels),
				ExtraAttr:         []string{"group:mainline"},
				Val: testParameters{
					tabletMode: false,
					oobe:       true,
				},
			}, {
				Name:              "variant2",
				ExtraHardwareDeps: hwdep.D(pre.AppsStableModels),
				ExtraAttr:         []string{"group:mainline"},
				Fixture:           fixture.LoggedIn,
				Val: testParameters{
					tabletMode: false,
					oobe:       false,
				},
			},
		}})
}

func not_init() {}
