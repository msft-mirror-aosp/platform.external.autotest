import json
from typing import Dict, List, Optional


_PUBLIC_BASE = 'public_base'
_INTERNAL_BASE = 'internal_base'
_PARTNER_BASE = 'partner_base'
_OFFICIAL_URL_PATTERN = 'official_url_pattern'
_PREVIEW_URL_PATTERN = 'preview_url_pattern'
_ABI_LIST = 'abi_list'

class AbiNotFoundException(Exception):
    """Raised when it fails to find the abi."""
    pass

class BundleNotFoundException(Exception):
    """Raised when it fails to find the bundle."""
    pass


def load_config(config_path: str) -> Dict[str, str]:
    """Function to load a config json file and return the content as a dictionary.

    Args:
        config_path: A string which means config json file path.
                     Refer bundle_url_config_schema.json for json annotation and validation.

    Returns:
        A dict mapping keys to the corresponding urls. These urls are used for building bundle urls.
        For example:

        {'public_base': 'https://dl.google.com/dl/android/cts/',
        'internal_base': 'gs://chromeos-arc-images/cts/bundle/R/',
        'official_url_pattern': 'android-cts-11_r9-linux_x86-%s.zip',
        'preview_url_pattern': 'android-cts-9099362-linux_x86-%s.zip',
        'abi_list': ['arm', 'x86']}
    """
    with open(config_path) as json_object:
        url_config = json.load(json_object)

    return url_config

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
                'invalid input: the abi "%s" is not in the %s' % (abi, url_config[_ABI_LIST])
            )
    else:
        # b/256079546: In GTS, _ABI_LIST is not in url_config, but abi may be specified.
        abi = None

    if bundle_type is None:
        base = url_config.get(_PUBLIC_BASE) or url_config.get(_PARTNER_BASE)
        pattern = url_config.get(_OFFICIAL_URL_PATTERN)
        if not base or not pattern:
            raise BundleNotFoundException(
                'invalid input: "%s" requires %s or %s and %s but they are not set. '
                'The url_config keys are "%s"' % (bundle_type, _PUBLIC_BASE, _PARTNER_BASE, _OFFICIAL_URL_PATTERN, ', '.join(list(url_config)))
            )

    elif bundle_type == 'LATEST':
        base = url_config.get(_INTERNAL_BASE)
        pattern = url_config.get(_OFFICIAL_URL_PATTERN)
        if not base or not pattern:
            raise BundleNotFoundException(
                'invalid input: "%s" requires %s and %s but they are not set. '
                'The url_config keys are "%s"' % (bundle_type, _INTERNAL_BASE, _OFFICIAL_URL_PATTERN, ', '.join(list(url_config)))
            )

    elif bundle_type == 'DEV':
        base = url_config.get(_INTERNAL_BASE)
        pattern = url_config.get(_PREVIEW_URL_PATTERN)
        if not base or not pattern:
            raise BundleNotFoundException(
                'invalid input: "%s" requires %s and %s but they are not set. '
                'The url_config keys are "%s"' % (bundle_type, _INTERNAL_BASE, _PREVIEW_URL_PATTERN, ', '.join(list(url_config)))
            )

    elif bundle_type == 'DEV_MOBLAB':
        base = url_config.get(_PARTNER_BASE)
        pattern = url_config.get(_PREVIEW_URL_PATTERN)
        if not base or not pattern:
            raise BundleNotFoundException(
                'invalid input: "%s" requires %s and %s but they are not set. '
                'The url_config keys are "%s"' % (bundle_type, _PARTNER_BASE, _PREVIEW_URL_PATTERN, ', '.join(list(url_config)))
            )

    elif bundle_type == 'DEV_WAIVER':
        base = url_config.get(_INTERNAL_BASE)
        pattern = url_config.get(_PREVIEW_URL_PATTERN)
        if not base or not pattern:
            raise BundleNotFoundException(
                'invalid input: "%s" requires %s and %s but they are not set. '
                'The url_config keys are "%s"' % (bundle_type, _INTERNAL_BASE, _PREVIEW_URL_PATTERN, ', '.join(list(url_config)))
            )

    else:
        raise BundleNotFoundException(
            'invalid input: the bundle type "%s" is not expected' % bundle_type
        )

    return base + pattern % abi if abi else base + pattern
