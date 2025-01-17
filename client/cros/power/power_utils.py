# Lint as: python2, python3
# Copyright 2012 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
import glob
import json
import logging
import os
import re
import shutil
import sys
import tempfile
import time
from autotest_lib.client.bin import utils
from autotest_lib.client.bin.input.input_device import InputDevice
from autotest_lib.client.common_lib import error
from autotest_lib.client.cros import upstart
from six.moves import range


# Possible display power settings. Copied from chromeos::DisplayPowerState
# in Chrome's dbus service constants.
DISPLAY_POWER_ALL_ON = 0
DISPLAY_POWER_ALL_OFF = 1
DISPLAY_POWER_INTERNAL_OFF_EXTERNAL_ON = 2
DISPLAY_POWER_INTERNAL_ON_EXTERNAL_OFF = 3
# for bounds checking
DISPLAY_POWER_MAX = 4

# Default location of the stb_read file used with amd-stb. Useful with decode_raw_stb_data().
STB_READ_PATH = '/sys/kernel/debug/amd_pmc/stb_read'
# Output files from the amd-stb command. Useful with decode_raw_stb_data().
AMD_STB_OUTFILE_STB_REPORT = 'stb_read_stb_report.txt'
AMD_STB_OUTFILE_STB_DICT = 'stb_read_stb_dictionary.json'
AMD_STB_OUTFILE_FW_REPORT = 'stb_firmware_report.txt'

def set_fullscreen(chrome):
    """Make the current focused window fullscreen.

    Arguments:
    @param chrome: chrome instance.
    """
    # Use JS API, instead of key replay, so that we can avoid UI reactions
    # such as omnibox hover because of the internal cursor location.
    chrome.autotest_ext.EvaluateJavaScript("""
      new Promise((resolve) => chrome.windows.update(
          chrome.windows.WINDOW_ID_CURRENT,
          {state: 'fullscreen'},
          resolve));
    """, promise=True)


def get_x86_cpu_arch():
    """Identify CPU architectural type.

    Intel's processor naming conventions is a mine field of inconsistencies.
    Armed with that, this method simply tries to identify the architecture of
    systems we care about.

    TODO(tbroch) grow method to cover processors numbers outlined in:
        http://www.intel.com/content/www/us/en/processors/processor-numbers.html
        perhaps returning more information ( brand, generation, features )

    Returns:
      String, explicitly (Atom, Core, Celeron) or None
    """
    cpuinfo = utils.read_file('/proc/cpuinfo')

    if re.search(r'AMD.*[AE][269]-9[0-9][0-9][0-9].*RADEON.*R[245]', cpuinfo):
        return 'Stoney'
    if re.search(r'AMD.*Ryzen.*Radeon.*', cpuinfo):
        return 'Ryzen'
    if re.search(r'Intel.*Atom.*[NZ][2-6]', cpuinfo):
        return 'Atom'
    if re.search(r'Intel.*Celeron.*N2[89][0-9][0-9]', cpuinfo):
        return 'Celeron N2000'
    if re.search(r'Intel.*Celeron.*N3[0-9][0-9][0-9]', cpuinfo):
        return 'Celeron N3000'
    if re.search(r'Intel.*Celeron.*[0-9]{3,4}', cpuinfo):
        return 'Celeron'
    # https://ark.intel.com/products/series/94028/5th-Generation-Intel-Core-M-Processors
    # https://ark.intel.com/products/series/94025/6th-Generation-Intel-Core-m-Processors
    # https://ark.intel.com/products/series/95542/7th-Generation-Intel-Core-m-Processors
    if re.search(r'Intel.*Core.*[mM][357]-[567][Y0-9][0-9][0-9]', cpuinfo):
        return 'Core M'
    if re.search(r'Intel.*Core.*i[357]-[234][0-9][0-9][0-9]', cpuinfo):
        return 'Core'

    logging.info(cpuinfo)
    return None


def decode_raw_stb_data(out_dir, in_path=STB_READ_PATH):
    """ Run the amd-stb command to decode the contents of
    /sys/kernel/debug/amd_pmc/stb_read. Resulting decoded files are placed in
    'out_dir'.

    Args:
      out_dir: directory to store output files when amd-stb is run. Note the
        list of filenames asssigned to the AMD_STB_OUTFILE_* values in this
        file.
      in_path: stb_read data to be decoded.
    Returns:
      CmdResult from the invocations of amd-stb.
    """
    if not shutil.which('amd-stb'):
        logging.warning('Could not find amd-stb tool.')
        return None
    cmd = 'amd-stb --input=%s --output_folder=%s' % (in_path, out_dir)
    result = utils.run(cmd)
    return result


