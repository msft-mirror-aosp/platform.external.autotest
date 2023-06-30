# Copyright 2023 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import logging
import re
import os

from .common import *


def combine_modules_by_common_word(modules):
    d = dict()
    # On first pass group modules with common first word together.
    for module in modules:
        pattern = _get_word_pattern(module)
        if pattern not in d:
            d[pattern] = []
        d[pattern].append(module)
    # Second pass extend names to maximum common prefix. This keeps control file
    # names identical if they contain only one module and less ambiguous if they
    # contain multiple modules.
    combined = dict()
    for key in sorted(d):
        # Instead if a one syllable prefix use longest common prefix of modules.
        prefix = os.path.commonprefix(d[key])
        # Beautification: strip Tests/TestCases from end of prefix, but only if
        # there is more than one module in the control file. This avoids
        # slightly strange combination of having CtsDpiTestCases1/2 inside of
        # CtsDpiTestCases (now just CtsDpi to make it clearer there are several
        # modules in this control file).
        if len(d[key]) > 1:
            prefix = re.sub('TestCases$', '', prefix)
            prefix = re.sub('Tests$', '', prefix)
        # Beautification: CtsMedia files run very long and are unstable. Give
        # each module its own control file, even though this heuristic would
        # lump them together.
        if prefix.startswith('CtsMedia') or prefix.startswith('CtsCamera'):
            # Separate each CtsMedia* modules, but group extra modules with
            # optional parametrization (ex: secondary_user, instant) together.
            prev = ' '
            for media in sorted(d[key]):
                if media.startswith(prev):
                    combined[prev].add(media)
                else:
                    prev = media
                    combined[media] = set([media])

        else:
            combined[prefix] = set(d[key])

    groups = [
            ModuleGroup(modules=frozenset(modules),
                        basename=prefix,
                        suites=frozenset())
            for prefix, modules in sorted(combined.items())
    ]
    logging.info('Combined %s modules into %s groups', len(modules),
                 len(groups))
    return groups


def _get_word_pattern(m, l=1):
    """Return the first few words of the CamelCase module name.

    Break after l+1 CamelCase word.
    Example: CtsDebugTestCases -> CtsDebug.
    """
    s = re.findall('^[a-z-_]+|[A-Z]*[^A-Z0-9]*', m)[0:l + 1]
    # Ignore Test or TestCases at the end as they don't add anything.
    if len(s) > l:
        if s[l].startswith('Test') or s[l].startswith('['):
            return ''.join(s[0:l])
        if s[l - 1] == 'Test' and s[l].startswith('Cases'):
            return ''.join(s[0:l - 1])
    return ''.join(s[0:l + 1])
