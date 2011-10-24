# Copyright (c) 2011 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import dbus, dbus.mainloop.glib, glib, gobject
import logging, os, pty, re, subprocess, traceback

from autotest_lib.client.bin import test, utils
from autotest_lib.client.common_lib import error
from autotest_lib.client.cros import network

from autotest_lib.client.cros import flimflam_test_path
import flimflam
import mm

# Preconditions for starting
START_DEVICE_PRESENT = 'start_device_present'
START_UDEVADM_RUNNING = 'start_udevadm_running'

# ModemManager service enters, leaves bus
MM_APPEARED = 'modem_manager_appeared'
MM_DISAPPEARED = 'modem_manager_disappeared'

# userlevel UDEV sees the modem come and go
MODEM_APPEARED = 'modem_appeared'
MODEM_DISAPPEARED = 'modem_disappeared'

class TestEventLoop(object):
  """Common tools for running glib event loops."""
  def __init__(self):
    # The glib mainloop sinks exceptions thrown by event handlers, so we
    # provide a wrapper that saves the exceptions so the event loop can
    # re-raise them.

    # TODO(rochberg): The rethrown exceptions come with the stack of the
    # rethrow point, not the original exceptions.  Fix.
    self.to_raise = None

    # Autotest won't continue until our children are dead.  Keep track
    # of them
    self.to_kill = []

  def ExceptionWrapper(self, f):
    """Returns a wrapper that calls f and saves exceptions for re-raising."""
    def to_return(*args, **kwargs):
      try:
        return f(*args, **kwargs)
      except Exception, e:
        logging.info('Caught: ' + traceback.format_exc())
        self.to_raise = e
        return True
    return to_return

  def Popen(self, *args, **kwargs):
    """Builds a supbrocess.Popen, saves a copy for later kill()ing."""
    to_return = subprocess.Popen(*args, **kwargs)
    self.to_kill.append(to_return)
    return to_return

  def KillSubprocesses(self):
    for victim in self.to_kill:
      victim.kill()

