# Copyright 2016 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""This is a server side audio volume test using the Chameleon board."""

import logging
import os
import time

from autotest_lib.client.common_lib import error
from autotest_lib.client.cros.chameleon import audio_test_utils
from autotest_lib.client.cros.chameleon import chameleon_audio_ids
from autotest_lib.client.cros.chameleon import chameleon_audio_helper
from autotest_lib.server.cros.audio import audio_test


class audio_AudioVolume(audio_test.AudioTest):
    """Server side audio volume test.

    This test talks to a Chameleon board and a Cros device to verify
    audio volume function of the Cros device.

    """
    version = 1
    RECORD_SECONDS = 5
    DELAY_AFTER_BINDING = 0.5

    def run_once(self,
                 source_id,
                 sink_id,
                 recorder_id,
                 volume_spec,
                 golden_file,
                 switch_hsp=False):
        """Running audio volume test.

        @param source_id: An ID defined in chameleon_audio_ids for source.
        @param sink_id: An ID defined in chameleon_audio_ids for sink if needed.
                        Currently this is only used on bluetooth.
        @param recorder: An ID defined in chameleon_audio_ids for recording.
        @param volume_spec: A tuple (low_volume, high_volume, highest_ratio).
                            Low volume and high volume specifies the two volumes
                            used in the test, and highest_ratio speficies the
                            highest acceptable value for
                            recorded_volume_low / recorded_volume_high.
                            For example, (50, 100, 0.2) asserts that
                            (recorded magnitude at volume 50) should be lower
                            than (recorded magnitude at volume 100) * 0.2.
        @param golden_file: A test file defined in audio_test_data.
        @param switch_hsp: Run a recording process on Cros device. This is
                           to trigger Cros switching from A2DP to HSP.
        """
        if (source_id == chameleon_audio_ids.CrosIds.SPEAKER
                    and not audio_test_utils.has_internal_speaker(self.host)):
            return

        source = self.widget_factory.create_widget(source_id)
        recorder = self.widget_factory.create_widget(recorder_id)

        # Chameleon Mic does not need binding.
        binding = (recorder_id != chameleon_audio_ids.ChameleonIds.MIC)

        binder = None

        if binding:
            if sink_id:
                sink = self.widget_factory.create_widget(sink_id)
                binder = self.widget_factory.create_binder(
                        source, sink, recorder)
            else:
                binder = self.widget_factory.create_binder(source, recorder)

        low_volume, high_volume, highest_ratio = volume_spec
        ignore_frequencies = [50, 60]

        second_peak_ratio = audio_test_utils.get_second_peak_ratio(
                source_id=source_id,
                recorder_id=recorder_id,
                is_hsp=switch_hsp)

        with chameleon_audio_helper.bind_widgets(binder):
            # Checks the node selected by cras is correct.
            time.sleep(self.DELAY_AFTER_BINDING)

            audio_test_utils.dump_cros_audio_logs(self.host, self.facade,
                                                  self.resultsdir,
                                                  'after_binding')

            node_type = audio_test_utils.cros_port_id_to_cras_node_type(
                    source.port_id)
            if node_type == 'HEADPHONE':
                node_type = audio_test_utils.get_headphone_node(self.host)
            audio_test_utils.check_and_set_chrome_active_node_types(
                    self.facade, node_type, None)
            audio_test_utils.dump_cros_audio_logs(
                    self.host, self.facade, self.resultsdir, 'after_select')
            audio_test_utils.check_output_port(self.facade, source.port_id)

            if switch_hsp:
                audio_test_utils.switch_to_hsp(self.facade)

            logging.info('Setting playback data on Cros device')
            source.set_playback_data(golden_file)

            def playback_record(tag):
                """Playback and record.

                @param tag: file name tag.

                """
                logging.info('Start recording from Chameleon.')
                recorder.start_recording()

                logging.info('Start playing %s on Cros device',
                             golden_file.path)
                source.start_playback()

                time.sleep(self.RECORD_SECONDS)
                self.facade.check_audio_stream_at_selected_device()
                recorder.stop_recording()
                logging.info('Stopped recording from Chameleon.')

                audio_test_utils.dump_cros_audio_logs(
                        self.host, self.facade, self.resultsdir,
                        'after_recording_' + 'tag')

                source.stop_playback()

                recorder.read_recorded_binary()
                logging.info('Read recorded binary from Chameleon.')

                recorded_file = os.path.join(self.resultsdir,
                                             "recorded_%s.raw" % tag)
                logging.info('Saving recorded data to %s', recorded_file)
                recorder.save_file(recorded_file)
                recorder.remove_head(0.5)

            self.facade.set_chrome_active_volume(low_volume)
            playback_record('low')
            low_dominant_spectrals = audio_test_utils.check_recorded_frequency(
                    golden_file,
                    recorder,
                    second_peak_ratio=second_peak_ratio,
                    ignore_frequencies=ignore_frequencies)

            self.facade.set_chrome_active_volume(high_volume)
            playback_record('high')
            high_dominant_spectrals = audio_test_utils.check_recorded_frequency(
                    golden_file,
                    recorder,
                    second_peak_ratio=second_peak_ratio,
                    ignore_frequencies=ignore_frequencies)

            error_messages = []
            logging.info('low_dominant_spectrals: %s', low_dominant_spectrals)
            logging.info('high_dominant_spectrals: %s',
                         high_dominant_spectrals)

            for channel in xrange(len(low_dominant_spectrals)):
                _, low_coeff = low_dominant_spectrals[channel]
                _, high_coeff = high_dominant_spectrals[channel]
                ratio = low_coeff / high_coeff
                logging.info('Channel %d volume(at %f) / volume(at %f) = %f',
                             channel, low_volume, high_volume, ratio)
                if ratio > highest_ratio:
                    error_messages.append(
                            'Channel %d volume ratio: %f is incorrect.' %
                            (channel, ratio))
            if error_messages:
                raise error.TestFail(
                        'Failed volume check: %s' % ' '.join(error_messages))
