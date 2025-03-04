# Lint as: python2, python3
# Copyright 2025 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from autotest_lib.server.cros.servo import chrome_ti50

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
            'RESET_FLAG_HIBERNATE': 1 << 1,  # EXIT
            'RESET_FLAG_SOFT': 1 << 4,  # SYSRESET
            'RESET_FLAG_HARD': 1 << 5,  # SOFTWARE
            'RESET_FLAG_BROWNOUT': 1 << 6,  # FST_BRNOUT
            'RESET_FLAG_SECURITY': 1 << 7,  # SEC_THREAT
            'RESET_FLAG_RBOX': 1 << 8,  # RBOX_COMB_RST
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