class GobiDesyncEventLoop(TestEventLoop):
  def __init__(self, bus):
    super(GobiDesyncEventLoop, self).__init__()
    self.bus = bus
    self.dbus_signal_receivers = []

    # Start conditions; once these have been met, call StartTest.
    # This makes sure that cromo and udevadm are ready to use
    self.remaining_start_conditions = set([START_DEVICE_PRESENT,
                                           START_UDEVADM_RUNNING])

    # We want to see all of these events before we're done
    self.remaining_events = set([MM_APPEARED, MM_DISAPPEARED,
                                 MODEM_APPEARED, MODEM_DISAPPEARED, ])


    # udevadm monitor output for user-level notifications of device
    # add and remove
    # UDEV  [1296763045.687859] add      /devices/virtual/QCQMI/qcqmi0 (QCQMI)
    self.udev_qcqmi = re.compile(
        r'UDEV.*\s(?P<action>\w+).*/QCQMI/qcqmi')

  def NameOwnerChanged(self, name, old, new):
    if name != 'org.chromium.ModemManager':
      return
    if not new:
      self.remaining_events.remove(MM_DISAPPEARED)
    elif not old:
      if MM_DISAPPEARED in self.remaining_events:
        raise Exception('Saw cromo appear before it disappeared')
      self.remaining_events.remove(MM_APPEARED)
    return True

  def ModemAdded(self, path):
    """Clock the StartIfReady() state machine when we see a modem added."""
    logging.info('Modem %s added' % path)
    self.StartIfReady()         # Checks to see if the modem is present

  def TimedOut(self):
    raise Exception('Timed out: still waiting for: '
                    + str(self.remaining_events))

  def UdevOutputReceived(self, source, condition):
    if condition & glib.IO_IN:
      output = os.read(source.fileno(), 65536)

      # We don't want to start the test until udevadm is running
      if 'KERNEL - the kernel uevent' in output:
        self.StartIfReady(START_UDEVADM_RUNNING)

      for line in output.split('\r\n'):
        logging.info(line)
        match = self.udev_qcqmi.search(line)
        if not match:
          continue
        action = match.group('action')
        logging.info('Action:[%s]' % action)
        if action == 'add':
          if MM_DISAPPEARED in self.remaining_events:
            raise Exception('Saw modem appear before it disappeared')
          self.remaining_events.remove(MODEM_APPEARED)

        elif action == 'remove':
          self.remaining_events.remove(MODEM_DISAPPEARED)
    return True


  def StartIfReady(self, condition_to_remove=None):
    """Call StartTest when remaining_start_conditions have been met."""
    if condition_to_remove:
      self.remaining_start_conditions.discard(condition_to_remove)

    try:
      if (START_DEVICE_PRESENT in self.remaining_start_conditions and
          mm.PickOneModem('Gobi')):
        self.remaining_start_conditions.discard(START_DEVICE_PRESENT)
    except org.freedesktop.DBus.Error.NoReply:
      pass

    if self.remaining_start_conditions:
      logging.info('Not starting until: %s' % self.remaining_start_conditions)
    else:
      logging.info('Preconditions satisfied')
      self.StartTest()
      self.remaining_start_conditions = ['dummy entry so we do not start twice']

  def RegisterDbusSignal(self, *args, **kwargs):
    """Register signal receiver with dbus and our cleanup list."""
    self.dbus_signal_receivers.append(
        self.bus.add_signal_receiver(*args, **kwargs))

  def CleanupDbusSignalReceivers(self):
    for signal_match in self.dbus_signal_receivers:
      signal_match.remove()

  def RegisterForDbusSignals(self):
    # Watch cromo leave the bus when it terminates and return when it
    # is restarted
    self.RegisterDbusSignal(self.ExceptionWrapper(self.NameOwnerChanged),
                            bus_name='org.freedesktop.DBus',
                            signal_name='NameOwnerChanged')

    # Wait for cromo to report that the modem is present.
    self.RegisterDbusSignal(self.ExceptionWrapper(self.ModemAdded),
                            bus_name='org.freedesktop.DBus',
                            signal_name='DeviceAdded',
                            dbus_interface='org.freedesktop.ModemManager')

  def RegisterForUdevMonitor(self):
    # have udevadm output to a pty so it will line buffer
    (master, slave) = pty.openpty()
    monitor = self.Popen(['/sbin/udevadm', 'monitor'],
                         stdout=os.fdopen(slave),
                         bufsize=1)

    glib.io_add_watch(os.fdopen(master),
                      glib.IO_IN | glib.IO_HUP,
                      self.ExceptionWrapper(self.UdevOutputReceived))

  def Wait(self, timeout_seconds):
    self.RegisterForDbusSignals()
    self.RegisterForUdevMonitor()
    gobject.timeout_add(timeout_seconds * 1000,
                        self.ExceptionWrapper(self.TimedOut))

    # Check to see if the modem is present and remove that from the
    # start preconditions if need be
    self.StartIfReady()

    context = gobject.MainLoop().get_context()
    while self.remaining_events and not self.to_raise:
      logging.info('Waiting for: ' + str(self.remaining_events))
      context.iteration()

    network.ClearGobiModemFaultInjection()
    self.KillSubprocesses()
    self.CleanupDbusSignalReceivers()
    if self.to_raise:
      raise self.to_raise
    logging.info('Done waiting for events')


class RegularOperationTest(GobiDesyncEventLoop):
  """This covers the case where the modem makes an API call that
     returns a "we've lost sync" error that should cause a reboot."""

  def __init__(self, bus):
    super(RegularOperationTest, self).__init__(bus)

  def StartTest(self):
    modem_manager, gobi_path = mm.PickOneModem('Gobi')
    gobi = modem_manager.GobiModem(gobi_path)
    simple = modem_manager.SimpleModem(gobi_path)

    modem_manager.Modem(gobi_path).Enable(1)

    gobi.InjectFault('SdkError', 12)
    _ = simple.GetStatus()


