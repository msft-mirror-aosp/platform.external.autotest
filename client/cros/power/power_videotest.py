# Lint as: python2, python3
# Copyright 2019 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
import abc
import logging
import time

from autotest_lib.client.bin import utils
from autotest_lib.client.common_lib.cros import arc_common
from autotest_lib.client.cros import tast
from autotest_lib.client.cros.tast.ui import chrome_service_pb2
from autotest_lib.client.cros.tast.ui import conn_service_pb2
from autotest_lib.client.cros.tast.ui import conn_tab
from autotest_lib.client.cros.tast.ui import lacros_service_pb2
from autotest_lib.client.cros.tast.ui import tast_utils
from autotest_lib.client.cros.tast.ui import tconn_service_pb2_grpc
from autotest_lib.client.cros.audio import audio_helper
from autotest_lib.client.cros.power import power_test


class power_VideoTest(power_test.power_Test):
    """Optional base class for power related video tests."""
    version = 1

    # Ram disk location to download video file.
    # We use ram disk to avoid power hit from network / disk usage.
    _RAMDISK = '/tmp/ramdisk'

    # Time in seconds to wait after set up before starting each video.
    _WAIT_FOR_IDLE = 15

    # Time in seconds to measure power per video file.
    _MEASUREMENT_DURATION = 120

    # Chrome arguments to disable HW video decode
    _DISABLE_HW_VIDEO_DECODE_ARGS = '--disable-accelerated-video-decode'


    def initialize(self,
                   seconds_period=3,
                   pdash_note='',
                   force_discharge=False,
                   check_network=False,
                   run_arc=True):
        """Create and mount ram disk to download video."""
        super(power_VideoTest,
              self).initialize(seconds_period=seconds_period,
                               pdash_note=pdash_note,
                               force_discharge=force_discharge,
                               check_network=check_network,
                               run_arc=run_arc)
        utils.run('mkdir -p %s' % self._RAMDISK)
        # Don't throw an exception on errors.
        result = utils.run('mount -t ramfs -o context=u:object_r:tmpfs:s0 '
                           'ramfs %s' % self._RAMDISK, ignore_status=True)
        if result.exit_status:
            logging.info('cannot mount ramfs with context=u:object_r:tmpfs:s0,'
                         ' trying plain mount')
            # Try again without selinux options.  This time fail on error.
            utils.run('mount -t ramfs ramfs %s' % self._RAMDISK)
        audio_helper.set_volume_levels(10, 10)

    @abc.abstractmethod
    def _prepare_video(self, url):
        """Prepare browser session before playing video.

        @param url: url of video file to play.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def _start_video(self, tab, url):
        """Open the video and play it.

        @param tab: object, Tast Chrome tab instance.
        @param url: url of video file to play.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def _teardown_video(self, url):
        """Teardown browser session after playing video.

        @param url: url of video file to play.
        """
        raise NotImplementedError()

    def _calculate_dropped_frame_percent(self, tab):
        """Calculate percent of dropped frame.

        @param tab: tab object that played video in Tast Chrome instance.
        """
        decoded_frame_count = tab.EvaluateJavaScript(
                "document.getElementsByTagName"
                "('video')[0].webkitDecodedFrameCount")
        dropped_frame_count = tab.EvaluateJavaScript(
                "document.getElementsByTagName"
                "('video')[0].webkitDroppedFrameCount")
        if decoded_frame_count != 0:
            dropped_frame_percent = \
                    100.0 * dropped_frame_count / decoded_frame_count
        else:
            logging.error("No frame is decoded. Set drop percent to 100.")
            dropped_frame_percent = 100.0

        logging.info("Decoded frames=%d, dropped frames=%d, percent=%f",
                decoded_frame_count, dropped_frame_count, dropped_frame_percent)
        return dropped_frame_percent

    def run_once(self, videos=None, secs_per_video=_MEASUREMENT_DURATION,
                 use_hw_decode=True, tast_bundle_path=None, use_lacros=False):
        """run_once method.

        @param videos: list of tuple of tagname and video url to test.
        @param secs_per_video: time in seconds to play video and measure power.
        @param use_hw_decode: if False, disable hw video decoding.
        @param tast_bundle_path: Path to a tast_bundle executable.
        @param use_lacros: Whether to use Lacros as the browser.
        """


        with tast.GRPC(tast_bundle_path) as tast_grpc,\
            tast.ChromeService(tast_grpc.channel) as chrome_service,\
            tast.LacrosService(tast_grpc.channel) as lacros_service,\
            tast.ConnService(tast_grpc.channel) as conn_service:
            tconn_service = tconn_service_pb2_grpc.TconnServiceStub(tast_grpc.channel)

            # --disable-sync disables test account info sync, eg. Wi-Fi
            # credentials, so that each test run does not remember info from
            # last test run.
            extra_args = ['--disable-sync']

            if not use_hw_decode:
                extra_args.append(self._DISABLE_HW_VIDEO_DECODE_ARGS)

            # Connect to Ash Chrome and login.
            chrome_service.New(chrome_service_pb2.NewRequest(
                # b/228256145 to avoid powerd restart
                disable_features = ['FirmwareUpdaterApp'],
                extra_args = extra_args,
                arc_mode = (chrome_service_pb2.ARC_MODE_ENABLED
                            if self._arc_mode == arc_common.ARC_MODE_ENABLED
                            else chrome_service_pb2.ARC_MODE_DISABLED),
                lacros = (chrome_service_pb2.Lacros(
                    mode=chrome_service_pb2.Lacros.Mode.MODE_ONLY)
                    if use_lacros else chrome_service_pb2.Lacros())
            ))

            if use_lacros:
                lacros_service.LaunchWithURL(lacros_service_pb2.LaunchWithURLRequest(
                    url = 'about:blank'
                ))
                response = conn_service.NewConnForTarget(conn_service_pb2.NewConnForTargetRequest(
                    url = 'about:blank',
                    call_on_lacros = True
                ))
            else:
                response = conn_service.NewConn(conn_service_pb2.NewConnRequest(
                    url = 'about:blank'
                ))
            tab = conn_tab.ConnTab(conn_service, response.id)
            tab.ActivateTarget()

            # Run in fullscreen.
            tast_utils.make_current_screen_fullscreen(tconn_service, call_on_lacros=use_lacros)

            # Stop services and disable multicast again as Chrome might have
            # restarted them.
            self._services.stop_services()
            self._multicast_disabler.disable_network_multicast()

            self.start_measurements()
            idle_start = time.time()

            for name, url in videos:
                self._prepare_video(url)
                time.sleep(self._WAIT_FOR_IDLE)

                logging.info('Playing video: %s', name)
                self._start_video(tab, url)
                self.checkpoint_measurements('idle', idle_start)

                loop_start = time.time()
                time.sleep(secs_per_video)
                self.checkpoint_measurements(name, loop_start)
                idle_start = time.time()
                self.keyvals[name + '_dropped_frame_percent'] = \
                        self._calculate_dropped_frame_percent(tab)
                self._teardown_video(url)

            # Re-enable multicast here instead of in the cleanup because Chrome
            # might re-enable it and we can't verify that multicast is off.
            self._multicast_disabler.enable_network_multicast()

    def cleanup(self):
        """Unmount ram disk."""
        utils.run('umount %s' % self._RAMDISK)
        super(power_VideoTest, self).cleanup()
