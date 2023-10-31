// Copyright 2023 The ChromiumOS Authors
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

package action

import (
	"go.chromium.org/chromiumos/tast_metadata_modifier/file"
)

// Note that for HwAgnostic there are two relevant field names:
//   - Attr for a test overall (including all parameterized tests in the file)
//   - ExtraAttr for a single parameterized test.
//
// The correct group id must be included in either list for the test to be
// marked as HwAgnostic.
const (
	hwAgnosticAttr     = "group:hw_agnostic"
	attrFieldName      = "Attr"
	extraAttrFieldName = "ExtraAttr"
)

// hwAgnosticInField returns whether the given field has the hw_agnostic group.
func hwAgnosticInField(field *file.FieldExpr) (bool, error) {
	if field == nil {
		return false, nil
	}
	elts, err := field.Strings()
	if err != nil {
		return false, err
	}
	for _, elt := range elts {
		if elt == hwAgnosticAttr {
			return true, nil
		}
	}
	return false, nil
}

// isHwAgnosticTest returns whether the overall test is hw_agnostic.
func isHwAgnosticTest(f *file.TestFile) (bool, error) {
	return hwAgnosticInField(f.FindTestField(attrFieldName))
}

// isHwAgnosticParam returns whether the given param test is hw_agnostic.
func isHwAgnosticParam(f *file.TestFile, paramTest string) (bool, error) {
	return hwAgnosticInField(f.FindParamField(extraAttrFieldName, paramTest))
}

// setHwAgnosticAll sets every test in the file as hw_agnostic, making sure that
// any param test isn't also set.
func setHwAgnosticAll(f *file.TestFile, paramTests file.TestIDSet) (bool, error) {
	for t := range paramTests {
		if _, err := unsetHwAgnosticParamTest(f, t); err != nil {
			return false, err
		}
	}
	return f.AddToTestStrings(attrFieldName, []string{hwAgnosticAttr}, file.FormatOneLine)
}

// setHwAgnosticParamTest sets the given param test as hw_agnostic in the given file.
func setHwAgnosticParamTest(f *file.TestFile, paramTest string) (bool, error) {
	return f.AddToParamStrings(
		paramTest, extraAttrFieldName, []string{hwAgnosticAttr}, file.FormatOneLine)
}

// unsetHwAgnosticAll ensures no test in the given file is marked as hw_agnostic.
func unsetHwAgnosticAll(f *file.TestFile, paramTests file.TestIDSet) (bool, error) {
	for p := range paramTests {
		_, err := f.RemoveStringsFromParam(
			p, extraAttrFieldName, []string{hwAgnosticAttr}, file.FormatOneLine)
		if err != nil {
			return false, err
		}
	}
	return f.RemoveStringsFromTest(attrFieldName, []string{hwAgnosticAttr}, file.FormatOneLine)
}

// unsetHwAgnosticParamTest unsets the given param test as hw_agnostic in the given file.
func unsetHwAgnosticParamTest(f *file.TestFile, paramTest string) (bool, error) {
	return f.RemoveStringsFromParam(
		paramTest, extraAttrFieldName, []string{hwAgnosticAttr}, file.FormatOneLine)
}

// SetHwAgnostic returns an action that sets hw_agnostic to true for the
// given test ids (or for all tests if nil). The value is set by adding
// "group:hw_agnostic" to the Attr field or ExtraAttr field for parameterized
// tests.
func SetHwAgnostic(tests file.TestIDSet) Action {
	return func(f *file.TestFile) (bool, error) {
		parentID := f.ParentTestID()
		paramTests := f.ParamTestIDs()

		// No test filter applied; add to everything.
		if tests == nil || len(tests) == 0 {
			return setHwAgnosticAll(f, paramTests)
		}

		// If this file has no parameterized tests, add only to the parent test.
		if paramTests == nil || len(paramTests) == 0 {
			return setHwAgnosticAll(f, paramTests)
		}

		// If the file is already hw_agnostic at the top level, all the param tests
		// are already hw_agnostic, so do nothing.
		isHwAgnostic, err := isHwAgnosticTest(f)
		if err != nil || isHwAgnostic {
			return false, err
		}

		// If the parent test name is in the filter it is either a default parameterized
		// test (and should be treated as a param test) or it should be treated as
		// a shortcut to apply to the entire file (the case handled below).
		if tests.Has(parentID) && !paramTests.Has(parentID) {
			return setHwAgnosticAll(f, paramTests)
		}

		// If the tests in the filter match all the tests present, set all tests.
		overlap := paramTests.Overlap(tests)
		if len(overlap) == len(paramTests) {
			return setHwAgnosticAll(f, paramTests)
		}

		// Not all param tests matched the filter, so check the remaining tests. If all
		// of those remaining are ALREADY hw_agnostic, set for the entire file instead.
		allAlreadyMatched := true
		for t := range paramTests.Difference(tests) {
			isHwAgnostic, err := isHwAgnosticParam(f, t)
			if err != nil {
				return false, err
			}
			if !isHwAgnostic {
				allAlreadyMatched = false
				break
			}
		}
		if allAlreadyMatched {
			return setHwAgnosticAll(f, paramTests)
		}

		// Set only matching tests in the filter as the default case.
		modified := false
		for t := range overlap {
			mLoop, err := setHwAgnosticParamTest(f, t)
			if err != nil {
				return modified || mLoop, err
			}
			modified = modified || mLoop
		}
		return modified, nil
	}
}

// UnsetHwAgnostic returns an action that removes the hw_agnostic
// definition, if any, from the given test ids (or from all
// tests if nil).
// This is done by removing the "group:hw_agnostic" value from
// Attr (or ExtraAttr) field.
func UnsetHwAgnostic(tests file.TestIDSet) Action {
	return func(f *file.TestFile) (bool, error) {
		parentID := f.ParentTestID()
		paramTests := f.ParamTestIDs()

		// No test filter applied; remove from everything.
		if tests == nil || len(tests) == 0 {
			return unsetHwAgnosticAll(f, paramTests)
		}

		// If this file has no parameterized tests, remove from the parent test.
		if paramTests == nil || len(paramTests) == 0 {
			return unsetHwAgnosticAll(f, paramTests)
		}

		// If the parent test name is in the filter it is either a default parameterized
		// test (and should be treated as a param test) or it should be treated as
		// a shortcut to apply to the entire file (the case handled below).
		if tests.Has(parentID) && !paramTests.Has(parentID) {
			return unsetHwAgnosticAll(f, paramTests)
		}

		// If the tests in the filter match all the tests present, unset all tests.
		overlap := paramTests.Overlap(tests)
		if len(overlap) == len(paramTests) {
			return unsetHwAgnosticAll(f, paramTests)
		}

		// Not all param tests matched the filter. If the entire file is hw_agnostic already,
		// we need to set the tests which don't match the filter.
		isHwAgnostic, err := isHwAgnosticTest(f)
		if err != nil {
			return false, err
		}
		if isHwAgnostic {
			if _, err := unsetHwAgnosticAll(f, paramTests); err != nil {
				return false, err
			}
			for t := range paramTests.Difference(tests) {
				if _, err := setHwAgnosticParamTest(f, t); err != nil {
					return false, err
				}
			}
		}

		// Unset only matching tests in the filter as the default case.
		modified := false
		for t := range overlap {
			mLoop, err := unsetHwAgnosticParamTest(f, t)
			if err != nil {
				return modified || mLoop, err
			}
			modified = modified || mLoop
		}
		return modified, nil
	}
}
