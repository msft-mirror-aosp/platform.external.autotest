# Lint as: python3
# Copyright 2022 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# TODO(b/241624731) Use pydbus to get the power manager object correctly.
# For now, we use dbus to get the power manager object because power_manager
# does not give an introspection for clients to do the proper parsing.
# In the longer term, we should use pydbus.
import dbus

# Should import dbus.mainloop.glib below if we'd like to run this script
# directly by the command line.
# $ python power_suspend_delay.py
import dbus.mainloop.glib

import logging
import threading

import common
from autotest_lib.client.cros.power import suspend_pb2
from autotest_lib.client.cros.power import sys_power


try:
    from gi.repository import GObject
except ImportError:
    import gobject as GObject


class PowerSuspendDelayException(Exception):
    """The PowerSuspendDelay module Exception."""
    pass


class PowerSuspendDelay(object):
    """A power manager proxy that handles the suspend delay procedure."""

    POWER_MANAGER_PATH = '/org/chromium/PowerManager'
    POWER_MANAGER_IFACE = 'org.chromium.PowerManager'
    POWER_MANAGER_SERVICE_NAME = 'org.chromium.PowerManager'
    SUSPEND_IMMINENT_SIGNAL = "SuspendImminent";
    SUSPEND_DONE_SIGNAL = "SuspendDone"

    SUSPEND_DELAY_SECS = 5
    SUSPEND_DELAY_TIMEOUT_SECS = SUSPEND_DELAY_SECS + 3

    # There are two phases in the sys_power.do_suspend().
    # First phase: pre-suspend
    #   It may take up to the POWER_MANAGER_MAX_SUSPEND_DELAY_TIMEOUT_SECS
    #   many seconds to get suspend readiness from all processes that have
    #   registered suspend delays.
    # Seconds phase: suspend
    #   The suspend interval has to be these MIN_ACTUAL_SUSPEND_TIME_SECS
    #   many seconds to be realistic for suspending. For example, asking
    #   the system to suspend for 1 second may not be realistic.
    # This value is used for checking purpose only.
    MIN_ACTUAL_SUSPEND_TIME_SECS = 5

    WAKEUP_TIMEOUT_SECS = SUSPEND_DELAY_TIMEOUT_SECS + 10

    # src/platform2/power_manager/powerd/policy/suspend_delay_controller.h
    POWER_MANAGER_MAX_SUSPEND_DELAY_TIMEOUT_SECS = 20

    # Add this slack seconds to mainloop_max_timeout_secs for the mainloop
    # to quit.
    MAINLOOP_MAX_TIMEOUT_SLACK_SECS = 30

    WAKEUP_TYPE = (
            'UNKNOWN',
            'NOT_APPLICABLE', # last suspend failed
            'INPUT',          # resume triggered by an input device
            'OTHER'           # resume triggered by non-input devices e.g. RTC
    )

    def __init__(self, suspend_delay_secs=SUSPEND_DELAY_SECS,
                 suspend_delay_timeout_secs=SUSPEND_DELAY_TIMEOUT_SECS,
                 wakeup_timeout_secs=WAKEUP_TIMEOUT_SECS):
        """Constructor of PowerSuspendDelay

        @param suspend_delay_secs: the suspend delay in seconds.
                When receiving the SuspendImminent signal, this object will
                idly wait for suspend_delay_secs before calling
                HandleSuspendReadiness to notify the power manager that this
                object is ready to suspend.
        @param suspend_delay_timeout_secs: the suspend delay timeout in seconds.
                This object notifies the power manager that if the object does
                not call HandleSuspendReadiness, the power manager can start
                suspending after suspend_delay_timeout_secs.
        @param wakeup_timeout_secs: the wakeup_timeout in seconds.
                This is the time interval between the time instant of calling
                sys_power.do_suspend() and the time instant that the device has
                to wake up. This time interval includes the 1st pre-suspend
                phase and the 2nd suspend phase.
        """
        self._assert_less_equal(
                suspend_delay_secs, suspend_delay_timeout_secs,
                "suspend_delay_secs > suspend_delay_timeout_secs")

        self._assert_less_equal(suspend_delay_timeout_secs,
                self.POWER_MANAGER_MAX_SUSPEND_DELAY_TIMEOUT_SECS,
                "suspend_delay_timeout_secs too large")

        self._assert_less_equal(
                (self.POWER_MANAGER_MAX_SUSPEND_DELAY_TIMEOUT_SECS +
                 self.MIN_ACTUAL_SUSPEND_TIME_SECS),
                wakeup_timeout_secs,
                "wakeup_timeout_secs too small")

        # Sets the gobject main loop to be the event loop for DBus.
        dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
        self.bus = dbus.SystemBus()
        self.obj = self.bus.get_object(self.POWER_MANAGER_SERVICE_NAME,
                                       self.POWER_MANAGER_PATH)
        self.iface = dbus.Interface(self.obj, self.POWER_MANAGER_IFACE)

        # The mainloop should quit within mainloop_max_timeout_secs.
        # mainloop_max_timeout_secs = wakeup_timeout_secs + some slack time
        mainloop_max_timeout_secs = (wakeup_timeout_secs +
                                     self.MAINLOOP_MAX_TIMEOUT_SLACK_SECS)
        self.mainloop = GObject.MainLoop()
        self.mainloop_quit_task = GObject.timeout_add(
                mainloop_max_timeout_secs * 1000, self._mainloop_quit)

        self.suspend_delay_secs = suspend_delay_secs
        self.suspend_delay_timeout_secs = suspend_delay_timeout_secs
        self.wakeup_timeout_secs = wakeup_timeout_secs
        self.delay_id = None
        self.ready_thread = None
        self.suspend_thread = None

    @staticmethod
    def _assert_less_equal(value1, value2, err_msg):
        """Asserts that value1 <= value2.

        Raises PowerSuspendDelayException when value1 > value2.

        @param value1: the 1st value to compare
        @param value2: the 2nd value to compare
        @param err_msg: the error message of the exception if value1 > value2.

        @raises PowerSuspendDelayException
        """
        if value1 > value2:
            raise PowerSuspendDelayException(err_msg)

    # TODO(b/241624731) Use pydbus to get the power manager object correctly.
    # This method might not be needed with pydbus per Abhishek's comment.
    # It will simply return a bytearray from the api.
    @staticmethod
    def _dbus_array_to_bytes(data):
        """Converts dbus.Array of dbus.Byte to bytes.

        An example:
          input: dbus.Array([dbus.Byte(8), dbus.Byte(188), dbus.Byte(128),
                 dbus.Byte(196), dbus.Byte(25), dbus.Byte(16), dbus.Byte(216),
                 dbus.Byte(54)], signature=dbus.Signature('y'))
          output: b'\x08\xbc\x80\xc4\x19\x10\xd86'

        @param data: the dbus.Array of dbus.Byte
        """
        return bytes(int(b) for b in data)

    def register_suspend_delay(self):
        """Registers suspend delay from the power manager.

        This method registers suspend delay, and connects to two signals,
        SUSPEND_IMMINENT_SIGNAL and SUSPEND_DONE_SIGNAL.
        """
        req = suspend_pb2.RegisterSuspendDelayRequest()
        req.timeout = self.suspend_delay_timeout_secs * 1000000
        req.description = 'power_register_suspend_test'

        args = dbus.types.ByteArray(req.SerializeToString())
        output = self.iface.RegisterSuspendDelay(args)

        reply = suspend_pb2.RegisterSuspendDelayReply()
        reply.ParseFromString(self._dbus_array_to_bytes(output))
        self.delay_id = reply.delay_id

        self.iface.connect_to_signal(self.SUSPEND_IMMINENT_SIGNAL,
                                     self.handle_suspend_imminent)
        self.iface.connect_to_signal(self.SUSPEND_DONE_SIGNAL,
                                     self.handle_suspend_done)

        logging.info('RegisterSuspendDelay: delay_id %d timeout %d ms',
                     reply.delay_id, reply.min_delay_timeout_ms)

    def send_suspend_readiness(self, data):
        """Calls HandleSuspendReadiness to indicate readiness for suspend.

        @param data: the data attached in the SuspendImminent signal
        """
        info = suspend_pb2.SuspendImminent()
        info.ParseFromString(self._dbus_array_to_bytes(data))

        req = suspend_pb2.SuspendReadinessInfo()
        req.delay_id = self.delay_id
        req.suspend_id = info.suspend_id
        args = dbus.types.ByteArray(req.SerializeToString())
        self.iface.HandleSuspendReadiness(args)

        logging.info('HandleSuspendReadiness: suspend_id %d delay %d seconds',
                     info.suspend_id, self.suspend_delay_secs)

    def handle_suspend_imminent(self, data):
        """The SuspendImminent signal handler

        @param data: the data attached in the SuspendImminent signal
        """
        # Wait a suspend delay interval before sending SuspendReadiness to the
        # power manager. A client can set a larger suspend_delay_secs value
        # and check if the client activities interfere with the suspend.
        self.ready_thread = threading.Timer(self.suspend_delay_secs,
                                            self.send_suspend_readiness,
                                            [data,])
        self.ready_thread.start()

        logging.info('SuspendImminent signal')

    def handle_suspend_done(self, data):
        """The SuspendDone signal handler

        @param data: the data attached in the SuspendDone signal
        """
        info = suspend_pb2.SuspendDone()
        info.ParseFromString(self._dbus_array_to_bytes(data))
        wakeup_type = self.WAKEUP_TYPE[info.wakeup_type]

        GObject.source_remove(self.mainloop_quit_task)
        self._mainloop_quit()

        logging.info('SuspendDone signal: duration %.3f seconds wakeup_type %s',
                     info.suspend_duration / 1000000, wakeup_type)

    def unregister_suspend_delay(self):
        """Unregisters the suspend delay from the power manager."""
        req = suspend_pb2.UnregisterSuspendDelayRequest()
        req.delay_id = self.delay_id
        args = dbus.types.ByteArray(req.SerializeToString())
        self.iface.UnregisterSuspendDelay(args)

        logging.info('UnregisterSuspendDelay: delay_id %d', req.delay_id)

    def _do_sys_suspend(self, wakeup_timeout):
        """Invokes the system suspend function.

        @param wakeup_timeout: the interval time from now after which the
                               device has to suspend
        """
        logging.info('suspend started')
        sys_power.do_suspend(wakeup_timeout)
        logging.info('suspend ended')

    def start_suspend_thread(self):
        """Starts a new thread to do suspend.

        This task has to be done in a thread; otherwise, the reception of
        the handle_suspend_imminent signal may be interfered.
        """
        self.suspend_thread = threading.Thread(target=self._do_sys_suspend,
                                               args=(self.wakeup_timeout_secs,))
        self.suspend_thread.start()

    def _mainloop_quit(self):
        """Quits the mainloop."""
        if self.mainloop.is_running():
            self.mainloop.quit()
        return False

    def cleanup(self):
        """Cleans up the suspend delay and threads."""
        self.unregister_suspend_delay()
        if self.ready_thread:
            self.ready_thread.join()
        if self.suspend_thread:
            self.suspend_thread.join()
        logging.info('cleanup')


