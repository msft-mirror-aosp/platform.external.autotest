import json
from typing import Dict, List, Optional


_PUBLIC_BASE = 'public_base'
_INTERNAL_BASE = 'internal_base'
_PARTNER_BASE = 'partner_base'
_OFFICIAL_URL_PATTERN = 'official_url_pattern'
_PREVIEW_URL_PATTERN = 'preview_url_pattern'
_OFFICIAL_VERSION_NAME = 'official_version_name'
_PREVIEW_VERSION_NAME = 'preview_version_name'
_ABI_LIST = 'abi_list'
_BUNDLE_PASSOWORD = 'bundle_password'


class AbiNotFoundException(Exception):
    """Raised when it fails to find the abi."""
    pass

class BundleNotFoundException(Exception):
    """Raised when it fails to find the bundle."""
    pass


class ConfigFileNotFoundException(Exception):
    """Raised when it fails to find the config file."""
    pass


class InvalidVersionNameKeyException(Exception):
    """Raised when an inappropriate version name is specified."""
    pass


class NoVersionNameException(Exception):
    """Raised when it fails to find the valid version name in url_config."""
    pass


class NoSuiteNameException(Exception):
    """Raised when it fails to find valid suite name in url_config."""


# TODO(b/256107709): Use class whose constructor is url_config to avoid to return arbitrary dictionary.
def load_config(config_path: str) -> Dict[str, str]:
    """Function to load a config json file and return the content as a dictionary.

    Args:
        config_path: A string which means a config json file path.
                     Refer bundle_url_config_schema.json for json annotation and validation.

    Returns:
        A dict mapping keys to the corresponding urls. These urls are used for building bundle urls.
        For example:

        {
            "public_base": "https://dl.google.com/dl/android/cts/",
            "internal_base": "gs://chromeos-arc-images/cts/bundle/R/",
            "partner_base": "gs://chromeos-partner-gts/R/",
            "official_url_pattern": "android-cts-%s-linux_x86-%s.zip",
            "preview_url_pattern": "android-cts-%s-linux_x86-%s.zip",
            "official_version_name": "11_r9",
            "preview_version_name": "9164413",
            "abi_list": {
                "arm": "test_suites_arm64",
                "x86": "test_suites_x86_64"
            }
        }
    """
    with open(config_path) as json_object:
        url_config = json.load(json_object)

    return url_config


def get_suite_name(url_config: Dict[str, str]) -> str:
    """Returns the suite name for unzipping the bundle.

    Returns:
        The suite name (cts/gts/sts) obtained from offcial_url_pattern.
    """
    url_pattern = url_config[_OFFICIAL_URL_PATTERN]
    suite_name = url_pattern.split('-', 2)[1]
    valid_suites_set = {'cts', 'gts', 'sts', 'vts', 'cts_instant'}
    if suite_name in valid_suites_set:
        return suite_name
    raise NoSuiteNameException(f'Invalid suite name {suite_name}')


def get_bundle_password(url_config: Dict[str, str]) -> str:
    """Returns the password for unzipping the bundle.

    Returns:
        A password required for unzipping the bundle. Returns an empty
        string if no password is required.
    """
    return url_config.get(_BUNDLE_PASSOWORD, '')


def get_official_version(url_config: Dict[str, str]) -> str:
    """Function to get the official version name from url_config.

    Args:
        url_config: A dict mapping keys to the corresponding urls. These urls are used for building bundle urls.

    Returns:
        A string which means a official version name in build_url_config.json.
        For example: '11_r9'

    Raises:
        NoVersionNameException: An error when url_config does not contain the official version key.
    """
    if _OFFICIAL_VERSION_NAME not in url_config:
        raise NoVersionNameException(
                'invalid input: To change the build id, %s is needed in bundle_url_config, '
                'But the current url_config keys are "%s"' %
                (_OFFICIAL_VERSION_NAME, ', '.join(list(url_config))))
    return url_config[_OFFICIAL_VERSION_NAME]


