import logging
import os

import bundle_utils

logging.basicConfig(level=logging.INFO)


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

    bundle_utils.modify_version_name_in_config(version_name, config_path,
                                               'official_version_name')
