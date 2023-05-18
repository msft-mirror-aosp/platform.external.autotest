import argparse
import os
import sys

tradefed_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), '..', '..', 'cros',
                     'tradefed'))
sys.path.append(tradefed_path)
import uprev_official_version_common

# TODO(b/256108932): Add --test_config flag for test upload to gs.
if __name__ == '__main__':
    parser = argparse.ArgumentParser(
            description=
            'Update the official version number in bundle_url_config.',
            formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument(
            '--to',
            dest='official_version',
            required=True,
            help=
            'Update the official version number of official_version in bundle_url_config. Example:\n'
            '--official_version 11_r9')
    args = parser.parse_args()
    config_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), 'bundle_url_config.json'))

    uprev_official_version_common.main(config_path, args.official_version)
