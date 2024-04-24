import pathlib
import sys
import unittest
from unittest import mock

sys.path.append('server/cros/tradefed')
from autotest_lib.server.cros.tradefed import uprev_preview_version_common


class UprevPreviewVersionCommonTest(unittest.TestCase):
    """Unittest for uprev_preview_version_common_unittest."""

    @mock.patch('subprocess.check_output')
    def test_get_latest_version_name(self, check_output_mock):
        """Test for get_latest_version_name."""

        check_output_mock.side_effect = [
                b'1000\n100\n10\n2\n1', b'100\n99\n11\n2\n1'
        ]
        common_latest_version = uprev_preview_version_common.get_latest_version_name(
                branch_name='test',
                abi_list={
                        "arm": "test_suites_arm64",
                        "x86": "test_suites_x86_64"
                })
        self.assertEqual('100', common_latest_version)

    @mock.patch('subprocess.check_output')
    def test_get_latest_version_name_no_common_version(self,
                                                       check_output_mock):
        """Test for build error of get_latest_version_name.

        If the latest 5 version numbers do not have common version number,
        it raises a GreenBuildNotFoundException.
        """

        check_output_mock.side_effect = [
                b'1000\n100\n10\n2\n1', b'1001\n101\n11\n4\n3'
        ]
        with self.assertRaises(
                uprev_preview_version_common.GreenBuildNotFoundException):
            common_latest_version = uprev_preview_version_common.get_latest_version_name(
                    branch_name='test',
                    abi_list={
                            "arm": "test_suites_arm64",
                            "x86": "test_suites_x86_64"
                    })

    @mock.patch('subprocess.check_output')
    @mock.patch('subprocess.check_call')
    def test_upload_preview_xts(self, check_call_mock, check_output_mock):
        """Verify that gsutil cp is called with the right flags."""

        _TEST_CONFIG = {
                "public_base": "https://dl.google.com/dl/android/cts/",
                "internal_base": "gs://chromeos-arc-images/cts/bundle/R/",
                "partner_base": "gs://chromeos-partner-gts/R/",
                "official_url_pattern": "android-cts-%s-linux_x86-%s.zip",
                "preview_url_pattern": "android-cts-%s-linux_x86-%s.zip",
                "official_version_name": "11_r9",
                "preview_version_name": "9199760",
                "abi_list": {
                        "arm": "test_suites_arm64",
                        "x86": "test_suites_x86_64"
                }
        }

        check_output_mock.return_value = b'gs://android-build-chromeos/builds/test_branch-linux-test_target/9199760/mock_hash/\n'

        uprev_preview_version_common.upload_preview_xts(
                branch_name='test_branch',
                target_name='test_target',
                url_config=_TEST_CONFIG,
                abi='arm',
                xts_name='cts',
                version_name='9199760',
        )

        self.assertEquals(check_output_mock.call_count, 1)
        self.assertEquals(check_call_mock.call_count, 2)
        check_output_mock.assert_called_once_with([
                'gsutil', 'ls',
                'gs://android-build-chromeos/builds/test_branch-linux-test_target/9199760/'
        ])

        check_call_mock.assert_any_call([
                'gsutil',
                'cp',
                'gs://android-build-chromeos/builds/test_branch-linux-test_target/9199760/mock_hash/android-cts.zip',
                'gs://chromeos-partner-gts/R/android-cts-9199760-linux_x86-arm.zip',
        ])

        check_call_mock.assert_any_call([
                'gsutil',
                'cp',
                'gs://android-build-chromeos/builds/test_branch-linux-test_target/9199760/mock_hash/android-cts.zip',
                'gs://chromeos-arc-images/cts/bundle/R/android-cts-9199760-linux_x86-arm.zip',
        ])

    @mock.patch('subprocess.check_call')
    def test_upload_preview_xts_gts(self, check_call_mock):
        """Tests if upload_preview_xts works with GTS bundles."""

        _TEST_CONFIG = {
                "internal_base": "gs://chromeos-arc-images/cts/bundle/",
                "partner_base": "gs://chromeos-partner-gts/",
                "official_url_pattern": "android-gts-%s.zip",
                "preview_url_pattern": "android-gts-%s.zip",
                "preview_version_name": "11-R4-R-Preview4-11561875",
        }

        uprev_preview_version_common.upload_preview_xts(
                branch_name='test_branch',
                target_name='test_target',
                url_config=_TEST_CONFIG,
                abi=None,
                xts_name='gts',
                version_name="11-R4-R-Preview4-11561875",
                local_file=pathlib.Path(
                        '/path/to/android-gts-11-R4-R-Preview4-11561875.zip'),
        )

        check_call_mock.assert_has_calls([
                mock.call([
                        'gsutil', 'cp',
                        '/path/to/android-gts-11-R4-R-Preview4-11561875.zip',
                        'gs://chromeos-arc-images/cts/bundle/android-gts-11-R4-R-Preview4-11561875.zip'
                ]),
                mock.call([
                        'gsutil', 'cp',
                        'gs://chromeos-arc-images/cts/bundle/android-gts-11-R4-R-Preview4-11561875.zip',
                        'gs://chromeos-partner-gts/android-gts-11-R4-R-Preview4-11561875.zip'
                ]),
        ])

    def test_get_gts_version_name(self):
        """Tests if get_gts_version_name returns the correct version name."""
        path = pathlib.Path(
                '/path/to/android-gts-11-R4-R-Preview4-11561875.zip')

        version_name = uprev_preview_version_common.get_gts_version_name(path)
        self.assertEqual(version_name, '11-R4-R-Preview4-11561875')

    def test_get_gts_version_name_invalid_format(self):
        """Tests if get_gts_version_name raises ValueError when name is invalid."""
        path = pathlib.Path(
                '/path/to/android-gts-11-R4(11-14)-Preview4-11561875.zip')

        with self.assertRaises(ValueError):
            uprev_preview_version_common.get_gts_version_name(path)
