# Copyright 2023 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import logging
import tempfile
import os.path
import typing

import bundle_utils
import generate_controlfiles_common as gcc


class Bundle(typing.NamedTuple):
    abi: str
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
        return Bundle(abi=abi,
                      build=build,
                      revision=revision,
                      source_type=source_type,
                      modules=modules)


def _fetch_tradefed_and_list_modules(url, tradefed_path, extra_executables,
                                     cache_dir, bundle_password):
    with tempfile.TemporaryDirectory(prefix='cts-android_') as tmp:
        if cache_dir is not None:
            assert os.path.isdir(cache_dir)
            bundle = os.path.join(cache_dir, os.path.basename(url))
            if not os.path.exists(bundle):
                logging.info('Downloading to %s.', cache_dir)
                gcc.download(url, bundle)
        else:
            bundle = os.path.join(tmp, os.path.basename(url))
            logging.info('Downloading to %s.', tmp)
            gcc.download(url, bundle)
        logging.info('Extracting %s.', bundle)
        gcc.unzip(bundle, tmp, bundle_password)
        modules, build, revision = gcc.get_tradefed_data(
                tmp, tradefed_path, extra_executables)
        if not revision:
            raise Exception('Could not determine revision.')
    return modules, build, revision
