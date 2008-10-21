#
# Copyright 2008 Google Inc. All Rights Reserved.
#

import os, getpass
from autotest_lib.frontend.afe import rpc_client_lib
from autotest_lib.frontend.afe.json_rpc import proxy

AFE_RPC_PATH = "/afe/server/noauth/rpc/"
TKO_RPC_PATH = "/new_tko/server/noauth/rpc/"

def get_autotest_server(web_server=None):
    if not web_server:
        if 'AUTOTEST_WEB' in os.environ:
            web_server = os.environ['AUTOTEST_WEB']
        else:
            web_server = 'http://autotest'

    # if the name doesn't start with http://,
    # nonexistant hosts get an obscure error
    if not web_server.startswith('http://'):
        web_server = 'http://' + web_server

    return web_server


class rpc_comm(object):
    """Shared AFE/TKO RPC class stuff"""
    def __init__(self, web_server, rpc_path):
        self.web_server = get_autotest_server(web_server)
        self.proxy = self._connect(rpc_path)

    def _connect(self, rpc_path):
        # This does not fail even if the address is wrong.
        # We need to wait for an actual RPC to fail
        headers = {'AUTHORIZATION' : getpass.getuser()}
        rpc_server = self.web_server + rpc_path
        return rpc_client_lib.get_proxy(rpc_server, headers=headers)


    def run(self, op, *args, **data):
        function = getattr(self.proxy, op)
        return function(*args, **data)


class afe_comm(rpc_comm):
    """Handles the AFE setup and communication through RPC"""
    def __init__(self, web_server=None, rpc_path=AFE_RPC_PATH):
        super(afe_comm, self).__init__(web_server, rpc_path)


class tko_comm(rpc_comm):
    """Handles the TKO setup and communication through RPC"""
    def __init__(self, web_server=None, rpc_path=TKO_RPC_PATH):
        super(tko_comm, self).__init__(web_server, rpc_path)
