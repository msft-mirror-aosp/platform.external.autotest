// Copyright 2023 The ChromiumOS Authors
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

package file

// ParamExpr represents a single {...} ast declaration on the
// Params field of testing.Test{...}.
type ParamTestExpr struct {
	*StructExpr
}

// Name returns the string value of the "Name" field for this parameterized test
// or "" if there is none.
func (p *ParamTestExpr) Name() string {
	nameField := p.FindFieldExpr("Name")
	if nameField == nil {
		return ""
	}
	v, err := nameField.StringValue()
	if err != nil {
		return ""
	}
	return v
}
