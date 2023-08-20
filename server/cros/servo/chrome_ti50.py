# Lint as: python2, python3
# Copyright 2021 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import logging
import pprint
import re

from autotest_lib.server.cros.servo import chrome_cr50
from autotest_lib.client.common_lib import error

CHIP_NAME = 'ti50'

class ChromeTi50(chrome_cr50.ChromeCr50):
    """Manages control of a Chrome Ti50.

    We control the Chrome Ti50 via the console of a Servo board. Chrome Ti50
    provides many interfaces to set and get its behavior via console commands.
    This class is to abstract these interfaces.
    """

    START_STR = ['ti50_common']
    NAME = CHIP_NAME
    BID_RE = r'Board ID: (\S{8}):?(|\S{8}), flags: (\S{8})\s'
    CCD_PW_DENIED = 'failed: ParamCount'

    # Ti50 only supports v2
    AP_RO_VERSIONS = [2]
    # ===============================================================
    # Ti50 Image Names
    GS_PRIVATE = 'gs://chromeos-localmirror-private/distfiles/'
    GS_PUBLIC = 'gs://chromeos-localmirror/distfiles/'
    # Prod signed test images are stored in the private ti50 directory.
    GS_PRIVATE_PROD = GS_PRIVATE + 'ti50/'
    # Node locked test images are in this private debug directory.
    GS_PRIVATE_DBG = GS_PRIVATE + 'chromeos-ti50-debug/'
    # This works for all ti50 file formats. RW_VER and BID are supplied by the
    # test.
    # old - ti50.ro.0.0.*.rw.RW_VER.BID.tar.xz
    # new - ti50.r0.0.*.w0.RW_VER.BID.tar.xz
    PROD_TAR = 'ti50.r*0.0.*%s%s.tar.xz'
    # Prod image from the tarball
    PROD_FILE = 'ti50.bin.prod'
    # ti50.dbg.0xDEVID0_0xDEVID1.bin.GIT_SHA.BID (SHA and BID are optional)
    DEBUG_FILE = '*/ti50.dbg.%s.bin.*%s'
    # ti50_Unknown_NodeLocked-DEVID0-DEVID1_cr50-accessory-mp.bin
    ERASEFLASHINFO_FILE = '*/ti50_Unknown_NodeLocked-%s_ti50-accessory-mp.bin'
    QUAL_VERSION_FILE = 'chromeos-ti50-QUAL_VERSION'
    DUT_FW = '/opt/google/ti50/firmware/'
    DUT_PROD = DUT_FW + PROD_FILE
    DUT_PREPVT = DUT_FW + 'ti50.bin.prepvt'
    # ===============================================================

    # Ti50 reset flags as defined in PMU_RSTSRC.
    RESET_FLAGS = {
           'RESET_FLAG_POWER_ON'         : 1 << 0, # POR
           'RESET_FLAG_HIBERNATE'        : 1 << 1, # EXIT
           'RESET_FLAG_SOFT'             : 1 << 4, # SYSRESET
           'RESET_FLAG_HARD'             : 1 << 5, # SOFTWARE
           'RESET_FLAG_BROWNOUT'         : 1 << 6, # FST_BRNOUT
           'RESET_FLAG_SECURITY'         : 1 << 7, # SEC_THREAT
           'RESET_FLAG_RBOX'             : 1 << 8, # RBOX_COMB_RST
    }

    # Ti50 interrupt numbers reported in taskinfo
    IRQ_DICT = {
            0: 'UART0_GRP0',
            1: 'UART1_GRP0',
            2: 'UART2_GRP0',
            3: 'UART3_GRP0',
            5: 'ADC0_GRP0',
            79: 'I2CS0_GRP0',
            99: 'RBOX0_GRP1',
            106: 'TIMER0_TIMER0_MATCH1',
            108: 'TIMER0_TIMER1_MATCH0',
            115: 'USB0_USBINTR',
            116: 'XO_CALIB',
            257: 'WAKEUP',
    }
    PRINT_IRQ_FMT = '    0x%x %-20s %-10s'
    # USB should be disabled if ccd is disabled.
    CCD_IRQS = [ 115 ]
    # Rdd and timer sof overflow irqs
    CCD_CHANGE_IRQS = [5, 116]
    GET_TASKINFO = ['IRQ counts by type:(.*)(>|Stack sizes)']
    # Ti50 has no periodic wake from regular sleep
    SLEEP_RATE = 0
    # Ti50 inhibits deep sleep for 60 seconds after AP power on.
    DEEP_SLEEP_DELAY = 60
    # Maximum TPM init time.
    TPM_INIT_MAX = 40000
    TIMESTAMP_RE = r'\[[ 0-9.]+.\] '
    WAKE_RESPONSE = [r'\n(|%s)> ' % TIMESTAMP_RE]
    TIME_RE = r'Since %s: [x0-9a-f]* = ([0-9\.]*) s'
    TIME_SINCE_DS_RE = TIME_RE % 'deep sleep'
    TIME_SINCE_COLD_RESET_RE = TIME_RE % 'reset'

    # Ti50 doesn't configure PLT_RST vs SYS_RST. All boards use PLT_RST
    BOARD_PROP_ALWAYS_TRUE = ['BOARD_USE_PLT_RESET']
    # Ti50 doesn't have any errors to track right now.
    ERROR_DESC_LIST = []

    def strip_timestamp(self, result):
        """Remove the timestamp from the result output.

        Tests expect a certain format from the command result. Timestamps add
        random noise to the output that tests can't handle. Strip the timestamp
        from the start of every line of the result. This makes the result closer
        to cr50 behavior. Cr50 doesn't print timestamps in console output.

        @param result: The list of matched output.
        @return: The list of matched output without timestamps
        """
        if isinstance(result, list) or isinstance(result, tuple):
            if isinstance(result, tuple):
                logging.warning('Turning tuple into list')
            new_result = []
            for part in result:
                new_result.append(self.strip_timestamp(part))
        elif isinstance(result, str):
            new_result = re.sub('^' + self.TIMESTAMP_RE,
                                '',
                                result,
                                flags=re.MULTILINE)
        else:
            new_result = result
        return new_result

    def send_command_get_output(self, command, regexp_list):
        """Send the command get the result.

        Strip ti50 timestamps from the result before returning it.

        @param command: the command to send
        @param regexp_list: The list of regular expressions to match in the
                            command output
        @return: A list of matched output
        """
        rv = super(ChromeTi50,
                   self).send_command_get_output(command, regexp_list)
        if regexp_list:
            # Remove the timestamps from the ti50 output since tests can't
            # handle it.
            rv = self.strip_timestamp(rv)
            logging.debug('no timestamps: %s', pprint.pformat(rv))
        return rv

    def set_ccd_level(self, level, password=''):
        if level == 'unlock':
            raise error.TestError(
                "Ti50 does not support privilege level unlock")
        super(ChromeTi50, self).set_ccd_level(level, password)

    def unlock_is_supported(self):
        return False

    def check_boot_mode(self, mode_exp='NORMAL'):
        """Query the Ti50 boot mode, and compare it against mode_exp.

        Args:
            mode_exp: expected boot mode. It should be either 'NORMAL'
                      or 'NO_BOOT'.
        Returns:
            True if the boot mode matches mode_exp.
            False, otherwise.
        Raises:
            TestError: Input parameter is not valid.
        """

        # Ti50 implements EFS 2.1, Cr50 implements EFS 2.0. This means
        # 'NORMAL' is renamed to 'VERIFIED'. Ti50 also changes the case.
        rv = self.send_command_retry_get_output('ec_comm',
                [r'boot_mode\s*:\s*(Verified|NoBoot)'], safe=True)
        if mode_exp == 'NORMAL':
            return rv[0][1] == 'Verified'
        elif mode_exp == 'NO_BOOT':
            return rv[0][1] == 'NoBoot'
        else:
            raise error.TestError('parameter, mode_exp is not valid: %s' %
                                  mode_exp)

    def get_serial(self):
        """Ti50's serial is lowercase."""
        return super(ChromeTi50, self).get_serial().lower()

    def send_safe_command_get_output(self, command, regexp_list,
            channel_mask=0x1):
        """Ti50 console does not support chan command"""
        return self.send_command_get_output(command, regexp_list)

    def rolledback(self):
        """Raise an error until there's a way to check rollback."""
        # TODO(b/263579376): add support to check rollback on ti50.
        raise error.TestError('No way to check rollback on ti50')

    def set_board_id(self, chip_bid, chip_flags):
        """Set the chip board id type and flags."""
        # Ti50 doesn't use '0x' at the start of the bid args.
        self.send_command('bid %x %x' % (chip_bid, chip_flags))

    def gettime_since_deep_sleep(self):
        """Get the time since deep sleep"""
        rv = self.send_gettime_cmd_get_output(self.TIME_SINCE_DS_RE)
        logging.info('Time since deep sleep reset: %r', rv)
        return rv

    def gettime(self):
        """Get the time since any sort of reset"""
        ds_time = self.gettime_since_deep_sleep()
        cr_time = self.gettime_since_cold_reset()
        min_time = min(ds_time, cr_time)
        logging.info('Min reset time: %s', min_time)
        return min_time

    def get_taskinfo_output(self):
        """Get output from taskinfo command"""
        output = self.send_command_get_output('taskinfo',
                                              self.GET_TASKINFO)[0][1]
        # For Ti50 check each line of output after any timestamps have been
        # removed by send_command_get_output. Each line should be 13 characters
        # long with only digits or spaces. There are 4 characters for the irq
        # number and 9 for the count.
        m = re.match(r'\s+(([\d ]{13}\r\n)+)', output)
        if m is None:
            raise error.TestError('Wrong taskinfo output', output)
        return output
