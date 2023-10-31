// Copyright 2023 The ChromiumOS Authors
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

package file

import (
	"fmt"

	"go/ast"
)

// TestExpr represents the testing.Test{...} ast declaration.
type TestExpr struct {
	*StructExpr
}

// FindTestExpr finds the testing.Test declaration in the given
// parsed ast.File, or returns nil if none is found.
// Expects that code is of the form:
//
//	init() {
//		testing.AddTest(&testing.Test{
//			...
//		}
//	}
//
// Note that newlines/spaces/comments will not impact the output.
func FindTestExpr(parsedFile *ast.File) (*TestExpr, bool) {
	if parsedFile == nil {
		return nil, false
	}
	// Step through the top level declarations in the file and find "init".
	for _, decl := range parsedFile.Decls {
		// Find the init() function.
		init, ok := decl.(*ast.FuncDecl)
		if !ok || init == nil || init.Name.Name != "init" {
			continue
		}

		// In "init", find "testing.AddTest".
		for _, bodyElt := range init.Body.List {
			initStmt, ok := bodyElt.(*ast.ExprStmt)
			if !ok || initStmt == nil {
				continue
			}
			addTestExpr, ok := initStmt.X.(*ast.CallExpr)
			if !ok {
				continue
			}
			sel, ok := addTestExpr.Fun.(*ast.SelectorExpr)
			if !ok || sel == nil || sel.Sel == nil || sel.Sel.Name != "AddTest" {
				continue
			}

			// In testing.AddTest find the unary "&"
			for _, args := range addTestExpr.Args {
				unary, ok := args.(*ast.UnaryExpr)
				if !ok {
					continue
				}
				x, ok := unary.X.(*ast.CompositeLit)
				if !ok {
					continue
				}
				// Found testing.Test{...}.
				return &TestExpr{&StructExpr{x}}, true
			}
		}
	}
	return nil, false
}

// FindParamTestExprs returns a list of ast expressions for
// all of the parameterized tests in the given parent test,
// or nil if there are none.
func (x *TestExpr) FindParamTestExprs(namePrefix string) (map[string]*ParamTestExpr, error) {
	paramField := x.FindFieldExpr("Params")
	if paramField == nil {
		return nil, nil
	}
	paramValue, ok := paramField.expr.Value.(*ast.CompositeLit)
	if !ok {
		return nil, fmt.Errorf("Param field was not a CompositeLit in %s", namePrefix)
	}

	output := make(map[string]*ParamTestExpr)
	for _, elt := range paramValue.Elts {
		test, ok := elt.(*ast.CompositeLit)
		if !ok {
			return nil, fmt.Errorf("Param element was not a CompositeLit in %s", namePrefix)
		}
		p := &ParamTestExpr{&StructExpr{test}}
		name := p.Name()
		if name == "" {
			output[namePrefix] = p
		} else {
			output[namePrefix+"."+name] = p
		}
	}
	if len(output) == 0 {
		return nil, nil
	}
	return output, nil
}

// Name returns the name used by this test expression.
// This does NOT include the package name.
func (x *TestExpr) Name() string {
	funcField := x.FindFieldExpr("Func")
	if funcField == nil {
		return ""
	}
	funcValue, ok := funcField.expr.Value.(*ast.Ident)
	if funcValue == nil || !ok {
		return ""
	}
	return funcValue.Name
}
