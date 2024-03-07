#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright 2020 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import argparse
import logging as log
import os
import re
import shlex
import shutil
import subprocess
import multiprocessing
import sys
import time
import uuid
import json
import functools
import glob

from google.cloud import storage
from google.api_core import exceptions as cloud_exceptions
# pylint: disable=no-name-in-module, import-error

import common
from autotest_lib.client.common_lib import global_config
from autotest_lib.client.common_lib import mail, pidfile
from autotest_lib.tko.parse import parse_one, export_tko_job_to_file
from autotest_lib.tko.job_serializer import JobSerializer

import pubsub_client

STATUS_FILE = "status"
STATUS_LOG_FILE = "status.log"
KEYVAL_FILE = "keyval"
NEW_KEYVAL_FILE = "new_keyval"
UPLOADED_STATUS_FILE = ".uploader_status"
STATUS_GOOD = "PUBSUB_SENT"
FAKE_MOBLAB_ID_FILE = "fake_moblab_id_do_not_delete.txt"
GIT_HASH_FILE = "git_hash.txt"
GIT_COMMAND = ("git log --pretty=format:'%h -%d %s (%ci) <%an>'"
               " --abbrev-commit -20")
AUTOTEST_DIR = "/mnt/host/source/src/third_party/autotest/files/"
if "AUTOTEST_REPO_ROOT" in os.environ:
    AUTOTEST_DIR = os.environ["AUTOTEST_REPO_ROOT"]

DEFAULT_SUITE_NAME = "default_suite"
SUITE_NAME_REGEX = "Fetching suite for suite named (.+?)\.\.\."
DEBUG_FILE_PATH = "debug/test_that.DEBUG"

APPLICATION_DEFAULT_CREDENTIALS_PATH = os.path.join(os.environ["HOME"], ".config/gcloud", "application_default_credentials.json")
PUB_SUB_KEY_JSON_NAME = "pubsub-key-do-not-delete.json"
SERVICE_ACCOUNT_JSON_NAME = ".service_account.json"
POSSIBLE_SERVICE_ACCOUNT_NAMES = [".service_account.json", "pubsub-key-do-not-delete.json"]

CONFIG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config")
if "UPLOAD_CONFIG_DIR" in os.environ:
    CONFIG_DIR = os.environ["UPLOAD_CONFIG_DIR"]
PUB_SUB_KEY_JSON_PATH = os.path.join(CONFIG_DIR, PUB_SUB_KEY_JSON_NAME)
SERVICE_ACCOUNT_JSON_PATH = os.path.join(CONFIG_DIR, SERVICE_ACCOUNT_JSON_NAME)
UPLOAD_CONFIG_JSON_PATH = os.path.join(CONFIG_DIR, "upload_config.json")
LABEL_REGEX = r"(.*)results-\d*-(.*)"

logging = log.getLogger(__name__)


