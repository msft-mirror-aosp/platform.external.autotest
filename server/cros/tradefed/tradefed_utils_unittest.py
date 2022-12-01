# Lint as: python2, python3
# Copyright 2017 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
import os
import unittest

import common

from autotest_lib.server.cros.tradefed import tradefed_utils


def _load_data(filename):
    """Loads the test data of the given file name."""
    with open(os.path.join(os.path.dirname(os.path.realpath(__file__)),
                           'tradefed_utils_unittest_data', filename), 'r') as f:
        return f.read()


class TradefedTestTest(unittest.TestCase):
    """Unittest for tradefed_utils."""

    def test_parse_tradefed_result(self):
        """Test for parse_tradefed_result."""

        waivers = set([
            'android.app.cts.SystemFeaturesTest#testUsbAccessory',
            'android.widget.cts.GridViewTest#testSetNumColumns',
        ])

        # b/35605415 and b/36520623
        # http://pantheon/storage/browser/chromeos-autotest-results/108103986-chromeos-test/
        # CTS: Tradefed may split a module to multiple chunks.
        # Besides, the module name may not end with "TestCases".
        waived, _ = tradefed_utils.parse_tradefed_result(
            _load_data('CtsHostsideNetworkTests.txt'),
            waivers=waivers)
        self.assertEquals(0, len(waived))

        # b/35530394
        # http://pantheon/storage/browser/chromeos-autotest-results/108291418-chromeos-test/
        # Crashed, but the automatic retry by tradefed executed the rest.
        waived, _ = tradefed_utils.parse_tradefed_result(
            _load_data('CtsMediaTestCases.txt'),
            waivers=waivers)
        self.assertEquals(0, len(waived))

        # b/35530394
        # http://pantheon/storage/browser/chromeos-autotest-results/106540705-chromeos-test/
        # Crashed in the middle, and the device didn't came back.
        waived, _ = tradefed_utils.parse_tradefed_result(
            _load_data('CtsSecurityTestCases.txt'),
            waivers=waivers)
        self.assertEquals(0, len(waived))

        # b/36629187
        # http://pantheon/storage/browser/chromeos-autotest-results/108855595-chromeos-test/
        # Crashed in the middle. Tradefed decided not to continue.
        waived, _ = tradefed_utils.parse_tradefed_result(
            _load_data('CtsViewTestCases.txt'),
            waivers=waivers)
        self.assertEquals(0, len(waived))

        # b/36375690
        # http://pantheon/storage/browser/chromeos-autotest-results/109040174-chromeos-test/
        # Mixture of real failures and waivers.
        waived, _ = tradefed_utils.parse_tradefed_result(
            _load_data('CtsAppTestCases.txt'),
            waivers=waivers)
        self.assertEquals(1, len(waived))
        # ... and the retry of the above failing iteration.
        waived, _ = tradefed_utils.parse_tradefed_result(
            _load_data('CtsAppTestCases-retry.txt'),
            waivers=waivers)
        self.assertEquals(1, len(waived))

        # http://pantheon/storage/browser/chromeos-autotest-results/116875512-chromeos-test/
        # When a test case crashed during teardown, tradefed prints the "fail"
        # message twice. Tolerate it and still return an (inconsistent) count.
        waived, _ = tradefed_utils.parse_tradefed_result(
            _load_data('CtsWidgetTestCases.txt'),
            waivers=waivers)
        self.assertEquals(1, len(waived))

        # http://pantheon/storage/browser/chromeos-autotest-results/117914707-chromeos-test/
        # When a test case unrecoverably crashed during teardown, tradefed
        # prints the "fail" and failure summary message twice. Tolerate it.
        waived, _ = tradefed_utils.parse_tradefed_result(
            _load_data('CtsPrintTestCases.txt'),
            waivers=waivers)
        self.assertEquals(0, len(waived))

        gts_waivers = set([
            ('com.google.android.placement.gts.CoreGmsAppsTest#' +
                'testCoreGmsAppsPreloaded'),
            ('com.google.android.placement.gts.CoreGmsAppsTest#' +
                'testGoogleDuoPreloaded'),
            'com.google.android.placement.gts.UiPlacementTest#testPlayStore'
        ])

        # crbug.com/748116
        # http://pantheon/storage/browser/chromeos-autotest-results/130080763-chromeos-test/
        # 3 ABIS: x86, x86_64, and armeabi-v7a
        waived, _ = tradefed_utils.parse_tradefed_result(
            _load_data('GtsPlacementTestCases.txt'),
            waivers=gts_waivers)
        self.assertEquals(9, len(waived))

        # b/64095702
        # http://pantheon/storage/browser/chromeos-autotest-results/130211812-chromeos-test/
        # The result of the last chunk not reported by tradefed.
        # The actual dEQP log is too big, hence the test data here is trimmed.
        waived, _ = tradefed_utils.parse_tradefed_result(
            _load_data('CtsDeqpTestCases-trimmed.txt'),
            waivers=waivers)
        self.assertEquals(0, len(waived))

        # b/80160772
        # http://pantheon/storage/browser/chromeos-autotest-results/201962931-kkanchi/
        # The newer tradefed requires different parsing to count waivers.
        waived, _ = tradefed_utils.parse_tradefed_result(
            _load_data('CtsAppTestCases_P_simplified.txt'),
            waivers=waivers)
        self.assertEquals(1, len(waived))

        # b/66899135, tradefed may reported inaccuratly with `list results`.
        # Check if summary section shows that the result is inacurrate.
        _, accurate = tradefed_utils.parse_tradefed_result(
            _load_data('CtsAppTestCases_P_simplified.txt'),
            waivers=waivers)
        self.assertTrue(accurate)

        _, accurate = tradefed_utils.parse_tradefed_result(
            _load_data('CtsDeqpTestCases-trimmed-inaccurate.txt'),
            waivers=waivers)
        self.assertFalse(accurate)

    def test_get_test_result_xml_path(self):
        path = tradefed_utils.get_test_result_xml_path(os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            'tradefed_utils_unittest_data', 'results'))
        self.assertEqual(path, os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            'tradefed_utils_unittest_data', 'results', '2019.11.07_10.14.55',
            'test_result.xml'))

        # assertNoRaises
        tradefed_utils.get_test_result_xml_path(os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            'tradefed_utils_unittest_data', 'not_exist'))

    def test_parse_tradefed_testresults_xml_no_failure(self):
        waived = tradefed_utils.parse_tradefed_testresults_xml(
                os.path.join(os.path.dirname(os.path.realpath(__file__)),
                             'tradefed_utils_unittest_data',
                             'test_result.xml'))
        self.assertEquals(0, len(waived))

    def test_parse_tradefed_testresults_xml_no_failure_R(self):
        waived = tradefed_utils.parse_tradefed_testresults_xml(
                os.path.join(os.path.dirname(os.path.realpath(__file__)),
                             'tradefed_utils_unittest_data',
                             'test_result_R.xml'))
        self.assertEquals(0, len(waived))

    def test_parse_tradefed_testresult_xml_waivers(self):
        waived = tradefed_utils.parse_tradefed_testresults_xml(
                os.path.join(os.path.dirname(os.path.realpath(__file__)),
                             'tradefed_utils_unittest_data',
                             'gtsplacement_test_result.xml'))
        self.assertEquals(0, len(waived))

        waivers = set([
            'com.google.android.media.gts.WidevineDashPolicyTests#testL1RenewalDelay5S',
            'com.google.android.media.gts.MediaDrmTest#testWidevineApi28',
            'com.google.android.media.gts.WidevineGenericOpsTests#testL3',
            'com.google.android.media.gts.WidevineDashPolicyTests#testL3RenewalDelay5S',
            'com.google.android.media.gts.WidevineH264PlaybackTests#testCbc1L3WithUHD30',
            'com.google.android.media.gts.WidevineH264PlaybackTests#testCbcsL3WithUHD30',
            'com.google.android.media.gts.WidevineH264PlaybackTests#testCbc1L1WithUHD30',
            'com.google.android.media.gts.WidevineDashPolicyTests#testL3RenewalDelay13S',
            'com.google.android.gts.backup.BackupHostTest#testGmsBackupTransportIsDefault',
            'com.google.android.placement.gts.CoreGmsAppsTest#testGoogleDuoPreloaded',
            'com.google.android.placement.gts.CoreGmsAppsTest#testCoreGmsAppsPreloaded',
            'com.google.android.media.gts.WidevineH264PlaybackTests#testCbcsL1WithUHD30'])
        waived = tradefed_utils.parse_tradefed_testresults_xml(os.path.join(
                os.path.dirname(os.path.realpath(__file__)),
                'tradefed_utils_unittest_data',
                'gtsplacement_test_result.xml'),
                                                               waivers=waivers)
        self.assertEquals(4, len(waived))

    def test_get_perf_metrics_from_test_result_xml(self):
        perf_result = tradefed_utils.get_perf_metrics_from_test_result_xml(
            os.path.join(os.path.dirname(os.path.realpath(__file__)),
                         'tradefed_utils_unittest_data', 'test_result.xml'),
            os.path.join('/', 'resultsdir'))
        expected_result = [
            {'units': 'ms',
             'resultsdir': '/resultsdir/tests/CTS.CtsMediaTestCases.armeabi-v7a',
             'description': 'android.media.cts.AudioRecordTest'
                            '#testAudioRecordLocalMono16Bit',
             'value': '7.1688596491228065', 'higher_is_better': False},
            {'units': 'ms',
             'resultsdir': '/resultsdir/tests/CTS.CtsMediaTestCases.armeabi-v7a',
             'description': 'android.media.cts.AudioRecordTest'
                            '#testAudioRecordLocalMono16BitShort',
             'value': '2.5416666666666665', 'higher_is_better': False},
            {'units': 'ms',
             'resultsdir': '/resultsdir/tests/CTS.CtsMediaTestCases.armeabi-v7a',
             'description': 'android.media.cts.AudioRecordTest'
                            '#testAudioRecordLocalNonblockingStereoFloat',
             'value': '1.75', 'higher_is_better': False},
            {'units': 'ms',
             'resultsdir': '/resultsdir/tests/CTS.CtsMediaTestCases.armeabi-v7a',
             'description': 'android.media.cts.AudioRecordTest'
                            '#testAudioRecordMonoFloat',
             'value': '12.958881578947368', 'higher_is_better': False},
            {'units': 'ms',
             'resultsdir': '/resultsdir/tests/CTS.CtsMediaTestCases.armeabi-v7a',
             'description': 'android.media.cts.AudioRecordTest'
                            '#testAudioRecordResamplerMono8Bit',
             'value': '0.0', 'higher_is_better': False},
            {'units': 'ms',
             'resultsdir': '/resultsdir/tests/CTS.CtsMediaTestCases.armeabi-v7a',
             'description': 'android.media.cts.AudioRecordTest'
                            '#testAudioRecordResamplerStereo8Bit',
             'value': '3.5', 'higher_is_better': False},
            {'units': 'ms',
             'resultsdir': '/resultsdir/tests/CTS.CtsMediaTestCases.armeabi-v7a',
             'description': 'android.media.cts.AudioRecordTest'
                            '#testAudioRecordStereo16Bit',
             'value': '3.5', 'higher_is_better': False},
            {'units': 'ms',
             'resultsdir': '/resultsdir/tests/CTS.CtsMediaTestCases.armeabi-v7a',
             'description': 'android.media.cts.AudioTrackTest'
                            '#testFastTimestamp',
             'value': '0.1547618955373764', 'higher_is_better': False},
            {'units': 'ms',
             'resultsdir': '/resultsdir/tests/CTS.CtsMediaTestCases.armeabi-v7a',
             'description': 'android.media.cts.AudioTrackTest'
                            '#testGetTimestamp',
             'value': '0.1490119844675064', 'higher_is_better': False},
            {'units': 'ms',
             'resultsdir': '/resultsdir/tests/CTS.CtsMediaTestCases.armeabi-v7a',
             'description': 'android.media.cts.AudioTrack_ListenerTest'
                            '#testAudioTrackCallback',
             'value': '9.347127739984884', 'higher_is_better': False},
            {'units': 'ms',
             'resultsdir': '/resultsdir/tests/CTS.CtsMediaTestCases.armeabi-v7a',
             'description': 'android.media.cts.AudioTrack_ListenerTest'
                            '#testAudioTrackCallbackWithHandler',
             'value': '7.776177955844914', 'higher_is_better': False},
            {'units': 'ms',
             'resultsdir': '/resultsdir/tests/CTS.CtsMediaTestCases.armeabi-v7a',
             'description': 'android.media.cts.AudioTrack_ListenerTest'
                            '#testStaticAudioTrackCallback',
             'value': '7.776177955844914', 'higher_is_better': False},
            {'units': 'ms',
             'resultsdir': '/resultsdir/tests/CTS.CtsMediaTestCases.armeabi-v7a',
             'description': 'android.media.cts.AudioTrack_ListenerTest'
                            '#testStaticAudioTrackCallbackWithHandler',
             'value': '9.514361300075587', 'higher_is_better': False},
            {'units': 'count',
             'resultsdir': '/resultsdir/tests/CTS.CtsMediaTestCases.armeabi-v7a',
             'description': 'android.media.cts.DecoderTest'
                            '#testH264ColorAspects',
             'value': '1.0', 'higher_is_better': True},
            {'units': 'count',
             'resultsdir': '/resultsdir/tests/CTS.CtsMediaTestCases.armeabi-v7a',
             'description': 'android.media.cts.DecoderTest'
                            '#testH265ColorAspects',
             'value': '1.0', 'higher_is_better': True},
            {'units': 'fps',
             'resultsdir': '/resultsdir/tests/CTS.CtsMediaTestCases.armeabi-v7a',
             'description': 'android.media.cts.VideoDecoderPerfTest'
                            '#testAvcGoog0Perf0320x0240',
             'value': '580.1607045151507', 'higher_is_better': True},
            {'units': 'fps',
             'resultsdir': '/resultsdir/tests/CTS.CtsMediaTestCases.armeabi-v7a',
             'description': 'android.media.cts.VideoDecoderPerfTest'
                            '#testAvcGoog0Perf0720x0480',
             'value': '244.18184010611358', 'higher_is_better': True},
            {'units': 'fps',
             'resultsdir': '/resultsdir/tests/CTS.CtsMediaTestCases.armeabi-v7a',
             'description': 'android.media.cts.VideoDecoderPerfTest'
                            '#testAvcGoog0Perf1280x0720',
             'value': '70.96290491279275', 'higher_is_better': True},
            {'units': 'fps',
             'resultsdir': '/resultsdir/tests/CTS.CtsMediaTestCases.armeabi-v7a',
             'description': 'android.media.cts.VideoDecoderPerfTest'
                            '#testAvcGoog0Perf1920x1080',
             'value': '31.299613935451564', 'higher_is_better': True},
            {'units': 'fps',
             'resultsdir': '/resultsdir/tests/CTS.CtsMediaTestCases.armeabi-v7a',
             'description': 'android.media.cts.VideoDecoderPerfTest'
                            '#testAvcOther0Perf0320x0240',
             'value': '1079.6843075197307', 'higher_is_better': True},
            {'units': 'fps',
             'resultsdir': '/resultsdir/tests/CTS.CtsMediaTestCases.armeabi-v7a',
             'description': 'android.media.cts.VideoDecoderPerfTest'
                            '#testAvcOther0Perf0720x0480',
             'value': '873.7785366761784', 'higher_is_better': True},
            {'units': 'fps',
             'resultsdir': '/resultsdir/tests/CTS.CtsMediaTestCases.armeabi-v7a',
             'description': 'android.media.cts.VideoDecoderPerfTest'
                            '#testAvcOther0Perf1280x0720',
             'value': '664.6463289568261', 'higher_is_better': True},
            {'units': 'fps',
             'resultsdir': '/resultsdir/tests/CTS.CtsMediaTestCases.armeabi-v7a',
             'description': 'android.media.cts.VideoDecoderPerfTest'
                            '#testAvcOther0Perf1920x1080',
             'value': '382.10811352923474', 'higher_is_better': True},
            {'units': 'fps',
             'resultsdir': '/resultsdir/tests/CTS.CtsMediaTestCases.armeabi-v7a',
             'description': 'android.media.cts.VideoDecoderPerfTest'
                            '#testH263Goog0Perf0176x0144',
             'value': '1511.3027429644353', 'higher_is_better': True},
            {'units': 'fps',
             'resultsdir': '/resultsdir/tests/CTS.CtsMediaTestCases.armeabi-v7a',
             'description': 'android.media.cts.VideoDecoderPerfTest'
                            '#testHevcGoog0Perf0352x0288',
             'value': '768.8737453173384', 'higher_is_better': True},
            {'units': 'fps',
             'resultsdir': '/resultsdir/tests/CTS.CtsMediaTestCases.armeabi-v7a',
             'description': 'android.media.cts.VideoDecoderPerfTest'
                            '#testHevcGoog0Perf0640x0360',
             'value': '353.7226028743237', 'higher_is_better': True},
            {'units': 'fps',
             'resultsdir': '/resultsdir/tests/CTS.CtsMediaTestCases.armeabi-v7a',
             'description': 'android.media.cts.VideoDecoderPerfTest'
                            '#testHevcGoog0Perf0720x0480',
             'value': '319.3122874170939', 'higher_is_better': True},
            {'units': 'fps',
             'resultsdir': '/resultsdir/tests/CTS.CtsMediaTestCases.armeabi-v7a',
             'description': 'android.media.cts.VideoDecoderPerfTest'
                            '#testHevcGoog0Perf1280x0720',
             'value': '120.89218432028369', 'higher_is_better': True},
            {'units': 'fps',
             'resultsdir': '/resultsdir/tests/CTS.CtsMediaTestCases.armeabi-v7a',
             'description': 'android.media.cts.VideoDecoderPerfTest'
                            '#testMpeg4Goog0Perf0176x0144',
             'value': '1851.890822618321', 'higher_is_better': True},
            {'units': 'fps',
             'resultsdir': '/resultsdir/tests/CTS.CtsMediaTestCases.armeabi-v7a',
             'description': 'android.media.cts.VideoDecoderPerfTest'
                            '#testVp8Goog0Perf0320x0180',
             'value': '1087.946513466716', 'higher_is_better': True},
            {'units': 'fps',
             'resultsdir': '/resultsdir/tests/CTS.CtsMediaTestCases.armeabi-v7a',
             'description': 'android.media.cts.VideoDecoderPerfTest'
                            '#testVp8Goog0Perf0640x0360',
             'value': '410.18461316281423', 'higher_is_better': True},
            {'units': 'fps',
             'resultsdir': '/resultsdir/tests/CTS.CtsMediaTestCases.armeabi-v7a',
             'description': 'android.media.cts.VideoDecoderPerfTest'
                            '#testVp8Goog0Perf1920x1080',
             'value': '36.26433070651982', 'higher_is_better': True},
            {'units': 'fps',
             'resultsdir': '/resultsdir/tests/CTS.CtsMediaTestCases.armeabi-v7a',
             'description': 'android.media.cts.VideoDecoderPerfTest'
                            '#testVp8Other0Perf0320x0180',
             'value': '1066.7819511702078', 'higher_is_better': True},
            {'units': 'fps',
             'resultsdir': '/resultsdir/tests/CTS.CtsMediaTestCases.armeabi-v7a',
             'description': 'android.media.cts.VideoDecoderPerfTest'
                            '#testVp8Other0Perf0640x0360',
             'value': '930.261434505189', 'higher_is_better': True},
            {'units': 'fps',
             'resultsdir': '/resultsdir/tests/CTS.CtsMediaTestCases.armeabi-v7a',
             'description': 'android.media.cts.VideoDecoderPerfTest'
                            '#testVp8Other0Perf1280x0720',
             'value': '720.4170603577236', 'higher_is_better': True},
            {'units': 'fps',
             'resultsdir': '/resultsdir/tests/CTS.CtsMediaTestCases.armeabi-v7a',
             'description': 'android.media.cts.VideoDecoderPerfTest'
                            '#testVp8Other0Perf1920x1080',
             'value': '377.55742437554915', 'higher_is_better': True},
            {'units': 'fps',
             'resultsdir': '/resultsdir/tests/CTS.CtsMediaTestCases.armeabi-v7a',
             'description': 'android.media.cts.VideoDecoderPerfTest'
                            '#testVp9Goog0Perf0320x0180',
             'value': '988.6158776121617', 'higher_is_better': True},
            {'units': 'fps',
             'resultsdir': '/resultsdir/tests/CTS.CtsMediaTestCases.armeabi-v7a',
             'description': 'android.media.cts.VideoDecoderPerfTest'
                            '#testVp9Goog0Perf0640x0360',
             'value': '409.8162085338674', 'higher_is_better': True},
            {'units': 'fps',
             'resultsdir': '/resultsdir/tests/CTS.CtsMediaTestCases.armeabi-v7a',
             'description': 'android.media.cts.VideoDecoderPerfTest'
                            '#testVp9Goog0Perf1280x0720',
             'value': '147.75847359424512', 'higher_is_better': True},
            {'units': 'fps',
             'resultsdir': '/resultsdir/tests/CTS.CtsMediaTestCases.armeabi-v7a',
             'description': 'android.media.cts.VideoDecoderPerfTest'
                            '#testVp9Goog0Perf1920x1080',
             'value': '83.95677136649255', 'higher_is_better': True}
        ]
        self.assertListEqual(list(perf_result), expected_result)

        perf_result = tradefed_utils.get_perf_metrics_from_test_result_xml(
            os.path.join(os.path.dirname(os.path.realpath(__file__)),
                         'tradefed_utils_unittest_data',
                         'malformed_test_result.xml'),
            os.path.join('/', 'resultsdir'))
        self.assertListEqual(list(perf_result), [])

        # assertNoRaises
        tradefed_utils.get_perf_metrics_from_test_result_xml(
            os.path.join(os.path.dirname(os.path.realpath(__file__)),
                         'tradefed_utils_unittest_data',
                         'not_exist'),
            os.path.join('/', 'resultsdir'))

    def test_get_perf_metrics_from_test_result_xml_R(self):
        perf_result = tradefed_utils.get_perf_metrics_from_test_result_xml(
            os.path.join(os.path.dirname(os.path.realpath(__file__)),
                         'tradefed_utils_unittest_data', 'test_result_R.xml'),
            os.path.join('/', 'resultsdir'))
        expected_result = [
            {
                "description": "android.media.cts.VideoDecoderPerfTest#testAvcGoog0Perf0320x0240",
                "value": "425.9024873707386",
                "units": "fps",
                "higher_is_better": True,
                "resultsdir": "/resultsdir/tests/CTS.CtsMediaTestCases.x86"
            },
            {
                "description": "android.media.cts.VideoDecoderPerfTest#testAvcGoog0Perf0720x0480",
                "value": "195.4383682600072",
                "units": "fps",
                "higher_is_better": True,
                "resultsdir": "/resultsdir/tests/CTS.CtsMediaTestCases.x86"
            },
            {
                "description": "android.media.cts.VideoDecoderPerfTest#testAvcGoog0Perf1280x0720",
                "value": "69.20977482750216",
                "units": "fps",
                "higher_is_better": True,
                "resultsdir": "/resultsdir/tests/CTS.CtsMediaTestCases.x86"
            },
            {
                "description": "android.media.cts.VideoDecoderPerfTest#testAvcGoog0Perf1920x1080",
                "value": "30.958506313987364",
                "units": "fps",
                "higher_is_better": True,
                "resultsdir": "/resultsdir/tests/CTS.CtsMediaTestCases.x86"
            },
            {
                "description": "android.media.cts.VideoDecoderPerfTest#testAvcOther0Perf0320x0240",
                "value": "732.6894607825965",
                "units": "fps",
                "higher_is_better": True,
                "resultsdir": "/resultsdir/tests/CTS.CtsMediaTestCases.x86"
            },
            {
                "description": "android.media.cts.VideoDecoderPerfTest#testAvcOther0Perf0720x0480",
                "value": "703.3580092266964",
                "units": "fps",
                "higher_is_better": True,
                "resultsdir": "/resultsdir/tests/CTS.CtsMediaTestCases.x86"
            },
            {
                "description": "android.media.cts.VideoDecoderPerfTest#testAvcOther0Perf1280x0720",
                "value": "646.0737746134075",
                "units": "fps",
                "higher_is_better": True,
                "resultsdir": "/resultsdir/tests/CTS.CtsMediaTestCases.x86"
            },
            {
                "description": "android.media.cts.VideoDecoderPerfTest#testAvcOther0Perf1920x1080",
                "value": "500.47545167909516",
                "units": "fps",
                "higher_is_better": True,
                "resultsdir": "/resultsdir/tests/CTS.CtsMediaTestCases.x86"
            },
            {
                "description": "android.media.cts.VideoDecoderPerfTest#testH263Goog0Perf0176x0144",
                "value": "866.3879535015095",
                "units": "fps",
                "higher_is_better": True,
                "resultsdir": "/resultsdir/tests/CTS.CtsMediaTestCases.x86"
            },
            {
                "description": "android.media.cts.VideoDecoderPerfTest#testH263Goog0Perf0352x0288",
                "value": "701.2566519202411",
                "units": "fps",
                "higher_is_better": True,
                "resultsdir": "/resultsdir/tests/CTS.CtsMediaTestCases.x86"
            },
            {
                "description": "android.media.cts.VideoDecoderPerfTest#testMpeg4Goog0Perf0176x0144",
                "value": "634.7102407594098",
                "units": "fps",
                "higher_is_better": True,
                "resultsdir": "/resultsdir/tests/CTS.CtsMediaTestCases.x86"
            },
            {
                "description": "android.media.cts.VideoDecoderPerfTest#testVp8Goog0Perf0320x0180",
                "value": "243.09459418396185",
                "units": "fps",
                "higher_is_better": True,
                "resultsdir": "/resultsdir/tests/CTS.CtsMediaTestCases.x86"
            },
            {
                "description": "android.media.cts.VideoDecoderPerfTest#testVp8Goog0Perf0640x0360",
                "value": "306.8324031113812",
                "units": "fps",
                "higher_is_better": True,
                "resultsdir": "/resultsdir/tests/CTS.CtsMediaTestCases.x86"
            },
            {
                "description": "android.media.cts.VideoDecoderPerfTest#testVp8Goog0Perf1280x0720",
                "value": "81.58652553204992",
                "units": "fps",
                "higher_is_better": True,
                "resultsdir": "/resultsdir/tests/CTS.CtsMediaTestCases.x86"
            },
            {
                "description": "android.media.cts.VideoDecoderPerfTest#testVp8Goog0Perf1920x1080",
                "value": "45.01702462022001",
                "units": "fps",
                "higher_is_better": True,
                "resultsdir": "/resultsdir/tests/CTS.CtsMediaTestCases.x86"
            },
            {
                "description": "android.media.cts.VideoDecoderPerfTest#testVp8Other0Perf0320x0180",
                "value": "788.6545833041424",
                "units": "fps",
                "higher_is_better": True,
                "resultsdir": "/resultsdir/tests/CTS.CtsMediaTestCases.x86"
            },
            {
                "description": "android.media.cts.VideoDecoderPerfTest#testVp8Other0Perf0640x0360",
                "value": "778.0597173350103",
                "units": "fps",
                "higher_is_better": True,
                "resultsdir": "/resultsdir/tests/CTS.CtsMediaTestCases.x86"
            },
            {
                "description": "android.media.cts.VideoDecoderPerfTest#testVp8Other0Perf1280x0720",
                "value": "585.2903039907794",
                "units": "fps",
                "higher_is_better": True,
                "resultsdir": "/resultsdir/tests/CTS.CtsMediaTestCases.x86"
            },
            {
                "description": "android.media.cts.VideoDecoderPerfTest#testVp8Other0Perf1920x1080",
                "value": "489.2917301676426",
                "units": "fps",
                "higher_is_better": True,
                "resultsdir": "/resultsdir/tests/CTS.CtsMediaTestCases.x86"
            },
            {
                "description": "android.media.cts.VideoDecoderPerfTest#testVp9Goog0Perf0320x0180",
                "value": "429.4805887788435",
                "units": "fps",
                "higher_is_better": True,
                "resultsdir": "/resultsdir/tests/CTS.CtsMediaTestCases.x86"
            },
            {
                "description": "android.media.cts.VideoDecoderPerfTest#testVp9Goog0Perf0640x0360",
                "value": "295.2932473589899",
                "units": "fps",
                "higher_is_better": True,
                "resultsdir": "/resultsdir/tests/CTS.CtsMediaTestCases.x86"
            },
            {
                "description": "android.media.cts.VideoDecoderPerfTest#testVp9Goog0Perf1280x0720",
                "value": "129.55228137550378",
                "units": "fps",
                "higher_is_better": True,
                "resultsdir": "/resultsdir/tests/CTS.CtsMediaTestCases.x86"
            },
            {
                "description": "android.media.cts.VideoDecoderPerfTest#testVp9Goog0Perf1920x1080",
                "value": "81.9227263883342",
                "units": "fps",
                "higher_is_better": True,
                "resultsdir": "/resultsdir/tests/CTS.CtsMediaTestCases.x86"
            },
            {
                "description": "android.media.cts.VideoDecoderPerfTest#testVp9Other0Perf0320x0180",
                "value": "759.5628360615216",
                "units": "fps",
                "higher_is_better": True,
                "resultsdir": "/resultsdir/tests/CTS.CtsMediaTestCases.x86"
            },
            {
                "description": "android.media.cts.VideoDecoderPerfTest#testVp9Other0Perf0640x0360",
                "value": "728.6718354322686",
                "units": "fps",
                "higher_is_better": True,
                "resultsdir": "/resultsdir/tests/CTS.CtsMediaTestCases.x86"
            },
            {
                "description": "android.media.cts.VideoDecoderPerfTest#testVp9Other0Perf1280x0720",
                "value": "590.7816040621742",
                "units": "fps",
                "higher_is_better": True,
                "resultsdir": "/resultsdir/tests/CTS.CtsMediaTestCases.x86"
            },
            {
                "description": "android.media.cts.VideoDecoderPerfTest#testVp9Other0Perf1920x1080",
                "value": "540.6159009278734",
                "units": "fps",
                "higher_is_better": True,
                "resultsdir": "/resultsdir/tests/CTS.CtsMediaTestCases.x86"
            },
            {
                "description": "android.media.cts.VideoDecoderPerfTest#testVp9Other0Perf3840x2160",
                "value": "199.65106211355229",
                "units": "fps",
                "higher_is_better": True,
                "resultsdir": "/resultsdir/tests/CTS.CtsMediaTestCases.x86"
            },
            {
                "description": "android.media.cts.VideoDecoderPerfTest#testAvcGoog0Perf0320x0240",
                "value": "427.8822932887614",
                "units": "fps",
                "higher_is_better": True,
                "resultsdir": "/resultsdir/tests/CTS.CtsMediaTestCases.x86_64"
            },
            {
                "description": "android.media.cts.VideoDecoderPerfTest#testAvcGoog0Perf0720x0480",
                "value": "192.8731843665681",
                "units": "fps",
                "higher_is_better": True,
                "resultsdir": "/resultsdir/tests/CTS.CtsMediaTestCases.x86_64"
            },
            {
                "description": "android.media.cts.VideoDecoderPerfTest#testAvcGoog0Perf1280x0720",
                "value": "65.61155091353832",
                "units": "fps",
                "higher_is_better": True,
                "resultsdir": "/resultsdir/tests/CTS.CtsMediaTestCases.x86_64"
            },
            {
                "description": "android.media.cts.VideoDecoderPerfTest#testAvcGoog0Perf1920x1080",
                "value": "29.35891270785351",
                "units": "fps",
                "higher_is_better": True,
                "resultsdir": "/resultsdir/tests/CTS.CtsMediaTestCases.x86_64"
            },
            {
                "description": "android.media.cts.VideoDecoderPerfTest#testAvcOther0Perf0320x0240",
                "value": "666.5203328792977",
                "units": "fps",
                "higher_is_better": True,
                "resultsdir": "/resultsdir/tests/CTS.CtsMediaTestCases.x86_64"
            },
            {
                "description": "android.media.cts.VideoDecoderPerfTest#testAvcOther0Perf0720x0480",
                "value": "666.2911692409583",
                "units": "fps",
                "higher_is_better": True,
                "resultsdir": "/resultsdir/tests/CTS.CtsMediaTestCases.x86_64"
            },
            {
                "description": "android.media.cts.VideoDecoderPerfTest#testAvcOther0Perf1280x0720",
                "value": "603.2106437620304",
                "units": "fps",
                "higher_is_better": True,
                "resultsdir": "/resultsdir/tests/CTS.CtsMediaTestCases.x86_64"
            },
            {
                "description": "android.media.cts.VideoDecoderPerfTest#testAvcOther0Perf1920x1080",
                "value": "476.8903935199129",
                "units": "fps",
                "higher_is_better": True,
                "resultsdir": "/resultsdir/tests/CTS.CtsMediaTestCases.x86_64"
            },
            {
                "description": "android.media.cts.VideoDecoderPerfTest#testH263Goog0Perf0176x0144",
                "value": "883.5886924690593",
                "units": "fps",
                "higher_is_better": True,
                "resultsdir": "/resultsdir/tests/CTS.CtsMediaTestCases.x86_64"
            },
            {
                "description": "android.media.cts.VideoDecoderPerfTest#testH263Goog0Perf0352x0288",
                "value": "464.87116856989996",
                "units": "fps",
                "higher_is_better": True,
                "resultsdir": "/resultsdir/tests/CTS.CtsMediaTestCases.x86_64"
            },
            {
                "description": "android.media.cts.VideoDecoderPerfTest#testMpeg4Goog0Perf0176x0144",
                "value": "970.5570997752711",
                "units": "fps",
                "higher_is_better": True,
                "resultsdir": "/resultsdir/tests/CTS.CtsMediaTestCases.x86_64"
            },
            {
                "description": "android.media.cts.VideoDecoderPerfTest#testVp8Goog0Perf0320x0180",
                "value": "637.9051874610072",
                "units": "fps",
                "higher_is_better": True,
                "resultsdir": "/resultsdir/tests/CTS.CtsMediaTestCases.x86_64"
            },
            {
                "description": "android.media.cts.VideoDecoderPerfTest#testVp8Goog0Perf0640x0360",
                "value": "334.0251231028025",
                "units": "fps",
                "higher_is_better": True,
                "resultsdir": "/resultsdir/tests/CTS.CtsMediaTestCases.x86_64"
            },
            {
                "description": "android.media.cts.VideoDecoderPerfTest#testVp8Goog0Perf1280x0720",
                "value": "103.80291555179312",
                "units": "fps",
                "higher_is_better": True,
                "resultsdir": "/resultsdir/tests/CTS.CtsMediaTestCases.x86_64"
            },
            {
                "description": "android.media.cts.VideoDecoderPerfTest#testVp8Goog0Perf1920x1080",
                "value": "44.59363040799118",
                "units": "fps",
                "higher_is_better": True,
                "resultsdir": "/resultsdir/tests/CTS.CtsMediaTestCases.x86_64"
            },
            {
                "description": "android.media.cts.VideoDecoderPerfTest#testVp8Other0Perf0320x0180",
                "value": "792.2834992688155",
                "units": "fps",
                "higher_is_better": True,
                "resultsdir": "/resultsdir/tests/CTS.CtsMediaTestCases.x86_64"
            },
            {
                "description": "android.media.cts.VideoDecoderPerfTest#testVp8Other0Perf0640x0360",
                "value": "757.2995259865929",
                "units": "fps",
                "higher_is_better": True,
                "resultsdir": "/resultsdir/tests/CTS.CtsMediaTestCases.x86_64"
            },
            {
                "description": "android.media.cts.VideoDecoderPerfTest#testVp8Other0Perf1280x0720",
                "value": "601.25953332624",
                "units": "fps",
                "higher_is_better": True,
                "resultsdir": "/resultsdir/tests/CTS.CtsMediaTestCases.x86_64"
            },
            {
                "description": "android.media.cts.VideoDecoderPerfTest#testVp8Other0Perf1920x1080",
                "value": "525.906136272798",
                "units": "fps",
                "higher_is_better": True,
                "resultsdir": "/resultsdir/tests/CTS.CtsMediaTestCases.x86_64"
            },
            {
                "description": "android.media.cts.VideoDecoderPerfTest#testVp9Goog0Perf0320x0180",
                "value": "542.4610919281389",
                "units": "fps",
                "higher_is_better": True,
                "resultsdir": "/resultsdir/tests/CTS.CtsMediaTestCases.x86_64"
            },
            {
                "description": "android.media.cts.VideoDecoderPerfTest#testVp9Goog0Perf0640x0360",
                "value": "297.242175049532",
                "units": "fps",
                "higher_is_better": True,
                "resultsdir": "/resultsdir/tests/CTS.CtsMediaTestCases.x86_64"
            },
            {
                "description": "android.media.cts.VideoDecoderPerfTest#testVp9Goog0Perf1280x0720",
                "value": "126.7377006131063",
                "units": "fps",
                "higher_is_better": True,
                "resultsdir": "/resultsdir/tests/CTS.CtsMediaTestCases.x86_64"
            },
            {
                "description": "android.media.cts.VideoDecoderPerfTest#testVp9Goog0Perf1920x1080",
                "value": "81.32502869248668",
                "units": "fps",
                "higher_is_better": True,
                "resultsdir": "/resultsdir/tests/CTS.CtsMediaTestCases.x86_64"
            },
            {
                "description": "android.media.cts.VideoDecoderPerfTest#testVp9Other0Perf0320x0180",
                "value": "765.775066604389",
                "units": "fps",
                "higher_is_better": True,
                "resultsdir": "/resultsdir/tests/CTS.CtsMediaTestCases.x86_64"
            },
            {
                "description": "android.media.cts.VideoDecoderPerfTest#testVp9Other0Perf0640x0360",
                "value": "703.1828275351592",
                "units": "fps",
                "higher_is_better": True,
                "resultsdir": "/resultsdir/tests/CTS.CtsMediaTestCases.x86_64"
            },
            {
                "description": "android.media.cts.VideoDecoderPerfTest#testVp9Other0Perf1280x0720",
                "value": "529.7877944503476",
                "units": "fps",
                "higher_is_better": True,
                "resultsdir": "/resultsdir/tests/CTS.CtsMediaTestCases.x86_64"
            },
            {
                "description": "android.media.cts.VideoDecoderPerfTest#testVp9Other0Perf1920x1080",
                "value": "529.8971158170783",
                "units": "fps",
                "higher_is_better": True,
                "resultsdir": "/resultsdir/tests/CTS.CtsMediaTestCases.x86_64"
            },
            {
                "description": "android.media.cts.VideoDecoderPerfTest#testVp9Other0Perf3840x2160",
                "value": "201.03995239697207",
                "units": "fps",
                "higher_is_better": True,
                "resultsdir": "/resultsdir/tests/CTS.CtsMediaTestCases.x86_64"
            }
        ]
        self.assertListEqual(list(perf_result), expected_result)

if __name__ == '__main__':
    unittest.main()
