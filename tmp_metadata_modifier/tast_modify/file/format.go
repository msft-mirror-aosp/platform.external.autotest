// Copyright 2023 The ChromiumOS Authors
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

package file

import (
	"fmt"
	"strings"
)

type Format int

const (
	FormatOneLine Format = iota
	FormatManyLines
)

func FormatStrings(format Format, input []string) string {
	switch format {
	case FormatOneLine:
		return fmt.Sprintf("[]string{\"%s\"}", strings.Join(input, "\", \""))
	case FormatManyLines:
		return fmt.Sprintf("[]string{\n\"%s\",\n}", strings.Join(input, "\",\n\""))
	}
	panic(fmt.Sprintf("Invalid string format %d", format))
}
