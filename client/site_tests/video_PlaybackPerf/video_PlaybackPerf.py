# Copyright (c) 2014 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import collections
import logging
import os
import time

from autotest_lib.client.bin import test, utils
from autotest_lib.client.common_lib import error
from autotest_lib.client.common_lib import file_utils
from autotest_lib.client.common_lib.cros import chrome
from autotest_lib.client.cros import service_stopper
from autotest_lib.client.cros.power import power_rapl
from autotest_lib.client.cros.power import power_status
from autotest_lib.client.cros.power import power_utils
from autotest_lib.client.cros.video import device_capability
from autotest_lib.client.cros.video import histogram_verifier
from autotest_lib.client.cros.video import constants
from autotest_lib.client.cros.video import helper_logger


DISABLE_ACCELERATED_VIDEO_DECODE_BROWSER_ARGS = '--disable-accelerated-video-decode'
ENABLE_AUTOPLAY = '--autoplay-policy=no-user-gesture-required'
DOWNLOAD_BASE = 'http://commondatastorage.googleapis.com/chromiumos-test-assets-public/'

PLAYBACK_WITH_HW_ACCELERATION = 'playback_with_hw_acceleration'
PLAYBACK_WITHOUT_HW_ACCELERATION = 'playback_without_hw_acceleration'

# Measurement duration in seconds.
MEASUREMENT_DURATION = 30
# Time to exclude from calculation after playing a video [seconds].
STABILIZATION_DURATION = 10

# Time in seconds to wait for cpu idle until giveup.
WAIT_FOR_IDLE_CPU_TIMEOUT = 60.0
# Maximum percent of cpu usage considered as idle.
CPU_IDLE_USAGE = 0.1

CPU_USAGE_DESCRIPTION = 'video_cpu_usage_'
DROPPED_FRAMES_DESCRIPTION = 'video_dropped_frames_'
DROPPED_FRAMES_PERCENT_DESCRIPTION = 'video_dropped_frames_percent_'
POWER_DESCRIPTION = 'video_mean_energy_rate_'
RAPL_GRAPH_NAME = 'rapl_power_consumption'

# Minimum battery charge percentage to run the test
BATTERY_INITIAL_CHARGED_MIN = 10