def get_preview_version(url_config: Dict[str, str]) -> str:
    """Function to get the preview version name from url_config.

    Args:
        url_config: A dict mapping keys to the corresponding urls. These urls are used for building bundle urls.

    Returns:
        A string which means a preview version name in build_url_config.json.
        For example: '9164413'

    Raises:
        NoVersionNameException: An error when url_config does not contain the preview version key.
    """
    if _PREVIEW_VERSION_NAME not in url_config:
        raise NoVersionNameException(
                'invalid input: To change the build id, %s is needed in bundle_url_config, '
                'But the current url_config keys are "%s"' %
                (_PREVIEW_VERSION_NAME, ', '.join(list(url_config))))
    return url_config[_PREVIEW_VERSION_NAME]


def set_official_version(url_config: Dict[str, str], version_name: str):
    """Sets the official version field of url_config.

    Args:
        url_config: The config.
        version_name: The version to set to.
    """
    url_config[_OFFICIAL_VERSION_NAME] = version_name


def set_preview_version(url_config: Dict[str, str], version_name: str):
    """Sets the preview version field of url_config.

    Args:
        url_config: The config.
        version_name: The version to set to.
    """
    url_config[_PREVIEW_VERSION_NAME] = version_name


def get_abis(url_config: Dict[str, str]) -> List[Optional[str]]:
    """Retrieves ABIs listed in url_config.

    Args:
        url_config: The config.

    Returns:
        A list of ABIs supported. If no ABI is specified for the bundle (for
        example GTS), a list with a single item None is returned.
    """
    if _ABI_LIST in url_config:
        return list(url_config[_ABI_LIST])
    return [None]


def get_abi_info(url_config: Dict[str, str]) -> Dict[str, str]:
    """Function to get the abi information from url_config.

    Args:
        url_config: A dict mapping keys to the corresponding urls. These urls are used for building bundle urls.

    Returns:
        A dict mapping keys to the corresponding abi information.

    Raises:
        AbiNotFoundException: An error when url_config does not contain abi_list key.
    """
    if _ABI_LIST not in url_config:
        raise AbiNotFoundException(
                'invalid input: To get an abi file name, %s is needed in bundle_url_config, '
                'But the current url_config keys are "%s"' %
                (_ABI_LIST, ', '.join(list(url_config))))
    return url_config[_ABI_LIST]


def write_url_config(url_config: Dict[str, str], config_path: str):
    """Writes url_config to the given path as JSON.

    Args:
        url_config: The config.
        config_path: The path to write to.
    """
    with open(config_path, mode="w") as f:
        json.dump(url_config, f, indent=4)


def make_urls_for_all_abis(url_config: Dict[str, str], bundle_type: Optional[str]) -> List[str]:
    """Function to make the list of all bundle urls for the given bundle_type.

    Args:
        url_config: A bundle config object.
        bundle_type: A string which means one of the bundle types (None, 'LATEST', 'DEV').

    Returns:
        A list of strings which mean path to the zip file in gs or public.
        For example:

        ['https://dl.google.com/dl/android/cts/android-cts-11_r9-linux_x86-arm.zip',
        'https://dl.google.com/dl/android/cts/android-cts-11_r9-linux_x86-x86.zip']
    """
    return [make_bundle_url(url_config, bundle_type, abi) for abi in url_config.get(_ABI_LIST, [None])]

