# Lint as: python2, python3
# Copyright 2016 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# repohooks/pre-upload.py currently does not run pylint. But for developers who
# want to check their code manually we disable several harmless pylint warnings
# which just distract from more serious remaining issues.
#
# The instance variables _host and _install_paths are not defined in __init__().
# pylint: disable=attribute-defined-outside-init
#
# Many short variable names don't follow the naming convention.
# pylint: disable=invalid-name
#
# _parse_result() and _dir_size() don't access self and could be functions.
# pylint: disable=no-self-use

from collections import namedtuple
import errno
import glob
import hashlib
import logging
import os
import pipes
import pwd
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import time
import six.moves.urllib_parse as urlparse

from autotest_lib.client.bin import utils as client_utils
from autotest_lib.client.common_lib import error
from autotest_lib.server import test
from autotest_lib.server import utils
from autotest_lib.server.cros.tradefed import adb as adb_utils
from autotest_lib.server.cros.tradefed import bundle_utils
from autotest_lib.server.cros.tradefed import cts_expected_failure_parser
from autotest_lib.server.cros.tradefed import tradefed_chromelogin as login
from autotest_lib.server.cros.tradefed import tradefed_constants as constants
from autotest_lib.server.cros.tradefed import tradefed_utils
from autotest_lib.server.cros.tradefed import tradefed_prerequisite
from autotest_lib.server.autotest import OFFLOAD_ENVVAR

# TODO(kinaba): Move to tradefed_utils together with the setup/cleanup methods.
MediaAsset = namedtuple('MediaAssetInfo', ['uri', 'localpath'])

_GCS_WAIVERS_PATH = 'gs://chromeos-arc-images/waivers/'


class UnsupportedSuiteVersion(Exception):
    """Custom exception for unsupported suite version."""


class BundleSpecification:
    """Class containing xTS bundle information."""

    def __init__(self, uri, password, suite_name):
        """Construct BundleSpecification

        Args:
            uri is the uri of the bundle.
            password is the password for extracting the bundle. Empty string means
                no password.
            suite_name is the suite name (CTS/GTS/STS).
        """
        self.uri = uri
        self.password = password
        self.suite_name = suite_name


class ETagNotFoundException(Exception):
    """Raised when it fails to find the ETag."""
    pass

def _GetETagFromGsUri(gs_uri):
    """Parses the output of gsutil ls -L and returns the ETag.

    The output format of gsutil ls -L should be like

    gs://bucket-name/path/fo/file:
        ...
        ETag:                   COOOrtv1r/gCEAE=
        ...

    This function finds the line and hex-encodes the ETag because it might
    contain characters that some file-systems cannot handle, such as '/' in the
    above.

    Args:
        gs_uri is a Google Storage URI to a file.

    Returns:
        Hex encoded ETag of the input file.

    Raises:
        ETagNotFoundException if an ETag is not found.
    """
    ls_result = utils.run('gsutil', args=('ls', '-L', gs_uri), verbose=True)
    output_text = ls_result.stdout
    for line in output_text.splitlines():
        if 'ETag:' not in line:
            continue
        parsed_text = line.split(':')[1].strip()
        return parsed_text.encode('utf-8').hex()

    raise ETagNotFoundException(
            'Failed to find ETag in command {}. Output: {}'.format(
                ls_result.command, output_text))


