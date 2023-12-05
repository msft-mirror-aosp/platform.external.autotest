// Copyright 2023 The ChromiumOS Authors
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

package file

import (
	"fmt"
	"os"

	"go/format"
	"go/parser"
	"go/token"
	"path/filepath"
)

// TestFile represents a single file which declares a test.
type TestFile struct {
	path       string
	contents   []byte
	fset       *token.FileSet
	testExpr   *TestExpr
	paramExprs map[string]*ParamTestExpr
}

// NewTestFile returns a TestFile for the given filepath,
// or false something went wrong (such as the file not having a test declaration).
func NewTestFile(filePath string) (*TestFile, error) {
	contents, err := os.ReadFile(filePath)
	if err != nil {
		return nil, err
	}

	testFile := &TestFile{
		path:     filePath,
		contents: contents,
	}
	if err := testFile.ParseContents(); err != nil {
		return nil, err
	}
	if testFile.testExpr == nil {
		return nil, nil
	}
	return testFile, nil
}

// ParseContents takes the given file's contents and populates the fields of
// fset, testExpr, and paramExprs.
func (f *TestFile) ParseContents() error {
	f.fset = token.NewFileSet()
	parsedFile, err := parser.ParseFile(f.fset, f.path, f.contents, 0)
	if err != nil {
		return fmt.Errorf("Could not parse %s: %v", f.path, err)
	}

	testExpr, ok := FindTestExpr(parsedFile)
	if !ok || testExpr == nil {
		return nil // No error - this just wasn't a test file.
	}
	f.testExpr = testExpr // Needs to be set before calling ParentTestID.

	// Look for parameterized tests and print out a warning if there is any problem.
	// Some tests use custom functions to define parameterized tests, and those
	// are out-of-scope for this tool.
	paramExprs, err := testExpr.FindParamTestExprs(f.ParentTestID())
	if err != nil {
		fmt.Printf("WARNING: could not parse Parameterized tests for %s\n", f.path)
		return nil
	}
	f.paramExprs = paramExprs

	return nil
}

// ReparseContents takes the given file's new contents and re-populates
// the fields of fset, testExpr, and paramExprs.
// Can be called to update these values after contents are modified.
func (f *TestFile) ReparseContents() error {
	if err := f.ParseContents(); err != nil {
		return fmt.Errorf("On reparse: %v", err)
	}
	if f.testExpr == nil {
		return fmt.Errorf("On reparse, could find test expression in %v!", f.path)
	}
	return nil
}

// Format is equivalent to running gofmt on f.contents.
func (f *TestFile) Format() error {
	output, err := format.Source(f.contents)
	f.contents = output
	return err
}

// Contents returns the contents of this file.
func (f *TestFile) Contents() []byte {
	return f.contents
}

// Path returns the path of this file.
func (f *TestFile) Path() string {
	return f.path
}

// Offset returns the integer offset of the given position in the current file,
// adjusted for things like line comments.
// The resulting integer can be used to index into f.contents.
func (f *TestFile) Offset(pos token.Pos) int {
	return f.fset.PositionFor(pos, true).Offset
}

// RemoveTestField removes a given fieldName's definition from the test file if
// it is set.
// Returns true if the file was modified.
func (f *TestFile) RemoveTestField(fieldName string) (bool, error) {
	return f.testExpr.RemoveField(f, fieldName)
}

// RemoveParamField removes a given fieldName from the given parameterized test.
func (f *TestFile) RemoveParamField(
	fieldName string, paramTest string) (bool, error) {
	return f.paramExprs[paramTest].RemoveField(f, fieldName)
}

// SetTestField sets the given fieldName's definition in the test
// file. The field value is set as the given string representation of the code.
// If the field name is already present, the value will be replaced.
// Otherwise, it will be added to the end of the test expression.
// E.g. f.SetTestField("Contents", "[]string{\"foo\"}")
func (f *TestFile) SetTestField(fieldName, newValue string) (bool, error) {
	return f.testExpr.SetField(f, fieldName, newValue)
}

// SetParamField sets the given fieldName's definition in given
// parameterized test name.
// The field value is set as the given string representation of the code.
// If the field name is already present, the value will be replaced.
// Otherwise, it will be added to the end of the test expression.
// E.g. f.SetParamField("Contents", "[]string{\"foo\"}")
func (f *TestFile) SetParamField(
	fieldName, newValue string, paramTest string) (bool, error) {
	return f.paramExprs[paramTest].SetField(f, fieldName, newValue)
}

// FindTestField returns the field expression from the main body
// of the test expression, or nil if it is undefined.
func (f *TestFile) FindTestField(fieldName string) *FieldExpr {
	return f.testExpr.FindFieldExpr(fieldName)
}

// FindTestField returns the field expression from the given parameterized
// test name, or nil if it is undefined.
func (f *TestFile) FindParamField(fieldName, paramTest string) *FieldExpr {
	return f.paramExprs[paramTest].FindFieldExpr(fieldName)
}

func (f *TestFile) RemoveStringsFromTest(fieldName string, input []string,
	format Format) (bool, error) {
	return f.testExpr.StructExpr.RemoveFromStrings(f, fieldName, input, format)
}

func (f *TestFile) RemoveStringsFromParam(paramTest, fieldName string,
	input []string, format Format) (bool, error) {
	return f.paramExprs[paramTest].RemoveFromStrings(f, fieldName, input, format)
}

func (f *TestFile) AddToTestStrings(fieldName string, input []string,
	format Format) (bool, error) {
	return f.testExpr.AddToStrings(f, fieldName, input, format)
}

func (f *TestFile) AddToParamStrings(paramTest, fieldName string,
	input []string, format Format) (bool, error) {
	return f.paramExprs[paramTest].AddToStrings(f, fieldName, input, format)
}

// TestIDs returns the testIDs of the parent test and
// any parameterized tests defined this TestFile.
func (f *TestFile) TestIDs() TestIDSet {
	output := f.ParamTestIDs()
	if output == nil {
		output = make(TestIDSet)
	}
	output.Add(f.ParentTestID())
	return output
}

// ParentTestID returns the testID of the main test, i.e. not
// a parameterized test.
// E.g. tast.packageName.TestName.
func (f *TestFile) ParentTestID() string {
	funcName := f.testExpr.Name()
	packageName := filepath.Base(filepath.Dir(f.path))
	return fmt.Sprintf("tast.%s.%s", packageName, funcName)
}

// ParamTestIDs returns the testIDs of any parameterized
// tests defined in this test file, or nil if there are none.
// E.g. tast.packageName.TestName.subtestName.
func (f *TestFile) ParamTestIDs() TestIDSet {
	if f.paramExprs == nil {
		return nil
	}
	output := make(TestIDSet)
	for p := range f.paramExprs {
		output.Add(p)
	}
	return output
}
