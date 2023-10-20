# Copyright 2023 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Functions to parse and modify control files when updating METADATA."""

import ast
import json

def format_string_value(s, indent=8, target_length=60):
    """Format a string value for printing in a control file.

    Args:
        s: the string to be formatted
        indent: the indent when multiple lines are needed
        target_length: the target line length for the file

    Returns:
        A formatted string.
    """
    value = ' '.join(s.split()) # Remove excess spaces/newlines.
    if len(value) < target_length:
        return f'"{value}"'
    printed_lines = []
    value = value.replace('"', '\"')
    words = value.split(' ')
    curr = ''
    for word in words:
        if len(curr) + len(word) + 1 < target_length:
            curr += word + ' '
        else:
            printed_lines.append(curr.strip())
            curr = word + ' '
    if curr != '':
        printed_lines.append(curr.strip())
    join_value = '"\n' + ' ' * indent + '"'
    return f'("{join_value.join(printed_lines)}")'

def format_list_value(l, indent=8):
    """Format a list value for printing in a control file.

    Args:
        l: the list to be formatted
        indent: the indent when multiple lines are needed

    Returns:
        A formatted string representing the list.
    """
    if len(l) <= 1:
        return json.dumps(l)
    # For lists with multiple string values, split them onto multiple lines.
    # E.g.: [\n"foo",\n        "bar",\n    ]
    value = json.dumps(l, indent=indent)
    return value.replace('\n]', ',\n    ]')

def format_metadata(metadata_dict):
    """Return a formatted string representing the given metadata.

    Args:
        metadata_dict: the metadata to be formatted

    Returns:
        A formatted string of the form 'METADATA = {...}'. This output can be
        swapped in with the previous METADATA declaraction in a file.
    """
    inner_values = ''
    for key in metadata_dict:
        value = metadata_dict[key]
        printed_value = json.dumps(value)
        if isinstance(value, list):
            printed_value = format_list_value(value)
        if isinstance(value, str):
            printed_value = format_string_value(value, indent=len(key)+9)
        if isinstance(value, bool):
            printed_value = "True" if value else "False"
        inner_values += f'    "{key}": {printed_value},\n'
    return f'METADATA = {{\n{inner_values}}}'


class ControlFile():
    """Class representing a Control file to be edited (or skipped)."""
    def __init__(self, path):
        self.path = path
        self.name_value = ''
        self.contents = '' # The contents of the file
        self.metadata_start = -1 # The index of the M in METADATA
        self.metadata_end = -1 # The index after the closing }
        self.isChanged = False

        self.metadata = {}
        self.is_valid = self.find_metadata_elt()

    def find_metadata_elt(self):
        """Parse the file and locate METADATA = ..., if present.

        Returns:
            True if the metadata declaration was found, else False.
        """
        with open(self.path, encoding='utf-8') as f:
            self.contents = f.read()
        if not self.contents:
            return False

        parsed_file = ast.parse(self.contents)
        metadata_elt = None
        for elt in parsed_file.body:
            if (isinstance(elt, ast.Assign) and
                len(elt.targets) > 0 and
                isinstance(elt.targets[0], ast.Name)):
                first_target = ast.Name(elt.targets[0].id)
                if (first_target.id == 'METADATA' and
                    isinstance(elt.value, ast.Dict)):
                    metadata_elt = elt
                if (first_target.id == 'NAME' and
                    isinstance(elt.value, ast.Constant) and
                    isinstance(elt.value.value, str)):
                    self.name_value = elt.value.value

        if not metadata_elt:
            return False

        # Calculate file offsets for the METADATA declaration.
        # Note that ast only reports offsets into a specific line, while
        # we need the offset into the entire file.
        lines = self.contents.split("\n")
        file_offset = 0
        for i, _ in enumerate(lines):
            if i == metadata_elt.lineno - 1:
                self.metadata_start = file_offset + metadata_elt.col_offset
            if i == metadata_elt.end_lineno - 1:
                self.metadata_end = file_offset + metadata_elt.end_col_offset
                break
            file_offset += len(lines[i])+1

        self.metadata = ast.literal_eval(metadata_elt.value)
        return True

    def update_contents(self):
        """Modify self.contents using the modified values in self.metadata."""
        new_metadata = format_metadata(self.metadata)
        self.contents = (self.contents[:self.metadata_start] +
                         new_metadata +
                         self.contents[self.metadata_end:])
        self.metadata_end = self.metadata_start + len(new_metadata)
