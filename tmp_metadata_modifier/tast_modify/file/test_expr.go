// Copyright 2023 The ChromiumOS Authors
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

package file

import (
	"go/ast"
)

// TestExpr represents the testing.Test{...} ast declaration.
type TestExpr struct {
	*ast.CompositeLit
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
				//return x.(*TestExpr), true
				return &TestExpr{x}, true
			}
		}
	}
	return nil, false
}
