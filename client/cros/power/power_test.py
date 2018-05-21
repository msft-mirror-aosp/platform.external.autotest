# Copyright 2018 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
import logging
import time

from autotest_lib.client.bin import test
from autotest_lib.client.cros import service_stopper
from autotest_lib.client.cros.power import power_dashboard
from autotest_lib.client.cros.power import power_rapl
from autotest_lib.client.cros.power import power_status
from autotest_lib.client.cros.power import power_telemetry_utils
from autotest_lib.client.cros.power import power_utils


class power_Test(test.test):
    """Optional base class power related tests."""
    version = 1

    def initialize(self, seconds_period=20.):
        """Perform necessary initialization prior to power test run.

        @param seconds_period: float of probing interval in seconds.

        @var backlight: power_utils.Backlight object.
        @var keyvals: dictionary of result keyvals.
        @var status: power_status.SysStat object.

        @var _plog: power_status.PowerLogger object to monitor power.
        @var _psr: power_utils.DisplayPanelSelfRefresh object to monitor PSR.
        @var _services: service_stopper.ServiceStopper object.
        @var _start_time: float of time in seconds since Epoch test started.
        @var _stats = power_status.StatoMatic object.
        @var _tlog: power_status.TempLogger ojbect to monitor temperatures.
        """
        super(power_Test, self).initialize()
        self.backlight = power_utils.Backlight()
        self.backlight.set_default()
        self.keyvals = None
        self.status = power_status.get_status()

        measurements = []
        if not self.status.on_ac():
            measurements.append(
                power_status.SystemPower(self.status.battery_path))
        if power_utils.has_powercap_support():
            measurements += power_rapl.create_powercap()
        elif power_utils.has_rapl_support():
            measurements += power_rapl.create_rapl()
        self._plog = power_status.PowerLogger(measurements,
                                              seconds_period=seconds_period)
        self._psr = power_utils.DisplayPanelSelfRefresh()
        self._services = service_stopper.ServiceStopper(
                service_stopper.ServiceStopper.POWER_DRAW_SERVICES)
        self._services.stop_services()
        self._stats = power_status.StatoMatic()

        self._tlog = power_status.TempLogger([], seconds_period=seconds_period)

    def warmup(self, warmup_time=30):
        """Warm up.

        Wait between initialization and run_once for new settings to stabilize.

        @param warmup_time: integer of seconds to warmup.
        """
        time.sleep(warmup_time)

    def start_measurements(self):
        """Start measurements."""
        self._plog.start()
        self._tlog.start()
        self._start_time = time.time()
        power_telemetry_utils.start_measurement()

    def loop_sleep(self, loop, sleep_secs):
        """Jitter free sleep.

        @param loop: integer of loop (1st is zero).
        @param sleep_secs: integer of desired sleep seconds.
        """
        next_time = self._start_time + (loop + 1) * sleep_secs
        time.sleep(next_time - time.time())

    def checkpoint_measurements(self, name, start_time=None):
        """Checkpoint measurements.

        @param name: string name of measurement being checkpointed.
        @start_time: float of time in seconds since Epoch that
                measurements being checkpointed began.
        """
        if not start_time:
            start_time = self._start_time
        self.status.refresh()
        self._plog.checkpoint(name, start_time)
        self._tlog.checkpoint(name, start_time)
        self._psr.refresh()

    def publish_keyvals(self):
        """Publish power result keyvals."""
        keyvals = self._stats.publish()
        keyvals['level_backlight_max'] = self.backlight.get_max_level()
        keyvals['level_backlight_current'] = self.backlight.get_level()

        # record battery stats if not on AC
        if self.status.on_ac():
            keyvals['b_on_ac'] = 1
        else:
            keyvals['b_on_ac'] = 0

        if self.status.battery:
            keyvals['ah_charge_full'] = self.status.battery[0].charge_full
            keyvals['ah_charge_full_design'] = \
                                self.status.battery[0].charge_full_design
            keyvals['ah_charge_now'] = self.status.battery[0].charge_now
            keyvals['a_current_now'] = self.status.battery[0].current_now
            keyvals['wh_energy'] = self.status.battery[0].energy
            keyvals['w_energy_rate'] = self.status.battery[0].energy_rate
            keyvals['v_voltage_min_design'] = \
                                self.status.battery[0].voltage_min_design
            keyvals['v_voltage_now'] = self.status.battery[0].voltage_now

        keyvals.update(self._plog.calc())
        keyvals.update(self._tlog.calc())
        keyvals.update(self._psr.get_keyvals())
        self.write_perf_keyval(keyvals)
        self.keyvals = keyvals

    def _publish_dashboard(self):
        """Report results to chromeperf & power dashboard."""

        if not self.keyvals:
            self.publish_keyvals()

        # publish power values
        publish = {
            key: self.keyvals[key]
            for key in self.keyvals.keys()
            if key.endswith('pwr')
        }

        for key, values in publish.iteritems():
            self.output_perf_value(description=key, value=values, units='W',
                                   higher_is_better=False, graph='power')

        # publish temperature values
        publish = {
            key: self.keyvals[key]
            for key in self.keyvals.keys()
            if key.endswith('temp')
        }

        for key, values in publish.iteritems():
            self.output_perf_value(description=key, value=values, units='C',
                                   higher_is_better=False, graph='temperature')

        # publish to power dashboard
        pdash = power_dashboard.PowerLoggerDashboard(
            self._plog, self.tagged_testname, self.resultsdir)
        pdash.upload()

    def postprocess_iteration(self):
        power_telemetry_utils.end_measurement()
        super(power_Test, self).postprocess_iteration()
        self._publish_dashboard()

    def cleanup(self):
        """Reverse setting change in initialization."""
        if self.backlight:
            self.backlight.restore()
        self._services.restore_services()
        super(power_Test, self).cleanup()
