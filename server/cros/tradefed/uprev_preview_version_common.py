import logging
import os
import subprocess
import tempfile
from typing import Dict, Optional

import bundle_utils

logging.basicConfig(level=logging.INFO)


class GreenBuildNotFoundException(Exception):
    """Raised when there is no version with all builds being successful."""
    pass


def get_latest_version_name(branch_name: str, abi_list: Dict[str, str]) -> str:
    """Function to get the latest build id using ab command.

    Args:
        branch_name: A string which means branch name where development is taking place.
        abi_list: A dict mapping keys to the corresponding abi file names.

    Returns:
        The latest build ID that is green for all test suite targets.

    Raises:
        GreenBuildNotFoundException: An error when latest 5 builds have all failed to build correctly.
    """
    _MAX_RESULT_SIZE = 5

    build_ids_per_target = []
    for target_name in abi_list.values():
        ab_cmd = [
                '/google/bin/releases/android/ab/ab.par',
                'list_builds',
                f'--branch={branch_name}',
                '--build_status=complete',
                f'--target={target_name}',
                f'--max_results={_MAX_RESULT_SIZE}',
                '--raw',
                '--custom_raw_format={o[buildId]}',
        ]
        # Get the latest 5 correctly built ids whose type is string in the specified branch and target.
        # For example: ['9204700', '9199760', '9198611', '9196948', '9196848']
        logging.info(f'getting build ids: the command is {ab_cmd}.')
        build_ids = subprocess.check_output(ab_cmd,
                                            encoding='utf-8').splitlines()
        build_ids_per_target.append(build_ids)

    if not build_ids_per_target:
        raise bundle_utils.AbiNotFoundException(
                f'invalid input: To get the latest version number in {branch_name} branch, target name is needed. '
                'But now, the abi_list is empty.')

    if len(build_ids_per_target) == 1 and build_ids_per_target[0]:
        return build_ids_per_target[0][0]

    # Find the most recent id in common among all build ids.
    common_build_ids = set(build_ids_per_target[0])
    for ids in build_ids_per_target[1:]:
        common_build_ids = common_build_ids.intersection(ids)

    if not common_build_ids:
        raise GreenBuildNotFoundException(
                f'The latest {_MAX_RESULT_SIZE} builds have all failed to build correctly,'
                ' so pleas use --is_preview option with specifying build id')
    return max(common_build_ids, key=int)


def fetch_artifact(download_dir, branch_name, target_name, xts_name,
                   version_name) -> None:
    """Function to download a test suite to download_dir using fetch_artifact.

    Args:
        download_dir: A string which means the file path where a test suite is downloaded.
        branch_name: A string which means branch name where development is taking place.
        target_name: A string which means the target name in the android-build page.
        xts_name: A string which is one of the test names: (cts, vts).
        version_name: A string which means target build version name.
    """
    fetch_cmd = [
            'fetch_artifact', f'--branch={branch_name}',
            f'--target={target_name}', f'android-{xts_name}.zip',
            f'--bid={version_name}'
    ]
    logging.info(
            f'Downloading to {download_dir}: the command is {fetch_cmd} in {download_dir}.'
    )
    subprocess.check_call(fetch_cmd, cwd=download_dir)


def upload_preview_xts(file_path: str, url_config: Dict[str, str], abi: str,
                       xts_name: str, version_name: str) -> None:
    """Function to upload the preview xTS zip file to multiple places on gs.

    Multiple places are URLs beginning with gs://chromeos-arc-images/ for Googler,
    and gs://chromeos-partner-gts/ for Partner.

    Args:
        file_path: A string which means the file path where a test suite is downloaded.
        url_config: A (dictionary) configuration for this xts bundle.
        abi: A string which means one of the abis (None, 'arm', 'x86', 'arm64', 'x86_64').
        xts_name: A string which is one of the test names: (cts, vts).
        version_name: A string which means target build version name.
    """
    url_config[bundle_utils._PREVIEW_VERSION_NAME] = version_name

    for remote_url in bundle_utils.make_preview_urls(url_config, abi):
        # TODO(b/256108932): Add a method to dryrun this to make it easier to
        # test without actually uploading. Alternatively inject a configuration
        # so that the upload destination can be changed.
        cmd = [
            'gsutil',
            'cp',
            f'{file_path}/android-{xts_name}.zip',
            f'{remote_url}'
        ]
        logging.info(
            f'Uploading to {remote_url}: the command is {cmd}.'
        )
        subprocess.check_call(cmd)
    return


def main(config_path: str,
         xts_name: str,
         branch_name: str,
         version_name: Optional[str] = None) -> None:
    """Function to uprev preview version and upload to gs if necessary.

    Args:
        config_path: A string which means a config json file path to modify.
        xts_name: A string which is one of the test names: (cts, vts).
        branch_name: A string which means branch name where development is taking place.
        version_name: A string which means build id. If none, the latest build id is used.

    Raises:
        ConfigFileNotFoundException: An error when config_path does not exist in the directory.
    """
    if not os.path.isfile(config_path):
        raise bundle_utils.ConfigFileNotFoundException(
                f'invalid input: {config_path} does not exist in the directory.'
        )

    url_config = bundle_utils.load_config(config_path)
    current_version_name = bundle_utils.get_preview_version(url_config)
    abi_info = bundle_utils.get_abi_info(url_config)
    if not version_name:
        version_name = get_latest_version_name(branch_name, abi_info)

    if version_name == current_version_name:
        logging.info(f'{version_name} is the latest version. No work to do.')
        return

    for target_abi, target_name in abi_info.items():
        with tempfile.TemporaryDirectory(
                prefix=f'fetch_artifact_{target_abi}_') as download_dir:
            fetch_artifact(download_dir, branch_name, target_name, xts_name,
                           version_name)
            upload_preview_xts(download_dir, url_config, target_abi, xts_name,
                               version_name)

    bundle_utils.modify_version_name_in_config(
            version_name, config_path, bundle_utils._PREVIEW_VERSION_NAME)
    logging.info(
            f'The value of {bundle_utils._PREVIEW_VERSION_NAME} was correctly uploaded to {version_name}.'
    )
