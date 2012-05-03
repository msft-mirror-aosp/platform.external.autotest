# Copyright (c) 2012 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import dbus, glob, logging, os, re, shutil, socket, stat, subprocess, sys, time
from dbus.mainloop.glib import DBusGMainLoop

import auth_server, common, constants, cros_logging, cros_ui, cryptohome
import dns_server, flimflam_test_path, login, ownership, pyauto_test
from autotest_lib.client.bin import utils
from autotest_lib.client.common_lib import error
import flimflam # Requires flimflam_test_path to be imported first.

class UITest(pyauto_test.PyAutoTest):
    """Base class for tests that drive some portion of the user interface.

    By default subclasses will use the default remote credentials before
    the run_once method is invoked, and will log out at the completion
    of the test case even if an exception is thrown.

    Subclasses can opt out of the automatic login by setting the member
    variable 'auto_login' to False.

    Subclasses can log in with arbitrary credentials by passing
    the 'creds' parameter in their control file.  See the documentation of
    UITest.initialize for more details.

    If your subclass overrides the initialize() or cleanup() methods, it
    should make sure to invoke this class' version of those methods as well.
    The standard super(...) function cannot be used for this, since the base
    test class is not a 'new style' Python class.
    """
    version = 1

    auto_login = True
    fake_owner = True
    username = None
    password = None

    # Processes that we know crash and are willing to ignore.
    crash_blacklist = []

    # ftrace-related files.
    _ftrace_process_fork_event_enable_file = \
        '/sys/kernel/debug/tracing/events/sched/sched_process_fork/enable'
    _ftrace_process_fork_event_filter_file = \
        '/sys/kernel/debug/tracing/events/sched/sched_process_fork/filter'
    _ftrace_signal_generate_event_enable_file = \
        '/sys/kernel/debug/tracing/events/signal/signal_generate/enable'
    _ftrace_signal_generate_event_filter_file = \
        '/sys/kernel/debug/tracing/events/signal/signal_generate/filter'
    _ftrace_trace_file = '/sys/kernel/debug/tracing/trace'

    # This is a symlink.  We look up the real path at runtime by following it.
    _resolv_test_file = 'resolv.conf.test'
    _resolv_bak_file = 'resolv.conf.bak'

    _last_chrome_log = ''


    def listen_to_signal(self, callback, signal, interface):
        """Listens to the given |signal| that is sent to power manager.
        """
        self._system_bus.add_signal_receiver(
            handler_function=callback,
            signal_name=signal,
            dbus_interface=interface,
            bus_name=None,
            path='/')


    def __connect_to_flimflam(self):
        """Connect to the network manager via DBus.

        Stores dbus connection in self._flim upon success, throws on failure.
        """
        self._bus_loop = DBusGMainLoop(set_as_default=True)
        self._system_bus = dbus.SystemBus(mainloop=self._bus_loop)
        self._flim = flimflam.FlimFlam(self._system_bus)


    def __get_host_by_name(self, hostname):
        """Resolve the dotted-quad IPv4 address of |hostname|

        This used to use suave python code, like this:
            hosts = socket.getaddrinfo(hostname, 80, socket.AF_INET)
            (fam, socktype, proto, canonname, (host, port)) = hosts[0]
            return host

        But that hangs sometimes, and we don't understand why.  So, use
        a subprocess with a timeout.
        """
        try:
            host = utils.system_output('%s -c "import socket; '
                                       'print socket.gethostbyname(\'%s\')"' % (
                                       sys.executable, hostname),
                                       ignore_status=True, timeout=2)
        except Exception as e:
            logging.warning(e)
            return None
        return host or None


    def __attempt_resolve(self, hostname, ip, expected=True):
        logging.debug('Attempting to resolve %s to %s' % (hostname, ip))
        try:
            host = self.__get_host_by_name(hostname)
            logging.debug('Resolve attempt for %s got %s' % (hostname, host))
            return host and (host == ip) == expected
        except socket.gaierror as err:
            logging.error(err)


    def use_local_dns(self, dns_port=53):
        """Set all devices to use our in-process mock DNS server.
        """
        self._dnsServer = dns_server.LocalDns(fake_ip='127.0.0.1',
                                              local_port=dns_port)
        self._dnsServer.run()
        # Turn off captive portal checking, until we fix
        # http://code.google.com/p/chromium-os/issues/detail?id=19640
        self.check_portal_list = self._flim.GetCheckPortalList()
        self._flim.SetCheckPortalList('')
        # Set all devices to use locally-running DNS server.
        try:
            # Follow resolv.conf symlink.
            resolv = os.path.realpath(constants.RESOLV_CONF_FILE)
            # Grab path to the real file, do following work in that directory.
            resolv_dir = os.path.dirname(resolv)
            resolv_test = os.path.join(resolv_dir, self._resolv_test_file)
            resolv_bak = os.path.join(resolv_dir, self._resolv_bak_file)
            resolv_contents = 'nameserver 127.0.0.1'
            # Back up the current resolv.conf.
            os.rename(resolv, resolv_bak)
            # To stop flimflam from editing resolv.conf while we're working
            # with it, we want to make the directory -r-x-r-x-r-x.  Open an
            # fd to the file first, so that we'll retain the ability to
            # alter it.
            resolv_fd = open(resolv, 'w')
            self._resolv_dir_mode = os.stat(resolv_dir).st_mode
            os.chmod(resolv_dir, (stat.S_IRUSR | stat.S_IXUSR |
                                  stat.S_IRGRP | stat.S_IXGRP |
                                  stat.S_IROTH | stat.S_IXOTH))
            resolv_fd.write(resolv_contents)
            resolv_fd.close()
            assert utils.read_one_line(resolv) == resolv_contents
        except Exception as e:
            logging.error(str(e))
            raise e

        utils.poll_for_condition(
            lambda: self.__attempt_resolve('www.google.com.', '127.0.0.1'),
            utils.TimeoutError('Timed out waiting for DNS changes.'),
            timeout=10)


    def revert_dns(self):
        """Clear the custom DNS setting for all devices and force them to use
        DHCP to pull the network's real settings again.
        """
        try:
            # Follow resolv.conf symlink.
            resolv = os.path.realpath(constants.RESOLV_CONF_FILE)
            # Grab path to the real file, do following work in that directory.
            resolv_dir = os.path.dirname(resolv)
            resolv_bak = os.path.join(resolv_dir, self._resolv_bak_file)
            os.chmod(resolv_dir, self._resolv_dir_mode)
            os.rename(resolv_bak, resolv)

            utils.poll_for_condition(
                lambda: self.__attempt_resolve('www.google.com.',
                                               '127.0.0.1',
                                               expected=False),
                utils.TimeoutError('Timed out waiting to revert DNS.  '
                                   'resolv.conf contents are: ' +
                                   utils.read_one_line(resolv)),
                timeout=10)
        finally:
            # Set captive portal checking to whatever it was at the start.
            self._flim.SetCheckPortalList(self.check_portal_list)


    def start_authserver(self):
        """Spin up a local mock of the Google Accounts server, then spin up
        a local fake DNS server and tell the networking stack to use it.  This
        will trick Chrome into talking to our mock when we login.
        Subclasses can override this method to change this behavior.
        """
        self._authServer = auth_server.GoogleAuthServer()
        self._authServer.run()
        self.use_local_dns()


    def stop_authserver(self):
        """Tears down fake dns and fake Google Accounts server.  If your
        subclass does not create these objects, you will want to override this
        method as well.
        """
        if hasattr(self, '_authServer'):
            self.revert_dns()
            self._authServer.stop()
            self._dnsServer.stop()


    def start_chrome_event_tracing(self):
        """Start tracing events of a chrome process being created or receiving a
        signal.
        """
        try:
            # Clear the trace buffer.
            utils.open_write_close(self._ftrace_trace_file, '')

            # Trace only chrome process creation events, which we may later use
            # to determine if a chrome process is killed by its parent.
            utils.open_write_close(
                self._ftrace_process_fork_event_filter_file,
                'child_comm==chrome')
            # Trace only chrome processes receiving any signal except for
            # the uninteresting SIGPROF (sig 27 on x86 and arm).
            utils.open_write_close(
                self._ftrace_signal_generate_event_filter_file,
                'comm==chrome && sig!=27')

            # Enable the process_fork event tracing.
            utils.open_write_close(
                self._ftrace_process_fork_event_enable_file, '1')
            # Enable the signal_generate event tracing.
            utils.open_write_close(
                self._ftrace_signal_generate_event_enable_file, '1')
        except IOError as err:
            logging.warning('Failed to start chrome signal tracing: %s', err)


    def stop_chrome_event_tracing(self):
        """Stop tracing events of a chrome process being created or receiving a
        signal.
        """
        try:
            # Disable the process_fork event tracing.
            utils.open_write_close(
                self._ftrace_process_fork_event_enable_file, '0')
            # Disable the signal_generate event tracing.
            utils.open_write_close(
                self._ftrace_signal_generate_event_enable_file, '0')

            # Clear the process_fork event filter.
            utils.open_write_close(
                self._ftrace_process_fork_event_filter_file, '0')
            # Clear the signal_generate event filter.
            utils.open_write_close(
                self._ftrace_signal_generate_event_filter_file, '0')

            # Dump the trace buffer to a log file.
            trace_file = os.path.join(self.resultsdir, 'chrome_event_trace')
            trace_data = utils.read_file(self._ftrace_trace_file)
            utils.open_write_close(trace_file, trace_data)
        except IOError as err:
            logging.warning('Failed to stop chrome signal tracing: %s', err)


    def start_tcpdump(self, iface):
        """Start tcpdump process, if not running already."""
        if not hasattr(self, '_tcpdump'):
            self._tcpdump = subprocess.Popen(
                ['tcpdump', '-i', iface, '-vv'], stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT)


    def stop_tcpdump(self, fname_prefix):
        """Stop tcpdump process and save output to a new file."""
        if hasattr(self, '_tcpdump'):
            self._tcpdump.terminate()
            # Save output to a new file
            next_index = len(glob.glob(
                os.path.join(self.resultsdir, '%s-*' % fname_prefix)))
            tcpdump_file = os.path.join(
                self.resultsdir, '%s-%d' % (fname_prefix, next_index))
            logging.info('Saving tcpdump output to %s' % tcpdump_file)
            utils.open_write_close(tcpdump_file, self._tcpdump.communicate()[0])
            del self._tcpdump


    def __log_all_processes(self, fname_prefix):
        """Log all processes to a file.

        Args:
            fname_prefix: Prefix of the log file.
        """
        try:
            next_index = len(glob.glob(
                os.path.join(self.resultsdir, '%s-*' % fname_prefix)))
            log_file = os.path.join(
                self.resultsdir, '%s-%d' % (fname_prefix, next_index))
            utils.open_write_close(log_file, utils.system_output('ps -eF'))
        except (error.CmdError, IOError, OSError) as err:
            logging.warning('Failed to log all processes: %s', err)


    def __perform_ui_diagnostics(self):
        """Save diagnostic logs about UI.

        This includes the output of:
          $ initctl status ui
          $ ps auxwww
        """
        output_file = os.path.join(self.resultsdir, 'ui_diagnostics.txt')
        with open(output_file, 'w') as output_fd:
            print >> output_fd, time.asctime(), '\n'
            cmd = 'initctl status ui'
            print >> output_fd, '$ %s' % cmd
            print >> output_fd, utils.system_output(cmd), '\n'
            cmd = 'ps auxwww'
            print >> output_fd, '$ %s' % cmd
            print >> output_fd, utils.system_output(cmd), '\n'
        logging.info('Saved UI diagnostics to %s' % output_file)


    def __generate_coredumps(self, names):
        """Generate core dump files in results dir for given processes.

        Note that the coredumps are forced via SIGBUS and the processes will be
        terminated. Ideally we should use gdb gcore to create dumps
        non-intrusively. However, the current dumps generated by gcore could not
        be properly read back by gdb, i.e. no reasonable symbolized stack could
        be generated.

        Args:
            names: A list of process names that need to be dumped.
        """

        # Get all pids of named processes.
        pids = []
        for name in names:
            # Get pids of given name, slice [1:] to skip ps's first line 'PID'
            pids = pids + [ pid.strip() for pid in utils.system_output(
                'ps -C %s -o pid' % name).splitlines()[1:]]
        logging.info('Will force core dumps for the following pid: %s' %
            ' '.join(pids))

        # Stop all processes so that forcing dump would change their state.
        for pid in pids:
            utils.system('kill -STOP %s' % pid)

        # Force core dump.
        for pid in pids:
            utils.system('kill -BUS %s' % pid)

        # Resume to let the core dump finish.
        for pid in reversed(pids):
            utils.system('kill -CONT %s' % pid)


    def initialize(self, creds=None, is_creating_owner=False,
                   extra_chrome_flags=[], subtract_extra_chrome_flags=[]):
        """Overridden from test.initialize() to log out and (maybe) log in.

        If self.auto_login is True, this will automatically log in using the
        credentials specified by 'creds' at startup, otherwise login will not
        happen.

        Regardless of the state of self.auto_login, the self.username and
        self.password properties will be set to the credentials specified
        by 'creds'.

        Authentication is not performed against live servers.  Instead, we spin
        up a local DNS server that will lie and say that all sites resolve to
        127.0.0.1.  We use DBus to tell flimflam to use this DNS server to
        resolve addresses.  We then spin up a local httpd that will respond
        to queries at the Google Accounts endpoints.  We clear the DNS setting
        and tear down these servers in cleanup().

        Args:
            creds: String specifying the credentials for this test case.  Can
                be a named set of credentials as defined by
                constants.CREDENTIALS, or a 'username:password' pair.
                Defaults to None -- browse without signing-in.
            is_creating_owner: If the test case is creating a new device owner.
            extra_chrome_flags: Extra chrome flags to pass to chrome, if any.
            subtract_extra_chrome_flags: Remove default flags passed to chrome
                by pyauto, if any.
        """
        # Mark /var/log/messages now; we'll run through all subsequent
        # log messages at the end of the test and log info about processes that
        # crashed.
        self._log_reader = cros_logging.LogReader()
        self._log_reader.set_start_by_current()

        self.__connect_to_flimflam()

        if creds:
            self.start_authserver()

        # Run tcpdump on 'lo' interface to investigate network
        # issues in the lab during login.
        self.start_tcpdump(iface='lo')

        # Log all processes so that we can correlate PIDs to processes in
        # the chrome signal trace.
        self.__log_all_processes('processes--before-tracing')

        # Start event tracing related to chrome processes.
        self.start_chrome_event_tracing()

        # We yearn for Chrome coredumps...
        open(constants.CHROME_CORE_MAGIC_FILE, 'w').close()

        # The UI must be taken down to ensure that no stale state persists.
        cros_ui.stop()
        (self.username, self.password) = self.__resolve_creds(creds)
        # Ensure there's no stale cryptohome from previous tests.
        try:
            cryptohome.remove_vault(self.username)
        except cryptohome.ChromiumOSError as err:
            logging.error(err)

        # Fake ownership unless the test is explicitly testing owner creation.
        if not is_creating_owner:
            logging.info('Faking ownership...')
            cros_ui.fake_ownership()
            self.fake_owner = True
        else:
            logging.info('Erasing stale owner state.')
            ownership.clear_ownership()
            self.fake_owner = False

        try:
            cros_ui.start()
        except:
            self.__perform_ui_diagnostics()
            self.__generate_coredumps(['chrome'])
            raise

        # Save name of the last chrome log before our test started.
        log_files = glob.glob(constants.CHROME_LOG_DIR + '/chrome_*')
        self._last_chrome_log = max(log_files) if log_files else ''

        pyauto_test.PyAutoTest.initialize(
            self, auto_login=False,
            extra_chrome_flags=extra_chrome_flags,
            subtract_extra_chrome_flags=subtract_extra_chrome_flags)
        if self.auto_login:
            self.login(self.username, self.password)
            if is_creating_owner:
                login.wait_for_ownership()


    def __resolve_creds(self, creds):
        """Map credential identifier to username, password and type.
        Args:
          creds: credential identifier to resolve.

        Returns:
          A (username, password) tuple.
        """
        if not creds:
            return [None, None]  # Browse without signing-in.
        if creds[0] == '$':
            if creds not in constants.CREDENTIALS:
                raise error.TestFail('Unknown credentials: %s' % creds)

            (name, passwd) = constants.CREDENTIALS[creds]
            return [cryptohome.canonicalize(name), passwd]

        (name, passwd) = creds.split(':')
        return [cryptohome.canonicalize(name), passwd]


    def take_screenshot(self, fname_prefix):
      """Take screenshot and save to a new file in the results dir.

      Args:
        fname_prefix: prefix for the output fname
      """
      next_index = len(glob.glob(
          os.path.join(self.resultsdir, '%s-*.png' % fname_prefix)))
      screenshot_file = os.path.join(
          self.resultsdir, '%s-%d.png' % (fname_prefix, next_index))
      logging.info('Saving screenshot to %s.' % screenshot_file)
      utils.system('DISPLAY=:0.0 XAUTHORITY=/home/chronos/.Xauthority '
                   '/usr/local/bin/import -window root %s' % screenshot_file)


    def login(self, username=None, password=None):
        """Log in with a set of credentials.

        This method is called from UITest.initialize(), so you won't need it
        unless your testcase has cause to log in multiple times.  This
        DOES NOT affect self.username or self.password.

        If username and self.username are not defined, logs in as guest.

        Forces a log out if already logged in.
        Blocks until login is complete.

        TODO(nirnimesh): Does NOT work with webui login
                         crosbug.com/18271

        Args:
            username: username to log in as, defaults to self.username.
            password: password to log in with, defaults to self.password.

        Raises:
            error.TestError, if login has an error
        """
        if self.logged_in():
            self.logout()

        uname = username or self.username
        passwd = password or self.password

        try:
            if uname:  # Regular login
                login_error = self.pyauto.Login(username=uname,
                                                password=passwd)
                if login_error:
                    raise error.TestError(
                        'Error during login (%s, %s): %s.' % (
                        uname, passwd, login_error))
                logging.info('Logged in as %s.' % uname)
            else:  # Login as guest
                self.pyauto.LoginAsGuest()
                logging.info('Logged in as guest.')
        except:
            self.take_screenshot(fname_prefix='login-fail-screenshot')
            raise
        finally:
            self.stop_tcpdump(fname_prefix='tcpdump-lo--till-login')

        if not self.logged_in():
            raise error.TestError('Not logged in')


    def logged_in(self):
        return self.pyauto.GetLoginInfo()['is_logged_in']


    def logout(self):
        """Log out.

        This method is called from UITest.cleanup(), so you won't need it
        unless your testcase needs to test functionality while logged out.
        """
        if not self.logged_in():
            return
        self._save_logs_from_cryptohome()

        try:
            cros_ui.restart(self.pyauto.Logout)
        except:
            self.__generate_coredumps(['chrome'])
            raise


    def _save_logs_from_cryptohome(self):
        """Recover dirs from cryptohome in case another test run wipes."""
        try:
            for dir in constants.CRYPTOHOME_DIRS_TO_RECOVER:
                dir_path = os.path.join(constants.CRYPTOHOME_MOUNT_PT, dir)
                if os.path.isdir(dir_path):
                    target = os.path.join(self.resultsdir,
                                          '%s-%f' % (dir, time.time()))
                    logging.debug('Saving %s to %s.', dir_path, target)
                    shutil.copytree(src=dir_path, dst=target, symlinks=True)
        except (IOError, OSError, shutil.Error) as err:
            logging.error(err)


    def validate_basic_policy(self, basic_policy):
        # Pull in protobuf definitions.
        sys.path.append(self.srcdir)
        from device_management_backend_pb2 import PolicyFetchResponse
        from device_management_backend_pb2 import PolicyData
        from chrome_device_policy_pb2 import ChromeDeviceSettingsProto
        from chrome_device_policy_pb2 import UserWhitelistProto

        response_proto = PolicyFetchResponse()
        response_proto.ParseFromString(basic_policy)
        ownership.assert_has_policy_data(response_proto)

        poldata = PolicyData()
        poldata.ParseFromString(response_proto.policy_data)
        ownership.assert_has_device_settings(poldata)
        ownership.assert_username(poldata, self.username)

        polval = ChromeDeviceSettingsProto()
        polval.ParseFromString(poldata.policy_value)
        ownership.assert_new_users(polval, True)
        ownership.assert_users_on_whitelist(polval, (self.username,))


    def __log_crashed_processes(self, processes):
        """Runs through the log watched by |watcher| to see if a crash was
        reported for any process names listed in |processes|. SIGABRT crashes in
        chrome or supplied-chrome during ui restart are ignored.
        """
        ui_restart_begin_regex = re.compile(cros_ui.UI_RESTART_ATTEMPT_MSG)
        crash_regex = re.compile(
            'Received crash notification for ([-\w]+).+ (sig \d+)')
        ui_restart_end_regex = re.compile(cros_ui.UI_RESTART_COMPLETE_MSG)

        in_restart = False
        for line in self._log_reader.get_logs().splitlines():
            if ui_restart_begin_regex.search(line):
                in_restart = True
            elif ui_restart_end_regex.search(line):
                in_restart = False
            else:
                match = crash_regex.search(line)
                if (match and not match.group(1) in processes and
                    not (in_restart and
                         (match.group(1) == constants.BROWSER or
                          match.group(1) == 'supplied_chrome') and
                         match.group(2) == 'sig 6')):
                    self.job.record('INFO', self.tagged_testname,
                                    line[match.start():])


    def cleanup(self):
        """Overridden from pyauto_test.cleanup() to log out and restart
           session_manager when the test is complete.
        """
        try:
            # Save all chrome logs created during the test.
            try:
                for fullpath in glob.glob(
                    constants.CHROME_LOG_DIR + '/chrome_*'):
                    if os.path.isfile(fullpath) and \
                        not os.path.islink(fullpath) and \
                        fullpath > self._last_chrome_log:  # ignore old logs
                        shutil.copy2(fullpath, self.resultsdir)

            except (IOError, OSError) as err:
                logging.error(err)

            self._save_logs_from_cryptohome()
            pyauto_test.PyAutoTest.cleanup(self)

            if os.path.isfile(constants.CRYPTOHOMED_LOG):
                try:
                    base = os.path.basename(constants.CRYPTOHOMED_LOG)
                    shutil.copy(constants.CRYPTOHOMED_LOG,
                                os.path.join(self.resultsdir, base))
                except (IOError, OSError) as err:
                    logging.error(err)

            if self.fake_owner:
                logging.info('Erasing fake owner state.')
                ownership.clear_ownership()

            self.__log_crashed_processes(self.crash_blacklist)

            if os.path.isfile(constants.CHROME_CORE_MAGIC_FILE):
                os.unlink(constants.CHROME_CORE_MAGIC_FILE)
        finally:
            self.stop_chrome_event_tracing()
            self.__log_all_processes('processes--after-tracing')
            self.stop_tcpdump(fname_prefix='tcpdump-lo--till-end')
            self.stop_authserver()


    def get_auth_endpoint_misses(self):
        if hasattr(self, '_authServer'):
            return self._authServer.get_endpoint_misses()
        else:
            return {}
