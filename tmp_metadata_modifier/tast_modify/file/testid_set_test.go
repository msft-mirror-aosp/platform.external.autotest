// Copyright 2023 The ChromiumOS Authors
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

package file

import (
	"reflect"
	"sort"
	"testing"
)

// TestTestIDSet covers the TestIDSet type.
func TestTestIDSet(t *testing.T) {
	a := NewTestIDSet([]string{"testA", "testB", "testC"})
	b := make(TestIDSet)

	b.Add("testA")
	b.Add("testC")

	a.Remove("testC")

	aExpected := []string{"testA", "testB"}
	aActual := a.Values()
	sort.Strings(aActual)
	if !reflect.DeepEqual(aExpected, aActual) {
		t.Fatalf("TestIDSet A was incorrect: %v", aActual)
	}

	if a.Has("testD") {
		t.Fatal("TestIDSet A claims to have a value it does not have.")
	}
	if !a.Has("testB") {
		t.Fatal("TestIDSet A claims to have not a value it does have.")
	}

	bExpected := []string{"testA", "testC"}
	bActual := b.Values()
	sort.Strings(bActual)
	if !reflect.DeepEqual(bExpected, bActual) {
		t.Fatalf("TestIDSet B was incorrect: %v", bActual)
	}

	overlapExpected := []string{"testA"}
	overlapActual := a.Overlap(b).Values()
	if !reflect.DeepEqual(overlapExpected, overlapActual) {
		t.Fatalf("TestIDSet Overlap was incorrect: %v", overlapActual)
	}

	differenceExpected := []string{"testB"}
	differenceActual := a.Difference(b).Values()
	if !reflect.DeepEqual(differenceExpected, differenceActual) {
		t.Fatalf("TestIDSet Difference was incorrect: %v", differenceActual)
	}
}