def parse_arguments(argv):
    """Creates the argument parser.

    Args:
        argv: A list of input arguments.

    Returns:
        A parser object for input arguments.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(
            help='select sub option for test result utility',
            dest='subcommand')
    subparsers.required = True
    parser.add_argument("-v",
                        "--verbose",
                        dest='verbose',
                        action='store_true',
                        help="Enable verbose (debug) logging.")
    parser.add_argument("-q",
                        "--quiet",
                        dest='quiet',
                        action='store_true',
                        help="Quiet mode for background call")
    def_logfile = "/tmp/" + os.path.basename(
            sys.argv[0].split(".")[0]) + ".log"
    parser.add_argument("-l",
                        "--logfile",
                        type=str,
                        required=False,
                        default=def_logfile,
                        help="Full path to logfile. Default: " + def_logfile)

    # configuration subcommand to create config file and populate environment
    config_parser = subparsers.add_parser(name="config",
                                          help='upload test results to CPCon')
    config_parser.add_argument(
            "-b",
            "--bucket",
            type=str,
            required=False,
            default="",
            help="The GCS bucket that test results are uploaded to, e.g."
            "'gs://xxxx'.")
    config_parser.add_argument("-f",
                               "--force",
                               dest='force',
                               action="store_true",
                               help="Force overwrite of previous config files")

    upload_parser = subparsers.add_parser(name="upload",
                                          help='upload test results to CPCon')
    upload_parser.add_argument(
            "--bug",
            type=_valid_bug_id,
            required=False,
            help=
            "Write bug id to the test results. Each test entry can only have "
            "at most 1 bug id. Optional.")
    upload_parser.add_argument(
            "-d",
            "--directory",
            type=str,
            required=True,
            help="The directory of non-Moblab test results.")
    upload_parser.add_argument(
            "--parse_only",
            action='store_true',
            help="Generate job.serialize locally but do not upload test "
            "directories and not send pubsub messages.")
    upload_parser.add_argument(
            "--upload_only",
            action='store_true',
            help="Leave existing protobuf files as-is, only upload "
            "directories and send pubsub messages.")
    upload_parser.add_argument(
            "-f",
            "--force",
            dest='force',
            action='store_true',
            help=
            "force re-upload of results even if results were already successfully uploaded."
    )
    upload_parser.add_argument(
            "-s",
            "--suite",
            type=str,
            default=None,
            help="The suite is used to identify the type of test results,"
            "e.g. 'power' for platform power team. If not specific, the "
            "default value is 'default_suite'.")
    upload_parser.add_argument(
            "--bucket",
            type=str,
            default=None,
            help="the bucket to upload the results to. If provided,"
            "this overrides the local config file")
    upload_parser.add_argument(
            "--sa_path",
            type=str,
            default=None,
            help="the sa path to use when uploading. If provided,"
            "this overrides the local config file")

    # checkacls subcommand to verify service account has proper acls to upload results to bucket
    subparsers.add_parser(name="checkacls", help='check ACLs of configured service account')
    return parser.parse_args(argv)


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


def _migrate_legacy_data_if_present():
    """
    In the old upload config workflow, the service account file could be named
    pubsub-key-do-not-delete.json instead of .service_account.json. If a
    pubsub-key-do-not-delete.json file is found in the configuration directory
    from the old flow, this function will rename it to .service_account.json
    """

    if os.path.exists(PUB_SUB_KEY_JSON_PATH):
        logging.info(
            f'found legacy {PUB_SUB_KEY_JSON_NAME} file; renaming it to {SERVICE_ACCOUNT_JSON_NAME}'
        )
        os.rename(PUB_SUB_KEY_JSON_PATH, SERVICE_ACCOUNT_JSON_PATH)
        with open(UPLOAD_CONFIG_JSON_PATH, "r") as cf:
            persistent_settings = json.load(cf)
        persistent_settings["service_account"] = SERVICE_ACCOUNT_JSON_PATH
        persistent_settings["boto_key"] = ""
        with open(UPLOAD_CONFIG_JSON_PATH, "w") as cf:
            json.dump(persistent_settings, cf)


def _environment_already_configured():
    """
    Returns True if environment has previously been configured, False otherwise
    """
    return os.path.exists(UPLOAD_CONFIG_JSON_PATH)


def _download_service_account(bucket, dest):
    """
    Downloads the service account json from the given bucket to the given path.
    Assumes user has already run:
    ```
    gcloud auth application-default login
    ```

    Args:
        bucket (str): The bucket from which to download the service account
        dest (str): Path to download the service account to

    Raises:
        Exception: If service account cannot be found in given bucket
    """

    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = APPLICATION_DEFAULT_CREDENTIALS_PATH
    gs_client_bucket = storage.Client(bucket).bucket(bucket)

    # search for the service account file in the bucket, download if found
    for service_account_name in POSSIBLE_SERVICE_ACCOUNT_NAMES:
        service_account = gs_client_bucket.blob(service_account_name)
        if service_account.exists():
            service_account.download_to_filename(dest)
            return

    raise ValueError("service account not found in bucket")


def _configure_environment(bucket, force):
    """
    Sets up the configuration directory (specified by the UPLOAD_CONFIG_JSON_PATH_DIR
    environment variable) with the service account credentials and the bucket
    information. If the directory has already been initialized, no configuration
    changes occur unless force is set to True

    Args:
        bucket (str): The bucket from which to download the service account needed
                      for results processing
        force (bool): If True, the configuration directory will be re-initialized
                      regardless if it has been already

    Raises:
        Exception: If service account cannot be found in given bucket
    """

    _migrate_legacy_data_if_present()

    if _environment_already_configured() and not force:
        logging.info("environment already configured, run with --force if you want to reconfigure")
    else:
        os.makedirs(CONFIG_DIR, exist_ok=True)

        if bucket == "":
            bucket = input("input gcs bucket: ")
        _download_service_account(bucket, SERVICE_ACCOUNT_JSON_PATH)

        upload_config_dict = {
            "bucket": bucket,
            # these keys are needed for backwards compatibility
            "service_account": SERVICE_ACCOUNT_JSON_PATH,
            "boto_key": ""
        }
        with open(UPLOAD_CONFIG_JSON_PATH, "w") as cf:
            cf.write(json.dumps(upload_config_dict))


def _assert_config_file_exists(file):
    """
    Raises exception if given config file does not have mandatory files
    """
    if not os.path.exists(file):
        raise Exception(f"missing {file} file, run config command")


def _load_config():
    """
    Initializes the GOOGLE_APPLICATION_CREDENTIALS with the configured service
    account and reads the persistent settings in the upload configuration json

    Args:
        bucket (str): The bucket from which to download the service account needed
                      for results processing
        force (bool): If True, the configuration directory will be re-initialized
                      regardless if it has been already

    Returns:
        A dictionary with all the settings in the upload configuration json

    Raises:
        Exception: If configuration directory does not have mandatory files
    """
    _migrate_legacy_data_if_present()

    _assert_config_file_exists(SERVICE_ACCOUNT_JSON_PATH)
    _assert_config_file_exists(UPLOAD_CONFIG_JSON_PATH)

    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = SERVICE_ACCOUNT_JSON_PATH

    with open(UPLOAD_CONFIG_JSON_PATH, "r") as cf:
        persistent_settings = json.load(cf)
    return persistent_settings


class ResultsManager:
    def __init__(self, results_parser, results_sender):
        self.parent_directory = ""
        self.result_directories = set()
        self.results = []
        self.results_parser = results_parser
        self.results_sender = results_sender
        self.bug_id = None
        self.suite_name = ""

        if "PUBLISH_HOSTNAME" in os.environ:
            self.moblab_id = os.environ["PUBLISH_HOSTNAME"]
        else:
            self.moblab_id = self.get_fake_moblab_id()

    def set_directory(self, parent_dir: str):
        self.parent_directory = parent_dir

    def enumerate_all_directories(self):
        self.result_directories = set()
        self.enumerate_result_directories(self.parent_directory)

    def enumerate_result_directories(self, parent_dir):
        """ Gets all test directories.

        Args:
        parent_dir: The parent directory of one or multiple test directories

        Creates a local_result for all directories with a status.log file
        and appends to local_results
        """
        if not os.path.exists(parent_dir) or not os.path.isdir(parent_dir):
            logging.warning('Test directory does not exist: %s' % parent_dir)
            return

        status_log_file = os.path.join(parent_dir, STATUS_LOG_FILE)
        job_serialize_file = os.path.join(parent_dir, "job.serialize")
        if os.path.exists(status_log_file) or \
                                            os.path.exists(job_serialize_file):
            self.result_directories.add(parent_dir)
            return

        for dir_name in os.listdir(parent_dir):
            subdir = os.path.join(parent_dir, dir_name)
            if os.path.isdir(subdir):
                self.enumerate_result_directories(subdir)

    def set_destination(self, destination):
        self.results_sender.set_destination(destination)

    def get_fake_moblab_id(self):
        """Get or generate a fake moblab id.

        Moblab id is the unique id to a moblab device. Since the upload script runs
        from the chroot instead of a moblab device, we need to generate a fake
        moblab id to comply with the CPCon backend. If there is a previously saved
        fake moblab id, read and use it. Otherwise, generate a uuid to fake a moblab
        device, and store it in the same directory as the upload script.

        Returns:
            A string representing a fake moblab id.
        """

        script_dir = os.path.dirname(__file__)
        fake_moblab_id_path = os.path.join(CONFIG_DIR, FAKE_MOBLAB_ID_FILE)

        # Migrate from prior moblab ID location into config directory if possible
        old_moblab_id_file = os.path.join(script_dir, FAKE_MOBLAB_ID_FILE)
        if os.path.exists(old_moblab_id_file):
            logging.info(
                    'Found an existing moblab ID outside config directory, migrating now'
            )
            os.rename(old_moblab_id_file, fake_moblab_id_path)
        try:
            with open(fake_moblab_id_path, "r") as fake_moblab_id_file:
                fake_moblab_id = str(fake_moblab_id_file.read())[0:32]
                if fake_moblab_id:
                    return fake_moblab_id
        except IOError as e:
            logging.info(
                    'Cannot find a fake moblab id at %s, creating a new one.',
                    fake_moblab_id_path)
        fake_moblab_id = uuid.uuid4().hex
        try:
            with open(fake_moblab_id_path, "w") as fake_moblab_id_file:
                fake_moblab_id_file.write(fake_moblab_id)
        except IOError as e:
            logging.warning('Unable to write the fake moblab id to %s: %s',
                            fake_moblab_id_path, e)
        return fake_moblab_id

    def overwrite_suite_name(self, suite_name):
        self.suite_name = suite_name

    def annotate_results_with_bugid(self, bug_id):
        self.bug_id = bug_id

    def parse_all_results(self, upload_only: bool = False):
        self.results = []
        self.enumerate_all_directories()

        for result_dir in self.result_directories:
            if self.bug_id is not None:
                self.results_parser.write_bug_id(result_dir, self.bug_id)
            self.results.append(
                    (result_dir,
                     self.results_parser.parse(result_dir,
                                               upload_only,
                                               suite_name=self.suite_name)))

    def upload_all_results(self, force):
        for result in self.results:
            self.results_sender.upload_result_and_notify(
                    result[0], self.moblab_id, result[1], force)


class FakeTkoDb:
    def find_job(self, tag):
        return None

    def run_with_retry(self, fn, *args):
        fn(*args)


class ResultsParserClass:
    def __init__(self):
        pass

    def job_tag(self, job_id, machine):
        return str(job_id) + "-moblab/" + str(machine)

    def parse(self, path, upload_only: bool, suite_name=""):
        job = None

        # fixes b/225403558 by tagging job_id with the current time
        job_id = int(time.time() * 1000)
        serialize_path = os.path.join(path, "job.serialize")
        if upload_only:
            js = JobSerializer()
            job = js.deserialize_from_binary(serialize_path)
        else:
            # this is needed to prevent errors on missing status.log
            status_log_file = os.path.join(path, STATUS_LOG_FILE)
            if not os.path.exists(status_log_file):
                logging.warning("no status.log file at %s", status_log_file)
                return

            #temporarily assign a fake job id until parsed
            fake_job_id = 1234
            fake_machine = "localhost"
            name = self.job_tag(fake_job_id, fake_machine)
            parse_options = argparse.Namespace(
                    **{
                            "suite_report": False,
                            "dry_run": True,
                            "reparse": False,
                            "mail_on_failure": False
                    })
            pid_file_manager = pidfile.PidFileManager("parser", path)
            self.print_autotest_git_history(path)
            job = parse_one(FakeTkoDb(), pid_file_manager, name, path,
                            parse_options)
            job.board = job.tests[0].attributes['host-board']
            if suite_name == "":
                logging.info("parsing suite name")
                job.suite = self.parse_suite_name(path)
            else:
                logging.info("overwrite with cmd line")
                job.suite = suite_name
            job.build_version = self.get_build_version(job.tests)

        if job.label is None:
            match = re.match(LABEL_REGEX, path)
            job.label = "cft/" + match.group(2)
        job.afe_job_id = str(job_id)
        if not job.afe_parent_job_id:
            job.afe_parent_job_id = str(job_id + 1)
            if "qual_run_id" in job.keyval_dict:
                logging.info("found qual_run_id in keyval dict")
                job.afe_parent_job_id = str(job.keyval_dict["qual_run_id"])
        name = self.job_tag(job_id, job.machine)
        export_tko_job_to_file(job, name, serialize_path)

        # autotest_lib appends additional global logger handlers
        # remove these handlers to avoid affecting logging for the google
        # storage library
        for handler in log.getLogger().handlers:
            log.getLogger().removeHandler(handler)
        return job

    def print_autotest_git_history(self, path):
        """
        Print the hash of the latest git commit of the autotest directory.

        Args:
            path: The test directory for non-moblab test results.
        """
        git_hash = ""
        try:
            git_hash = subprocess.check_output(shlex.split(GIT_COMMAND),
                                            cwd=AUTOTEST_DIR)
        except:
            git_hash = "CONTAINER_UPLOAD".encode("utf-8")
        git_hash_path = os.path.join(path, GIT_HASH_FILE)
        with open(git_hash_path, "w") as git_hash_file:
            git_hash_file.write(git_hash.decode("utf-8"))

    def parse_suite_name(self, path):
        """Get the suite name from a results directory.

        If we don't find the suite name in the first ten lines of test_that.DEBUG
        then return None.

        Args:
            path: The directory specified on the command line.
        """
        path = path.split('/')[:-1]
        path = '/'.join(path)

        debug_file = os.path.join(path, DEBUG_FILE_PATH)
        if not os.path.exists(debug_file) or not os.path.isfile(debug_file):
            return DEFAULT_SUITE_NAME
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
        return DEFAULT_SUITE_NAME

    def get_build_version(self, tests):
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

    def valid_bug_id(self, v):
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

    def write_bug_id(self, test_dir, bug_id):
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
                        old_bug_id = self.valid_bug_id(match.group(1))
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


ResultsParser = ResultsParserClass()
_valid_bug_id = functools.partial(ResultsParserClass.valid_bug_id,
                                  ResultsParser)


class ResultsSenderClass:
    def __init__(self):
        self.gcs_bucket = ""

    def set_destination(self, destination):
        self.gcs_bucket = destination

    def upload_result_and_notify(self, test_dir, moblab_id, job, force):
        job_id = job.afe_job_id
        if self.uploaded(test_dir) and not force:
            return
        self.upload_result(test_dir, moblab_id, job_id, job.machine)
        self.send_pubsub_message(test_dir, moblab_id, job_id)

    def upload_batch_files(self, gs_path, test_dir, files):
        for file in files:
            if not os.path.isfile(file):
                continue
            gs_client_bucket = storage.Client().bucket(self.gcs_bucket)
            # remove trailing slash to ensure dest_file path gets created properly
            test_dir = test_dir.rstrip('/')
            dest_file = gs_path + file.replace(test_dir, "", 1)
            logging.info("uploading file: %s", dest_file)
            blob = gs_client_bucket.blob(dest_file)
            blob.upload_from_filename(file, timeout=None)

    def upload_result(self, test_dir, moblab_id, job_id, hostname):
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

        gcs_bucket_path = os.path.join("results", fake_moblab_id,
                                       fake_moblab_install_id,
                                       "%s-moblab" % job_id, hostname)

        try:
            logging.info(
                    "Start to upload test directory: %s to GCS bucket path: %s",
                    test_dir, gcs_bucket_path)
            with open(upload_status_file, "w") as upload_status:
                upload_status.write("UPLOADED")

            files_to_upload = glob.glob(test_dir + "/**", recursive=True)
            batch_size = 8
            with multiprocessing.Pool(4) as p:
                files_to_upload_batch = [
                        files_to_upload[i:i + batch_size]
                        for i in range(0, len(files_to_upload), batch_size)
                ]
                p.map(
                        functools.partial(
                                ResultsSenderClass.upload_batch_files, self,
                                gcs_bucket_path, test_dir),
                        files_to_upload_batch)

            logging.info(
                    "Successfully uploaded test directory: %s to GCS bucket path: %s",
                    test_dir, gcs_bucket_path)
        except Exception as e:
            with open(upload_status_file, "w") as upload_status:
                upload_status.write("UPLOAD_FAILED")
            raise Exception(
                    "Failed to upload test directory: %s to GCS bucket "
                    "path: %s for the error: %s" %
                    (test_dir, gcs_bucket_path, e))

    def send_pubsub_message(self, test_dir, moblab_id, job_id):
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
        gsuri = "gs://%s/results/%s/%s/%s-moblab" % (
                self.gcs_bucket, moblab_id, moblab_install_id, job_id)

        try:
            logging.info("Start to send the pubsub message to GCS path: %s",
                         gsuri)
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
            raise Exception(
                    "Failed to send the pubsub message with moblab id: %s "
                    "and job id: %s to GCS path: %s for the error: %s" %
                    (moblab_id, job_id, gsuri, e))

    def uploaded(self, test_dir):
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


ResultsSender = ResultsSenderClass()


def main(args):
    parsed_args = parse_arguments(args)

    fmt = log.Formatter('%(asctime)s :: %(levelname)-8s :: %(message)s')
    logging.propagate = False

    log_level = log.INFO
    if parsed_args.verbose:
        log_level = log.DEBUG
    if not parsed_args.quiet:
        stream_handler = log.StreamHandler(sys.stdout)
        stream_handler.setFormatter(fmt)
        stream_handler.setLevel(log_level)
        logging.addHandler(stream_handler)

    logging.info("logging to %s", parsed_args.logfile)
    file_handler = log.FileHandler(parsed_args.logfile, mode='w')
    file_handler.setFormatter(fmt)
    file_handler.setLevel(log.DEBUG)
    logging.addHandler(file_handler)

    if parsed_args.subcommand == "config":
        _configure_environment(parsed_args.bucket, parsed_args.force)
        return

    persistent_settings = dict()
    if parsed_args.bucket != "" and parsed_args.sa_path != "":
        logging.info("setting bucket and sa_path from flags")
        persistent_settings["bucket"] = parsed_args.bucket
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = parsed_args.sa_path
    else:
        persistent_settings = _load_config()

    if parsed_args.subcommand == "checkacls":
        _check_acls(persistent_settings)
        return

    results_manager = ResultsManager(ResultsParser, ResultsSender)
    results_manager.set_destination(persistent_settings["bucket"])
    results_manager.set_directory(parsed_args.directory)

    if parsed_args.bug:
        results_manager.annotate_results_with_bugid(parsed_args.bug)
    if parsed_args.suite:
        results_manager.overwrite_suite_name(parsed_args.suite)
    if parsed_args.parse_only:
        results_manager.parse_all_results()
    elif parsed_args.upload_only:
        results_manager.parse_all_results(upload_only=True)
        results_manager.upload_all_results(force=parsed_args.force)
    else:
        results_manager.parse_all_results()
        results_manager.upload_all_results(force=parsed_args.force)


def _check_acls(settings):
    bucket_name = settings["bucket"]
    gs_client_bucket = storage.Client().bucket(bucket_name)

    # use https://cloud.google.com/storage/docs/access-control/iam-gsutil to get list of required permissions
    needed_perms = ["storage.objects.create", "storage.objects.delete", "storage.objects.list", "storage.objects.get"]
    perms = gs_client_bucket.test_iam_permissions(needed_perms)
    if len(perms) != len(needed_perms):
        logging.error("did not find neccesary ACLs for bucket: %s want permissions: %s, got permissions: %s", settings["bucket"], needed_perms, perms)
        sys.exit(1)
    else:
        logging.info("found valid ACLs for bucket: %s", bucket_name)

if __name__ == "__main__":
    try:
        main(sys.argv[1:])
    except KeyboardInterrupt:
        sys.exit(0)
    except Exception as err:
        logging.error(str(err))
        sys.exit(1)
