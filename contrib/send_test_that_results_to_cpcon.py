#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright 2020 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import argparse
import logging
import os
import re
import shlex
import shutil
import subprocess
import sys
import time
import uuid

from google.cloud import storage

# Appends the third_party.autotest and src paths so that the script can import
# libraries under these paths.
sys.path.append('/mnt/host/source/src/platform/moblab/src')

# pylint: disable=no-name-in-module, import-error
import common
from tko import job_serializer, models, parser_lib
from moblab_common import pubsub_client

os.environ.setdefault("GOOGLE_APPLICATION_CREDENTIALS",
                      "%s/.service_account.json" % os.environ["HOME"])

CURRENT_TIMESTAMP = int(time.time())
FAKE_JOB_ID = CURRENT_TIMESTAMP
CONTROL_FILE = "control"
JOB_SERIALIZE_FILE = "job.serialize"
STATUS_FILE = "status"
KEYVAL_FILE = "keyval"
NEW_KEYVAL_FILE = "new_keyval"
UPLOADED_STATUS_FILE = ".uploader_status"
STATUS_GOOD = "PUBSUB_SENT"
FAKE_MOBLAB_ID_FILE = "fake_moblab_id_do_not_delete.txt"
GIT_HASH_FILE = "git_hash.txt"
GIT_COMMAND = ("git log --pretty=format:'%h -%d %s (%ci) <%an>'"
               " --abbrev-commit -20")
AUTOTEST_DIR = "/mnt/host/source/src/third_party/autotest/files/"
DEFAULT_SUITE_NAME = "default_suite"
SUITE_NAME_REGEX = "Fetching suite for suite named (.+?)\.\.\."
DEBUG_FILE_PATH = "debug/test_that.DEBUG"


