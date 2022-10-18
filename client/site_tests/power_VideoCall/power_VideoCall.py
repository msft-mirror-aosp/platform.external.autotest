# Lint as: python2, python3
# Copyright 2019 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import logging
import re
import threading
import time

from google.protobuf import struct_pb2
from autotest_lib.client.bin import utils
from autotest_lib.client.cros.input_playback import keyboard
from autotest_lib.client.cros.power import power_status
from autotest_lib.client.cros.power import power_test
from autotest_lib.client.cros import tast
from autotest_lib.client.cros.tast.ui import chrome_service_pb2
from autotest_lib.client.cros.tast.ui import tconn_service_pb2
from autotest_lib.client.cros.tast.ui import tconn_service_pb2_grpc
from autotest_lib.client.cros.tast.ui import conn_service_pb2
from autotest_lib.client.cros.tast.ui import conn_tab


class power_VideoCall(power_test.power_Test):
    """class for power_VideoCall test."""
    version = 1

    video_url = 'https://storage.googleapis.com/chromiumos-test-assets-public/power_VideoCall/power_VideoCall.html'
    webrtc_video_url = 'https://storage.googleapis.com/chromiumos-test-assets-public/power_VideoCall/power_VideoCall.webrtc.html'
    doc_url = 'http://crospower.page.link/power_VideoCall_doc'

    def initialize(self,
                   seconds_period=20.,
                   pdash_note='',
                   force_discharge=False,
                   check_network=False,
                   disable_hdrnet=False):
        """initialize method."""
        super(power_VideoCall,
              self).initialize(seconds_period=seconds_period,
                               pdash_note=pdash_note,
                               force_discharge=force_discharge,
                               check_network=check_network,
                               disable_hdrnet=disable_hdrnet)


    def run_once(self,
                 duration=7200,
                 preset='',
                 video_url='',
                 num_video=5,
                 multitask=True,
                 min_run_time_percent=100,
                 webrtc=False,
                 tast_bundle_path=None):
        """run_once method.

        @param duration: time in seconds to display url and measure power.
        @param preset: preset of the camera record. Possible values are
                       'ultra' :  1080p30_vp9,
                       'high' :   720p30_vp9,
                       'medium' : 720p24_vp8,
                       'low' :    360p24_vp8
                       If not supplied, preset will be determined automatically.
        @param video_url: url of video call simulator.
        @param num_video: number of video including camera preview.
        @param multitask: boolean indicate Google Docs multitask enablement.
        @param min_run_time_percent: int between 0 and 100;
                                     run time must be longer than
                                     min_run_time_percent / 100.0 * duration.
        @param webrtc: If true use WebRTC, otherwise use MediaEncoder.
        @param tast_bundle_apth: Path to the tast local bundle to be used with the test.
        """

        if not preset and not video_url:
            preset = self._get_camera_preset()
        if not video_url:
            if webrtc:
                video_url = self.webrtc_video_url
            else:
                video_url = self.video_url

        # Append preset to self.video_url for camera preset.
        if preset:
            video_url = '%s?preset=%s' % (video_url, preset)

        logging.info('Starting gRPC Tast')
        with keyboard.Keyboard() as keys,\
            tast.GRPC(tast_bundle_path) as tast_grpc,\
            tast.ConnService(tast_grpc.channel) as conn_service,\
            tast.ChromeService(tast_grpc.channel) as chrome_service:
            tconn_service = tconn_service_pb2_grpc.TconnServiceStub(tast_grpc.channel)

            chrome_service.New(chrome_service_pb2.NewRequest(
                # b/228256145 to avoid powerd restart
                disable_features = ['FirmwareUpdaterApp'],
                extra_args = self.get_extra_browser_args_for_camera_test(),
            ))

            # Stop services and disable multicast again as Chrome might have
            # restarted them.
            self._services.stop_services()
            self._multicast_disabler.disable_network_multicast()

            response = conn_service.NewConn(conn_service_pb2.NewConnRequest(
                url = 'about:blank'
            ))

            tab_left = conn_tab.ConnTab(conn_service, response.id)

            # Move existing window to left half and open video page
            tab_left.ActivateTarget()
            tab_left.WaitForDocumentReadyStateToBeComplete()
            if multitask:
                keys.press_key('alt+[')
            else:
                # Run in fullscreen when not multitask.
                tconn_service.Eval(tconn_service_pb2.EvalRequest(
                    expr='''(async () => {
                        let window_id = await new Promise(
                            (resolve) => chrome.windows.getCurrent({},
                            (window) => resolve(window.id))
                        )
                        await new Promise(
                            (resolve) => chrome.windows.update(
                                window_id, { state: 'fullscreen' },
                                resolve));
                    })()'''))

            logging.info('Navigating left window to %s', video_url)
            tab_left.Navigate(video_url)
            tab_left.WaitForDocumentReadyStateToBeComplete()
            video_init_time = power_status.VideoFpsLogger.time_until_ready(
                    tab_left, num_video=num_video)
            self.keyvals['video_init_time'] = video_init_time

            tab_right = None
            if multitask:
                # Open Google Doc on right half
                logging.info('Navigating right window to %s', self.doc_url)
                arg_value = struct_pb2.Value()
                arg_value.string_value = self.doc_url
                tconn_service.Call(tconn_service_pb2.CallRequest(
                    fn='''async (url) => {
                        await new Promise(
                            (resolve) => chrome.windows.create(
                                { url: url, focused: true },
                                () => resolve()));
                        }''',
                    args=[arg_value]
                    ))
                response = conn_service.NewConnForTarget(conn_service_pb2.NewConnForTargetRequest(
                    url = self.doc_url
                ))
                tab_right = conn_tab.ConnTab(conn_service, response.id)
                tab_right.ActivateTarget()
                keys.press_key('alt+]')
                tab_right.WaitForDocumentReadyStateToBeComplete()
                time.sleep(5)

            # We need to prevent the threads from issuing concurrent
            # EvaluateJavaScript calls to the browser, otherwise the telemetry
            # connection gets corrupt.
            lock = threading.Lock()

            self._vlog = power_status.VideoFpsLogger(tab_left,
                lock=lock,
                seconds_period=self._seconds_period,
                checkpoint_logger=self._checkpoint_logger)
            self._meas_logs.append(self._vlog)

            if webrtc:
                self._webrtc_logger = power_status.WebRTCMetricLogger(
                        tab_left,
                        lock=lock,
                        checkpoint_logger=self._checkpoint_logger)
                self._meas_logs.append(self._webrtc_logger)
                # Sleep for a few seconds to allow the WebRTC bandwidth to
                # stabilize.
                time.sleep(5)

            # Start typing number block
            self.start_measurements()
            # TODO(b/226960942): Revert crrev.com/c/3556798 once root cause is
            # found for why test fails before 2 hrs.
            min_run_time = min_run_time_percent / 100.0 * duration
            type_count = 0
            while time.time() - self._start_time < duration:
                if multitask:
                    keys.press_key('number_block')
                    type_count += 1
                    if type_count == 10:
                        keys.press_key('ctrl+a_backspace')
                        type_count = 0
                else:
                    time.sleep(60)

                if not tab_left.IsAlive():
                    msg = 'Video tab crashed'
                    logging.error(msg)
                    if time.time() - self._start_time < min_run_time:
                        self._failure_messages.append(msg)
                    break

                if tab_right and not tab_right.IsAlive():
                    msg = 'Doc tab crashed'
                    logging.error(msg)
                    if time.time() - self._start_time < min_run_time:
                        self._failure_messages.append(msg)
                    break

                self.status.refresh()
                if self.status.is_low_battery():
                    logging.info(
                        'Low battery, stop test early after %.0f minutes',
                        (time.time() - self._start_time) / 60)
                    break

            # Manually stop the logger so we don't keep trying to refresh stats
            # after chrome has been closed.
            self._vlog.done = True
            self._vlog.join()

            if webrtc:
                self._webrtc_logger.done = True
                self._webrtc_logger.join()

                tab_left.EvaluateJavaScript('window.stopWebRTC()')

            if multitask:
                self.collect_keypress_latency(conn_tab.new_tab(conn_service, 'about:blank'))

            # Re-enable multicast here instead of in the cleanup because Chrome
            # might re-enable it and we can't verify that multicast is off.
            self._multicast_disabler.enable_network_multicast()

    def _get_camera_preset(self):
        """Return camera preset appropriate to hw spec.

        Preset will be determined using this logic.
        - Newer Intel Core U/P-series CPU with fan -> 'high'
        - AMD Ryzen CPU with fan -> 'high'
        - Above without fan -> 'medium'
        - High performance ARM -> 'medium'
        - Other Intel Core CPU -> 'medium'
        - AMD APU -> 'low'
        - Intel N-series CPU -> 'low'
        - Older ARM CPU -> 'low'
        - Other CPU -> 'low'
        """
        HIGH_IF_HAS_FAN_REGEX = r'''
            Intel[ ]Core[ ]i[357]-[6-9][0-9]{3}U|     # Intel Core i7-8650U
            Intel[ ]Core[ ]i[357]-1[0-9]{3,4}[UPHG]|  # 10510U, 1135G7, 1250P
            AMD[ ]Ryzen[ ][357][ ][3-9][0-9]{3}C|     # AMD Ryzen 7 3700C
            Genuine[ ]Intel[ ]0000|                   # Unreleased Intel CPU
            AMD[ ]Eng[ ]Sample                        # Unreleased AMD CPU
        '''
        MEDIUM_REGEX = r'''
            Intel[ ]Core[ ][im][357]-[0-9]{4,5}[UY]|  # Intel Core i5-8200Y
            Intel[ ]Core[ ][im][357]-[67]Y[0-9]{2}|   # Intel Core m7-6Y75
            Intel[ ]Pentium[ ][0-9]{4,5}[UY]|         # Intel Pentium 6405U
            Intel[ ]Celeron[ ][0-9]{4,5}[UY]|         # Intel Celeron 5205U
            qcom[ ]sc[0-9]{4}|                        # qcom sc7180
            mediatek[ ]mt819[0-9]                     # mediatek mt8192
        '''
        cpu_name = utils.get_cpu_name()

        if re.search(HIGH_IF_HAS_FAN_REGEX, cpu_name, re.VERBOSE):
            if power_status.has_fan():
                return 'high'
            return 'medium'

        if re.search(MEDIUM_REGEX, cpu_name, re.VERBOSE):
            return 'medium'

        return 'low'