def get_stb_firmware_resume_stats(kernel_resume_time):
    """ Get additional data related to firmware resume stats using
    Smart Trace Buffer(STB) method. It invokes amd stb tool i.e
    amd-stb present in the device for better reporting of power
    resume stats.

    Args:
      kernel_resume_time: kernel resume time info measured in sec.
    Returns:
      dictionary of stb firmware info
    """
    if not shutil.which('amd-stb'):
        logging.warning('Could not find amd-stb tool in the device')
        return dict()

    in_path = '/sys/kernel/debug/amd_pmc/stb_read'
    out_path = tempfile.mkdtemp(prefix='STB')

    cmd = 'amd-stb --input=%s --output_folder=%s' % (in_path, out_path)
    output = utils.run(cmd)

    file_path = '%s/%s' % (out_path, 'stb_firmware_report.txt')
    try:
        stb_firmware_report_file = open(file_path, 'r')
        lines = stb_firmware_report_file.readlines()
    except IOError as err:
        logging.warning(output)
        logging.warning('Failed to retrieve Firmware '
                        'Resume Latency Report %s: %s', file_path, str(err))
        logging.warning('Returning without additional firmware resume stats')
        return dict()
    else:
        logging.debug("Firmware Resume Latency Report File Path: %s", file_path)
        stb_firmware_report_file.close()

    # stb_firmware_report.txt has event name and time info like below
    # S0i3 Exit(SMU part-1a)    :   0.37ms
    # Extracting event name and time info from it.

    stb_regex = r'''
        S0i3[ ]Exit            # S0i3 followed a space and then Exit
        (?P<event_name>(.*?))  # mark string as group event_name
        [ \t]+                 # spaces or tabs before the colon
        :                      # single colon :
        [ \t]+                 # spaces or tabs after the colon
        (?P<time>[0-9.]+)ms    # mark number before ms as group time
        '''
    matcher = re.compile(stb_regex, re.VERBOSE)

    stb_dict = {}
    event_count = 0
    for line in lines:
        match = matcher.match(line)
        if not match:
            continue
        event_name = match.group('event_name')
        event_count += 1
        ordnum = str(event_count).zfill(2)
        # event name "(SMU part-1a)" is converted as "SMUpart1a",
        # Output is formatted as
        # "system_resume_ms_<Ordering Number>_<Event Name>"
        # As seen in example below -
        # .../power_Resume  system_resume_ms_05_SMUpart1a  0.37
        # .../power_Resume  system_resume_ms_06_DXIO       82.790000000000006
        # .../...
        # Ordering number is added to keep the order of events in FW.
        # In power_Resume test, it does reporting in "sorted" string
        # order for event entries in result dictionary
        dispstring = re.sub('[^a-zA-Z0-9_]+', '', event_name)
        dispstring = "system_resume_ms_" + ordnum + "_" + dispstring
        time_ms = match.group('time')
        stb_dict[dispstring] = float(time_ms)

    last_event_time_sec = list(stb_dict.values())[-1]/1000
    # add entries for total fw resume time, calulated using STB and
    # also resume time calculated together from kernel and fw(using stb)
    stb_dict['seconds_system_resume_firmware_stb'] = last_event_time_sec
    stb_dict['seconds_system_resume_kernel_plus_fwstb'] = \
            kernel_resume_time + last_event_time_sec

    return stb_dict

def has_rapl_support():
    """Identify if CPU microarchitecture supports RAPL energy profile.

    TODO(harry.pan): Since Sandy Bridge, all microarchitectures have RAPL
    in various power domains. With that said, the Silvermont and Airmont
    support RAPL as well, while the ESU (Energy Status Unit of MSR 606H)
    are in different multipiler against others, hense not list by far.

    Returns:
        Boolean, True if RAPL supported, False otherwise.
    """
    rapl_set = set(["Haswell", "Haswell-E", "Broadwell", "Skylake", "Goldmont",
                    "Kaby Lake", "Comet Lake", "Ice Lake", "Tiger Lake",
                    "Tremont"])
    cpu_uarch = utils.get_intel_cpu_uarch()
    if (cpu_uarch in rapl_set):
        return True
    else:
        # The cpu_uarch here is either unlisted uarch, or family_model.
        logging.debug("%s is not in RAPL support collection", cpu_uarch)
    return False


def has_powercap_support():
    """Identify if OS supports powercap sysfs.

    Returns:
        Boolean, True if powercap supported, False otherwise.
    """
    return os.path.isdir('/sys/devices/virtual/powercap/intel-rapl/')


def has_lid():
    """
    Checks whether the device has lid.

    @return: Returns True if the device has a lid, False otherwise.
    """
    INPUT_DEVICE_LIST = "/dev/input/event*"

    return any(InputDevice(node).is_lid() for node in
               glob.glob(INPUT_DEVICE_LIST))


def _call_dbus_method(destination, path, interface, method_name, args):
    """Performs a generic dbus method call."""
    command = ('dbus-send --type=method_call --system '
               '--dest=%s %s %s.%s %s') % (destination, path, interface,
                                           method_name, args)
    utils.system_output(command)


def call_powerd_dbus_method(method_name, args=''):
    """
    Calls a dbus method exposed by powerd.

    Arguments:
    @param method_name: name of the dbus method.
    @param args: string containing args to dbus method call.
    """
    _call_dbus_method(destination='org.chromium.PowerManager',
                      path='/org/chromium/PowerManager',
                      interface='org.chromium.PowerManager',
                      method_name=method_name, args=args)


def get_power_supply():
    """
    Determine what type of power supply the host has.

    Copied from server/host/cros_hosts.py

    @returns a string representing this host's power supply.
             'power:battery' when the device has a battery intended for
                    extended use
             'power:AC_primary' when the device has a battery not intended
                    for extended use (for moving the machine, etc)
             'power:AC_only' when the device has no battery at all.
    """
    try:
        psu = utils.system_output('cros_config /hardware-properties psu-type')
    except Exception:
        # Assume battery if unspecified in cros_config.
        return 'power:battery'

    psu_str = psu.strip()
    if psu_str == 'unknown':
        return None

    return 'power:%s' % psu_str


