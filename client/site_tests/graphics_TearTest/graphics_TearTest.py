# Copyright (c) 2010 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import logging, os

from autotest_lib.client.bin import site_login, site_ui_test
from autotest_lib.client.common_lib import error, site_ui, utils


def html_button(label, onclick=None):
  return ('''<input type="button" value="%s" onclick="do_submit('%s')"/>''' %
          (label, onclick if onclick else label))

TEMPLATE = '''
<h5>{0}</h5>
<table>
<tr> <td>{1[0][desc]}</td> <td>{1[0][result]}</td> </tr>
<tr> <td>{1[1][desc]}</td> <td>{1[1][result]}</td> </tr>
<tr> <td>{1[2][desc]}</td> <td>{1[2][result]}</td> </tr>
</table>
'''

class graphics_TearTest(site_ui_test.UITest):
    version = 1


    def setup(self):
        self.job.setup_dep(['glbench'])


    def run_once(self):
        dep = 'glbench'
        dep_dir = os.path.join(self.autodir, 'deps', dep)
        self.job.install_pkg(dep, 'dep', dep_dir)
  
        exefile = os.path.join(self.autodir, 'deps/glbench/teartest')
        
        while True:
            tests = [
                dict(cmd=exefile+' --tests uniform',
                     desc='Uniform updates', result=''),
                dict(cmd=exefile+' --tests teximage2d',
                     desc='glTexImage2D updates', result=''),
                dict(cmd=exefile+' --tests pixmap',
                     desc='Pixmap to texture', result=''),
            ]

            # First, present the starting screen with one Start button.
            header = ("These tests check vertical synchronization. You will " +
                    "see two vertical lines scrolling horizontally. The test " +
                    "passes if lines stay straight with no tearing.<br/>" +
                    html_button('Start'))
            dialog = site_ui.Dialog(question=TEMPLATE.format(header, tests),
                                    choices=[])
            result = dialog.get_result()

            header = html_button('Restart')

            # Run testcases from tests array.
            for test in tests:
                cmd = test['cmd']
                logging.info("command launched: %s" % cmd)
                utils.system(site_ui.xcommand(cmd))

                test['result'] = html_button('Pass') + html_button('Fail')
                dialog = site_ui.Dialog(question=TEMPLATE.format(header, tests),
                                        choices=[])
                # Store user's response if the testcase passed or failed.
                result = dialog.get_result()
                test['result'] = result if result else 'Timeout'

            # Test passed if all testcases passed.
            passed = all(test['result'] == 'Pass' for test in tests)
            header = ("Test %s.<br/>" % ("passed" if passed else "failed") +
                      html_button('Done') + html_button('Restart'))
            # Show the summary screen.
            dialog = site_ui.Dialog(question=TEMPLATE.format(header, tests),
                                    choices=[])
            result = dialog.get_result()

            # If user chose 'Restart', run the whole thing again.
            if result != 'Restart':
                break

        if not passed:
            raise error.TestFail('Failed: ' +
                ', '.join(test['desc'] for test in tests
                          if test['result'] != 'Pass'))
