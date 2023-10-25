// Copyright 2023 The ChromiumOS Authors
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

package file

import (
	"fmt"
	"os"
	"strings"

	"go/ast"
	"go/format"
	"go/parser"
	"go/token"
	"path/filepath"
)

// TestFile represents a single file which declares a test.
type TestFile struct {
	path     string
	contents []byte
	ast      *ast.File
	fset     *token.FileSet
	expr     *TestExpr
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
	if testFile.expr == nil {
		return nil, nil
	}
	return testFile, nil
}

// ParseContents takes the given file's contents and populates the fields of
// fset, ast, and expr.
func (f *TestFile) ParseContents() error {
	f.fset = token.NewFileSet()
	parsedFile, err := parser.ParseFile(f.fset, f.path, f.contents, 0)
	if err != nil {
		return fmt.Errorf("Could not parse %s: %v", f.path, err)
	}
	f.ast = parsedFile

	expr, ok := FindTestExpr(f.ast)
	if ok {
		f.expr = expr
	} else {
		f.expr = nil
	}
	return nil
}

// ReparseContents takes the given file's new contents and re-populates
// the fields of fset, ast, and expr.
// Can be called to update these values after contents are modified.
func (f *TestFile) ReparseContents() error {
	if err := f.ParseContents(); err != nil {
		return fmt.Errorf("On reparse: %v", err)
	}
	if f.expr == nil {
		return fmt.Errorf("On reparse, could find test expression in %v!", f.path)
	}
	return nil
}

// Contents returns the contents of the file.
func (f *TestFile) Contents() []byte {
	return f.contents
}

// RemoveField removes a given fieldName's definition from the test file if
// it is set.
// Returns true if the file was modified.
func (f *TestFile) RemoveField(fieldName string) (bool, error) {
	field := f.expr.FindFieldExpr(fieldName)
	if field == nil || !field.isDefined {
		return false, nil // Field is not set.
	}
	start := f.fset.PositionFor(field.expr.Pos(), true).Offset
	end := f.fset.PositionFor(field.expr.End(), true).Offset
	// Clean up end position to avoid extra newlines.
	for f.contents[end] == ',' || f.contents[end] == '\n' {
		end += 1
	}
	f.contents = append(
		f.contents[0:start],
		f.contents[end:len(f.contents)]...)

	// Re-parse the contents of the file to update the ast values.
	if err := f.ReparseContents(); err != nil {
		return false, err
	}
	return true, nil
}

// SetFieldValue sets the given fieldName's definition in the test
// file. The field value is set as the given string representation of the code.
// If the field name is already present, the value will be replaced.
// Otherwise, it will be added to the end of the test expression.
// Returns true if the file was modified.
// E.g. f.SetFieldValue("Contents", "[]string{\"foo\"}")
func (f *TestFile) SetFieldValue(fieldName, newValue string) (bool, error) {
	fieldExpr := f.expr.FindFieldExpr(fieldName)
	if fieldExpr == nil || !fieldExpr.isDefined {
		return f.addField(fieldName, newValue) // Field should be added.
	}
	valueExpr := fieldExpr.expr.Value
	start := f.fset.PositionFor(valueExpr.Pos(), true).Offset
	end := f.fset.PositionFor(valueExpr.End(), true).Offset

	f.contents = append(
		f.contents[0:start],
		append(
			[]byte(newValue),
			f.contents[end:len(f.contents)]...)...)

	// Re-parse the contents of the file to update the ast values.
	if err := f.ReparseContents(); err != nil {
		return false, err
	}
	return true, nil
}

// addField adds the given fieldName's string representation of
// its contents to the end of the test file's test expression.
// If there is a Params field, add the new field before that instead.
// Assumes the field does not already exist in the list.
// Returns true if the file was modified.
func (f *TestFile) addField(fieldName, value string) (bool, error) {
	code := []byte(fmt.Sprintf(",\n%v: %v", fieldName, value))

	nextPos := -1
	allFields := f.expr.AllFieldExprs()
	if paramsExpr := f.expr.FindFieldExpr("Params"); paramsExpr != nil && paramsExpr.isDefined {
		// Add the new code just before the Params definition.
		if paramsExpr.idx != 0 {
			prevExpr := allFields[paramsExpr.idx-1]
			nextPos = f.fset.PositionFor(prevExpr.expr.End(), true).Offset
		} else {
			nextPos = f.fset.PositionFor(paramsExpr.expr.Pos(), true).Offset
		}
	} else {
		// Add the new code just after the last field definition.
		prevExpr := allFields[len(allFields)-1]
		nextPos = f.fset.PositionFor(prevExpr.expr.End(), true).Offset
	}

	f.contents = append(
		f.contents[0:nextPos],
		append(code, f.contents[nextPos:len(f.contents)]...)...)

	// Re-parse the contents of the file to update the ast values.
	if err := f.ReparseContents(); err != nil {
		return false, err
	}
	return true, nil
}

// Format is equivalent to running gofmt on f.contents.
func (f *TestFile) Format() error {
	output, err := format.Source(f.contents)
	f.contents = output
	return err
}

// TestID returns the testID of this TestFile.
// This does NOT include parameterized tests.
func (f *TestFile) TestID() string {
	funcName := "UnknownTestID"
	funcField := f.expr.FindFieldExpr("Func")
	if funcField != nil && funcField.isDefined {
		funcValue, ok := funcField.expr.Value.(*ast.Ident)
		if funcValue != nil && ok {
			funcName = funcValue.Name
		}
	}
	packageName := filepath.Base(filepath.Dir(f.path))
	return fmt.Sprintf("tast.%s.%s", packageName, funcName)
}

// Contacts returns the contacts declared in this TestFile.
// Return an empty slice if no contacts are defined.
func (f *TestFile) Contacts() []string {
	contactsExpr := f.expr.FindFieldExpr("Contacts")
	if contactsExpr == nil || !contactsExpr.isDefined {
		return []string{}
	}
	contacts, err := contactsExpr.StringSliceValue()
	if err != nil {
		fmt.Println(err)
		return []string{}
	}
	return contacts
}

// SetContacts replaces the inner contents of the existing Contacts []string{...}.
// Each email is put on a new line.
// Existing comments are ignored.
// No changes are made if the Contacts field is not present in the file.
func (f *TestFile) SetContacts(emails []string) (bool, error) {
	if len(emails) == 0 {
		return false, nil
	}
	newCode := fmt.Sprintf("[]string{\n\"%s\",\n}", strings.Join(emails, "\",\n\""))
	return f.SetFieldValue("Contacts", newCode)
}

// HwAgnostic returns the value of the HwAgnostic field, or false
// if it is not set or there was any problem reading the value.
// NB: False is the default value for HwAgnostic.
func (f *TestFile) HwAgnostic() bool {
	hwAgnosticExpr := f.expr.FindFieldExpr("HwAgnostic")
	if hwAgnosticExpr == nil || !hwAgnosticExpr.isDefined {
		return false
	}
	b, err := hwAgnosticExpr.BoolValue()
	if err != nil {
		return false
	}
	return b
}