def get_sleep_state():
    """
    Returns the current powerd configuration of the sleep state.
    Can be "freeze" or "mem".
    """
    cmd = 'check_powerd_config --suspend_to_idle'
    result = utils.run(cmd, ignore_status=True)
    return 'freeze' if result.exit_status == 0 else 'mem'


def has_battery():
    """Determine if DUT has a battery.

    Returns:
        Boolean, False if known not to have battery, True otherwise.
    """
    return get_power_supply() == 'power:battery'


def get_low_battery_shutdown_percent():
    """Get the percent-based low-battery shutdown threshold.

    Returns:
        Float, percent-based low-battery shutdown threshold. 0 if error.
    """
    ret = 0.0
    try:
        command = 'check_powerd_config --low_battery_shutdown_percent'
        ret = float(utils.run(command).stdout)
    except error.CmdError:
        logging.debug("Can't run %s", command)
    except ValueError:
        logging.debug("Didn't get number from %s", command)

    return ret


def has_hammer():
    """Check whether DUT has hammer device or not.

    Returns:
        boolean whether device has hammer or not
    """
    command = 'grep Hammer /sys/bus/usb/devices/*/product'
    return utils.run(command, ignore_status=True).exit_status == 0


def get_core_keyvals(keyvals):
    """Get important keyvals to report.

    Remove the following types of non-important keyvals.
    - Minor checkpoints. (start with underscore)
    - Individual cpu / gpu frequency buckets.
      (regex '[cg]pu(freq(_\d+)+)?_\d{3,}')
    - Specific idle states from cpuidle/cpupkg.
      (regex '.*cpu(idle|pkg)[ABD-Za-z0-9_\-]+C[^0].*')

    Args:
      keyvals: keyvals to remove non-important ones.

    Returns:
      Dictionary, keyvals with non-important ones removed.
    """
    matcher = re.compile(r"""
                         _.*|
                         .*_[cg]pu(freq(_\d+)+)?_\d{3,}_.*|
                         .*cpu(idle|pkg)[ABD-Za-z0-9_\-]+C[^0].*
                         """, re.X)
    return {k: v for k, v in keyvals.items() if not matcher.match(k)}


def run_kb_backlight_cmd(arg_str):
    """Perform keyboard backlight command.

    Args:
        arg_str:  String of additional arguments to keyboard backlight command.

    Returns:
        String output of the backlight command.

    Raises:
        KbdBacklightException: if 'cmd' returns non-zero exit status.
    """
    cmd = 'backlight_tool --keyboard %s' % (arg_str)
    logging.debug("backlight_cmd: %s", cmd)
    try:
        return utils.system_output(cmd).rstrip()
    except error.CmdError:
        raise KbdBacklightException('%s returns non-zero exit status' % cmd)


# TODO(b/220192766): Remove when Python 2 completely phase out.
def encoding_kwargs():
    """Use encoding kwarg if it is running in Python 3+.
    """
    if sys.version_info.major > 2:
        return {'encoding': 'utf-8'}
    else:
        return {}


class BacklightException(Exception):
    """Class for Backlight exceptions."""


