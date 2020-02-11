# Copyright (c) 2013 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from autotest_lib.client.bin import utils
from autotest_lib.client.common_lib import error
from autotest_lib.server import autotest
from autotest_lib.server import hosts
from autotest_lib.server import test


class hardware_StorageQualSuspendStress(test.test):
    """ Run Fio while suspending aggressively."""

    version = 1

    def run_once(self, client_ip, duration, other_dev=False):
        client = hosts.create_host(client_ip)
        client_at = autotest.Autotest(client)
        timeout = int(duration * 1.5)
        fio_test = "hardware_StorageFio"
        if other_dev:
            fio_test = "hardware_StorageFioOther"
        control = """job.parallel(
            [lambda: job.run_test('power_SuspendStress', tag='disk',
                duration=%d, init_delay=10, min_suspend=7, min_resume=30,
                check_connection=True)],
            [lambda: job.run_test('%s', test_length=%d,
                disable_sysinfo=True, requirements=[('write_stress', [])],
                tag='qual_suspend')], timeout=%d)""" % \
            (duration, fio_test, duration, timeout)
        client_at.run(control, '.', None)

