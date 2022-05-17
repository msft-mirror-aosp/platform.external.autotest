# Copyright 2022 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""A wrapper around ssh for common operations on a CrOS-based device"""
from __future__ import absolute_import
import logging
import os
import re
import shutil
import stat
import subprocess
import tempfile

import common

from autotest_lib.client.common_lib.cros.autotestChrome.util import cmd_util

# Some developers' workflow includes running the Chrome process from
# /usr/local/... instead of the default location. We have to check for both
# paths in order to support this workflow.
_CHROME_PROCESS_REGEX = [re.compile(r'^/opt/google/chrome/chrome '),
                         re.compile(r'^/usr/local/?.*/chrome/chrome ')]

_CHROME_MOUNT_NAMESPACE_PATH = "/run/namespaces/mnt_chrome"

_IGNORE_FILETYPES_FOR_MINIDUMP_PULLS = [
    '.lock',
    '.dat',
]

def GetAllCmdOutput(args, cwd=None, quiet=False):
  # GetAllCmdOutput returns bytes on Python 3. As the downstream codes are
  # expecting strings, we decode the inpout here.
  stdout, stderr = cmd_util.GetAllCmdOutput(args, cwd, quiet)
  return (stdout.decode('utf-8'), stderr.decode('utf-8'))

def _Unquote(s):
  """Removes any trailing/leading single/double quotes from a string.

  No-ops if the given object is not a string or otherwise does not have a
  .strip() method.

  Args:
    s: The string to remove quotes from.

  Returns:
    |s| with trailing/leading quotes removed.
  """
  if not hasattr(s, 'strip'):
    return s
  # Repeated to handle both "'foo'" and '"foo"'
  return s.strip("'").strip('"').strip("'")

