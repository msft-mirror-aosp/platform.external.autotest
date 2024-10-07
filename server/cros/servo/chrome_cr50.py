# Copyright 2017 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import functools
import logging
import pprint
import re
import six
from six.moves import range
import time

from autotest_lib.client.bin import utils
from autotest_lib.client.common_lib import error
from autotest_lib.client.common_lib.cros import cr50_utils
from autotest_lib.server.cros.servo import chrome_ec
from autotest_lib.server.cros.servo import servo

CHIP_NAME = 'cr50'

def dts_control_command(func):
    """For methods that should only run when dts mode control is supported."""
    @functools.wraps(func)
    def wrapper(instance, *args, **kwargs):
        """Ignore those functions if dts mode control is not supported."""
        if instance._servo.dts_mode_is_valid():
            return func(instance, *args, **kwargs)
        logging.info('Servo setup does not support DTS mode. ignoring %s',
                     func.__name__)
    return wrapper


class ChromeCr50(chrome_ec.ChromeConsole):
    """Manages control of a Chrome Cr50.

    We control the Chrome Cr50 via the console of a Servo board. Chrome Cr50
    provides many interfaces to set and get its behavior via console commands.
    This class is to abstract these interfaces.
    """
    PROD_RW_KEYIDS = ['0x87b73b67', '0xde88588d']
    PROD_RO_KEYIDS = ['0xaa66150f']
    OPEN = 'open'
    UNLOCK = 'unlock'
    LOCK = 'lock'
    PP_SHORT_INT = 1
    # Cr50 command to erase board id and rollback space.
    EFI_CMD = 'eraseflashinfo'
    # The amount of time you need to show physical presence.
    PP_SHORT = 15
    PP_LONG = 300
    CCD_PASSWORD_RATE_LIMIT = 3
    IDLE_COUNT = 'count: (\d+)\s'
    SHORT_WAIT = 3
    ACCESS_DENIED = 'Access Denied'
    CCD_PW_DENIED = ACCESS_DENIED
    BID_RE = r'Board ID: (\S{8}):?(|\S{8}), flags (\S{8})\s'
    # The version has four groups: the partition, the header version, debug
    # descriptor and then version string.
    # There are two partitions A and B. The active partition is marked with a
    # '*'. If it is a debug image '/DBG' is added to the version string. If the
    # image has been corrupted, the version information will be replaced with
    # 'Error'.
    # So the output may look something like this.
    #   RW_A:    0.0.21/cr50_v1.1.6133-fd788b
    #   RW_B:  * 0.0.22/DBG/cr50_v1.1.6138-b9f0b1d
    # Or like this if the region was corrupted.
    #   RW_A:  * 0.0.21/cr50_v1.1.6133-fd788b
    #   RW_B:    Error
    # Ti50 will print "Empty" not "Error"
    VERSION_FORMAT = 'RW_(A|B): +%s +(\d+\.\d+\.\d+|Error|Empty)(/DBG)?(\S+)?\s'
    INACTIVE_VERSION = VERSION_FORMAT % ''
    ACTIVE_VERSION = VERSION_FORMAT % '\*'
    RO_VERSION_FORMAT = VERSION_FORMAT.replace('RW', 'RO')

    RO_ACTIVE_VERSION = RO_VERSION_FORMAT % '\*'
    # Following lines of the version output may print the image board id
    # information. eg.
    # BID A:   5a5a4146:ffffffff:00007f00 Yes
    # BID B:   00000000:00000000:00000000 Yes
    # Use the first group from ACTIVE_VERSION to match the active board id
    # partition.
    BID_ERROR = 'read_board_id: failed'
    BID_FORMAT = ':\s+[a-f0-9:]{26} '
    ACTIVE_BID = r'%s.*(\1%s|%s.*>)' % (ACTIVE_VERSION, BID_FORMAT,
            BID_ERROR)
    WAKE_CHAR = '\n\n\n\n'
    WAKE_RESPONSE = ['(>|Console is enabled)']
    START_UNLOCK_TIMEOUT = 20
    GETTIME = ['= (\S+)']
    FWMP_LOCKED_PROD = ["Managed device console can't be unlocked"]
    FWMP_LOCKED_DBG = ['Ignoring FWMP unlock setting']
    MAX_RETRY_COUNT = 10
    CCDSTATE_MAX_RETRY_COUNT = 20
    START_STR = ['((Havn|UART).*Console is enabled;)']
    NAME = CHIP_NAME
    REBOOT_DELAY_WITH_CCD = 60
    REBOOT_DELAY_WITH_FLEX = 3
    ON_STRINGS = ['enable', 'enabled', 'on']
    CONSERVATIVE_CCD_WAIT = 10
    CCD_SHORT_PRESSES = 5
    CAP_IS_ACCESSIBLE = 0
    CAP_SETTING = 1
    CAP_REQ = 2
    GET_CAP_TRIES = 20
    # Cap used to require 10s of physical presence to open ccd.
    CAP_SHORT_PP = 'UnlockNoShortPP'
    # Cap used to require wiping nvmem before opening ccd.
    CAP_OPEN_NO_TPM_WIPE = 'OpenNoTPMWipe'
    CAP_IF_OPENED = 'IfOpened'
    CAP_ALWAYS = 'Always'
    # Regex to match the valid capability settings.
    CAP_STATES = '(%s|Default|%s|UnlessLocked|Never)' % (CAP_ALWAYS, CAP_IF_OPENED)
    # There are two capability formats. Match both.
    #  UartGscRxECTx   Y 3=IfOpened
    #  or
    #  UartGscRxECTx   Y 0=Default (Always)
    # Make sure the last word is at the end of the line. The next line will
    # start with some whitespace, so account for that too.
    CAP_FORMAT = r'\s+(Y|-) \d\=(%s[\S ]*)[\r\n]+\s*' % CAP_STATES

    # If any capabilities are used by all servo types, add them to this list.
    UNIVERSAL_SERVO_REQ_CAPS = []
    SERVO_SPECIFIC_REQ_CAPS = {
            # CCD Capabilities used for c2d2 control drivers. C2D2 just needs
            # console command access.
            'c2d2': [
                    'OverrideWP',
                    'RebootECAP',
                    'GscFullConsole',
            ],
            # CCD needs most stuff.
            'ccd': [
                    # Open without physical presence. Being able to reopen ccd
                    # is the most important part.
                    'UnlockNoShortPP',
                    'OpenNoLongPP',
                    'OpenNoDevMode',
                    'OpenFromUSB',
                    # UART
                    'UartGscRxAPTx',
                    'UartGscTxAPRx',
                    'UartGscRxECTx',
                    'UartGscTxECRx',
                    # Flash access
                    'FlashAP',
                    'FlashEC',
                    # Console commands
                    'OverrideWP',
                    'RebootECAP',
                    'GscFullConsole',
            ],
            # servo_* servos don't need any ccd capabilities.
            'servo': [],
    }

    BOARD_PROP_ALWAYS_TRUE = []
    # CR50 Board Properties as defined in platform/ec/board/cr50/scratch-reg1.h
    BOARD_PROP = {
            'BOARD_PERIPH_CONFIG_SPI': (1 << 0, None),
            'BOARD_PERIPH_CONFIG_SPI': (1 << 0, None),
            'BOARD_PERIPH_CONFIG_I2C': (1 << 1, None),
            'BOARD_PERIPH_CONFIG_I2C': (1 << 1, None),
            'BOARD_NEEDS_SYS_RST_PULL_UP': (1 << 5, None),
            'BOARD_USE_PLT_RESET': (1 << 6, None),
            'BOARD_WP_ASSERTED': (1 << 8, None),
            'BOARD_FORCING_WP': (1 << 9, None),
            'BOARD_NO_RO_UART': (1 << 10, None),
            'BOARD_CCD_UNLOCKED': (1 << 11, 3 << 11),
            'BOARD_CCD_OPENED': (2 << 11, 3 << 11),
            'BOARD_DEEP_SLEEP_DISABLED': (1 << 13, None),
            'BOARD_DETECT_AP_WITH_UART': (1 << 14, None),
            'BOARD_ITE_EC_SYNC_NEEDED': (1 << 15, None),
            'BOARD_WP_DISABLE_DELAY': (1 << 16, None),
            'BOARD_CLOSED_SOURCE_SET1': (1 << 17, None),
            'BOARD_CLOSED_LOOP_RESET': (1 << 18, None),
            'BOARD_NO_INA_SUPPORT': (1 << 19, None),
            'BOARD_ALLOW_CHANGE_TPM_MODE': (1 << 20, None),
            'BOARD_EC_CR50_COMM_SUPPORT': (1 << 21, None),
            'BOARD_CCD_REC_LID_PIN_DIOA1': (1 << 22, 3 << 22),
            'BOARD_CCD_REC_LID_PIN_DIOA9': (2 << 22, 3 << 22),
            'BOARD_CCD_REC_LID_PIN_DIOA12': (3 << 22, 3 << 22)
    }

    # CR50 reset flags as defined in platform ec_commands.h. These are only the
    # flags used by cr50.
    RESET_FLAGS = {
           'RESET_FLAG_OTHER'            : 1 << 0,
           'RESET_FLAG_BROWNOUT'         : 1 << 2,
           'RESET_FLAG_POWER_ON'         : 1 << 3,
           'RESET_FLAG_SOFT'             : 1 << 5,
           'RESET_FLAG_HIBERNATE'        : 1 << 6,
           'RESET_FLAG_RTC_ALARM'        : 3 << 7,
           'RESET_FLAG_WAKE_PIN'         : 1 << 8,
           'RESET_FLAG_HARD'             : 1 << 11,
           'RESET_FLAG_USB_RESUME'       : 1 << 14,
           'RESET_FLAG_RDD'              : 1 << 15,
           'RESET_FLAG_RBOX'             : 1 << 16,
           'RESET_FLAG_SECURITY'         : 1 << 17,
    }
    FIPS_RE = r' ([^ ]*)approved.*allowed: (1|0)'
    # Cr50 may have flash operation errors during the test. Here's an example
    # of one error message.
    # List of errors to search for. The first element is the string to look
    # for. The second is a bool that tells whether the error should be fatal.
    ERROR_DESC_LIST = [
            # do_flash_op:245 errors 20 fsh_pe_control 40720004
            # The stuff after the ':' may change, but all flash operation errors
            # contain do_flash_op. do_flash_op is only ever printed if there is an
            # error during the flash operation. Just search for do_flash_op to
            # simplify the search string and make it applicable to all flash op
            # errors.
            ['do_flash_op', False],
            # USB issues may show up with the timer sof calibration overflow
            # interrupt. Count these during cleanup.
            ['timer_sof_calibration_overflow_int', False],
            # Message printed during watchdog reset.
            ['WATCHDOG PC', True],
            # Message printed when there's an invalid EPS seed size.
            [': seed size', True]
    ]
    # Regex for checking if the ccd device is connected.
    CCD_CONNECTED_RE = r'ccd.*: connected'
    # ===============================================================
    # Constants used to report the AP state
    CCDSTATE_FULL_EXT = ' full'
    CCDSTATE_AP_KEY = 'AP'
    # If ccdstate prints appends "(K)" or "(F)" to the AP state, it'll show up
    # in the AP full output.
    CCDSTATE_AP_FULL_KEY = CCDSTATE_AP_KEY + CCDSTATE_FULL_EXT
    # PCR0 Info
    CCDSTATE_PCR0_KEY = 'pcr0'
    # Just print the first 8 characters of the pcr0 value. That should be enough
    # to determine the state.
    PCR0_REPORT_CHARS = 8
    PCR0_DICT = {
        # Known PCR0 values.
        '0000000000000000000000000000000000000000000000000000000000000000' : 'zeroed',
        '89eaf35134b4b3c649f44c0c765b96aeab8bb34ee83cc7a683c4e53d1581c8c7' : 'normal',
        '9f9ea866d3f34fe3a3112ae9cb1fbabc6ffe8cd261d42493bc6842a9e4f93b3d' : 'rec',
        '23e14dd9bb51a50e16911f7e11df1e1aaf0b17134dc739c5653607a1ec8dd37a' : 'dev',
        '2a7580e5da289546f4d2e0509cc6de155ea131818954d36d49e027fd42b8c8f8' : 'dev+rec',
        # If cr50 can't read the pcr0 value, it'll return "error"
        'error' : 'pcr_read_error',
    }
    # ===============================================================
    # AP_RO strings
    # Specify the start of the output as ap_ro_check or result, so the timestamp
    # of the ap_ro_check_unsupported message is ignored. This lets the test
    # compare the output. Use '|' instead of '?', so the result format is the
    # same whether or not ap_ro_check output shows up in the result.
    GET_AP_RO_OUTPUT_RE = [r'(ap_ro_check.*|)result.*>']
    # Cr50 only supports v2
    AP_RO_VERSIONS = [1]
    # supported is a substring of ap_ro_check_unsupported. Make sure to check
    # for ap_ro_check_unsupported first.
    AP_RO_KEYS = [
        'ap_ro_check_unsupported',
        'flags',
        'gbbd',
        'result',
        'supported',
        'sha256 hash'
    ]
    # This is a list of optional AP RO keys. Set them to None while getting the
    # ap ro status to ensure they always exist.
    AP_RO_OPTIONAL_KEY_DICT = {
        'hash' : None,
        'reason' : None,
        'gbbd' : None,
        'flags' : None
    }
    # Rename some keys for read
    AP_RO_KEY_MAP = {
        'ap_ro_check_unsupported' : 'reason',
        'sha256 hash' : 'hash'
    }

    # ===============================================================
    # Cr50 Image Names
    GS_PRIVATE = 'gs://chromeos-localmirror-private/distfiles/'
    GS_PUBLIC = 'gs://chromeos-localmirror/distfiles/'
    # Prod signed test images are stored in the private cr50 directory.
    GS_PRIVATE_PROD = GS_PRIVATE + 'cr50/'
    # Node locked test images are in this private debug directory.
    GS_PRIVATE_DBG = GS_PRIVATE + 'chromeos-cr50-debug-0.0.11/'
    # cr50.r0.0.1*.wRW_VER.BID.tbz2
    PROD_TAR = 'cr50.r0.0.1*.w%s%s.tbz2'
    # cr50.dbg.0xDEVID0_0xDEVID1.bin.GIT_SHA
    DEBUG_FILE = '*/cr50.dbg.%s.bin.*%s'
    # cr50_Unknown_NodeLocked-DEVID0-DEVID1_cr50-accessory-mp.bin
    ERASEFLASHINFO_FILE = (
            '*/cr50_Unknown_NodeLocked-%s_cr50-accessory-mp.bin')
    QUAL_VERSION_FILE = 'chromeos-cr50-QUAL_VERSION'

    # Cr50 OS FW information.
    # Image prefix used by Chrome OS.
    GSC_IMG_PREFIX = 'cr50'
    # ChromeOS Cr50 firmware directory
    DUT_FW = '/opt/google/cr50/firmware/'

    PROD_FILE = GSC_IMG_PREFIX + '.bin.prod'
    DUT_PROD = DUT_FW + PROD_FILE
    DUT_PREPVT = DUT_FW + GSC_IMG_PREFIX + '.bin.prepvt'
    DUT_REMOVE_GSC_IMAGES = 'rm ' + DUT_FW + GSC_IMG_PREFIX + '*'

    DUT_PROD_PATHS = [DUT_PROD]
    DUT_PREPVT_PATHS = [DUT_PREPVT]
    # ===============================================================
    # Cr50 interrupt numbers reported in taskinfo
    IRQ_DICT = {
            4: 'HOST_CMD_DONE',
            81: 'GPIO0',
            98: 'GPIO1',
            103: 'I2CS WRITE',
            112: 'PMU WAKEUP',
            113: 'AC present FED',
            114: 'AC present RED',
            124: 'RBOX_INTR_PWRB',
            126: 'RDD',
            130: 'SPS CS deassert',
            138: 'SPS RXFIFO LVL',
            159: 'SPS RXFIFO overflow',
            160: 'EVENT TIMER',
            174: 'CR50_RX_SERVO_TX',
            177: 'CR50_TX_SERVO_RX',
            181: 'AP_TX_CR50_RX',
            184: 'AP_RX_CR50_TX',
            188: 'EC_TX_CR50_RX',
            191: 'EC_RX_CR50_TX',
            193: 'USB',
            201: 'SLOW_CALIB_OVERFLOW'
    }
    PRINT_IRQ_FMT = '    %3s %-20s %-10s'
    # USB, AP UART, and EC UART should be disabled if ccd is disabled.
    CCD_IRQS = [ 181, 184, 188, 191, 193 ]
    # Rdd and timer sof overflow IRQs
    CCD_CHANGE_IRQS = [126, 201]
    # Each line relevant taskinfo output should be 13 characters long with only
    # digits or spaces. Use this information to make sure every taskinfo command
    # gets the full relevant output. There are 4 characters for the irq number
    # and 9 for the count.
    GET_TASKINFO = ['IRQ counts by type:\s+(([\d ]{13}\r\n)+)Service calls']
    # Cr50 should wake up twice per second while in regular sleep
    SLEEP_RATE = 2
    # Cr50 will deep sleep after 20 seconds.
    DEEP_SLEEP_DELAY = 20
    # Maximum TPM init time.
    TPM_INIT_MAX = 120000
    TIME_SINCE_DS_RE = ' = (.*) s'
    TIME_SINCE_COLD_RESET_RE = 'since cold_reset: ([0-9]*) s'

    def __init__(self, servo, faft_config):
        """Initializes a ChromeCr50 object.

        @param servo: A servo object.
        @param faft_config: A faft config object.
        """
        super(ChromeCr50, self).__init__(servo, 'cr50_uart')
        self.faft_config = faft_config
        self.init_gsc_servo_caps()
        version = servo.get('gsc_version')
        if self.NAME not in version:
            raise error.TestError('%r not found in %r' % (self.NAME, version))
        logging.info('Setup %s console', self.NAME)

    def wake_console(self):
        """Wake up cr50 by sending some linebreaks and wait for the response"""
        for i in range(self.MAX_RETRY_COUNT):
            try:
                rv = super(ChromeCr50, self).send_command_get_output(
                        self.WAKE_CHAR, self.WAKE_RESPONSE)
                logging.debug('wake result %r', rv)
                return
            except servo.ResponsiveConsoleError as e:
                logging.info("Console responsive, but couldn't match wake "
                             "response %s", e)
        raise servo.ResponsiveConsoleError('Unable to wake cr50')


    def send_command(self, commands):
        """Send command through UART.

        Cr50 will drop characters input to the UART when it resumes from sleep.
        If servo is not using ccd, send some characters before sending the
        real command to make sure cr50 is awake.

        @param commands: the command string to send to cr50
        """
        if self._servo.main_device_is_flex():
            self.wake_console()
        super(ChromeCr50, self).send_command(commands)


    def set_cap(self, cap, setting):
        """Set the capability to setting

        @param cap: The capability string
        @param setting: The setting to set the capability to.
        """
        self.set_caps({ cap : setting })


    def set_caps(self, cap_dict):
        """Use cap_dict to set all the cap values

        Set all of the capabilities in cap_dict to the correct config.

        @param cap_dict: A dictionary with the capability as key and the desired
                         setting as values
        """
        for cap, config in six.iteritems(cap_dict):
            self.send_command('ccd set %s %s' % (cap, config))
        current_cap_settings = self.get_cap_dict(info=self.CAP_SETTING)
        for cap, config in six.iteritems(cap_dict):
            if (current_cap_settings[cap].lower() !=
                config.lower()):
                raise error.TestFail('Failed to set %s to %s' % (cap, config))


    def get_cap_overview(self, cap_dict):
        """Get a basic overview of the capability dictionary

        If all capabilities are set to Default, ccd has been reset to default.
        If all capabilities are set to Always, ccd is in factory mode.

        @param cap_dict: A dictionary of the capability settings
        @return: A tuple of the capability overview (in factory mode, is reset)
        """
        in_factory_mode = True
        is_reset = True
        for cap, cap_info in six.iteritems(cap_dict):
            cap_setting = cap_info[self.CAP_SETTING]
            if cap_setting != 'Always':
                in_factory_mode = False
            if cap_setting != 'Default':
                is_reset = False
        return in_factory_mode, is_reset


    def set_password(self, password):
        """Try to set the password. Should return Access Denied on prod images"""
        time.sleep(self.CCD_PASSWORD_RATE_LIMIT)
        rv = self.send_command_get_output('ccd password %s' % password,
                                          ['ccd.*>'])
        if self.CCD_PW_DENIED not in rv[0]:
            raise error.TestFail('%s not found in password response %r' %
                                 (self.CCD_PW_DENIED, rv))

    def password_is_reset(self):
        """Returns True if the password is cleared"""
        return self.get_ccd_info('Password') == 'none'


    def ccd_is_reset(self):
        """Returns True if the ccd is reset

        The password must be cleared, write protect and battery presence must
        follow battery presence, and all capabilities must be Always
        """
        return (self.password_is_reset() and self.wp_is_reset() and
                self.batt_pres_is_reset() and
                self.get_cap_overview(self.get_cap_dict())[1])

    def wp_follows_batt_pres(self):
        """Returns True if wp is reset to follow batt pres at all times"""
        wp_state = self.get_wp_state()
        follow_batt_pres = wp_state[0]
        follow_batt_pres_atboot = wp_state[2]
        return follow_batt_pres and follow_batt_pres_atboot

    def wp_is_reset(self):
        """Returns True if wp is reset to follow batt pres at all times

        Cr50 sets WP to follow battery present after ccd reset or
        factory mode disabled is called.
        """
        rv = self.wp_follows_batt_pres()
        logging.info('WP reset - WP follow batt pres: %s', rv)
        return rv

    def wp_is_forced_enabled(self):
        """Returns True if wp is forced enabled now and atboot"""
        wp_state = self.get_wp_state()
        follow_batt_pres = wp_state[0]
        enabled = wp_state[1]
        follow_batt_pres_atboot = wp_state[2]
        enabled_atboot = wp_state[3]
        if follow_batt_pres or follow_batt_pres_atboot:
            return False
        return enabled and enabled_atboot

    def get_wp_state(self):
        """Get the current write protect and atboot state

        The atboot setting cannot really be determined now if it is set to
        follow battery presence. It is likely to remain the same after reboot,
        but who knows. If the third element of the tuple is True, the last
        element will not be that useful

        @return: a tuple with the current write protect state
                (True if current state is to follow batt presence,
                 True if write protect is enabled,
                 True if current state is to follow batt presence atboot,
                 True if write protect is enabled atboot,
                 True if the fwmp is forcing wp)
        """
        rv = self.send_command_retry_get_output('wp', [
                'Flash WP: (fwmp )?(forced )?(enabled|disabled).*at boot: (fwmp )?(forced )?'
                '(follow|enabled|disabled)'
        ],
                                                safe=True)[0]
        _, fwmp, forced, enabled, _, _, atboot = rv
        logging.info(rv[0])
        return (not forced, enabled == 'enabled', atboot == 'follow',
                atboot == 'enabled', not not fwmp)

    def set_wp_state(self, setting):
        """Set the WP state."""
        self.send_command('wp ' + setting)
        time.sleep(self.SHORT_WAIT)
        return self.get_wp_state()

    def fwmp_forcing_wp(self):
        """Returns True if the FWMP is forcing WP."""
        return self.get_wp_state()[4]

    def in_dev_mode(self):
        """Return True if cr50 thinks the device is in dev mode"""
        return 'dev_mode' in self.get_ccd_info('TPM')


    def get_ccd_info(self, field=None):
        """Get the current ccd state.

        Take the output of 'ccd' and convert it to a dictionary.

        @param: the ccd info param to get or None to get the full ccd output
                dictionary.
        @return: the field value or a dictionary with the ccd field name as the
                 key and the setting as the value.
        """
        original_timeout = float(self._servo.get('cr50_uart_timeout'))
        # Change the console timeout to 10s, it may take longer than 3s to read
        # ccd info
        self._servo.set_nocheck('cr50_uart_timeout', self.CONSERVATIVE_CCD_WAIT)
        try:
            rv = self.send_command_retry_get_output('ccd', ['ccd.*>'],
                                                    safe=True,
                                                    compare_output=True)[0]
        finally:
            self._servo.set_nocheck('cr50_uart_timeout', original_timeout)
        ccd_output = {}
        k = None
        for line in rv.splitlines():
            if ':' in line:
                k, v = line.split(':')
                ccd_output[k] = [v.strip()]
            elif k == 'Capabilities':
                # The Capablitiy key has multiple lines.
                ccd_output[k].append(line)
        for k, v in six.iteritems(ccd_output):
            ccd_output[k] = '\n'.join(v)
        logging.info('Current CCD settings:\n%s', pprint.pformat(ccd_output))
        if field:
            return ccd_output.get(field)
        return ccd_output


    def get_cap(self, cap):
        """Returns the capabilitiy from the capability dictionary"""
        return self.get_cap_dict()[cap]


    def get_cap_dict(self, info=None):
        """Get the current ccd capability settings.

        The capability may be using the 'Default' setting. That doesn't say much
        about the ccd state required to use the capability. Return all ccd
        information in the cap_dict
        [is accessible, setting, requirement]

        @param info: Only fill the cap_dict with the requested information:
                     CAP_IS_ACCESSIBLE, CAP_SETTING, or CAP_REQ
        @return: A dictionary with the capability as the key a list of the
                 current settings as the value [is_accessible, setting,
                 requirement]
        """
        # Add whitespace at the end, so we can still match the last line.
        cap_strings = self.get_ccd_info('Capabilities').splitlines()
        caps = {}
        for line in cap_strings:
            if '=' not in line:
                continue
            logging.debug(line)
            # There are two capability formats. Match both.
            #  UartGscRxECTx   Y 3=IfOpened
            #  or
            #  UartGscRxECTx   Y 0=Default (Always)
            start, end = line.split('=')
            cap, accessible, _ = start.split()
            settings = re.findall(self.CAP_STATES, end)
            # The first setting is Default or the actual setting
            setting = settings[0]
            # The last setting is the actual setting
            required = settings[-1]
            cap_info = [accessible == 'Y', setting, required]
            if info is not None:
                caps[cap] = cap_info[info]
            else:
                caps[cap] = cap_info
        logging.info(pprint.pformat(caps))
        return caps


    def send_command_get_output(self, command, regexp_list):
        """Send command through UART and wait for response.

        Cr50 will drop characters input to the UART when it resumes from sleep.
        If servo is not using ccd, send some characters before sending the
        real command to make sure cr50 is awake.

        @param command: the command to send
        @param regexp_list: The list of regular expressions to match in the
                            command output
        @return: A list of matched output
        """
        if self._servo.main_device_is_flex():
            self.wake_console()

        # We have started prepending '\n' to separate cr50 console junk from
        # the real command. If someone is just searching for .*>, then they will
        # only get the output from the first '\n' we added. Raise an error to
        # change the test to look for something more specific ex command.*>.
        # cr50 will print the command in the output, so that is an easy way to
        # modify '.*>' to match the real command output.
        if '.*>' in regexp_list:
            raise error.TestError('Send more specific regexp %r %r' % (command,
                    regexp_list))

        # prepend \n to separate the command from any junk that may have been
        # sent to the cr50 uart.
        command = '\n' + command
        return super(ChromeCr50, self).send_command_get_output(command,
                                                               regexp_list)


    def send_safe_command_get_output(self, command, regexp_list,
            channel_mask=0x1):
        """Restrict the console channels while sending console commands.

        @param command: the command to send
        @param regexp_list: The list of regular expressions to match in the
                            command output
        @param channel_mask: The mask to pass to 'chan' prior to running the
                             command, indicating which channels should remain
                             enabled (0x1 is command output)
        @return: A list of matched output
        """
        self.send_command('chan save')
        self.send_command('chan 0x%x' % channel_mask)
        try:
            rv = self.send_command_get_output(command, regexp_list)
        finally:
            self.send_command('chan restore')
        return rv


    def send_command_retry_get_output(self, command, regexp_list, safe=False,
                                      compare_output=False, retries=MAX_RETRY_COUNT):
        """Retry the command 5 times if you get a timeout or drop some output


        @param command: the command string
        @param regexp_list: the regex to search for
        @param safe: use send_safe_command_get_output if True otherwise use
                     send_command_get_output
        @param compare_output: look for reproducible output
        """
        send_command = (self.send_safe_command_get_output if safe else
                        self.send_command_get_output)
        err = 'no consistent output' if compare_output else 'unknown'
        past_rv = []
        for i in range(retries):
            try:
                rv = send_command(command, regexp_list)
                if not compare_output or rv in past_rv:
                    return rv
                if past_rv:
                    logging.debug('%d %s not in %s', i, rv, past_rv)
                past_rv.append(rv)
            except Exception as e:
                err = e
                logging.info('attempt %d %r: %s %s', i, command, type(e),
                             str(e))
        if compare_output:
            logging.info('No consistent output for %r %s', command,
                         pprint.pformat(past_rv))
        raise error.TestError('Issue sending %r command: %r' % (command, err))


    def get_deep_sleep_count(self):
        """Get the deep sleep count from the idle task"""
        result = self.send_command_retry_get_output('idle', [self.IDLE_COUNT],
                                                    safe=True)
        return int(result[0][1])


    def clear_deep_sleep_count(self):
        """Clear the deep sleep count"""
        self.send_command('idle c')
        if self.get_deep_sleep_count():
            raise error.TestFail("Could not clear deep sleep count")


    def get_board_properties(self):
        """Get information from the version command"""
        rv = self.send_command_retry_get_output('brdprop',
                ['properties = (\S+)\s'], safe=True)
        return int(rv[0][1], 16)


    def uses_board_property(self, prop_name):
        """Returns 1 if the given property is set, or 0 otherwise

        @param prop_name: a property name in string type.
        """
        # Ti50 and Cr50 configure different board properties differently.
        # Some may be always true for Ti50. They won't show up in the board
        # property value.
        if prop_name in self.BOARD_PROP_ALWAYS_TRUE:
            logging.info('%s is not configured by brdprop', prop_name)
            return True
        brdprop = self.get_board_properties()
        (prop, mask) = self.BOARD_PROP[prop_name]
        # Use the board property value for the mask if no mask is given.
        mask = mask or prop
        return (brdprop & mask) == prop


    def has_command(self, cmd):
        """Returns 1 if cr50 has the command 0 if it doesn't"""
        try:
            self.send_command_retry_get_output('help', [cmd],
                                               safe=True,
                                               retries=3)
        except:
            logging.info("Image does not include '%s' command", cmd)
            return 0
        return 1


    def reboot(self):
        """Reboot Cr50 and wait for cr50 to reset"""
        self.wait_for_reboot(cmd='reboot', timeout=10)


    def _uart_wait_for_reboot(self, cmd='\n', timeout=60):
        """Use uart to wait for cr50 to reboot.

        If a command is given run it and wait for cr50 to reboot. Monitor
        the cr50 uart to detect the reset. Wait up to timeout seconds
        for the reset.

        @param cmd: the command to run to reset cr50.
        @param timeout: seconds to wait to detect the reboot.
        """
        original_timeout = float(self._servo.get('cr50_uart_timeout'))
        # Change the console timeout to timeout, so we wait at least that long
        # for cr50 to print the start string.
        self._servo.set_nocheck('cr50_uart_timeout', timeout)
        try:
            rv = self.send_command_get_output(cmd, self.START_STR)
            logging.debug('Detected cr50 reboot %s', rv[0][0])
        except error.TestFail as e:
            logging.debug('Failed to detect cr50 reboot')
        # Reset the timeout.
        self._servo.set_nocheck('cr50_uart_timeout', original_timeout)


    def wait_for_reboot(self, cmd='\n', timeout=60):
        """Wait for cr50 to reboot

        Run the cr50 reset command. Wait for cr50 to reset and reenable ccd if
        necessary.

        @param cmd: the command to run to reset cr50.
        @param timeout: seconds to wait to detect the reboot.
        """
        logging.info('Wait up to %s seconds for reboot (%s)', timeout,
                     cmd.strip())
        if self._servo.main_device_is_ccd():
            self.send_command(cmd)
            # Cr50 USB is reset when it reboots. Wait for the CCD connection to
            # go down to detect the reboot.
            self.wait_for_ccd_disable(timeout, raise_error=False)
            self.ccd_enable()
        else:
            self._uart_wait_for_reboot(cmd, timeout)

        # On most devices, a Cr50 reset will cause an AP reset. Force this to
        # happen on devices where the AP is left down.
        if not self.faft_config.ap_up_after_cr50_reboot:
            # Reset the DUT a few seconds after cr50 reboot.
            time.sleep(self.SHORT_WAIT)
            logging.info('Resetting DUT after Cr50 reset')
            self._servo.get_power_state_controller().reset()


    def set_board_id(self, chip_bid, chip_flags):
        """Set the chip board id type and flags."""
        self.send_command('bid 0x%x 0x%x' % (chip_bid, chip_flags))


    def get_board_id(self):
        """Get the chip board id type and flags.

        bid_type_inv will be '' if the bid output doesn't show it. If no board
        id type inv is shown, then board id is erased will just check the type
        and flags.

        @returns a tuple (A string of bid_type:bid_type_inv:bid_flags,
                          True if board id is erased)
        """
        bid = self.send_command_retry_get_output('bid', [self.BID_RE],
                                                 safe=True)[0][1:]
        bid_str = ':'.join(bid)
        bid_is_erased =  set(bid).issubset({'', 'ffffffff'})
        logging.info('chip board id: %s', bid_str)
        logging.info('chip board id is erased: %s',
                     'yes' if bid_is_erased else 'no')
        return bid_str, bid_is_erased


    def eraseflashinfo(self, retries=10):
        """Run eraseflashinfo.

        @returns True if the board id is erased
        """
        for i in range(retries):
            # The console could drop characters while matching 'eraseflashinfo'.
            # Retry if the command times out. It's ok to run eraseflashinfo
            # multiple times.
            rv = self.send_command_retry_get_output(
                    self.EFI_CMD, [self.EFI_CMD + '(.*)>'])[0][1].strip()
            logging.info('eraseflashinfo output: %r', rv)
            bid_erased = self.get_board_id()[1]
            eraseflashinfo_issue = 'Busy' in rv or 'do_flash_op' in rv
            if not eraseflashinfo_issue and bid_erased:
                break
            logging.info('Retrying eraseflashinfo')
        return bid_erased


    def clear_rollback(self):
        """Clear the rollback counter and reboot."""
        if not self.has_command('clear_rollback'):
            logging.info('gsc does not have clear_rollback')
            return
        self.wait_for_reboot(cmd='clear_rollback', timeout=10)

    def rollback(self):
        """Set the reset counter high enough to force a rollback and reboot."""
        if not self.has_command('rollback'):
            raise error.TestError("need image with 'rollback'")

        inactive_partition = self.get_inactive_version_info()[0]

        self.wait_for_reboot(cmd='rollback', timeout=10)

        running_partition = self.get_active_version_info()[0]
        if inactive_partition != running_partition:
            raise error.TestError("Failed to rollback to inactive image")


    def rolledback(self):
        """Returns true if cr50 just rolled back"""
        return 'Rollback detected' in self.send_command_retry_get_output(
                'sysinfo', ['sysinfo.*>'], safe=True)[0]


    def get_version_info(self, regexp):
        """Get information from the version command"""
        return self.send_command_retry_get_output('version', [regexp],
                                                  safe=True,
                                                  compare_output=True)[0][1::]


    def get_inactive_version_info(self):
        """Get the active partition, version, and hash"""
        return self.get_version_info(self.INACTIVE_VERSION)


    def get_active_version_info(self):
        """Get the active partition, version, and hash"""
        return self.get_version_info(self.ACTIVE_VERSION)


    def get_ro_active_version_info(self):
        """Get the active partition, version, and hash"""
        return self.get_version_info(self.RO_ACTIVE_VERSION)

    def using_prod_rw_keys(self):
        """Returns True if the RW keyid is prod"""
        rv = self.send_command_retry_get_output('sysinfo',
                ['RW keyid:\s+(0x[0-9a-f]{8})'], safe=True)[0][1]
        logging.info('RW Keyid: 0x%s', rv)
        return rv in self.PROD_RW_KEYIDS


    def get_active_board_id_str(self):
        """Get the running image board id.

        @return: The board id string or None if the image does not support board
                 id or the image is not board id locked.
        """
        # Getting the board id from the version console command is only
        # supported in board id locked images .22 and above. Any image that is
        # board id locked will have support for getting the image board id.
        #
        # If board id is not supported on the device, return None. This is
        # still expected on all current non board id locked release images.
        try:
            version_info = self.get_version_info(self.ACTIVE_BID)
        except error.TestFail as e:
            logging.info(str(e))
            logging.info('Cannot use the version to get the board id')
            return None

        if self.BID_ERROR in version_info[4]:
            raise error.TestError(version_info)
        bid = version_info[4].split()[1]
        return cr50_utils.GetBoardIdInfoString(bid)


    def get_version(self):
        """Get the RW version"""
        return self.get_active_version_info()[1].strip()

    def get_ro_version(self):
        """Get the RW version"""
        return self.get_ro_active_version_info()[1].strip()

    def running_mp_image(self):
        """Returns True if gsc is running a mp image"""
        major = int(self.get_version().split('.')[1])
        return bool(major % 2)

    def get_full_version(self):
        """Get the complete RW version string."""
        _, rw_ver, dbg, ver_str = self.get_active_version_info()
        return  rw_ver + (dbg if dbg else '') + ver_str

    def get_full_ro_version(self):
        """Get the complete RW version string."""
        _, ro_ver, dbg, ver_str = self.get_ro_active_version_info()
        return ro_ver + (dbg if dbg else '') + ver_str

    def ccd_is_enabled(self):
        """Return True if ccd is enabled.

        If the test is running through ccd, the console won't be available when
        ccd is disconnected. Use the watchdog state to check if ccd is enabled.
        If a flex cable is being used, use the CCD_MODE_L gpio setting to
        determine the ccd state.

        @return: True if ccd is enabled. False if it's disabled.
        """
        if self._servo.main_device_is_ccd():
            return bool(re.search(self.CCD_CONNECTED_RE,
                                  self._servo.get('watchdog')))
        return not bool(self.gpioget('CCD_MODE_L'))

    @dts_control_command
    def wait_for_stable_ccd_state(self, state, timeout, raise_error):
        """Wait up to timeout seconds for CCD to be 'on' or 'off'

        Verify ccd is off or on and remains in that state for 3 seconds.

        @param state: a string either 'on' or 'off'.
        @param timeout: time in seconds to wait
        @param raise_error: Raise TestFail if the value is state is not reached.
        @raise TestFail: if ccd never reaches the specified state
        """
        wait_for_enable = state == 'on'
        logging.info("Wait until ccd is %s", 'on' if wait_for_enable else 'off')
        enabled = utils.wait_for_value(self.ccd_is_enabled, wait_for_enable,
                                       timeout_sec=timeout)
        if enabled != wait_for_enable:
            error_msg = ("timed out before detecting ccd '%s'" %
                         ('on' if wait_for_enable else 'off'))
            if raise_error:
                raise error.TestFail(error_msg)
            logging.warning(error_msg)
        else:
            # Make sure the state doesn't change.
            enabled = utils.wait_for_value(self.ccd_is_enabled, not enabled,
                                           timeout_sec=self.SHORT_WAIT)
            if enabled != wait_for_enable:
                error_msg = ("CCD switched %r after briefly being %r" %
                             ('on' if enabled else 'off', state))
                if raise_error:
                    raise error.TestFail(error_msg)
                logging.info(error_msg)
        logging.info("ccd is %r", 'on' if enabled else 'off')


    @dts_control_command
    def wait_for_ccd_disable(self, timeout=60, raise_error=True):
        """Wait for the cr50 console to stop working"""
        self.wait_for_stable_ccd_state('off', timeout, raise_error)


    @dts_control_command
    def wait_for_ccd_enable(self, timeout=60, raise_error=False):
        """Wait for the cr50 console to start working"""
        self.wait_for_stable_ccd_state('on', timeout, raise_error)


    @dts_control_command
    def ccd_disable(self, raise_error=True):
        """Change the values of the CC lines to disable CCD"""
        logging.info("disable ccd")
        self._servo.set_dts_mode('off')
        self.wait_for_ccd_disable(raise_error=raise_error)


    @dts_control_command
    def ccd_enable(self, raise_error=False):
        """Reenable CCD and reset servo interfaces"""
        logging.info("reenable ccd")
        self._servo.set_dts_mode('on')
        # If the test is actually running with ccd, wait for USB communication
        # to come up after reset.
        if self._servo.main_device_is_ccd():
            time.sleep(self._servo.USB_DETECTION_DELAY)
        self.wait_for_ccd_enable(raise_error=raise_error)

    def open_req_physical_presence(self):
        """Returns False if physical presence capabilities are set to Always."""
        return (not self.cap_is_always_on('UnlockNoShortPP')
                or not self.cap_is_always_on('OpenNoLongPP'))

    def _get_physical_presence_duration(self, level):
        """Returns the amount of time to press the power button"""
        if level == 'testlab open' or level == self.LOCK:
            return 0
        if 'testlab' in level:
            return self.PP_SHORT
        dbg_en = self.get_active_version_info()[2]
        # DBG images never require 5 minutes to open ccd. They only use short
        # physical presence.
        long_pp = self.PP_SHORT if dbg_en else self.PP_LONG
        caps = self.get_cap_dict()
        # If the level is open and the ccd capabilities say physical presence
        # is required, then physical presence will be required.
        if level == 'open' and not caps['OpenNoLongPP'][
                self.CAP_IS_ACCESSIBLE]:
            return long_pp
        if not caps[self.CAP_SHORT_PP][self.CAP_IS_ACCESSIBLE]:
            return self.PP_SHORT
        return 0


    def _state_to_bool(self, state):
        """Converts the state string to True or False"""
        # TODO(mruthven): compare to 'on' once servo is up to date in the lab
        return state.lower() in self.ON_STRINGS


    def testlab_is_on(self):
        """Returns True of testlab mode is on"""
        return self._state_to_bool(self._servo.get('cr50_testlab'))


    def set_ccd_testlab(self, state):
        """Set the testlab mode

        @param state: the desired testlab mode string: 'on' or 'off'
        @raise TestFail: if testlab mode was not changed
        """
        if self._servo.main_device_is_ccd():
            raise error.TestError('Cannot set testlab mode with CCD. Use flex '
                    'cable instead.')
        if not self.faft_config.has_powerbutton:
            raise error.TestError('No power button on device')

        request_on = self._state_to_bool(state)
        testlab_on = self.testlab_is_on()
        request_str = 'on' if request_on else 'off'

        if testlab_on == request_on:
            logging.info('ccd testlab already set to %s', request_str)
            return

        original_level = self.get_ccd_level()

        # We can only change the testlab mode when the device is open. If
        # testlab mode is already enabled, we can go directly to open using 'ccd
        # testlab open'. This will save 5 minutes, because we can skip the
        # physical presence check.
        if testlab_on:
            self.send_command('ccd testlab open')
        else:
            self.set_ccd_level('open')

        ap_is_on = self.ap_is_on()
        # Set testlab mode
        rv = self.send_command_get_output('ccd testlab %s' % request_str,
                ['ccd.*>'])[0]
        if 'Access Denied' in rv:
            raise error.TestFail("'ccd %s' %s" % (request_str, rv))

        # Press the power button once a second for 15 seconds. If the AP is
        # currently on, make sure it's on at the end of the open process.
        self.run_pp(self.PP_SHORT, ensure_ap_on=ap_is_on)

        self.set_ccd_level(original_level)
        if request_on != self.testlab_is_on():
            raise error.TestFail('Failed to set ccd testlab to %s' % state)


    def get_ccd_level(self):
        """Returns the current ccd privilege level"""
        return self.get_ccd_info('State').lower().rstrip('ed')


    def set_ccd_level(self, level, password=''):
        """Set the Cr50 CCD privilege level.

        @param level: a string of the ccd privilege level: 'open', 'lock', or
                      'unlock'.
        @param password: send the ccd command with password. This will still
                         require the same physical presence.
        @raise TestFail: if the level couldn't be set
        """
        level = level.lower()

        if level == self.get_ccd_level():
            logging.info('CCD privilege level is already %s', level)
            return

        if 'testlab' in level:
            raise error.TestError("Can't change testlab mode using "
                "ccd_set_level")

        testlab_on = self._state_to_bool(self._servo.get('cr50_testlab'))
        batt_is_connected = self.get_batt_pres_state()[1]
        pp_duration = self._get_physical_presence_duration(level)
        can_reopen = (not self._servo.main_device_is_ccd()
                      or not self.open_req_physical_presence())
        logging.info('setting ccd %r', level)
        logging.info('physical presence: %d', pp_duration)

        if pp_duration and not can_reopen:
            raise error.TestError("Can't change privilege level to '%s' "
                "without physical presence." % level)

        if not testlab_on and not can_reopen:
            raise error.TestError("Wont change privilege level without "
                "physical presence or testlab mode enabled")

        original_timeout = float(self._servo.get('cr50_uart_timeout'))
        # Change the console timeout to CONSERVATIVE_CCD_WAIT, running 'ccd' may
        # take more than 3 seconds.
        self._servo.set_nocheck('cr50_uart_timeout', self.CONSERVATIVE_CCD_WAIT)
        # Start the unlock process.

        if level == 'open' or level == 'unlock':
            logging.info('waiting %d seconds, the minimum time between'
                         ' ccd password attempts',
                         self.CCD_PASSWORD_RATE_LIMIT)
            time.sleep(self.CCD_PASSWORD_RATE_LIMIT)
        else:
            # 'lock' does not accept a password, so don't provide one.
            password = ''

        ap_is_on = self.ap_is_on()
        try:
            cmd = 'ccd %s%s' % (level, (' ' + password) if password else '')
            # ccd command outputs on the rbox, ccd, and console channels,
            # respectively. Cr50 uses these channels to print relevant ccd
            # information.
            # Restrict all other channels.
            ccd_output_channels = 0x20000 | 0x8 | 0x1
            logging.info('sending %r', cmd)
            rv = self.send_safe_command_get_output(
                    cmd, ['ccd(.*)>'],
                    channel_mask=ccd_output_channels)[0][1]
        finally:
            self._servo.set('cr50_uart_timeout', original_timeout)
        logging.info(rv)
        if ('ccd_open denied: fwmp' in rv or 'Blocked by fwmp' in rv):
            raise error.TestFail('FWMP disabled %r: %s' % (cmd, rv))
        if 'Access Denied' in rv:
            raise error.TestFail("%r %s" % (cmd, rv))
        if 'Busy' in rv:
            raise error.TestFail("cr50 is too busy to run %r: %s" % (cmd, rv))

        # Press the power button once a second, if we need physical presence.
        if pp_duration and batt_is_connected:
            # If the AP is currently on, make sure it's on at the end of the
            # open process.
            self.run_pp(pp_duration, ensure_ap_on=ap_is_on)

        if level != self.get_ccd_level():
            self.check_for_console_errors('Running console ccd %s' % level)
            raise error.TestFail('Could not set privilege level to %s' % level)

        logging.info('Successfully set CCD privelege level to %s', level)


    def run_pp(self, unlock_timeout, ensure_ap_on=False):
        """Press the power button a for unlock_timeout seconds.

        This will press the power button many more times than it needs to be
        pressed. Cr50 doesn't care if you press it too often. It just cares that
        you press the power button at least once within the detect interval.

        For privilege level changes you need to press the power button 5 times
        in the short interval and then 4 times within the long interval.
        Short Interval
        100msec < power button press < 5 seconds
        Long Interval
        60s < power button press < 300s

        For testlab enable/disable you must press the power button 5 times
        spaced between 100msec and 5 seconds apart.

        @param unlock_timeout: time to press the power button in seconds.
        @param ensure_ap_on: If true, press the power to turn on the AP.
        """
        end_time = time.time() + unlock_timeout

        logging.info('Pressing power button for %ds', unlock_timeout)
        logging.info('The process should end at %s', time.ctime(end_time))

        # Press the power button once every PP_SHORT_INT to unlock the console.
        while time.time() < end_time:
            self._servo.power_short_press()
            time.sleep(self.PP_SHORT_INT)

        # If the last power button press left the AP powered off, and it was on
        # before, turn it back on.
        # TODO(b/151156740): This sleep is too long, and probably unneeded.
        time.sleep(self.faft_config.shutdown)
        if ensure_ap_on and not self.ap_is_on():
            logging.info('AP is off. Pressing the power button to turn it on')
            self._servo.power_short_press()
            logging.debug('Pressing PP to turn back on')


    def send_gettime_cmd_get_output(self, regex, raise_error=True):
        """Send get time command."""
        rv = self.send_command_retry_get_output('gettime', ['gettime(.*)>'],
                                                safe=True)[0][1]
        m = re.search(regex, rv)
        if m is not None:
            return float(m.group(1))
        # TODO: always raise an error when cr50 has time since cold reset
        # support.
        err = 'Did not find %r in gettime output: %s' % (regex, rv)
        if raise_error:
            raise error.TestError(err)
        logging.warning(err)
        return 0

    def gettime_since_cold_reset(self):
        """Get the time since the last cold reset"""
        rv = self.send_gettime_cmd_get_output(self.TIME_SINCE_COLD_RESET_RE,
                                              False)
        logging.info('Time since cold reset: %r', rv)
        return rv

    def gettime(self):
        """Get the time since the last wake from deep sleep or reset"""
        rv = self.send_gettime_cmd_get_output(self.TIME_SINCE_DS_RE)
        logging.info('Time since last reset: %r', rv)
        return rv

    def servo_dts_mode_is_valid(self):
        """Returns True if cr50 registers change in servo dts mode."""
        # This is to test that Cr50 actually recognizes the change in ccd state
        # We cant do that with tests using ccd, because the cr50 communication
        # goes down once ccd is enabled.
        if not self._servo.dts_mode_is_safe():
            return False

        ccd_start = 'on' if self.ccd_is_enabled() else 'off'
        dts_start = self._servo.get_dts_mode()
        try:
            # Verify both ccd enable and disable
            self.ccd_disable(raise_error=True)
            self.ccd_enable(raise_error=True)
            rv = True
        except Exception as e:
            logging.info(e)
            rv = False
        self._servo.set_dts_mode(dts_start)
        self.wait_for_stable_ccd_state(ccd_start, 60, True)
        logging.info('Test setup does%s support servo DTS mode',
                '' if rv else 'n\'t')
        return rv


    def wait_until_update_is_allowed(self):
        """Wait until cr50 will be able to accept an update.

        Cr50 rejects any attempt to update if it has been less than 60 seconds
        since it last recovered from deep sleep or came up from reboot. This
        will wait until cr50 gettime shows a time greater than 60.
        """
        if self.get_active_version_info()[2]:
            logging.info("Running DBG image. Don't need to wait for update.")
            return
        cr50_time = self.gettime()
        if cr50_time < 60:
            sleep_time = 61 - cr50_time
            logging.info('Cr50 has been up for %ds waiting %ds before update',
                         cr50_time, sleep_time)
            time.sleep(sleep_time)


    def tpm_is_enabled(self):
        """Query the current TPM mode.

        @return:  True if TPM is enabled, False otherwise.
        """
        result = self.send_command_retry_get_output('sysinfo',
                ['(?i)TPM\s+MODE:\s+(enabled|disabled)'], safe=True)[0][1]
        logging.debug(result)

        return result.lower() == 'enabled'


    def get_keyladder_state(self):
        """Get the status of H1 Key Ladder.

        @return: The keyladder state string. prod or dev both mean enabled.
        """
        result = self.send_command_retry_get_output('sysinfo',
                ['(?i)Key\s+Ladder:\s+(enabled|prod|dev|disabled)'],
                safe=True)[0][1]
        logging.debug(result)
        return result


    def keyladder_is_disabled(self):
        """Get the status of H1 Key Ladder.

        @return: True if H1 Key Ladder is disabled. False otherwise.
        """
        return self.get_keyladder_state() == 'disabled'


    def get_sleepmask(self):
        """Returns the sleepmask as an int"""
        rv = self.send_command_retry_get_output('sleepmask',
                ['sleep mask: (\S{8})\s+'], safe=True)[0][1]
        logging.info('sleepmask %s', rv)
        return int(rv, 16)


    def get_ccdstate(self):
        """Return a dictionary of the ccdstate once it's done debouncing"""
        for i in range(self.CCDSTATE_MAX_RETRY_COUNT):
            rv = self.send_command_retry_get_output('ccdstate',
                    ['ccdstate(.*)>'], safe=True, compare_output=True)[0][0]

            # Look for a line like 'AP: on' or 'AP: off'. 'debouncing' or
            # 'unknown' may appear transiently. 'debouncing' should transition
            # to 'on' or 'off' within 1 second, and 'unknown' should do so
            # within 20 seconds.
            if 'debouncing' not in rv and 'unknown' not in rv:
                break
            time.sleep(self.SHORT_WAIT)
        ccdstate = {}
        for line in rv.splitlines():
            line = line.strip()
            if ':' in line:
                k, v = line.split(':', 1)
                k = k.strip()
                v = v.strip()
                if '(' in v:
                    ccdstate[k + self.CCDSTATE_FULL_EXT] = v
                    v = v.split('(')[0].strip()
                ccdstate[k] = v
        logging.info('Current CCD state:\n%s', pprint.pformat(ccdstate))
        return ccdstate


    def ccdstate_ds_disabled(self):
        """Returns True if "DS Dis" is on.

        @return: True if ds is disabled; False otherwise.
        """
        # This will return false if "DS Dis" isn't the dictionary. If "DS Dis"
        # isn't in the dictionary, then that feature isn't supported and the
        # AP can't disable deep sleep.
        return self.get_ccdstate().get('DS Dis', '').lower() == 'on'

    def ap_is_on(self):
        """Get the power state of the AP.

        @return: True if the AP is on; False otherwise.
        """
        ap_state = self.get_ccdstate()['AP']
        if ap_state.lower() == 'on':
            return True
        elif ap_state.lower() == 'off':
            return False
        else:
            raise error.TestFail('Read unusable AP state from ccdstate: %r' %
                                 ap_state)


    def gpioget(self, signal_name):
        """Get the current state of the signal

        @return an integer 1 or 0 based on the gpioget value
        """
        result = self.send_command_retry_get_output(
                'gpioget', ['(0|1)[ *]+%s' % signal_name], safe=True)
        return int(result[0][1])


    def batt_pres_is_reset(self):
        """Returns True if batt pres is reset to always follow batt pres"""
        follow_bp, _, follow_bp_atboot, _ = self.get_batt_pres_state()
        return follow_bp and follow_bp_atboot


    def get_batt_pres_state(self):
        """Get the current and atboot battery presence state

        The atboot setting cannot really be determined now if it is set to
        follow battery presence. It is likely to remain the same after reboot,
        but who knows. If the third element of the tuple is True, the last
        element will not be that useful

        @return: a tuple of the current battery presence state
                 (True if current state is to follow batt presence,
                  True if battery is connected,
                  True if current state is to follow batt presence atboot,
                  True if battery is connected atboot)
        """
        # bpforce is added in 4.16. If the image doesn't have the command, cr50
        # always follows battery presence. In these images 'gpioget BATT_PRES_L'
        # accurately represents the battery presence state, because it can't be
        # overidden.
        if not self.has_command('bpforce'):
            batt_pres = not bool(self.gpioget('BATT_PRES_L'))
            return (True, batt_pres, True, batt_pres)

        # The bpforce command is very similar to the wp command. It just
        # substitutes 'connected' for 'enabled' and 'disconnected' for
        # 'disabled'.
        rv = self.send_command_retry_get_output('bpforce',
                ['batt pres: (forced )?(con|dis).*at boot: (forced )?'
                 '(follow|discon|con)'], safe=True)[0]
        _, forced, connected, _, atboot = rv
        logging.info(rv)
        return (not forced, connected == 'con', atboot == 'follow',
                atboot == 'con')


    def set_batt_pres_state(self, state, atboot):
        """Override the battery presence state.

        @param state: a string of the battery presence setting: 'connected',
                  'disconnected', or 'follow_batt_pres'
        @param atboot: True if we're overriding battery presence atboot
        """
        cmd = 'bpforce %s%s' % (state, ' atboot' if atboot else '')
        logging.info('running %r', cmd)
        self.send_command(cmd)


    def dump_nvmem(self):
        """Print nvmem objects."""
        rv = self.send_command_retry_get_output('dump_nvmem',
                                                ['dump_nvmem(.*)>'],
                                                safe=True)[0][1]
        logging.info('NVMEM OUTPUT:\n%s', rv)


    def get_reset_cause(self):
        """Returns the reset flags for the last reset."""
        rv = self.send_command_retry_get_output('sysinfo',
                ['Reset flags:\s+0x([0-9a-f]{8})\s'], compare_output=True)[0][1]
        logging.info('reset cause: %s', rv)
        return int(rv, 16)


    def was_reset(self, reset_type):
        """Returns 1 if the reset type is found in the reset_cause.

        @param reset_type: reset name in string type.
        """
        reset_cause = self.get_reset_cause()
        reset_flag = self.RESET_FLAGS[reset_type]
        return bool(reset_cause & reset_flag)


    def get_devid(self):
        """Returns the cr50 serial number."""
        return self.send_command_retry_get_output('sysinfo',
                ['DEV_ID:\s+(0x[0-9a-f]{8} 0x[0-9a-f]{8})'])[0][1]


    def get_serial(self):
        """Returns the cr50 serial number."""
        serial = self.get_devid().replace('0x', '').replace(' ', '-').upper()
        logging.info('CCD serial: %s', serial)
        return serial

    def check_boot_mode(self, mode_exp='NORMAL'):
        """Query the boot mode to Cr50, and compare it against mode_exp.

        Args:
            mode_exp: expecting boot mode. It should be either 'NORMAL'
                      or 'NO_BOOT'.
        Returns:
            True if the boot mode matches mode_exp.
            False, otherwise.
        Raises:
            TestError: Input parameter is not valid.
        """

        if mode_exp not in ['NORMAL', 'NO_BOOT']:
            raise error.TestError('parameter, mode_exp is not valid: %s' %
                                  mode_exp)
        rv = self.send_command_retry_get_output('ec_comm',
                ['boot_mode\s*:\s*(NORMAL|NO_BOOT)'], safe=True)
        return mode_exp == rv[0][1]

    def get_reset_count(self):
        """Returns the cr50 reset count"""
        return self.send_command_retry_get_output('sysinfo',
                                                  ['Reset count: (\d+)'],
                                                  safe=True)[0][1]

    def check_servo_monitor(self):
        """Returns True if cr50 can detect servo connect/disconnect"""
        # CCD devices can't simulate servo disconnect, because they cant access
        # the servo EC uart signal.
        if self._servo.main_device_is_ccd():
            return False
        orig_dts = self._servo.get('servo_dts_mode')
        # Detach ccd so EC uart won't interfere with servo detection
        self._servo.set_dts_mode('off')
        self._servo.set('ec_uart_en', 'off')
        time.sleep(self.SHORT_WAIT)
        if self.get_ccdstate()['Servo'] != 'disconnected':
            self._servo.set_dts_mode(orig_dts)
            return False

        self._servo.set('ec_uart_en', 'on')
        time.sleep(self.SHORT_WAIT)
        if self.get_ccdstate()['Servo'] != 'connected':
            self._servo.set_dts_mode(orig_dts)
            return False
        self._servo.set_dts_mode(orig_dts)
        return True

    def fips_crypto_allowed(self):
        """Return 1 if fips crypto is enabled."""
        if not self.has_command('fips'):
            return 0

        rv = self.send_command_retry_get_output('fips', [self.FIPS_RE])
        logging.info('FIPS: %r', rv)
        _, approved, allowed = rv[0]
        if int(approved == '') != int(allowed):
            raise error.TestFail('Approved does not match allowed %r' % rv)
        return int(allowed)

    def unlock_is_supported(self):
        """Returns True if GSC supports the ccd unlock state."""
        return True

    def cap_is_always_on(self, cap):
        """Returns True if the capability is set to Always"""
        rv = self.send_command_retry_get_output('ccd',
                                                [cap + self.CAP_FORMAT])[0]
        # "Always" must show up in the capability line.
        return self.CAP_ALWAYS in rv[0]

    def init_gsc_servo_caps(self):
        """Save a list of the capabilities needed for servo to work."""
        servo_class = self._servo.get_main_servo_device().split('_')[0]
        logging.info('Looking up %r gsc capabilities', servo_class)
        self._gsc_servo_caps = self.UNIVERSAL_SERVO_REQ_CAPS
        self._gsc_servo_caps.extend(self.SERVO_SPECIFIC_REQ_CAPS[servo_class])
        logging.info('Required caps: %s', self._gsc_servo_caps)

    def servo_drv_enabled(self):
        """Check if the caps  are accessible on boards wigh gsc controls."""
        if not self._gsc_servo_caps:
            return True
        for cap in self._gsc_servo_caps:
            # If any capability isn't accessible, return False.
            if not self.cap_is_always_on(cap):
                return False
        return True

    def has_servo_control_caps(self):
        """Returns True if any capabilities are required to run the test."""
        return not not self._gsc_servo_caps

    def enable_servo_control_caps(self):
        """Set all servo control capabilities to Always."""
        # Nothing do do if servo doesn't use gsc for any controls.
        if not self.has_servo_control_caps():
            return
        logging.info('Setting servo caps to Always')
        self.send_command('ccd testlab open')
        for cap in self._gsc_servo_caps:
            self.send_command('ccd set %s Always' % cap)
        return self.servo_drv_enabled()

    def ccd_reset_factory(self):
        """Enable factory mode."""
        self.send_command('ccd reset factory')

    def ccd_reset(self, servo_en=True):
        """Reset ccd capabilities."""
        req_caps = self.has_servo_control_caps()
        # If testlab mode is enabled, capabilities can be restored. It's
        # ok to reset ccd.
        if not servo_en and req_caps and not self.testlab_is_on():
            raise error.TestError(
                    'Board uses ccd drivers. Enable testlab mode '
                    'before ccd reset')
        self.send_command('ccd reset')
        if servo_en:
            self.enable_servo_control_caps()

    def check_for_console_errors(self, desc, error_strings=None):
        """Check cr50 uart output for errors.

        Use the logs captured during firmware_test cleanup to check for cr50
        errors. Flash operation issues aren't obvious unless you check the logs.
        All flash op errors print do_flash_op and it isn't printed during normal
        operation. Open the cr50 uart file and count the number of times this is
        printed. Log the number of errors.
        """
        self.dump_nvmem()
        self._servo.record_uart_capture()
        cr50_uart_file = self._servo.get_uart_logfile('cr50')
        if not cr50_uart_file:
            logging.info('There is not a cr50 uart file')
            return

        if error_strings == None:
            error_strings = self.ERROR_DESC_LIST

        error_counts = [0 for i in range(len(error_strings))]
        with open(cr50_uart_file, 'r') as f:
            for line in f:
                for i, gsc_err in enumerate(error_strings):
                    srch_str = gsc_err[0]
                    if srch_str in line:
                        error_counts[i] += 1

        error_msg = []
        for i, count in enumerate(error_counts):
            error_str, is_fatal = error_strings[i]
            fatal_str = ''
            if is_fatal and count:
                error_msg.append('Found %r %d times in logs' %
                                 (error_str, count))
                fatal_str = '(fatal)'
            logging.info('%r count%s: %d', error_str, fatal_str, count)
        if error_msg:
            raise error.TestFail('%s: %s' % (desc, ','.join(error_msg)))

    def ap_ro_version_is_supported(self, version):
        """Returns True if GSC supports the given version."""
        return version in self.AP_RO_VERSIONS

    def parse_ap_ro_line(self, line):
        """Returns the key and value from the AP RO info line."""
        # Remove ':' from the line.
        line = line.replace(':', '')
        for k in self.AP_RO_KEYS:
            if k in line:
                sections = line.partition(k)
                k = sections[-2]
                k = self.AP_RO_KEY_MAP.get(k, k)

                v = sections[-1].strip()
                # Return an int instead of a string
                if v.isdigit():
                    v = int(v)
                elif v == 'yes':
                    v = True
                elif v == 'no':
                    v = False
                elif 'no (' in v:
                    # Some fields have a reason in parenthisis after the no
                    # output. Convert that to False
                    v = False
                return k, v
        return None

    def get_ap_ro_info(self):
        """Returns a dictionary of the AP RO info.

        Get the ap_ro_info output. Convert it to a usable dictionary.

        Returns:
            A dictionary with the following key value pairs.
                'reason': String of unsupported reason or None if ap ro is
                          supported.
                'hash': 64 char hash or None if it isn't supported.
                'supported': bool whether AP RO verification is supported.
                'result': int of the AP RO verification result.
                'gbbd': string "ok|na (status)".
                'flags': a hex str of the saved flag value.
        """
        info =  {}
        # Some keys don't always appear in the output. Set their vaulues to
        # None, so they're always in the dictionary even when they're not in
        # the output.
        info.update(self.AP_RO_OPTIONAL_KEY_DICT)
        rv = self.send_command_retry_get_output('ap_ro_info',
                                                self.GET_AP_RO_OUTPUT_RE,
                                                compare_output=True)
        for line in rv[0][0].strip().splitlines():
            item = self.parse_ap_ro_line(line)
            if not item:
                logging.debug('Ignoring: %r', line)
                continue
            info[item[0]] = item[1]
        logging.info('APRO info: %s', pprint.pformat(info))
        return info

    def ccd_reset_and_wipe_tpm(self):
        """Open CCD to wipe the tpm."""
        if not self.testlab_is_on():
            return
        self.send_command('ccd testlab open')
        self.send_command('ccd reset factory')
        time.sleep(self.CCD_PASSWORD_RATE_LIMIT)
        self.send_command('ccd set OpenNoTPMWipe IfOpened')
        time.sleep(self.CCD_PASSWORD_RATE_LIMIT)
        self.set_ccd_level('lock')
        time.sleep(self.CCD_PASSWORD_RATE_LIMIT)
        self.send_command('ccd open')
        time.sleep(self.CCD_PASSWORD_RATE_LIMIT)
        self.ccd_reset()
        self.reboot()

    def get_taskinfo_output(self):
        """Get output from taskinfo command"""
        output = self.send_command_retry_get_output('taskinfo',
                                                    self.GET_TASKINFO,
                                                    safe=True,
                                                    retries=10)[0][1]
        return output

    def print_irqs(self, irq_dict):
        """Print the irq number, name, and count."""
        for num, count in irq_dict.items():
            logging.info(self.PRINT_IRQ_FMT, num, self.IRQ_DICT.get(num),
                         count)

    def get_irq_counts(self):
        """Return a dict with the irq numbers as keys and counts as values"""
        irq_counts = {}
        output = self.get_taskinfo_output()
        irq_list = re.findall('\d+\s+\d+[\r\n]', output)
        logging.info('IRQ:')
        # Make sure the regular sleep irq is in the dictionary, even if cr50
        # hasn't seen any interrupts. It's important the test sees that there's
        # never an interrupt.
        for irq_info in irq_list:
            logging.debug(irq_info)
            num, count = irq_info.split()
            num = int(num)
            count = int(count)
            irq_counts[num] = count
        self.print_irqs(irq_counts)
        return irq_counts

    def get_ap_ccdstate_info_str(self, ccdstate):
        """Return a string with the AP information from ccdstate."""
        if self.CCDSTATE_AP_FULL_KEY in ccdstate:
            val = ccdstate[self.CCDSTATE_AP_FULL_KEY]
        elif self.CCDSTATE_AP_KEY in ccdstate:
            val = ccdstate[self.CCDSTATE_AP_KEY]
        else:
            return ''
        return 'AP=%s' % val

    def get_pcr0_ccdstate_info_str(self, ccdstate):
        """Return a string with the pcr0 information from ccdstate.

        This converts the value to something that's human readable.

        @returns a string with the human readable pcr0 information or '' if
                 ccdstate doesn't contain the pcr0 information.
        """
        pcr0_val = ccdstate.get(self.CCDSTATE_PCR0_KEY, '').strip()
        if not pcr0_val:
            return ''
        logging.info('PCR0 - %s', pcr0_val)
        found_desc = 'unknown'
        for known_val, desc in self.PCR0_DICT.items():
            if known_val.startswith(pcr0_val):
                found_desc = desc
                break
        logging.info('PCR0 - %s : %s', found_desc, pcr0_val)
        # The PCR0 value is very long. Just report the first 8 characters
        report_len = min(len(pcr0_val), self.PCR0_REPORT_CHARS)
        return ',pcr0=%s(%s)' % (found_desc, pcr0_val[:report_len])

    def get_debug_ap_state(self):
        """Use gsc ccdstate to try and get some information about the AP state.

        @returns '' if there's any error or a string with the AP and pcr0
                information if ccdstate reported it.
        """
        ap_info = ''
        try:
            ccdstate = self.get_ccdstate()
            ap_info += self.get_ap_ccdstate_info_str(ccdstate)
            ap_info += self.get_pcr0_ccdstate_info_str(ccdstate)
        except Exception as e:
            # Ignore all exceptions. This is just an attempt to get AP state
            # that can be reported in errors. This should not override the
            # original error.
            logging.warning('Ignoring exception getting the AP state from '
                            'GSC: %s', e)
        logging.info('AP state: %s', ap_info)
        return ap_info

    def get_flog(self):
        """Return the flog contents"""
        return self.send_command_retry_get_output('flog', ['flog(.*)>'],
                                                  safe=True)[0][1].strip()

    def clear_system_reset_enforcement(self):
        """Cr50 doesn't enforce system reset with AP RO verification"""
        pass
