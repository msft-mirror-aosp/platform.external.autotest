# Copyright 2022 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import base64
import unittest

from autotest_lib.server.cros import chrome_sideloader


class TestGetTastExpr(unittest.TestCase):
    """Test GetTastExpr in ChromeSideloader library."""

    def testTastExpr(self):
        tast_expr = "lacros.Basic"
        args_dict = {'tast_expr': tast_expr}
        self.assertEqual(chrome_sideloader.get_tast_expr(args_dict), tast_expr)

    def testEmptyArgsDict(self):
        args_dict = {}
        with self.assertRaises(Exception):
            chrome_sideloader.get_tast_expr(args_dict)

    def testTastExprB64(self):
        tast_expr = '''("group:mainline" && !informational)'''
        tast_expr_b64 = _base64_encode_str(tast_expr)
        args_dict = {'tast_expr_b64': tast_expr_b64}
        self.assertEqual(chrome_sideloader.get_tast_expr(args_dict), tast_expr)

    def testTastExprB64Corrupted(self):
        tast_expr = '''("group:mainline" && !informational)'''
        tast_expr_b64 = _base64_encode_str(tast_expr)
        # remove last character to corrupt the encoding
        tast_expr_b64 = tast_expr_b64[:-1]
        args_dict = {'tast_expr_b64': tast_expr_b64}
        with self.assertRaises(Exception):
            chrome_sideloader.get_tast_expr(args_dict)


def _base64_encode_str(s):
    return base64.b64encode(s.encode('utf-8')).decode('ascii')


if __name__ == '__main__':
    unittest.main()
