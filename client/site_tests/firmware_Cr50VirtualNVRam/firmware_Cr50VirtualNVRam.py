# Copyright 2018 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import logging
import re
from autotest_lib.client.bin import test, utils
from autotest_lib.client.common_lib import error
from autotest_lib.client.cros import service_stopper
from autotest_lib.client.cros.tpm import *

tpm_owner_password = ''
tpm_pw_hex = ''

def get_gsc_version():
    """Detect Cr50 vs Ti50 using Spec Revision in tpm_version."""
    rev = get_tpm_spec_revision()
    if rev == 116:
        return 'cr50'
    elif rev >= 162:
        return 'ti50'
    else:
        raise error.TestError('Unexpected Spec Revision: %d' % rev)

def run_tpmc_cmd(subcommand):
    """Make this test more readable by simplifying commonly used tpmc command.

    @param subcommand: String of the tpmc subcommand (read, raw, ...)
    @return String output (which may be empty).
    """

    # Run tpmc command, redirect stderr to stdout, and merge to one line.
    cmd = 'tpmc %s 2>&1 | awk 1 ORS=""' % subcommand
    return utils.system_output(cmd, ignore_status=True).strip()

def check_tpmc(subcommand, expected):
    """Runs tpmc command and checks the output against an expected regex.

    @param subcommand: String of the tpmc subcommand (read, raw, ...)
    @param expected: String re.
    @raises error.TestError() for not matching expected.
    """
    error_msg = 'invalid response to tpmc %s' % subcommand
    out = run_tpmc_cmd(subcommand)
    if (not re.match(expected, out)):
        raise error.TestError('%s: %s' % (error_msg, out))

    return out

def expect_tpmc_error(subcommand, expected_error):
    """Expect a tpmc error."""
    check_tpmc(subcommand, '.*failed.*%s.*' % expected_error)

