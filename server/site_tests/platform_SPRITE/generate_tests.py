"""Creates control files for SPRITE suite."""

import os
import argparse


def open_template(template_path):
    """Opens a template file.
    Args:
        template_path: Path to the template file.

    Returns:
        The template context
    """

    template = ''
    with open(template_path, "r") as file:
        template = file.read()
    return template


def main():
    """Creates control files for SPRITE general and quick suites."""

    parser = argparse.ArgumentParser(
        description='Generates control files for sprite test suite.')
    parser.add_argument('--suite_type', required=True,
                        help='Type of the suite (e.g. general, quick')

    args = parser.parse_args()
    suite_type_tag = ''
    iterations = 0
    if args.suite_type == 'quick':
        iterations = 1
        suite_type_tag = '_quick'
    elif args.suite_type == 'general':
        iterations = 10
        suite_type_tag = ''
    else:
        raise ValueError("Invalid suite_type. Valid values: quick, general.")

    template_path = os.path.join('./templace.control.performance_cuj_sprite')
    tests_expresion = [
        "tabswitchcuj2_basic_noproxy",
        "quickcheckcuj2_basic_wakeup",
        "quickcheckcuj2_basic_unlock",
        "everydaymultitaskingcuj_basic_ytmusic",
        "videocuj2_basic_youtube_web",
        "videocuj2_basic_youtube_app",
        "googlemeetcuj_basic_two",
        "googlemeetcuj_basic_small",
        "googlemeetcuj_basic_large",
        "googlemeetcuj_basic_class",
        "tabswitchcuj2_plus_noproxy",
        "everydaymultitaskingcuj_plus_ytmusic",
        "googlemeetcuj_plus_large",
        "googlemeetcuj_plus_class",
        "tabswitchcuj2_premium_noproxy",
        "videocuj2_premium_youtube_web",
        "videocuj2_premium_youtube_app",
        "googlemeetcuj_premium_large"
        ]

    TESTS = [{'test_name':t,'test_expr':f'meta.RunCUJ.{t}'} for t in tests_expresion]

    for test in TESTS:
        template = open_template(template_path)
        control_file_contents = template.format(
            name=test['test_name'], test_exprs=test['test_expr'], suite_tag=suite_type_tag, iteration=iterations)

        control_file_path = os.path.join('control.performance_cuj_meta_run_cuj_%s' % test['test_name'] + suite_type_tag)
        with open(control_file_path, 'w') as f:
            f.write(control_file_contents)
            print(f'file saved at: {control_file_path}')

if __name__ == '__main__':
    main()