def suspend_delay(suspend_delay_secs, suspend_delay_timeout_secs,
                  wakeup_timeout_secs):
    """A helper function to execute the suspend delay.

    This function blocks until the suspend is completed.

    @param suspend_delay_secs: the suspend delay in seconds
    @param suspend_delay_timeout_secs: the suspend delay timeout in seconds
    @param wakeup_timeout_secs: the wakeup_timeout in seconds
    """
    power = PowerSuspendDelay(suspend_delay_secs, suspend_delay_timeout_secs,
                              wakeup_timeout_secs)
    power.register_suspend_delay()
    power.start_suspend_thread()
    power.mainloop.run()
    power.cleanup()


def start_suspend_delay_thread(suspend_delay_secs, suspend_delay_timeout_secs,
                               wakeup_timeout_secs):
    """A non-blocking helper function to execute the suspend delay.

    @param suspend_delay_secs: the suspend delay in seconds
    @param suspend_delay_timeout_secs: the suspend delay timeout in seconds
    @param wakeup_timeout_secs: the wakeup_timeout in seconds
    """
    suspend_delay_thread = threading.Thread(target=suspend_delay,
                                            args=(suspend_delay_secs,
                                                  suspend_delay_timeout_secs,
                                                  wakeup_timeout_secs))
    return suspend_delay_thread


if __name__ == '__main__':
    logging.getLogger().setLevel(logging.INFO)
    logging.basicConfig(format='%(asctime)s %(message)s')

    # An example of calling suspend_delay() in a blocking way.
    # suspend_delay(suspend_delay_secs=8,
    #               suspend_delay_timeout_secs=10,
    #               wakeup_timeout_secs=30)

    # An example of calling suspend_delay() in a non-blocking way.
    delay_thread = start_suspend_delay_thread(suspend_delay_secs=8,
                                              suspend_delay_timeout_secs=10,
                                              wakeup_timeout_secs=30)
    logging.info('suspend_delay started')
    delay_thread.start()
    delay_thread.join()
    logging.info('suspend_delay done')
