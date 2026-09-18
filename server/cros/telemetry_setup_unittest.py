#!/usr/bin/python3
# Lint as: python3
# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Unit tests for server/cros/telemetry_setup.py."""

import os
import shlex
import shutil
import subprocess
import tempfile
import unittest
from unittest import mock

import common
import requests
from autotest_lib.client.common_lib import packages
from autotest_lib.server.cros import telemetry_setup

_BUILD = 'octopus-release/R156-16825.0.0'
_DEVSERVER_URL = 'http://devserver:8082'
_BZ2 = 'dep-telemetry_dep.tar.bz2'
_ZST = 'dep-telemetry_dep.tar.zst'

# What curl --fail -sS prints for a 404 on current and older versions.
_CURL_404 = b'curl: (22) The requested URL returned error: 404\n'
_OLD_CURL_404 = b'curl: (22) The requested URL returned error: 404 Not Found\n'


def _http_response(status, body=b'payload'):
    """Returns a stand-in for a requests.Response with the given status."""
    resp = mock.Mock(status_code=status)
    if status >= 400:
        resp.raise_for_status.side_effect = requests.exceptions.HTTPError(
                '%d Error' % status)
    resp.iter_content.return_value = [body]
    return resp


def _popen_exiting(returncode, stderr=b''):
    """Returns a stand-in for subprocess.Popen whose process exits as given."""
    proc = mock.Mock(returncode=returncode)
    proc.communicate.return_value = (b'', stderr)
    return mock.Mock(return_value=proc)


def _tarball_name(url):
    """Returns the tarball name that a devserver extract URL asks for."""
    return url.rsplit('/', 1)[-1]


class TelemetrySetupTestCase(unittest.TestCase):
    """Builds a TelemetrySetup that touches no devserver and no shared dirs."""

    def setUp(self):
        super().setUp()
        self.tmpdir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmpdir, ignore_errors=True)

        devserver = mock.Mock(hostname='devserver')
        devserver.url.return_value = _DEVSERVER_URL
        patchers = (
                mock.patch.object(telemetry_setup.dev_server.ImageServer,
                                  'resolve',
                                  return_value=devserver),
                mock.patch.object(telemetry_setup.TelemetrySetup,
                                  '_BASE_DIR_PATH',
                                  os.path.join(self.tmpdir, 'workdir')),
        )
        for patcher in patchers:
            patcher.start()
            self.addCleanup(patcher.stop)

        self.telemetry = telemetry_setup.TelemetrySetup(hostname='dut',
                                                        build=_BUILD)
        self.addCleanup(shutil.rmtree,
                        self.telemetry._setup_dir_path,
                        ignore_errors=True)


