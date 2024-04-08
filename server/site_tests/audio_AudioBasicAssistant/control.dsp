# Copyright 2019 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from autotest_lib.client.common_lib import utils

NAME = "audio_AudioBasicAssistant.dsp"
METADATA = {
    "contacts": ["chromeos-audio-bugs@google.com"],
    "bug_component": "b:875558",
    "criteria": "This test will fail if the assistant can't open a tab requested by voice command.",
    "doc" : """
            A basic assistant voice command test. We need a DUT with hotwording
            function, chameleon with speaker and audio box to run the test.
            """
}
TEST_TYPE = "server"
#ATTRIBUTES = "suite:audio_advanced"
DEPENDENCIES = "audio_box, chameleon_state:WORKING"

args_dict = utils.args_to_dict(args)
chameleon_args = hosts.CrosHost.get_chameleon_arguments(args_dict)

def run(machine):
    job.run_test('audio_AudioBasicAssistant',
            host=hosts.create_host(machine, chameleon_args=chameleon_args),
            enable_dsp_hotword=True)

parallel_simple(run, machines)