class TradefedTest(test.test):
    """Base class to prepare DUT to run tests via tradefed."""
    version = 1

    # Default and upperbounds of max_retry, based on board and revision
    # after branching (that is, 'y' of R74-12345.y.z).
    #
    # By default, 0<=y<1 does 5 retries and 1<=y does 10. The |max_retry|
    # parameter in control files can override the count, within the
    # _BRANCH_MAX_RETRY limit below.
    _BRANCH_DEFAULT_RETRY = [(0, 5), (1, 10)]  # dev=5, beta=stable=10
    _BRANCH_MAX_RETRY = [(0, 12), (1, 30),      # dev=12, beta=30, stable=99
        (constants.APPROXIMATE_STABLE_BRANCH_NUMBER, 99)]
    # TODO(kinaba): betty-arcnext
    _BOARD_MAX_RETRY = {'betty': 0}

    _SHARD_CMD = None
    _board_arch = None
    _board_name = None
    _model_name = None
    _release_branch_number = None  # The 'y' of OS version Rxx-xxxxx.y.z
    _android_version = None
    _first_api_level = None
    _bundle_uri = None
    _bundle_abi = None
    _bundle_spec = None
    _retry_manual_tests = False
    _num_media_bundles = 0
    _abilist = []
    _feature_list = []

    # A job will be aborted after 16h. Subtract 30m for setup/teardown.
    _MAX_LAB_JOB_LENGTH_IN_SEC = 16 * 60 * 60 - 30 * 60
    _job_deadline = None

    # Map only the versions that ARC releases care.
    _SDK_VER_MAP = {28: 'P', 30: 'R', 33: 'T'}

    # Currently this is only used for dependency injection for testing.
    def __init__(self, *args, **kwargs):
        super().__init__(*args)
        self._adb = kwargs.get('adb', adb_utils.Adb())

    def _log_java_version(self):
        """Log java version to debug failures due to version mismatch."""
        utils.run(
            'java',
            args=('-version',),
            ignore_status=False,
            verbose=True,
            stdout_tee=utils.TEE_TO_LOGS,
            stderr_tee=utils.TEE_TO_LOGS)

    def initialize(self,
                   bundle=None,
                   uri=None,
                   host=None,
                   hosts=None,
                   max_retry=None,
                   retry_manual_tests=False,
                   warn_on_test_retry=True,
                   hard_reboot_on_failure=False):
        """Sets up the tools and binary bundles for the test."""
        if utils.is_in_container() and not client_utils.is_moblab():
            self._job_deadline = time.time() + self._MAX_LAB_JOB_LENGTH_IN_SEC

        self._bundle_uri = uri
        self._bundle_abi = bundle
        self._retry_manual_tests = retry_manual_tests
        self._install_paths = []
        # TODO(pwang): Remove host if we enable multiple hosts everywhere.
        self._hosts = [host] if host else hosts
        for host in self._hosts:
            logging.info('Hostname: %s', host.host_port)
        self._verify_hosts()

        self._max_retry = self._get_max_retry(max_retry)
        self._warn_on_test_retry = warn_on_test_retry

        # Sets self._tradefed_cache_* properties.
        self._configure_tradefed_cache()

        # The content of the install location does not survive across jobs and
        # is isolated (by using a unique path)_against other autotest instances.
        # This is not needed for the lab, but if somebody wants to run multiple
        # TradedefTest instance.
        self._tradefed_install = tempfile.mkdtemp(
            prefix=constants.TRADEFED_PREFIX)
        # Under lxc the cache is shared between multiple autotest/tradefed
        # instances. We need to synchronize access to it. All binaries are
        # installed through the (shared) cache into the local (unshared)
        # lxc/autotest instance storage.
        # If clearing the cache it must happen before all downloads.
        self._clean_download_cache_if_needed()
        # Set permissions (rwxr-xr-x) to the executable binaries.
        permission = (
            stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH
            | stat.S_IXOTH)

        self._install_files(constants.ADB_DIR, constants.ADB_FILES, permission)
        self._install_files(constants.AAPT_DIR, constants.AAPT_FILES,
                            permission)
        self._install_files(constants.SDK_TOOLS_DIR,
                            constants.SDK_TOOLS_FILES, permission)

        # Always use JDK9 in the skylab SSP runs. CFT run will use container
        # provided JDK.
        if utils.is_in_container(
        ) and not client_utils.is_moblab() and os.getuid() == 0:
            logging.info('Lab: switching to JDK9')
            try:
                os.environ['JAVA_HOME'] = '/usr/lib/jvm/jdk-9.0.4'
                os.environ['PATH'] = os.environ['JAVA_HOME']\
                                  + '/bin:' + os.environ['PATH']
                logging.info(
                        subprocess.check_output(['java', '-version'],
                                                stderr=subprocess.STDOUT))
            except OSError:
                logging.error('Can\'t change current PATH directory')
        else:
            logging.info('Non-lab environment: should be using JDK9+')

        # On go/cloudbots DUTs are not reachable via network directly. We need
        # to tunnal ADB connections via SSH.
        if self._is_cloudbot():
            self._adb.set_tunnel(adb_utils.SshAdbTunnel(hosts))

        # TODO(kinaba): Remove the hack and fully enable the feature.
        # For release branches (Rx-yyyyy.3.0 or above), always use the
        # official build instead of the release build. See b/210369548
        if uri == 'DEV' and self._get_release_branch_number() >= 3:
            uri = 'LATEST'
        # Install the tradefed bundle.
        self._bundle_spec = self._get_bundle_specification(uri, bundle)
        bundle_install_path = self._install_bundle(self._bundle_spec.uri,
                                                   self._bundle_spec.password)
        self._repository = os.path.join(bundle_install_path,
                                        self._get_tradefed_base_dir())

        # Newer version os xTS bundles JDK. Points to the path as the default choice.
        os.environ['PATH'] = '%s:%s' % (os.path.join(self._repository, 'jdk', 'bin'),
            os.environ['PATH'])

        self._waivers = None

        self._hard_reboot_on_failure = hard_reboot_on_failure

    def _is_cloudbot(self):
        """Returns True if the test job is running on cloudbot."""
        return os.environ.get('SWARMING_BOT_ID', '').startswith('cloudbots-')

    def _load_local_waivers(self, directory, is_dev=False):
        return self._get_expected_failures(os.path.join(self.bindir, directory), is_dev)

    def _load_waivers(self, official_suite_version):
        """Load expected test failures to exclude them from re-runs."""
        self._waivers = set()
        self._notest_modules = set()

        is_dev = self._bundle_uri and self._bundle_uri.startswith('DEV')
        is_public = not self._bundle_uri
        self._waivers.update(
                self._load_local_waivers('expectations', is_dev))

        if self._should_load_gcs_waivers(is_public):
            self._waivers.update(
                    self._load_gcs_waivers(official_suite_version, is_dev))

        if not self._retry_manual_tests:
            self._waivers.update(
                    self._load_local_waivers('manual_tests'))

        # Load modules with no tests.
        self._notest_modules.update(
                self._load_local_waivers('notest_modules'))

    def _output_perf(self):
        """Output performance values."""
        base = self._default_tradefed_base_dir()
        path = tradefed_utils.get_test_result_xml_path(base)
        if path:
            for metric in tradefed_utils.get_perf_metrics_from_test_result_xml(
                path, self.resultsdir):
                self.output_perf_value(**metric)

    def _prepare_synchronous_offloads(self):
        """
        Copy files needed for APFE to synchronous offload dir,  with some
        structure to make the post-job postprocessing simpler.
        """
        testname = os.path.basename(self.outputdir)
        # This is yyyy.mm.dd_hh.mm.ss  (start time)
        timestamp_pattern = ("[0-9][0-9][0-9][0-9].[0-9][0-9].[0-9][0-9]" +
                             "_[0-9][0-9].[0-9][0-9].[0-9][0-9]")
        time_glob = os.path.join(
            self._default_tradefed_base_dir(), timestamp_pattern
        )
        for dirpath in glob.glob(time_glob):
            timestamp = os.path.basename(dirpath)
            locs = [os.path.join(dirpath, f) for f in ["test_result.xml",
                                                       "testResult.xml"]]
            for f in locs:
                if os.path.exists(f):
                    subdirs = self._subdirs(f, testname, timestamp)
                    self._copy_to_offload_dir(f, subdirs)
        for z in glob.glob(time_glob+".zip"):
            self._copy_to_offload_dir(z, self._subdirs(z, testname))

    def _copy_to_offload_dir(self, src_path, subdirs, recursive=True):
        target = os.path.join(os.getenv(OFFLOAD_ENVVAR), *subdirs)
        self._safe_makedirs(target)
        if not recursive or os.path.isfile(src_path):
            return shutil.copy2(src_path, str(target))
        return shutil.copytree(src_path, str(target))

    def _subdirs(self, path, testname, timestamp=""):
        # CTS results from bvt-arc suites need to be sent to the
        # specially-designated bucket for early EDI entries in APFE,
        # but only there.
        dest = "BVT" if 'bvt-arc' in path else "CTS"
        return ["APFE", dest, testname, timestamp]

    def cleanup(self):
        """Cleans up any dirtied state."""

        # We also run a postprocess result and performance data
        # offloading here so that WARN and FAIL runs also run the
        # steps. postprocess() method only runs for PASSing jobs.
        self._prepare_synchronous_offloads()
        self._output_perf()

        try:
            # Clean up test data that may not be deletable on previous
            # ChromeOS versions. See b/170276268.
            self._run_commands([
                    'cryptohome --action=remove --force --user=test@test.test'
            ],
                               ignore_status=True)
        except:
            logging.error('Failed to clean up the test account.')

        self._kill_adb_server()

        if hasattr(self, '_tradefed_install'):
            logging.info('Cleaning up %s.', self._tradefed_install)
            try:
                shutil.rmtree(self._tradefed_install)
            except IOError:
                pass

    def _kill_adb_server(self):
        # Kill any lingering adb servers.
        try:
            self._adb.run(None,
                          verbose=True,
                          args=('kill-server', ),
                          timeout=constants.
                          ADB_SERVER_COMMAND_TIMEOUT_SECONDS)
        except error.CmdTimeoutError as e:
            logging.warn(e)
            # `adb kill-server` sometimes hangs up. Kill it more brutally.
            try:
                client_utils.system(
                        'killall adb',
                        ignore_status=True,
                        timeout=constants.ADB_SERVER_COMMAND_TIMEOUT_SECONDS)
            except error.CmdTimeoutError as e:
                # The timeout is ignored, since the only known failure pattern
                # b/142828365 is due to a zombie process that does not prevent
                # starting a new server with a new adb key.
                logging.warn(e)
        except (error.CmdError, AttributeError):
            pass

    def _verify_hosts(self):
        """Verify all hosts' ChromeOS consistency."""
        # Check release builder path. E.g. cave-release/R66-10435.0.0
        release_builder_path = set(host.get_release_builder_path()
                                   for host in self._hosts)
        if len(release_builder_path) > 1:
            raise error.TestFail('Hosts\' CHROMEOS_RELEASE_BUILDER_PATH is '
                                 'different: %s', release_builder_path)

        # Check ChromeOS ARC VERSION. E.g.
        arc_version = set(host.get_arc_version() for host in self._hosts)
        if len(arc_version) > 1:
            raise error.TestFail('Hosts\' CHROMEOS_ARC_VERSION is different: '
                                 '%s', arc_version)

        # Check ChromeOS model for unibuild.
        # TODO(pwang): Adding a check if we found how to detect host's model.

    def _verify_arc_hosts(self):
        """Verify all hosts' Android configuration consistency.

        This method should only be called after all hosts' Android has been
        successfully booted up."""
        # Check all hosts have same Android fingerprint.
        fingerprint = set(
                self._adb.run(host,
                              args=('shell', 'getprop',
                                    'ro.build.fingerprint')).stdout
                for host in self._hosts)
        if len(fingerprint) > 1:
            raise error.TestFail('Hosts\' supported fingerprint is different: '
                                 '%s', fingerprint)

    def _calculate_test_count_factor(self, bundle):
        """ Calculate the multiplicative factor for the test case number.

        The value equals to the times each test case is run, which is determined
        by the intersection of the supported ABIs of the CTS/GTS bundle and that
        of the tested device."""
        # This is only a conservative approximation. Some suites only run the
        # primary ABI, so to be fully precise, those have to be counted as 1.
        arm_abis = set(('armeabi-v7a', 'arm64-v8a'))
        x86_abis = set(('x86', 'x86_64'))
        if bundle and bundle.startswith('arm'):
            tradefed_abis = arm_abis
        elif bundle and bundle.startswith('x86'):
            tradefed_abis = x86_abis
        else:
            tradefed_abis = arm_abis | x86_abis
        self._test_count_factor = len(set(self._get_abilist()) & tradefed_abis)
        # Avoid setting timeout=0 (None) in any cases.
        self._timeout_factor = max(1, self._test_count_factor)

    def _try_adb_connect(self, host):
        """Attempts to connect to adb on the DUT.

        @param host: DUT that need to be connected.
        @return boolean indicating if adb connected successfully.
        """
        # Add ADB_TRACE=all for debugging adb connection failures.
        env = os.environ.copy()
        env['ADB_TRACE'] = 'all'
        try:
            # This may fail return failure due to a race condition in adb
            # connect (b/29370989). If adb is already connected, this command
            # will immediately return success.
            host_port = self._adb.get_adb_target(host)
            result = self._adb.run(
                    host,
                    args=('connect', host_port),
                    verbose=True,
                    env=env,
                    ignore_status=True,
                    timeout=constants.ADB_CONNECT_TIMEOUT_SECONDS)
            if result.exit_status != 0:
                return False

            result = self._adb.run(
                    host,
                    args=('devices', ),
                    env=env,
                    timeout=constants.ADB_CONNECT_TIMEOUT_SECONDS)
            pat = rf'^{re.escape(host_port)}\s+(.*)$'
            m = re.search(pat, result.stdout, re.MULTILINE)
            if not m:
                logging.info('No result found in with pattern: %s', pat)
                return False

            conn_state = m.group(1)
            if conn_state == 'offline':
                # An offline device is considered connected, to force reconnect
                # we need to explicitly disconnect first.
                logging.warn(
                        'ADB is offline, trying disconnect then reconnect')
                self._adb.run(None,
                              args=('disconnect', host_port),
                              verbose=True,
                              env=env,
                              ignore_status=True,
                              timeout=constants.ADB_CONNECT_TIMEOUT_SECONDS)
                return False
            if conn_state != 'device':
                logging.warn(
                        'ADB is in unknown state "%s", tests may fail to run',
                        conn_state)

            # Actually test the connection with an adb command as there can be
            # a race between detecting the connected device and actually being
            # able to run a command with authenticated adb.
            result = self._adb.run(
                    host,
                    args=('shell', 'exit'),
                    env=env,
                    ignore_status=True,
                    timeout=constants.ADB_CONNECT_TIMEOUT_SECONDS)
            return result.exit_status == 0
        except error.CmdTimeoutError as e:
            logging.warning(e)
            return False

    def _android_shell(self, host, command):
        """Run a command remotely on the device in an android shell

        This function is strictly for internal use only, as commands do not run
        in a fully consistent Android environment. Prefer adb shell instead.
        """
        host.run('android-sh -c ' + pipes.quote(command))

    def _connect_adb(self, host):
        """Sets up ADB connection to the ARC container.

        @param host: DUT that should be connected to.
        """
        logging.info('Setting up adb connection.')

        # adbd may take some time to come up. Repeatedly try to connect to adb.
        utils.poll_for_condition(
            lambda: self._try_adb_connect(host),
            timeout=constants.ADB_READY_TIMEOUT_SECONDS,
            sleep_interval=constants.ADB_POLLING_INTERVAL_SECONDS)

        logging.info('Successfully setup adb connection.')

    def _wait_for_arc_boot(self, host):
        """Wait until ARC is fully booted.

        Tests for the presence of the intent helper app to determine whether ARC
        has finished booting.
        @param host: DUT that need to be connected to.
        """

        def _intent_helper_running():
            result = self._adb.run(host,
                                   args=('shell', 'pgrep', '-f',
                                         'org.chromium.arc.intent_helper'),
                                   ignore_status=True)
            return bool(result.stdout)

        utils.poll_for_condition(
            _intent_helper_running,
            exception=error.TestFail(
                'Error: Timed out waiting for intent helper.'),
            timeout=constants.ARC_READY_TIMEOUT_SECONDS,
            sleep_interval=constants.ARC_POLLING_INTERVAL_SECONDS)

    def _disable_adb_install_dialog(self, host):
        """Disables a dialog shown on adb install execution.

        By default, on adb install execution, "Allow Google to regularly check
        device activity ... " dialog is shown. It requires manual user action
        so that tests are blocked at the point.
        This method disables it.
        """
        logging.info('Disabling the adb install dialog.')
        result = self._adb.run(host,
                               verbose=True,
                               args=('shell', 'settings', 'put', 'global',
                                     'verifier_verify_adb_installs', '0'))
        logging.info('Disable adb dialog: %s', result.stdout)

        result = self._adb.run(host,
                               verbose=True,
                               args=('shell', 'settings', 'put', 'global',
                                     'verifier_engprod', '1'))
        logging.info('Disable Play Protect dialog: %s', result.stdout)

        # Android "RescueParty" feature can reset the above settings when the
        # device crashes often. Disable the rescue during testing.
        # Keeping only for P and below since R has SELinux restrictions.
        if self._get_android_version() < 29:
            self._android_shell(host, 'setprop persist.sys.disable_rescue true')

    def _ready_arc(self):
        """Ready ARC and adb in parallel for running tests via tradefed."""
        key_path = os.path.join(self.tmpdir, 'test_key')
        with open(key_path, 'w') as f:
            f.write(constants.PRIVATE_KEY)
        os.environ['ADB_VENDOR_KEYS'] = key_path

        for _ in range(2):
            try:
                # Kill existing adb server to ensure that the env var is picked
                # up, and reset any previous bad state.
                self._kill_adb_server()

                # Random ADB port is required for CFT where containers use host
                # networking. Pick a random port every time as setup may fail
                # due to port collision.
                self._adb.pick_random_port()

                # TODO(pwang): connect_adb takes 10+ seconds on a single DUT.
                #              Parallelize it if it becomes a bottleneck.
                for host in self._hosts:
                    self._connect_adb(host)
                    self._disable_adb_install_dialog(host)
                    self._wait_for_arc_boot(host)
                self._verify_arc_hosts()
                return
            except (utils.TimeoutError, error.CmdTimeoutError):
                logging.error('Failed to set up adb connection. Retrying...')
        raise error.TestFail('Error: Failed to set up adb connection')

    def _safe_makedirs(self, path):
        """Creates a directory at |path| and its ancestors.

        Unlike os.makedirs(), ignore errors even if directories exist.
        """
        try:
            os.makedirs(path)
        except OSError as e:
            if not (e.errno == errno.EEXIST and os.path.isdir(path)):
                raise

    def _unzip(self, filename, password=''):
        """Unzip the file.

        The destination directory name will be the stem of filename.
        E.g., _unzip('foo/bar/baz.zip') will create directory at
        'foo/bar/baz', and then will inflate zip's content under the directory.
        If here is already a directory at the stem, that directory will be used.

        @param filename: Path to the zip archive.
        @param password: Optional password for unarchiving.
        @return Path to the inflated directory.
        """
        destination = os.path.splitext(filename)[0]
        if os.path.isdir(destination):
            logging.info('Skipping unzip %s, reusing content of %s', filename,
                         destination)
            return destination
        tmp = tempfile.mkdtemp(dir=os.path.dirname(filename))
        logging.info('Begin unzip %s', filename)
        try:
            unzip_args = ('-d', tmp, filename)
            if password:
                # It is ok to pass a password even if it is not actually
                # password protected. So this shouldn't fail for unencrypted
                # zips.
                unzip_args = ('-P', password) + unzip_args
            utils.run('unzip', args=unzip_args)
        except:
            logging.error('Failed unzip, cleaning up.')
            # Clean up just created files.
            shutil.rmtree(tmp, ignore_errors=True)
            raise
        logging.info('End unzip %s', filename)
        try:
            os.renames(tmp, destination)
        except:
            logging.error('Failed rename, cleaning up.')
            shutil.rmtree(destination, ignore_errors=True)
            shutil.rmtree(tmp, ignore_errors=True)
            raise
        return destination

    def _dir_size(self, directory):
        """Compute recursive size in bytes of directory."""
        size = 0
        for root, _, files in os.walk(directory):
            for name in files:
                try:
                    size += os.path.getsize(os.path.join(root, name))
                except OSError:
                    logging.error('Inaccessible path (crbug/793696): %s/%s',
                                  root, name)
        return size

    def _invalidate_download_cache(self):
        """Marks the download cache for deferred deletion.

        Used to make cache file operations atomic across failures and reboots.
        The caller is responsible to hold the lock to the cache.
        """
        if not os.path.exists(self._tradefed_cache_dirty):
            os.mkdir(self._tradefed_cache_dirty)

    def _validate_download_cache(self):
        """Validates and unmarks the download cache from deletion.

        Used to make cache file operations atomic across failures and reboots.
        The caller is responsible to hold the lock to the cache.
        """
        shutil.rmtree(self._tradefed_cache_dirty, ignore_errors=True)

    def _clean_download_cache_if_needed(self, force=False):
        """Invalidates cache to prevent it from growing too large."""
        # If the cache is large enough to hold a working set, we can simply
        # delete everything without thrashing.
        # TODO(ihf): Investigate strategies like LRU.
        clean = force
        with tradefed_utils.lock(self._tradefed_cache_lock):
            size = self._dir_size(self._tradefed_cache)
            if size > self._tradefed_cache_max_size_gib * (1 << 30):
                logging.info(
                    'Current cache size=%d got too large. Clearing %s.', size,
                    self._tradefed_cache)
                clean = True
            else:
                logging.info('Current cache size=%d of %s.', size,
                             self._tradefed_cache)
            if os.path.exists(self._tradefed_cache_dirty):
                logging.info('Found dirty cache.')
                clean = True
            if clean:
                logging.warning('Cleaning download cache.')
                shutil.rmtree(self._tradefed_cache, ignore_errors=True)
                self._safe_makedirs(self._tradefed_cache)
                shutil.rmtree(self._tradefed_cache_dirty, ignore_errors=True)

    def _download_to_cache(self, uri):
        """Downloads the uri from the storage server.

        It always checks the cache for available binaries first and skips
        download if binaries are already in cache.

        The caller of this function is responsible for holding the cache lock.

        @param uri: The Google Storage, dl.google.com or local uri.
        @return Path to the downloaded object, name.
        """
        if uri.startswith('gs://'):
            # For Google storage URIs, the ETag of the remote file can be
            # obtained.
            # Using ETags should also work for bundles that use "*-latest.zip"
            # naming scheme because ETag is supposed to update whenever a new
            # zip file is placed at the same URI.
            outdir_name = _GetETagFromGsUri(uri)
        else:
            outdir_name = hashlib.md5(uri.encode()).hexdigest()

        # We are hashing the uri instead of the binary. This is acceptable, as
        # the uris are supposed to contain version information and an object is
        # not supposed to be changed once created.
        output_dir = os.path.join(self._tradefed_cache, outdir_name)
        # Check for existence of cache entry. We check for directory existence
        # instead of file existence, so that _install_bundle can delete original
        # zip files to save disk space.
        if os.path.exists(output_dir):
            # TODO(crbug.com/800657): Mitigation for the invalid state. Normally
            # this should not happen, but when a lock is force borken due to
            # high IO load, multiple processes may enter the critical section
            # and leave a bad state permanently.
            if os.listdir(output_dir):
                logging.info('Skipping download of %s, reusing content of %s.',
                             uri, output_dir)
                return os.path.join(output_dir,
                    os.path.basename(urlparse.urlparse(uri).path))
            logging.error('Empty cache entry detected %s', output_dir)
        return self._download_to_dir(uri, output_dir)

    def _download_to_dir(self, uri, output_dir):
        """Downloads the gs|http|https|file uri from the storage server.

        @param uri: The Google Storage, dl.google.com or local uri.
        @output_dir: The directory where the downloaded file should be placed.
        @return Path to the downloaded object, name.
        """
        # Split uri into 3 pieces for use by gsutil and also by wget.
        parsed = urlparse.urlparse(uri)
        filename = os.path.basename(parsed.path)
        output = os.path.join(output_dir, filename)

        self._safe_makedirs(output_dir)
        if parsed.scheme not in ['gs', 'http', 'https', 'file']:
            raise error.TestFail(
                'Error: Unknown download scheme %s' % parsed.scheme)
        if parsed.scheme in ['http', 'https']:
            logging.info('Using wget to download %s to %s.', uri, output_dir)
            # We are downloading 1 file at a time, hence using -O over -P.
            utils.run(
                'wget',
                args=('--report-speed=bits', '-O', output, uri),
                verbose=True)
            return output

        if parsed.scheme in ['file']:
            logging.info('Copy the local file from %s to %s.', parsed.path,
                         output_dir)
            utils.run(
                'cp',
                args=('-f', parsed.path, output),
                verbose=True)
            return output

        # If the machine can access to the storage server directly,
        # defer to "gsutil" for downloading.
        logging.info('Downloading %s directly to %s.', uri, output)
        # b/17445576: gsutil rsync of individual files is not implemented.
        res = utils.run('gsutil',
                        args=('cp', uri, output),
                        verbose=True,
                        ignore_status=True)
        if not res or res.exit_status != 0:
            logging.warning('Retrying download...')
            utils.run('gsutil', args=('cp', uri, output), verbose=True)
        return output

    def _instance_copyfile(self, cache_path):
        """Makes a copy of a file from the (shared) cache to a wholy owned
        local instance. Also copies one level of cache directoy (MD5 named).
        """
        filename = os.path.basename(cache_path)
        dirname = os.path.basename(os.path.dirname(cache_path))
        instance_dir = os.path.join(self._tradefed_install, dirname)
        # Make sure destination directory is named the same.
        self._safe_makedirs(instance_dir)
        instance_path = os.path.join(instance_dir, filename)
        shutil.copyfile(cache_path, instance_path)
        return instance_path

    def _instance_copytree(self, cache_path):
        """Makes a copy of a directory from the (shared and writable) cache to
        a wholy owned local instance.

        TODO(ihf): Consider using cp -al to only copy links. Not sure if this
        is really a benefit across the container boundary, but it is risky due
        to the possibility of corrupting the original files by an lxc instance.
        """
        # We keep the top 2 names from the cache_path = .../dir1/dir2.
        dir2 = os.path.basename(cache_path)
        dir1 = os.path.basename(os.path.dirname(cache_path))
        instance_path = os.path.join(self._tradefed_install, dir1, dir2)
        # TODO(kinaba): Fix in a safer way.
        # Below is a workaround to avoid copying large CTS/GTS tree in test lab.
        # Contents of $cache_path/android-cts are symlinked to the destination
        # rather than copied.
        #  1) Why not symlink 'android-cts' itself? Because the tests will
        #     create results/ logs/ subplans/ subdirectory there. We do not
        #     want to write to the shared cache.
        #  2) Why not hardlink? Cache and the local directory may be on
        #     different mount points, so hardlink may not work.
        #  3) Why this isn't safe? Cache is cleared when it became full, even
        #     during the test is run on an instance.
        #  4) Why this is acceptable despite the unsatefy? Cache clearance is
        #     a rare event (once in 6 months). Skylab drones won't usually
        #     live that long, and even if it did, the failure is once in 6
        #     months after all.
        special_src = None
        special_dest = None
        if utils.is_in_container() and not client_utils.is_moblab():
            for xts_name in ['android-cts', 'android-gts', 'android-sts']:
                xts_root = os.path.join(cache_path, xts_name)
                if os.path.exists(xts_root):
                    special_src = xts_root
                    special_dest = os.path.join(instance_path, xts_name)
                    break
        if special_src:
            logging.info('SYMLINK&COPY contents of %s to instance %s',
                         cache_path, instance_path)
            self._safe_makedirs(special_dest)
            for entry in os.listdir(special_src):
                # Subdirectories are created by relative path from
                # tools/cts_tradefed. So for 'tools' dir we copy.
                if entry == 'tools':
                    shutil.copytree(os.path.join(special_src, entry),
                                    os.path.join(special_dest, entry))
                elif entry == 'testcases':
                    # Directory structure in testcases/ needs to be
                    # instantiated, because CTS tries `find` command
                    # in the directory without following symlinks
                    for subdir, _, files in os.walk(
                            os.path.join(special_src, entry)):
                        rel = os.path.relpath(subdir, special_src)
                        os.mkdir(os.path.join(special_dest, rel))
                        for file in files:
                            os.symlink(os.path.join(special_src, rel, file),
                                       os.path.join(special_dest, rel, file))
                else:
                    os.symlink(os.path.join(special_src, entry),
                               os.path.join(special_dest, entry))
        else:
            logging.info('Copying %s to instance %s', cache_path,
                         instance_path)
            shutil.copytree(cache_path, instance_path)

        # Hacky workaround for b/271219433 until GTS is fixed.
        # 'tradefed.jar' needs to be listed before 'tradefed-no-fwk.jar'
        # regardless of the locale. So here we just rename the latter.
        try:
            tools_dir = os.path.join(instance_path,
                                     self._get_tradefed_base_dir(), 'tools')
            os.rename(os.path.join(tools_dir, 'tradefed-no-fwk.jar'),
                      os.path.join(tools_dir, 'zz-tradefed-no-fwk.jar'))
            # Workaround for STS b/332649786
            os.rename(os.path.join(tools_dir, 'tradefed-test-framework.jar'),
                      os.path.join(tools_dir, 'zz-tradefed-test-framework.jar'))
        except OSError:
            pass
        return instance_path

    def _install_bundle(self, gs_uri, password=''):
        """Downloads a zip file, installs it and returns the local path.

        @param gs_uri: GS bucket that contains the necessary files.
        @param password: Optional password for unarchiving the bundle.
        """
        if not gs_uri.endswith('.zip'):
            raise error.TestFail('Error: Not a .zip file %s.', gs_uri)
        # Atomic write through of file.
        with tradefed_utils.lock(self._tradefed_cache_lock):
            # Atomic operations.
            self._invalidate_download_cache()
            # Download is lazy (cache_path may not actually exist if
            # cache_unzipped does).
            cache_path = self._download_to_cache(gs_uri)
            # Unzip is lazy as well (but cache_unzipped guaranteed to
            # exist).
            cache_unzipped = self._unzip(cache_path, password)
            # To save space we delete the original zip file. This works as
            # _download only checks existence of the cache directory for
            # lazily skipping download, and unzip itself will bail if the
            # unzipped destination exists. Hence we don't need the original
            # anymore.
            if os.path.exists(cache_path):
                logging.info('Deleting original %s', cache_path)
                os.remove(cache_path)
            # Erase dirty marker from disk.
            self._validate_download_cache()
            # We always copy files to give tradefed a clean copy of the
            # bundle.
            unzipped_local = self._instance_copytree(cache_unzipped)
        return unzipped_local

    def _install_files(self, gs_dir, files, permission):
        """Installs binary tools."""
        for filename in files:
            gs_uri = os.path.join(gs_dir, filename)
            # Atomic write through of file.
            with tradefed_utils.lock(self._tradefed_cache_lock):
                # We don't want to leave a corrupt cache for other jobs.
                self._invalidate_download_cache()
                cache_path = self._download_to_cache(gs_uri)
                # Mark cache as clean again.
                self._validate_download_cache()
                # This only affects the current job, so not part of cache
                # validation.
                local = self._instance_copyfile(cache_path)
            os.chmod(local, permission)
            # Keep track of PATH.
            local_dir = os.path.dirname(local)
            self._install_paths.append(local_dir)
            self._adb.add_path(local_dir)

    def _prepare_media(self, media_asset):
        """Downloads and offers the cached media files to tradefed."""
        if media_asset.uri:
            media = self._install_bundle(media_asset.uri)
            if os.path.islink(media_asset.localpath):
                os.unlink(media_asset.localpath)
            if os.path.isdir(media_asset.localpath):
                shutil.rmtree(media_asset.localpath)
            self._safe_makedirs(os.path.dirname(media_asset.localpath))
            os.symlink(media, media_asset.localpath)

            logging.info('Offered %s as a media directory in %s',
                    media, media_asset.localpath)

        # Records the number of existing media bundles, to check later.
        if os.path.isdir(media_asset.localpath):
            self._num_media_bundles = len(
                    os.listdir(media_asset.localpath))

    def _cleanup_media(self, media_asset):
        """Clean up the local copy of cached media files."""
        self._fail_on_unexpected_media_download(media_asset)
        if os.path.islink(media_asset.localpath):
            path = os.readlink(media_asset.localpath)
            os.unlink(media_asset.localpath)
            if os.path.isdir(path):
                logging.info('Cleaning up media files in %s', path)
                shutil.rmtree(path)

    def _fail_on_unexpected_media_download(self, media_asset):
        if os.path.isdir(media_asset.localpath):
            contents = os.listdir(media_asset.localpath)
            # Ignore a table-of-contents file created by newer xTS
            TOC_FILE = 'contents.toc'
            if TOC_FILE in contents:
                contents.remove(TOC_FILE)
            if len(contents) > self._num_media_bundles:
                raise error.TestFail(
                    'Failed: Unexpected media bundle was added %s' % contents)

    def _fetch_helpers_from_dut(self):
        """Fetches the CTS helpers from the dut and installs into the testcases
           subdirectory of our local autotest copy.
        """
        tf_testcases = os.path.join(self._repository, 'testcases')

        # Earlier checks enforce that each host has the same build fingerprint,
        # so we can assume that the packages from the first host will work
        # across the whole set.
        package_list = self._adb.run(
                self._hosts[0],
                args=('shell', 'getprop',
                      constants.TRADEFED_CTS_HELPERS_PROPERTY)).stdout.strip()
        for pkg in package_list.split(':'):
            if not pkg:
                continue
            apk_name = pkg + '.apk'
            logging.info('Installing CTS helper package %s to %s', apk_name,
                         tf_testcases)
            self._hosts[0].get_file(
                    os.path.join(constants.BOARD_CTS_HELPERS_DIR, apk_name),
                    tf_testcases)

    def _run(self, *args, **kwargs):
        """Executes the given command line.

        To support SDK tools, such as adb or aapt, this adds _install_paths
        to the extra_paths. Before invoking this, ensure _install_files() has
        been called.
        """
        kwargs['extra_paths'] = (
            kwargs.get('extra_paths', []) + self._install_paths)
        return utils.run(*args, **kwargs)

    def _collect_tradefed_global_log(self, result, destination):
        """Collects the tradefed global log.

        @param result: The result object from utils.run.
        @param destination: Autotest result directory (destination of logs).
        """
        match = re.search(r'Saved log to /tmp/(tradefed_global_log_.*\.txt)',
                          result.stdout)
        if not match:
            logging.debug(result.stdout)
            logging.error('no tradefed_global_log file is found')
            return

        name = match.group(1)
        dest = os.path.join(destination, 'logs', 'tmp')
        self._safe_makedirs(dest)
        shutil.copy(os.path.join('/tmp', name), os.path.join(dest, name))

    def _configure_tradefed_cache(self):
        """Configures Tradefed cache for current runtime environment."""
        # Tests in the lab run within individual lxc container instances.
        current_uid = os.getuid()
        current_user = pwd.getpwuid(current_uid)
        logging.info('Current user is: %d, %s',
                     current_uid, current_user.pw_name)
        if utils.is_in_container() and current_uid == 0:
            # SSP container
            cache_config = constants.TRADEFED_CACHE_CONTAINER
        elif utils.is_in_container():
            # CFT container
            if self._bundle_uri == 'DEV':
                cache_config = constants.TRADEFED_CACHE_CFT_DEV
            else:
                # Note DEV_WAIVER and DEV_MOBLAB jobs also use this.
                cache_config = constants.TRADEFED_CACHE_CFT
        else:
            # Local chroot environment
            cache_config = constants.TRADEFED_CACHE_LOCAL

        cache_root, max_size_gib = cache_config
        logging.info('Using cache_root = %s, max_size_gib = %s', cache_root,
                     max_size_gib)
        # The content of the cache survives across jobs.
        self._safe_makedirs(cache_root)
        self._tradefed_cache = os.path.join(cache_root, 'cache')
        self._tradefed_cache_lock = os.path.join(cache_root, 'lock')
        self._tradefed_cache_dirty = os.path.join(cache_root, 'dirty')
        self._tradefed_cache_max_size_gib = max_size_gib

    def _get_version_tuple(self, version):
        """Split version like 9_r14/9_sts-r14 to format (9, 14)."""
        vs = re.fullmatch(r"(.+)_.*r(\d+)", version)
        if not vs:
            logging.error("xTS wrong version format for %s !", version)
            raise UnsupportedSuiteVersion(version)
        return tuple(map(float, vs.groups()))

    def _get_valid_waivers(self, waivers_result, release_version):
        """Filter waivers by current CTS release version."""
        valid_waivers = []
        release_version_tuple = self._get_version_tuple(release_version)
        return [
                gcs_path for target_fixed_version, gcs_path in waivers_result
                if self._get_version_tuple(target_fixed_version) >
                release_version_tuple
        ]

    def _should_load_gcs_waivers(self, is_public):
        """Not supporting CTS_Instant and moblab now."""
        # Will not be supporting CTS_Instant since P waivers stopped updating.
        # Not support moblab for now since each moblab uses multiple service
        # accounts, so if set proper ACLs we need to maintain a list of moblab
        # service accounts.
        # TODO(ruki): potentially will support moblab if needed.
        # Since moblab will run public version tests so here just check is_public.
        return self._bundle_spec.suite_name in ['CTS', 'GTS', 'STS'
                                                ] and not is_public

    def _load_gcs_waivers(self, official_suite_version, is_dev=False):
        """Load GCS waivers."""
        expected_gcs_fail_files = []
        waivers_list = []
        # List waiver files from GCS bucket.
        try:
            result = utils.run('gsutil',
                               args=('ls', _GCS_WAIVERS_PATH),
                               verbose=True)
            waiver_files = result.stdout

            # Filter out waivers for current sdk_ver.
            # Default waivers will be put into expected_gcs_fail_files directly.
            # Non-default waivers will be filtered by TargetFixedVersion.
            # Waivers file name example : 9_r14-CTS-R.yaml, 11_sts-r12-STS-R.yaml
            for wf in waiver_files.splitlines():
                f = os.path.basename(wf)
                vs = re.fullmatch(r"(expected|.+r.+)-(.+)-(.+).yaml", f)
                if not vs:
                    continue
                target_fixed_version, suite_name, dessert = vs.groups()
                if dessert == self._SDK_VER_MAP[
                        self._get_android_version()] and self._bundle_spec.suite_name == suite_name:
                    if target_fixed_version == 'expected':
                        expected_gcs_fail_files.append(wf)
                    else:
                        waivers_list.append([target_fixed_version, wf])

        except error.CmdError as e:
            logging.warning(
                    'Skip loading GCS waivers. gsutil ls failed with: %s',
                    e)
            return set()

        try:
            if not is_dev:
                expected_gcs_fail_files.extend(
                        self._get_valid_waivers(
                                waivers_list, official_suite_version))
        except UnsupportedSuiteVersion as e:
            logging.warning(
                    'Skip loading GCS waivers for unsupported version format: %s',
                    e)

        gcs_local_fail_files = []
        with tempfile.TemporaryDirectory(prefix='cts-waivers_') as tmp:
            for failure_file in expected_gcs_fail_files:
                local_file_path = os.path.join(tmp,
                                               os.path.basename(failure_file))
                try:
                    utils.run('gsutil',
                              args=('cp', failure_file, local_file_path),
                              verbose=True)
                    gcs_local_fail_files.append(local_file_path)
                except error.CmdError as e:
                    logging.warning('gsutil cp failed for file %s with: %s',
                                    failure_file, e)
                    continue
            return self._get_expected_failures(tmp, is_dev)

    def _get_expected_failures(self,
                               expected_fail_dir,
                               is_dev=False):
        """Return a list of expected failures or no test module.

        @param expected_fail_dir: A directory with expected no tests or failures
                                  files.
        @param is_dev: Check if it's DEV runner we only apply default waivers.
        @return: A list of expected failures or no test modules for the current
                 testing device.
        """
        # Load waivers and manual tests so TF doesn't re-run them.
        expected_fail_files = []
        test_board = self._get_board_name()
        test_model = self._get_model_name()
        test_arch = self._get_board_arch()
        sdk_ver = self._get_android_version()
        first_api_level = self._get_first_api_level()
        if os.path.exists(expected_fail_dir):
            if is_dev:
                # For DEV runners, it runs the latest source code to detect
                # failures, so we should stop applying non default waivers.
                expected_fail_files += glob.glob(expected_fail_dir +
                                                 '/expected-*.yaml')
            else:
                expected_fail_files += glob.glob(expected_fail_dir + '/*.yaml')

        waivers = cts_expected_failure_parser.ParseKnownCTSFailures(
                expected_fail_files)

        return waivers.find_waivers(test_arch, test_board, test_model,
                                    self._bundle_abi, sdk_ver, first_api_level)

    def _get_abilist(self):
        """Return the abilist supported by calling adb command.

        This method should only be called after the android environment is
        successfully initialized."""
        if not self._abilist:
            for _ in range(3):
                abilist_str = self._adb.run(
                        self._hosts[0],
                        args=('shell', 'getprop',
                              'ro.product.cpu.abilist')).stdout.strip()
                if abilist_str:
                    self._abilist = abilist_str.split(',')
                    break
                else:
                    # TODO(kinaba): Sometimes getprop returns an empty string.
                    # Investigate why. For now we mitigate the bug by retries.
                    logging.error('Empty abilist.')
        return self._abilist

    def _get_feature_list(self):
        """Return the Android feature list via adb.

        This method should only be called after the android environment is
        successfully initialized."""
        if not self._feature_list:
            features_str = self._adb.run(
                    self._hosts[0],
                    args=('shell', 'pm', 'list', 'features')).stdout
            for line in features_str.split():
                if line.startswith('feature:'):
                    self._feature_list.append(line[8:])
        return self._feature_list

    def _has_back_camera(self):
        return 'android.hardware.camera' in self._get_feature_list()

    def _is_back_camera_collect_test(self, test_name):
        return 'camerabox.back' in test_name and 'collect-tests' in test_name

    def _get_release_branch_number(self):
        """Returns the DUT branch number (z of Rxx-yyyyy.z.w) or 0 on error."""
        if not self._release_branch_number:
            ver = (self._hosts[0].get_release_version() or '').split('.')
            self._release_branch_number = (int(ver[1]) if len(ver) >= 3 else 0)
        return self._release_branch_number

    def _get_board_arch(self):
        """Return target DUT arch name."""
        if not self._board_arch:
            self._board_arch = ('arm' if self._hosts[0].get_cpu_arch() == 'arm'
                else 'x86')
        return self._board_arch

    def _get_board_name(self):
        """Return target DUT board name."""
        if not self._board_name:
            self._board_name = self._hosts[0].get_board().split(':')[1]
        return self._board_name

    def _get_model_name(self):
        """Return target DUT model name."""
        if not self._model_name:
            self._model_name = self._hosts[0].get_model_from_cros_config()
        return self._model_name

    def _get_android_version(self):
        """Return target DUT Android SDK version"""
        # TODO(kinaba): factor this out to server/hosts/cros_host.py
        if not self._android_version:
            self._android_version = self._hosts[0].run(
                'grep ANDROID_SDK /etc/lsb-release',
                ignore_status=True).stdout.rstrip().split('=')[1]
        return int(self._android_version)

    def _get_first_api_level(self):
        """Return target DUT Android first API level."""
        if not self._first_api_level:
            self._first_api_level = self._hosts[0].get_arc_first_api_level()
        return int(self._first_api_level)

    def _get_max_retry(self, max_retry):
        """Return the maximum number of retries.

        @param max_retry: max_retry specified in the control file.
        @return: number of retries for this specific host.
        """
        if max_retry is None:
            max_retry = self._get_branch_retry(self._BRANCH_DEFAULT_RETRY)
        candidate = [max_retry]
        candidate.append(self._get_board_retry())
        candidate.append(self._get_branch_retry(self._BRANCH_MAX_RETRY))
        return min(x for x in candidate if x is not None)

    def _get_board_retry(self):
        """Return the maximum number of retries for DUT board name.

        @return: number of max_retry or None.
        """
        board = self._get_board_name()
        if board in self._BOARD_MAX_RETRY:
            return self._BOARD_MAX_RETRY[board]
        logging.info('No board retry specified for board: %s', board)
        return None

    def _get_branch_retry(self, table):
        """Returns the retry count for DUT branch number defined in |table|."""
        number = self._get_release_branch_number()
        for lowerbound, retry in reversed(table):
            if lowerbound <= number:
                return retry
        logging.warning('Could not establish channel. Using retry=0.')
        return 0

    def _is_tablet_mode_device(self):
        """Returns if running the test on a tabled mode device"""
        # TODO(kinaba): consider adding per-model check
        board = self._get_board_name()
        return any(board.startswith(b) for b in constants.TABLET_MODE_BOARDS)

    def _run_commands(self, commands, **kwargs):
        """Run commands on all the hosts."""
        # We need to copy the ADB key to the device to run adb on it.
        pre_commands = []
        if any(command.startswith('adb ') for command in commands):
            key_path = '/tmp/arc.adb_key'
            for host in self._hosts:
                host.env['ADB_VENDOR_KEYS'] = key_path
            pre_commands = [
                    'adb kill-server',
                    'echo %s > %s' %
                    (pipes.quote(constants.PRIVATE_KEY), key_path),
                    # Workaround b/285802634: no-op command to ensure connection
                    'adb shell cd'
            ]

        for host in self._hosts:
            if pre_commands:
                logging.info('Running DUT adb setup')
                for command in pre_commands:
                    host.run(command, ignore_status=True, verbose=False)
            for command in commands:
                logging.info('RUN: %s\n', command)
                output = host.run(command, **kwargs)
                logging.info('END: %s\n', command)
                logging.debug(output)

    def _override_powerd_prefs(self):
        """Overrides powerd prefs to prevent screen from turning off, complying
        with CTS requirements.

        This is a remote version of PowerPrefChanger which ensures overrided
        policies won't persist across reboots by bind-mounting onto the config
        directory.
        """
        pref_dir = constants.POWERD_PREF_DIR
        temp_dir = constants.POWERD_TEMP_DIR
        commands = (
                'cp -r %s %s' % (pref_dir, temp_dir),
                'echo 1 > %s/ignore_external_policy' % temp_dir,
                'echo 0 | tee %s/{,un}plugged_{dim,off,suspend}_ms' % temp_dir,
                'mount --bind %s %s' % (temp_dir, pref_dir),
                'restart powerd',
        )
        try:
            self._run_commands(commands)
        except (error.AutoservRunError, error.AutoservSSHTimeout):
            logging.warning('Failed to override powerd policy, tests depending '
                            'on screen being always on may fail.')

    def _restore_powerd_prefs(self):
        """Restores powerd prefs overrided by _override_powerd_prefs()."""
        pref_dir = constants.POWERD_PREF_DIR
        temp_dir = constants.POWERD_TEMP_DIR
        commands = (
                'umount %s' % pref_dir,
                'restart powerd',
                'rm -rf %s' % temp_dir,
        )
        try:
            self._run_commands(commands)
        except (error.AutoservRunError, error.AutoservSSHTimeout):
            logging.warning('Failed to restore powerd policy, overrided policy '
                            'will persist until device reboot.')

    def _mute_device(self):
        """Mutes the device to avoid noises while running tests"""
        try:
            self._run_commands(['cras_test_client --mute 1'],
                               ignore_status=True)
        except:
            logging.warning('Failed to mute the device')

    def _clean_crash_logs(self):
        try:
            self._run_commands(['rm -f /home/chronos/crash/*'])
        except (error.AutoservRunError, error.AutoservSSHTimeout):
            logging.warning('Failed to clean up crash logs.')

    def _run_and_parse_tradefed(self, command):
        """Kick off the tradefed command.

        @param command: Lists of command tokens.
        @raise TestFail: when a test failure is detected.
        @return: tuple of (tests, pass, fail, notexecuted) counts.
        """
        target_argument = []
        for host in self._hosts:
            target_argument += ['-s', self._adb.get_adb_target(host)]
        shard_argument = []
        if len(self._hosts) > 1:
            if self._SHARD_CMD:
                shard_argument = [self._SHARD_CMD, str(len(self._hosts))]
            else:
                logging.warning('cts-tradefed shard command isn\'t defined, '
                                'falling back to use single device.')
        command = command + target_argument + shard_argument

        try:
            output = self._run_tradefed(command)
        except Exception as e:
            self._log_java_version()
            if isinstance(e, error.CmdTimeoutError):
                pass
            elif isinstance(e, error.CmdError) and e.result_obj.exit_status == 137:
                logging.error('Killed by SIGKILL.')
            else:
                # In case this happened due to file corruptions, try to
                # force to recreate the cache.
                logging.error('Failed to run tradefed! Cleaning up now.')
                self._clean_download_cache_if_needed(force=True)
            raise

        result_destination = self._default_tradefed_base_dir()
        # Gather the global log first. Datetime parsing below can abort the test
        # if tradefed startup had failed. Even then the global log is useful.
        self._collect_tradefed_global_log(output, result_destination)
        # Result parsing must come after all other essential operations as test
        # warnings, errors and failures can be raised here.
        base = self._default_tradefed_base_dir()
        path = tradefed_utils.get_test_result_xml_path(base)
        if self._waivers is None:
            try:
                official_suite_version = tradefed_utils.get_test_result_suite_version(
                        path)
                self._load_waivers(official_suite_version)
            except:
                logging.warning('Skip loading waivers due to error ',
                                exc_info=True)
        return tradefed_utils.parse_tradefed_testresults_xml(
            test_result_xml_path=path,
            waivers=self._waivers)

    def _setup_result_directories(self):
        """Sets up the results and logs directories for tradefed.

        Tradefed saves the logs and results at:
          self._repository/results/$datetime/
          self._repository/results/$datetime.zip
          self._repository/logs/$datetime/
        Because other tools rely on the currently chosen Google storage paths
        we need to keep destination_results in:
          self.resultsdir/android-cts/results/$datetime/
          self.resultsdir/android-cts/results/$datetime.zip
          self.resultsdir/android-cts/results/logs/$datetime/
        To bridge between them, create symlinks from the former to the latter.
        """
        logging.info('Setting up tradefed results and logs directories.')

        results_destination = self._default_tradefed_base_dir()
        logs_destination = os.path.join(results_destination, 'logs')
        directory_mapping = [
            (os.path.join(self._repository, 'results'), results_destination),
            (os.path.join(self._repository, 'logs'), logs_destination),
        ]

        for (tradefed_path, final_path) in directory_mapping:
            if os.path.exists(tradefed_path):
                shutil.rmtree(tradefed_path)
            self._safe_makedirs(final_path)
            os.symlink(final_path, tradefed_path)

    def _default_tradefed_base_dir(self):
        return os.path.join(self.resultsdir, self._get_tradefed_base_dir())

    def _install_plan(self, subplan):
        """Copy test subplan to CTS-TF.

        @param subplan: CTS subplan to be copied into TF.
        """
        logging.info('Install subplan: %s', subplan)
        subplans_tf_dir = os.path.join(self._repository, 'subplans')
        if not os.path.exists(subplans_tf_dir):
            os.makedirs(subplans_tf_dir)
        test_subplan_file = os.path.join(self.bindir, 'subplans',
                                         '%s.xml' % subplan)
        try:
            shutil.copy(test_subplan_file, subplans_tf_dir)
        except (shutil.Error, OSError, IOError) as e:
            raise error.TestFail(
                'Error: failed to copy test subplan %s to CTS bundle. %s' %
                (test_subplan_file, e))

    def _should_skip_test(self, _bundle):
        """Some tests are expected to fail and are skipped.

        Subclasses should override with specific details.
        """
        return False

    def _should_reboot(self, steps):
        """Oracle to decide if DUT should reboot or just restart Chrome.

        For now we will not reboot after the first two iterations, but on all
        iterations afterward as before. In particular this means that most CTS
        tests will now not get a "clean" machine, but one on which tests ran
        before. But we will still reboot after persistent failures, hopefully
        not causing too many flakes down the line.
        """
        if steps < 3:
            return False
        return True

    def _copy_extra_artifacts_dut(self, extra_artifacts, host, output_dir):
        """ Upload the custom artifacts """
        self._safe_makedirs(output_dir)

        for artifact in extra_artifacts:
            logging.info('Copying extra artifacts from "%s" to "%s".',
                         artifact, output_dir)
            try:
                self._adb.run(host,
                              verbose=True,
                              timeout=120,
                              args=('pull', artifact, output_dir))
            except:
                # Maybe ADB connection failed, or the artifacts don't exist.
                logging.exception('Copying extra artifacts failed.')

    def _copy_extra_artifacts_host(self, extra_artifacts, host, output_dir):
        """ Upload the custom artifacts """
        self._safe_makedirs(output_dir)

        for artifact in extra_artifacts:
            logging.info('Copying extra artifacts from "%s" to "%s".',
                         artifact, output_dir)
            for extracted_path in glob.glob(artifact):
                logging.info('... %s', extracted_path)
                # Move it not to collect it again in future retries.
                shutil.move(extracted_path, output_dir)

    def _run_tradefed_list_results(self):
        """Run the `tradefed list results` command.

        @return: tuple of the last (session_id, pass, fail, all_done?).
        """

        # Fix b/143580192: We set the timeout to 3 min. It never takes more than
        # 10s on light disk load.
        output = self._run_tradefed_with_timeout(['list', 'results'], 180)

        # Parses the last session from the output that looks like:
        #
        # Session  Pass  Fail  Modules Complete ...
        # 0        90    10    1 of 2
        # 1        199   1     2 of 2
        # ...
        lastmatch = None
        for m in re.finditer(r'^(\d+)\s+(\d+)\s+(\d+)\s+(\d+) of (\d+)',
                             output.stdout, re.MULTILINE):
            session, passed, failed, done, total = map(int,
                                                       m.group(1, 2, 3, 4, 5))
            lastmatch = (session, passed, failed, done == total)
        return lastmatch

    def _get_bundle_specification(self, uri, bundle):
        """Get the bundle information.
        """
        if uri and (uri.startswith('http') or uri.startswith('gs')):
            return BundleSpecification(uri, password='')
        else:
            # Get the module file path of a derived class via inheritance.
            cheets_path = sys.modules[self.__class__.__module__].__file__
            config_file = 'bundle_url_config.json'
            config_path = os.path.abspath(os.path.join(cheets_path, '..', config_file))
            url_config = bundle_utils.load_config(config_path)
            bundle_password = bundle_utils.get_bundle_password(url_config)
            suite_name = bundle_utils.get_suite_name(url_config).upper()

            return BundleSpecification(
                    bundle_utils.make_bundle_url(url_config, uri, bundle),
                    bundle_password, suite_name)

    def _wait_cpu_cooldown(self, timeout):
        crosvm_cpu_usage_cmd = "top -bn1 | awk '{if ($12 == \"crosvm\") print $9;}'"
        cpu_temperature_cmd = "cat /sys/class/thermal/thermal_zone0/temp"
        check_cnt = 2
        deadline = time.time() + timeout
        while check_cnt and time.time() < deadline:
            crosvm_cpu_usage = float(self._hosts[0].run(crosvm_cpu_usage_cmd,
                                                        ignore_status=True,
                                                        verbose=False).stdout)
            cpu_temperature = int(self._hosts[0].run(cpu_temperature_cmd,
                                                     ignore_status=True,
                                                     verbose=False).stdout)
            if crosvm_cpu_usage > 10 or cpu_temperature > 45000:
                check_cnt = 2
            else:
                check_cnt -= 1
            logging.info(
                    "cpu is busy, wait 10s, crosvm cpu utlization percent = %2f, cpu_temperature = %d, check_cnt = %d, timeout = %ds",
                    crosvm_cpu_usage, cpu_temperature, check_cnt,
                    deadline - time.time())
            time.sleep(10)

    def _tradefed_retry_command(self, template, session_id):
        raise NotImplementedError('Subclass should override this function')

    def _tradefed_run_command(self, template):
        raise NotImplementedError('Subclass should override this function')

    def _tradefed_cmd_path(self):
        raise NotImplementedError('Subclass should override this function')

    def _tradefed_env(self):
        env = os.environ.copy()
        env['ANDROID_ADB_SERVER_PORT'] = str(self._adb.get_port())
        # See b/262183144. CTS implicity assumes how shell expands "*.jar".
        env['LC_COLLATE'] = 'en_US.UTF-8'
        # b/318310878: Tell TF "feature server" to use random port
        env['TF_SERVICE_PORT'] = '0'
        return env

    def _run_tradefed_with_timeout(self, command, timeout):
        tradefed = self._tradefed_cmd_path()
        with tradefed_utils.adb_keepalive(self._adb.get_adb_targets(
                self._hosts),
                                          self._install_paths,
                                          socket=self._adb.get_socket()):
            logging.info('RUN(timeout=%d): %s', timeout,
                         ' '.join([tradefed] + command))
            output = self._run(
                tradefed,
                args=tuple(command),
                env=self._tradefed_env(),
                timeout=timeout,
                verbose=True,
                ignore_status=False,
                # Make sure to tee tradefed stdout/stderr to autotest logs
                # continuously during the test run.
                stdout_tee=utils.TEE_TO_LOGS,
                stderr_tee=utils.TEE_TO_LOGS)
            logging.info('END: %s\n', ' '.join([tradefed] + command))
        return output

    def _run_tradefed(self, command):
        timeout = self._timeout * self._timeout_factor
        if self._job_deadline is not None:
            clipped = int(min(timeout, self._job_deadline - time.time()))
            # Even the shortest tradefed run takes 1.5 minutes. Took 2x'ed
            # value as a threshold that a meaningful test can run.
            if clipped < 3 * 60:
                raise error.TestError(
                        'Hitting job time limit: only %s seconds left' %
                        clipped)
            timeout = clipped
        return self._run_tradefed_with_timeout(command, timeout)

    def _run_tradefed_with_retries(self,
                                   test_name,
                                   run_template,
                                   retry_template,
                                   timeout,
                                   media_asset=None,
                                   enable_default_apps=False,
                                   vm_force_max_resolution=False,
                                   vm_tablet_mode=False,
                                   target_module=None,
                                   target_plan=None,
                                   executable_test_count=None,
                                   bundle=None,
                                   use_helpers=False,
                                   extra_artifacts=[],
                                   extra_artifacts_host=[],
                                   login_precondition_commands=[],
                                   precondition_commands=[],
                                   prerequisites=[],
                                   chrome_feature=None):
        """Run CTS/GTS with retry logic.

        We first kick off the specified module. Then rerun just the failures
        on the next MAX_RETRY iterations.
        """
        for prereq in prerequisites:
            result = tradefed_prerequisite.check(prereq, self._hosts)
            if not result[0]:
                raise error.TestError(result[1])

        # On dev and beta channels timeouts are sharp, lenient on stable.
        self._timeout = timeout
        if (self._get_release_branch_number() >=
                constants.APPROXIMATE_STABLE_BRANCH_NUMBER):
            self._timeout += 3600

        if self._should_skip_test(bundle):
            logging.warning('Skipped test %s', ' '.join(test_name))
            return

        steps = -1  # For historic reasons the first iteration is not counted.
        self.summary = ''
        board = self._get_board_name()
        session_id = None

        self._setup_result_directories()
        if media_asset:
            self._prepare_media(media_asset)

        # This loop retries failures. For this reason please do not raise
        # TestFail in this loop if you suspect the failure might be fixed
        # in the next loop iteration.
        while steps < self._max_retry:
            steps += 1
            keep_media = media_asset and media_asset.uri and steps >= 1
            self._run_commands(login_precondition_commands, ignore_status=True)

            session_log_dir = os.path.join(self.resultsdir,
                                           'login_session_log',
                                           'step%02d' % steps)
            with login.login_chrome(
                    hosts=self._hosts,
                    board=board,
                    dont_override_profile=keep_media,
                    enable_default_apps=enable_default_apps,
                    vm_force_max_resolution=vm_force_max_resolution,
                    log_dir=session_log_dir,
                    feature=chrome_feature) as current_logins, \
                            self._adb.create_tunnel():
                if self._should_reboot(steps):
                    # TODO(rohitbm): Evaluate if power cycle really helps with
                    # Bluetooth test failures, and then make the implementation
                    # more strict by first running complete restart and reboot
                    # retries and then perform power cycle.
                    #
                    # Currently, (steps + 1 == self._max_retry) means that
                    # hard_reboot is attempted after "this" cycle failed. Then,
                    # the last remaining 1 step will be run on the rebooted DUT.
                    hard_reboot = (self._hard_reboot_on_failure
                        and steps + 1 == self._max_retry)
                    for current_login in current_logins:
                        current_login.need_reboot(hard_reboot=hard_reboot)
                self._ready_arc()
                self._calculate_test_count_factor(bundle)

                # Check the ABI list and skip (pass) the tests if not applicable.
                # This needs to be done after _ready_arc() for reading the device's
                # ABI list from the booted ARC instance.
                if '--abi' in run_template:
                    abi = run_template[run_template.index('--abi') + 1]
                    abilist = self._get_abilist()
                    if abilist and abi not in abilist:
                        logging.info(
                                'Specified ABI %s is not in the device ABI list %s. Skipping.',
                                abi, abilist)
                        return

                # Skip back-camera collect tests on devices without back camera
                if (self._is_back_camera_collect_test(test_name) and
                        not self._has_back_camera()):
                    logging.info('No back camera. Skipping back-camera collect-tests.')
                    return

                if vm_tablet_mode:
                    self._run_commands([
                            'inject_powerd_input_event --code=tablet --value=1'
                    ],
                                       ignore_status=True)

                # TODO(kinaba): Make it a general config (per-model choice
                # of tablet,clamshell,default) if the code below works.
                elif utils.is_in_container() and not client_utils.is_moblab():
                    # Force laptop mode for non TABLET_MODE_BOARDS
                    if not self._is_tablet_mode_device():
                        self._run_commands(
                            ['inject_powerd_input_event --code=tablet --value=0'],
                            ignore_status=True)

                self._run_commands(precondition_commands, ignore_status=True)
                if use_helpers:
                    self._fetch_helpers_from_dut()

                # On drawcia, CPU is too busy during CTS and cause RecordingTest easy to fail.
                # Wait until CPU cool down before running CtsCameraTestCases.See b/270081260.
                test_model = self._get_model_name()
                if test_model == 'drawcia' and 'CtsCameraTestCases' in test_name:
                    try:
                        self._wait_cpu_cooldown(1800)
                    except:
                        logging.exception('Wait cpu cool down failed.')
                # Run tradefed.
                if session_id == None:
                    if target_plan is not None:
                        self._install_plan(target_plan)

                    logging.info('Running %s:', test_name)
                    command = self._tradefed_run_command(run_template)
                else:
                    logging.info('Retrying failures of %s with session_id %d:',
                                 test_name, session_id)
                    command = self._tradefed_retry_command(retry_template,
                                                           session_id)

                if media_asset and media_asset.uri:
                    # Clean-up crash logs from previous sessions to ensure
                    # enough disk space for 16GB storage devices: b/156075084.
                    if not keep_media:
                        self._clean_crash_logs()
                # b/196748125. Mute before running tests to avoid noises.
                self._mute_device()
                # TODO(b/182397469): speculatively disable the "screen-on"
                # handler for dEQP. Revert when the issue is resolved.
                keep_screen_on = not (target_module
                                      and "CtsDeqpTestCases" in target_module)
                if keep_screen_on:
                    self._override_powerd_prefs()
                try:
                    waived_tests = self._run_and_parse_tradefed(command)
                finally:
                    if keep_screen_on:
                        self._restore_powerd_prefs()
                if media_asset:
                    self._fail_on_unexpected_media_download(media_asset)
                result = self._run_tradefed_list_results()
                if not result:
                    logging.error('Did not find any test results. Retry.')
                    for current_login in current_logins:
                        current_login.need_reboot()
                    continue

                last_waived = len(waived_tests)
                last_session_id, last_passed, last_failed, last_all_done =\
                    result

                if last_failed > last_waived or not utils.is_in_container():
                    for host in self._hosts:
                        dir_name = "%s-step%02d" % (host.hostname, steps)
                        output_dir = os.path.join(
                            self.resultsdir, 'extra_artifacts', dir_name)
                        self._copy_extra_artifacts_dut(
                            extra_artifacts, host, output_dir)
                        self._copy_extra_artifacts_host(
                            extra_artifacts_host, host, output_dir)

                if last_passed + last_failed > 0:
                    # At least one test had run, which means the media push step
                    # of tradefed didn't fail. To free up the storage earlier,
                    # delete the copy on the server side. See crbug.com/970881
                    if media_asset:
                        self._cleanup_media(media_asset)

                if last_failed < last_waived:
                    logging.error(
                        'Error: Internal waiver bookkeeping has become '
                        'inconsistent (f=%d, w=%d)', last_failed, last_waived)

                msg = 'run' if session_id == None else ' retry'
                msg += '(p=%s, f=%s, w=%s)' % (last_passed, last_failed,
                                               last_waived)
                self.summary += msg
                logging.info('RESULT: %s %s', msg, result)

                # Overwrite last_all_done if the executed test count is equal
                # to the known test count of the job.
                if (not last_all_done and executable_test_count != None and
                    (last_passed + last_failed in executable_test_count)):
                    logging.warning('Overwriting all_done as True, since the '
                                    'explicitly set executable_test_count '
                                    'tests have run.')
                    last_all_done = True

                # Check for no-test modules. We use the "all_done" indicator
                # provided by list_results to decide if there are outstanding
                # modules to iterate over (similar to missing tests just on a
                # per-module basis).
                notest = (last_passed + last_failed == 0 and last_all_done)
                if target_module in self._notest_modules:
                    if notest:
                        logging.info('Package has no tests as expected.')
                        return
                    else:
                        # We expected no tests, but the new bundle drop must
                        # have added some for us. Alert us to the situation.
                        raise error.TestFail(
                            'Failed: Remove module %s from '
                            'notest_modules directory!' % target_module)
                elif notest:
                    logging.error('Did not find any tests in module. Hoping '
                                  'this is transient. Retry after reboot.')
                    for current_login in current_logins:
                        current_login.need_reboot()
                    continue

                # After the no-test check, commit the pass/fail count.
                waived = last_waived
                session_id, passed, failed, all_done =\
                    last_session_id, last_passed, last_failed, last_all_done

                # Check if all the tests passed.
                if failed <= waived and all_done:
                    break

                # TODO(b/127908450) Tradefed loses track of not-executed tests
                # when the commandline pattern included '*', and retry run for
                # them wrongly declares all tests passed. This is misleading.
                # Rather, we give up the retry and report the result as FAIL.
                # TODO(b/243725038) Ditto for sharding cases.
                if not all_done and ('*' in ''.join(run_template)
                                     or '--shard-count' in run_template):
                    break

        if session_id == None:
            raise error.TestFail('Error: Could not find any tests in module.')

        if failed <= waived and all_done:
            # TODO(ihf): Make this error.TestPass('...') once
            # available.
            if steps > 0 and self._warn_on_test_retry:
                raise error.TestWarn(
                    'Passed: after %d retries passing %d tests, '
                    'waived=%d. %s' % (steps, passed, waived,
                                       self.summary))
            return

        raise error.TestFail(
                'Failed: after %d retries giving up. '
                'passed=%d, failed=%d, waived=%d%s. %s' %
                (steps, passed, failed, waived,
                 '' if all_done else ', notexec>=1', self.summary))