class DownloadDependencyTest(TelemetrySetupTestCase):
    """Tests how _DownloadDependency probes the candidate tarball names."""

    def setUp(self):
        super().setUp()
        patcher = mock.patch.object(packages, 'DEFAULT_TARBALL_SUFFIX',
                                    packages.BZIP2_TARBALL_SUFFIX)
        patcher.start()
        self.addCleanup(patcher.stop)

    def _serve(self, statuses):
        """Answers requests.get for each tarball name with the given status.

        @param statuses: Map from tarball name to HTTP status. Names that are
                         not in the map get a 404.

        @returns The requests.get mock.
        """

        def fake_get(url, timeout=None):
            return _http_response(statuses.get(_tarball_name(url), 404))

        patcher = mock.patch.object(telemetry_setup.requests,
                                    'get',
                                    side_effect=fake_get)
        self.addCleanup(patcher.stop)
        return patcher.start()

    @staticmethod
    def _requested(get):
        """Returns the tarball names requested through get, in order."""
        return [_tarball_name(call[0][0]) for call in get.call_args_list]

    def test_found_in_default_format_without_probing_others(self):
        get = self._serve({_BZ2: 200, _ZST: 200})
        path = self.telemetry._DownloadDependency('telemetry_dep')
        self.assertEqual(path,
                         os.path.join(self.telemetry._setup_dir_path, _BZ2))
        self.assertEqual(self._requested(get), [_BZ2])
        with open(path, 'rb') as f:
            self.assertEqual(f.read(), b'payload')

    def test_order_follows_default_tarball_suffix(self):
        get = self._serve({_BZ2: 200, _ZST: 200})
        with mock.patch.object(packages, 'DEFAULT_TARBALL_SUFFIX',
                               packages.ZSTD_TARBALL_SUFFIX):
            path = self.telemetry._DownloadDependency('telemetry_dep')
        self.assertEqual(os.path.basename(path), _ZST)
        self.assertEqual(self._requested(get), [_ZST])

    def test_404_falls_through_to_next_format(self):
        get = self._serve({_ZST: 200})
        path = self.telemetry._DownloadDependency('telemetry_dep')
        self.assertEqual(os.path.basename(path), _ZST)
        self.assertEqual(self._requested(get), [_BZ2, _ZST])

    def test_410_falls_through_to_next_format(self):
        get = self._serve({_BZ2: 410, _ZST: 200})
        path = self.telemetry._DownloadDependency('telemetry_dep')
        self.assertEqual(os.path.basename(path), _ZST)
        self.assertEqual(self._requested(get), [_BZ2, _ZST])

    def test_no_format_published_returns_none_and_warns(self):
        get = self._serve({})
        with self.assertLogs(level='WARNING') as logs:
            path = self.telemetry._DownloadDependency('telemetry_dep')
        self.assertIsNone(path)
        self.assertEqual(self._requested(get), [_BZ2, _ZST])
        self.assertIn('%s, %s' % (_BZ2, _ZST), logs.output[0])

    def test_server_error_raises_without_trying_next_format(self):
        get = self._serve({_BZ2: 503, _ZST: 200})
        with self.assertRaises(telemetry_setup.TelemetrySetupError):
            self.telemetry._DownloadDependency('telemetry_dep')
        self.assertEqual(self._requested(get), [_BZ2])

    def test_transient_http_errors_fall_back_to_ssh(self):
        errors = (
                requests.exceptions.ConnectionError('refused'),
                requests.exceptions.Timeout('timed out'),
        )
        for err in errors:
            with self.subTest(error=type(err).__name__):

                def fake_get(url, timeout=None, exc=err):
                    if _tarball_name(url) == _BZ2:
                        raise exc
                    return _http_response(200)

                popen = _popen_exiting(22, _CURL_404)
                with mock.patch.object(telemetry_setup.requests,
                                       'get',
                                       side_effect=fake_get), \
                        mock.patch.object(telemetry_setup.subprocess,
                                          'Popen', popen):
                    path = self.telemetry._DownloadDependency('telemetry_dep')
                self.assertEqual(os.path.basename(path), _ZST)
                self.assertEqual(popen.call_count, 1)
                self.assertFalse(
                        os.path.exists(
                                os.path.join(self.telemetry._setup_dir_path,
                                             _BZ2)))


