#!/usr/bin/python3
# Lint as: python3
# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Unit tests for client/common_lib/packages.py and related packaging paths."""

import os
import re
import shutil
import sys
import tempfile
import unittest
from unittest import mock

import common
from autotest_lib.client.bin import harness_autoserv
from autotest_lib.client.common_lib import error
from autotest_lib.client.common_lib import packages
from autotest_lib.client.common_lib import utils


class StubFetcher(packages.RepositoryFetcher):
    """In-memory RepositoryFetcher stub for unit tests."""

    def __init__(self, url, available=None, fail_with=None):
        """Initializes the stub fetcher.

        @param url: Repository URL identifier.
        @param available: Collection of filenames present in this repository.
        @param fail_with: Optional exception instance or callable(filename) to
            raise instead of PackageNotFoundError when a file is not in
            available.
        """
        self.url = url
        self.available = set(available or ())
        self.fail_with = fail_with
        self.calls = []

    def fetch_pkg_file(self, filename, dest_path):
        """Records the fetch attempt and simulates success or failure."""
        self.calls.append((self.url, filename))
        if filename in self.available:
            return
        if self.fail_with is not None:
            exc = (self.fail_with(filename)
                   if callable(self.fail_with) else self.fail_with)
            raise exc
        raise error.PackageNotFoundError('%s not in %s' % (filename, self.url))


class PackageManagerTestBase(unittest.TestCase):
    """Base test case providing a real PackageManager with a fake runner."""

    def setUp(self):
        super().setUp()
        self.temp_dir = tempfile.mkdtemp(prefix='packages_unittest_')
        self.addCleanup(shutil.rmtree, self.temp_dir, ignore_errors=True)
        self.existing_files = {}
        self.existing_dirs = {self.temp_dir, '/fetch', '/install'}
        self.commands = []

    def _fake_run(self, cmd, *_args, **_dargs):
        """Simulates shell commands issued by BasePackageManager."""
        self.commands.append(cmd)
        if cmd.startswith('test -d '):
            path = cmd[len('test -d '):].strip()
            if path in self.existing_dirs or os.path.isdir(path):
                return utils.CmdResult(command=cmd, exit_status=0)
            raise error.CmdError(cmd,
                                 utils.CmdResult(command=cmd, exit_status=1))
        if cmd.startswith('test -e '):
            path = cmd[len('test -e '):].strip()
            if path in self.existing_files or os.path.exists(path):
                return utils.CmdResult(command=cmd, exit_status=0)
            raise error.CmdError(cmd,
                                 utils.CmdResult(command=cmd, exit_status=1))
        if cmd.startswith('mkdir -p '):
            path = cmd[len('mkdir -p '):].strip()
            self.existing_dirs.add(path)
            return utils.CmdResult(command=cmd, exit_status=0)
        if cmd.startswith('echo '):
            match = re.match(r'^echo "(.*)" > (\S+)\s*$', cmd, re.DOTALL)
            if match:
                content, path = match.groups()
                self.existing_files[path] = content + '\n'
                if os.path.isdir(os.path.dirname(path)):
                    with open(path, 'w') as f:
                        f.write(content + '\n')
            return utils.CmdResult(command=cmd, stdout='', exit_status=0)
        if cmd.startswith('cat '):
            path = cmd[len('cat '):].strip()
            if path in self.existing_files:
                return utils.CmdResult(command=cmd,
                                       stdout=self.existing_files[path],
                                       exit_status=0)
            if os.path.isfile(path):
                with open(path, 'r') as f:
                    return utils.CmdResult(command=cmd,
                                           stdout=f.read(),
                                           exit_status=0)
            raise error.CmdError(cmd,
                                 utils.CmdResult(command=cmd, exit_status=1))
        if cmd.startswith('md5sum '):
            return utils.CmdResult(
                    command=cmd,
                    stdout='d41d8cd98f00b204e9800998ecf8427e  -\n',
                    exit_status=0)
        return utils.CmdResult(command=cmd, stdout='', exit_status=0)

    def _make_pkgmgr(self, repo_urls=None, upload_paths=None):
        """Constructs a PackageManager backed by self._fake_run."""
        return packages.PackageManager(self.temp_dir,
                                       repo_urls=repo_urls,
                                       upload_paths=upload_paths,
                                       do_locking=False,
                                       run_function=self._fake_run)


