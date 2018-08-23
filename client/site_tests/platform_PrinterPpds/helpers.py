# Copyright 2018 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import gzip
import json
import md5
import os
import requests

# ==================== Documents digests

def calculate_digest(doc):
    """
    Calculates digests for given document.

    @param doc: document's content

    @returns calculated digests as a string of hexadecimals

    """
    # Split by newline character and filter out problematic lines
    lines = doc.split('\n')
    if lines[0].find(b'\x1B%-12345X@PJL') >= 0:
        for i, line in enumerate(lines):
            if ( line.startswith('@PJL SET ')
                    or line.startswith('@PJL COMMENT')
                    or line.startswith('@PJL JOB NAME')
                    or line.startswith('trailer << ') ):
                lines[i] = ''
    doc = '\n'.join(lines)
    # Calculates hash
    return md5.new(doc).hexdigest()


def parse_digests_file(path_digests):
    """
    Parses digests from file.

    @param path_digests: a path to a file with digests

    @returns a dictionary with digests indexed by ppd filenames or an empty
            dictionary if the given file does not exist

    """
    digests = dict()
    if os.path.isfile(path_digests):
        with open(path_digests, 'rb') as file_digests:
            lines = file_digests.read().splitlines()
            for line in lines:
                cols = line.split()
                if len(cols) >= 2:
                    digests[cols[0]] = cols[1]
    return digests


def calculate_list_of_digests(path_directory, blacklist):
    """
    Calculates list of digests for outputs from given directory.

    @param path_directory: path to directory with outputs
    @param blacklist: list of outputs to ignore

    @return a content of digests file for outputs from given directory

    """
    digests_content = ''
    filenames = list_entries_from_directory(
                        path=path_directory,
                        with_suffixes=('.out.gz'),
                        include_directories=False )
    filenames = list(set(filenames).difference(blacklist))
    filenames.sort()
    for filename in filenames:
        path_file = os.path.join(path_directory, filename)
        with gzip.open(path_file, 'rb') as file:
            file_content = file.read()
        digest = calculate_digest(file_content)
        digests_content += filename[:-7] + '\t' + digest + '\n'
    return digests_content


def load_blacklist():
    """
    Loads blacklist of outputs to omit.

    Raw outputs generated by some PPD files cannot be verified by digests,
    because they contain variables like date/time, job id or other non-static
    parameters. This routine returns list of blacklisted output files.

    @returns a list of output files to ignore during calculation of digests

    """
    path_current = os.path.dirname(os.path.realpath(__file__))
    path_blacklist = os.path.join(path_current, 'digests_blacklist.txt')
    with open(path_blacklist) as file_blacklist:
        blacklist = file_blacklist.readlines()

    # convert to output name
    for i, entry in enumerate(blacklist):
        entry = entry.strip()
        if entry != '':
            blacklist[i] = entry
            if not entry.endswith('.out.gz'):
                blacklist[i] += '.out.gz'

    return blacklist


# ===================== PPD files on the SCS server

def get_filenames_from_PPD_index(task_id):
    """
    It downloads an index file from the SCS server and extracts names
    of PPD files from it.

    @param task_id: an order number of an index file to process; this is
            an integer from the interval [0..20)

    @returns a list of PPD filenames (may contain duplicates)

    """
    # calculates a URL of the index file
    url_metadata = 'https://www.gstatic.com/chromeos_printing/metadata_v2/'
    url_ppd_index = url_metadata + ('index-%02d.json' % task_id)
    # donwloads and parses the index file
    request = requests.get(url_ppd_index)
    entries = json.loads(request.content)
    # extracts PPD filenames (the second element in each index entry)
    output = []
    for entry in entries:
        output.append(entry[1])
    # returns a list of extracted filenames
    return output


def download_PPD_file(ppd_file):
    """
    It downloads a PPD file from the SCS server.

    @param ppd_file: a filename of PPD file (neither path nor URL)

    @returns content of the PPD file
    """
    url_ppds = 'https://www.gstatic.com/chromeos_printing/ppds/'
    request = requests.get(url_ppds + ppd_file)
    return request.content


# ==================== Local filesystem

def list_entries_from_directory(
        path,
        with_suffixes=None, nonempty_results=False,
        include_files=True, include_directories=True ):
    """
    It returns all filenames from given directory. Results may be filtered
    by filenames suffixes or entries types.

    @param path: a path to directory to list files from
    @param with_suffixes: if set, only entries with given suffixes are
            returned; it must be a tuple
    @param nonempty_results: if True then Exception is raised if there is no
            results
    @param include_files: if False, then regular files and links are omitted
    @param include_directories: if False, directories are omitted

    @returns a nonempty list of entries meeting given criteria

    @raises Exception if no matching filenames were found and
            nonempty_results is set to True

    """
    # lists all files from the directory and filter them by given criteria
    list_of_files = []
    for filename in os.listdir(path):
        path_entry = os.path.join(path, filename)
        # check type
        if os.path.isfile(path_entry):
            if not include_files:
                continue
        elif os.path.isdir(path_entry):
            if not include_directories:
                continue
        else:
            continue
        # check suffix
        if with_suffixes is not None:
            if not filename.endswith(with_suffixes):
                continue
        list_of_files.append(filename)
    # throws exception if no files were found
    if nonempty_results and len(list_of_files) == 0:
        message = 'Directory %s does not contain any ' % path
        message += 'entries meeting the criteria'
        raise Exception(message)
    # returns a non-empty list
    return list_of_files

