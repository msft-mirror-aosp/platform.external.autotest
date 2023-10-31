// Copyright 2023 The ChromiumOS Authors
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

package file

import (
	"fmt"

	"go/ast"
)

// StructExpr is a generic ast CompositeLit which can have fields
// removed or added to it within a test file.
// Specific examples are the testing.Test{...} contents or the
// elements in a []testing.Param{...} slice elements.
type StructExpr struct {
	*ast.CompositeLit
}

// StructFunc is a function which acts on a StructExpr, returning
// a boolean if anything was modified or an error if anything went wrong.
type StructFunc func(expr *StructExpr, isParam bool) (bool, error)

// FindFieldExpr returns the FieldExpr for the given field name,
// or an error if a problem was found.
// e.g. x.FieldExpr("Contacts") will find the expression for
// the code declaring `Contacts: string[]{...}`
func (x *StructExpr) FindFieldExpr(keyName string) *FieldExpr {
	for i, elt := range x.Elts {
		pair, ok := elt.(*ast.KeyValueExpr)
		if !ok {
			continue
		}
		key, ok := pair.Key.(*ast.Ident)
		if !ok {
			continue
		}
		if key.Name == keyName {
			return &FieldExpr{
				name: keyName,
				expr: pair,
				idx:  i,
			}
		}
	}
	return nil
}

// AllFieldExprs returns a slice of the FieldExpr for this struct expression,
// or an error if a problem was found.
// Fields are returned in the order in which they are listed in code.
func (x *StructExpr) AllFieldExprs() []*FieldExpr {
	fields := []*FieldExpr{}
	for i, elt := range x.Elts {
		pair, ok := elt.(*ast.KeyValueExpr)
		if !ok {
			continue
		}
		key, ok := pair.Key.(*ast.Ident)
		if !ok {
			continue
		}
		fields = append(fields, &FieldExpr{
			name: key.Name,
			expr: pair,
			idx:  i,
		})
	}
	return fields
}

// RemoveField removes a given fieldName's definition from the test file if
// it is set.
// Returns true if the file was modified.
func (x *StructExpr) RemoveField(f *TestFile, fieldName string) (bool, error) {
	field := x.FindFieldExpr(fieldName)
	if field == nil {
		return false, nil // Field is not set.
	}
	start := f.Offset(field.expr.Pos())
	end := f.Offset(field.expr.End())
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

// SetField sets the given fieldName's definition in the test
// file. The field value is set as the given string representation of the code.
// If the field name is already present, the value will be replaced.
// Otherwise, it will be added to the end of the test expression.
// Returns true if the file was modified.
// E.g. f.SetField("Contents", "[]string{\"foo\"}")
func (x *StructExpr) SetField(f *TestFile, fieldName, newValue string) (bool, error) {
	fieldExpr := x.FindFieldExpr(fieldName)
	if fieldExpr == nil {
		return x.addField(f, fieldName, newValue) // Field should be added.
	}
	valueExpr := fieldExpr.expr.Value
	start := f.Offset(valueExpr.Pos())
	end := f.Offset(valueExpr.End())

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
func (x *StructExpr) addField(f *TestFile, fieldName, value string) (bool, error) {
	code := []byte(fmt.Sprintf(",\n%v: %v", fieldName, value))

	nextPos := -1
	allFields := x.AllFieldExprs()
	if paramsExpr := x.FindFieldExpr("Params"); paramsExpr != nil {
		// Add the new code just before the Params definition.
		if paramsExpr.idx != 0 {
			prevExpr := allFields[paramsExpr.idx-1]
			nextPos = f.Offset(prevExpr.expr.End())
		} else {
			nextPos = f.Offset(paramsExpr.expr.Pos())
		}
	} else {
		// Add the new code just after the last field definition.
		prevExpr := allFields[len(allFields)-1]
		nextPos = f.Offset(prevExpr.expr.End())
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

// AddToStrings adds the given list of strings
// to the string slice field of name fieldName in the given file
// on this StructExpr.
// Any elements that are already there will not be repeated.
func (x *StructExpr) AddToStrings(
	f *TestFile, fieldName string, input []string, format Format) (bool, error) {
	toAdds := []string{}
	currentValues := []string{}
	if fieldExpr := x.FindFieldExpr(fieldName); fieldExpr != nil {
		var err error
		currentValues, err = fieldExpr.Strings()
		if err != nil {
			return false, err
		}
	}
	for _, toAdd := range input {
		found := false
		for _, elt := range currentValues {
			if toAdd == elt {
				found = true
				break
			}
		}
		if !found {
			toAdds = append(toAdds, toAdd)
		}
	}
	if len(toAdds) == 0 {
		return false, nil
	}
	newValues := append(currentValues, toAdds...)
	valueStr := FormatStrings(format, newValues)
	return x.SetField(f, fieldName, valueStr)
}

// RemoveFromStrings removes the given list of strings
// to the string slice field of name fieldName in the given file
// on this StructExpr.
// If no element is present, no action is taken.
// If removing all the elements leaves the original slice empty,
// the field is removed instead.
func (x *StructExpr) RemoveFromStrings(
	f *TestFile, fieldName string, input []string, format Format) (bool, error) {
	newValues := []string{}
	fieldExpr := x.FindFieldExpr(fieldName)
	if fieldExpr == nil {
		return false, nil
	}
	currentValues, err := fieldExpr.Strings()
	if err != nil {
		return false, err
	}
	for _, elt := range currentValues {
		found := false
		for _, toRemove := range input {
			if elt == toRemove {
				found = true
				break
			}
		}
		if !found {
			newValues = append(newValues, elt)
		}
	}
	if len(newValues) == len(currentValues) {
		return false, nil
	}
	if len(newValues) == 0 {
		return x.RemoveField(f, fieldName)
	}

	valueStr := FormatStrings(format, newValues)
	return x.SetField(f, fieldName, valueStr)
}
