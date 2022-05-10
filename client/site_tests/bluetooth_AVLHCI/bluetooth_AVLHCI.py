# Lint as: python3
# Copyright 2022 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import logging
from autotest_lib.client.bin import test
from autotest_lib.client.common_lib import error
from autotest_lib.client.cros.bluetooth.hcitool import Hcitool
from autotest_lib.client.cros.multimedia import bluetooth_facade


class bluetooth_AVLHCI(test.test):
    """Test bluetooth avl HCI requirements."""
    version = 1
    MIN_ACL_BUFFER_SIZE = 1021
    ACL_DATA_PACKET_LENGTH_VALUE_INDEX = 1
    MIN_ACL_PACKETS_NUMBER = 4
    TOTAL_NUM_ACL_DATA_PACKETS_VALUE_INDEX = 3
    MIN_SCO_PACKETS_NUMBER = 6
    TOTAL_NUM_SYNCHRONOUS_DATA_PACKETS_VALUE_INDEX = 4
    NON_FLUSHABLE_PACKET_BOUNDARY_FEATURE = 'Non-flushable Packet Boundary Flag'
    ERRONEOUS_DATA_REPORTING_FEATURE = 'Erroneous Data Reporting'
    MAC_EVENT_FILTERS = [['1', '2', '00 17 C9 AA AA AA'],
                         ['1', '2', '00 17 9B AA AA AA'],
                         ['1', '2', '00 17 94 AA AA AA'],
                         ['1', '2', '00 17 95 AA AA AA'],
                         ['1', '2', '00 17 B0 AA AA AA'],
                         ['1', '2', '00 17 C0 AA AA AA'],
                         ['1', '2', '00 17 08 AA AA AA'],
                         ['1', '2', '00 16 EA AA AA AA']]
    CONTROLLER_MEMORY_FULL_STATUS_VALUE = 7
    CONTROLLER_SUCCESS_STATUS_VALUE = 0

    def initialize(self):
        """Initializes Autotest."""
        self.hcitool = Hcitool()
        self.facade = bluetooth_facade.BluezFacadeLocal()

    def spec_legacy_test(self):
        """Checks Bluetooth legacy specification."""
        logging.info('* Running Bluetooth spec_legacy_test:')
        self.flushable_data_packets_test()
        self.erroneous_data_reporting_test()
        self.event_filter_size_test()
        self.acl_min_buffer_number_test()
        self.acl_min_buffer_size_test()
        self.sco_min_buffer_number_test()

    def flushable_data_packets_test(self):
        """Checks the Bluetooth controller must support flushable data packets.

        Note: As long as the chips are verified by SIG, setting the
                'Non-flushable Packet Boundary Flag' bit guarantees the related
                functionalities.
        """
        logging.info('** Running Bluetooth flushable data packets test:')
        supported_features = self.hcitool.read_local_supported_features()[1]
        if self.NON_FLUSHABLE_PACKET_BOUNDARY_FEATURE in supported_features:
            logging.info(
                    'packet boundary flag flushable data packets is supported')
        else:
            raise error.TestFail(
                    'packet boundary flag flushable data packets not supported'
            )

    def erroneous_data_reporting_test(self):
        """Checks the Bluetooth controller supports Erroneous Data Reporting."""
        logging.info('** Running Bluetooth erroneous data reporting test:')
        supported_features = self.hcitool.read_local_supported_features()[1]
        if self.ERRONEOUS_DATA_REPORTING_FEATURE in supported_features:
            logging.info('%s is supported',
                         self.ERRONEOUS_DATA_REPORTING_FEATURE)
        else:
            raise error.TestFail(self.ERRONEOUS_DATA_REPORTING_FEATURE +
                                 ' not supported')

    def event_filter_size_test(self):
        """Checks the Bluetooth controller event filter entries count.

        Checks the Bluetooth controller event filter has at least 8 entries.
        """
        logging.info('** Running Bluetooth event filter size test:')
        number_of_added_filters = 0
        for event_filter in self.MAC_EVENT_FILTERS:
            set_filter_result = self.hcitool.set_event_filter(
                    event_filter[0], event_filter[1], event_filter[2])[0]
            if set_filter_result == self.CONTROLLER_MEMORY_FULL_STATUS_VALUE:
                self.facade.reset_on()
                raise error.TestFail('Filter ' + ''.join(event_filter) +
                                     ' failed to apply. Only ' +
                                     str(number_of_added_filters) +
                                     ' filters were added')

            elif set_filter_result != self.CONTROLLER_SUCCESS_STATUS_VALUE:
                self.facade.reset_on()
                raise error.TestError(
                        'Failed to apply filter, status code is ' +
                        set_filter_result)
            number_of_added_filters += 1
        logging.info(
                'All 8 event filters were set successfully with values %s',
                self.MAC_EVENT_FILTERS)
        # Reset filter after done with test
        if not self.hcitool.set_event_filter('0', '0', '0'):
            logging.error('Unable to clear filter, reset bluetooth')
            self.facade.reset_on()
        else:
            logging.debug('Filter cleared')

    def acl_min_buffer_number_test(self):
        """Checks if ACL minimum buffers count(number of data packets) >=4."""
        logging.info('** Running Bluetooth acl min buffer number test:')
        acl_buffers_count = self.hcitool.read_buffer_size()[
                self.TOTAL_NUM_ACL_DATA_PACKETS_VALUE_INDEX]
        self.assert_(acl_buffers_count >= self.MIN_ACL_PACKETS_NUMBER)
        logging.info("ACL buffers count = %d which is >= %d",
                     acl_buffers_count, self.MIN_ACL_PACKETS_NUMBER)

    def acl_min_buffer_size_test(self):
        """Checks if ACL minimum buffers size >=1021."""
        logging.info('** Running Bluetooth acl min buffer size test:')
        acl_buffer_size = self.hcitool.read_buffer_size()[
                self.ACL_DATA_PACKET_LENGTH_VALUE_INDEX]
        self.assert_(acl_buffer_size >= self.MIN_ACL_BUFFER_SIZE)
        logging.info('ACL buffer size (number of packets)= %d which is >= %d',
                     acl_buffer_size, self.MIN_ACL_BUFFER_SIZE)

    def sco_min_buffer_number_test(self):
        """Checks if SCO minimum buffer size(number of data packets) >=6."""
        logging.info('** Running Bluetooth sco min buffer number test:')
        sco_buffers_count = self.hcitool.read_buffer_size()[
                self.TOTAL_NUM_SYNCHRONOUS_DATA_PACKETS_VALUE_INDEX]
        self.assert_(sco_buffers_count >= self.MIN_SCO_PACKETS_NUMBER)
        logging.info('SCO buffers count = %d which is >= %d',
                     sco_buffers_count, self.MIN_SCO_PACKETS_NUMBER)

    def avl_hci_batch_run(self, test_name=None):
        """Runs bluetooth_AVLHCI test batch (all test).

        @param test_name: test name as string from control file.
        """
        if test_name is None:
            self.spec_legacy_test()
            # All future test will be here
        else:
            getattr(self, test_name)()

    def run_once(self, test_name=None):
        """Runs bluetooth_AVLHCI.

        @param test_name: test name as string from control file.
        """
        self.facade.reset_on()
        self.avl_hci_batch_run(test_name)
        self.facade.reset_on()
