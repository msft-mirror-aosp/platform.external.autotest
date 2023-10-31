// Copyright 2023 The ChromiumOS Authors
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

package file

// A TestIDSet represents a group of test ids.
type TestIDSet map[string]struct{}

// NewTestIDSet turns the given slice into a testid set.
func NewTestIDSet(input []string) TestIDSet {
	output := make(TestIDSet)
	output.AddAll(input)
	return output
}

// Add adds a single element to the testid set.
func (s TestIDSet) Add(elt string) {
	s[elt] = struct{}{}
}

// AddAll adds a slice to the testid set.
func (s TestIDSet) AddAll(elts []string) {
	for _, elt := range elts {
		s.Add(elt)
	}
}

// Remove removes a single element from the testid set.
func (s TestIDSet) Remove(elt string) {
	delete(s, elt)
}

// RemoveAll remove a slice from the testid set.
func (s TestIDSet) RemoveAll(elts []string) {
	for _, elt := range elts {
		s.Remove(elt)
	}
}

// Has returns whether the given test is represented in the set.
func (s TestIDSet) Has(elt string) bool {
	_, ok := s[elt]
	return ok
}

// Overlap returns the tests in the base set that are represented
// in the input set.
func (s TestIDSet) Overlap(input TestIDSet) TestIDSet {
	output := make(TestIDSet)
	a, b := s, input
	if len(a) < len(b) {
		a, b = b, a // Ensure b is the smaller of the two.
	}
	for elt := range b {
		if a.Has(elt) {
			output.Add(elt)
		}
	}
	return output
}

// Difference returns the tests in the base set that are NOT represented
// in the input set.
func (s TestIDSet) Difference(input TestIDSet) TestIDSet {
	output := make(TestIDSet)
	for elt := range s {
		if !input.Has(elt) {
			output.Add(elt)
		}
	}
	return output
}

// Values returns all the values as a slice.
func (s TestIDSet) Values() []string {
	output := make([]string, len(s))
	i := 0
	for t := range s {
		output[i] = t
		i++
	}
	return output
}