class TarballNamingTests(PackageManagerTestBase):
    """Tests for tarball naming, suffix stripping, and name parsing."""

    def test_strip_tarball_suffix(self):
        """Both bzip2 and zstd suffixes are stripped; others return None."""
        self.assertEqual(packages.strip_tarball_suffix('dep-foo.tar.bz2'),
                         'dep-foo')
        self.assertEqual(packages.strip_tarball_suffix('dep-foo.tar.zst'),
                         'dep-foo')
        self.assertIsNone(packages.strip_tarball_suffix('dep-foo.tar.gz'))
        self.assertIsNone(packages.strip_tarball_suffix('dep-foo'))

    def test_get_tarball_name_default_and_explicit(self):
        """get_tarball_name defaults to DEFAULT_TARBALL_SUFFIX."""
        pm = packages.PackageManager
        self.assertEqual(pm.get_tarball_name('telemetry_dep', 'dep'),
                         'dep-telemetry_dep.tar.zst')
        self.assertEqual(
                pm.get_tarball_name('telemetry_dep', 'dep',
                                    packages.BZIP2_TARBALL_SUFFIX),
                'dep-telemetry_dep.tar.bz2')
        self.assertEqual(
                pm.get_tarball_name('telemetry_dep', 'dep',
                                    packages.ZSTD_TARBALL_SUFFIX),
                'dep-telemetry_dep.tar.zst')

    def test_get_tarball_name_respects_runtime_default(self):
        """suffix=None resolves DEFAULT_TARBALL_SUFFIX at call time."""
        with mock.patch.object(packages, 'DEFAULT_TARBALL_SUFFIX',
                               packages.BZIP2_TARBALL_SUFFIX):
            self.assertEqual(
                    packages.PackageManager.get_tarball_name(
                            'telemetry_dep', 'dep'),
                    'dep-telemetry_dep.tar.bz2')

    def test_get_tarball_names_order(self):
        """get_tarball_names puts DEFAULT_TARBALL_SUFFIX first."""
        self.assertEqual(
                packages.BasePackageManager.get_tarball_names(
                        'telemetry_dep', 'dep'),
                ['dep-telemetry_dep.tar.zst', 'dep-telemetry_dep.tar.bz2'])
        self.assertEqual(
                packages.PackageManager.get_tarball_names(
                        'telemetry_dep', 'dep'),
                ['dep-telemetry_dep.tar.zst', 'dep-telemetry_dep.tar.bz2'])
        with mock.patch.object(packages, 'DEFAULT_TARBALL_SUFFIX',
                               packages.BZIP2_TARBALL_SUFFIX):
            self.assertEqual(
                    packages.PackageManager.get_tarball_names(
                            'telemetry_dep', 'dep'),
                    ['dep-telemetry_dep.tar.bz2', 'dep-telemetry_dep.tar.zst'])

    def test_get_published_tarball_names(self):
        """PUBLISHED_TARBALL_SUFFIXES is a subset of TARBALL_SUFFIXES."""
        self.assertTrue(packages.PUBLISHED_TARBALL_SUFFIXES)
        self.assertLessEqual(set(packages.PUBLISHED_TARBALL_SUFFIXES),
                             set(packages.TARBALL_SUFFIXES))
        self.assertEqual(
                packages.PackageManager.get_published_tarball_names(
                        'telemetry_dep', 'dep'),
                ['dep-telemetry_dep.tar.zst', 'dep-telemetry_dep.tar.bz2'])
        with mock.patch.object(packages, 'PUBLISHED_TARBALL_SUFFIXES',
                               (packages.ZSTD_TARBALL_SUFFIX, )):
            self.assertEqual(
                    packages.PackageManager.get_published_tarball_names(
                            'telemetry_dep', 'dep'),
                    ['dep-telemetry_dep.tar.zst'])

    def test_parse_tarball_name(self):
        """parse_tarball_name accepts both suffixes and rejects unknown ones."""
        pm = packages.PackageManager
        self.assertEqual(pm.parse_tarball_name('dep-telemetry_dep.tar.bz2'),
                         ('telemetry_dep', 'dep'))
        self.assertEqual(pm.parse_tarball_name('dep-telemetry_dep.tar.zst'),
                         ('telemetry_dep', 'dep'))
        self.assertEqual(pm.parse_tarball_name('test-my-cool-test.tar.zst'),
                         ('my-cool-test', 'test'))
        with self.assertRaises(ValueError):
            pm.parse_tarball_name('dep-telemetry_dep.tar.gz')
        with self.assertRaises(ValueError):
            pm.parse_tarball_name('not_a_tarball')
        with self.assertRaises(ValueError):
            pm.parse_tarball_name(None)

    def test_get_package_name_non_url(self):
        """get_package_name strips both suffixes for non-URL inputs."""
        pm = self._make_pkgmgr()
        self.assertEqual(pm.get_package_name('sleeptest.tar.bz2', 'test'),
                         ('sleeptest', 'sleeptest'))
        self.assertEqual(pm.get_package_name('sleeptest.tar.zst', 'test'),
                         ('sleeptest', 'sleeptest'))
        self.assertEqual(pm.get_package_name('123.sleeptest.tar.zst', 'test'),
                         ('sleeptest', 'sleeptest'))
        self.assertEqual(pm.get_package_name('sleeptest', 'test'),
                         ('', 'sleeptest'))

    def test_get_package_name_url(self):
        """get_package_name strips both suffixes for URL inputs."""
        pm = self._make_pkgmgr()
        self.assertEqual(
                pm.get_package_name('http://h/grp/sleeptest.tar.bz2', 'test'),
                ('h_grp', 'sleeptest'))
        self.assertEqual(
                pm.get_package_name('http://h/grp/sleeptest.tar.zst', 'test'),
                ('h_grp', 'sleeptest'))
        self.assertEqual(
                pm.get_package_name('http://h/grp/sleeptest.tar.zst.42',
                                    'test'), ('h_grp', 'sleeptest'))


