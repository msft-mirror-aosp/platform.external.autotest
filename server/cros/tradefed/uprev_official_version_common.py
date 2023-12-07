import logging
import os
import subprocess
import urllib.request

import bundle_utils

logging.basicConfig(level=logging.INFO)


class InvalidURLError(Exception):
    """Raised when the bundle URL is found invalid."""
    pass


def check_url_is_valid(url: str) -> bool:
    """Checks if the given bundle URL points to a existing file.

    Args:
        url: The bundle URL. Supported schemes are https:// and gs://

    Raises:
        InvalidURLError if the URL isn't valid.
        ValueError if the URL scheme isn't supported.
    """
    logging.info('Checking if bundle URL is valid: %s', url)

    if url.startswith('https://'):
        req = urllib.request.Request(url, method='HEAD')
        with urllib.request.urlopen(req) as f:
            pass
        if f.status != 200:
            raise InvalidURLError(f'HTTP returns status {f.status}: {url}')
    elif url.startswith('gs://'):
        try:
            subprocess.check_output(['gsutil', 'stat', url])
        except subprocess.CalledProcessError as e:
            raise InvalidURLError(f'gsutil exited with non-zero status: {url}')
    else:
        raise ValueError(f'Unsupported URL scheme: {url.split(":")[0]}')


def main(config_path: str, version_name: str) -> None:
    """Function to uprev official version.

    Args:
        config_path: A string which means a config json file path to modify.
        version_name: A string which is set as new version.

    Raises:
        ConfigFileNotFoundException: An error when config_path does not exist in the directory
    """
    if not os.path.isfile(config_path):
        raise bundle_utils.ConfigFileNotFoundException(
                f'invalid input: {config_path} does not exist in the directory'
        )

    url_config = bundle_utils.load_config(config_path)
    current_version_name = bundle_utils.get_official_version(url_config)
    if version_name == current_version_name:
        logging.info(
                f'Current version "{current_version_name}" is the same as the one you specified.'
        )
        return

    bundle_utils.set_official_version(url_config, version_name)
    for bundle_type in (None, 'LATEST'):
        urls = bundle_utils.make_urls_for_all_abis(url_config, bundle_type)
        for url in urls:
            check_url_is_valid(url)

    bundle_utils.write_url_config(url_config, config_path)