class DownloadViaSshTest(TelemetrySetupTestCase):
    """Tests the SSH fallback, _DownloadFilesFromDevserverViaSSH."""

    def setUp(self):
        super().setUp()
        self.url = (telemetry_setup.STATIC_URL_TEMPLATE %
                    (_DEVSERVER_URL, telemetry_setup.DEFAULT_DEPS_BUCKET,
                     _BUILD, _BZ2))
        self.dep_path = os.path.join(self.tmpdir, _BZ2)

    def _download(self, returncode, stderr=b''):
        """Runs the SSH download against a process that exits as given.

        @returns A (return value, Popen mock) pair.
        """
        popen = _popen_exiting(returncode, stderr)
        with mock.patch.object(telemetry_setup.subprocess, 'Popen', popen):
            result = self.telemetry._DownloadFilesFromDevserverViaSSH(
                    self.url, self.dep_path)
        return result, popen

    def test_success_returns_path(self):
        result, _ = self._download(0)
        self.assertEqual(result, self.dep_path)
        self.assertTrue(os.path.exists(self.dep_path))

    def test_404_returns_none_and_removes_file(self):
        result, _ = self._download(22, _CURL_404)
        self.assertIsNone(result)
        self.assertFalse(os.path.exists(self.dep_path))

    def test_404_from_older_curl_returns_none(self):
        result, _ = self._download(22, _OLD_CURL_404)
        self.assertIsNone(result)
        self.assertFalse(os.path.exists(self.dep_path))

    def test_410_returns_none_and_removes_file(self):
        result, _ = self._download(
                22, b'curl: (22) The requested URL returned error: 410\n')
        self.assertIsNone(result)
        self.assertFalse(os.path.exists(self.dep_path))

    def test_other_http_error_raises_and_removes_file(self):
        with self.assertRaisesRegex(telemetry_setup.TelemetrySetupError,
                                    'returned error: 503'):
            self._download(
                    22, b'curl: (22) The requested URL returned error: 503\n')
        self.assertFalse(os.path.exists(self.dep_path))

    def test_transport_error_raises_and_removes_file(self):
        with self.assertRaisesRegex(telemetry_setup.TelemetrySetupError,
                                    'Failed to connect'):
            self._download(
                    7, b'curl: (7) Failed to connect to devserver port 8082\n')
        self.assertFalse(os.path.exists(self.dep_path))

    def test_command_quotes_url_and_bounds_time(self):
        _, popen = self._download(0)
        cmd = popen.call_args[0][0]
        self.assertEqual(cmd[:-1], [
                'ssh',
                '-n',
                '-o',
                'BatchMode=yes',
                '-o',
                'ConnectTimeout=%d' % telemetry_setup._REQUEST_TIMEOUT_SECONDS,
                '-o',
                'ServerAliveInterval=30',
                '-o',
                'ServerAliveCountMax=3',
                'devserver',
        ])
        # The URL embeds the build label and a '?', so it has to reach the
        # remote shell quoted.
        self.assertTrue(cmd[-1].endswith(" '%s'" % self.url))
        self.assertEqual(shlex.split(cmd[-1]), [
                'curl', '--fail', '-sS', '--max-time',
                str(telemetry_setup._SSH_CURL_MAX_TIME_SECONDS), self.url
        ])


class ExtractTarballTest(TelemetrySetupTestCase):
    """Tests the tar command line that _ExtractTarball runs."""

    def _extract(self, tarball_name, returncode=0, stderr=b''):
        """Runs _ExtractTarball against a tar that exits as given.

        @returns The tar command line.
        """
        popen = _popen_exiting(returncode, stderr)
        with mock.patch.object(telemetry_setup.subprocess, 'Popen', popen):
            self.telemetry._ExtractTarball(
                    os.path.join(self.tmpdir, tarball_name), self.tmpdir)
        return popen.call_args[0][0]

    def test_zstd_decompressor_is_explicit(self):
        cmd = self._extract(_ZST)
        self.assertEqual(cmd[:5],
                         ['tar', '--no-same-owner', '-x', '-I', 'zstd'])

    def test_bzip2_decompressor_is_explicit(self):
        cmd = self._extract(_BZ2)
        self.assertEqual(cmd[:4], ['tar', '--no-same-owner', '-x', '-j'])

    def test_unknown_suffix_raises(self):
        with self.assertRaisesRegex(telemetry_setup.TelemetrySetupError,
                                    'Unsupported tarball format'):
            self._extract('dep-telemetry_dep.tar.gz')

    def test_tar_failure_raises(self):
        with self.assertRaisesRegex(telemetry_setup.TelemetrySetupError,
                                    'zstd: Cannot exec'):
            self._extract(_ZST,
                          returncode=2,
                          stderr=b'tar: zstd: Cannot exec: No such file\n')

    def test_popen_exception_removes_dest_and_raises(self):
        dest = tempfile.mkdtemp(dir=self.tmpdir)
        with mock.patch.object(telemetry_setup.subprocess,
                               'Popen',
                               side_effect=OSError('no tar')):
            with self.assertRaisesRegex(telemetry_setup.TelemetrySetupError,
                                        'no tar'):
                self.telemetry._ExtractTarball(os.path.join(self.tmpdir, _BZ2),
                                               dest)
        self.assertFalse(os.path.exists(dest))