def parse_arguments(argv):
    """Creates the argument parser.

    Args:
        argv: A list of input arguments.

    Returns:
        A parser object for input arguments.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
            "-b",
            "--bucket",
            type=str,
            required=True,
            help="The GCS bucket that test results are uploaded to, e.g."
            "'gs://xxxx'.")
    parser.add_argument(
            "--bug",
            type=_valid_bug_id,
            required=False,
            help=
            "Write bug id to the test results. Each test entry can only have "
            "at most 1 bug id. Optional.")
    parser.add_argument("-d",
                        "--directory",
                        type=str,
                        required=True,
                        nargs='+',
                        help="The directory of non-Moblab test results.")
    parser.add_argument(
            "--dry_run",
            action='store_true',
            help="Generate job.serialize locally but do not upload test "
            "directories and not send pubsub messages.")
    def_logfile = "/tmp/" + os.path.basename(
            sys.argv[0].split(".")[0]) + ".log"
    parser.add_argument("-l",
                        "--logfile",
                        type=str,
                        required=False,
                        default=def_logfile,
                        help="Full path to logfile. Default: " + def_logfile)
    parser.add_argument(
            "-s",
            "--suite",
            type=str,
            default=None,
            help="The suite is used to identify the type of test results,"
            "e.g. 'power' for platform power team. If not specific, the "
            "default value is 'default_suite'.")
    parser.add_argument("-v",
                        "--verbose",
                        action='store_true',
                        help="Enable verbose (debug) logging.")
    return parser.parse_args(argv)


def fetch_test_dirs(parent_dir, test_dirs):
    """ Gets all test directories.

    Args:
        parent_dir: The parent directory of one or multiple test directories
        test_dirs: The output set of test directories.
    """
    if not os.path.exists(parent_dir) or not os.path.isdir(parent_dir):
        logging.warning('Test directory does not exist: %s' % parent_dir)
        return

    control_file = os.path.join(parent_dir, CONTROL_FILE)
    status_file = os.path.join(parent_dir, STATUS_FILE)
    if os.path.exists(control_file) and os.path.exists(status_file):
        test_dirs.add(parent_dir)
        return

    for dir_name in os.listdir(parent_dir):
        subdir = os.path.join(parent_dir, dir_name)
        if os.path.isdir(subdir):
            fetch_test_dirs(subdir, test_dirs)


def parse_test_job(test_dir, job_keyval, job_id, suite):
    """
        Parses test results and get the job object for the given test directory.
        The job object will be used to generate job.serialize file.

    Args:
        test_dir: The test directory for non-moblab test results.
        job_keyval: The key-value object of the job.
        job_id: A job_id.
        suite: A suite name.

    Returns:
        The job object or None if build version not found.
    """
    logging.info("Start to parse the test job for: %s", test_dir)

    # Looks up the status version and hostname
    status_version = job_keyval.get("status_version", 0)
    parser = parser_lib.parser(status_version)

    status_log_path = _find_status_log_path(test_dir)
    if not status_log_path:
        logging.warning('No status log file exists in: %s', test_dir)
        return None

    job = parser.make_job(test_dir)
    # workaround for CPCon pipeline, "board" is mandatory
    job.board = job.machine_group

    job.tests = _get_job_tests(parser, job, status_log_path)

    # The job id and suite name are necessary for CPCon pipeline. Since
    # non-moblab test results don't have these fields, the values here are fake.
    # Set a different afe_paren_job_id so that the test won't be regarded as a
    # suite test.
    job.afe_job_id = job_id
    job.afe_parent_job_id = job_id + "1"
    job.suite = suite

    job.build_version = _get_build_version(job.tests)
    job.build = job.build_version
    if not job.build_version:
        logging.warning('Failed to get build version in: %s', test_dir)
        return None

    logging.info("Successfully parsed the job.serialize for: %s", test_dir)
    return job


def generate_job_serialize(test_dir, job, job_keyval):
    """
        Generate the job.serialize for the given test directory, job object and
        job key-value object.

    Args:
        test_dir: The test directory for non-moblab test results.
        job: A job object.
        job_keyval: The key-value object of the job.
    """
    job_serialize_file = os.path.join(test_dir, JOB_SERIALIZE_FILE)
    logging.info("Start to generate the job.serialize for: %s",
                 job_serialize_file)

    hostname = job_keyval.get('hostname', '0.0.0.0')  # ip address
    job_name = "%s-moblab/%s" % (job.afe_job_id, hostname)

    serializer = job_serializer.JobSerializer()
    serializer.serialize_to_binary(job, job_name, job_serialize_file)
    logging.info("Successfully generated the job.serialize for: %s",
                 job_serialize_file)


def is_pubsub_sent(test_dir):
    """
       Checks if the message for the uploaded bucket has been sent.

    Args:
        test_dir: The test directory for non-moblab test results.
    """
    upload_status_file = os.path.join(test_dir, UPLOADED_STATUS_FILE)
    if not os.path.exists(upload_status_file):
        logging.debug("The upload status file %s does not exist.",
                      upload_status_file)
        return False

    with open(upload_status_file, "r") as upload_status:
        if upload_status.read() == STATUS_GOOD:
            logging.warn(
                    "The test directory: %s status has already been "
                    "sent to CPCon and the .upload_status file has "
                    "been set to PUBSUB_SENT.", test_dir)
            return True
        else:
            logging.debug("The pubsub message was not successful")
    return False


def upload_test_results(args, test_dir, job_keyval, moblab_id, job_id):
    """
        Upload the test directory with job.serialize to GCS bucket.

    Args:
        args: A list of input arguments.
        test_dir: The test directory for non-moblab test results.
        job_keyval: The key-value object of the job.
        moblab_id: A string that represents the unique id of a moblab device.
        job_id: A job id.
    """
    upload_status_file = os.path.join(test_dir, UPLOADED_STATUS_FILE)
    with open(upload_status_file, "w") as upload_status:
        upload_status.write("UPLOADING")

    fake_moblab_id = moblab_id
    fake_moblab_install_id = moblab_id
    hostname = job_keyval.get('hostname', '0.0.0.0')  # ip address

    bucket = args.bucket
    gcs_bucket_path = os.path.join("gs://%s" % bucket, "results",
                                   fake_moblab_id, fake_moblab_install_id,
                                   "%s-moblab" % job_id, hostname)

    try:
        logging.info(
                "Start to upload test directory: %s to GCS bucket path: %s",
                test_dir, gcs_bucket_path)
        with open(upload_status_file, "w") as upload_status:
            upload_status.write("UPLOADED")

        cmd = "gsutil -m cp -r %s %s" % (test_dir, gcs_bucket_path)
        subprocess.check_output(shlex.split(cmd))

        logging.info(
                "Successfully uploaded test directory: %s to GCS bucket path: %s",
                test_dir, gcs_bucket_path)
    except Exception as e:
        with open(upload_status_file, "w") as upload_status:
            upload_status.write("UPLOAD_FAILED")
        raise Exception("Failed to upload test directory: %s to GCS bucket "
                        "path: %s for the error: %s" %
                        (test_dir, gcs_bucket_path, e))


def send_pubsub_message(test_dir, bucket, moblab_id, job_id):
    """
        Send pubsub messages to trigger CPCon pipeline to process non-moblab
        test results in the specific GCS bucket path.

    Args:
        bucket: The GCS bucket.
        moblab_id: A moblab id.
        job_id: A job id.
    """
    moblab_install_id = moblab_id
    console_client = pubsub_client.PubSubBasedClient()
    gsuri = "gs://%s/results/%s/%s/%s-moblab" % (bucket, moblab_id,
                                                 moblab_install_id, job_id)

    try:
        logging.info("Start to send the pubsub message to GCS path: %s", gsuri)
        message_id = \
            console_client.send_test_job_offloaded_message(gsuri,
                                                           moblab_id,
                                                           moblab_install_id)
        upload_status_file = os.path.join(test_dir, UPLOADED_STATUS_FILE)
        with open(upload_status_file, "w") as upload_status:
            upload_status.write(STATUS_GOOD)

        logging.info(
                "Successfully sent the pubsub message with message id: %s to GCS "
                "path: %s", message_id[0], gsuri)
    except Exception as e:
        raise Exception("Failed to send the pubsub message with moblab id: %s "
                        "and job id: %s to GCS path: %s for the error: %s" %
                        (moblab_id, job_id, gsuri, e))


def _find_status_log_path(test_dir):
    log_path = os.path.join(test_dir, "status.log")
    if os.path.exists(log_path):
        return log_path

    log_path = os.path.join(test_dir, "status")
    if os.path.exists(log_path):
        return log_path
    return ""


def _get_job_tests(parser, job, status_log_path):
    status_lines = open(status_log_path).readlines()
    parser.start(job)
    tests = parser.end(status_lines)

    # The parser.end can return the same object multiple times, so filter out
    # dups.
    return list(set([test for test in tests]))


def _get_build_version(tests):
    release_version_label = "CHROMEOS_RELEASE_VERSION"
    milestone_label = "CHROMEOS_RELEASE_CHROME_MILESTONE"
    for test in tests:
        if not test.subdir:
            continue

        release = None
        milestone = None
        if release_version_label in test.attributes:
            release = test.attributes[release_version_label]
        if milestone_label in test.attributes:
            milestone = test.attributes[milestone_label]
        if release and milestone:
            return "R%s-%s" % (milestone, release)

    return ""


def _get_partial_object_path(bucket, moblab_id):
    storage_client = storage.Client()
    blob_itr = storage_client.bucket(bucket).list_blobs(prefix=moblab_id)

    for blob in blob_itr:
        if ("job.serialize" in blob.name and "moblab" in blob.name):
            yield blob.name


def _confirm_option(question):
    """
        Get a yes/no answer from the user via command line.

    Args:
        question: string, question to ask the user.

    Returns:
        A boolean. True if yes; False if no.
    """
    expected_answers = ['y', 'yes', 'n', 'no']
    answer = ''
    while answer not in expected_answers:
        answer = input(question + "(y/n): ").lower().strip()
    return answer[0] == "y"


def _write_bug_id(test_dir, bug_id):
    """
        Write the bug id to the test results.

    Args:
        test_dir: The test directory for non-moblab test results.
        bug_id: The bug id to write to the test results.
    Returns:
        A boolean. True if the bug id is written successfully or is the same as
        the old bug id already in test results; False if failed to write the
        bug id, or if the user decides not to overwrite the old bug id already
        in test results.
    """
    old_bug_id = None
    new_keyval = list()

    keyval_file = os.path.join(test_dir, KEYVAL_FILE)
    try:
        with open(keyval_file, 'r') as keyval_raw:
            for line in keyval_raw.readlines():
                match = re.match(r'bug_id=(\d+)', line)
                if match:
                    old_bug_id = _valid_bug_id(match.group(1))
                else:
                    new_keyval.append(line)
    except IOError as e:
        logging.error(
                'Cannot read keyval file from %s, skip writing the bug '
                'id %s: %s', test_dir, bug_id, e)
        return False

    if old_bug_id:
        if old_bug_id == bug_id:
            return True
        overwrite_bug_id = _confirm_option(
                'Would you like to overwrite bug id '
                '%s with new bug id %s?' % (old_bug_id, bug_id))
        if not overwrite_bug_id:
            return False

    new_keyval.append('bug_id=%s' % bug_id)
    new_keyval_file = os.path.join(test_dir, NEW_KEYVAL_FILE)
    try:
        with open(new_keyval_file, 'w') as new_keyval_raw:
            for line in new_keyval:
                new_keyval_raw.write(line)
            new_keyval_raw.write('\n')
        shutil.move(new_keyval_file, keyval_file)
        return True
    except Exception as e:
        logging.error(
                'Cannot write bug id to keyval file in %s, skip writing '
                'the bug id %s: %s', test_dir, bug_id, e)
        return False


def _valid_bug_id(v):
    """Check if user input bug id is in valid format.

    Args:
        v: User input bug id in string.
    Returns:
        An int representing the bug id.
    Raises:
        argparse.ArgumentTypeError: if user input bug id has wrong format.
    """
    try:
        bug_id = int(v)
    except ValueError as e:
        raise argparse.ArgumentTypeError(
                "Bug id %s is not a positive integer: "
                "%s" % (v, e))
    if bug_id <= 0:
        raise argparse.ArgumentTypeError(
                "Bug id %s is not a positive integer" % v)
    return bug_id


def _get_fake_moblab_id():
    """Get or generate a fake moblab id.

    Moblab id is the unique id to a moblab device. Since the upload script runs
    from the chroot instead of a moblab device, we need to generate a fake
    moblab id to comply with the CPCon backend. If there is a previously saved
    fake moblab id, read and use it. Otherwise, generate a uuid to fake a moblab
    device, and store it in the same directory as the upload script.

    Returns:
        A string representing a fake moblab id.
    """
    script_dir = os.path.realpath(
            os.path.join(os.getcwd(), os.path.dirname(__file__)))
    fake_moblab_id_path = os.path.join(script_dir, FAKE_MOBLAB_ID_FILE)
    try:
        with open(fake_moblab_id_path, "r") as fake_moblab_id_file:
            fake_moblab_id = str(fake_moblab_id_file.read())[0:32]
            if fake_moblab_id:
                return fake_moblab_id
    except IOError as e:
        logging.info('Cannot find a fake moblab id at %s, creating a new one.',
                     fake_moblab_id_path)
    fake_moblab_id = uuid.uuid4().hex
    try:
        with open(fake_moblab_id_path, "w") as fake_moblab_id_file:
            fake_moblab_id_file.write(fake_moblab_id)
    except IOError as e:
        logging.warning('Unable to write the fake moblab id to %s: %s',
                        fake_moblab_id_path, e)
    return fake_moblab_id


def print_autotest_git_history(test_dir):
    """
       Print the hash of the latest git commit of the autotest directory.

    Args:
        test_dir: The test directory for non-moblab test results.
    """
    git_hash = subprocess.check_output(shlex.split(GIT_COMMAND),
                                       cwd=AUTOTEST_DIR)
    git_hash_path = os.path.join(test_dir, GIT_HASH_FILE)
    with open(git_hash_path, "w") as git_hash_file:
        git_hash_file.write(git_hash.decode("utf-8"))


def get_suite_name(results_dir):
    """Get the suite name from a results directory.

    If we don't find the suite name in the first ten lines of test_that.DEBUG
    then return None.

    Args:
        results_dir: The directory specified on the command line.
    """
    debug_file = os.path.join(results_dir, DEBUG_FILE_PATH)
    if not os.path.exists(debug_file) or not os.path.isfile(debug_file):
        return None
    exp = re.compile(SUITE_NAME_REGEX)
    try:
        with open(debug_file) as f:
            line_count = 0
            for line in f:
                line_count += 1
                if line_count > 10:
                    break
                result = exp.search(line)
                if not result:
                    continue
                else:
                    return result.group(1)
    except IOError as e:
        logging.warning('Error trying to read test_that.DEBUG: %s', e)
    return None


def main(args):
    parsed_args = parse_arguments(args)
    bucket = parsed_args.bucket

    logger = logging.getLogger()
    fmt = logging.Formatter('%(asctime)s :: %(levelname)-8s :: %(message)s')

    log_level = logging.INFO
    if parsed_args.verbose:
        log_level = logging.DEBUG

    # modify existing handlers
    for handler in logger.handlers:
        handler.setFormatter(fmt)
        handler.setLevel(log_level)

    logging.info("logging to %s", parsed_args.logfile)

    hfile = logging.FileHandler(parsed_args.logfile, mode='w')
    hfile.setFormatter(fmt)
    hfile.setLevel(log_level)
    logger.addHandler(hfile)

    # The non-moblab test results generated by test_that CLI don't have moblab
    # id, moblab install id, suite name and job id. Thus, we need to fake these
    # fields with valid values.
    fake_moblab_id = _get_fake_moblab_id()

    result_dirs = map(os.path.normpath, parsed_args.directory)
    for directory in set(result_dirs):
        # If suite name is specified on command line, use it.
        # Otherwise try to get name from result_dir (-d on command line).
        # Otherwise use the default suite name.
        if parsed_args.suite:
            fake_suite = parsed_args.suite
        else:
            result_dir_suite_name = get_suite_name(directory)
            fake_suite = result_dir_suite_name or DEFAULT_SUITE_NAME
        logging.info("suite name: %s", fake_suite)

        test_dirs = set()
        fetch_test_dirs(directory, test_dirs)
        for test_dir in test_dirs:
            # Uses a unique timestamp in milliseconds to fake the afe job id and
            # skylab job id.
            if parsed_args.bug:
                _write_bug_id(test_dir, parsed_args.bug)
            fake_job_id = str(int(time.time() * 1000))
            job_keyval = models.job.read_keyval(test_dir)
            job = parse_test_job(test_dir, job_keyval, fake_job_id, fake_suite)

            if not job:
                logging.warning(
                        "Failed to generate job.serialize file and "
                        "skipped the test directory: %s", test_dir)
                continue

            generate_job_serialize(test_dir, job, job_keyval)

            print_autotest_git_history(test_dir)

            if parsed_args.dry_run:
                continue

            # This process run is not a dry run
            if not is_pubsub_sent(test_dir):
                try:
                    upload_test_results(parsed_args, test_dir, job_keyval,
                                        fake_moblab_id, fake_job_id)
                    send_pubsub_message(test_dir, bucket, fake_moblab_id,
                                        fake_job_id)
                except Exception as e:
                    logging.warning(e)
                    continue


if __name__ == "__main__":
    try:
        main(sys.argv[1:])
    except KeyboardInterrupt:
        sys.exit(0)