class Backlight(object):
    """Class for control of built-in panel backlight.

    Public methods:
       set_level: Set backlight level to the given brightness.
       set_percent: Set backlight level to the given brightness percent.
       set_default: Set backlight to CrOS default.

       get_level: Get backlight level currently.
       get_max_level: Get maximum backight level.
       get_percent: Get backlight percent currently.
       restore: Restore backlight to initial level when instance created.

    Public attributes:
        default_brightness_percent: float of default brightness.
        force_battery: bool; if True, force backlight_tool to assume that the
                       device is on battery and have AC disconnected; if False,
                       use the device's real power source.

    Private methods:
        _try_bl_cmd: run a backlight command.

    Private attributes:
        _init_level: integer of backlight level when object instantiated.
        _can_control_bl: boolean determining whether backlight can be controlled
                         or queried
    """
    # Default brightness is based on expected average use case.
    # See http://www.chromium.org/chromium-os/testing/power-testing for more
    # details.

    def __init__(self, default_brightness_percent=0, force_battery=False):
        """Constructor.

        attributes:
        """
        self._init_level = None
        self.default_brightness_percent = default_brightness_percent

        self._can_control_bl = True
        try:
            self._init_level = self.get_level()
        except error.TestFail:
            self._can_control_bl = False

        logging.debug("device can_control_bl: %s", self._can_control_bl)
        if not self._can_control_bl:
            return

        if not self.default_brightness_percent:
            force_battery_arg = "--force_battery " if force_battery else ""
            cmd = ("backlight_tool --get_initial_brightness --lux=150 " +
                   force_battery_arg + "2>/dev/null")
            try:
                level = float(utils.system_output(cmd).rstrip())
                self.default_brightness_percent = \
                    (level / self.get_max_level()) * 100
                logging.info("Default backlight brightness percent = %f%s",
                             self.default_brightness_percent,
                             " with force battery" if force_battery else "")
            except error.CmdError:
                self.default_brightness_percent = 40.0
                logging.warning("Unable to determine default backlight "
                                "brightness percent.  Setting to %f",
                                self.default_brightness_percent)

    def _try_bl_cmd(self, arg_str):
        """Perform backlight command.

        Args:
          arg_str:  String of additional arguments to backlight command.

        Returns:
          String output of the backlight command.

        Raises:
          error.TestFail: if 'cmd' returns non-zero exit status.
        """
        if not self._can_control_bl:
            return 0
        cmd = 'backlight_tool %s' % (arg_str)
        logging.debug("backlight_cmd: %s", cmd)
        try:
            return utils.system_output(cmd).rstrip()
        except error.CmdError:
            raise error.TestFail(cmd)

    def set_level(self, level):
        """Set backlight level to the given brightness.

        Args:
          level: integer of brightness to set
        """
        self._try_bl_cmd('--set_brightness=%d' % (level))

    def set_percent(self, percent):
        """Set backlight level to the given brightness percent.

        Args:
          percent: float between 0 and 100
        """
        self._try_bl_cmd('--set_brightness_percent=%f' % (percent))

    def set_default(self):
        """Set backlight to CrOS default.
        """
        self.set_percent(self.default_brightness_percent)

    def get_level(self):
        """Get backlight level currently.

        Returns integer of current backlight level or zero if no backlight
        exists.
        """
        return int(self._try_bl_cmd('--get_brightness'))

    def get_max_level(self):
        """Get maximum backight level.

        Returns integer of maximum backlight level or zero if no backlight
        exists.
        """
        return int(self._try_bl_cmd('--get_max_brightness'))

    def get_percent(self):
        """Get backlight percent currently.

        Returns float of current backlight percent or zero if no backlight
        exists
        """
        return float(self._try_bl_cmd('--get_brightness_percent'))

    def linear_to_nonlinear(self, linear):
        """Convert supplied linear brightness percent to nonlinear.

        Returns float of supplied linear brightness percent converted to
        nonlinear percent.
        """
        return float(self._try_bl_cmd('--linear_to_nonlinear=%f' % linear))

    def nonlinear_to_level(self, nonlinear):
        """Convert supplied nonlinear brightness percent to level.

        Returns float of supplied nonlinear brightness percent converted to
        level.
        """
        return float(self._try_bl_cmd('--nonlinear_to_level=%f' % nonlinear))

    def nonlinear_to_linear(self, nonlinear):
        """Convert supplied nonlinear brightness percent to linear.

        Returns float of supplied nonlinear brightness percent converted to
        linear percent.
        """
        return float(self._try_bl_cmd('--nonlinear_to_linear=%f' % nonlinear))

    def restore(self):
        """Restore backlight to initial level when instance created."""
        if self._init_level is not None:
            self.set_level(self._init_level)


class KbdBacklightException(Exception):
    """Class for KbdBacklight exceptions."""


class KbdBacklight(object):
    """Class for control of keyboard backlight.

    Example code:
        kblight = power_utils.KbdBacklight()
        kblight.set_level(10)
        print "kblight % is %.f" % kblight.get_percent()

    Public methods:
        set_percent: Sets the keyboard backlight to a percent.
        get_percent: Get current keyboard backlight percentage.
        set_level: Sets the keyboard backlight to a level.
        get_level: Get current keyboard backlight level.
        get_default_level: Get default keyboard backlight brightness level.
        get_max_level: Get maximum keyboard backight level.
        restore: Restore keyboard backlight level to before this object started
                 controlling it.
        linear_to_nonlinear: convert linear percentage to nonlinear (UI)
                             percentage.
        nonlinear_to_linear: convert nonlinear(UI) percentage to linear
                             percentage.

    Private attributes:
        _default_backlight_level: keboard backlight level set by default
        _original_backlight_level: keyboard backlight level before this object
                                   started controlling it.
    """

    def __init__(self):
        cmd = 'check_powerd_config --keyboard_backlight'
        result = utils.run(cmd, ignore_status=True)
        if result.exit_status:
            raise KbdBacklightException(
                    'Keyboard backlight support is not enabled')
        arg = "--get_initial_brightness --lux=0 2>/dev/null"
        self._default_backlight_level = int(run_kb_backlight_cmd(arg))
        self._original_backlight_level = self.get_level()
        logging.info(
                "Default keyboard backlight brightness level = %d, "
                "current keyboard backlight brightness level = %d",
                self._default_backlight_level, self._original_backlight_level)

    def get_percent(self):
        """Get current keyboard brightness setting percentage.

        Returns:
            float, percentage of keyboard brightness in the range [0.0, 100.0].
        """
        arg = '--get_brightness_percent'
        return float(run_kb_backlight_cmd(arg))

    def get_level(self):
        """Get current keyboard brightness setting level.

        Returns:
            int, level of keyboard brightness.
        """
        arg = '--get_brightness'
        return int(run_kb_backlight_cmd(arg))

    def get_default_level(self):
        """
        Returns the default backlight level.

        Returns:
            The default keyboard backlight level.
        """
        return self._default_backlight_level

    def set_percent(self, percent):
        """Set keyboard backlight percent.

        Args:
        @param percent: float value in the range [0.0, 100.0]
                        to set keyboard backlight to.
        """
        arg = '--set_brightness_percent=%f' % percent
        run_kb_backlight_cmd(arg)

    def set_level(self, level):
        """
        Set keyboard backlight to given level.
        Args:
        @param level: level to set keyboard backlight to.
        """
        arg = '--set_brightness=%d' % level
        run_kb_backlight_cmd(arg)

    def get_max_level(self):
        """
        Get maximum keyboard backlight level.

        Returns:
            int, maximum keyboard backlight level.
        """
        return int(run_kb_backlight_cmd('--get_max_brightness'))

    def restore(self):
        """
        Set keyboard backlight to original level.
        """
        self.set_level(self._original_backlight_level)

    def linear_to_nonlinear(self, linear):
        """Convert supplied linear brightness percent to nonlinear.

        Returns float of supplied linear brightness percent converted to
        nonlinear percent.
        """
        return float(run_kb_backlight_cmd('--linear_to_nonlinear=%f' % linear))

    def nonlinear_to_linear(self, nonlinear):
        """Convert supplied nonlinear brightness percent to linear.

        Returns float of supplied nonlinear brightness percent converted to
        linear percent.
        """
        return float(run_kb_backlight_cmd('--nonlinear_to_linear=%f' % nonlinear))