class FetcherErrorClassificationTests(PackageManagerTestBase):
    """Tests that fetchers distinguish missing packages from transport errors."""

    def test_http_fetcher_404_and_410_raise_package_not_found(self):
        """Curl exit 22 with HTTP 404 or 410 raises PackageNotFoundError."""
        for err_cls in (error.CmdError, error.AutoservRunError):
            for http_code in ('404', '410'):

                def fail_not_found(cmd,
                                   *_args,
                                   _cls=err_cls,
                                   _code=http_code,
                                   **_dargs):
                    if cmd.startswith('curl '):
                        res = utils.CmdResult(command=cmd,
                                              stdout=_code,
                                              exit_status=22)
                        raise _cls(cmd, res)
                    return utils.CmdResult(command=cmd,
                                           stdout='/tmp/t\n',
                                           exit_status=0)

                pm = packages.PackageManager(self.temp_dir,
                                             do_locking=False,
                                             run_function=fail_not_found)
                fetcher = packages.SiteHttpFetcher(pm, 'http://cache/repo')
                with self.assertRaises(error.PackageNotFoundError) as ctx:
                    fetcher.fetch_pkg_file('dep-foo.tar.zst', '/fetch/out')
                self.assertIn('HTTP ' + http_code, str(ctx.exception))

    def test_http_fetcher_503_raises_package_fetch_error(self):
        """Curl exit 22 with HTTP 503 raises PackageFetchError, not NotFound."""
        for err_cls in (error.CmdError, error.AutoservRunError):

            def fail_503(cmd, *_args, _cls=err_cls, **_dargs):
                if cmd.startswith('curl '):
                    res = utils.CmdResult(command=cmd,
                                          stdout='503',
                                          exit_status=22)
                    raise _cls(cmd, res)
                return utils.CmdResult(command=cmd,
                                       stdout='/tmp/t\n',
                                       exit_status=0)

            pm = packages.PackageManager(self.temp_dir,
                                         do_locking=False,
                                         run_function=fail_503)
            fetcher = packages.SiteHttpFetcher(pm, 'http://cache/repo')
            with self.assertRaises(error.PackageFetchError) as ctx:
                fetcher.fetch_pkg_file('dep-foo.tar.bz2', '/fetch/out')
            self.assertNotIsInstance(ctx.exception, error.PackageNotFoundError)
            self.assertIn('could not be fetched from', str(ctx.exception))
            self.assertIn('HTTP 503', str(ctx.exception))

    def test_http_fetcher_transport_error_raises_package_fetch_error(self):
        """Non-22 curl failures raise PackageFetchError and omit HTTP 000."""
        for err_cls in (error.CmdError, error.AutoservRunError):

            def fail_conn(cmd, *_args, _cls=err_cls, **_dargs):
                if cmd.startswith('curl '):
                    res = utils.CmdResult(command=cmd,
                                          stdout='000',
                                          stderr='Connection refused',
                                          exit_status=7)
                    raise _cls(cmd, res)
                return utils.CmdResult(command=cmd,
                                       stdout='/tmp/t\n',
                                       exit_status=0)

            pm = packages.PackageManager(self.temp_dir,
                                         do_locking=False,
                                         run_function=fail_conn)
            fetcher = packages.SiteHttpFetcher(pm, 'http://cache/repo')
            with self.assertRaises(error.PackageFetchError) as ctx:
                fetcher.fetch_pkg_file('dep-foo.tar.bz2', '/fetch/out')
            self.assertNotIsInstance(ctx.exception, error.PackageNotFoundError)
            self.assertIn('could not be fetched from', str(ctx.exception))
            self.assertNotIn('HTTP 000', str(ctx.exception))

    def test_is_http_not_found(self):
        """is_http_not_found matches only exit 22 with 404 or 410."""
        self.assertTrue(packages.is_http_not_found(22, '404'))
        self.assertTrue(packages.is_http_not_found(22, '410\n'))
        self.assertTrue(packages.is_http_not_found(22, 404))
        self.assertFalse(packages.is_http_not_found(22, '503'))
        self.assertFalse(packages.is_http_not_found(22, '000'))
        self.assertFalse(packages.is_http_not_found(22, ''))
        self.assertFalse(packages.is_http_not_found(22, None))
        self.assertFalse(packages.is_http_not_found(7, '404'))

    def test_site_http_fetcher_format_cmd_does_not_duplicate_fail(self):
        """SiteHttpFetcher.format_cmd(..., fail=True) keeps a single --fail."""
        cmd_fail = packages.SiteHttpFetcher.format_cmd('http://cache/pkg',
                                                       '/fetch/pkg',
                                                       fail=True)
        self.assertEqual(cmd_fail.count('--fail'), 1)
        self.assertIn("-w '%{http_code}'", cmd_fail)

        cmd_probe = packages.SiteHttpFetcher.format_cmd('http://cache/pkg',
                                                        '/fetch/pkg',
                                                        fail=False)
        self.assertEqual(cmd_probe.count('--fail'), 1)
        self.assertNotIn("-w '%{http_code}'", cmd_probe)

    def test_base_http_fetcher_adds_fail_only_for_package_fetch(self):
        """HttpFetcher omits --fail in _quick_http_test but adds it on fetch."""
        seen_curl_cmds = []

        def run_fn(cmd, *_args, **_dargs):
            if cmd.startswith('curl '):
                seen_curl_cmds.append(cmd)
                if '--fail' in cmd:
                    raise error.CmdError(
                            cmd,
                            utils.CmdResult(command=cmd,
                                            stdout='404',
                                            exit_status=22))
            return utils.CmdResult(command=cmd,
                                   stdout='/tmp/probe\n',
                                   exit_status=0)

        pm = packages.BasePackageManager(self.temp_dir,
                                         do_locking=False,
                                         run_function=run_fn)
        fetcher = packages.HttpFetcher(pm, 'http://repo/base')
        with self.assertRaises(error.PackageNotFoundError):
            fetcher.fetch_pkg_file('dep-foo.tar.zst', '/fetch/out')
        self.assertEqual(len(seen_curl_cmds), 2)
        self.assertNotIn('--fail', seen_curl_cmds[0])
        self.assertIn('--fail', seen_curl_cmds[1])
        self.assertIn("-w '%{http_code}'", seen_curl_cmds[1])

    def test_local_filesystem_fetcher_missing_vs_cp_and_ssh_errors(self):
        """LocalFilesystemFetcher distinguishes missing file from cp/SSH errors."""

        def fail_cp(cmd, *_args, **_dargs):
            if cmd.startswith('cp '):
                raise error.CmdError(
                        cmd, utils.CmdResult(command=cmd, exit_status=1))
            if cmd.startswith('test -e '):
                path = cmd[len('test -e '):].strip()
                if path not in self.existing_files:
                    raise error.AutoservRunError(
                            cmd,
                            utils.CmdResult(
                                    command=cmd,
                                    stderr='Warning: Permanently added host\n',
                                    exit_status=1))
            return self._fake_run(cmd)

        pm = packages.PackageManager(self.temp_dir,
                                     do_locking=False,
                                     run_function=fail_cp)
        fetcher = packages.LocalFilesystemFetcher(pm, '/local/repo')
        with self.assertRaises(error.PackageNotFoundError):
            fetcher.fetch_pkg_file('dep-foo.tar.zst', '/fetch/out')

        # Source file exists, but cp fails -> PackageFetchError.
        self.existing_files['/local/repo/dep-foo.tar.bz2'] = 'data'
        with self.assertRaises(error.PackageFetchError) as ctx:
            fetcher.fetch_pkg_file('dep-foo.tar.bz2', '/fetch/out')
        self.assertNotIsInstance(ctx.exception, error.PackageNotFoundError)

        # SSH transport failure (exit 255) -> PackageFetchError, not NotFound.
        def fail_ssh(cmd, *_args, **_dargs):
            raise error.AutoservRunError(
                    cmd,
                    utils.CmdResult(command=cmd,
                                    stderr='ssh: connect timed out',
                                    exit_status=255))

        pm_ssh = packages.PackageManager(self.temp_dir,
                                         do_locking=False,
                                         run_function=fail_ssh)
        fetcher_ssh = packages.LocalFilesystemFetcher(pm_ssh, '/local/repo')
        with self.assertRaises(error.PackageFetchError) as ctx:
            fetcher_ssh.fetch_pkg_file('dep-foo.tar.zst', '/fetch/out')
        self.assertNotIsInstance(ctx.exception, error.PackageNotFoundError)

    def test_autoserv_fetcher_missing_vs_disabled(self):
        """AutoservFetcher raises NotFound when unserved, FetchError if off."""
        pm = self._make_pkgmgr()
        harness = mock.MagicMock()
        fetcher = harness_autoserv.AutoservFetcher(pm, harness)

        dest = os.path.join(self.temp_dir, 'unserved.tar.zst')
        with self.assertRaises(error.PackageNotFoundError):
            fetcher.fetch_pkg_file('unserved.tar.zst', dest)

        with mock.patch.object(harness_autoserv.global_config.global_config,
                               'get_config_value',
                               return_value=False):
            with self.assertRaises(error.PackageFetchError) as ctx:
                fetcher.fetch_pkg_file('unserved.tar.zst', dest)
            self.assertNotIsInstance(ctx.exception, error.PackageNotFoundError)


