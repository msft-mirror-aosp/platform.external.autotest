# Copyright 2021 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import logging
import os
import sys
import tempfile
import shutil

from autotest_lib.client.common_lib import error
from autotest_lib.client.common_lib import utils
from autotest_lib.server import test

from autotest_lib.server.cros import chrome_sideloader


class chromium(test.test):
    """Run Chromium tests built on a Skylab DUT."""

    version = 1

    def initialize(self, host=None, args=None):
        self.host = host
        args_dict = utils.args_to_dict(args)
        self.server_pkg = tempfile.mkdtemp()
        self.exe_rel_path = args_dict.get('exe_rel_path', '')
        self.build_dir = f'{self.server_pkg}/out/Release'
        if self.exe_rel_path:
            # FIXME: This assumes the build-dir is nested two dirs within the
            # checkout. This is not strictly a safe assumption. The build-dir
            # should be properly propagated to Skylab from Chrome builders.
            parts = self.exe_rel_path.split(os.sep)
            if len(parts) > 2:
                self.build_dir = os.path.join(*parts[:2])
        self.executable = os.path.join(self.server_pkg, self.exe_rel_path)
        self.test_args = chrome_sideloader.get_test_args(
                args_dict, 'test_args')

        with tempfile.TemporaryDirectory() as tmp_archive_dir:
            archive_file_path = chrome_sideloader.download_gs(
                    args_dict.get('lacros_gcs_path'), tmp_archive_dir)
            chrome_sideloader.unarchive(archive_file_path, self.server_pkg,
                                        **args_dict)
            cmd = ['chmod', '-R', '755', self.server_pkg]
            try:
                utils.run(cmd, stdout_tee=sys.stdout, stderr_tee=sys.stderr)
            except error.CmdError as e:
                raise Exception('Error changing file permissions', e)

        self._total_shards = args_dict.get('total_shards', 1)
        # Leaves the check to ensure no code uses "shard_number".
        # TODO: Remove this after we see no failure for a while.
        if 'shard_number' in args_dict:
            raise Exception('Should use "total_shards" instead of "shard_number".', e)

        self.shard_index = args_dict.get('shard_index', 0)
        self.max_run_sec = int(args_dict.get('max_run_sec', 3600))

    def cleanup(self):
        shutil.rmtree(self.server_pkg)

    def run_once(self):
        cmd = [
                'vpython3',
                '-vpython-spec',
                f'{self.server_pkg}/.vpython3',
                self.executable,
                '--test-launcher-summary-output',
                f'{self.resultsdir}/output.json',
                '--test-launcher-shard-index',
                f'{self.shard_index}',
                '--test-launcher-total-shards',
                f'{self._total_shards}',
                '--board',
                self.host.host_info_store.get().board,
                '--path-to-outdir',
                self.build_dir,
        ]
        if self.host.port:
            cmd.extend(['--device', f'{self.host.hostname}:{self.host.port}'])
        else:
            cmd.extend(['--device', self.host.hostname])
        cmd_str = (' ').join(cmd)
        # Test args from chromium builders are unknown to the autotest wrapper,
        # so just append whatever received here to the command string.
        if self.test_args:
            cmd_str += ' ' + self.test_args
        logging.info('Running: %s', cmd_str)
        exit_code = 0
        try:
            result = utils.run(
                    cmd_str,
                    stdout_tee=sys.stdout,
                    stderr_tee=sys.stderr,
                    timeout=self.max_run_sec,
                    extra_paths=['/opt/infra-tools', '/opt/browser-tools'])
            exit_code = result.exit_status
        except error.CmdError as e:
            logging.debug('Error occurred executing gtest tests.')
            exit_code = e.result_obj.exit_status

        if exit_code:
            raise error.TestFail(
                    f'Chromium Test failed to run. Exit code: {exit_code}')
