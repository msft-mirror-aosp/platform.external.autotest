import os
import sys

tradefed_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), '..', '..', 'cros',
                     'tradefed'))
sys.path.append(tradefed_path)
import uprev_preview_version_common

_XTS_NAME = 'cts'
_BRANCH_NAME = 'aosp-pie-cts-dev'

# TODO(b/256108932): Add --test_config flag for test upload to gs.
if __name__ == '__main__':
    config_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), 'bundle_url_config.json'))

    uprev_preview_version_common.main(
            config_path, _XTS_NAME, _BRANCH_NAME,
            os.path.dirname(os.path.realpath(__file__)))
