# Copyright 2022 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
import logging
import re

from autotest_lib.client.common_lib import error


class ElogVerifier:
    """
    Class that handles event log searching.
    """
    _DELIMITER = 'System boot'

    @classmethod
    def is_delimiter(cls, entry):
        """
        Check if the entry is a delimiter.
        """
        # [idx] | [timestamp] | [event type] | [data]
        return entry.split(' | ')[2] == cls._DELIMITER

    def __init__(self, system):
        """
        Split the event log by each boot.

        @param system: A SystemServicer object.

        @raise TestError: Failing to get event log.
        """
        entries = system.run_shell_command_get_output('elogtool list')

        if not entries:
            raise error.TestError('Failed to retrieve event log by elogtool')

        self._events = []
        for entry in entries:
            if self.is_delimiter(entry) or not self._events:
                self._events.append([])  # New boot
            self._events[-1].append(entry)

    def find_events(self, pattern, idx=1):
        """
        Search the pattern in the idx-th to last boot log.

        @param pattern: The regex to search.
        @param idx: The idx-th to last boot to be searched. For example, 1
                    means the current boot, and 2 means the previous boot.

        @return: The list of entries match the regex.
        """
        if len(self._events) < idx:
            raise error.TestError(
                    'Need at least %d system boot events,'
                    ' only have %d', idx, len(self._events))
        if not self.is_delimiter(self._events[-idx][0]):
            logging.warning('Event log is truncated')
        return list(filter(re.compile(pattern).search, self._events[-idx]))
