# Copyright (c) 2013 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import BaseHTTPServer
import logging
import shutil
import thread
import urlparse

from autotest_lib.client.bin import test
from autotest_lib.client.common_lib import error
from autotest_lib.client.common_lib import utils
from autotest_lib.client.cros.cellular import test_environment

def _split_url(url):
    """Splits a URL into the URL base and path."""
    split_url = urlparse.urlsplit(url)
    url_base = urlparse.urlunsplit(
            (split_url.scheme, split_url.netloc, '', '', ''))
    url_path = split_url.path
    return url_base, url_path.lstrip('/')

class NanoOmahaDevserver(object):
    """Simple implementation of Omaha."""

    class Handler(BaseHTTPServer.BaseHTTPRequestHandler):
        """Inner class for handling HTTP requests."""

        _OMAHA_RESPONSE_TEMPLATE_HEAD = """
          <response protocol=\"3.0\">
            <daystart elapsed_seconds=\"44801\"/>
            <app appid=\"{87efface-864d-49a5-9bb3-4b050a7c227a}\" status=\"ok\">
              <ping status=\"ok\"/>
              <updatecheck status=\"ok\">
                <urls>
                  <url codebase=\"%s\"/>
                </urls>
                <manifest version=\"9999.0.0\">
                  <packages>
                    <package name=\"%s\" size=\"%d\" required=\"true\"/>
                  </packages>
                  <actions>
                    <action event=\"postinstall\"
              ChromeOSVersion=\"9999.0.0\"
              sha256=\"%s\"
              needsadmin=\"false\"
              IsDeltaPayload=\"%s\"
"""

        _OMAHA_RESPONSE_TEMPLATE_TAIL = """ />
                  </actions>
                </manifest>
              </updatecheck>
            </app>
          </response>
"""

        def do_POST(self):
            """Handler for POST requests."""
            if self.path == '/update':
                (base, name) = _split_url(self.server._devserver._image_url)
                response = self._OMAHA_RESPONSE_TEMPLATE_HEAD % (
                        base + '/',
                        name,
                        self.server._devserver._image_size,
                        self.server._devserver._sha256,
                        str(self.server._devserver._is_delta).lower())
                if self.server._devserver._is_delta:
                    response += '              IsDelta="true"\n'
                if self.server._devserver._metadata_size:
                    response += '              MetadataSize="%d"\n' % (
                            self.server._devserver._metadata_size)
                if self.server._devserver._metadata_signature:
                    response += '              MetadataSignatureRsa="%s"\n' % (
                            self.server._devserver._metadata_signature)
                if self.server._devserver._public_key:
                    response += '              PublicKeyRsa="%s"\n' % (
                            self.server._devserver._public_key)
                response += self._OMAHA_RESPONSE_TEMPLATE_TAIL
                self.send_response(200)
                self.send_header('Content-Type', 'application/xml')
                self.end_headers()
                self.wfile.write(response)
            else:
                self.send_response(500)

    def start(self):
        """Starts the server."""
        self._httpd = BaseHTTPServer.HTTPServer(('127.0.0.1', 0), self.Handler)
        self._httpd._devserver = self
        # Serve HTTP requests in a dedicated thread.
        thread.start_new_thread(self._httpd.serve_forever, ())
        self._port = self._httpd.socket.getsockname()[1]

    def stop(self):
        """Stops the server."""
        self._httpd.shutdown()

    def get_port(self):
        """Returns the TCP port number the server is listening on."""
        return self._port

    def set_image_params(self, image_url, image_size, sha256,
                         metadata_size=None, metadata_signature=None,
                         public_key=None, is_delta=False):
        """Sets the values to return in the Omaha response. Only the
        |image_url|, |image_size| and |sha256| parameters are
        mandatory."""
        self._image_url = image_url
        self._image_size = image_size
        self._sha256 = sha256
        self._metadata_size = metadata_size
        self._metadata_signature = metadata_signature
        self._public_key = public_key
        self._is_delta = is_delta


class autoupdate_CannedOmahaUpdate(test.test):
    """
    Client-side mechanism to update a DUT with a given image.

    Restarts update_engine and attempts an update from the image
    pointed to by |image_url| of size |image_size| with checksum
    |image_sha256|. The rest of the parameters are optional.

    If the |allow_failure| parameter is True, then the test will
    succeed even if the update failed.

    """
    version = 1

    def cleanup(self):
        shutil.copy('/var/log/update_engine.log', self.resultsdir)


    def run_canned_update(self, allow_failure):
        utils.run('restart update-engine')
        self._omaha.start()
        try:
            utils.run('update_engine_client -update -omaha_url=' +
                      'http://127.0.0.1:%d/update ' % self._omaha.get_port())
        except error.CmdError as e:
            self._omaha.stop()
            if not allow_failure:
                raise error.TestFail('Update attempt failed: %s' % e)
            else:
                logging.info('Ignoring failed update. Failure reason: %s', e)


    def run_once(self, image_url, image_size, image_sha256,
                 allow_failure=False, metadata_size=None,
                 metadata_signature=None, public_key=None, use_cellular=False,
                 is_delta=False):

        self._omaha = NanoOmahaDevserver()
        self._omaha.set_image_params(image_url, image_size, image_sha256,
                                     metadata_size, metadata_signature,
                                     public_key, is_delta)

        if use_cellular:
            # Setup DUT so that we have ssh over ethernet but DUT uses
            # cellular as main connection.
            test_env = test_environment.CellularOTATestEnvironment()
            CONNECT_TIMEOUT = 120
            with test_env:
                service = test_env.shill.wait_for_cellular_service_object()
                if not service:
                    raise error.TestError('No cellular service found.')
                test_env.shill.connect_service_synchronous(
                        service, CONNECT_TIMEOUT)
                self.run_canned_update(allow_failure)
        else:
            self.run_canned_update(allow_failure)