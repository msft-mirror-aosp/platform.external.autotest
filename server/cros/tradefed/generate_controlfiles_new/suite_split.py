# Copyright 2023 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import logging
from typing import Dict, Optional, Tuple

LONG_SUITE = -1


class Splitter:
    """Helper class that performs the suite split algorithm."""
    def __init__(self,
                 max_runtime: int,
                 per_test_overhead: int,
                 runtime_hints: Dict[str, int],
                 merge_tests: bool = False):
        """Initializes the Splitter.

        Args:
            max_runtime: Max total run time per group, in seconds.
            per_test_overhead: Overhead run time for each test, in seconds. See
                also merge_tests.
            runtime_hints: Mapping between test names and their expected
                runtime, usually based on historical test results.
            merge_tests: If the tests are to be merged into a single Tauto test
                instead of run as separate tests. If true, per_test_overhead is
                only counted once per shard (unless there are tests with
                different bitness and have to be run separately).
        """
        self._max_runtime = max_runtime
        self._per_test_overhead = per_test_overhead
        self._runtime_hints = runtime_hints
        self._merge_tests = merge_tests
        self._cur_shard = 1
        self._cur_total_runtime = 0
        self._long_total_runtime = 0
        self._last_abi_bits = None

    def get_shard(self, basename: str, abi_bits: Optional[int]) -> int:
        """Retrieves the shard the given test belongs to.

        Args:
            basename: Name of the test, same as those in runtime hints.
            abi_bits: Bitness of the test if specified.

        Returns:
            The shard number, or the constant LONG_SUITE denoting the test
            belongs to the long suite.
        """
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

        # Ignore overhead when applicable
        ignore_overhead = self._merge_tests and abi_bits == self._last_abi_bits
        if ignore_overhead:
            runtime -= self._per_test_overhead

        if self._cur_total_runtime + runtime > self._max_runtime:
            # Current shard is full; increment shard count
            self._cur_shard += 1
            if ignore_overhead:
                # |runtime| does not contain overhead. Initialize shard runtime
                # = per test overhead to make sure we count the overhead once
                self._cur_total_runtime = self._per_test_overhead
            else:
                self._cur_total_runtime = 0
        # Add test to current shard
        self._cur_total_runtime += runtime
        self._last_abi_bits = abi_bits
        return self._cur_shard

    def stats(self) -> Tuple[int, int]:
        """Returns stats for logging purposes.

        Returns:
            (total number of shards, total runtime of long suite)
        """
        return self._cur_shard, self._long_total_runtime
