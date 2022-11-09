import argparse
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
    parser = argparse.ArgumentParser(
            description=
            'Update the preview version number in bundle_url_config and upload to gs if necessary.',
            formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument(
            '--to',
            dest='preview_version',
            default=None,
            help=
            'If updating with the latest preview version of CTS, this option is not required.'
            ' Update the version number of preview_version in bundle_url_config and'
            ' upload to gs if necessary. Example:\n'
            '--to 9164413')
    parser.add_argument(
            '--to_latest',
            dest='to_latest',
            default=False,
            action='store_true',
            help='Update with the latest preview version of CTS. Example:\n'
            '--to_latest')
    args = parser.parse_args()
    config_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), 'bundle_url_config.json'))

    if args.preview_version or args.to_latest:
        uprev_preview_version_common.main(config_path, _XTS_NAME, _BRANCH_NAME,
                                          args.preview_version)
    else:
        parser.print_help()
