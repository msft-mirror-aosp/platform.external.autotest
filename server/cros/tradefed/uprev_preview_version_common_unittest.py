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
                '1000\n100\n10\n2\n1', '100\n99\n11\n2\n1'
        ]
        common_latest_version = uprev_preview_version_common.get_latest_version_name(
                branch_name='test',
                abi_list={
                        "arm": "test_suites_arm64",
                        "x86": "test_suites_x86_64"
                })
        self.assertEquals('100', common_latest_version)

    @mock.patch('subprocess.check_output')
    def test_get_latest_version_name_no_common_version(self,
                                                       check_output_mock):
        """Test for build error of get_latest_version_name.

        If the latest 5 version numbers do not have common version number,
        it raises a GreenBuildNotFoundException.
        """

        check_output_mock.side_effect = [
                '1000\n100\n10\n2\n1', '1001\n101\n11\n4\n3'
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

        check_output_mock.return_value = b'gs://android-build/builds/test_branch-linux-test_target/9199760/mock_hash/\n'

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
                'gs://android-build/builds/test_branch-linux-test_target/9199760/'
        ])

        check_call_mock.assert_any_call([
                'gsutil',
                'cp',
                'gs://android-build/builds/test_branch-linux-test_target/9199760/mock_hash/android-cts.zip',
                'gs://chromeos-partner-gts/R/android-cts-9199760-linux_x86-arm.zip',
        ])

        check_call_mock.assert_any_call([
                'gsutil',
                'cp',
                'gs://android-build/builds/test_branch-linux-test_target/9199760/mock_hash/android-cts.zip',
                'gs://chromeos-arc-images/cts/bundle/R/android-cts-9199760-linux_x86-arm.zip',
        ])
