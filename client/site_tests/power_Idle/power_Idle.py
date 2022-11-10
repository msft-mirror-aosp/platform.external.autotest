# Lint as: python2, python3
# Copyright (c) 2012 The ChromiumOS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import logging
import time

from autotest_lib.client.bin import utils
from autotest_lib.client.common_lib import error
from autotest_lib.client.common_lib.cros import arc_common
from autotest_lib.client.cros.bluetooth import bluetooth_device_xmlrpc_server
from autotest_lib.client.cros.power import power_test
from autotest_lib.client.cros.power import power_utils
from autotest_lib.client.cros import tast
from autotest_lib.client.cros.tast.ui import chrome_service_pb2
from autotest_lib.client.cros.tast.ui import tconn_service_pb2
from autotest_lib.client.cros.tast.ui import tconn_service_pb2_grpc


class power_Idle(power_test.power_Test):
    """class for power_Idle test.

    Collects power stats when machine is idle

    Current tests,

      | test# | seconds | display   | bluetooth |
      -------------------------------------------
      | 1     | 120     | off       | off       |
      | 2     | 120     | default   | off       |
      | 3     | 120     | default   | on - idle |
      | 4     | 120     | off       | on - idle |

    """
    version = 1
    first_test_warmup_secs = 60
    first_test_arcvm_warmup_secs = 150

    def initialize(self, pdash_note='', seconds_period=10.,
                   force_discharge='optional', run_arc=True):
        super(power_Idle, self).initialize(seconds_period=seconds_period,
                                           pdash_note=pdash_note,
                                           force_discharge=force_discharge,
                                           run_arc=run_arc)

    def run_once(self, warmup_secs=20, idle_secs=120, default_only=False,
                 tast_bundle_path=None):
        """Collect power stats for idle tests."""

        def measure_it(warmup_secs, idle_secs, tagname):
            """Helper function to wrap testing loop for each sub test."""
            if self.is_first_test:
                warmup_secs += self.first_test_warmup_secs
                if (self._arc_mode != arc_common.ARC_MODE_DISABLED and
                    utils.is_arcvm()):
                    warmup_secs += self.first_test_arcvm_warmup_secs
                self.is_first_test = False
            if warmup_secs > 0:
                tstart = time.time()
                time.sleep(warmup_secs)
                self.checkpoint_measurements("warmup", tstart)
            tstart = time.time()
            time.sleep(idle_secs)
            self.checkpoint_measurements(tagname, tstart)

        bt_device = bluetooth_device_xmlrpc_server \
            .BluetoothDeviceXmlRpcDelegate()

        logging.info('Starting gRPC Tast')
        with tast.GRPC(tast_bundle_path) as tast_grpc,\
            tast.ChromeService(tast_grpc.channel) as chrome_service:
            tconn_service = tconn_service_pb2_grpc.TconnServiceStub(tast_grpc.channel)

            chrome_service.New(chrome_service_pb2.NewRequest(
                # b/228256145 to avoid powerd restart
                disable_features = ['FirmwareUpdaterApp'],
                # --disable-sync disables test account info sync, eg. Wi-Fi
                # credentials, so that each test run does not remember info from
                # last test run.
                extra_args = ['--disable-sync'],
                arc_mode = (chrome_service_pb2.ARC_MODE_ENABLED
                            if self._arc_mode == arc_common.ARC_MODE_ENABLED
                            else chrome_service_pb2.ARC_MODE_DISABLED),
            ))

            # Measure power in full-screen blank tab.
            # In order to hide address bar, we call chrome.windows API twice.
            # TODO(b/253003075): Get rid of explicit promise by switching Tast
            # test extension to MV3.
            tconn_service.Eval(tconn_service_pb2.EvalRequest(
                expr='''(async () => {
                    let window_id = await new Promise(
                        (resolve) => chrome.windows.create(
                            { url: ["about:blank"], focused: true },
                            (window) => resolve(window.id)));
                    await new Promise(
                        (resolve) => chrome.windows.update(
                            window_id, { state: 'fullscreen' },
                            resolve));
                })()'''
            ))

            # Stop services and disable multicast again as Chrome might have
            # restarted them.
            self._services.stop_services()
            self._multicast_disabler.disable_network_multicast()

            self.is_first_test = True

            if default_only:
                self.start_measurements()
                measure_it(warmup_secs, idle_secs, 'all-default')
                return

            # test1 : display off, BT off
            power_utils.set_display_power(power_utils.DISPLAY_POWER_ALL_OFF)
            if not bt_device.set_powered(False):
                raise error.TestFail('Cannot turn off bluetooth adapter.')
            self.start_measurements()
            measure_it(warmup_secs, idle_secs, 'display-off_bluetooth-off')

            # test2 : display default, BT off
            power_utils.set_display_power(power_utils.DISPLAY_POWER_ALL_ON)
            measure_it(warmup_secs, idle_secs,
                       'display-default_bluetooth-off')

            # test3 : display default, BT on
            if not bt_device.set_powered(True):
                logging.warning('Cannot turn on bluetooth adapter.')
                return
            measure_it(warmup_secs, idle_secs, 'display-default_bluetooth-on')

            # test4 : display off, BT on
            power_utils.set_display_power(power_utils.DISPLAY_POWER_ALL_OFF)
            measure_it(warmup_secs, idle_secs, 'display-off_bluetooth-on')

            # Re-enable multicast here instead of in the cleanup because Chrome
            # might re-enable it and we can't verify that multicast is off.
            self._multicast_disabler.enable_network_multicast()

    def cleanup(self):
        """Reset to previous state."""
        power_utils.set_display_power(power_utils.DISPLAY_POWER_ALL_ON)
        super(power_Idle, self).cleanup()
