"""
websocket - WebSocket client library for Python

Copyright (C) 2010 Hiroki Ohtani(liris)

    This library is free software; you can redistribute it and/or
    modify it under the terms of the GNU Lesser General Public
    License as published by the Free Software Foundation; either
    version 2.1 of the License, or (at your option) any later version.

    This library is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
    Lesser General Public License for more details.

    You should have received a copy of the GNU Lesser General Public
    License along with this library; if not, write to the Free Software
    Foundation, Inc., 51 Franklin Street, Fifth Floor,
    Boston, MA  02110-1335  USA

"""
from __future__ import absolute_import
import errno
import os
import socket
import sys
import six

import common

from autotest_lib.client.common_lib.cros.autotestChrome.websocket._exceptions import *
from autotest_lib.client.common_lib.cros.autotestChrome.websocket._logging import *
from autotest_lib.client.common_lib.cros.autotestChrome.websocket._socket import*
from autotest_lib.client.common_lib.cros.autotestChrome.websocket._url import *

if six.PY3:
    from base64 import encodebytes as base64encode
else:
    from base64 import encodestring as base64encode

__all__ = ["proxy_info", "connect", "read_headers"]


class proxy_info(object):

    def __init__(self, **options):
        self.host = options.get("http_proxy_host", None)
        if self.host:
            self.port = options.get("http_proxy_port", 0)
            self.auth = options.get("http_proxy_auth", None)
            self.no_proxy = options.get("http_no_proxy", None)
        else:
            self.port = 0
            self.auth = None
            self.no_proxy = None


def connect(url, options, proxy, socket):
    hostname, port, resource, is_secure = parse_url(url)

    if socket:
        return socket, (hostname, port, resource)

    addrinfo_list, need_tunnel, auth = _get_addrinfo_list(
        hostname, port, is_secure, proxy)
    if not addrinfo_list:
        raise WebSocketException(
            "Host not found.: " + hostname + ":" + str(port))

    sock = None
    try:
        sock = _open_socket(addrinfo_list, options.sockopt, options.timeout)
        if need_tunnel:
            sock = _tunnel(sock, hostname, port, auth)

        if is_secure:
            if HAVE_SSL:
                sock = _ssl_socket(sock, options.sslopt, hostname)
            else:
                raise WebSocketException("SSL not available.")

        return sock, (hostname, port, resource)
    except:
        if sock:
            sock.close()
        raise


def _get_addrinfo_list(hostname, port, is_secure, proxy):
    phost, pport, pauth = get_proxy_info(
        hostname, is_secure, proxy.host, proxy.port, proxy.auth, proxy.no_proxy)
    if not phost:
        addrinfo_list = socket.getaddrinfo(
            hostname, port, 0, 0, socket.SOL_TCP)
        return addrinfo_list, False, None
    else:
        pport = pport and pport or 80
        addrinfo_list = socket.getaddrinfo(phost, pport, 0, 0, socket.SOL_TCP)
        return addrinfo_list, True, pauth


def _open_socket(addrinfo_list, sockopt, timeout):
    err = None
    for addrinfo in addrinfo_list:
        family = addrinfo[0]
        sock = socket.socket(family)
        sock.settimeout(timeout)
        for opts in DEFAULT_SOCKET_OPTION:
            sock.setsockopt(*opts)
        for opts in sockopt:
            sock.setsockopt(*opts)

        address = addrinfo[4]
        try:
            sock.connect(address)
        except socket.error as error:
            error.remote_ip = str(address[0])
            if error.errno in (errno.ECONNREFUSED, ):
                err = error
                continue
            else:
                raise
        else:
            break
    else:
        raise err

    return sock

def read_headers(sock):
    status = None
    headers = {}
    trace("--- response header ---")

    while True:
        line = recv_line(sock)
        line = line.decode('utf-8').strip()
        if not line:
            break
        trace(line)
        if not status:

            status_info = line.split(" ", 2)
            status = int(status_info[1])
        else:
            kv = line.split(":", 1)
            if len(kv) == 2:
                key, value = kv
                headers[key.lower()] = value.strip()
            else:
                raise WebSocketException("Invalid header")

    trace("-----------------------")

    return status, headers