class firmware_Cr50VirtualNVRam(test.test):
    'Tests the virtual NVRAM functionality in Cr50 through TPM commands.'

    version = 1

    def __take_tpm_ownership(self):
        global tpm_owner_password
        global tpm_pw_hex
        take_ownership()

        tpm_owner_password = get_tpm_password()
        if not tpm_owner_password:
            raise error.TestError('TPM owner password is empty after '
                                  'taking ownership.')
        for ch in tpm_owner_password:
            tpm_pw_hex = tpm_pw_hex + format(ord(ch), 'x') + ' '

    def __read_tests(self):
        # Check reading board ID returns a valid value.
        bid = check_tpmc('read 0x3fff00 0xc',
                         '([0-9a-f]{1,2} ?){12}')

        # Check that a subset of board ID can be read.
        check_tpmc('read 0x3fff00 0x6',
                   ' '.join(bid.split()[:6]))  # Matches previous read

        # Check that size constraints are respected.
        exp_err = '0x146' # TPM_RC_NV_RANGE
        if self.gsc_version == 'ti50':
            exp_err = '0x18b'  # TPM_RC_HANDLE
        expect_tpmc_error('read 0x3fffff 0xd', exp_err)

        # Check zero-length can be read.
        check_tpmc('read 0x3fff00 0x0', '')

        # Check arbitrary index can be read.
        check_tpmc('read 0x3fff73 0x0', '')

        # Check highest index can be read.
        check_tpmc('read 0x3fffff 0x0', '')

    def __get_write_cmd(self, index, offset, size):
        assert (size + 35) < 256
        assert offset < 256
        cmd_size = format(35 + size, 'x') + ' '
        size_hex = '00 ' + format(size, 'x') + ' '
        offset_hex = '00 ' + format(offset, 'x') + ' '
        data = ''
        for _ in range(size):
            data = data + 'ff '

        return ('raw '
                '80 02 '                    # TPM_ST_SESSIONS
                '00 00 00 ' + cmd_size +    # commandSize
                '00 00 01 37 ' +            # TPM_CC_NV_Write
                 index + ' ' +              # authHandle
                 index + ' ' +              # nvIndex
                '00 00 00 09 '              # sessionSize
                '40 00 00 09 '              # passwordAuth
                '00 00 '                    # nonceSize
                '00 '                       # sessionAttributes
                '00 00 ' +                  # password length
                 size_hex +                 # dataSize
                 data +                     # data
                 offset_hex)                # offset

    def __write_tests(self):
        # Check an implemented index cannot be written to:

        exp_err = '0x148' # TPM_RC_NV_LOCKED
        if self.gsc_version == 'ti50':
            exp_err = '0x12f'  # TPM_RC_AUTH_UNAVAILABLE

        # Zero-length write.
        expect_tpmc_error(self.__get_write_cmd('01 3f ff 00', 0, 0), exp_err)

        # Single byte.
        expect_tpmc_error(self.__get_write_cmd('01 3f ff 00', 0, 1), exp_err)

        # Single byte, offset.
        expect_tpmc_error(self.__get_write_cmd('01 3f ff 00', 4, 1), exp_err)

        # Write full length of index.
        expect_tpmc_error(self.__get_write_cmd('01 3f ff 00', 0, 12), exp_err)

        if self.gsc_version == 'ti50':
            exp_err = '0x18b'  # TPM_RC_HANDLE

        # Check an unimplemented index cannot be written to.
        expect_tpmc_error(self.__get_write_cmd('01 3f ff ff', 0, 1), exp_err)

    def __get_define_cmd(self, index, size):
        assert (len(tpm_owner_password) + 45) < 256
        pw_sz = format(len(tpm_owner_password), 'x') + ' '
        session_sz = format(len(tpm_owner_password) + 9, 'x') + ' '
        cmd_sz = format(len(tpm_owner_password) + 45, 'x') + ' '

        return ('raw '
                '80 02 '
                '00 00 00 ' + cmd_sz  +  # commandSize
                '00 00 01 2a '              # commandCode
                '40 00 00 01 '              # TPM_RH_OWNER
                '00 00 00 ' + session_sz +  # sessionSize
                '40 00 00 09 '              # passwordAuth
                '00 00 '                    # nonceSize
                '00 '                       # sessionAttributes
                '00 ' + pw_sz +             # password length
                tpm_pw_hex +                # password
                '00 00 '                    # auth value

                # TPM2B_NV_PUBLIC: publicInfo
                  '00 0e ' +                 # size
                  index + ' '                # nvIndex
                  '00 0b '                   # TPM_ALG_SHA256
                  '00 02 00 02 '             # attributes
                  '00 00 '                   # authPolicy
                  '00 ' + format(size, 'x')) # size

    def __get_undefine_cmd(self, index):
        assert (len(tpm_owner_password) + 31) < 256
        pw_sz = format(len(tpm_owner_password), 'x') + ' '
        session_sz = format(len(tpm_owner_password) + 9, 'x') + ' '
        cmd_sz = format(len(tpm_owner_password) + 31, 'x') + ' '

        return ('raw '
                '80 02 '
                '00 00 00 ' + cmd_sz + ' ' +  # commandSize
                '00 00 01 22 '                # commandCode
                '40 00 00 01 ' +              # TPM_RH_OWNER
                index + ' ' +                 # nvIndex
                '00 00 00 ' + session_sz +    # sessionSize
                '40 00 00 09 '                # passwordAuth
                '00 00 '                      # nonceSize
                '00 '                         # sessionAttributes
                '00 ' + pw_sz +               # password length
                tpm_pw_hex)                   # password

    def __definespace_check(self):
        # A space outside the virtual range can be defined
        check_tpmc(self.__get_define_cmd('01 4f aa df', 12),
                   '(0x[0-9]{2} ){6}'
                   '(0x00 ){4}'        # TPM_RC_SUCCESS
                   '(0x[0-9]{2} ?){9}')

        # A space outside the virtual range can be undefined.
        check_tpmc(self.__get_undefine_cmd('01 4f aa df'),
                   '(0x[0-9]{2} ){6}'
                   '(0x00 ){4}'        # TPM_RC_SUCCESS
                   '(0x[0-9]{2} ?){9}')

    def __definespace_tests(self):
        # Check an implemented space in the virtual range cannot be defined.
        expect_tpmc_error(self.__get_define_cmd('01 3f ff 00', 12),
                          '0x149')  # TPM_RC_NV_AUTHORIZATION

        if self.gsc_version == 'cr50':
            # Check an unimplemented space in the virtual range cannot be defined.
            expect_tpmc_error(self.__get_define_cmd('01 3f ff df', 12),
                            '0x149')  # TPM_RC_NV_AUTHORIZATION
        else:
            check_tpmc(self.__get_define_cmd('01 3f ff df', 12),
                    '(0x[0-9]{2} ){6}'
                    '(0x00 ){4}'        # TPM_RC_SUCCESS
                    '(0x[0-9]{2} ?){9}')


    def __undefinespace_tests(self):
        # Check an implemented space in the virtual range cannot be defined.
        expect_tpmc_error(self.__get_undefine_cmd('01 3f ff 00'),
                          '0x149')  # TPM_RC_NV_AUTHORIZATION

        if self.gsc_version == 'cr50':
            # Check an unimplemented space in the virtual range cannot be defined.
            expect_tpmc_error(self.__get_undefine_cmd('01 3f ff df'),
                            '0x149')  # TPM_RC_NV_AUTHORIZATION
        else:
            check_tpmc(self.__get_undefine_cmd('01 3f ff df'),
                    '(0x[0-9]{2} ){6}'
                    '(0x00 ){4}'        # TPM_RC_SUCCESS
                    '(0x[0-9]{2} ?){9}')

    def __readpublic_test(self):
        public = check_tpmc(('raw '
                    '80 01 '         # TPM_ST_NO_SESSIONS
                    '00 00 00 0e '   # commandSize
                    '00 00 01 69 '   # TPM_CC_ReadPublic
                    '01 3f ff 00'),  # nvIndex
                   '(0x([0-9a-f]){2} *){62}')

        # For attribute details see Table 204, Part 2 of TPM2.0 spec

        # TODO: remove support for old attributes.
        attributes_old = hex(1 << 10 |  # TPMA_NV_POLICY_DELETE
                         1 << 11 |      # TPMA_NV_WRITELOCKED
                         1 << 13 |      # TPMA_NV_WRITEDEFINE
                         1 << 18 |      # TPMA_NV_AUTHREAD
                         1 << 29)      # TPMA_NV_WRITTEN
        attributes_old = '%s %s %s %s ' % (attributes_old[2:4],
                                           attributes_old[4:6],
                                           attributes_old[6:8],
                                           attributes_old[8:10])

        attributes = hex(1 << 10 |  # TPMA_NV_POLICY_DELETE
                         1 << 11 |  # TPMA_NV_WRITELOCKED
                         1 << 13 |  # TPMA_NV_WRITEDEFINE
                         1 << 16 |  # TPMA_NV_PPREAD
                         1 << 18 |  # TPMA_NV_AUTHREAD
                         1 << 29)  # TPMA_NV_WRITTEN
        attributes = '%s %s %s %s ' % (attributes[2:4],
                                       attributes[4:6],
                                       attributes[6:8],
                                       attributes[8:10])

        # Support the old and new NvRam attributes for now
        valid_attributes = '(%s|%s)' % (attributes_old, attributes)
        expected = ('80 01 '                # TPM_ST_NO_SESSIONS
                    '00 00 00 3e '          # responseSize
                    '00 00 00 00 '          # responseCode

                    # TPM2B_PUBLIC: nvPublic
                      '00 0e '              # size
                      '01 3f ff 00 '        # nvIndex
                      '00 0b ' +            # TPM_ALG_SHA256
                      valid_attributes +    # old or new attributes
                      '00 00 '              # authPolicy
                      '00 0c '              # dataSize

                    # TPM2B_NAME: name
                     '00 22 '               # size
                     '([0-9a-f] ?){34} ')

        m = re.match(expected, re.sub('0x', '', public))
        if not m:
            raise error.TestError('%s does not match expected (%s)'
                                  % (public, expected))
        logging.info('Read public groups: %s', m.groups())

    def __readlock_test(self):
        # Virtual NV indices explicitly cannot be read locked, and attempts
        # to do so will return an authorization error.

        expect_tpmc_error(('raw '
                           '80 02 '             # TPM_ST_SESSIONS
                           '00 00 00 1f '       # commandSize
                           '00 00 01 4f '       # TPM_CC_NV_ReadLock
                           '01 3f ff 00 '       # authHandle
                           '01 3f ff 00 '       # nvIndex
                           '00 00 00 09 '       # sessionSize
                           '40 00 00 09 '       # password auth
                           '00 00 00 00 00'),   # empty password
                          '0x149')  # TPM_RC_NV_AUTHORIZATION

    def __writelock_test(self):
        # Virtual NV indices have no write policy defined, so cannot be write
        # locked.

        expect_tpmc_error(('raw '
                           '80 02 '              # TPM_ST_SESSIONS
                           '00 00 00 1f '        # commandSize
                           '00 00 01 38 '        # TPM_CC_NV_WriteLock
                           '01 3f ff 00 '        # authHandle
                           '01 3f ff 00 '        # nvIndex
                           '00 00 00 09 '        # sessionSize
                           '40 00 00 09 '        # password auth
                           '00 00 00 00 00'),    # empty password
                          '0x12f');  # TPM_RC_AUTH_UNAVAILABLE

    def initialize(self):
        """Initialize the test."""
        self.gsc_version = get_gsc_version()
        self.__take_tpm_ownership()
        # Stop services that access to the TPM, to be able to use tpmc.
        # Note: for TPM2 the order of re-starting services (they are started
        # in the reversed listed order) is important: e.g. tpm_managerd must
        # start after trunksd, and cryptohomed after attestationd.
        self._services = service_stopper.ServiceStopper(['cryptohomed',
                                                         'chapsd',
                                                         'attestationd',
                                                         'tpm_managerd',
                                                         'tcsd',
                                                         'trunksd'])
        self._services.stop_services()

    def run_once(self):
        """Run a few TPM state checks."""
        # If first virtual index is not defined, assumed we are not running
        # on cr50, or running on an old build of cr50. Skip the test.
        if re.match('.*failed.*0x18b.*',  # TPM_RC_HANDLE
                    run_tpmc_cmd('read 0x3fff00 0x0')):
            raise error.TestNAError("TPM does not support vNVRAM")

        self.__readpublic_test()
        self.__definespace_check()
        self.__definespace_tests()
        self.__undefinespace_tests()
        self.__readlock_test()
        self.__writelock_test()
        self.__write_tests()
        self.__read_tests()

    def cleanup(self):
        """Cleanup the test."""
        self._services.restore_services()
