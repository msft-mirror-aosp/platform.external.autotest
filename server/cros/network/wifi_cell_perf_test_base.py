# Copyright (c) 2021 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import logging

from autotest_lib.client.common_lib import error
from autotest_lib.client.common_lib import utils
from autotest_lib.client.common_lib.cros.network import ping_runner
from autotest_lib.server.cros.network import ip_config_context_manager
from autotest_lib.server.cros.network import perf_test_manager as perf_manager
from autotest_lib.server.cros.network import wifi_cell_test_base


class WiFiCellPerfTestBase(wifi_cell_test_base.WiFiCellTestBase):
    """An abstract base class for autotests in WiFi performance cells.

    Similar to WiFiCellTestBase with one major exception:

    The pcap device is also used as an endpoint in performance tests, so the
    router and pcap device must have a direct Ethernet connection over their LAN
    ports in a WiFiCellPerfTestBase.
    """

    DEFAULT_ROUTER_LAN_IP_ADDRESS = "192.168.1.50"
    DEFAULT_PCAP_LAN_IP_ADDRESS = "192.168.1.51"
    DEFAULT_ROUTER_LAN_IFACE_NAME = "eth1"
    DEFAULT_PCAP_LAN_IFACE_NAME = "eth1"

    def parse_additional_arguments(self, commandline_args):
        """Hook into super class to take control files parameters.

        @param commandline_args dict of parsed parameters from the autotest.

        """
        self._power_save_off = 'power_save_off' in commandline_args

        def get_arg_value_or_default(attr, default): return commandline_args[
            attr] if attr in commandline_args else default

        self._router_lan_ip_addr = get_arg_value_or_default(
            'router_lan_ip_addr', self.DEFAULT_ROUTER_LAN_IP_ADDRESS)
        self._router_lan_iface_name = get_arg_value_or_default(
            'router_lan_iface_name', self.DEFAULT_ROUTER_LAN_IFACE_NAME)
        self._pcap_lan_ip_addr = get_arg_value_or_default(
            'pcap_lan_ip_addr', self.DEFAULT_PCAP_LAN_IP_ADDRESS)
        self._pcap_lan_iface_name = get_arg_value_or_default(
            'pcap_lan_iface_name', self.DEFAULT_PCAP_LAN_IFACE_NAME)

        self.parse_governor(commandline_args)

    def configure_and_connect_to_ap(self, ap_config):
        """Configure the router as an AP with the given config and connect
        the DUT to it.

        @param ap_config HostapConfig object.

        @return name of the configured AP
        """
        # self.context.configure has a similar check - but that one only
        # errors out if the AP *requires* VHT i.e. AP is requesting
        # MODE_11AC_PURE and the client does not support it.
        # For performance tests we don't want to run MODE_11AC_MIXED on the AP if
        # the client does not support VHT, as we are guaranteed to get the
        # same results at 802.11n/HT40 in that case.
        if ap_config.is_11ac and not self.context.client.is_vht_supported():
            raise error.TestNAError('Client does not have AC support')
        return super(WiFiCellPerfTestBase,
                     self).configure_and_connect_to_ap(ap_config)

    def _verify_additional_setup_requirements(self):
        """Ensure that the router and pcap device in the cell have a direct
        connection available over their respective LAN ports. Raises a test NA
        error if this connection cannot be verified.
        """

        with ip_config_context_manager.IpConfigContextManager() as ip_context:
            try:
                self._setup_ip_config(ip_context, False)

                ping_config = ping_runner.PingConfig(
                        self._pcap_lan_ip_addr,
                        count=5,
                        source_iface=self._router_lan_iface_name,
                        ignore_result=True)
                ping_result = self.context.router.ping(ping_config)
                if ping_result.received == 0:
                    raise Exception("Ping failed (%s)" % (ping_result))
            except Exception as e:
                raise error.TestNAError(
                    'Could not verify connection between router and pcap '
                    'devices. Router and pcap device must have a direct '
                    'Ethernet connection over their LAN ports to run '
                    'performance tests: %s' % (e))

    def _setup_ip_config(self, ip_context, add_ip_route=True):
        """Set up the IP configs required by the test.

        @param ip_context: IpConfigContextManager object within which to make
                changes to the IP configs of the router, client and pcap.
        """
        ip_context.bring_interface_up(self.context.router.host,
                                      self._router_lan_iface_name)
        ip_context.bring_interface_up(self.context.pcap_host.host,
                                      self._pcap_lan_iface_name)
        ip_context.assign_ip_addr_to_iface(self.context.router.host,
                                           self._router_lan_ip_addr,
                                           self._router_lan_iface_name)
        ip_context.assign_ip_addr_to_iface(self.context.pcap_host.host,
                                           self._pcap_lan_ip_addr,
                                           self._pcap_lan_iface_name)
        if add_ip_route:
                ip_context.add_ip_route(self.context.client.host,
                                        self._pcap_lan_ip_addr,
                                        self.context.client.wifi_if,
                                        self.context.router.wifi_ip)
                ip_context.add_ip_route(self.context.pcap_host.host,
                                        self.context.client.wifi_ip,
                                        self._router_lan_iface_name,
                                        self._router_lan_ip_addr)

    def parse_governor(self, commandline_args):
        """Validate governor string.

        Not all machines will support all of these governors, but this at least
        ensures that a potentially valid governor was passed in.
        """
        if 'governor' in commandline_args:
            self._governor = commandline_args['governor']

            if self._governor not in ('performance', 'powersave', 'userspace',
                                      'ondemand', 'conservative', 'schedutil'):
                logging.warning(
                    'Unrecognized CPU governor %s. Running test '
                    'without setting CPU governor...', self._governor)
                self._governor = None
        else:
            self._governor = None

    @staticmethod
    def get_current_governor(host):
        """
        @return the CPU governor name used on a machine. If cannot find
                the governor info of the host, or if there are multiple
                different governors being used on different cores, return
                'default'.
        """
        try:
            governors = set(utils.get_scaling_governor_states(host))
            if len(governors) != 1:
                return 'default'
            return next(iter(governors))
        except:
            return 'default'

    def setup_governor(self, governor):
        """Set the governor if provided. Otherwise, read it from client and
        router hosts. Fallback to the 'default' name if different values were
        read.
        """
        if governor:
            self.set_scaling_governors(governor)
            governor_name = governor
        else:
            # try to get machine's current governor
            governor_name = self.get_current_governor(self.context.client.host)
            if governor_name != self.get_current_governor(self.context.router.host):
                governor_name = 'default'
        return governor_name

    def set_scaling_governors(self, governor):
        """Set governors for client and router hosts.

        Record the current governors to be able to restore to the
        original state.
        """
        self.client_governor = utils.get_scaling_governor_states(
            self.context.client.host)
        self.router_governor = utils.get_scaling_governor_states(
            self.context.router.host)
        utils.set_scaling_governors(governor, self.context.client.host)
        utils.set_scaling_governors(governor, self.context.router.host)

    def restore_scaling_governors(self):
        """Restore governors to the original states.
        """
        utils.restore_scaling_governor_states(self.client_governor,
                                              self.context.client.host)
        utils.restore_scaling_governor_states(self.router_governor,
                                              self.context.router.host)

    def configure_and_run_tests(self):
        """IP configuration for router and pcap hosts.

        Bring interfaces up, assign IP addresses and add routes.
        Run the test for all provided AP configs and enabled governors.
        """
        failed_performance_tests = set()

        for ap_config in self._ap_configs:
            # Set up the router and associate the client with it.
            self.configure_and_connect_to_ap(ap_config)
            with ip_config_context_manager.IpConfigContextManager(
            ) as ip_context:

                self._setup_ip_config(ip_context)

                manager = perf_manager.PerfTestManager(self._use_iperf)
                # Flag a test error if we disconnect for any reason.
                with self.context.client.assert_no_disconnects():
                    for governor in sorted(set([None, self._governor])):
                        # Run the performance test and record the test types
                        # which failed due to low throughput.
                        failed_performance_tests.update(
                            self.do_run(ap_config, manager,
                                        not (self._power_save_off),
                                        governor))

            # Clean up router and client state for the next run.
            self.context.client.shill.disconnect(
                self.context.router.get_ssid())
            self.context.router.deconfig()

        return failed_performance_tests
