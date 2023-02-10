# Lint as: python3
# Copyright 2023 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
import logging
import time

from autotest_lib.client.common_lib.cros import chrome
from autotest_lib.client.cros.power import power_test
from autotest_lib.client.cros.power import power_utils


class power_BasicBrowsing(power_test.power_Test):
    """class for power_BasicBrowsing test.

    This tests is used for web content repeatability experiment
    for power test gen2. This will get deleted once Tast power
    library is ready.
    """
    version = 1

    URL_PREFIX = 'https://storage.googleapis.com/chromiumos-test-assets-public/power_LoadTest/p/'
    URL_SUFFIX = '.html'
    SITES = [
            'google', 'youtube', 'wikipedia', 'yahoo', 'amazon', 'samsung',
            'naver', 'weather', 'globo', 'aajtak'
    ]

    def run_once(self,
                 urls=None,
                 warmup_secs=20,
                 secs_per_url=180,
                 loop_count=2):
        """run_once method.

        @param urls: list of url to do browsing
        @param warmup_secs: duration for warmup at the beginning of the test
        @param secs_per_url: duration to show on each url in each loop
        @param loop_count: number of loop to test
        """
        if urls is None:
            urls = [
                    self.URL_PREFIX + site + self.URL_SUFFIX
                    for site in self.SITES
            ]

        # --disable-sync disables test account info sync, eg. Wi-Fi credentials,
        # so that each test run does not remember info from last test run.
        extra_browser_args = ['--disable-sync']
        # b/228256145 to avoid powerd restart
        extra_browser_args.append('--disable-features=FirmwareUpdaterApp')
        with chrome.Chrome(autotest_ext=True,
                           extra_browser_args=extra_browser_args,
                           init_network_controller=True) as self.cr:
            # Just measure power in full-screen.
            tab = self.cr.browser.tabs[0]
            tab.Activate()
            power_utils.set_fullscreen(self.cr)

            tab.Navigate(urls[0])
            tab.WaitForDocumentReadyStateToBeComplete()
            time.sleep(warmup_secs)

            # Stop services and disable multicast again as Chrome might have
            # restarted them.
            self._services.stop_services()
            self._multicast_disabler.disable_network_multicast()

            self.start_measurements()

            task_count = 0
            secs_per_scroll = 20
            for loop in range(loop_count):
                for i, url in enumerate(urls):
                    start_time = time.time()
                    logging.info('Navigating to url: %s', url)
                    tab.Navigate(url)
                    tab.WaitForDocumentReadyStateToBeComplete()

                    tagname = '%s_%s' % (self.SITES[i], loop)
                    scroll_amount = 600
                    for sec in range(secs_per_scroll, secs_per_url,
                                     secs_per_scroll):
                        end_time = start_time + sec
                        sleep_time = end_time - time.time()
                        if sleep_time < 0:
                            logging.warn(
                                    'Skip scrolling at %s because load time'
                                    'is too long at %d secs', url, sec)
                            continue
                        time.sleep(sleep_time)
                        js = 'window.scrollBy(0, %d)' % scroll_amount
                        tab.EvaluateJavaScript(js)
                        scroll_amount = -scroll_amount
                    self.loop_sleep(task_count, secs_per_url)
                    self.checkpoint_measurements(tagname, start_time)
                    task_count += 1

            # Re-enable multicast here instead of in the cleanup because Chrome
            # might re-enable it and we can't verify that multicast is off.
            self._multicast_disabler.enable_network_multicast()