class RealTarTest(TelemetrySetupTestCase):
    """Runs _ExtractTarball and Setup against real tarballs."""

    def _make_tarball(self, name, compress_args):
        """Creates a tarball rooted at test_src/, like a dep tarball.

        @param name: File name of the tarball, which sets its format.
        @param compress_args: tar arguments that select the compressor.

        @returns Path to the tarball.
        """
        src = tempfile.mkdtemp(dir=self.tmpdir)
        os.mkdir(os.path.join(src, 'test_src'))
        with open(os.path.join(src, 'test_src', 'marker'), 'w') as f:
            f.write('telemetry')
        path = os.path.join(self.tmpdir, name)
        subprocess.check_call(['tar', '-c'] + compress_args +
                              ['-f', path, '-C', src, 'test_src'])
        return path

    def _make_corrupt_tarball(self):
        """Creates a file that is named like a tarball but is not one."""
        path = os.path.join(self.tmpdir, _BZ2)
        with open(path, 'wb') as f:
            f.write(b'not a tarball')
        return path

    def _assert_extracts(self, tarball):
        """Checks that _ExtractTarball unpacks the given tarball."""
        dest = tempfile.mkdtemp(dir=self.tmpdir)
        self.telemetry._ExtractTarball(tarball, dest)
        with open(os.path.join(dest, 'test_src', 'marker')) as f:
            self.assertEqual(f.read(), 'telemetry')

    def test_extracts_bzip2(self):
        self._assert_extracts(self._make_tarball(_BZ2, ['-j']))

    @unittest.skipUnless(packages.has_zstd(), 'zstd is not installed')
    def test_extracts_zstd(self):
        self._assert_extracts(self._make_tarball(_ZST, ['-I', 'zstd']))

    def test_corrupt_tarball_raises(self):
        with self.assertRaises(telemetry_setup.TelemetrySetupError):
            self.telemetry._ExtractTarball(self._make_corrupt_tarball(),
                                           self.tmpdir)

    def test_setup_moves_extracted_tree_to_src(self):
        tarball = self._make_tarball(_BZ2, ['-j'])
        with mock.patch.object(self.telemetry,
                               '_DownloadDependency',
                               side_effect=[tarball, None, None]):
            src = self.telemetry.Setup()
        with open(os.path.join(src, 'marker')) as f:
            self.assertEqual(f.read(), 'telemetry')

    def test_setup_reports_extraction_failure(self):
        corrupt = self._make_corrupt_tarball()
        with mock.patch.object(self.telemetry,
                               '_DownloadDependency',
                               return_value=corrupt):
            with self.assertRaises(telemetry_setup.TelemetrySetupError):
                self.telemetry.Setup()

    def test_setup_raises_when_telemetry_dep_is_missing(self):
        chrome_test = self._make_tarball('dep-chrome_test.tar.bz2', ['-j'])
        with mock.patch.object(self.telemetry,
                               '_DownloadDependency',
                               side_effect=[None, chrome_test,
                                            None]) as download:
            with self.assertRaisesRegex(telemetry_setup.TelemetrySetupError,
                                        'dep-telemetry_dep'):
                self.telemetry.Setup()
        self.assertEqual(download.call_args_list, [mock.call('telemetry_dep')])

    def test_setup_raises_when_archive_lacks_test_src(self):
        with mock.patch.object(self.telemetry,
                               '_DownloadDependency',
                               side_effect=['/fake/tarball', None, None]), \
                mock.patch.object(self.telemetry, '_ExtractTarball'):
            with self.assertRaisesRegex(telemetry_setup.TelemetrySetupError,
                                        'test_src/'):
                self.telemetry.Setup()

    def test_setup_reports_move_failure(self):
        tarball = self._make_tarball(_BZ2, ['-j'])
        with mock.patch.object(self.telemetry,
                               '_DownloadDependency',
                               side_effect=[tarball, None, None]), \
                mock.patch.object(telemetry_setup.shutil,
                                  'move',
                                  side_effect=OSError('permission denied')):
            with self.assertRaisesRegex(telemetry_setup.TelemetrySetupError,
                                        'permission denied'):
                self.telemetry.Setup()


if __name__ == '__main__':
    unittest.main()
