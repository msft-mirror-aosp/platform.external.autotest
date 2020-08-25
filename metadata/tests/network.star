
# Copyright 2020 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# !!! GENERATED FILE. DO NOT EDIT !!!

load('//metadata/test_common.star', 'test_common')

def define_tests():
    return [
        test_common.define_test(
            'network/ChromeCelluarEndToEnd',
            suites = [],
        ),
        test_common.define_test(
            'network/ChromeCellularNetworkPresent',
            suites = ['network_ui'],
        ),
        test_common.define_test(
            'network/ChromeCellularNetworkProperties',
            suites = [],
        ),
        test_common.define_test(
            'network/ChromeCellularSmokeTest',
            suites = ['network_ui'],
        ),
        test_common.define_test(
            'network/ChromeWifiConfigure',
            suites = ['network_ui'],
        ),
        test_common.define_test(
            'network/ChromeWifiEndToEnd',
            suites = [],
        ),
        test_common.define_test(
            'network/DhcpBrokenDefaultGateway',
            suites = [],
        ),
        test_common.define_test(
            'network/DhcpClasslessStaticRoute',
            suites = ['network_nightly'],
        ),
        test_common.define_test(
            'network/DhcpFQDN',
            suites = [],
        ),
        test_common.define_test(
            'network/DhcpFailureWithStaticIP',
            suites = [],
        ),
        test_common.define_test(
            'network/DhcpMTU',
            suites = [],
        ),
        test_common.define_test(
            'network/DhcpNak',
            suites = ['network_nightly'],
        ),
        test_common.define_test(
            'network/DhcpNegotiationSuccess',
            suites = ['network_nightly'],
        ),
        test_common.define_test(
            'network/DhcpNegotiationTimeout',
            suites = ['network_nightly'],
        ),
        test_common.define_test(
            'network/DhcpNonAsciiParameter',
            suites = ['network_nightly'],
        ),
        test_common.define_test(
            'network/DhcpRenew',
            suites = ['network_nightly'],
        ),
        test_common.define_test(
            'network/DhcpRenewWithOptionSubset',
            suites = [],
        ),
        test_common.define_test(
            'network/DhcpRequestHostName',
            suites = [],
        ),
        test_common.define_test(
            'network/DhcpStaticIP',
            suites = ['network_nightly'],
        ),
        test_common.define_test(
            'network/DhcpVendorEncapsulatedOptions',
            suites = [],
        ),
        test_common.define_test(
            'network/DhcpWpadNegotiation',
            suites = ['network_nightly'],
        ),
        test_common.define_test(
            'network/Dhcpv6Basic',
            suites = [],
        ),
        test_common.define_test(
            'network/DiskFull',
            suites = [],
        ),
        test_common.define_test(
            'network/EthCaps',
            suites = [],
        ),
        test_common.define_test(
            'network/EthCapsServer',
            suites = [],
        ),
        test_common.define_test(
            'network/EthernetStressPlug',
            suites = [],
        ),
        test_common.define_test(
            'network/FirewallHolePunch',
            suites = [],
        ),
        test_common.define_test(
            'network/FirewallHolePunchServer',
            suites = ['network_nightly'],
        ),
        test_common.define_test(
            'network/Ipv6SimpleNegotiation',
            suites = ['network_nightly'],
        ),
        test_common.define_test(
            'network/NegotiatedLANSpeed',
            suites = [],
        ),
        test_common.define_test(
            'network/PortalStress',
            suites = [],
        ),
        test_common.define_test(
            'network/ProxyResolver',
            suites = [],
        ),
        test_common.define_test(
            'network/RackWiFiConnect',
            suites = [],
        ),
        test_common.define_test(
            'network/RestartShill',
            suites = [],
        ),
        test_common.define_test(
            'network/RoamWifiEndToEnd',
            suites = [],
        ),
        test_common.define_test(
            'network/StressServoEthernetPlug',
            suites = [],
        ),
        test_common.define_test(
            'network/WiFiCaps',
            suites = ['network_nightly'],
        ),
        test_common.define_test(
            'network/WiFiHECaps',
            suites = ['wifi_flaky'],
        ),
        test_common.define_test(
            'network/WiFiResume',
            suites = ['bvt-perbuild', 'network_nightly', 'wificell-cq'],
        ),
        test_common.define_test(
            'network/WiFi_AssocConfigPerformance',
            suites = ['wifi_flaky'],
        ),
        test_common.define_test(
            'network/WiFi_BSSTMReq',
            suites = ['wifi_matfunc', 'wifi_release'],
        ),
        test_common.define_test(
            'network/WiFi_BT_AntennaCoex',
            suites = ['wifi_matfunc'],
        ),
        test_common.define_test(
            'network/WiFi_CSA',
            suites = ['wifi_matfunc', 'wificell-cq'],
        ),
        test_common.define_test(
            'network/WiFi_CSADisconnect',
            suites = ['wifi_matfunc', 'wificell-cq'],
        ),
        test_common.define_test(
            'network/WiFi_ChannelHop',
            suites = ['wifi_matfunc'],
        ),
        test_common.define_test(
            'network/WiFi_ChannelScanDwellTime',
            suites = ['wifi_perf'],
        ),
        test_common.define_test(
            'network/WiFi_ChaosConfigFailure',
            suites = [],
        ),
        test_common.define_test(
            'network/WiFi_ChaosConfigSniffer',
            suites = [],
        ),
        test_common.define_test(
            'network/WiFi_ChromeEndToEnd',
            suites = [],
        ),
        test_common.define_test(
            'network/WiFi_ConnectOnResume',
            suites = [],
        ),
        test_common.define_test(
            'network/WiFi_ConnectionIdentifier',
            suites = ['wifi_matfunc', 'wificell-cq'],
        ),
        test_common.define_test(
            'network/WiFi_DarkResumeActiveScans',
            suites = ['wifi_lucidsleep'],
        ),
        test_common.define_test(
            'network/WiFi_DisableEnable',
            suites = ['wifi_matfunc', 'wificell-cq'],
        ),
        test_common.define_test(
            'network/WiFi_DisableRandomMACAddress',
            suites = ['wifi_matfunc'],
        ),
        test_common.define_test(
            'network/WiFi_FastReconnectInDarkResume',
            suites = ['wifi_lucidsleep'],
        ),
        test_common.define_test(
            'network/WiFi_GTK',
            suites = ['wifi_matfunc', 'wificell-cq'],
        ),
        test_common.define_test(
            'network/WiFi_HiddenRemains',
            suites = ['wifi_matfunc', 'wificell-cq'],
        ),
        test_common.define_test(
            'network/WiFi_HiddenScan',
            suites = ['wifi_matfunc'],
        ),
        test_common.define_test(
            'network/WiFi_LinkMonitorFailure',
            suites = ['wifi_matfunc'],
        ),
        test_common.define_test(
            'network/WiFi_MalformedProbeResp',
            suites = ['wifi_matfunc', 'wificell-cq'],
        ),
        test_common.define_test(
            'network/WiFi_Manual',
            suites = [],
        ),
        test_common.define_test(
            'network/WiFi_MultiAuth',
            suites = ['wifi_matfunc', 'wificell-cq'],
        ),
        test_common.define_test(
            'network/WiFi_OverlappingBSSScan',
            suites = ['wifi_matfunc'],
        ),
        test_common.define_test(
            'network/WiFi_PMKSACaching',
            suites = ['wifi_matfunc'],
        ),
        test_common.define_test(
            'network/WiFi_PTK',
            suites = ['wifi_matfunc'],
        ),
        test_common.define_test(
            'network/WiFi_Prefer5Ghz',
            suites = ['wifi_matfunc'],
        ),
        test_common.define_test(
            'network/WiFi_ProfileBasic',
            suites = ['wifi_matfunc', 'wificell-cq'],
        ),
        test_common.define_test(
            'network/WiFi_ProfileGUID',
            suites = ['wifi_matfunc'],
        ),
        test_common.define_test(
            'network/WiFi_RandomMACAddress',
            suites = ['wifi_matfunc'],
        ),
        test_common.define_test(
            'network/WiFi_RateControl',
            suites = ['wifi_flaky'],
        ),
        test_common.define_test(
            'network/WiFi_Reassociate',
            suites = ['wifi_matfunc', 'wificell-cq'],
        ),
        test_common.define_test(
            'network/WiFi_Reset',
            suites = ['wifi_matfunc'],
        ),
        test_common.define_test(
            'network/WiFi_RetryConnectHidden',
            suites = [],
        ),
        test_common.define_test(
            'network/WiFi_RoamDbus',
            suites = ['wifi_matfunc'],
        ),
        test_common.define_test(
            'network/WiFi_RoamDiagnostics',
            suites = [],
        ),
        test_common.define_test(
            'network/WiFi_RoamEndToEnd',
            suites = ['wifi_endtoend', 'wifi_release'],
        ),
        test_common.define_test(
            'network/WiFi_RoamNatural',
            suites = [],
        ),
        test_common.define_test(
            'network/WiFi_RoamSuspend',
            suites = [],
        ),
        test_common.define_test(
            'network/WiFi_RoamSuspendEndToEnd',
            suites = ['wifi_endtoend'],
        ),
        test_common.define_test(
            'network/WiFi_SSIDSwitchBack',
            suites = ['wifi_matfunc'],
        ),
        test_common.define_test(
            'network/WiFi_ScanPerformance',
            suites = ['wifi_matfunc', 'wificell-cq'],
        ),
        test_common.define_test(
            'network/WiFi_SecChange',
            suites = ['wifi_matfunc', 'wificell-cq'],
        ),
        test_common.define_test(
            'network/WiFi_SetOptionalDhcpProperties',
            suites = ['wifi_matfunc', 'wificell-cq'],
        ),
        test_common.define_test(
            'network/WiFi_SuspendTwice',
            suites = [],
        ),
        test_common.define_test(
            'network/WiFi_UpdateRouter',
            suites = [],
        ),
        test_common.define_test(
            'network/WiFi_VerifyAttenuator',
            suites = [],
        ),
        test_common.define_test(
            'network/WiFi_VerifyRouter',
            suites = ['wifi_update_router'],
        ),
        test_common.define_test(
            'network/WiFi_WakeOnDisconnect',
            suites = ['wifi_lucidsleep'],
        ),
        test_common.define_test(
            'network/WiFi_WakeOnSSID',
            suites = ['wifi_lucidsleep'],
        ),
        test_common.define_test(
            'network/WiFi_WakeOnWiFiThrottling',
            suites = ['wifi_lucidsleep'],
        ),
        test_common.define_test(
            'network/WiFi_WoWLAN',
            suites = ['wifi_lucidsleep'],
        ),
        test_common.define_test(
            'network/WlanRegulatory',
            suites = ['wifi_matfunc'],
        )
    ]
