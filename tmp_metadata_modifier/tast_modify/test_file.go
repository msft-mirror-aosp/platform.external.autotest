// Copyright 2023 The ChromiumOS Authors
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

package main

import (
	"fmt"
	"os"

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
	if ok := testFile.ParseContents(); !ok {
		return nil, nil
	}
	return testFile, nil
}

// ParseContents takes the given file's contents and populates the fields of
// fset, ast, and expr.
// Can be called to update these values after contents are modified.
func (f *TestFile) ParseContents() bool {
	f.fset = token.NewFileSet()
	parsedFile, err := parser.ParseFile(f.fset, f.path, f.contents, 0)
	if err != nil {
		fmt.Printf("Could not read %s: %v\n", f.path, err)
		return false
	}
	f.ast = parsedFile

	expr, ok := FindTestExpr(f.ast)
	if ok {
		f.expr = expr
	}
	return ok
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
	funcName, ok := f.expr.ExprOf("Func").(*ast.Ident)
	if !ok {
		return ""
	}
	packageName := filepath.Base(filepath.Dir(f.path))
	return fmt.Sprintf("tast.%s.%s", packageName, funcName)
}

// Contacts returns the contacts declared in this TestFile.
func (f *TestFile) Contacts() []string {
	return f.expr.ValueOfStringList("Contacts")
}

// SetContacts replaces the inner contents of the existing Contacts []string{...}.
// Each email is put on a new line.
// Existing comments are ignored.
// No changes are made if the Contacts field is not present in the file.
func (f *TestFile) SetContacts(emails []string) {
	if len(emails) == 0 {
		return
	}
	replacement := "\n"
	for _, email := range emails {
		replacement += "\"" + email + "\",\n"
	}

	contacts := f.expr.ExprOf("Contacts").(*ast.CompositeLit)
	start := f.fset.PositionFor(contacts.Lbrace, true).Offset + 1
	end := f.fset.PositionFor(contacts.Rbrace, true).Offset - 1
	f.contents = append(
		f.contents[0:start],
		append(
			[]byte(replacement),
			f.contents[end+1:len(f.contents)]...)...)

	// Re-parse the contents of the file to update the ast values.
	f.ParseContents()
}

// RemoveContact removes a given email alias from the contacts list.
// Returns whether or not a modification was made.
func (f *TestFile) RemoveContact(email string) bool {
	contacts := []string{}
	modified := false
	for _, elt := range f.Contacts() {
		if elt == email {
			modified = true
		} else {
			contacts = append(contacts, email)
		}
	}
	if modified {
		f.SetContacts(contacts)
	}
	return modified
}
