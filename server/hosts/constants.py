# Lint as: python2, python3
# Copyright (c) 2021 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
#
# Expects to be run in an environment with sudo and no interactive password
# prompt, such as within the Chromium OS development chroot.

# Default docker socker.
DOCKER_SOCKET = '/var/run/docker.sock'

# Optional docker tcp ip address/port dockerd listens to.
DOCKER_TCP_SERVER_IP = '192.168.231.1'
DOCKER_TCP_SERVER_PORT = '2375'
