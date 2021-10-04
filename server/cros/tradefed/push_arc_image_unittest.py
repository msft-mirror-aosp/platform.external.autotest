# Copyright 2021 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import unittest
from mock import Mock, ANY, call

from autotest_lib.server.cros.tradefed import push_arc_image


class PushArcImageTest(unittest.TestCase):
    """Unittest for push_arc_image."""

    def test_push_userdebug_image_x86_64(self):
        mock_host = Mock()
        mock_host.get_arc_version.return_value = '7750398'
        mock_host.get_arc_primary_abi.return_value = 'x86_64'
        mock_host.host_port = 'somehost:9384'

        mock_download_func = Mock()
        mock_download_func.side_effect = ['bertha_img.zip', 'sepolicy.zip']

        mock_install_bundle_func = Mock()
        mock_install_bundle_func.return_value = 'some/extracted/dir'

        mock_run_func = Mock()

        in_sequence = Mock()
        in_sequence.attach_mock(mock_run_func, 'run')
        in_sequence.attach_mock(mock_host.run, 'host_run')

        push_arc_image.push_userdebug_image(mock_host, mock_download_func,
                                            mock_install_bundle_func,
                                            mock_run_func)

        mock_host.get_arc_version.assert_called_once()
        mock_host.get_arc_primary_abi.assert_called_once()
        mock_download_func.assert_any_call(
                'gs://chromeos-arc-images/builds/'
                'git_rvc-arc-*linux-bertha_x86_64-userdebug/'
                '7750398/bertha_x86_64-img-7750398.zip')

        mock_download_func.assert_any_call(
                'gs://chromeos-arc-images/builds/'
                'git_rvc-arc-*linux-bertha_x86_64-userdebug/'
                '7750398/sepolicy.zip')

        mock_install_bundle_func.assert_any_call(
                'gs://chromeos-arc-images/builds/'
                'git_rvc-arc-*linux-bertha_x86_64-userdebug/'
                '7750398/push_to_device.zip')

        # Expect force provisioning marker then push_to_device.
        expected_calls = [
                call.host_run(
                        'touch /mnt/stateful_partition/.force_provision'),
                call.run(
                        'some/extracted/dir/push_to_device.py',
                        args=[
                                '--use-prebuilt-file',
                                'bertha_img.zip',
                                '--sepolicy-artifacts-path',
                                'sepolicy.zip',
                                '--force',
                                'somehost:9384',
                        ],
                        ignore_status=ANY,
                        verbose=ANY,
                        nickname=ANY,
                ),
        ]
        self.assertEqual(in_sequence.mock_calls, expected_calls)

    # Verify that it works for ARM64.
    def test_push_userdebug_image_arm64(self):
        mock_host = Mock()
        mock_host.get_arc_version.return_value = '7750398'
        mock_host.get_arc_primary_abi.return_value = 'arm64-v8a'
        mock_host.host_port = 'somehost:9384'

        mock_download_func = Mock()
        mock_download_func.side_effect = ['bertha_img.zip', 'sepolicy.zip']

        mock_install_bundle_func = Mock()
        mock_install_bundle_func.return_value = 'some/extracted/dir'

        mock_run_func = Mock()

        in_sequence = Mock()
        in_sequence.attach_mock(mock_run_func, 'run')
        in_sequence.attach_mock(mock_host.run, 'host_run')

        push_arc_image.push_userdebug_image(mock_host, mock_download_func,
                                            mock_install_bundle_func,
                                            mock_run_func)

        mock_host.get_arc_version.assert_called_once()
        mock_host.get_arc_primary_abi.assert_called_once()
        mock_download_func.assert_any_call(
                'gs://chromeos-arc-images/builds/'
                'git_rvc-arc-*linux-bertha_arm64-userdebug/'
                '7750398/bertha_arm64-img-7750398.zip')

        mock_download_func.assert_any_call(
                'gs://chromeos-arc-images/builds/'
                'git_rvc-arc-*linux-bertha_arm64-userdebug/'
                '7750398/sepolicy.zip')

        mock_install_bundle_func.assert_any_call(
                'gs://chromeos-arc-images/builds/'
                'git_rvc-arc-*linux-bertha_arm64-userdebug/'
                '7750398/push_to_device.zip')

        # Expect force provisioning marker then push_to_device.
        expected_calls = [
                call.host_run(
                        'touch /mnt/stateful_partition/.force_provision'),
                call.run(
                        'some/extracted/dir/push_to_device.py',
                        args=[
                                '--use-prebuilt-file',
                                'bertha_img.zip',
                                '--sepolicy-artifacts-path',
                                'sepolicy.zip',
                                '--force',
                                'somehost:9384',
                        ],
                        ignore_status=ANY,
                        verbose=ANY,
                        nickname=ANY,
                ),
        ]
        self.assertEqual(in_sequence.mock_calls, expected_calls)

    # Only newer push to device has support for HOST:PORT format.
    # Verify that the if the build ID on the device is old, it
    # downloads a newer ptd.py that has the necessary features.
    def test_push_userdebug_image_old_image(self):
        mock_host = Mock()

        # Arbitrary, but small enough.
        mock_host.get_arc_version.return_value = '5985921'
        mock_host.get_arc_primary_abi.return_value = 'x86_64'
        mock_host.host_port = 'somehost:9384'

        mock_download_func = Mock()
        mock_download_func.side_effect = ['bertha_img.zip', 'sepolicy.zip']

        mock_install_bundle_func = Mock()
        mock_install_bundle_func.return_value = 'some/extracted/dir'

        mock_run_func = Mock()
        push_arc_image.push_userdebug_image(mock_host, mock_download_func,
                                            mock_install_bundle_func,
                                            mock_run_func)

        mock_host.get_arc_version.assert_called_once()
        mock_host.get_arc_primary_abi.assert_called_once()
        mock_download_func.assert_any_call(
                'gs://chromeos-arc-images/builds/'
                'git_rvc-arc-*linux-bertha_x86_64-userdebug/'
                '5985921/bertha_x86_64-img-5985921.zip')

        mock_download_func.assert_any_call(
                'gs://chromeos-arc-images/builds/'
                'git_rvc-arc-*linux-bertha_x86_64-userdebug/'
                '5985921/sepolicy.zip')

        mock_install_bundle_func.assert_any_call(
                'gs://chromeos-arc-images/builds/'
                'git_rvc-arc-*linux-bertha_x86_64-userdebug/'
                '7744997/push_to_device.zip')

        mock_host.run.assert_called_once_with(
                'touch /mnt/stateful_partition/.force_provision')

        mock_run_func.assert_called_with(
                'some/extracted/dir/push_to_device.py',
                args=[
                        '--use-prebuilt-file',
                        'bertha_img.zip',
                        '--sepolicy-artifacts-path',
                        'sepolicy.zip',
                        '--force',
                        'somehost:9384',
                ],
                ignore_status=ANY,
                verbose=ANY,
                nickname=ANY,
        )
