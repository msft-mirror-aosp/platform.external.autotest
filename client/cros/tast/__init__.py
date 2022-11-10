# Lint as: python2, python3
# Copyright 2022 The ChromiumOS Authors.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import logging
import os
import subprocess

import grpc

from google.protobuf import empty_pb2
from autotest_lib.client.cros.tast.ui import chrome_service_pb2_grpc

# An arbitrary port number.
_TCP_PORT = 23456


class GRPC:
    """Wraps Tast gRPC APIs."""

    def __init__(self, bundle_path=None):
        if bundle_path is None:
            bundle_path = '/usr/local/libexec/tast/bundles/local/cros'
        self._bundle_path = bundle_path

    def __enter__(self):
        # Currently, there's no way to create gRPC service client from an FD.
        # So, instead, we use the on-device TCP connection with a fixed port.
        # cf) https://github.com/grpc/grpc/issues/23760
        # TODO(crbug.com/1382287): Handle the case where the TCP port is
        # occupied.
        self._process = subprocess.Popen(
            [self._bundle_path, '-rpctcp', '-port', str(_TCP_PORT)],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        self._channel = grpc.insecure_channel('localhost:%d' % _TCP_PORT)
        # Wait until the channel gets available before returning.
        # 30 secs should be long enough that tast gRPC is set up.
        try:
            grpc.channel_ready_future(self._channel).result(timeout=30)
        except e:
            logging.error(
                'Process: ' + self._process.stdout.read().decode('utf-8'))
            raise e
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._channel.close()
        self._process.kill()
        self._process.wait()

    @property
    def channel(self):
        return self._channel


class ChromeService(chrome_service_pb2_grpc.ChromeServiceStub):
    """Wraps ChromeServiceStub to close Chrome on exit."""

    def __init__(self, channel):
        super().__init__(channel)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Close makes the tast bundle disconnects from Chrome and cleans up
        # standard extensions. However it does not terminate Chrome. See Close()
        # on tast-tests/src/chromiumos/tast/local/chrome/chrome.go.
        self.Close(empty_pb2.Empty())
        # Restart ui (and thus Chrome). Do this to make the behaviour consistent
        # with autotest Chrome.
        self._restart_ui()

    def _restart_ui(self):
        logging.info('(Re)starting the ui (logs the user out)')

        subprocess.run(['stop', 'ui'])
        subprocess.run(['start', 'ui'])