class InstallPkgTests(PackageManagerTestBase):
    """Tests for candidate selection, repository ordering, and error handling."""

    def test_install_pkg_first_candidate_found(self):
        """When the first candidate succeeds, the second is not probed."""
        pm = self._make_pkgmgr()
        repo = StubFetcher('http://repo', {'dep-foo.tar.zst'})
        pm.add_repository(repo)
        untarred = []
        pm.untar_pkg = lambda path, d: untarred.append(path)

        pm.install_pkg('foo', 'dep', '/fetch', '/install')
        self.assertEqual(repo.calls, [
                ('http://repo', 'dep-foo.tar.zst'),
                ('http://repo', 'packages.checksum'),
        ])
        self.assertEqual(untarred, ['/fetch/dep-foo.tar.zst'])

    def test_install_pkg_falls_back_to_second_candidate(self):
        """When the first candidate raises PackageNotFoundError, second wins."""
        pm = self._make_pkgmgr()
        repo = StubFetcher('http://repo', {'dep-foo.tar.bz2'})
        pm.add_repository(repo)
        untarred = []
        pm.untar_pkg = lambda path, d: untarred.append(path)

        pm.install_pkg('foo', 'dep', '/fetch', '/install')
        self.assertEqual(repo.calls, [
                ('http://repo', 'dep-foo.tar.zst'),
                ('http://repo', 'dep-foo.tar.bz2'),
                ('http://repo', 'packages.checksum'),
        ])
        self.assertEqual(untarred, ['/fetch/dep-foo.tar.bz2'])

    def test_install_pkg_neither_found(self):
        """When neither candidate is found, PackageInstallError names both."""
        pm = self._make_pkgmgr()
        repo = StubFetcher('http://repo', set())
        pm.add_repository(repo)

        with self.assertRaises(error.PackageInstallError) as ctx:
            pm.install_pkg('foo', 'dep', '/fetch', '/install')
        self.assertEqual(repo.calls, [
                ('http://repo', 'dep-foo.tar.zst'),
                ('http://repo', 'dep-foo.tar.bz2'),
        ])
        self.assertIn('dep-foo.tar.bz2', str(ctx.exception))
        self.assertIn('dep-foo.tar.zst', str(ctx.exception))

    def test_install_pkg_uses_checksum_dict_to_order_candidates(self):
        """packages.checksum orders the advertised format first."""
        pm = self._make_pkgmgr()
        pm._checksum_dict = {'dep-foo.tar.bz2': 'deadbeef'}
        repo = StubFetcher('http://repo', {'dep-foo.tar.bz2'})
        pm.add_repository(repo)
        untarred = []
        pm.untar_pkg = lambda path, d: untarred.append(path)

        pm.install_pkg('foo', 'dep', '/fetch', '/install')
        self.assertEqual(repo.calls, [('http://repo', 'dep-foo.tar.bz2')])
        self.assertEqual(untarred, ['/fetch/dep-foo.tar.bz2'])

    def test_install_pkg_uses_checksum_file_on_disk_when_memory_empty(self):
        """On-disk packages.checksum orders candidates when _checksum_dict is empty."""
        pm = self._make_pkgmgr()
        self.existing_files[
                pm._get_checksum_file_path()] = 'deadbeef dep-foo.tar.bz2\n'
        repo = StubFetcher('http://repo', {'dep-foo.tar.bz2'})
        pm.add_repository(repo)
        untarred = []
        pm.untar_pkg = lambda path, d: untarred.append(path)

        pm.install_pkg('foo', 'dep', '/fetch', '/install')
        self.assertEqual(repo.calls, [('http://repo', 'dep-foo.tar.bz2')])
        self.assertEqual(untarred, ['/fetch/dep-foo.tar.bz2'])

    def test_install_pkg_checksum_lists_both_formats(self):
        """When packages.checksum lists both formats, default suffix is first."""
        pm = self._make_pkgmgr()
        pm._checksum_dict = {
                'dep-foo.tar.bz2': 'aaaa',
                'dep-foo.tar.zst': 'bbbb',
        }
        repo = StubFetcher('http://repo',
                           {'dep-foo.tar.bz2', 'dep-foo.tar.zst'})
        pm.add_repository(repo)
        untarred = []
        pm.untar_pkg = lambda path, d: untarred.append(path)

        pm.install_pkg('foo', 'dep', '/fetch', '/install')
        self.assertEqual(repo.calls, [('http://repo', 'dep-foo.tar.zst')])
        self.assertEqual(untarred, ['/fetch/dep-foo.tar.zst'])

    def test_install_pkg_checksum_stale_falls_back_to_other_format(self):
        """If the format in packages.checksum is missing, the other is tried."""
        pm = self._make_pkgmgr()
        pm._checksum_dict = {'dep-foo.tar.zst': 'deadbeef'}
        repo = StubFetcher('http://repo', {'dep-foo.tar.bz2'})
        pm.add_repository(repo)
        untarred = []
        pm.untar_pkg = lambda path, d: untarred.append(path)

        pm.install_pkg('foo', 'dep', '/fetch', '/install')
        self.assertEqual(repo.calls, [
                ('http://repo', 'dep-foo.tar.zst'),
                ('http://repo', 'dep-foo.tar.bz2'),
        ])
        self.assertEqual(untarred, ['/fetch/dep-foo.tar.bz2'])

    def test_install_pkg_forwards_repo_url(self):
        """An explicit repo_url is resolved via get_fetcher and used directly."""
        pm = self._make_pkgmgr()
        repo = StubFetcher('http://custom/repo', {'dep-foo.tar.zst'})
        pm.untar_pkg = lambda path, d: None

        with mock.patch.object(pm, 'get_fetcher',
                               return_value=repo) as mock_gf:
            pm.install_pkg('foo',
                           'dep',
                           '/fetch',
                           '/install',
                           repo_url='http://custom/repo')
        mock_gf.assert_called_once_with('http://custom/repo')
        self.assertEqual(repo.calls, [
                ('http://custom/repo', 'dep-foo.tar.zst'),
        ])

    def test_empty_repo_url_uses_configured_repositories(self):
        """repo_url='' (from os.path.dirname on bare names) uses self.repositories."""
        pm = self._make_pkgmgr()
        repo = StubFetcher('http://repo',
                           {'sleeptest.tar.zst', 'dep-foo.tar.zst'})
        pm.add_repository(repo)
        pm.untar_pkg = lambda path, d: None

        pm.fetch_pkg('sleeptest.tar.zst',
                     '/fetch/sleeptest.tar.zst',
                     repo_url='')
        pm.install_pkg('foo', 'dep', '/fetch', '/install', repo_url='')
        self.assertEqual(repo.calls, [
                ('http://repo', 'sleeptest.tar.zst'),
                ('http://repo', 'dep-foo.tar.zst'),
                ('http://repo', 'packages.checksum'),
        ])

    def test_install_pkg_preserves_repository_priority(self):
        """A higher-priority repo's bz2 beats a lower-priority repo's zst."""
        pm = self._make_pkgmgr()
        self.existing_files[pm._get_checksum_file_path()] = ''
        untarred = []
        pm.untar_pkg = lambda path, d: untarred.append(path)

        low_prio = StubFetcher('autoserv://', {'dep-foo.tar.zst'})
        high_prio = StubFetcher('http://devserver', {'dep-foo.tar.bz2'})
        pm.repositories = [low_prio, high_prio]

        with mock.patch.object(packages, 'DEFAULT_TARBALL_SUFFIX',
                               packages.ZSTD_TARBALL_SUFFIX):
            pm.install_pkg('foo', 'dep', '/fetch', '/install')

        self.assertEqual(high_prio.calls, [
                ('http://devserver', 'dep-foo.tar.zst'),
                ('http://devserver', 'dep-foo.tar.bz2'),
        ])
        self.assertEqual(low_prio.calls, [])
        self.assertEqual(untarred, ['/fetch/dep-foo.tar.bz2'])

    def test_install_pkg_dead_repo_skips_second_format_and_falls_back(self):
        """A transport error on a repo skips remaining formats on that repo."""
        pm = self._make_pkgmgr()
        self.existing_files[pm._get_checksum_file_path()] = ''
        untarred = []
        pm.untar_pkg = lambda path, d: untarred.append(path)

        dead_repo = StubFetcher(
                'http://dead-cache',
                fail_with=lambda fn: error.PackageFetchError('timeout: ' + fn))
        fallback_repo = StubFetcher('autoserv://', {'dep-foo.tar.zst'})
        pm.repositories = [fallback_repo, dead_repo]

        pm.install_pkg('foo', 'dep', '/fetch', '/install')
        self.assertEqual(dead_repo.calls,
                         [('http://dead-cache', 'dep-foo.tar.zst')])
        self.assertEqual(fallback_repo.calls,
                         [('autoserv://', 'dep-foo.tar.zst')])
        self.assertEqual(untarred, ['/fetch/dep-foo.tar.zst'])

    def test_install_pkg_uncached_dead_repo_makes_single_attempt(self):
        """Uncached install against a dead repo does not fetch packages.checksum."""
        pm = self._make_pkgmgr()
        dead_repo = StubFetcher(
                'http://dead-cache',
                fail_with=lambda fn: error.PackageFetchError('timeout: ' + fn))
        pm.add_repository(dead_repo)

        with self.assertRaises(error.PackageInstallError):
            pm.install_pkg('autotest', 'client', '/fetch', '/install')

        self.assertEqual(dead_repo.calls,
                         [('http://dead-cache', 'client-autotest.tar.zst')])

    def test_install_pkg_does_not_retry_failed_checksum_fetch(self):
        """When packages.checksum fetch fails, compare_checksum does not retry."""
        pm = self._make_pkgmgr()
        # Simulate a cached tarball already on the DUT, but no local checksum.
        self.existing_files['/fetch/client-autotest.tar.zst'] = 'cached'
        dead_repo = StubFetcher(
                'http://dead-cache',
                fail_with=lambda fn: error.PackageFetchError('timeout: ' + fn))
        pm.add_repository(dead_repo)

        with self.assertRaises(error.PackageInstallError):
            pm.install_pkg('autotest', 'client', '/fetch', '/install')

        self.assertEqual(dead_repo.calls, [
                ('http://dead-cache', 'packages.checksum'),
                ('http://dead-cache', 'client-autotest.tar.zst'),
        ])

    def test_failed_direct_checksum_fetch_marks_checksum_fetch_failed(self):
        """A failed fetch_pkg(CHECKSUM_FILE) prevents a retry in install_pkg."""
        pm = self._make_pkgmgr()
        self.existing_files['/fetch/dep-foo.tar.zst'] = 'cached'
        dead_repo = StubFetcher(
                'http://dead-cache',
                fail_with=lambda fn: error.PackageFetchError('timeout: ' + fn))
        pm.add_repository(dead_repo)

        with self.assertRaises(error.PackageFetchError):
            pm.fetch_pkg(packages.CHECKSUM_FILE,
                         pm._get_checksum_file_path(),
                         use_checksum=False)
        self.assertTrue(pm._checksum_fetch_failed)

        with self.assertRaises(error.PackageInstallError):
            pm.install_pkg('foo', 'dep', '/fetch', '/install')

        self.assertEqual(dead_repo.calls, [
                ('http://dead-cache', 'packages.checksum'),
                ('http://dead-cache', 'dep-foo.tar.zst'),
        ])

    def test_install_pkg_falls_back_to_bz2_when_zst_untar_fails(self):
        """If extracting .tar.zst fails on the target, .tar.bz2 is tried next."""
        pm = self._make_pkgmgr()
        repo = StubFetcher(
                'http://repo', {
                        'dep-foo.tar.zst', 'dep-foo.tar.bz2',
                        'dep-bar.tar.zst', 'dep-bar.tar.bz2'
                })
        pm.add_repository(repo)
        untarred = []

        def fake_untar(tarball_path, dest_dir):
            if tarball_path.endswith('.tar.zst'):
                raise error.CmdError(
                        'tar',
                        utils.CmdResult(command='tar',
                                        stderr='zstd: Cannot exec',
                                        exit_status=2))
            untarred.append(tarball_path)

        pm.untar_pkg = fake_untar
        with mock.patch.object(packages, 'DEFAULT_TARBALL_SUFFIX',
                               packages.ZSTD_TARBALL_SUFFIX):
            pm.install_pkg('foo', 'dep', '/fetch', '/install')
            # Subsequent install_pkg calls on the same manager deprioritize
            # .tar.zst and go straight to .tar.bz2.
            repo.calls.clear()
            pm.install_pkg('bar', 'dep', '/fetch', '/install')

        self.assertEqual(untarred,
                         ['/fetch/dep-foo.tar.bz2', '/fetch/dep-bar.tar.bz2'])
        self.assertEqual(repo.calls, [('http://repo', 'dep-bar.tar.bz2')])

    def test_install_pkg_non_untar_cmd_error_does_not_trigger_zst_fallback(
            self):
        """A failing rm -rf on install_dir raises immediately without fallback."""

        def fail_rm_install(cmd, *_args, **_dargs):
            if cmd == 'rm -rf /install':
                raise error.CmdError(
                        cmd, utils.CmdResult(command=cmd, exit_status=1))
            return self._fake_run(cmd)

        pm = packages.PackageManager(self.temp_dir,
                                     do_locking=False,
                                     run_function=fail_rm_install)
        repo = StubFetcher(
                'http://repo', {
                        'dep-foo.tar.zst', 'dep-foo.tar.bz2',
                        'dep-bar.tar.zst', 'dep-bar.tar.bz2'
                })
        pm.add_repository(repo)
        pm.untar_pkg = lambda path, d: None

        with mock.patch.object(packages, 'DEFAULT_TARBALL_SUFFIX',
                               packages.ZSTD_TARBALL_SUFFIX):
            with self.assertRaises(error.CmdError):
                pm.install_pkg('foo', 'dep', '/fetch', '/install')

        self.assertEqual(repo.calls, [
                ('http://repo', 'dep-foo.tar.zst'),
                ('http://repo', 'packages.checksum'),
        ])

    def test_install_pkg_zst_untar_failure_without_bz2_reraises_untar_error(
            self):
        """When .tar.zst untar fails and no .tar.bz2 exists, untar error raises."""
        for default_suffix in (packages.BZIP2_TARBALL_SUFFIX,
                               packages.ZSTD_TARBALL_SUFFIX):
            pm = self._make_pkgmgr()
            repo1 = StubFetcher('http://repo1', {'dep-foo.tar.zst'})
            repo2 = StubFetcher('http://repo2', {'dep-foo.tar.zst'})
            pm.repositories = [repo2, repo1]
            untar_calls = []

            def fail_zst_untar(tarball_path, dest_dir, _calls=untar_calls):
                _calls.append(tarball_path)
                raise error.CmdError(
                        'tar',
                        utils.CmdResult(command='tar',
                                        stderr='zstd: Cannot exec',
                                        exit_status=2))

            pm.untar_pkg = fail_zst_untar
            with mock.patch.object(packages, 'DEFAULT_TARBALL_SUFFIX',
                                   default_suffix):
                with self.assertRaises(error.CmdError):
                    pm.install_pkg('foo', 'dep', '/fetch', '/install')

            # .tar.zst was marked unusable after failing on repo1, so repo2
            # must not fetch or extract it a second time.
            self.assertEqual(untar_calls, ['/fetch/dep-foo.tar.zst'])
            self.assertNotIn(('http://repo2', 'dep-foo.tar.zst'), repo2.calls)

    def test_failed_fetch_resets_cached_existence(self):
        """A failed fetch that deletes dest_path does not leave it marked present."""

        class DeletingFetcher(packages.RepositoryFetcher):
            """Fetcher that deletes dest_path on failure or creates it on success."""

            def __init__(self, url, existing_files, should_fail):
                self.url = url
                self.existing_files = existing_files
                self.should_fail = should_fail

            def fetch_pkg_file(self, filename, dest_path):
                if self.should_fail:
                    self.existing_files.pop(dest_path, None)
                    raise error.PackageFetchError('failed from ' + self.url)
                self.existing_files[dest_path] = 'fresh'

        def strict_md5_run(cmd, *_args, **_dargs):
            if cmd.startswith('md5sum '):
                path = cmd[len('md5sum '):].strip()
                if path not in self.existing_files:
                    raise error.CmdError(
                            cmd, utils.CmdResult(command=cmd, exit_status=1))
            return self._fake_run(cmd)

        # 1. install_pkg path: cached file with stale checksum, first repo
        # fails and deletes it, second repo succeeds without md5sum failing.
        pm = packages.PackageManager(self.temp_dir,
                                     do_locking=False,
                                     run_function=strict_md5_run)
        self.existing_files['/fetch/dep-foo.tar.bz2'] = 'stale'
        pm._checksum_dict = {'dep-foo.tar.bz2': 'updated_md5'}
        pm.repositories = [
                DeletingFetcher('http://ok', self.existing_files, False),
                DeletingFetcher('http://bad', self.existing_files, True),
        ]
        pm.untar_pkg = lambda path, d: None
        pm.install_pkg('foo', 'dep', '/fetch', '/install')
        self.assertEqual(self.existing_files.get('/fetch/dep-foo.tar.bz2'),
                         'fresh')

        # 2. fetch_pkg(use_checksum=True) path.
        self.existing_files['/fetch/dep-bar.tar.bz2'] = 'stale'
        pm._checksum_dict['dep-bar.tar.bz2'] = 'updated_md5'
        pm.fetch_pkg('dep-bar.tar.bz2',
                     '/fetch/dep-bar.tar.bz2',
                     use_checksum=True)
        self.assertEqual(self.existing_files.get('/fetch/dep-bar.tar.bz2'),
                         'fresh')


