# Lint as: python2, python3
# Copyright 2022 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.


from autotest_lib.client.cros.tast.ui import tconn_service_pb2


def make_current_screen_fullscreen(tconn_service, call_on_lacros=False):
    """Makes the current Chrome screen fullscreen.

    @param tconn_service: tconn_service instance connected to Chrome.
    """
    tconn_service.Eval(tconn_service_pb2.EvalRequest(
        expr='''(async () => {
            let window_id = await new Promise(
                (resolve) => chrome.windows.getCurrent({},
                (window) => resolve(window.id))
            )
            await new Promise(
                (resolve) => chrome.windows.update(
                    window_id, { state: 'fullscreen' },
                    resolve));
        })()'''),
        call_on_lacros=call_on_lacros)