class BacklightController(object):
    """Class to simulate control of backlight via keyboard or Chrome UI.

    Public methods:
      increase_brightness: Increase backlight by one adjustment step.
      decrease_brightness: Decrease backlight by one adjustment step.
      set_brightness_to_max: Increase backlight to max by calling
          increase_brightness()
      set_brightness_to_min: Decrease backlight to min or zero by calling
          decrease_brightness()

    Private attributes:
      _max_num_steps: maximum number of backlight adjustment steps between 0 and
                      max brightness.
    """

    def __init__(self):
        self._max_num_steps = 16

    def decrease_brightness(self, allow_off=False):
        """
        Decrease brightness by one step, as if the user pressed the brightness
        down key or button.

        Arguments
        @param allow_off: Boolean flag indicating whether the brightness can be
                     reduced to zero.
                     Set to true to simulate brightness down key.
                     set to false to simulate Chrome UI brightness down button.
        """
        call_powerd_dbus_method('DecreaseScreenBrightness',
                                'boolean:%s' %
                                ('true' if allow_off else 'false'))

    def increase_brightness(self):
        """
        Increase brightness by one step, as if the user pressed the brightness
        up key or button.
        """
        call_powerd_dbus_method('IncreaseScreenBrightness')

    def set_brightness_to_max(self):
        """
        Increases the brightness using powerd until the brightness reaches the
        maximum value. Returns when it reaches the maximum number of brightness
        adjustments
        """
        num_steps_taken = 0
        while num_steps_taken < self._max_num_steps:
            self.increase_brightness()
            time.sleep(0.05)
            num_steps_taken += 1

    def set_brightness_to_min(self, allow_off=False):
        """
        Decreases the brightness using powerd until the brightness reaches the
        minimum value (zero or the minimum nonzero value). Returns when it
        reaches the maximum number of brightness adjustments.

        Arguments
        @param allow_off: Boolean flag indicating whether the brightness can be
                     reduced to zero.
                     Set to true to simulate brightness down key.
                     set to false to simulate Chrome UI brightness down button.
        """
        num_steps_taken = 0
        while num_steps_taken < self._max_num_steps:
            self.decrease_brightness(allow_off)
            time.sleep(0.05)
            num_steps_taken += 1


class DisplayException(Exception):
    """Class for Display exceptions."""


def set_display_power(power_val):
    """Function to control screens via Chrome.

    Possible arguments:
      DISPLAY_POWER_ALL_ON,
      DISPLAY_POWER_ALL_OFF,
      DISPLAY_POWER_INTERNAL_OFF_EXTERNAL_ON,
      DISPLAY_POWER_INTERNAL_ON_EXTENRAL_OFF
    """
    if (not isinstance(power_val, int)
            or power_val < DISPLAY_POWER_ALL_ON
            or power_val >= DISPLAY_POWER_MAX):
        raise DisplayException('Invalid display power setting: %d' % power_val)
    _call_dbus_method(destination='org.chromium.DisplayService',
                      path='/org/chromium/DisplayService',
                      interface='org.chromium.DisplayServiceInterface',
                      method_name='SetPower',
                      args='int32:%d' % power_val)


class PowerPrefChanger(object):
    """
    Class to temporarily change powerd prefs. Construct with a dict of
    pref_name/value pairs (e.g. {'disable_idle_suspend':0}). Destructor (or
    reboot) will restore old prefs automatically."""

    _PREFDIR = '/var/lib/power_manager'
    _TEMPDIR = '/tmp/autotest_powerd_prefs'
    _DBUS_TIMEOUT_SECONDS = 10

    def __init__(self, prefs):
        shutil.copytree(self._PREFDIR, self._TEMPDIR)
        for name, value in prefs.items():
            utils.write_one_line('%s/%s' % (self._TEMPDIR, name), value)
        utils.system('mount --bind %s %s' % (self._TEMPDIR, self._PREFDIR))
        self._restart_powerd()

    @classmethod
    def _restart_powerd(cls):
        try:
            import dbus
            from autotest_lib.client.cros import dbus_util
        except ImportError as e:
            logging.exception(
                    'Cannot import dbus libraries: %s. This method should only '
                    'be called on a Cros device.', e)
            raise
        upstart.restart_job('powerd')
        # Wait for the DBus session to start
        bus = dbus.SystemBus()
        dbus_util.get_dbus_object(bus,
                                  'org.chromium.PowerManager',
                                  '/org/chromium/PowerManager',
                                  cls._DBUS_TIMEOUT_SECONDS)

    @classmethod
    def finalize(cls):
        """finalize"""
        if os.path.exists(cls._TEMPDIR):
            utils.system('umount %s' % cls._PREFDIR, ignore_status=True)
            shutil.rmtree(cls._TEMPDIR)
            cls._restart_powerd()

    def __del__(self):
        self.finalize()


