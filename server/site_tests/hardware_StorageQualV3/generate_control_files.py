# Lint as: python3
# Copyright 2023 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from collections import namedtuple
import os

TEMPLATE_FILE = 'template.control.v3'

TestEntry = namedtuple('TestEntry',
                       ['name', 'test_expr', 'attributes', 'duration'])


def _write_control_file(name, contents):
    f = open(name, 'w')
    f.write(contents)
    f.close()


def _read_template_file(filename):
    f = open(filename)
    d = f.read()
    f.close()
    return d


v3_tests = [
        TestEntry(name='storage_testing_v3_basic_info',
                  test_expr=[
                          'storage.InternalDeviceTypeCheck',
                          'storage.HealthInfo', 'storage.FfuSupport'
                  ],
                  attributes=[
                          'pdp-enabled', 'pdp-kpi', 'pdp-stress', 'avl-v3',
                          'avl-v3-batch1'
                  ],
                  duration=1200),
        TestEntry(name='storage_testing_v3_device_config',
                  test_expr=[
                          'storage.EmmcConfiguration',
                          'storage.UfsConfiguration',
                          'storage.NvmeConfiguration'
                  ],
                  attributes=[
                          'pdp-enabled', 'pdp-kpi', 'pdp-stress', 'avl-v3',
                          'avl-v3-batch1'
                  ],
                  duration=1200),
        TestEntry(name='storage_testing_v3_erase_behaviour',
                  test_expr=[
                          'storage.Trim', 'storage.WriteZeroCorrectness',
                          'storage.WriteZeroPerf'
                  ],
                  attributes=[
                          'pdp-enabled', 'pdp-kpi', 'pdp-stress', 'avl-v3',
                          'avl-v3-batch1'
                  ],
                  duration=1200),
        TestEntry(name='storage_testing_v3_soc_perf',
                  test_expr=['storage.SocPerformance.*'],
                  attributes=['pdp-kpi', 'pdp-stress'],
                  duration=1200),
        TestEntry(name='storage_testing_v3_power_state',
                  test_expr=['storage.LowPowerStateResidence'],
                  attributes=[
                          'pdp-kpi', 'pdp-stress', 'avl-v3', 'avl-v3-batch1'
                  ],
                  duration=600),
        TestEntry(name='storage_testing_v3_part_perf',
                  test_expr=['storage.Performance.*'],
                  attributes=['avl-v3', 'avl-v3-batch1'],
                  duration=7800),
        TestEntry(name='storage_testing_v3_stress_write',
                  test_expr=['storage.StressWrite'],
                  attributes=['pdp-stress', 'avl-v3', 'avl-v3-batch1'],
                  duration=28800),
        TestEntry(name='storage_testing_v3_stress_write_2',
                  test_expr=[
                          'storage.StressWrite.iteration_2',
                  ],
                  attributes=['avl-v3', 'avl-v3-batch2'],
                  duration=28800),
        TestEntry(name='storage_testing_v3_stress_write_3',
                  test_expr=[
                          'storage.StressWrite.iteration_3'
                  ],
                  attributes=['avl-v3', 'avl-v3-batch2'],
                  duration=28800),
        TestEntry(name='storage_testing_v3_stress_suspend',
                  test_expr=['storage.SuspendStress'],
                  attributes=['pdp-stress', 'avl-v3', 'avl-v3-batch1'],
                  duration=28800),
        TestEntry(name='storage_testing_v3_stress_suspend_2',
                  test_expr=[
                          'storage.SuspendStress.iteration_2',
                  ],
                  attributes=['avl-v3', 'avl-v3-batch3'],
                  duration=28800),
        TestEntry(name='storage_testing_v3_stress_suspend_3',
                  test_expr=[
                          'storage.SuspendStress.iteration_3'
                  ],
                  attributes=['avl-v3', 'avl-v3-batch3'],
                  duration=28800),
        TestEntry(name='storage_testing_v3_stress',
                  test_expr=['storage.Stress'],
                  attributes=['pdp-stress', 'avl-v3', 'avl-v3-batch1'],
                  duration=28800),
        TestEntry(name='storage_testing_v3_stress_2',
                  test_expr=['storage.Stress.iteration2'],
                  attributes=['avl-v3', 'avl-v3-batch4'],
                  duration=28800),
]

template = _read_template_file(
        os.path.join(os.path.dirname(os.path.realpath(__file__)),
                     TEMPLATE_FILE))

priority = 200
for test in v3_tests:
    control_file = template.format(name=test.name,
                                   attributes=', '.join([
                                           'suite:storage-qual-' + attr
                                           for attr in test.attributes
                                   ]),
                                   priority=priority,
                                   test_exprs="', '".join(test.test_expr),
                                   duration=test.duration)
    control_file_name = 'control.' + test.name
    _write_control_file(control_file_name, control_file)
    priority -= 1
