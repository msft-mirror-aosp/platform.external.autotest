# Copyright 2023 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Script to analyse the control files in the autotest repo"""

import argparse
from dataclasses import dataclass
import os
import re
from typing import List


@dataclass
class ControlFile:
    """Data class representing control files."""

    path: str = None
    name: str = None
    suites: [] = List[str]
    tast_wrapper: bool = False
    contacts: [] = List[str]
    package: str = None

    def json_str(self):
        """Method to convert the dataclass to json representation."""

        suites_str = "[]"
        if self.suites:
            suites_str = ("[" + ",".join(
                    [f'{{"suite": "{suite}"}}'
                     for suite in self.suites]) + "]")
        contacts_str = "[]"
        if self.contacts:
            contacts_str = ("[" + ",".join([
                    f'{{"contact": "{contact}"}}' for contact in self.contacts
            ]) + "]")
        return f"""{{"path": "{self.path}",
      "name": "{self.name}",
      "suites": {suites_str},
      "tast_wrapper": "{self.tast_wrapper}",
      "contacts": {contacts_str},
      "package": "{self.package}"
    }}""".replace("\n", "")


def walk_files(root_dir):
    """Method to traverse the control files in the given root directory."""
    result = []
    pattern = "^control((?!.txt).)*$"
    for root, _, files in os.walk(root_dir):
        for filename in files:
            if re.search(pattern, filename):
                file_path = os.path.abspath(os.path.join(root, filename))
                result.append(file_path)
    return result


def parse_control_files(file_paths):  # pylint: disable=too-many-locals
    """Method to parse the information from the control files."""

    result = []
    test_names = set("")
    contacts_pattern = r'[\'|"]contacts[\'|"]: \[([\s\S]+?)\]'
    author_pattern = r'AUTHOR\s7*=\s*["\'](.*)["\']'
    name_pattern = r'NAME\s*=\s*[\'|"](\w|.+)[\'|"]'
    tast_presence_check = r"job\.run_test\(\s*\'tast\'"
    package_pattern = r".*/site_tests/(.*)/"
    suite_pattern = r"suite:(\w+)"
    for file_path in file_paths:
        control_instance = ControlFile(path=file_path)
        if match := re.search(package_pattern, file_path):
            control_instance.package = match.group(1)
        with open(file_path, "r", encoding="utf-8") as control_file:
            file_contents = control_file.read()
            file_contents.replace("\n", "")
            if match := re.search(name_pattern, file_contents):
                name = match.group(1)
                if name in test_names:
                    continue
                test_names.add(name)
                control_instance.name = name
            if matches := re.search(contacts_pattern, file_contents):
                control_instance.contacts = re.findall(r'[\'"]([^"]+)[\'|"]',
                                                       matches.group(1))
            elif matches := re.search(author_pattern, file_contents):
                control_instance.contacts = re.findall(author_pattern,
                                                       file_contents)
            control_instance.tast_wrapper = (re.search(tast_presence_check,
                                                       file_contents)
                                             is not None)
            control_instance.package = os.path.basename(
                    os.path.dirname(file_path))
            control_instance.suites = re.findall(suite_pattern, file_contents)
            result.append(control_instance)
    return result


def main():
    """Main function to parse the control files."""
    root_dirs = [
            "../client/site_tests",
            "../server/site_tests",
            "../../../../../infra/autotest-drone/client/site_tests",
            "../../../../../infra/autotest-drone/server/site_tests",
            "../../../autotest-private/",
            "../../../autotest-tests-cheets//server/site_tests/",
    ]
    parser = argparse.ArgumentParser(
            description=
            f"Parses every control file in these directories:{root_dirs}")
    parser.add_argument(
            "-o",
            "--output",
            dest="json_out_path",
            required=True,
            help="Path to output JSON file",
    )
    args = parser.parse_args()

    control_instances = []

    control_files = []
    for root_dir in root_dirs:
        control_files.extend(walk_files(root_dir))

    control_instances = parse_control_files(control_files)

    json_converted = ""
    for control_instance in control_instances:
        json_converted += control_instance.json_str() + "\n"

    with open(args.json_out_path, "w", encoding="utf-8") as out_file:
        out_file.write(json_converted)

    print(len(control_instances))


if __name__ == "__main__":
    main()