class Registers(object):
    """Class to examine PCI and MSR registers."""

    def __init__(self):
        self._cpu_id = 0
        self._rdmsr_cmd = 'iotools rdmsr'
        self._mmio_read32_cmd = 'iotools mmio_read32'
        self._rcba = 0xfed1c000

        self._pci_read32_cmd = 'iotools pci_read32'
        self._mch_bar = None
        self._dmi_bar = None

    def _init_mch_bar(self):
        if self._mch_bar != None:
            return
        # MCHBAR is at offset 0x48 of B/D/F 0/0/0
        cmd = '%s 0 0 0 0x48' % (self._pci_read32_cmd)
        self._mch_bar = int(utils.system_output(cmd), 16) & 0xfffffffe
        logging.debug('MCH BAR is %s', hex(self._mch_bar))

    def _init_dmi_bar(self):
        if self._dmi_bar != None:
            return
        # DMIBAR is at offset 0x68 of B/D/F 0/0/0
        cmd = '%s 0 0 0 0x68' % (self._pci_read32_cmd)
        self._dmi_bar = int(utils.system_output(cmd), 16) & 0xfffffffe
        logging.debug('DMI BAR is %s', hex(self._dmi_bar))

    def _read_msr(self, register):
        cmd = '%s %d %s' % (self._rdmsr_cmd, self._cpu_id, register)
        return int(utils.system_output(cmd), 16)

    def _read_mmio_read32(self, address):
        cmd = '%s 0x%x' % (self._mmio_read32_cmd, address)
        return int(utils.system_output(cmd), 16)

    def _read_dmi_bar(self, offset):
        self._init_dmi_bar()
        return self._read_mmio_read32(self._dmi_bar + int(offset, 16))

    def _read_mch_bar(self, offset):
        self._init_mch_bar()
        return self._read_mmio_read32(self._mch_bar + int(offset, 16))

    def _read_rcba(self, offset):
        return self._read_mmio_read32(self._rcba + int(offset, 16))

    def _shift_mask_match(self, reg_name, value, match):
        expr = match[1]
        bits = match[0].split(':')
        operator = match[2] if len(match) == 3 else '=='
        hi_bit = int(bits[0])
        if len(bits) == 2:
            lo_bit = int(bits[1])
        else:
            lo_bit = int(bits[0])

        value >>= lo_bit
        mask = (1 << (hi_bit - lo_bit + 1)) - 1
        value &= mask

        good = eval("%d %s %d" % (value, operator, expr))
        if not good:
            logging.error(
                'FAILED: %s bits: %s value: %s mask: %s expr: %s operator: %s',
                reg_name, bits, hex(value), mask, expr, operator)
        return good

    def _verify_registers(self, reg_name, read_fn, match_list):
        errors = 0
        for k, v in match_list.items():
            r = read_fn(k)
            for item in v:
                good = self._shift_mask_match(reg_name, r, item)
                if not good:
                    errors += 1
                    logging.error('Error(%d), %s: reg = %s val = %s match = %s',
                                  errors, reg_name, k, hex(r), v)
                else:
                    logging.debug('ok, %s: reg = %s val = %s match = %s',
                                  reg_name, k, hex(r), v)
        return errors

    def verify_msr(self, match_list):
        """
        Verify MSR

        @param match_list: match list
        """
        errors = 0
        for cpu_id in range(0, max(utils.count_cpus(), 1)):
            self._cpu_id = cpu_id
            errors += self._verify_registers('msr', self._read_msr, match_list)
        return errors

    def verify_dmi(self, match_list):
        """
        Verify DMI

        @param match_list: match list
        """
        return self._verify_registers('dmi', self._read_dmi_bar, match_list)

    def verify_mch(self, match_list):
        """
        Verify MCH

        @param match_list: match list
        """
        return self._verify_registers('mch', self._read_mch_bar, match_list)

    def verify_rcba(self, match_list):
        """
        Verify RCBA

        @param match_list: match list
        """
        return self._verify_registers('rcba', self._read_rcba, match_list)


class USBDevicePower(object):
    """Class for USB device related power information.

    Public Methods:
        autosuspend: Return boolean whether USB autosuspend is enabled or False
                     if not or unable to determine

    Public attributes:
        vid: string of USB Vendor ID
        pid: string of USB Product ID
        allowlisted: Boolean if USB device is allowlisted for USB auto-suspend

    Private attributes:
       path: string to path of the USB devices in sysfs ( /sys/bus/usb/... )

    TODO(tbroch): consider converting to use of pyusb although not clear its
    beneficial if it doesn't parse power/control
    """

    def __init__(self, vid, pid, allowlisted, path):
        self.vid = vid
        self.pid = pid
        self.allowlisted = allowlisted
        self._path = path

    def autosuspend(self):
        """Determine current value of USB autosuspend for device."""
        control_file = os.path.join(self._path, 'control')
        if not os.path.exists(control_file):
            logging.info('USB: power control file not found for %s', dir)
            return False

        out = utils.read_one_line(control_file)
        logging.debug('USB: control set to %s for %s', out, control_file)
        return (out == 'auto')


