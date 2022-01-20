# Copyright 2016 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# TEST IS DISABLED UNTIL MIGRATED TO PYTHON 3.
# For instructions on how to: go/tauto-py3-migration
# To re-enable migrate to Python 3.
# If the test is not migrated by 1/14/22 it will be deleted.

AUTHOR = 'The Chromium OS Authors,chromeos-audio@google.com'
NAME = 'audio_AlsaAPI.move'
ATTRIBUTES = ""
PURPOSE = 'Test that simple ALSA API succeeds to move appl_ptr.'
CRITERIA = """
Check that the ALSA API succeeds.
"""
TIME='SHORT'
TEST_CATEGORY = 'Functional'
TEST_CLASS = "audio"
TEST_TYPE = 'client'

DOC = """
Check ALSA API succeeds to move appl_ptr.
"""

job.run_test('audio_AlsaAPI', to_test='move', tag='move')