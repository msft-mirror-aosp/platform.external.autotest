# Lint as: python2, python3
# Copyright 2021 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""This is a server side noise cancellation test using the Chameleon board."""

import logging
import os
import time

from autotest_lib.client.common_lib import error
from autotest_lib.client.cros.audio import audio_test_data
from autotest_lib.client.cros.audio import visqol_utils
from autotest_lib.client.cros.bluetooth.bluetooth_audio_test_data import (
        download_file_from_bucket, get_visqol_binary)
from autotest_lib.client.cros.chameleon import audio_test_utils
from autotest_lib.client.cros.chameleon import chameleon_audio_ids
from autotest_lib.client.cros.chameleon import chameleon_audio_helper
from autotest_lib.server.cros.audio import audio_test

DIST_FILES = 'gs://chromeos-localmirror/distfiles'
DATA_DIR = '/tmp'


class audio_AudioNoiseCancellation(audio_test.AudioTest):
    """Server side input audio noise cancellation test.

    This test talks to a Chameleon board and a Cros device to verify
    input audio noise cancellation function of the Cros device.

    """
    version = 1
    DELAY_BEFORE_RECORD_SECONDS = 0.5
    RECORD_SECONDS = 10
    DELAY_AFTER_BINDING = 0.5

    # This is a 11-second, 2-channel raw audio which will be played by Chameleon
    # speaker on test. It is mixed with the speech reference and the simulated
    # office ambient noise.
    SPEECH_WITH_NOISE_FILE = 'speech_with_noise.raw'

    # This is a 9-second, 1-channel wav file which will be the reference file on
    # VISQOL score calculation. It is the pure speech reference without noise.
    SPEECH_REFERENCE_FILE = 'speech_ref.wav'

    # VISQOL score is ranged from 1.0 to 5.0; the larger score means the better
    # speech quality.
    MIN_VISQOL_SCORE = 3.5

    def cleanup(self):
        # Restore the default state of bypass blocking mechanism in Cras.
        self.facade.set_bypass_block_noise_cancellation(bypass=False)

        # Remove downloaded speech file and reference file.
        if os.path.exists(os.path.join(DATA_DIR, self.SPEECH_WITH_NOISE_FILE)):
            os.remove(os.path.join(DATA_DIR, self.SPEECH_WITH_NOISE_FILE))
        if os.path.exists(os.path.join(DATA_DIR, self.SPEECH_REFERENCE_FILE)):
            os.remove(os.path.join(DATA_DIR, self.SPEECH_REFERENCE_FILE))

    def run_once(self):
        """Runs Audio Noise Cancellation test."""
        if not self.facade.get_noise_cancellation_supported():
            logging.warning('Noise Cancellation is not supported.')
            raise error.TestWarn('Noise Cancellation is not supported.')

        # Download the speech with noise file from bucket.
        remote_path = os.path.join(DIST_FILES, self.SPEECH_WITH_NOISE_FILE)
        if not download_file_from_bucket(
                DATA_DIR, remote_path, lambda _, __, p: p.returncode == 0):
            logging.error('Failed to download %s to %s', remote_path, DATA_DIR)
            raise error.TestError(
                    'Failed to download speech file from bucket.')

        speech_file = audio_test_data.AudioTestData(
                path=os.path.join(DATA_DIR, self.SPEECH_WITH_NOISE_FILE),
                data_format=dict(file_type='raw',
                                 sample_format='S16_LE',
                                 channel=2,
                                 rate=48000),
                duration_secs=11.0)

        # Get and set VISQOL working environment.
        get_visqol_binary()

        # Download the speech reference file from bucket.
        remote_path = os.path.join(DIST_FILES, self.SPEECH_REFERENCE_FILE)
        if not download_file_from_bucket(
                DATA_DIR, remote_path, lambda _, __, p: p.returncode == 0):
            logging.error('Failed to download %s to %s', remote_path, DATA_DIR)
            raise error.TestError('Failed to download ref file from bucket.')

        # Bypass blocking mechanism in Cras to make sure Noise Cancellation is
        # enabled.
        self.facade.set_bypass_block_noise_cancellation(bypass=True)

        source = self.widget_factory.create_widget(
                chameleon_audio_ids.ChameleonIds.LINEOUT)
        sink = self.widget_factory.create_widget(
                chameleon_audio_ids.PeripheralIds.SPEAKER)
        binder = self.widget_factory.create_binder(source, sink)

        recorder = self.widget_factory.create_widget(
                chameleon_audio_ids.CrosIds.INTERNAL_MIC)

        with chameleon_audio_helper.bind_widgets(binder):
            time.sleep(self.DELAY_AFTER_BINDING)

            audio_test_utils.dump_cros_audio_logs(self.host, self.facade,
                                                  self.resultsdir,
                                                  'after_binding')

            # Selects and checks the node selected by cras is correct.
            audio_test_utils.check_and_set_chrome_active_node_types(
                    self.facade, None,
                    audio_test_utils.get_internal_mic_node(self.host))

            logging.info('Setting playback data on Chameleon')
            source.set_playback_data(speech_file)

            # Starts playing, waits for some time, and then starts recording.
            # This is to avoid artifact caused by chameleon codec initialization
            # in the beginning of playback.
            logging.info('Start playing %s from Chameleon', speech_file.path)
            source.start_playback()

            time.sleep(self.DELAY_BEFORE_RECORD_SECONDS)
            logging.info('Start recording from Cros device.')
            recorder.start_recording()

            time.sleep(self.RECORD_SECONDS)

            recorder.stop_recording()
            logging.info('Stopped recording from Cros device.')

            audio_test_utils.dump_cros_audio_logs(self.host, self.facade,
                                                  self.resultsdir,
                                                  'after_recording')

            recorder.read_recorded_binary()
            logging.info('Read recorded binary from Cros device.')

        # Removes the beginning of recorded data. This is to avoid artifact
        # caused by Cros device codec initialization in the beginning of
        # recording.
        recorder.remove_head(1.0)

        recorded_file = os.path.join(self.resultsdir, "recorded.raw")
        logging.info('Saving recorded data to %s', recorded_file)
        recorder.save_file(recorded_file)

        # WAV file is also saved by recorder.save_file().
        recorded_wav_path = recorded_file + '.wav'
        if not os.path.isfile(recorded_wav_path):
            logging.error('WAV file %s does not exist.', recorded_wav_path)
            raise error.TestError('Failed to find recorded wav file.')

        # Get VISQOL score. The score should be high because we expect the
        # recorded data is already noise-cancelled. Set speech_mode to False
        # because the recording rate is 48k, while speech_mode only accepts 16k
        # rate.
        ref_wav_path = os.path.join(DATA_DIR, self.SPEECH_REFERENCE_FILE)
        score = visqol_utils.get_visqol_score(ref_file=ref_wav_path,
                                              deg_file=recorded_wav_path,
                                              log_dir=self.resultsdir,
                                              speech_mode=False)

        logging.info('Got score %f, min passing score: %f', score,
                     self.MIN_VISQOL_SCORE)

        # Track VISQOL performance score
        test_desc = 'internal_mic_noise_cancellation'
        self.write_perf_keyval({test_desc: score})

        if score < self.MIN_VISQOL_SCORE:
            raise error.TestError(
                    'Failed to pass visqol score; got: %f, min: %f' %
                    (score, self.MIN_VISQOL_SCORE))