class USBPower(object):
    """Class to expose USB related power functionality.

    Initially that includes the policy around USB auto-suspend and our
    allowlisting of devices that are internal to CrOS system.

    Example code:
       usbdev_power = power_utils.USBPower()
       for device in usbdev_power.devices
           if device.is_allowlisted()
               ...

    Public attributes:
        devices: list of USBDevicePower instances

    Private functions:
        _is_allowlisted: Returns Boolean if USB device is allowlisted for USB
                         auto-suspend
        _load_allowlist: Reads allowlist and stores int _allowlist attribute

    Private attributes:
        _alist_file: path to laptop-mode-tools (LMT) USB autosuspend
                         conf file.
        _alist_vname: string name of LMT USB autosuspend allowlist
                          variable
        _allowlisted: list of USB device vid:pid that are allowlisted.
                        May be regular expressions.  See LMT for details.
    """

    def __init__(self):
        self._alist_file = \
            '/etc/laptop-mode/conf.d/board-specific/usb-autosuspend.conf'
        # TODO b:169251326 terms below are set outside of this codebase
        # and should be updated when possible. ("WHITELIST" -> "ALLOWLIST") # nocheck
        self._alist_vname = '$AUTOSUSPEND_USBID_WHITELIST' # nocheck
        self._allowlisted = None
        self.devices = []

    def _load_allowlist(self):
        """Load USB device allowlist for enabling USB autosuspend

        CrOS allowlist only internal USB devices to enter USB auto-suspend mode
        via laptop-mode tools.
        """
        cmd = "source %s && echo %s" % (self._alist_file,
                                        self._alist_vname)
        out = utils.system_output(cmd, ignore_status=True)
        logging.debug('USB allowlist = %s', out)
        self._allowlisted = out.split()

    def _is_allowlisted(self, vid, pid):
        """Check to see if USB device vid:pid is allowlisted.

        Args:
          vid: string of USB vendor ID
          pid: string of USB product ID

        Returns:
          True if vid:pid in allowlist file else False
        """
        if self._allowlisted is None:
            self._load_allowlist()

        match_str = "%s:%s" % (vid, pid)
        for re_str in self._allowlisted:
            if re.match(re_str, match_str):
                return True
        return False

    def query_devices(self):
        """."""
        dirs_path = '/sys/bus/usb/devices/*/power'
        dirs = glob.glob(dirs_path)
        if not dirs:
            logging.info('USB power path not found')
            return 1

        for dirpath in dirs:
            vid_path = os.path.join(dirpath, '..', 'idVendor')
            pid_path = os.path.join(dirpath, '..', 'idProduct')
            if not os.path.exists(vid_path):
                logging.debug("No vid for USB @ %s", vid_path)
                continue
            vid = utils.read_one_line(vid_path)
            pid = utils.read_one_line(pid_path)
            allowlisted = self._is_allowlisted(vid, pid)
            self.devices.append(USBDevicePower(vid, pid, allowlisted, dirpath))


class DisplayPanelSelfRefresh(object):
    """Class for control and monitoring of display's PSR."""
    _PSR_STATUS_FILE_X86 = '/sys/kernel/debug/dri/0/i915_edp_psr_status'
    _PSR_STATUS_FILE_ARM = '/sys/kernel/debug/dri/*/psr_active_ms'

    def __init__(self, init_time=time.time()):
        """Initializer.

        @Public attributes:
            supported: Boolean of whether PSR is supported or not

        @Private attributes:
            _init_time: time when PSR class was instantiated.
            _init_counter: integer of initial value of residency counter.
            _keyvals: dictionary of keyvals
        """
        self._psr_path = ''
        if os.path.exists(self._PSR_STATUS_FILE_X86):
            self._psr_path = self._PSR_STATUS_FILE_X86
            self._psr_parse_prefix = 'Performance_Counter:'
        else:
            paths = glob.glob(self._PSR_STATUS_FILE_ARM)
            if paths:
                # Should be only one PSR file
                self._psr_path = paths[0]
                self._psr_parse_prefix = ''

        self._init_time = init_time
        self._init_counter = self._get_counter()
        self._keyvals = {}
        self.supported = (self._init_counter != None)

    def _get_counter(self):
        """Get the current value of the system PSR counter.

        This counts the number of milliseconds the system has resided in PSR.

        @returns: amount of time PSR has been active since boot in ms, or None if
        the performance counter can't be read.
        """
        try:
            count = utils.get_field(utils.read_file(self._psr_path),
                                    0, linestart=self._psr_parse_prefix)
        except IOError:
            logging.info("Can't find or read PSR status file")
            return None

        logging.debug("PSR performance counter: %s", count)
        return int(count) if count else None

    def _calc_residency(self):
        """Calculate the PSR residency.

        @returns: PSR residency in percent or -1 if not able to calculate.
        """
        if not self.supported:
            return -1

        tdelta = time.time() - self._init_time
        cdelta = self._get_counter() - self._init_counter
        return cdelta / (10 * tdelta)

    def refresh(self):
        """Refresh PSR related data."""
        self._keyvals['percent_psr_residency'] = self._calc_residency()

    def get_keyvals(self):
        """Get keyvals associated with PSR data.

        @returns dictionary of keyvals
        """
        return self._keyvals


