#!/usr/bin/python3
# Copyright 2019 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import json
import unittest
from unittest import mock

import common
from autotest_lib.client.common_lib import error
from autotest_lib.server.cros import telemetry_deploy
from autotest_lib.server.cros import telemetry_runner
from autotest_lib.server.cros import telemetry_setup

histograms_sample = [
    {
        'values': [
            'story1'
        ],
        'guid': '00000001-...',
        'type': 'GenericSet'
    },
    {
        'values': [
            'story2'
        ],
        'guid': '00000002-...',
        'type': 'GenericSet'
    },
    {
        'values': [
            'benchmark1'
        ],
        'guid': 'a0000001-...',
        'type': 'GenericSet'
    },
    {
        'values': [
            'benchmark_desc1'
        ],
        'guid': 'b0000001-...',
        'type': 'GenericSet'
    },
    {
        'sampleValues': [1.0, 2.0],
        'name': 'metric1',
        'diagnostics': {
            'stories': '00000001-...',
            'benchmarks': 'a0000001-...',
            'benchmarkDescriptions': 'b0000001-...'
        },
        'unit': 'ms_smallerIsBetter'
    },
    {
        'sampleValues': [1.0, 2.0],
        'name': 'metric1',
        'diagnostics': {
            'stories': '00000002-...',
            'benchmarks': 'a0000001-...',
            'benchmarkDescriptions': 'b0000001-...'
        },
        'unit': 'ms_smallerIsBetter'
    }
]

chartjson_sample = {
    'format_version': 1.0,
    'benchmark_name': 'benchmark1',
    'benchmark_description': 'benchmark_desc1',
    'benchmark_metadata': {
        'type': 'telemetry_benchmark',
        'name': 'benchmark1',
        'description': 'benchmark_desc1'
    },
    'charts': {
        'metric1': {
            'story1': {
                'std': 0.5,
                'name': 'metric1',
                'type': 'list_of_scalar_values',
                'values': [1.0, 2.0],
                'units': 'ms',
                'improvement_direction': 'down'
            },
            'story2': {
                'std': 0.5,
                'name': 'metric1',
                'type': 'list_of_scalar_values',
                'values': [1.0, 2.0],
                'units': 'ms',
                'improvement_direction': 'down'
            },
            'summary': {
                'std': 0.5,
                'name': 'metric1',
                'type': 'list_of_scalar_values',
                'values': [1.0, 1.0, 2.0, 2.0],
                'units': 'ms',
                'improvement_direction': 'down'
            }
        },
    }
}

class TelemetryRunnerTestCase(unittest.TestCase):
    """Test telemetry runner module."""

    def test_convert_chart_json(self):
        # Deep comparison of 2 objects with json dumps.
        converted = telemetry_runner.TelemetryRunner.convert_chart_json(
            histograms_sample)
        chartjson_dumps = json.dumps(chartjson_sample, sort_keys=True)
        chartjson_dumps2 = json.dumps(converted, sort_keys=True)
        self.assertEqual(chartjson_dumps, chartjson_dumps2)