def make_bundle_url(url_config: Dict[str, str], bundle_type: Optional[str], abi: Optional[str]) -> str:
    """Function to make the bundle url for the bundle_type and the abi.

    Args:
        url_config: A bundle config object.
        bundle_type: A string which means one of the bundle types (None, 'LATEST', 'DEV', 'DEV_MOBLAB', 'DEV_WAIVER').
        abi: A string which means one of the abis (None, 'arm', 'x86', 'arm64', 'x86_64').

    Returns:
        A string which means the path to the zip file in gs or public.
        For example:

        'https://dl.google.com/dl/android/cts/android-cts-11_r9-linux_x86-arm.zip'

    Raises:
        AbiNotFoundException: An error when abi does not correspond to any of the possible abi.
        BundleNotFoundException: An error when bundle_type is not expected or
                                 url_config does not contain the required information.
    """
    if _ABI_LIST in url_config:
        if abi not in url_config[_ABI_LIST]:
            raise AbiNotFoundException(
                    'invalid input: the abi "%s" is not in the abi_info %s' %
                    (abi, url_config[_ABI_LIST]))
    else:
        # b/256079546: In GTS, _ABI_LIST is not in url_config, but abi may be specified.
        abi = None

    if bundle_type is None:
        base = url_config.get(_PUBLIC_BASE) or url_config.get(_PARTNER_BASE)
        pattern = url_config.get(_OFFICIAL_URL_PATTERN)
        version_name = url_config.get(_OFFICIAL_VERSION_NAME)
        if not base or not pattern or not version_name:
            raise BundleNotFoundException(
                    'invalid input: "%s" requires %s or %s, %s and %s but they are not set. '
                    'The url_config keys are "%s"' %
                    (bundle_type, _PUBLIC_BASE, _PARTNER_BASE,
                     _OFFICIAL_URL_PATTERN, _OFFICIAL_VERSION_NAME, ', '.join(
                             list(url_config))))

    elif bundle_type == 'LATEST':
        base = url_config.get(_INTERNAL_BASE)
        pattern = url_config.get(_OFFICIAL_URL_PATTERN)
        version_name = url_config.get(_OFFICIAL_VERSION_NAME)
        if not base or not pattern or not version_name:
            raise BundleNotFoundException(
                    'invalid input: "%s" requires %s, %s and %s but they are not set. '
                    'The url_config keys are "%s"' %
                    (bundle_type, _INTERNAL_BASE, _OFFICIAL_URL_PATTERN,
                     _OFFICIAL_VERSION_NAME, ', '.join(list(url_config))))

    elif bundle_type == 'DEV':
        base = url_config.get(_INTERNAL_BASE)
        pattern = url_config.get(_PREVIEW_URL_PATTERN)
        version_name = url_config.get(_PREVIEW_VERSION_NAME)
        if not base or not pattern or not version_name:
            raise BundleNotFoundException(
                    'invalid input: "%s" requires %s, %s and %s but they are not set. '
                    'The url_config keys are "%s"' %
                    (bundle_type, _INTERNAL_BASE, _PREVIEW_URL_PATTERN,
                     _PREVIEW_VERSION_NAME, ', '.join(list(url_config))))

    elif bundle_type == 'DEV_MOBLAB':
        base = url_config.get(_PARTNER_BASE)
        pattern = url_config.get(_PREVIEW_URL_PATTERN)
        version_name = url_config.get(_PREVIEW_VERSION_NAME)
        if not base or not pattern or not version_name:
            raise BundleNotFoundException(
                    'invalid input: "%s" requires %s, %s and %s but they are not set. '
                    'The url_config keys are "%s"' %
                    (bundle_type, _PARTNER_BASE, _PREVIEW_URL_PATTERN,
                     _PREVIEW_VERSION_NAME, ', '.join(list(url_config))))

    elif bundle_type == 'DEV_WAIVER':
        base = url_config.get(_INTERNAL_BASE)
        pattern = url_config.get(_PREVIEW_URL_PATTERN)
        version_name = url_config.get(_PREVIEW_VERSION_NAME)
        if not base or not pattern or not version_name:
            raise BundleNotFoundException(
                    'invalid input: "%s" requires %s, %s and %s but they are not set. '
                    'The url_config keys are "%s"' %
                    (bundle_type, _INTERNAL_BASE, _PREVIEW_URL_PATTERN,
                     _PREVIEW_VERSION_NAME, ', '.join(list(url_config))))

    else:
        raise BundleNotFoundException(
            'invalid input: the bundle type "%s" is not expected' % bundle_type
        )

    return base + pattern % (version_name,
                             abi) if abi else base + pattern % version_name


def make_preview_urls(url_config: Dict[str, str], abi: str) -> List[str]:
    """Function to make possible preview urls from url_config.

    Args:
        url_config: A bundle config object.
        abi: A string which means one of the abis ('arm', 'x86').

    Returns:
        A list of strings of possible urls that contain the preview_base url.
    """
    if _PARTNER_BASE not in url_config:
        return [make_bundle_url(url_config, 'DEV', abi)]

    return [
            make_bundle_url(url_config, bundle, abi)
            for bundle in ['DEV', 'DEV_MOBLAB']
    ]
