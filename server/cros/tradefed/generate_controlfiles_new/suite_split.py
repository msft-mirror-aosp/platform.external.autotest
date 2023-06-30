# Copyright 2023 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import logging

LONG_SUITE = -1


class Splitter:
    def __init__(self, max_runtime, per_test_overhead, runtime_hints):
        self._max_runtime = max_runtime
        self._per_test_overhead = per_test_overhead
        self._runtime_hints = runtime_hints
        self._cur_shard = 1
        self._cur_total_runtime = 0
        self._long_total_runtime = 0

    def get_shard(self, basename, abi_bits):
        if abi_bits is not None:
            basename += f".{abi_bits}"
        if basename not in self._runtime_hints:
            logging.warn(
                    'Test %s not found in runtime hint, assuming long test',
                    basename)
            return LONG_SUITE

        runtime = self._runtime_hints[basename] + self._per_test_overhead
        if runtime > self._max_runtime:
            # Mark the test as a "long" test
            logging.info('Marking long test: %s (%.1fh)', basename,
                         runtime / 3600)
            self._long_total_runtime += runtime
            return LONG_SUITE

        if self._cur_total_runtime + runtime > self._max_runtime:
            # Current shard is full; increment shard count
            self._cur_shard += 1
            self._cur_total_runtime = 0
        # Add test to current shard
        self._cur_total_runtime += runtime
        return self._cur_shard

    def stats(self):
        return self._cur_shard, self._long_total_runtime
