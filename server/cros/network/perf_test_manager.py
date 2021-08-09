# Copyright (c) 2021 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from autotest_lib.client.common_lib import error
from autotest_lib.server.cros.network import netperf_runner
from autotest_lib.server.cros.network import netperf_session


class PerfTestTypes(object):
    """These are the different performance test types that are supported by
    autotest. The are defined from perspective of the Device Under Test, so for
    example 'tcp_rx' refers to a performance test of data transfer from a remote
    server to the DUT using the TCP protocol.
    """
    TEST_TYPE_TCP_TX = 'tcp_tx'
    TEST_TYPE_TCP_RX = 'tcp_rx'
    TEST_TYPE_TCP_BIDIRECTIONAL = 'tcp_bidirectional'
    TEST_TYPE_UDP_TX = 'udp_tx'
    TEST_TYPE_UDP_RX = 'udp_rx'
    TEST_TYPE_UDP_BIDIRECTIONAL = 'udp_bidirectional'


class PerfTestManager(object):
    """Manager for Performance tests. This class provides a unified API to allow
    callers run performance tests using the supported tools.
    """

    # TODO(b:195574472): Add support for iperf in this class.

    DEFAULT_TEST_TIME = 10

    def get_config(self, test_type, test_time=DEFAULT_TEST_TIME):
        """ Get a NetperfConfig object for a performance tests based on the test
        type and other parameters.

        @param test_type string, test type from performance_test_types.
        @param test_time int number of seconds to run the test for.

        @return NetperfConfig object.
        """
        return netperf_runner.NetperfConfig(
                self._netperf_type_from_perf_type(test_type),
                test_time=test_time)

    def get_session(self,
                    test_device_proxy,
                    peer_device_proxy,
                    test_device_interface=None,
                    peer_device_interface=None,
                    ignore_failures=False):
        """Get a NetperfSession object for a set of performance tests.

        @param test_device_proxy: WiFiClient object for the device-under-test.
        @param peer_device_proxy: LinuxSystem object for the performance testing
        peer of the DUT.
        @param test_device_interface Interface object for the test device.
        @param peer_device_interface Interface object for the peer device.

        @return NetperfSession object.
        """
        return netperf_session.NetperfSession(
                test_device_proxy,
                peer_device_proxy,
                client_interface=test_device_interface,
                server_interface=peer_device_interface,
                ignore_failures=ignore_failures)

    def get_result(self, results):
        """Get a single performance result from a list of results.

        @param results list NetperfResults.

        @return a single NetperfResult which represents the
        distribution of results.
        """

        return netperf_runner.NetperfResult.from_samples(results)

    def _netperf_type_from_perf_type(self, test_type):
        """Convert a performance test type to a netperf test type.

        @param test_type string, test type from PerfTestTypes.

        @return string netperf test type that corresponds to the generic test type.
        """
        if test_type == PerfTestTypes.TEST_TYPE_TCP_TX:
            return netperf_runner.NetperfConfig.TEST_TYPE_TCP_STREAM
        elif test_type == PerfTestTypes.TEST_TYPE_TCP_RX:
            return netperf_runner.NetperfConfig.TEST_TYPE_TCP_MAERTS
        elif test_type == PerfTestTypes.TEST_TYPE_TCP_BIDIRECTIONAL:
            return netperf_runner.NetperfConfig.TEST_TYPE_TCP_BIDIRECTIONAL
        elif test_type == PerfTestTypes.TEST_TYPE_UDP_TX:
            return netperf_runner.NetperfConfig.TEST_TYPE_UDP_STREAM
        elif test_type == PerfTestTypes.TEST_TYPE_UDP_RX:
            return netperf_runner.NetperfConfig.TEST_TYPE_UDP_MAERTS
        elif test_type == PerfTestTypes.TEST_TYPE_UDP_BIDIRECTIONAL:
            return netperf_runner.NetperfConfig.TEST_TYPE_UDP_BIDIRECTIONAL
        raise error.TestFail(
                'Test type %s is not supported by netperf_runner.' % test_type)
