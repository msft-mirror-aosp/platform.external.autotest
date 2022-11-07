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

    @mock.patch('subprocess.check_call')
    def test_fetch_artifact_argument(self, check_call_mock):
        """Test for argument of fetch_artifact."""

        uprev_preview_version_common.fetch_artifact(
                download_dir='test_dir',
                branch_name='test_branch',
                target_name='test_target',
                xts_name='cts',
                version_name='test_version')
        args, kwargs = check_call_mock.call_args
        fetch_cmd = args[0]
        # fetch_cmd needs --branch, --target, file_name, and --bid options,
        # so its length must be greater than or equal to 5 including command itself.
        self.assertGreaterEqual(len(fetch_cmd), 5)
        self.assertEquals('fetch_artifact', fetch_cmd[0])
        self.assertEquals(
                set([
                        '--branch=test_branch', '--target=test_target',
                        'android-cts.zip', '--bid=test_version'
                ]), set(fetch_cmd[1:]))
