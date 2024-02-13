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
        self.exe_rel_path = args_dict.get('exe_rel_path', '')
        self.server_pkg = tempfile.mkdtemp()
        self.executable = os.path.join(self.server_pkg, self.exe_rel_path)
        self.test_args = chrome_sideloader.get_test_args(
                args_dict, 'test_args')

        with tempfile.TemporaryDirectory() as tmp_archive_dir:
            archive_file_path = chrome_sideloader.download_gs(
                    args_dict.get('lacros_gcs_path'), tmp_archive_dir)
            chrome_sideloader.unsquashfs(archive_file_path, self.server_pkg)
            cmd = ['chmod', '-R', '755', self.server_pkg]
            try:
                utils.run(cmd, stdout_tee=sys.stdout, stderr_tee=sys.stderr)
            except error.CmdError as e:
                raise Exception('Error changing file permissions', e)

        self.shard_number = args_dict.get('shard_number', 1)
        self.shard_index = args_dict.get('shard_index', 0)
        self.max_run_sec = int(args_dict.get('max_run_sec', 3600))

    def cleanup(self):
        shutil.rmtree(self.server_pkg)

    def run_once(self):
        cmd = ' '.join([
                'vpython3',
                '-vpython-spec',
                f'{self.server_pkg}/.vpython3',
                self.executable,
                '--test-launcher-summary-output',
                f'{self.resultsdir}/output.json',
                '--test-launcher-shard-index',
                f'{self.shard_index}',
                '--test-launcher-total-shards',
                f'{self.shard_number}',
                '--device',
                self.host.hostname,
                '--board',
                self.host.host_info_store.get().board,
                '--path-to-outdir',
                f'{self.server_pkg}/out/Release',
        ])
        if self.test_args:
            cmd += ' ' + self.test_args
        logging.debug('Running: %s', cmd)
        exit_code = 0
        try:
            result = utils.run(cmd,
                               stdout_tee=sys.stdout,
                               stderr_tee=sys.stderr,
                               timeout=self.max_run_sec,
                               extra_paths=['/opt/infra-tools'])
            exit_code = result.exit_status
        except error.CmdError as e:
            logging.debug('Error occurred executing gtest tests.')
            exit_code = e.result_obj.exit_status

        if exit_code:
            raise error.TestFail(
                    f'Chromium Test failed to run. Exit code: {exit_code}')
