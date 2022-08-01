# Lint as: python3
# Copyright 2022 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import logging
from autotest_lib.client.common_lib import error
from autotest_lib.client.common_lib.cros.bluetooth import chipinfo
from autotest_lib.client.cros.bluetooth.bluetooth_quick_tests import (
        BluetoothQuickTests)
from autotest_lib.client.cros.bluetooth.hcitool import Hcitool


class BluetoothAVLHCITests(BluetoothQuickTests):
    """Test bluetooth avl HCI requirements."""
    test_wrapper = BluetoothQuickTests.quick_test_test_decorator
    batch_wrapper = BluetoothQuickTests.quick_test_batch_decorator
    test_log_result = BluetoothQuickTests.test_log_result

    MIN_ACL_BUFFER_SIZE = 1021
    ACL_DATA_PACKET_LENGTH_VALUE_INDEX = 1
    MIN_ACL_PACKETS_NUMBER = 4
    MIN_ACL_PACKETS_NUMBER_OPTIONAL = 6
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
    SCO_BUFFER_SIZE_VALUE_INDEX = 2
    MIN_SCO_BUFFER_SIZE = 60
    LE_CONTROLLER_FEATURE = 'LE Supported (Controller)'
    BR_EDR_NOT_SUPPORT_FEATURE = 'BR/EDR Not Supported'
    LE_AND_BR_EDR_CONTROLLER_FEATURE = (
            'Simultaneous LE and BR/EDR to Same Device Capable (Controller)')
    MIN_ACCEPT_LIST_SIZE_ENTRIES = 8
    BR_SECURE_CONNECTION_FEATURE = 'Secure Connections (Controller Support)'
    LE_DATA_PACKETS_LENGTH_EXTENSION_FEATURE = 'LE Data Packet Length Extension'
    LE_LINK_LAYER_PRIVACY_FEATURE = 'LL Privacy'
    MAX_PACKET_LENGTH = 251
    MIN_RESOLVING_LIST_SIZE_ENTRIES = 8
    LE_EXTENDED_ADVERTISING_FEATURE = 'LE Extended Advertising'
    LE_TWO_MEGA_PHYSICAL_CHANNEL_FEATURE = 'LE 2M PHY'
    MIN_ADVERTISEMENT_SETS_NUMBER = 10
    LE_CONNECTED_ISOCHRONOUS_STREAM_CENTRAL_FEATURE = (
            'Connected Isochronous Stream Central')
    LE_CONNECTED_ISOCHRONOUS_STREAM_PERIPHERAL_FEATURE = (
            'Connected Isochronous Stream Peripheral')
    LE_ISOCHRONOUS_BROADCASTER_FEATURE = 'Isochronous Broadcaster'
    LE_SYNCHRONIZED_RECEIVER_FEATURE = 'Synchronized Receiver'
    LE_POWER_CONTROL_REQUEST_FEATURE = 'LE Power Control Request'
    LE_POWER_CHANGE_INDICATION_FEATURE = 'LE Power Change Indication'
    GOOGLE_FEATURE_SPECIFICATION_VERSION = 98
    LE_ADV_RSSI_MONITORING = 'RSSI Monitoring of LE advertisements'
    LE_ADV_MONITORING = 'Advertising Monitoring of LE advertisements'
    CVSD_SYNCHRONOUS_DATA_FEATURE = 'CVSD synchronous data'

    CHIPSETS_UNSUPPORT_LEGACY = [
            'MVL-8897', 'MVL-8997', 'QCA-6174A-3-UART', 'QCA-6174A-5-USB'
    ]
    CHIPSETS_UNSUPPORT_LEGACY_OPTIONAL = [
            'Intel-AC7265', 'Intel-AC9260', 'Intel-AC9560', 'Intel-AX200',
            'Intel-AX201'
    ]
    CHIPSETS_UNSUPPORT_4_1 = ['MVL-8897', 'MVL-8997']
    CHIPSETS_UNSUPPORT_4_2 = ['MVL-8897', 'MVL-8997']
    CHIPSETS_UNSUPPORT_5_0 = [
            'MVL-8897', 'MVL-8997', 'QCA-6174A-3-UART', 'QCA-6174A-5-USB',
            'Intel-AC7265'
    ]
    CHIPSETS_UNSUPPORT_5_2 = [
            'MVL-8897', 'MVL-8997', 'QCA-6174A-3-UART', 'QCA-6174A-5-USB',
            'WCN3991', 'Intel-AC7265', 'Intel-AC9260', 'Intel-AC9560',
            'Intel-AX200', 'Intel-AX201', 'Intel-AX211',
            'Realtek-RTL8822C-USB', 'Realtek-RTL8822C-UART',
            'Realtek-RTL8852A-USB'
    ]

    CHIPSETS_UNSUPPORT_LLT_QUIRK = [
            'Intel-AC7265', 'QCA-6174A-5-USB', 'QCA-6174A-3-UART'
    ]
    CHIPSETS_UNSUPPORT_BR_EDR_SECURE_CONNECTION = [
            'Intel-AC7265', 'Realtek-RTL8822C-USB', 'Realtek-RTL8822C-UART'
    ]
    CHIPSETS_UNSUPPORT_PACKET_DATA_LENGTH = [
            'QCA-6174A-3-UART', 'QCA-6174A-5-USB'
    ]
    CHIPSETS_UNSUPPORT_LL_PRIVACY = ['Realtek-RTL8822C-USB']
    CHIPSETS_UNSUPPORT_ADV_SETS_NUMBER = [
            'Intel-AC9260', 'Intel-AC9560', 'Realtek-RTL8822C-USB',
            'Realtek-RTL8822C-UART'
    ]
    # These chipsets may still support AOSP Get Vendor Cap command as well as
    # BQR feature. They just don't support the features except BQR.
    CHIPSETS_SUPPORT_BQR_ONLY = [
            'Realtek-RTL8822C-USB', 'Realtek-RTL8822C-UART',
            'Realtek-RTL8852A-USB', 'Mediatek-MTK7921-USB',
            'Mediatek-MTK7921-SDIO'
    ]

    def initialize(self):
        """Initializes Autotest."""
        self.hcitool = Hcitool()

    # TODO(b/236922299): Un-skip QCA chipsets after the firmware fix landed.
    @test_wrapper('spec_legacy_test',
                  skip_chipsets=CHIPSETS_UNSUPPORT_LEGACY +
                  ['QCA-WCN6856', 'WCN3991'],
                  flags=['Quick Health'])
    def spec_legacy_test(self):
        """Checks Bluetooth legacy specification."""
        self.test_flushable_data_packets()
        self.test_erroneous_data_reporting()
        self.test_event_filter_size()
        self.test_acl_min_buffer_number()
        self.test_acl_min_buffer_size()
        self.test_sco_min_buffer_number()
        self.test_sco_min_buffer_size()

    @test_wrapper('spec_legacy_optional_test',
                  skip_chipsets=CHIPSETS_UNSUPPORT_LEGACY_OPTIONAL,
                  flags=['Quick Health'])
    def spec_legacy_optional_test(self):
        """Checks Bluetooth legacy optional specification."""
        self.test_acl_min_buffer_number_optional()

    @test_wrapper('spec_4_0_test', flags=['Quick Health'])
    def spec_4_0_test(self):
        """Checks Bluetooth version 4.0 specification."""
        self.test_low_energy_feature()
        self.test_accept_list_size()

    @test_wrapper('spec_4_1_basic_test',
                  skip_chipsets=CHIPSETS_UNSUPPORT_4_1,
                  flags=['Quick Health'])
    def spec_4_1_basic_test(self):
        """Checks Bluetooth version 4.1 basic specification."""
        self.test_le_dual_mode_topology_feature()

    @test_wrapper('spec_4_1_llt_test',
                  skip_chipsets=CHIPSETS_UNSUPPORT_4_1 +
                  CHIPSETS_UNSUPPORT_LLT_QUIRK,
                  flags=['Quick Health'])
    def spec_4_1_llt_test(self):
        """Checks Bluetooth version 4.1 llt feature."""
        self.test_link_layer_topology_feature()

    @test_wrapper('spec_4_1_br_edr_secure_conn_test',
                  skip_chipsets=CHIPSETS_UNSUPPORT_4_1 +
                  CHIPSETS_UNSUPPORT_BR_EDR_SECURE_CONNECTION,
                  flags=['Quick Health'])
    def spec_4_1_br_edr_secure_conn_test(self):
        """Checks Bluetooth version 4.1 BR/EDR secure connection feature."""
        self.test_br_edr_controller_secure_connection_feature()

    # TODO(b/235453469): Un-skip the RTK chipset after the firmware fix landed.
    @test_wrapper('spec_4_2_basic_test',
                  skip_chipsets=CHIPSETS_UNSUPPORT_4_2 +
                  ['Realtek-RTL8822C-UART'],
                  flags=['Quick Health'])
    def spec_4_2_basic_test(self):
        """Checks Bluetooth version 4.2 basic specification."""
        self.test_le_data_packet_length_extension_feature()

    # TODO(b/235453469): Un-skip the RTK chipset after the firmware fix landed.
    @test_wrapper('spec_4_2_packet_data_len_test',
                  skip_chipsets=CHIPSETS_UNSUPPORT_4_2 +
                  CHIPSETS_UNSUPPORT_PACKET_DATA_LENGTH +
                  ['Realtek-RTL8822C-UART'],
                  flags=['Quick Health'])
    def spec_4_2_packet_data_len_test(self):
        """Checks Bluetooth version 4.2 packet data length feature."""
        self.test_packet_data_length()

    # TODO(b/235453469): Un-skip RTK chipsets after the firmware fix landed.
    @test_wrapper('spec_4_2_ll_privacy_test',
                  skip_chipsets=CHIPSETS_UNSUPPORT_4_2 +
                  CHIPSETS_UNSUPPORT_LL_PRIVACY +
                  ['Realtek-RTL8822C-UART', 'Realtek-RTL8852A-USB'],
                  flags=['Quick Health'])
    def spec_4_2_ll_privacy_test(self):
        """Checks Bluetooth version 4.2 LL privacy features."""
        self.test_le_link_layer_privacy_feature()
        self.test_resolving_list_size()

    @test_wrapper('spec_5_0_basic_test',
                  skip_chipsets=CHIPSETS_UNSUPPORT_5_0,
                  flags=['Quick Health'])
    def spec_5_0_basic_test(self):
        """Check Bluetooth version 5.0 basic specification."""
        self.test_le_extended_advertising_feature()
        self.test_le_two_mega_physical_channel_feature()

    @test_wrapper('spec_5_0_adv_sets_number_test',
                  skip_chipsets=CHIPSETS_UNSUPPORT_5_0 +
                  CHIPSETS_UNSUPPORT_ADV_SETS_NUMBER,
                  flags=['Quick Health'])
    def spec_5_0_adv_sets_number_test(self):
        """Check Bluetooth version 5.0 advertisement sets number."""
        self.test_advertisement_sets_number()

    @test_wrapper('spec_5_2_test',
                  skip_chipsets=CHIPSETS_UNSUPPORT_5_2,
                  flags=['Quick Health'])
    def spec_5_2_test(self):
        """Checks Bluetooth version 5.0 specification."""
        self.test_le_isochronous_channels_feature()
        self.test_le_power_control_feature()

    @test_wrapper('hci_ext_msft_test', flags=['Quick Health'])
    def hci_ext_msft_test(self):
        """Checks Microsoft Bluetooth HCI command execution."""
        self.test_hci_vs_msft_read_supported_features()

    @test_wrapper('hci_ext_aosp_bqr_test', flags=['Quick Health'])
    def hci_ext_aosp_bqr_test(self):
        """Checks Android Bluetooth HCI extension BQR feature."""
        self.test_aosp_quality_report()

    @test_wrapper('hci_ext_aosp_non_bqr_test',
                  skip_chipsets=CHIPSETS_SUPPORT_BQR_ONLY,
                  flags=['Quick Health'])
    def hci_ext_aosp_non_bqr_test(self):
        """Checks Android Bluetooth HCI extension non-BQR feature."""
        self.test_le_apcf()
        self.test_le_batch_scan_and_events()
        self.test_le_extended_set_scan_parameters()
        self.test_le_get_controller_activity_energy_info()
        self.test_get_controller_debug_info_sub_event()

    @test_wrapper('Voice Path test', flags=['Quick Health'])
    def voice_path_test(self):
        """Checks HFP related features."""
        self.test_au_nbs_cvsd()

    def verify_not_support(self, feature, supported_features):
        """Verifies that the feature is not supported.

        @param feature: The feature which should be unsupported.
        @param supported_features: List of supported features.

        """
        self.results[feature + ' is not supported as expected'] = (
                feature not in supported_features)

    def verify_support(self, feature, supported_features):
        """Verifies that the feature is supported.

        @param feature: The feature which should be supported.
        @param supported_features: List of supported features.

        """
        self.results[feature + ' is supported'] = feature in supported_features

    def verify_equal(self, actual, expected, value_name):
        """Verifies that actual value is equal to expected value.

        @param actual: The value we got.
        @param expected: The value we expected.
        @param value_name: The name of the value. It is used for TestFail
        message.

        """
        self.results['%s is %s, expected %s' %
                     (value_name, actual, expected)] = actual == expected

    def verify_greater_equal(self, value, threshold, value_name):
        """Verifies that value is greater than or equal to threshold.

        @param value: The value we got.
        @param threshold: The threshold of the value.
        @param value_name: The name of the value. It is used for TestFail
        message.

        """
        self.results['%s is %d, want >= %d' %
                     (value_name, value, threshold)] = value >= threshold

    @test_log_result
    def test_flushable_data_packets(self):
        """Checks the Bluetooth controller must support flushable data packets.

        Note: As long as the chips are verified by SIG, setting the
                'Non-flushable Packet Boundary Flag' bit guarantees the related
                functionalities.
        """
        supported_features = self.hcitool.read_local_supported_features()[1]
        self.verify_support(self.NON_FLUSHABLE_PACKET_BOUNDARY_FEATURE,
                            supported_features)
        return all(self.results.values())

    @test_log_result
    def test_erroneous_data_reporting(self):
        """Checks the Bluetooth controller supports Erroneous Data Reporting."""
        supported_features = self.hcitool.read_local_supported_features()[1]
        self.verify_support(self.ERRONEOUS_DATA_REPORTING_FEATURE,
                            supported_features)
        return all(self.results.values())

    @test_log_result
    def test_event_filter_size(self):
        """Checks the Bluetooth controller event filter entries count.

        Checks the Bluetooth controller event filter has at least 8 entries.
        """
        number_of_added_filters = 0
        for event_filter in self.MAC_EVENT_FILTERS:
            set_filter_result = self.hcitool.set_event_filter(
                    event_filter[0], event_filter[1], event_filter[2])[0]
            if set_filter_result == self.CONTROLLER_MEMORY_FULL_STATUS_VALUE:
                break
            elif set_filter_result != self.CONTROLLER_SUCCESS_STATUS_VALUE:
                raise error.TestError(
                        'Failed to apply filter, status code is ' +
                        set_filter_result)
            number_of_added_filters += 1
        # Reset filter after done with test
        if not self.hcitool.set_event_filter('0', '0', '0'):
            logging.error('Unable to clear filter, reset bluetooth')
            self.bluetooth_facade.reset_on()
        else:
            logging.debug('Filter cleared')
        self.results['Filters added'] = number_of_added_filters
        return number_of_added_filters == 8

    @test_log_result
    def test_acl_min_buffer_number(self):
        """Checks if ACL minimum buffers count(number of data packets) >=4."""
        acl_buffers_count = self.hcitool.read_buffer_size()[
                self.TOTAL_NUM_ACL_DATA_PACKETS_VALUE_INDEX]
        self.verify_greater_equal(acl_buffers_count,
                                  self.MIN_ACL_PACKETS_NUMBER,
                                  'ACL buffers count')
        return all(self.results.values())

    @test_log_result
    def test_acl_min_buffer_number_optional(self):
        """Checks if ACL minimum buffers count(number of data packets) >=6."""
        acl_buffers_count = self.hcitool.read_buffer_size()[
                self.TOTAL_NUM_ACL_DATA_PACKETS_VALUE_INDEX]
        self.verify_greater_equal(acl_buffers_count,
                                  self.MIN_ACL_PACKETS_NUMBER_OPTIONAL,
                                  'ACL buffers count')
        return all(self.results.values())

    @test_log_result
    def test_acl_min_buffer_size(self):
        """Checks if ACL minimum buffers size >=1021."""
        acl_buffer_size = self.hcitool.read_buffer_size()[
                self.ACL_DATA_PACKET_LENGTH_VALUE_INDEX]
        self.verify_greater_equal(acl_buffer_size, self.MIN_ACL_BUFFER_SIZE,
                                  'ACL buffer size')
        return all(self.results.values())

    @test_log_result
    def test_sco_min_buffer_number(self):
        """Checks if SCO minimum buffer size(number of data packets) >=6."""
        sco_buffers_count = self.hcitool.read_buffer_size()[
                self.TOTAL_NUM_SYNCHRONOUS_DATA_PACKETS_VALUE_INDEX]
        self.verify_greater_equal(sco_buffers_count,
                                  self.MIN_SCO_PACKETS_NUMBER,
                                  'SCO buffers count')
        return all(self.results.values())

    @test_log_result
    def test_sco_min_buffer_size(self):
        """Checks if SCO minimum buffer size >=60."""
        sco_buffer_size = self.hcitool.read_buffer_size()[
                self.SCO_BUFFER_SIZE_VALUE_INDEX]
        self.verify_greater_equal(sco_buffer_size, self.MIN_SCO_BUFFER_SIZE,
                                  'SCO buffer size')
        return all(self.results.values())

    @test_log_result
    def test_low_energy_feature(self):
        """Checks if Bluetooth controller must use support
        Bluetooth Low Energy (BLE)."""
        supported_features = self.hcitool.read_local_supported_features()[1]
        self.verify_support(self.LE_CONTROLLER_FEATURE, supported_features)
        return all(self.results.values())

    @test_log_result
    def test_accept_list_size(self):
        """Checks if accept list size >= 8 entries."""
        accept_list_entries_count = self.hcitool.le_read_accept_list_size()[1]
        self.verify_greater_equal(accept_list_entries_count,
                                  self.MIN_ACCEPT_LIST_SIZE_ENTRIES,
                                  'Accept list size')
        return all(self.results.values())

    @test_log_result
    def test_le_dual_mode_topology_feature(self):
        """Checks if Bluetooth controller supports LE dual mode topology."""
        supported_features = self.hcitool.read_local_supported_features()[1]
        self.verify_not_support(self.BR_EDR_NOT_SUPPORT_FEATURE,
                                supported_features)
        self.verify_support(self.LE_CONTROLLER_FEATURE, supported_features)
        self.verify_support(self.LE_AND_BR_EDR_CONTROLLER_FEATURE,
                            supported_features)
        return all(self.results.values())

    @test_log_result
    def test_br_edr_controller_secure_connection_feature(self):
        """Checks if Bluetooth controller supports BR/EDR secure connections."""
        supported_features = self.hcitool.read_local_extended_features(2)[3]
        self.verify_support(self.BR_SECURE_CONNECTION_FEATURE,
                            supported_features)
        return all(self.results.values())

    @test_log_result
    def test_link_layer_topology_feature(self):
        """Checks if central and peripheral roles are supported concurrently."""
        self.results['supported roles'] = (
                self.bluetooth_facade.get_supported_le_roles())
        return 'central-peripheral' in self.results['supported roles']

    @test_log_result
    def test_le_data_packet_length_extension_feature(self):
        """Checks LE data packet length extension support."""
        supported_features = self.hcitool.read_le_local_supported_features()[1]
        self.verify_support(self.LE_DATA_PACKETS_LENGTH_EXTENSION_FEATURE,
                            supported_features)
        return all(self.results.values())

    @test_log_result
    def test_packet_data_length(self):
        """Checks if data packet length <= 251."""
        packet_data_length = self.hcitool.le_read_maximum_data_length()[1]
        self.verify_equal(packet_data_length, self.MAX_PACKET_LENGTH,
                          'Packet data length')
        return all(self.results.values())

    @test_log_result
    def test_le_link_layer_privacy_feature(self):
        """Checks if Bluetooth controller supports link layer privacy."""
        supported_features = self.hcitool.read_le_local_supported_features()[1]
        self.verify_support(self.LE_LINK_LAYER_PRIVACY_FEATURE,
                            supported_features)
        return all(self.results.values())

    @test_log_result
    def test_resolving_list_size(self):
        """Checks if resolving list size >= 8 entries."""
        resolving_list_entries_count = self.hcitool.le_read_resolving_list_size(
        )[1]
        self.verify_greater_equal(resolving_list_entries_count,
                                  self.MIN_RESOLVING_LIST_SIZE_ENTRIES,
                                  'Resolving list size')
        return all(self.results.values())

    @test_log_result
    def test_le_extended_advertising_feature(self):
        """Checks if Bluetooth controller supports LE advertising extension."""
        supported_features = self.hcitool.read_le_local_supported_features()[1]
        self.verify_support(self.LE_EXTENDED_ADVERTISING_FEATURE,
                            supported_features)
        return all(self.results.values())

    @test_log_result
    def test_advertisement_sets_number(self):
        """Checks if number of advertisement sets >= 10."""
        advertisement_sets_number = (
                self.hcitool.le_read_number_of_supported_advertising_sets()[1])
        self.verify_greater_equal(advertisement_sets_number,
                                  self.MIN_ADVERTISEMENT_SETS_NUMBER,
                                  'Advertisement sets number')
        return all(self.results.values())

    @test_log_result
    def test_le_two_mega_physical_channel_feature(self):
        """Checks if Bluetooth controller supports 2 Msym/s PHY for LE."""
        supported_features = self.hcitool.read_le_local_supported_features()[1]
        self.verify_support(self.LE_TWO_MEGA_PHYSICAL_CHANNEL_FEATURE,
                            supported_features)
        return all(self.results.values())

    @test_log_result
    def test_le_isochronous_channels_feature(self):
        """Checks if ISO channels feature is supported."""
        supported_features = self.hcitool.read_le_local_supported_features()[1]
        self.verify_support(
                self.LE_CONNECTED_ISOCHRONOUS_STREAM_CENTRAL_FEATURE,
                supported_features)
        self.verify_support(
                self.LE_CONNECTED_ISOCHRONOUS_STREAM_PERIPHERAL_FEATURE,
                supported_features)
        self.verify_support(self.LE_ISOCHRONOUS_BROADCASTER_FEATURE,
                            supported_features)
        self.verify_support(self.LE_SYNCHRONIZED_RECEIVER_FEATURE,
                            supported_features)
        return all(self.results.values())

    @test_log_result
    def test_le_power_control_feature(self):
        """Checks if Bluetooth controller supports LE power control."""
        supported_features = self.hcitool.read_le_local_supported_features()[1]
        self.verify_support(self.LE_POWER_CONTROL_REQUEST_FEATURE,
                            supported_features)
        self.verify_support(self.LE_POWER_CHANGE_INDICATION_FEATURE,
                            supported_features)
        return all(self.results.values())

    @test_log_result
    def test_hci_vs_msft_read_supported_features(self):
        """Checks if Bluetooth controller supports VS MSFT features."""
        chipset_name = self.bluetooth_facade.get_chipset_name()
        chip_info = chipinfo.query(chipset_name)
        if not chip_info.msft_support:
            raise error.TestNAError('Chipset ' + chipset_name +
                                    ' does not support MSFT HCI extensions')
        vs_msft_supported_features = (
                self.hcitool.vs_msft_read_supported_features(
                        chip_info.msft_ocf)[2])
        self.verify_support(self.LE_ADV_RSSI_MONITORING,
                            vs_msft_supported_features)
        self.verify_support(self.LE_ADV_MONITORING, vs_msft_supported_features)
        return all(self.results.values())

    def assert_aosp_hci(self):
        """Checks if a chipset supports AOSP HCI extensions."""
        chipset_name = self.bluetooth_facade.get_chipset_name()
        chip_info = chipinfo.query(chipset_name)
        if not chip_info.aosp_support:
            raise error.TestNAError('Chipset ' + chipset_name +
                                    ' does not support AOSP HCI extensions')

    @test_log_result
    def test_aosp_quality_report(self):
        """Checks if Bluetooth controller supports AOSP quality report."""
        self.assert_aosp_hci()
        version_supported = self.hcitool.le_get_vendor_capabilities_command(
        )[8]

        self.verify_greater_equal(version_supported,
                                  self.GOOGLE_FEATURE_SPECIFICATION_VERSION,
                                  'version_supported')
        if not all(self.results.values()):
            return False

        bluetooth_quality_report_support = (
                self.hcitool.le_get_vendor_capabilities_command()[14])

        self.results['bluetooth_quality_report_support is supported'] = (
                bluetooth_quality_report_support)

        return all(self.results.values())

    @test_log_result
    def test_le_apcf(self):
        """Checks if APCF filtering feature is supported."""
        self.assert_aosp_hci()
        filtering_support = self.hcitool.le_get_vendor_capabilities_command(
        )[5]
        self.results['LE APCF feature is supported'] = filtering_support
        return all(self.results.values())

    @test_log_result
    def test_le_batch_scan_and_events(self):
        """Checks if LE batch scan and events feature is supported."""
        self.assert_aosp_hci()
        total_scan_result_storage = (
                self.hcitool.le_get_vendor_capabilities_command()[3])

        self.results['LE batch scan and events feature is supported'] = (
                total_scan_result_storage != 0)
        return all(self.results.values())

    @test_log_result
    def test_le_extended_set_scan_parameters(self):
        """Checks if LE extended set scan parameters feature is supported."""
        self.assert_aosp_hci()
        extended_scan_support = self.hcitool.le_get_vendor_capabilities_command(
        )[10]

        self.results['LE extended set scan parameters feature is '
                     'supported'] = extended_scan_support
        return all(self.results.values())

    @test_log_result
    def test_le_get_controller_activity_energy_info(self):
        """Checks if LE get controller activity energy info feature is
        supported. """
        self.assert_aosp_hci()
        activity_energy_info_support = (
                self.hcitool.le_get_vendor_capabilities_command()[7])

        self.results['LE get controller activity energy info feature is '
                     'supported'] = activity_energy_info_support
        return all(self.results.values())

    @test_log_result
    def test_get_controller_debug_info_sub_event(self):
        """Checks if get controller debug info and sub-event features is
        supported. """
        self.assert_aosp_hci()
        debug_logging_support = self.hcitool.le_get_vendor_capabilities_command(
        )[11]

        self.results['Get controller debug info and sub-event features is '
                     'supported'] = debug_logging_support
        return all(self.results.values())

    @test_log_result
    def test_au_nbs_cvsd(self):
        """Checks if narrowband speech CVSD codec feature is supported."""
        supported_features = self.hcitool.read_local_supported_features()[1]
        self.verify_support(self.CVSD_SYNCHRONOUS_DATA_FEATURE,
                            supported_features)
        return all(self.results.values())

    @batch_wrapper('AVLHCI batch')
    def avl_hci_batch_run(self, num_iterations=1, test_name=None):
        """Runs bluetooth_AVLHCI test batch (all test).

        @param num_iterations: Number of times to run batch.
        @param test_name: test name as string from control file.
        """
        self.spec_legacy_test()
        self.spec_legacy_optional_test()
        self.spec_4_0_test()
        self.spec_4_1_basic_test()
        self.spec_4_1_llt_test()
        self.spec_4_1_br_edr_secure_conn_test()
        self.spec_4_2_basic_test()
        self.spec_4_2_packet_data_len_test()
        self.spec_4_2_ll_privacy_test()
        self.spec_5_0_basic_test()
        self.spec_5_0_adv_sets_number_test()
        self.spec_5_2_test()
        self.hci_ext_msft_test()
        self.hci_ext_aosp_bqr_test()
        self.hci_ext_aosp_non_bqr_test()
        self.voice_path_test()
