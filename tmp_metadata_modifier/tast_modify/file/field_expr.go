// Copyright 2023 The ChromiumOS Authors
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

package file

import (
	"fmt"
	"strconv"
	"strings"

	"go/ast"
	"go/token"
)

// Field represents a given field ast declaration.
type FieldExpr struct {
	name string
	expr *ast.KeyValueExpr
	idx  int
}

func (f *FieldExpr) Value() (any, error) {
	if compLit, ok := f.expr.Value.(*ast.CompositeLit); ok {
		output := []string{}
		for _, eltUntyped := range compLit.Elts {
			elt, ok := eltUntyped.(*ast.BasicLit)
			if !ok {
				return nil, fmt.Errorf("Found bad string slice value: %v.", elt)
			}
			// Trim trailing/leading whitespace from each element.
			// Omit trailing/leading " characters.
			output = append(output, strings.Trim(strings.TrimSpace(elt.Value), "\""))
		}
		return output, nil
	}
	if basicLit, ok := f.expr.Value.(*ast.BasicLit); ok {
		switch basicLit.Kind {
		case token.STRING:
			return strings.Trim(strings.TrimSpace(basicLit.Value), "\""), nil
		case token.INT:
			return strconv.Atoi(basicLit.Value)
		case token.FLOAT:
			return strconv.ParseFloat(basicLit.Value, 64)
		case token.IMAG:
			return strconv.ParseComplex(basicLit.Value, 64)
		case token.CHAR:
			return strings.Trim(strings.TrimSpace(basicLit.Value), "'"), nil
		}
	}
	if ident, ok := f.expr.Value.(*ast.Ident); ok {
		// Note: Booleans are represented as ast.Ident values in the ast tree.
		switch ident.Name {
		case "true":
			return true, nil
		case "false":
			return false, nil
		}
	}
	return "", fmt.Errorf("No known value type for field %s", f.name)

}

// StringValue returns the string value of the field, or an error
// if any problem was found.
func (f *FieldExpr) StringValue() (string, error) {
	v, err := f.Value()
	if err != nil {
		return "", err
	}
	if output, ok := v.(string); ok {
		return output, nil
	}
	return "", fmt.Errorf("Could not cast %v into string!", f.expr.Value)
}

// Strings returns the []string value of the field, or an error
// if any problem was found.
func (f *FieldExpr) Strings() ([]string, error) {
	v, err := f.Value()
	if err != nil {
		return nil, err
	}
	if output, ok := v.([]string); ok {
		return output, nil
	}
	return nil, fmt.Errorf("Could not cast %v into string slice!", f.expr.Value)
}

// Bool returns the bool value of the field, or an error
// if any problem was found.
func (f *FieldExpr) Bool() (bool, error) {
	v, err := f.Value()
	if err != nil {
		return false, err
	}
	if output, ok := v.(bool); ok {
		return output, nil
	}
	return false, fmt.Errorf("Could not cast %v into bool!", f.expr.Value)
}