class video_PlaybackPerf(test.test):
    """
    The test outputs the cpu usage, the dropped frame count and the power
    consumption for video playback to performance dashboard.
    """
    version = 1


    def initialize(self):
        self._service_stopper = None
        self._original_governors = None
        self._backlight = None


    def start_playback(self, cr, tab, local_path):
        """
        Opens the video and plays it.

        @param cr: Autotest Chrome instance.
        @param tab: Chrome tab playing a video.
        @param local_path: path to the local video file to play.
        """
        cr.browser.platform.SetHTTPServerDirectories(self.bindir)
        tab.Navigate(cr.browser.platform.http_server.UrlOf(local_path))
        tab.WaitForDocumentReadyStateToBeComplete()
        tab.EvaluateJavaScript("document.getElementsByTagName('video')[0]."
                               "loop=true")


    @helper_logger.video_log_wrapper
    def run_once(self, video_name, video_description, capability,
                 power_test=False):
        """
        Runs the video_PlaybackPerf test.

        @param video_name: the name of video to play in the DOWNLOAD_BASE
        @param video_description: a string describes the video to play which
                will be part of entry name in dashboard.
        @param capability: If a device has a specified capability, HW playback
                must be available.
        @param power_test: True if this is a power test and it would only run
                the power test. If False, it would run the cpu usage test and
                the dropped frame count test.
        """
        # Download test video.
        url = DOWNLOAD_BASE + video_name
        local_path = os.path.join(self.bindir, os.path.basename(video_name))
        logging.info("Downloading %s to %s", url, local_path);
        file_utils.download_file(url, local_path)
        self.must_hw_playback = (
            device_capability.DeviceCapability().have_capability(capability))

        if not power_test:
            # Run the video playback dropped frame tests.
            keyvals = self.test_dropped_frames(local_path)

            # Every dictionary value is a tuple. The first element of the tuple
            # is dropped frames. The second is dropped frames percent.
            keyvals_dropped_frames = {k: v[0] for k, v in keyvals.iteritems()}
            keyvals_dropped_frames_percent = {
                    k: v[1] for k, v in keyvals.iteritems()}

            self.log_result(keyvals_dropped_frames, DROPPED_FRAMES_DESCRIPTION +
                                video_description, 'frames')
            self.log_result(keyvals_dropped_frames_percent,
                            DROPPED_FRAMES_PERCENT_DESCRIPTION +
                                video_description, 'percent')

            # Run the video playback cpu usage tests.
            keyvals = self.test_cpu_usage(local_path)
            self.log_result(keyvals, CPU_USAGE_DESCRIPTION + video_description,
                            'percent')
        else:
            tmp = self.test_power(local_path)
            # Power measurement with rapl(4 domains) and system drain are
            # reported. Reformat the data to align with the log_result.
            keyvals = collections.defaultdict(dict)
            for top_key in tmp.keys():
                for key in tmp[top_key].keys():
                    keyvals[key][top_key] = tmp[top_key][key]

            for key in keyvals:
                rapl_type = [keyword for keyword in power_rapl.VALID_DOMAINS
                             if keyword in key]
                if rapl_type:
                    description = "%s_%s_pwr" % (video_description,
                                                 rapl_type[0])
                    self.log_result(keyvals[key], description, 'W',
                                    graph=RAPL_GRAPH_NAME)
                else:
                    self.log_result(keyvals[key],
                                    POWER_DESCRIPTION + video_description, 'W')


    def test_dropped_frames(self, local_path):
        """
        Runs the video dropped frame test.

        @param local_path: the path to the video file.

        @return a dictionary that contains the test result.
        """
        def get_dropped_frames(cr):
            time.sleep(MEASUREMENT_DURATION)
            tab = cr.browser.tabs[0]
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
                              decoded_frame_count,
                              dropped_frame_count,
                              dropped_frame_percent)
            return (dropped_frame_count, dropped_frame_percent)
        return self.test_playback(local_path, get_dropped_frames)


    def test_cpu_usage(self, local_path):
        """
        Runs the video cpu usage test.

        @param local_path: the path to the video file.

        @return a dictionary that contains the test result.
        """
        def get_cpu_usage(cr):
            time.sleep(STABILIZATION_DURATION)
            cpu_usage_start = utils.get_cpu_usage()
            time.sleep(MEASUREMENT_DURATION)
            cpu_usage_end = utils.get_cpu_usage()
            return utils.compute_active_cpu_time(cpu_usage_start,
                                                      cpu_usage_end) * 100

        # crbug/753292 - APNG login pictures increase CPU usage. Move the more
        # strict idle checks after the login phase.
        if not utils.wait_for_idle_cpu(WAIT_FOR_IDLE_CPU_TIMEOUT,
                                       CPU_IDLE_USAGE):
            logging.warning('Could not get idle CPU pre login.')
        if not utils.wait_for_cool_machine():
            logging.warning('Could not get cold machine pre login.')

        # Stop the thermal service that may change the cpu frequency.
        self._service_stopper = service_stopper.get_thermal_service_stopper()
        self._service_stopper.stop_services()
        # Set the scaling governor to performance mode to set the cpu to the
        # highest frequency available.
        self._original_governors = utils.set_high_performance_mode()
        return self.test_playback(local_path, get_cpu_usage)


    def test_power(self, local_path):
        """
        Runs the video power consumption test.

        @param local_path: the path to the video file.

        @return a dictionary that contains the test result.
        """

        self._backlight = power_utils.Backlight()
        self._backlight.set_default()

        self._service_stopper = service_stopper.ServiceStopper(
                service_stopper.ServiceStopper.POWER_DRAW_SERVICES)
        self._service_stopper.stop_services()

        self._power_status = power_status.get_status()
        # We expect the DUT is powered by battery now. But this is not always
        # true due to other bugs. Disable this test temporarily as workaround.
        # TODO(kcwu): remove this workaround after AC control is stable
        #             crbug.com/723968
        if self._power_status.on_ac():
            logging.warning('Still powered by AC. Skip this test')
            return {}
        # Verify that the battery is sufficiently charged.
        self._power_status.assert_battery_state(BATTERY_INITIAL_CHARGED_MIN)

        measurements = [power_status.SystemPower(
                self._power_status.battery_path)]
        if power_utils.has_rapl_support():
            measurements += power_rapl.create_rapl()

        def get_power(cr):
            power_logger = power_status.PowerLogger(measurements)
            power_logger.start()
            time.sleep(STABILIZATION_DURATION)
            start_time = time.time()
            time.sleep(MEASUREMENT_DURATION)
            power_logger.checkpoint('result', start_time)
            keyval = power_logger.calc()
            # save_results() will save result_raw.txt and result_summary.txt,
            # where the former contains raw data.
            fname_prefix = 'result_%.0f' % time.time()
            power_logger.save_results(self.resultsdir, fname_prefix)
            pwrval = {}
            for measurement in measurements:
                metric_name = 'result_' + measurement.domain
                # Use a list contains the average power only for fallback.
                pwrval[metric_name + '_pwr'] = [
                        keyval[metric_name + '_pwr_avg']]
                with open(os.path.join(
                        self.resultsdir, fname_prefix + '_raw.txt')) as f:
                    for line in f.readlines():
                        if line.startswith(metric_name):
                            split_data = line.split('\t')
                            # split_data[0] is metric_name, [1:] are raw data.
                            pwrval[metric_name + '_pwr'] = [
                                    float(data) for data in split_data[1:]]
                            break
            return pwrval

        return self.test_playback(local_path, get_power)


    def test_playback(self, local_path, gather_result):
        """
        Runs the video playback test with and without hardware acceleration.

        @param local_path: the path to the video file.
        @param gather_result: a function to run and return the test result
                after chrome opens. The input parameter of the funciton is
                Autotest chrome instance.

        @return a dictionary that contains test the result.
        """
        keyvals = {}

        with chrome.Chrome(
                extra_browser_args=[helper_logger.chrome_vmodule_flag(),
                                    ENABLE_AUTOPLAY],
                init_network_controller=True) as cr:

            # crbug/753292 - enforce the idle checks after login
            if not utils.wait_for_idle_cpu(WAIT_FOR_IDLE_CPU_TIMEOUT,
                                           CPU_IDLE_USAGE):
                logging.warning('Could not get idle CPU post login.')
            if not utils.wait_for_cool_machine():
                logging.warning('Could not get cold machine post login.')
            hd = histogram_verifier.HistogramDiffer(
                    cr, constants.MEDIA_GVD_INIT_STATUS)
            error_differ = histogram_verifier.HistogramDiffer(
                cr, constants.MEDIA_GVD_ERROR)

            # Open the video playback page and start playing.
            video_tab = cr.browser.tabs[0]
            self.start_playback(cr, video_tab, local_path)
            result = gather_result(cr)

            self.check_playback(video_tab)

            # Check if decode is hardware accelerated.
            _, histogram = histogram_verifier.poll_histogram_grow(
                    hd, timeout=10, sleep_interval=1)

            # Without disabling HW acceleration, some bucket in GVD Initialize
            # Status must be incremented, in either failure or success.
            if len(histogram) != 1:
                raise error.TestError(err_desc)

            # Check if there's GPU Video Error for a period of time.
            has_error, diff_error = histogram_verifier.poll_histogram_grow(
                error_differ)
            if has_error:
                raise error.TestError(
                    'GPU Video Decoder Error. Histogram diff: %r' % diff_error)

            if constants.MEDIA_GVD_BUCKET in histogram:
                keyvals[PLAYBACK_WITH_HW_ACCELERATION] = result
            else:
                logging.info('Hardware playback not detected.')
                if self.must_hw_playback:
                    raise error.TestError(
                        'Expected hardware playback is not detected.')
                keyvals[PLAYBACK_WITHOUT_HW_ACCELERATION] = result
                return keyvals

        # Start chrome with disabled video hardware decode flag.
        with chrome.Chrome(extra_browser_args=[
                DISABLE_ACCELERATED_VIDEO_DECODE_BROWSER_ARGS,
                ENABLE_AUTOPLAY],
                init_network_controller=True) as cr:
            hd = histogram_verifier.HistogramDiffer(
                    cr, constants.MEDIA_GVD_INIT_STATUS)
            # Open the video playback page and start playing.
            video_tab = cr.browser.tabs[0]
            self.start_playback(cr, video_tab, local_path)
            result = gather_result(cr)

            self.check_playback(video_tab)

            # Make sure decode is not hardware accelerated.
            _, histogram = histogram_verifier.poll_histogram_grow(
                    hd, timeout=10, sleep_interval=1)
            if constants.MEDIA_GVD_BUCKET in histogram:
                raise error.TestError(
                        'Video decode acceleration should not be working.')

            keyvals[PLAYBACK_WITHOUT_HW_ACCELERATION] = result

        return keyvals


    def check_playback(self, tab, minimum_decoded_frames=100):
        """
        Checks if video playback works as expected.
        It checks number of decoded frames. It it is too few, there must be
        something wrong.

        @param tab: chrome tab used to play a video.
        @param minimum_decoded_frame: the number of decoded frames if Chrome
            plays a video correctly in the tab.
        @raise TestError if video is not played correctly.
        """
        decoded_frame_count = tab.EvaluateJavaScript(
            "document.getElementsByTagName"
            "('video')[0].webkitDecodedFrameCount")
        # If playback is performed successfully, 100 video frames are decoded
        # at least in any case.
        if decoded_frame_count < minimum_decoded_frames:
            raise error.TestError(
                "Playback is not done correctly. The number of decoded "
                "frames (=%d) is less than %d for 30 seconds" %
                (decoded_frame_count, minimum_decoded_frames))


    def log_result(self, keyvals, description, units, graph=None):
        """
        Logs the test result output to the performance dashboard.

        @param keyvals: a dictionary that contains results returned by
                test_playback.
        @param description: a string that describes the video and test result
                and it will be part of the entry name in the dashboard.
        @param units: the units of test result.
        @param graph: a string that indicates which graph should the result
                      belongs to.
        """
        result_with_hw = keyvals.get(PLAYBACK_WITH_HW_ACCELERATION)
        if result_with_hw is not None:
            self.output_perf_value(
                    description= 'hw_' + description, value=result_with_hw,
                    units=units, higher_is_better=False, graph=graph)

        result_without_hw = keyvals.get(PLAYBACK_WITHOUT_HW_ACCELERATION)
        if result_without_hw is not None:
            self.output_perf_value(
                    description= 'sw_' + description, value=result_without_hw,
                    units=units, higher_is_better=False, graph=graph)


    def cleanup(self):
        # cleanup() is run by common_lib/test.py.
        if self._backlight:
            self._backlight.restore()
        if self._service_stopper:
            self._service_stopper.restore_services()
        if self._original_governors:
            utils.restore_scaling_governor_states(self._original_governors)

        super(video_PlaybackPerf, self).cleanup()