class CrOSInterface(object):

  CROS_MINIDUMP_DIR = '/var/log/chrome/Crash Reports/'

  _DEFAULT_SSH_CONNECTION_TIMEOUT = 5

  def __init__(self, hostname=None, ssh_port=None, ssh_identity=None):
    self._hostname = hostname
    self._ssh_port = ssh_port

    # List of ports generated from GetRemotePort() that may not be in use yet.
    self._reserved_ports = []

    self._device_host_clock_offset = None
    self._master_connection_open = False
    self._disable_strict_filenames = False

    # Cached properties
    self._arch_name = None
    self._board = None
    self._device_type_name = None
    self._is_running_on_vm = None

    if self.local:
      return

    self._ssh_identity = None
    self._ssh_args = ['-o StrictHostKeyChecking=no',
                      '-o KbdInteractiveAuthentication=no',
                      '-o PreferredAuthentications=publickey',
                      '-o UserKnownHostsFile=/dev/null', '-o ControlMaster=no']

    if ssh_identity:
      self._ssh_identity = os.path.abspath(os.path.expanduser(ssh_identity))
      os.chmod(self._ssh_identity, stat.S_IREAD)

    # Since only one test will be run on a remote host at a time,
    # the control socket filename can be telemetry@hostname.
    self._ssh_control_file = '/tmp/' + 'telemetry' + '@' + self._hostname
    self.OpenConnection()

  @property
  def local(self):
    return not self._hostname

  def OpenConnection(self):
    """Opens a master connection to the device."""
    if self._master_connection_open or self.local:
      return
    # Establish master SSH connection using ControlPersist.
    with open(os.devnull, 'w') as devnull:
      subprocess.call(
          self.FormSSHCommandLine(['-M', '-o ControlPersist=yes']),
          stdin=devnull,
          stdout=devnull,
          stderr=devnull)
    self._master_connection_open = True

  def FormSSHCommandLine(self, args, extra_ssh_args=None, port_forward=False,
                         connect_timeout=None):
    """Constructs a subprocess-suitable command line for `ssh'.
    """
    if self.local:
      # We run the command through the shell locally for consistency with
      # how commands are run through SSH (crbug.com/239161). This work
      # around will be unnecessary once we implement a persistent SSH
      # connection to run remote commands (crbug.com/239607).
      return ['sh', '-c', " ".join(args)]

    full_args = ['ssh', '-o ForwardX11=no', '-o ForwardX11Trusted=no', '-n']
    if connect_timeout:
      full_args += ['-o ConnectTimeout=%d' % connect_timeout]
    else:
      full_args += [
          '-o ConnectTimeout=%d' % self._DEFAULT_SSH_CONNECTION_TIMEOUT]
    # As remote port forwarding might conflict with the control socket
    # sharing, skip the control socket args if it is for remote port forwarding.
    if not port_forward:
      full_args += ['-S', self._ssh_control_file]
    full_args += self._ssh_args
    if self._ssh_identity is not None:
      full_args.extend(['-i', self._ssh_identity])
    if extra_ssh_args:
      full_args.extend(extra_ssh_args)
    full_args.append('root@%s' % self._hostname)
    full_args.append('-p%d' % self._ssh_port)
    full_args.extend(args)
    return full_args

  def _RemoveSSHWarnings(self, to_clean):
    """Removes specific ssh warning lines from a string.

    Args:
      to_clean: A string that may be containing multiple lines.

    Returns:
      A copy of to_clean with all the Warning lines removed.
    """
    # Remove the Warning about connecting to a new host for the first time.
    return re.sub(
        r'Warning: Permanently added [^\n]* to the list of known hosts.\s\n',
        '', to_clean)

  def RunCmdOnDevice(self, args, cwd=None, quiet=False, connect_timeout=None,
                     port_forward=False):
    stdout, stderr = GetAllCmdOutput(
        self.FormSSHCommandLine(
            args, connect_timeout=connect_timeout, port_forward=port_forward),
        cwd=cwd,
        quiet=quiet)
    # The initial login will add the host to the hosts file but will also print
    # a warning to stderr that we need to remove.
    stderr = self._RemoveSSHWarnings(stderr)
    return stdout, stderr

  def PushFile(self, filename, remote_filename):
    if self.local:
      args = ['cp', '-r', filename, remote_filename]
      _, stderr = GetAllCmdOutput(args, quiet=True)
      if stderr != '':
        raise OSError('No such file or directory %s' % stderr)
      return

    args = self._FormSCPToRemote(
        os.path.abspath(filename),
        remote_filename,
        extra_scp_args=['-r'])

    _, stderr = GetAllCmdOutput(args, quiet=True)
    stderr = self._RemoveSSHWarnings(stderr)
    if stderr != '':
      raise OSError('No such file or directory %s' % stderr)

  def GetFile(self, filename, destfile=None):
    """Copies a remote file |filename| on the device to a local file |destfile|.

    Args:
      filename: The name of the remote source file.
      destfile: The name of the file to copy to, and if it is not specified
        then it is the basename of the source file.

    """
    logging.debug("GetFile(%s, %s)" % (filename, destfile))
    if self.local:
      filename = _Unquote(filename)
      destfile = _Unquote(destfile)
      if destfile is not None and destfile != filename:
        shutil.copyfile(filename, destfile)
        return
      else:
        raise OSError('No such file or directory %s' % filename)

    if destfile is None:
      destfile = os.path.basename(filename)
    destfile = os.path.abspath(destfile)
    extra_args = ['-T'] if self._disable_strict_filenames else []
    args = self._FormSCPFromRemote(
        filename, destfile, extra_scp_args=extra_args)

    _, stderr = GetAllCmdOutput(args, quiet=True)
    stderr = self._RemoveSSHWarnings(stderr)
    # This is a workaround for a bug in SCP that was added ~January 2019, where
    # strict filename checking can erroneously reject valid filenames. Passing
    # -T goes back to the older behavior, but scp doesn't have a good way of
    # checking the version, so we can't pass -T the first time based on that.
    # Instead, try without -T and retry with -T if the error message is
    # appropriate. See
    # https://unix.stackexchange.com/questions/499958/why-does-scps-strict-filename-checking-reject-quoted-last-component-but-not-oth
    # for more information.
    if ('filename does not match request' in stderr and
        not self._disable_strict_filenames):
      self._disable_strict_filenames = True
      args = self._FormSCPFromRemote(filename, destfile, extra_scp_args=['-T'])
      _, stderr = GetAllCmdOutput(args, quiet=True)
      stderr = self._RemoveSSHWarnings(stderr)
    if stderr != '':
      raise OSError('No such file or directory %s' % stderr)

  def GetFileContents(self, filename):
    """Get the contents of a file on the device.

    Args:
      filename: The name of the file on the device.

    Returns:
      A string containing the contents of the file.
    """
    with tempfile.NamedTemporaryFile() as t:
      self.GetFile(filename, t.name)
      with open(t.name, 'r') as f2:
        res = f2.read()
        logging.debug("GetFileContents(%s)->%s" % (filename, res))
        return res

  def HasSystemd(self):
    """Return True or False to indicate if systemd is used.

    Note: This function checks to see if the 'systemctl' utilitary
    is installed. This is only installed along with the systemd daemon.
    """
    _, stderr = self.RunCmdOnDevice(['systemctl'], quiet=True)
    return stderr == ''

  def ListProcesses(self):
    """Returns (pid, cmd, ppid, state) of all processes on the device."""
    stdout, stderr = self.RunCmdOnDevice(
        [
            '/bin/ps', '--no-headers', '-A', '-o', 'pid,ppid,args:4096,state'
        ],
        quiet=True)
    assert stderr == '', stderr
    procs = []
    for l in stdout.split('\n'):
      if l == '':
        continue
      m = re.match(r'^\s*(\d+)\s+(\d+)\s+(.+)\s+(.+)', l, re.DOTALL)
      assert m
      procs.append((int(m.group(1)), m.group(3).rstrip(), int(m.group(2)),
                    m.group(4)))
    logging.debug("ListProcesses(<predicate>)->[%i processes]" % len(procs))
    return procs

  def _GetSessionManagerPid(self, procs):
    """Returns the pid of the session_manager process, given the list of
    processes."""
    for pid, process, _, _ in procs:
      argv = process.split()
      if argv and os.path.basename(argv[0]) == 'session_manager':
        return pid
    return None

  def GetChromeProcess(self):
    """Locates the the main chrome browser process.

    Chrome on cros is usually in /opt/google/chrome, but could be in
    /usr/local/ for developer workflows - debug chrome is too large to fit on
    rootfs.

    Chrome spawns multiple processes for renderers. pids wrap around after they
    are exhausted so looking for the smallest pid is not always correct. We
    locate the session_manager's pid, and look for the chrome process that's an
    immediate child. This is the main browser process.
    """
    procs = self.ListProcesses()
    session_manager_pid = self._GetSessionManagerPid(procs)
    if not session_manager_pid:
      return None

    # Find the chrome process that is the child of the session_manager.
    for pid, process, ppid, _ in procs:
      if ppid != session_manager_pid:
        continue
      for regex in _CHROME_PROCESS_REGEX:
        path_match = re.match(regex, process)
        if path_match is not None:
          return {'pid': pid, 'path': path_match.group(), 'args': process}
    return None

  def GetChromePid(self):
    """Returns pid of main chrome browser process."""
    result = self.GetChromeProcess()
    if result and 'pid' in result:
      return result['pid']
    return None

  def RmRF(self, filename):
    logging.debug("rm -rf %s" % filename)
    self.RunCmdOnDevice(['rm', '-rf', filename], quiet=True)

  def Chown(self, filename):
    self.RunCmdOnDevice(['chown', '-R', 'chronos:chronos', filename])

  def IsServiceRunning(self, service_name):
    """Check with the init daemon if the given service is running."""
    if self.HasSystemd():
      # Querying for the pid of the service will return 'MainPID=0' if
      # the service is not running.
      stdout, stderr = self.RunCmdOnDevice(
          ['systemctl', 'show', '-p', 'MainPID', service_name], quiet=True)
      running = int(stdout.split('=')[1]) != 0
    else:
      stdout, stderr = self.RunCmdOnDevice(['status', service_name], quiet=True)
      running = 'running, process' in stdout
    assert stderr == '', stderr
    logging.debug("IsServiceRunning(%s)->%s" % (service_name, running))
    return running

  def _GetMountSourceAndTarget(self, path, ns=None):
    def _RunAndSplit(cmd):
      cmd_out, _ = self.RunCmdOnDevice(cmd)
      return cmd_out.split('\n')

    cmd = ['/bin/df', '--output=source,target', path]
    df_ary = []
    if ns:
      ns_cmd = ['nsenter', '--mount=%s' % ns]
      ns_cmd.extend(cmd)
      # Try running 'df' in the non-root mount namespace.
      df_ary = _RunAndSplit(ns_cmd)

    if len(df_ary) < 3:
      df_ary = _RunAndSplit(cmd)

    # 3 lines for title, mount info, and empty line:
    # # df --output=source,target `cryptohome-path user '$guest'`
    # Filesystem     Mounted on\n
    # /dev/loop6     /home/user/a5715c406109752ce7c31dad219c85c4e812728f\n
    #
    if len(df_ary) == 3:
      line_ary = df_ary[1].split()
      return line_ary if len(line_ary) == 2 else None
    return None

  def EphemeralCryptohomePath(self, user):
    """Returns the ephemeral cryptohome mount poing for |user|."""
    profile_path = self.CryptohomePath(user)
    # Get user hash as last element of cryptohome path last.
    return os.path.join('/run/cryptohome/ephemeral_mount/',
                        os.path.basename(profile_path))

  def CryptohomePath(self, user):
    """Returns the cryptohome mount point for |user|."""
    stdout, stderr = self.RunCmdOnDevice(['cryptohome-path', 'user', "'%s'" %
                                          user])
    if stderr != '':
      raise OSError('cryptohome-path failed: %s' % stderr)
    return stdout.rstrip()

  def IsCryptohomeMounted(self, username, is_guest):
    """Returns True iff |user|'s cryptohome is mounted."""
    # Check whether it's ephemeral mount from a loop device.
    profile_ephemeral_path = self.EphemeralCryptohomePath(username)
    ns = None
    if is_guest:
      ns = _CHROME_MOUNT_NAMESPACE_PATH
    ephemeral_mount_info = self._GetMountSourceAndTarget(profile_ephemeral_path,
                                                         ns)
    if ephemeral_mount_info:
      return (ephemeral_mount_info[0].startswith('/dev/loop') and
              ephemeral_mount_info[1] == profile_ephemeral_path)

    profile_path = self.CryptohomePath(username)
    mount_info = self._GetMountSourceAndTarget(profile_path)
    if mount_info:
      # Checks if the filesytem at |profile_path| is mounted on |profile_path|
      # itself. Before mounting cryptohome, it shows an upper directory (/home).
      is_guestfs = (mount_info[0] == 'guestfs')
      return is_guestfs == is_guest and mount_info[1] == profile_path
    return False

  def GetArchName(self):
    if self._arch_name is None:
      self._arch_name = self.RunCmdOnDevice(['uname', '-m'])[0].rstrip()
    return self._arch_name

  def RestartUI(self, clear_enterprise_policy):
    logging.info('(Re)starting the ui (logs the user out)')
    start_cmd = ['start', 'ui']
    restart_cmd = ['restart', 'ui']
    stop_cmd = ['stop', 'ui']
    if self.HasSystemd():
      start_cmd.insert(0, 'systemctl')
      restart_cmd.insert(0, 'systemctl')
      stop_cmd.insert(0, 'systemctl')
    if clear_enterprise_policy:
      self.RunCmdOnDevice(stop_cmd)
      # TODO(b/187793661) Delete /var/lib/whitelist once migration is finished.
      self.RmRF('/var/lib/whitelist/*')
      self.RmRF('/var/lib/devicesettings/*')
      self.RmRF(r'/home/chronos/Local\ State')

    if self.IsServiceRunning('ui'):
      self.RunCmdOnDevice(restart_cmd)
    else:
      self.RunCmdOnDevice(start_cmd)

  def CloseConnection(self):
    if not self.local and self._master_connection_open:
      with open(os.devnull, 'w') as devnull:
        subprocess.call(
            self.FormSSHCommandLine(['-O', 'exit', self._hostname]),
            stdout=devnull,
            stderr=devnull)
      self._master_connection_open = False