// Copyright 2023 The ChromiumOS Authors
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

package file

import (
	"fmt"
	"strings"

	"go/ast"
)

// Field represents a given field ast declaration.
type FieldExpr struct {
	name      string
	isDefined bool
	expr      *ast.KeyValueExpr
	idx       int
}

// FindFieldExpr returns the FieldExpr for the given field name,
// or an error if a problem was found.
// e.g. x.FieldExpr("Contacts") will find the expression for
// the code declaring `Contacts: string[]{...}`
func (x *TestExpr) FindFieldExpr(keyName string) *FieldExpr {
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
				name:      keyName,
				expr:      pair,
				isDefined: true,
				idx:       i,
			}
		}
	}
	return &FieldExpr{
		name:      keyName,
		isDefined: false,
	}
}

// AllFieldExprs returns a list of the FieldExpr for this test expression,
// or an error if a problem was found.
// Fields are returned in the order in which they are listed in code.
func (x *TestExpr) AllFieldExprs() []*FieldExpr {
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
			name:      key.Name,
			expr:      pair,
			isDefined: true,
			idx:       i,
		})
	}
	return fields
}

// StringSliceValue returns the []string value of the field, or an error
// if any problem was found.
func (f *FieldExpr) StringSliceValue() ([]string, error) {
	if !f.isDefined || f.expr == nil {
		return nil, fmt.Errorf("%v is not defined!", f.name)
	}
	compLit, ok := f.expr.Value.(*ast.CompositeLit)
	if !ok || compLit == nil {
		return nil, fmt.Errorf("Could not force %v into slice!", f.expr.Value)
	}

	output := []string{}
	for _, eltUntyped := range compLit.Elts {
		elt, ok := eltUntyped.(*ast.BasicLit)
		if !ok {
			return nil, fmt.Errorf("Found bad string slice value: %v.", elt)
		}
		// Trim trailing/leading whitespace from each element.
		// Omit trailing/leading \" characters.
		output = append(output, strings.TrimSpace(elt.Value)[1:len(elt.Value)-1])
	}
	return output, nil
}

// BoolValue returns the bool value of the field, or an error
// if any problem was found.
// Note: Booleans are represented as ast.Ident values in the ast tree.
func (f *FieldExpr) BoolValue() (bool, error) {
	if !f.isDefined || f.expr == nil {
		return false, fmt.Errorf("%v is not defined!", f.name)
	}
	expr, ok := f.expr.Value.(*ast.Ident)
	if expr == nil || !ok {
		return false, fmt.Errorf("Could not force %v into boolean!", f.expr.Value)
	}
	if expr.Name == "true" {
		return true, nil
	} else if expr.Name == "false" {
		return false, nil
	}
	return false, fmt.Errorf("Expected true or false, not %v!", expr.Name)
}