class TelemetryDeployWiringTestCase(unittest.TestCase):
    """Tests that on-DUT telemetry runs deploy Telemetry when it is missing."""

    def _make_runner(self, telemetry_on_dut):
        """Builds a runner with _setup_telemetry stubbed out."""
        with mock.patch.object(telemetry_runner.LocalTelemetryRunner,
                               '_setup_telemetry'):
            runner = telemetry_runner.LocalTelemetryRunner(
                    mock.Mock(), telemetry_on_dut=telemetry_on_dut)
        runner._telemetry_path = '/drone/telemetry'
        return runner

    @mock.patch.object(telemetry_runner.telemetry_deploy,
                       'ensure_telemetry_on_dut')
    def test_deploys_for_on_dut_run(self, ensure):
        ensure.return_value = True
        runner = self._make_runner(telemetry_on_dut=True)
        runner._ensure_telemetry_on_dut()
        ensure.assert_called_once_with(runner._host)
        self.assertTrue(runner._deployed_telemetry)

    @mock.patch.object(telemetry_runner.telemetry_deploy,
                       'ensure_telemetry_on_dut')
    def test_skips_for_remote_run(self, ensure):
        """telemetry_on_dut=False runs the harness on the drone."""
        runner = self._make_runner(telemetry_on_dut=False)
        runner._ensure_telemetry_on_dut()
        ensure.assert_not_called()

    @mock.patch.object(telemetry_runner.telemetry_deploy,
                       'ensure_telemetry_on_dut')
    def test_ignore_flag_overrides_remote_run(self, ensure):
        """GPU integration tests run on the DUT regardless of the setting."""
        ensure.return_value = True
        runner = self._make_runner(telemetry_on_dut=False)
        runner._ensure_telemetry_on_dut(ignore_telemetry_on_dut=True)
        ensure.assert_called_once_with(runner._host)

    @mock.patch.object(telemetry_runner.telemetry_deploy,
                       'ensure_telemetry_on_dut')
    def test_image_supplied_telemetry_is_not_owned(self, ensure):
        """A no-op deploy must not make us responsible for cleanup."""
        ensure.return_value = False
        runner = self._make_runner(telemetry_on_dut=True)
        runner._ensure_telemetry_on_dut()
        self.assertFalse(runner._deployed_telemetry)

    @mock.patch.object(telemetry_runner.telemetry_deploy,
                       'cleanup_telemetry_on_dut')
    def test_cleanup_only_removes_what_we_deployed(self, cleanup):
        runner = self._make_runner(telemetry_on_dut=True)

        runner._deployed_telemetry = False
        runner._cleanup_telemetry_on_dut()
        cleanup.assert_not_called()

        runner._deployed_telemetry = True
        runner._cleanup_telemetry_on_dut()
        cleanup.assert_called_once_with(runner._host)
        self.assertFalse(runner._deployed_telemetry)

    @mock.patch.object(telemetry_runner.telemetry_deploy,
                       'ensure_telemetry_on_dut')
    @mock.patch.object(telemetry_runner.telemetry_deploy,
                       'cleanup_telemetry_on_dut')
    def test_context_exit_cleans_up(self, cleanup, ensure):
        ensure.return_value = True
        runner = self._make_runner(telemetry_on_dut=True)
        with runner:
            runner._ensure_telemetry_on_dut()
        cleanup.assert_called_once_with(runner._host)

    @mock.patch.object(telemetry_runner.TelemetryRunner, '_run_telemetry')
    @mock.patch.object(telemetry_runner.TelemetryRunner, '_ensure_deps')
    @mock.patch.object(telemetry_runner.TelemetryRunner,
                       '_ensure_telemetry_on_dut')
    def test_deploy_precedes_dep_fetch(self, ensure, ensure_deps, run):
        """_ensure_deps rsyncs into the tree, so it must exist first."""
        order = []
        ensure.side_effect = lambda *a, **k: order.append('deploy')
        ensure_deps.side_effect = lambda *a, **k: order.append('deps')
        run.return_value = telemetry_runner.TelemetryResult()

        runner = self._make_runner(telemetry_on_dut=True)
        runner.run_telemetry_benchmark('octane')

        self.assertEqual(order, ['deploy', 'deps'])

    @mock.patch.object(telemetry_runner.telemetry_deploy,
                       'ensure_telemetry_on_dut')
    def test_deploy_failure_is_reported_as_infra(self, ensure):
        """A deploy failure must not surface as a bare, unattributed error."""
        ensure.side_effect = telemetry_deploy.TelemetryDeployError(
                'no space left')

        runner = self._make_runner(telemetry_on_dut=True)
        with self.assertRaises(error.AutotestError) as caught:
            runner._ensure_telemetry_on_dut()

        self.assertIn('no space left', str(caught.exception))
        self.assertFalse(runner._deployed_telemetry)


class DroneTelemetryDeployKwargsTestCase(unittest.TestCase):
    """Tests that the DUT-side tree is pinned to the drone-side one."""

    def _make_runner(self, override_setup_gs_bucket=None):
        """Builds a drone runner with _setup_telemetry stubbed out."""
        with mock.patch.object(telemetry_runner.DroneTelemetryRunner,
                               '_setup_telemetry'):
            return telemetry_runner.DroneTelemetryRunner(
                    mock.Mock(),
                    override_setup_gs_bucket=override_setup_gs_bucket)

    def test_defaults_before_setup(self):
        """Nothing is pinned until _setup_telemetry has resolved the build."""
        runner = self._make_runner()
        self.assertEqual(runner._deploy_kwargs(), {
                'build': None,
                'bucket': None,
        })

    def test_pins_build_and_bucket(self):
        # A bare bucket name, matching telemetry_setup.STAGING_DEPS_BUCKET and
        # what telemetry_AFDOGenerate passes. STATIC_URL_TEMPLATE interpolates
        # this into a path, so a gs:// prefix would produce a broken URL.
        runner = self._make_runner(
                override_setup_gs_bucket=telemetry_setup.STAGING_DEPS_BUCKET)
        runner._build = 'octopus-release/R156-16825.0.0'
        self.assertEqual(
                runner._deploy_kwargs(), {
                        'build': 'octopus-release/R156-16825.0.0',
                        'bucket': 'staging-chromeos-image-archive',
                })

    @mock.patch.object(telemetry_runner.telemetry_deploy,
                       'ensure_telemetry_on_dut')
    def test_pinning_reaches_the_deploy(self, ensure):
        """The hook is worthless if the values never get passed down."""
        ensure.return_value = True
        runner = self._make_runner(
                override_setup_gs_bucket=telemetry_setup.STAGING_DEPS_BUCKET)
        runner._telemetry_on_dut = True
        runner._build = 'octopus-release/R156-16825.0.0'

        runner._ensure_telemetry_on_dut()

        ensure.assert_called_once_with(runner._host,
                                       build='octopus-release/R156-16825.0.0',
                                       bucket='staging-chromeos-image-archive')

    @mock.patch.object(telemetry_runner.telemetry_deploy,
                       'cleanup_telemetry_on_dut')
    def test_exit_cleans_up_dut_even_if_drone_cleanup_raises(self, cleanup):
        """Drone-side cleanup must not be able to strand the DUT-side tree."""
        runner = self._make_runner()
        runner._deployed_telemetry = True
        runner._telemetry_setup = mock.Mock()
        runner._telemetry_setup.Cleanup.side_effect = RuntimeError(
                'drone boom')

        with self.assertRaises(RuntimeError):
            with runner:
                pass

        cleanup.assert_called_once_with(runner._host)


if __name__ == '__main__':
    unittest.main()
