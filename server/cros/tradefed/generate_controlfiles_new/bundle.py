# Copyright 2023 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import logging
import os
import re
import stat
import subprocess
import tempfile
import typing
import zipfile

import bundle_utils


class Bundle(typing.NamedTuple):
    """Represents a xTS bundle.

    Attributes:
        abi: The bundle's ABI, or None if unspecified (in the case of GTS).
        build: The Tradefed build ID, e.g. '10555997'.
        revision: The xTS revision string, e.g. '13_r5'.
        source_type: Either of 'MOBLAB', 'LATEST', 'DEV'.
        modules: Set of modules provided by this bundle.
    """
    abi: typing.Optional[str]
    build: str
    revision: str
    source_type: str
    modules: typing.FrozenSet[str]

    @staticmethod
    def download(config, url_config, source_type, abi, cache_dir):
        # TODO clean this up
        bundle_type = None if source_type == 'MOBLAB' else source_type

        url = bundle_utils.make_bundle_url(url_config, bundle_type, abi)
        bundle_password = bundle_utils.get_bundle_password(url_config)
        tradefed_path = config['TRADEFED_EXECUTABLE_PATH']
        extra_executables = config.get('EXECUTABLE_PATH_LIST', [])
        modules, build, revision = _fetch_tradefed_and_list_modules(
                url, tradefed_path, extra_executables, cache_dir,
                bundle_password)
        modules = [
                m for m in modules
                if m not in config.get('EXCLUDE_MODULES', [])
        ]
        return Bundle(abi=abi,
                      build=build,
                      revision=revision,
                      source_type=source_type,
                      modules=modules)


def _download(uri, destination):
    """Download |uri| to local |destination|.

       |destination| must be a file path (not a directory path)."""
    if uri.startswith('http://') or uri.startswith('https://'):
        subprocess.check_call(['wget', uri, '-O', destination])
    elif uri.startswith('gs://'):
        subprocess.check_call(['gsutil', 'cp', uri, destination])
    else:
        raise Exception


def _unzip(filename, destination, password=''):
    """Unzips a zip file to the destination directory.

    Args:
        filename is the file to be unzipped.
        destination is where the zip file would be extracted.
        password is an optional value for unzipping. If the zip file is not
            encrypted, the value has no effect.
    """
    # We are trusting Android to have a valid zip file for us.
    with zipfile.ZipFile(filename) as zf:
        zf.extractall(path=destination, pwd=password.encode())


def _fixup_tradefed_executable_bits(basepath, executables):
    """ Do chmod u+x for files to be executed, because Python's zipfile
    module does not set the executable bit.
    """
    for subpath in executables:
        path = os.path.join(basepath, subpath)
        if os.path.exists(path):
            os.chmod(path, os.stat(path).st_mode | stat.S_IEXEC)


def _get_tradefed_build(line):
    """Gets the build of Android CTS from tradefed.

    @param line Tradefed identification output on startup. Example:
                Android Compatibility Test Suite 7.0 (3423912)
    @return Tradefed CTS build. Example: 2813453.
    """
    # Sample string:
    # - Android Compatibility Test Suite 7.0 (3423912)
    # - Android Compatibility Test Suite for Instant Apps 1.0 (4898911)
    # - Android Google Mobile Services (GMS) Test Suite 6.0_r1 (4756896)
    m = re.search(r' \((.*)\)', line)
    if m:
        return m.group(1)
    logging.warning('Could not identify build in line "%s".', line)
    return '<unknown>'


def _get_tradefed_revision(line):
    """Gets the revision of Android CTS from tradefed.

    @param line Tradefed identification output on startup.
                Example:
                 Android Compatibility Test Suite 6.0_r6 (2813453)
                 Android Compatibility Test Suite for Instant Apps 1.0 (4898911)
    @return Tradefed CTS revision. Example: 6.0_r6.
    """
    tradefed_identifier_list = [
            r'Android Google Mobile Services \(GMS\) Test Suite (.*) \(',
            r'Android Compatibility Test Suite(?: for Instant Apps)? (.*) \(',
            r'Android Vendor Test Suite (.*) \(',
            r'Android Security Test Suite (.*) \('
    ]

    for identifier in tradefed_identifier_list:
        m = re.search(identifier, line)
        if m:
            return m.group(1)

    logging.warning('Could not identify revision in line "%s".', line)
    return None


def _get_tradefed_data(path, tradefed_path, extra_executables=None):
    """Queries tradefed to provide us with a list of modules.

    Notice that the parsing gets broken at times with major new CTS drops.
    """
    executables = extra_executables.copy(
    ) if extra_executables is not None else []
    executables.append(tradefed_path)
    _fixup_tradefed_executable_bits(path, executables)

    tradefed = os.path.join(path, tradefed_path)
    logging.info('Calling tradefed for list of modules.')
    # tradefed terminates itself if stdin is not a tty.
    # Starting V the modules list is printed to stderr.
    tradefed_output = subprocess.check_output(
            [tradefed, 'list', 'modules'],
            stdin=subprocess.DEVNULL,
            stderr=subprocess.STDOUT).decode()

    _ABI_PREFIXES = ('arm', 'x86')
    _MODULE_PREFIXES = ('Cts', 'cts-', 'signed-Cts', 'vm-tests-tf', 'Sts')

    modules = set()
    build = '<unknown>'
    revision = None
    for line in tradefed_output.splitlines():
        # Android Compatibility Test Suite 7.0 (3423912)
        if (line.startswith('Android Compatibility Test Suite ')
                    or line.startswith('Android Google ')
                    or line.startswith('Android Vendor Test Suite')
                    or line.startswith('Android Security Test Suite')):
            logging.info('Unpacking: %s.', line)
            build = _get_tradefed_build(line)
            revision = _get_tradefed_revision(line)
        elif line.startswith(_ABI_PREFIXES):
            # Newer CTS shows ABI-module pairs like "arm64-v8a CtsNetTestCases"
            modules.add(line.split()[1])
        elif line.startswith(_MODULE_PREFIXES):
            # Old CTS plainly lists up the module name
            modules.add(line)
        elif line.isspace() or line.startswith('Use "help"'):
            pass
        else:
            logging.warning('Ignoring "%s"', line)

    if not modules:
        raise Exception("no modules found.")
    return list(modules), build, revision


def _fetch_tradefed_and_list_modules(url, tradefed_path, extra_executables,
                                     cache_dir, bundle_password):
    with tempfile.TemporaryDirectory(prefix='cts-android_') as tmp:
        if cache_dir is not None:
            assert os.path.isdir(cache_dir)
            bundle = os.path.join(cache_dir, os.path.basename(url))
            if not os.path.exists(bundle):
                logging.info('Downloading to %s.', cache_dir)
                _download(url, bundle)
        else:
            bundle = os.path.join(tmp, os.path.basename(url))
            logging.info('Downloading to %s.', tmp)
            _download(url, bundle)
        logging.info('Extracting %s.', bundle)
        _unzip(bundle, tmp, bundle_password)
        modules, build, revision = _get_tradefed_data(tmp, tradefed_path,
                                                      extra_executables)
        if not revision:
            raise Exception('Could not determine revision.')
    return modules, build, revision
