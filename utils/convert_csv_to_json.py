# Copyright 2023 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Script to convert csv to json file"""

import argparse
import os


def csv_to_json(csv_file, json_file):
    """Converts CSV to json. Skips the header."""
    json_output = ""
    with open(csv_file, "r", encoding="utf-8") as csv_input:
        for row in csv_input:
            test_name, occurances = row.split(",")
            try:
                int(occurances)
                occurances = occurances.strip("\n")
                json_output += f'{{"test_name": "{test_name}", "occurrence": {occurances}}}\n'
            except ValueError:
                print("header bypassed.")
    with open(json_file, "w", encoding="utf-8") as out_file:
        out_file.write(json_output)


def replace_extension(file_path, new_extension):
    """returns the file_path with the new extension"""
    base_name, _ = os.path.splitext(file_path)
    new_file_path = base_name + new_extension
    return new_file_path


def main():
    """Main method to control the flow."""
    parser = argparse.ArgumentParser(
            description="Converts the given CSV file into a JSON.")
    parser.add_argument(
            "-i",
            "--input",
            dest="csv_input_path",
            required=True,
            help="Path to csv input file",
    )
    args = parser.parse_args()

    json_file_path = replace_extension(args.csv_input_path, ".json")

    csv_to_json(args.csv_input_path, json_file_path)


if __name__ == "__main__":
    main()