class DataConnectTest(GobiDesyncEventLoop):
  """Test the special-case code path where we receive an error from
     StartDataSession.  If we're not also disabling at the same time,
     this should behave the same as other desync errors."""

  def __init__(self, bus):
    super(DataConnectTest, self).__init__(bus)

  def ignore(self, *args, **kwargs):
    logging.info('ignoring')
    pass

  def StartTest(self):
    modem_manager, gobi_path = mm.PickOneModem('Gobi')
    gobi = modem_manager.GobiModem(gobi_path)
    simple = modem_manager.SimpleModem(gobi_path)

    modem_manager.Modem(gobi_path).Enable(1)

    gobi.InjectFault('AsyncConnectSleepMs', 1000)
    gobi.InjectFault('ConnectFailsWithErrorSendingQmiRequest', 1)
    simple.Connect({},
                   reply_handler=self.ignore,
                   error_handler=self.ignore)

class ApiConnectTest(GobiDesyncEventLoop):
  """Test the special-case code on errors connecting to the API. """
  def __init__(self, bus):
    super(ApiConnectTest, self).__init__(bus)

  def StartTest(self):
    modem_manager, gobi_path = mm.PickOneModem('Gobi')
    gobi = modem_manager.GobiModem(gobi_path)

    modem_manager.Modem(gobi_path).Enable(0)

    saw_exception = False
    # Failures on API connect are a different code path
    gobi.InjectFault('SdkError', 1)
    try:
      modem_manager.Modem(gobi_path).Enable(1)
    except dbus.exceptions.DBusException:
      saw_exception = True
    if not saw_exception:
      raise error.TestFail('Enable returned when it should have crashed')

class EnableDisableTest():
  """Test that the Enable and Disable technology functions work."""

  def CompareModemPowerState(self, manager, path, expected_state):
    """Compare the modem manager power state of a modem to an expected state."""
    props = manager.Properties(path)
    state = props['Enabled']
    logging.info('Modem Enabled = %s' % state)
    return state == expected_state

  def CompareDevicePowerState(self, device, expected_state):
    """Compare the flimflam device power state to an expected state."""
    device_properties = device.GetProperties(utf8_strings=True);
    state = device_properties['Powered']
    logging.info('Device Enabled = %s' % state)
    return state == expected_state

  def Test(self):
    """Test that the Enable and Disable technology functions work.

       The expectation is that by using enable technology flimflam
       will change the power state of the device by requesting that
       the modem manager modem be either Enabled or Disabled.  The
       state tracked by flimflam should not change until *after* the
       modem state has changed.  Thus after Enabling or Disabling the
       technology, we wait until the flimflam device state changes,
       and then assert that the modem state has also changed, without
       having to wait again.

       Raises:
         error.TestFail - if the flimflam device or the modem manager
           modem is not in the expected state
    """
    flim = flimflam.FlimFlam()
    modem_manager, gobi_path = mm.PickOneModem('Gobi')
    props = modem_manager.Properties(gobi_path)
    interface= props['Device']
    device = flim.FindElementByPropertySubstring('Device',
                                                 'Interface', interface)

    for i in range(2):
      # Enable technology, ensure that device and modem are enabled.
      flim.EnableTechnology('cellular')
      utils.poll_for_condition(
          lambda: self.CompareDevicePowerState(device, True),
          error.TestFail('Device Failed to enter state Powered=True'))
      if not self.CompareModemPowerState(modem_manager, gobi_path, True):
        raise error.TestFail('Modem Failed to enter state Enabled')

      # Disable technology, ensure that device and modem are disabled.
      flim.DisableTechnology('cellular')
      utils.poll_for_condition(
          lambda: self.CompareDevicePowerState(device, False),
          error.TestFail('Device Failed to enter state Powered=False'))
      if not self.CompareModemPowerState(modem_manager, gobi_path, False):
        raise error.TestFail('Modem Failed to enter state Disabled')


class network_3GRecoverFromGobiDesync(test.test):
  version = 1

  def run_once(self, cycles=1, min=1, max=20):
    bus_loop = dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    self.bus = dbus.SystemBus(mainloop=bus_loop)
    try:
      logging.info('Testing failure during DataConnect')
      DataConnectTest(self.bus).Wait(60)

      logging.info('Testing failure while in regular operation')
      RegularOperationTest(self.bus).Wait(60)

      logging.info('Testing failure during device initialization')
      ApiConnectTest(self.bus).Wait(60)

      logging.info('Testing that Enable and Disable technology still work')
      EnableDisableTest().Test()
    finally:
      network.ClearGobiModemFaultInjection()
