# Copyright 2022 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import logging
from autotest_lib.client.bin import test
from autotest_lib.client.bin import utils
from autotest_lib.client.common_lib import error

class graphics_HardwareProbe(test.test):
    """Examine the GPU information returned from autotest is consistent with graphics/hardware_probe.
    """
    version = 1
    def run_once(self):
        gpu = utils.get_gpu_family().strip()
        probe_gpu = utils.run("/usr/local/graphics/hardware_probe").stdout.strip()
        if gpu != probe_gpu:
            raise error.TestFail('Failed: autotest %s != hardware_probe %s' % (gpu, probe_gpu))
        logging.info('Got gpu: %s', gpu)
