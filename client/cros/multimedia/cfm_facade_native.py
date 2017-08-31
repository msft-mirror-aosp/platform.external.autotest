# Copyright 2017 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Facade to access the CFM functionality."""

import logging
import urlparse

from autotest_lib.client.common_lib import error
from autotest_lib.client.common_lib.cros import cfm_hangouts_api
from autotest_lib.client.common_lib.cros import cfm_meetings_api
from autotest_lib.client.common_lib.cros import enrollment
from autotest_lib.client.common_lib.cros import kiosk_utils


class TimeoutException(Exception):
    """Timeout Exception class."""
    pass


class CFMFacadeNative(object):
    """Facade to access the CFM functionality.

    The methods inside this class only accept Python native types.
    """
    _USER_ID = 'cfmtest@croste.tv'
    _PWD = 'test0000'
    _EXT_ID = 'ikfcpmgefdpheiiomgmhlmmkihchmdlj'
    _DEFAULT_TIMEOUT = 30


    def __init__(self, resource, screen):
        """Initializes a CFMFacadeNative.

        @param resource: A FacadeResource object.
        """
        self._resource = resource
        self._screen = screen


    def enroll_device(self):
        """Enroll device into CFM."""
        self._resource.start_custom_chrome({"auto_login": False,
                                            "disable_gaia_services": False})
        enrollment.RemoraEnrollment(self._resource._browser, self._USER_ID,
                self._PWD)


    def check_hangout_extension_context(self):
        """Check to make sure hangout app launched.

        @raises error.TestFail if the URL checks fails.
        """
        ext_contexts = kiosk_utils.wait_for_kiosk_ext(
                self._resource._browser, self._EXT_ID)
        ext_urls = [context.EvaluateJavaScript('location.href;')
                        for context in ext_contexts]
        expected_urls = ['chrome-extension://' + self._EXT_ID + '/' + path
                         for path in ['hangoutswindow.html?windowid=0',
                                      'hangoutswindow.html?windowid=1',
                                      'hangoutswindow.html?windowid=2',
                                      '_generated_background_page.html']]
        for url in ext_urls:
            logging.info('Extension URL %s', url)
            if url not in expected_urls:
                raise error.TestFail(
                    'Unexpected extension context urls, expected one of %s, '
                    'got %s' % (expected_urls, url))


    def reboot_device_with_chrome_api(self):
        """Reboot device using chrome runtime API."""
        ext_contexts = kiosk_utils.wait_for_kiosk_ext(
                self._resource._browser, self._EXT_ID)
        for context in ext_contexts:
            context.WaitForDocumentReadyStateToBeInteractiveOrBetter()
            ext_url = context.EvaluateJavaScript('document.URL')
            background_url = ('chrome-extension://' + self._EXT_ID +
                              '/_generated_background_page.html')
            if ext_url in background_url:
                context.ExecuteJavaScript('chrome.runtime.restart();')


    def _get_webview_context_by_screen(self, screen):
        """Get webview context that matches the screen param in the url.

        @param screen: Value of the screen param, e.g. 'hotrod' or 'control'.
        """
        ctxs = kiosk_utils.get_webview_contexts(self._resource._browser,
                                                self._EXT_ID)
        for ctx in ctxs:
            parsed_url = urlparse.urlparse(ctx.GetUrl())
            if urlparse.parse_qs(parsed_url.query)['screen'][0] == screen:
                return ctx
        return None


    def skip_oobe_after_enrollment(self):
        """Skips oobe and goes to the app landing page after enrollment."""
        self.check_hangout_extension_context()
        self.wait_for_hangouts_telemetry_commands()
        self.wait_for_oobe_start_page()
        self.skip_oobe_screen()


    @property
    def _webview_context(self):
        """Get webview context object."""
        return self._get_webview_context_by_screen(self._screen)


    @property
    def _cfmApi(self):
        """Instantiate appropriate cfm api wrapper"""
        if self._webview_context.EvaluateJavaScript(
                "typeof window.hrRunDiagnosticsForTest == 'function'"):
            return cfm_hangouts_api.CfmHangoutsAPI(self._webview_context)
        return cfm_meetings_api.CfmMeetingsAPI(self._webview_context)


    #TODO: This is a legacy api. Deprecate this api and update existing hotrod
    #      tests to use the new wait_for_hangouts_telemetry_commands api.
    def wait_for_telemetry_commands(self):
        """Wait for telemetry commands."""
        self.wait_for_hangouts_telemetry_commands()


    def wait_for_hangouts_telemetry_commands(self):
        """Wait for Hangouts App telemetry commands."""
        self._webview_context.WaitForJavaScriptCondition(
                "typeof window.hrOobIsStartPageForTest == 'function'",
                timeout=self._DEFAULT_TIMEOUT)


    def wait_for_meetings_telemetry_commands(self):
        """Wait for Meet App telemetry commands """
        self._webview_context.WaitForJavaScriptCondition(
                'window.hasOwnProperty("hrTelemetryApi")',
                timeout=self._DEFAULT_TIMEOUT)


    def wait_for_meetings_in_call_page(self):
        """Waits for the in-call page to launch."""
        self.wait_for_meetings_telemetry_commands()
        self._cfmApi.wait_for_meetings_in_call_page()


    def wait_for_meetings_landing_page(self):
        """Waits for the landing page screen."""
        self.wait_for_meetings_telemetry_commands()
        self._cfmApi.wait_for_meetings_landing_page()


    # UI commands/functions
    def wait_for_oobe_start_page(self):
        """Wait for oobe start screen to launch."""
        self._cfmApi.wait_for_oobe_start_page()


    def skip_oobe_screen(self):
        """Skip Chromebox for Meetings oobe screen."""
        self._cfmApi.skip_oobe_screen()


    def is_oobe_start_page(self):
        """Check if device is on CFM oobe start screen.

        @return a boolean, based on oobe start page status.
        """
        return self._cfmApi.is_oobe_start_page()


    # Hangouts commands/functions
    def start_new_hangout_session(self, session_name):
        """Start a new hangout session.

        @param session_name: Name of the hangout session.
        """
        self._cfmApi.start_new_hangout_session(session_name)


    def end_hangout_session(self):
        """End current hangout session."""
        self._cfmApi.end_hangout_session()


    def is_in_hangout_session(self):
        """Check if device is in hangout session.

        @return a boolean, for hangout session state.
        """
        return self._cfmApi.is_in_hangout_session()


    def is_ready_to_start_hangout_session(self):
        """Check if device is ready to start a new hangout session.

        @return a boolean for hangout session ready state.
        """
        return self._cfmApi.is_ready_to_start_hangout_session()


    def join_meeting_session(self, session_name):
        """Joins a meeting.

        @param session_name: Name of the meeting session.
        """
        self._cfmApi.join_meeting_session(session_name)


    def start_meeting_session(self):
        """Start a meeting."""
        self._cfmApi.start_meeting_session()


    def end_meeting_session(self):
        """End current meeting session."""
        self._cfmApi.end_meeting_session()


    # Diagnostics commands/functions
    def is_diagnostic_run_in_progress(self):
        """Check if hotrod diagnostics is running.

        @return a boolean for diagnostic run state.
        """
        return self._cfmApi.is_diagnostic_run_in_progress()


    def wait_for_diagnostic_run_to_complete(self):
        """Wait for hotrod diagnostics to complete."""
        self._cfmApi.wait_for_diagnostic_run_to_complete()


    def run_diagnostics(self):
        """Run hotrod diagnostics."""
        self._cfmApi.run_diagnostics()


    def get_last_diagnostics_results(self):
        """Get latest hotrod diagnostics results.

        @return a dict with diagnostic test results.
        """
        return self._cfmApi.get_last_diagnostics_results()


    # Mic audio commands/functions
    def is_mic_muted(self):
        """Check if mic is muted.

        @return a boolean for mic mute state.
        """
        return self._cfmApi.is_mic_muted()


    def mute_mic(self):
        """Local mic mute from toolbar."""
        self._cfmApi.mute_mic()


    def unmute_mic(self):
        """Local mic unmute from toolbar."""
        self._cfmApi.unmute_mic()


    def remote_mute_mic(self):
        """Remote mic mute request from cPanel."""
        self._cfmApi.remote_mute_mic()


    def remote_unmute_mic(self):
        """Remote mic unmute request from cPanel."""
        self._cfmApi.remote_unmute_mic()


    def get_mic_devices(self):
        """Get all mic devices detected by hotrod.

        @return a list of mic devices.
        """
        return self._cfmApi.get_mic_devices()


    def get_preferred_mic(self):
        """Get mic preferred for hotrod.

        @return a str with preferred mic name.
        """
        return self._cfmApi.get_preferred_mic()


    def set_preferred_mic(self, mic):
        """Set preferred mic for hotrod.

        @param mic: String with mic name.
        """
        self._cfmApi.set_preferred_mic(mic)


    # Speaker commands/functions
    def get_speaker_devices(self):
        """Get all speaker devices detected by hotrod.

        @return a list of speaker devices.
        """
        return self._cfmApi.get_speaker_devices()


    def get_preferred_speaker(self):
        """Get speaker preferred for hotrod.

        @return a str with preferred speaker name.
        """
        return self._cfmApi.get_preferred_speaker()


    def set_preferred_speaker(self, speaker):
        """Set preferred speaker for hotrod.

        @param speaker: String with speaker name.
        """
        self._cfmApi.set_preferred_speaker(speaker)


    def set_speaker_volume(self, volume_level):
        """Set speaker volume.

        @param volume_level: String value ranging from 0-100 to set volume to.
        """
        self._cfmApi.set_speaker_volume(volume_level)


    def get_speaker_volume(self):
        """Get current speaker volume.

        @return a str value with speaker volume level 0-100.
        """
        return self._cfmApi.get_speaker_volume()


    def play_test_sound(self):
        """Play test sound."""
        self._cfmApi.play_test_sound()


    # Camera commands/functions
    def get_camera_devices(self):
        """Get all camera devices detected by hotrod.

        @return a list of camera devices.
        """
        return self._cfmApi.get_camera_devices()


    def get_preferred_camera(self):
        """Get camera preferred for hotrod.

        @return a str with preferred camera name.
        """
        return self._cfmApi.get_preferred_camera()


    def set_preferred_camera(self, camera):
        """Set preferred camera for hotrod.

        @param camera: String with camera name.
        """
        self._cfmApi.set_preferred_camera(camera)


    def is_camera_muted(self):
        """Check if camera is muted (turned off).

        @return a boolean for camera muted state.
        """
        return self._cfmApi.is_camera_muted()


    def mute_camera(self):
        """Turned camera off."""
        self._cfmApi.mute_camera()


    def unmute_camera(self):
        """Turned camera on."""
        self._cfmApi.unmute_camera()