class TarAndUntarTests(PackageManagerTestBase):
    """Tests for tar_package and untar_pkg command construction and I/O."""

    def test_tar_package_commands(self):
        """tar_package selects the compressor matching the tarball suffix."""
        pm = self._make_pkgmgr()
        recorded = []
        with mock.patch.object(packages.utils, 'system',
                               side_effect=recorded.append), \
                mock.patch.object(os, 'rename'), \
                mock.patch.object(packages, 'has_zstd', return_value=True):
            with mock.patch.object(packages, '_PBZIP2_AVAILABLE', True):
                pm.tar_package('dep-x.tar.bz2', '/src', '/dest')
            with mock.patch.object(packages, '_PBZIP2_AVAILABLE', False):
                pm.tar_package('dep-x.tar.bz2', '/src', '/dest')
            pm.tar_package('dep-x.tar.zst', '/src', '/dest')

        self.assertIn('--use-compress-prog=pbzip2', recorded[0])
        self.assertIn(' -j', recorded[1])
        self.assertIn("--use-compress-prog='zstd -10 --long=27'", recorded[2])

    def test_tar_package_zst_requires_zstd_binary(self):
        """tar_package raises PackagingError if zstd is unavailable."""
        pm = self._make_pkgmgr()
        with mock.patch.object(packages, 'has_zstd', return_value=False):
            with self.assertRaises(error.PackagingError):
                pm.tar_package('dep-x.tar.zst', '/src', '/dest')

    def test_untar_pkg_commands(self):
        """untar_pkg passes an explicit decompressor flag per suffix."""
        pm = self._make_pkgmgr()
        pm.untar_pkg('/tmp/dep-x.tar.bz2', '/dest')
        pm.untar_pkg('/tmp/dep-x.tar.zst', '/dest')

        tar_cmds = [c for c in self.commands if c.startswith('tar ')]
        self.assertEqual(tar_cmds, [
                'tar --no-same-owner -xjf /tmp/dep-x.tar.bz2 -C /dest',
                'tar --no-same-owner -I zstd -xf /tmp/dep-x.tar.zst '
                '-C /dest',
        ])

        with self.assertRaises(ValueError):
            pm.untar_pkg('/tmp/dep-x.tar.gz', '/dest')

    @unittest.skipUnless(packages.has_zstd(), 'zstd binary is not installed')
    def test_tar_and_untar_roundtrip(self):
        """A real directory tree round-trips through both bzip2 and zstd."""
        src_dir = os.path.join(self.temp_dir, 'src')
        os.makedirs(os.path.join(src_dir, 'nested'))
        with open(os.path.join(src_dir, 'hello.txt'), 'w') as f:
            f.write('hello world\n')
        with open(os.path.join(src_dir, 'nested', 'data.txt'), 'w') as f:
            f.write('nested payload\n' * 50)

        out_dir = os.path.join(self.temp_dir, 'out')
        os.makedirs(out_dir)

        pm = packages.PackageManager(self.temp_dir,
                                     do_locking=False,
                                     run_function=utils.run)

        for suffix in (packages.BZIP2_TARBALL_SUFFIX,
                       packages.ZSTD_TARBALL_SUFFIX):
            pkg_name = pm.get_tarball_name('sample', 'dep', suffix)
            tarball_path = pm.tar_package(pkg_name, src_dir, out_dir, ' .')
            self.assertTrue(os.path.isfile(tarball_path))

            dest_dir = os.path.join(self.temp_dir,
                                    'dest_' + suffix.lstrip('.'))
            os.makedirs(dest_dir)
            pm.untar_pkg(tarball_path, dest_dir)

            with open(os.path.join(dest_dir, 'hello.txt')) as f:
                self.assertEqual(f.read(), 'hello world\n')
            with open(os.path.join(dest_dir, 'nested', 'data.txt')) as f:
                self.assertEqual(f.read(), 'nested payload\n' * 50)
            self.assertTrue(os.path.isfile(os.path.join(dest_dir,
                                                        '.checksum')))


