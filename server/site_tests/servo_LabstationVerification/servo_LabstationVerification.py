# Copyright 2019 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Wrapper test to run verification on a labstation."""

import json
import logging
import os
import re
import time

from autotest_lib.client.common_lib import error
from autotest_lib.server import test
from autotest_lib.server import utils as server_utils
from autotest_lib.server.hosts import servo_host
from autotest_lib.server.hosts import servo_constants
from autotest_lib.server.hosts import factory

class servo_LabstationVerification(test.test):
    """Wrapper test to run verifications on a labstation image.

    This test verifies basic servod behavior on the host supplied to it e.g.
    that servod can start etc, before inferring the DUT attached to the servo
    device, and running more comprehensive servod tests by using a full
    cros_host and servo_host setup.
    """
    version = 1

    UL_BIT_MASK = 0x2

    # Regex to match ipv4 byte.
    IPV4_RE_BLOCK = r'(25[0-5]|2[0-4][0-9]|[01]?[0-9]?[0-9])'

    # Full regex to match an ipv4 with optional subnet mask.
    RE_IPV4 = re.compile(r'^(%(block)s\.){3}(%(block)s)(/\d+)?$' %
                         {'block':IPV4_RE_BLOCK})

    # Timeout in seconds to wait after cold_reset before attempting to ping
    # again. This includes a potential fw screen (30s), and some buffer
    # for the network.
    RESET_TIMEOUT_S = 60

    def get_servo_mac(self, servo_proxy):
        """Given a servo's serial retrieve ethernet port mac address.

        @param servo_proxy: proxy to talk to servod

        @returns: mac address of the ethernet port as a string
        @raises: error.TestError: if mac address cannot be inferred
        """
        # TODO(coconutruben): once mac address retrieval through v4 is
        # implemented remove these lines of code, and replace with
        # servo_v4_eth_mac.
        try:
            serial = servo_proxy.get('support.serialname')
            if serial == 'unknown':
                serial = servo_proxy.get('serialname')
        except error.TestFail as e:
            if 'No control named' in e:
                serial = servo_proxy.get('serialname')
            else:
              raise e
        ctrl_path = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                                 'serial_to_mac_map.json')
        with open(ctrl_path, 'r') as f:
            serial_mac_map = json.load(f)
        if not serial in serial_mac_map:
            raise error.TestError('Unable to retrieve mac address for '
                                  'serial %s' % serial)
        return str(serial_mac_map[serial])

    def _flip_UL_bit(self, byte):
        """Helper to flip the Universal/Local bit in a given byte.

        For some IPv6's extended unique identifier (EUI) 64 calculation
        part of the logic is to flip the U/L bit on the first byte.

        Note: it is the callers responsibility to ensure that |byte| is
        only one byte. This function will just flip the 7th bit of whatever
        is supplied and return that.

        @param byte: the byte to flip

        @returns: |byte| with it's U/L bit flipped.
        """
        return byte ^ self.UL_BIT_MASK

    def _from_mac_to_ipv6_eui_64(self, mac):
        """Convert a MAC address (IEEE EUI48) to a IEEE EUI64 node component.

        This follows guidelines to convert a mac address to an IPv6 node
        component by
        - splitting the mac into two parts
        - inserting 0xfffe in between the two parts
        - flipping the U/L bit on the first byte

        @param mac: string containing the mac address

        @returns: string containing the IEEE EUI64 node component to |mac|
        """
        mac_bytes = [b.lower() for b in mac.split(':')]
        # First, flip the 7th bit again. This converts the string coming from
        # the mac (as it's a hex) into an int, flips it, before casting it back
        # to a hex as is expected for the mac address.
        mac_bytes[0] = hex(self._flip_UL_bit(int(mac_bytes[0],16)))[2:]
        mac_bytes = (mac_bytes[:3] + ['ff', 'fe'] + mac_bytes[-3:])
        ipv6_components = []
        while mac_bytes:
            # IPv6 has two bytes between :
            ipv6_components.append('%s%s' % (mac_bytes.pop(0),
                                             mac_bytes.pop(0)))
        # Lastly, remove the leading 0s to have a well formatted concise IPv6.
        return ':'.join([c.lstrip('0') for c in ipv6_components])

    def _mac_to_ipv6_addr(self, mac, ipv6_network_component):
        """Helper to generate an IPv6 address given network component and mac.

        @param mac: the mac address of the target network interface
        @param ipv6_network_component: prefix + subnet id portion of IPv6 [:64]

        @returns: an IPv6 address that could be used to target the network
                  interface at |mac| if it's on the same network as the network
                  component indicates
        """
        # Do not add an extra/miss a ':' when glueing both parts together.
        glue = '' if ipv6_network_component[-1] == ':' else ':'
        return '%s%s%s' % (ipv6_network_component, glue,
                           self._from_mac_to_ipv6_eui_64(mac))

    def _from_ipv6_to_mac_address(self, ipv6):
        """Given an IPv6 address retrieve the mac address.

        Assuming the address at |ipv6| followed the conversion standard layed
        out at _from_mac_to_ipv6_eui_64() above, this helper does the inverse.

        @param ipv6: full IPv6 address to extract the mac address from

        @returns: mac address extracted from node component as a string
        """
        # The node component i.e. the one holding the mac info is the 64 bits.
        components = ipv6.split(':')[-4:]
        # This is reversing the EUI 64 logic.
        mac_bytes = []
        for component in components:
            # Expand the components fully again.
            full_component = component.rjust(4,'0')
            # Mac addresses use one byte components as opposed to the two byte
            # ones for IPv6 - split them up.
            mac_bytes.extend([full_component[:2], full_component[2:]])
        # First, flip the 7th bit again.
        mac_bytes[0] = self._flip_UL_bit(mac_bytes[0])
        # Second, remove the 0xFFFE bytes inserted in the middle again.
        mac_bytes = mac_bytes[:3] + mac_bytes[-3:]
        return ':'.join([c.lower() for c in mac_bytes])

    def _build_ssh_cmd(self, hostname, cmd):
        """Build the ssh command to run |cmd| via bash on |hostname|.

        @param hostname: hostname/ip where to run the cmd on
        @param cmd: cmd on hostname to run

        @returns: ssh command to run
        """
        ssh_cmd = [r'ssh', '-q', '-o', 'StrictHostKeyChecking=no',
                   r'-o', 'UserKnownHostsFile=/dev/null',
                   r'root@%s' % hostname,
                   r'"%s"' % cmd]
        return ' '.join(ssh_cmd)

    def _ip_info_from_host(self, host, ip, info, host_name):
        """Retrieve some |info| related to |ip| from host on |ip|.

        @param host: object that implements 'run', where the command
                     will be executed form
        @param ip: ip address to run on and to filter for
        @param info: one of 'ipv4' or 'dev'
        @param host_name: executing host's name, for error message

        @returns: ipv4 associated on the same nic as |ip| if |info|== 'ipv4'
                  nic dev name associated with |ip| if |info|== 'dev'

        @raises error.TestError: if output of 'ip --brief addr' is unexpected
        @raises error.TestError: info not in ['ipv4', 'dev']
        """
        if info not in ['ipv4', 'dev']:
            raise error.TestFail('Cannot retrieve info %r', info)
        ip_stub = r"ip --brief addr | grep %s" % ip
        cmd = self._build_ssh_cmd(ip, ip_stub)
        logging.info('command to find %s on %s: %s', info, host_name, cmd)
        # The expected output here is of the form:
        # [net device] [UP/DOWN] [ipv4]/[subnet mask] [ipv6]/[subnet mask]+
        try:
            output = host.run(cmd).stdout.strip()
        except (error.AutoservRunError, error.CmdError) as e:
            logging.error(str(e))
            raise error.TestFail('Failed to retrieve %s on %s' % (info, ip))
        logging.debug('ip raw output: %s', output)
        components = output.split()
        if info == 'ipv4':
            # To be safe, get all IPs, and subsequently report the first ipv4
            # found.
            raw_ips = components[2:]
            for raw_ip in raw_ips:
                if re.match(self.RE_IPV4, raw_ip):
                    ret = raw_ip.split('/')[0]
                    logging.info('ipv4 found: %s', ret)
                    break
            else:
                raise error.TestFail('No ipv4 address found in ip command: %s' %
                                     ', '.join(raw_ips))
        if info == 'dev':
            ret = components[0]
            logging.info('dev found: %s', ret)
        return ret

    def get_dut_on_servo_ip(self, servo_host_proxy):
        """Retrieve the IPv4 IP of the DUT attached to a servo.

        Note: this will reboot the DUT if it fails initially to get the IP
        Note: for this to work, servo host and dut have to be on the same subnet

        @param servo_host_proxy: proxy to talk to the servo host

        @returns: IPv4 address of DUT attached to servo on |servo_host_proxy|

        @raises error.TestError: if the ip cannot be inferred
        """
        # Note: throughout this method, sh refers to servo host, dh to DUT host.
        # Figure out servo hosts IPv6 address that's based on its mac address.
        servo_proxy = servo_host_proxy._servo
        sh_ip = server_utils.get_ip_address(servo_host_proxy.hostname)
        sh_nic_dev = self._ip_info_from_host(servo_host_proxy, sh_ip, 'dev',
                                             'servo host')
        addr_cmd ='cat /sys/class/net/%s/address' % sh_nic_dev
        sh_dev_addr = servo_host_proxy.run(addr_cmd).stdout.strip()
        logging.debug('Inferred Labstation MAC to be: %s', sh_dev_addr)
        sh_dev_ipv6_stub = self._from_mac_to_ipv6_eui_64(sh_dev_addr)
        # This will get us the IPv6 address that uses the mac address as node id
        cmd = (r'ifconfig %s | grep -oE "([0-9a-f]{0,4}:){4}%s"' %
               (sh_nic_dev, sh_dev_ipv6_stub))
        servo_host_ipv6 = servo_host_proxy.run(cmd).stdout.strip()
        logging.debug('Inferred Labstation IPv6 to be: %s', servo_host_ipv6)
        # Figure out DUTs expected IPv6 address
        # The network component should be shared between the DUT and the servo
        # host as long as they're on the same subnet.
        network_component = ':'.join(servo_host_ipv6.split(':')[:4])
        dut_ipv6 = self._mac_to_ipv6_addr(self.get_servo_mac(servo_proxy),
                                          network_component)
        logging.info('Inferred DUT IPv6 to be: %s', dut_ipv6)
        # Dynamically generate the correct shell-script to retrieve the ipv4.
        try:
            server_utils.run('ping -6 -c 1 -w 35 %s' % dut_ipv6)
        except error.CmdError:
            # If the DUT cannot be pinged, then try to reset it and try to
            # ping again.
            logging.info('Failed to ping DUT on ipv6: %s. Cold resetting',
                         dut_ipv6)
            servo_proxy._power_state.reset()
            time.sleep(self.RESET_TIMEOUT_S)
        dut_ipv4 = None
        try:
            # Pass |server_utils| here as it implements the same interface
            # as a host to run things locally i.e. on the autoserv runner.
            dut_ipv4 = self._ip_info_from_host(server_utils, dut_ipv6, 'ipv4',
                                               'autoserv')
            return dut_ipv4
        except error.TestFail:
            logging.info('Failed to retrieve the DUT ipv4 directly. '
                         'Going to attempt to tunnel request through '
                         'labstation and forgive the error for now.')
        # Lastly, attempt to run the command from the labstation instead
        # to guard against networking issues.
        dut_ipv4 = self._ip_info_from_host(servo_host_proxy, dut_ipv6, 'ipv4',
                                           'autoserv')
        return dut_ipv4

    def _set_dut_stable_version(self, dut_host):
        """Helper method to set stable_version in DUT host.

        @param dut_host: CrosHost object representing the DUT.
        """
        logging.info('Setting stable_version to %s for DUT host.',
                     self.cros_version)
        host_info = dut_host.host_info_store.get()
        host_info.stable_versions['cros'] = self.cros_version
        dut_host.host_info_store.commit(host_info)

    def _get_dut_info_from_config(self):
        """Get DUT info from json config file.

        @returns a list of dicts that each dict represents a dut.
        """
        ctrl_path = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                                 'labstation_to_dut_map.json')
        with open(ctrl_path, 'r') as f:
            data = json.load(f, object_hook=self._byteify)
            # create a default dut dict in case the servohost is not in config
            # map, this is normally happened in local testing.
            default_dut = {
                'hostname': None,
                'servo_port': '9999',
                'servo_serial': None
            }
            return data.get(self.labstation_host.hostname, [default_dut])

    def _byteify(self, data, ignore_dicts=False):
        """Helper method to convert unicode to string.
        """
        if isinstance(data, unicode):
            return data.encode('utf-8')
        if isinstance(data, list):
            return [self._byteify(item, ignore_dicts=True) for item in data]
        if isinstance(data, dict) and not ignore_dicts:
            return {
                self._byteify(key, ignore_dicts=True):
                    self._byteify(value, ignore_dicts=True)
                for key, value in data.iteritems()
            }
        return data

    def _setup_servod(self):
        """Setup all servod instances under servohost for later testing.
        """
        for dut in self.dut_list:
            # Use board: nami as default for local testing.
            board = dut.get('board', 'nami')
            port = dut.get('servo_port')
            serial = dut.get('servo_serial')

            logging.info('Setting up servod for port %s', port)

            # Stop existing servod instance.
            stop_servod_cmd = 'stop servod PORT=%s' % port
            self.labstation_host.run(stop_servod_cmd, ignore_status=True)
            # Wait for existing servod turned down.
            time.sleep(3)
            # Then, restart servod ourselves.
            start_servod_cmd = 'start servod BOARD=%s PORT=%s' % (board, port)
            if serial:
                start_servod_cmd += ' SERIAL=%s' % serial
            self.labstation_host.run(start_servod_cmd)
            # Give servod plenty of time to come up.
            time.sleep(40)
            try:
                validate_cmd = 'servodutil show -p %s' % port
                self.labstation_host.run_grep(validate_cmd,
                    stdout_err_regexp='No servod scratch entry found.')
            except error.AutoservRunError:
                raise error.TestFail('Servod did not come up on labstation.')

    def initialize(self, host, config=None):
        """Setup servod on |host| to run subsequent tests.

        @param host: LabstationHost object representing the servohost.
        @param config: the args argument from test_that in a dict.
        """
        # Save the host.
        self.labstation_host = host
        # Make sure recovery is quick in case of failure.
        self.job.fast = True
        # Get list of duts under the servohost.
        self.dut_list = self._get_dut_info_from_config()
        # Setup servod for all duts.
        self._setup_servod()
        # We need a cros build number for testing download image to usb and
        # use servo to reimage DUT purpose. So copying labstation's
        # stable_version here since we don't really care about which build
        # to install on the DUT.
        self.cros_version = (
            self.labstation_host.host_info_store.get().cros_stable_version)

        # collect user input args that used for local testing.
        self.dut_ip = None
        if config:
            if 'dut_ip' in config:
                # Retrieve DUT ip from args if caller specified it.
                self.dut_ip = config['dut_ip']
            if 'cros_version' in config:
                # We allow user to override a cros image build.
                self.cros_version = config['cros_version']


    def run_once(self, local=False):
        """Run through the test sequence.

        @param local: whether a test image is already on the usb stick.
        """
        # Servod came up successfully - build a ServoHost and CrosHost for
        # later testing to verfiy servo functionality. Since we only need
        # one CrosHost so we just pick the first one in the dut list.
        dut_hostname = self.dut_list[0].get('hostname') or self.dut_ip
        servo_port = self.dut_list[0].get('servo_port')
        servo_serial = self.dut_list[0].get('servo_serial')
        servo_args = {
            servo_constants.SERVO_HOST_ATTR: self.labstation_host.hostname,
            servo_constants.SERVO_PORT_ATTR: servo_port,
            servo_constants.SERVO_SERIAL_ATTR: servo_serial,
            'is_in_lab': False,
        }
        # Close out this host as the test will restart it as a servo host.
        self.labstation_host.close()
        self.labstation_host, servo_state = servo_host.create_servo_host(
            None, servo_args)
        self.labstation_host.connect_servo()
        servo_proxy = self.labstation_host.get_servo()
        if not dut_hostname:
            dut_hostname = self.get_dut_on_servo_ip(self.labstation_host)
        logging.info('Running the DUT side on DUT %r', dut_hostname)
        dut_host = factory.create_host(dut_hostname)
        dut_host.set_servo_host(self.labstation_host)

        # Copy labstation's stable_version to dut_host for later test consume.
        # TODO(xianuowang@): remove this logic once we figured out how to
        # propagate DUT's stable_version to the test.
        self._set_dut_stable_version(dut_host)

        if not self.job.run_test('servo_Verification', host=dut_host,
                                 local=local, subdir_tag=servo_port):
            raise error.TestFail('At least one test failed.')

    def cleanup(self):
        """Clean up by stopping the servod instance again."""
        self.labstation_host.run_background('stop servod PORT=9999')