class BaseActivityException(Exception):
    """Class for base activity simulation exceptions."""


class BaseActivitySimulator(object):
    """Class to simulate wake activity on the normally autosuspended base."""

    # Note on naming: throughout this class, the word base is used to mean the
    # base of a detachable (keyboard, touchpad, etc).

    # file defines where to look for detachable base.
    # TODO(coconutruben): check when next wave of detachables come out if this
    # structure still holds, or if we need to replace it by querying input
    # devices.
    _BASE_INIT_CMD = 'cros_config /detachable-base usb-path'
    _BASE_INIT_FILE = '/etc/init/hammerd.override'
    _BASE_WAKE_TIME_MS = 10000

    def __init__(self):
        """Initializer

        Let the BaseActivitySimulator bootstrap itself by detecting if
        the board is a detachable, and ensuring the base path exists.
        Sets the base to autosuspend, and the autosuspend delay to be
        at most _BASE_WAKE_TIME_MS.

        """
        self._should_run = False

        if os.path.exists(self._BASE_INIT_FILE):
            # Try hammerd.override first.
            init_file_content = utils.read_file(self._BASE_INIT_FILE)
            try:
                # The string can be like: env USB_PATH="1-1.1"
                path = re.search(r'env USB_PATH=\"?([0-9.-]+)\"?',
                                 init_file_content).group(1)
            except AttributeError:
                logging.warning('Failed to read USB path from hammerd file.')
            else:
                self._should_run = self._set_base_power_path(path)
                if not self._should_run:
                    logging.warning('Device has hammerd file, but base USB'
                                    ' device not found.')

        if not self._should_run:
            # Try cros_config.
            result = utils.run(self._BASE_INIT_CMD, ignore_status=True)
            if result.exit_status:
                logging.warning('Command failed: %s', self._BASE_INIT_CMD)
            else:
                self._should_run = self._set_base_power_path(result.stdout)
                if not self._should_run:
                    logging.warning('cros_config has base info, but base USB'
                                    ' device not found.')

        if self._should_run:
            self._base_control_path = os.path.join(self._base_power_path,
                                                   'control')
            self._autosuspend_delay_path = os.path.join(self._base_power_path,
                                                        'autosuspend_delay_ms')
            logging.debug("base activity simulator will be running.")
            with open(self._base_control_path, 'r+') as f:
                self._default_control = f.read()
                if self._default_control != 'auto':
                    logging.debug("Putting the base into autosuspend.")
                    f.write('auto')

            with open(self._autosuspend_delay_path, 'r+') as f:
                self._default_autosuspend_delay_ms = f.read().rstrip('\n')
                f.write(str(self._BASE_WAKE_TIME_MS))
        else:
            logging.info('No base USB device found, base activity simulator'
                         ' will NOT be running.')

    def _set_base_power_path(self, usb_path):
        """Set base power path and check if it exists.

        Args:
          usb_path: the USB device path under /sys/bus/usb/devices/.

        Returns:
          True if the base power path exists, or False otherwise.
        """
        self._base_power_path = '/sys/bus/usb/devices/%s/power/' % usb_path
        if not os.path.exists(self._base_power_path):
            logging.warning('Path not found: %s', self._base_power_path)
        return os.path.exists(self._base_power_path)

    def wake_base(self, wake_time_ms=_BASE_WAKE_TIME_MS):
        """Wake up the base to simulate user activity.

        Args:
          wake_time_ms: time the base should be turned on
                        (taken out of autosuspend) in milliseconds.
        """
        if self._should_run:
            logging.debug("Taking base out of runtime suspend for %d seconds",
                          wake_time_ms/1000)
            with open(self._autosuspend_delay_path, 'r+') as f:
                f.write(str(wake_time_ms))
            # Toggling the control will keep the base awake for
            # the duration specified in the autosuspend_delay_ms file.
            with open(self._base_control_path, 'w') as f:
                f.write('on')
            with open(self._base_control_path, 'w') as f:
                f.write('auto')

    def restore(self):
        """Restore the original control and autosuspend delay."""
        if self._should_run:
            with open(self._base_control_path, 'w') as f:
                f.write(self._default_control)

            with open(self._autosuspend_delay_path, 'w') as f:
                f.write(self._default_autosuspend_delay_ms)


def is_charge_limit_enabled():
    """Return if Charge Limit is enabled.

    Returns:
      True if Charge Limit is enabled and False if it is not.\
    """
    _CHECK_CHARGE_LIMIT_ENABLED_CMD_ = \
        'check_powerd_config --charge_limit_enabled'
    result = utils.run(_CHECK_CHARGE_LIMIT_ENABLED_CMD_, ignore_status=True)
    return (result.exit_status == 0)


hdrnet_path = "/run/camera/hdrnet_config.json"


def disable_camera_hdrnet():
    """Disable camera hdrnet feature by creating a override config file."""
    content = {
            "hdrnet_enable": False,
    }
    with open(hdrnet_path, 'w') as f:
        json.dump(content, f, indent=4)


def remove_camera_hdrnet_override():
    """Remove camera hdrnet override by deleting the config file."""
    if os.path.isfile(hdrnet_path):
        os.remove(hdrnet_path)
