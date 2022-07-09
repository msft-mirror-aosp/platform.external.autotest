# Lint as: python2, python3
# Copyright (c) 2022 The Chromium OS Authors.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import logging

class HackRFRunnerContextManager(object):
    """Guarantees that the broadcasting of RF data is stopped when the context
    is exited.
    """

    def __init__(self, hackrf_runner_proxy):
        """Construct an HackRFRunnerContextManager. This class handles stopping
        the broadcast of noise.

        @param hackrf_runner_proxy: RPiHackRFRunner object.
        """
        self._hackrf_runner_proxy = hackrf_runner_proxy

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        logging.info('Cleaning up hackrf_transfer operations.')
        self._hackrf_runner_proxy.stop_broadcasting_file()
