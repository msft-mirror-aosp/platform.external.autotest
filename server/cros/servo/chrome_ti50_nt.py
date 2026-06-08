# Lint as: python2, python3
# Copyright 2025 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import logging
import time

from autotest_lib.client.common_lib import error
from autotest_lib.server.cros.servo import chrome_ti50
from autotest_lib.server.cros.servo import chrome_cr50

FW_NAME = 'ti50'
CHIP_NAME = 'g ti50 nt'


class ChromeTi50NT(chrome_ti50.ChromeTi50):
    """Manages control of a Chrome Ti50 NT device.

    We control the Chrome Ti50 via the console of a Servo board. Chrome Ti50
    provides many interfaces to set and get its behavior via console commands.
    This class is to abstract these interfaces.
    """

    RESET_FLAGS = {
            'RESET_FLAG_POWER_ON': 1 << 0,  # POR
            'RESET_FLAG_HIBERNATE': 1 << 1,  # LOW_POWER_EXIT
            'RESET_FLAG_HARD': 1 << 2,  # SOFTWARE request hard reset
            'RESET_FLAG_RBOX': 1 << 3,  # SYS_RST_AON
            'RESET_FLAG_WATCHDOG': 1 << 4,  # AON_TIMER_AON
            'RESET_FLAG_BROWNOUT': 1 << 5,  # PWRMGR_AON
            'RESET_FLAG_SECURITY': 1 << 6,  # ALERT_HANDLER
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
    # ===============================================================
    # Ti50 NT Image Names
    GS_PRIVATE = 'gs://chromeos-localmirror-private/distfiles/'
    GS_PUBLIC = 'gs://chromeos-localmirror/distfiles/'
    # Node locked test images are in this private debug directory.
    GS_PRIVATE_DBG = GS_PRIVATE + 'chromeos-ti50-debug-nt/'
    # Ti50 NT tarball format
    PROD_TAR = 'ti50-nt.r*.0.*%s%s.tar.xz'
    # ti50-nt.dbg.0xDEVID0_0xDEVID1.bin.GIT_SHA.BID (SHA and BID are optional)
    DEBUG_FILE = '*/ti50-nt.dbg.%s.bin.*%s'
    # ti50_Unknown_NodeLocked-DEVID0-DEVID1_(signing key).bin
    ERASEFLASHINFO_FILE = '*/ti50_Unknown_NodeLocked-%s_*.bin'
    QUAL_VERSION_FILE = 'chromeos-ti50-nt-QUAL_VERSION'

    # Image prefix used by Chrome OS.
    GSC_IMG_PREFIX = FW_NAME + '-nt'
    NAME = GSC_IMG_PREFIX
    # ChromeOS Ti50 firmware directory
    DUT_FW = '/opt/google/ti50/firmware/'

    # Ti50 image in tarballs
    PROD_FILE = 'ti50-nt.bin.prod'
    # Ti50 CrOS image information
    DUT_PROD = DUT_FW + GSC_IMG_PREFIX + '.bin.prod'
    DUT_PREPVT = DUT_FW + GSC_IMG_PREFIX + '.bin.prepvt'
    DUT_REMOVE_GSC_IMAGES = 'rm ' + DUT_FW + GSC_IMG_PREFIX + '*'

    # Ti50 FW is installed in 2 locations
    DUT_PROD_PATHS = [DUT_PROD]
    DUT_PREPVT_PATHS = [DUT_PREPVT]
    ALWAYS_HAD_ROLLBACK_PRINT = True
    CCD_DISABLE_RETRY_COUNT = 3

    @chrome_cr50.dts_control_command
    def ccd_disable(self, raise_error=True):
        """Try to disable CCD with dts mode then try the CCD_MODE gpio"""
        # TODO(b/455592006): use CCD_MODE to disable rdd. Remove this once the
        # board issue has been fixed.
        use_workaround = (self._servo.main_device_is_flex()
                          and "rdd_use_ccd_mode"
                          in self.faft_config.cr50_capability)
        logging.debug("CCD workaround (%s): %r", use_workaround,
                      self.faft_config.cr50_capability)
        super(ChromeTi50NT, self).ccd_disable(raise_error
                                              and not use_workaround)
        if not use_workaround:
            return
        for i in range(self.CCD_DISABLE_RETRY_COUNT):
            logging.info('attempt %d: try ccd disable workaround', i)
            # Give GSC some time for rdd state changes to propagate.
            time.sleep(2)
            self.send_command('ccd testlab open')
            self.send_command('gpioset CCD_MODE_L 1')
            self.wait_for_ccd_disable(raise_error=False)
            if not self.ccd_is_enabled():
                logging.info('attempt %d: disabled ccd with workaround', i)
                return
        if raise_error:
            raise error.TestError('Failed to disable CCD')
