# Lint as: python2, python3
# Copyright 2022 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# Sets relative import path.
# Please refer https://github.com/protocolbuffers/protobuf/issues/1491#issuecomment-547504972

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))