class RuntestGateTests(unittest.TestCase):
    """Tests that common_lib/test.py routes both tarball suffixes to install."""

    @staticmethod
    def _load_common_test():
        """Imports common_lib.test lazily, stubbing metrics if protobuf >= 4.

        Note: mock.patch.dict restores sys.modules on exit, which removes both
        the fake frozen_chromite entry and common_lib.test so the mock does not
        leak into other tests; callers in this process should call this helper
        rather than importing common_lib.test directly.
        """
        try:
            from autotest_lib.client.common_lib import test as common_test
            return common_test
        except TypeError:
            with mock.patch.dict(
                    sys.modules, {
                            'autotest_lib.utils.frozen_chromite.lib':
                            mock.MagicMock(metrics=utils.metrics_mock)
                    }):
                from autotest_lib.client.common_lib import test as common_test
                return common_test

    def test_runtest_routes_bz2_and_zst_to_installtest(self):
        """Both .tar.bz2 and .tar.zst URLs trigger _installtest."""
        common_test = self._load_common_test()

        class _InstallCalled(Exception):
            pass

        for url in ('http://h/grp/sleeptest.tar.bz2',
                    'http://h/grp/sleeptest.tar.zst'):
            job = mock.MagicMock()
            with mock.patch.object(common_test,
                                   '_installtest',
                                   side_effect=_InstallCalled) as mock_install:
                with self.assertRaises(_InstallCalled):
                    common_test.runtest(job, url, None, (), {})
                mock_install.assert_called_once_with(job, url)


if __name__ == '__main__':
    unittest.main()
