# Copyright 2017 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Utility to parse git commits."""

import argparse
from dataclasses import dataclass
from datetime import datetime
import re
import subprocess
from typing import List


@dataclass
class Commit:  # pylint: disable=too-many-instance-attributes
    """Data class to represent the Commits."""

    authore_name: str = ""
    authore_email: str = ""
    hash: str = ""
    message: str = ""
    date: datetime = None
    files: [] = None
    effected_packages: [] = None
    url: str = ""
    source_str: str = ""

    def json_str(self):
        """Method to extract a commit as a json element."""
        files_str = "[]"
        if self.files:
            files_str = ("[" + ",".join([
                    f'{{"mode": "{f[0]}", "file": "{f[1]}"}}'
                    for f in self.files
            ]) + "]")
        packages_str = "[]"
        trimed_message = self.message.replace('"', "'").rstrip("\\")
        if self.effected_packages:
            packages_str = ("[" + ",".join([
                    f'{{"package": "{package}"}}'
                    for package in self.effected_packages
            ]) + "]")

        return f"""{{"authore_name": "{self.authore_name}",
        "authore_email": "{self.authore_email}",
        "hash": "{self.hash}",
        "message": "{trimed_message}",
        "date": "{self.date if self.date else ""}",
        "effected_packages": {packages_str},
        "files": {files_str},
        "url": "{self.url}"
        }}""".replace("\n", "")


def parse_commit(text: str):
    """Method to parse the commit text into a commit data class."""
    result = Commit()
    hash_pattern = r"commit (.*)"
    author_pattern = r"Author:\s*([\w ]+) <([\w\d@\.]+)>"
    date_pattern = r"AuthorDate:\s*(.*)"
    message_pattern = r"CommitDate:.*((\n.*)+)(?=\sChange-Id)"
    package_pattern = r"/site_tests/(.*)?/"
    url_pattern = r"\s*Reviewed-on:\s*(.*)"
    files_pattern = r":.* .* .* .* ([M|A|D|R(\d+)])\s+(.*)"
    result.source_str = text
    if match := re.search(hash_pattern, text):
        result.hash = match.group(1)
    match = re.search(author_pattern, text)

    if match and len(match.groups()) >= 2:
        result.authore_name = match.group(1)
        result.authore_email = match.group(2)
    if match := re.search(date_pattern, text):
        result.date = datetime.strptime(match.group(1),
                                        "%a %b %d %H:%M:%S %Y %z")
    if match := re.search(message_pattern, text):
        result.message = match.group(1).strip()

    if match := re.search(url_pattern, text):
        result.url = match.group(1)
    if match := re.findall(files_pattern, text):
        result.files = match
        packages_set = set()
        for _, package_txt in result.files:
            if match := re.search(package_pattern, package_txt):
                packages_set.add(match.group(1))

        result.effected_packages = list(packages_set)

    return result


def list_git_commits():
    """Method which invokes the git command to get the list of all commits in a time frame."""

    git_cmd = [
            "git",
            "log",
            "--raw",
            "--full-diff",
            "--pretty=fuller",
            "--after",
            "2022-06-01",
    ]
    try:
        git_run_result = subprocess.run(git_cmd,
                                        capture_output=True,
                                        check=True)
    except subprocess.CalledProcessError as error:
        print(f"Error in running git command. Git command:{git_cmd}, Error:{error}"
              )
        return ""

    return git_run_result.stdout.decode("utf-8")


def split_commits(text) -> List[str]:
    """Method to split the list of all commits into individual commit messages."""
    split_word = "commit"
    commits_log = [split_word + c for c in text.split("\n\n" + split_word)]
    return commits_log


def main():
    """Main function of the code."""
    parser = argparse.ArgumentParser(
            description="Get the list of recent commits on the repository")
    parser.add_argument(
            "-o",
            "--output",
            dest="json_out_path",
            required=True,
            help="Path to output JSON file",
    )
    args = parser.parse_args()

    git_log = list_git_commits()
    commits_txt = split_commits(git_log)

    commits = []
    for commit_text in commits_txt:
        commit = parse_commit(commit_text)
        commits.append(commit)

    json_converted = ""
    for commit in commits:
        json_converted += commit.json_str() + "\n"

    with open(args.json_out_path, "w", encoding="utf-8") as out_file:
        out_file.write(json_converted)


if __name__ == "__main__":
    main()
