# Lint as: python2, python3
# Copyright (c) 2022 The Chromium OS Authors.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import logging

from autotest_lib.client.common_lib import error
from autotest_lib.client.common_lib.cros import path_utils
from autotest_lib.server import site_linux_rpi


class RPiHackRFRunner(site_linux_rpi.LinuxRPi):
    """Linux RaspberryPi with HackRF capabilities for WiFiTest class."""

    RF_DATA_FILES_FOLDER = '/etc/hackrf_files'
    LATEST_FIRMWARE_VERSION = '2021.03.1'
    # TODO (b/239568628): HackRF supports sample rates in the 8MHz-20MHz range,
    # chose 10MHz as the default arbitrarily but need to update the sample rate
    # after experimentation with the noisy environment tests.
    DEFAULT_SAMPLE_RATE = 10000000

    def __init__(self, host):
        """Build a RPiHackRFRunner.

        @param host: Host object representing the remote machine.
        """
        super(RPiHackRFRunner, self).__init__(
                host,
                role=site_linux_rpi.RPiRole.HACKRF_RUNNER)
        self._command_hackrf_info = None
        self._hackrf_serial_number = None
        self._hackrf_firmware_version = None
        self.__setup()


    def __setup(self):
        """Setup this system.

        Can be used to complete initialization of a RaspberryPi object that is
        being used a HackRF Runner, or to re-establish a good state after a
        reboot.
        """
        self.verify_hackrf_commands()


    def close(self):
        """Close global resources held by this system."""
        self.stop_broadcasting_file()
        super(RPiHackRFRunner, self).close()


    # HackRF-specific functions
    def install_rf_data_file(self, rf_data_file):
        """ Install a radio frequency data file on the HackRF Runner.

        @param rf_data_file: string name of the radio frequency data file to be
                installed on the HackRF Runner including the absolute path to it
                on the DUT.
        """
        # Make sure the directory exists.
        self.host.run('mkdir -p %s' % self.RF_DATA_FILES_FOLDER)
        try:
            self.host.send_file('%s' % rf_data_file,
                                self.RF_DATA_FILES_FOLDER)
        except error.AutoservRunError:
            logging.error('Failed to install RF data file on the HackRF Runner')
            raise


    def delete_rf_data_file(self, rf_data_file=None):
        """ Remove the specified file or all radio frequency data files from the
        HackRF Runner.

        @param rf_data_file: string name of the radio frequency data file to be
                deleted including the absolute path to it on the HackRF Runner
                or None.
        """
        if rf_data_file:
            self.host.run('rm %s' % rf_data_file)
            logging.info('Deleted the RF data file %s', rf_data_file)
        else:
            self.host.run('rm %s/*', self.RF_DATA_FILES_FOLDER)
            logging.info('Deleted all the RF data files in the directory %s',
                         self.RF_DATA_FILES_FOLDER)


    def stop_broadcasting_file(self):
        """ Interrupt the broadcasting of RF data on the HackRF."""
        self._kill_process_instance(process='hackrf_transfer')


    def verify_hackrf_commands(self):
        """ Verify that the HackRF runner can run commands on the HackRF.

        Checks whether the HackRF Runner has the necessary packages and installs
        them otherwise. Extracts the serial number and firmware version of the
        first HackRF if there are several connected HackRFs. Requests for the
        firmware to be updated if it is out of date. Tests whether the HackRF
        can transmit radio frequency data.
        """
        # Ensure that the HackRF Runner has the necessary packages.
        try:
            self._command_hackrf_info = path_utils.must_be_installed(
                    'hackrf_info',
                    host=self.host)
        except error.TestError:
            logging.warning('Don\'t have hackrf commands installed. Proceeding '
                            'to install the necessary packages...')
            self.host.run('sudo apt-get update')
            self.host.run('sudo apt-get install -y hackrf')
            self._command_hackrf_info = path_utils.must_be_installed(
                    'hackrf_info',
                    host=self.host)
        hackrf_information = self.host.run(self._command_hackrf_info,
                                           ignore_status=True).stdout
        if 'No HackRF boards found' in hackrf_information:
            raise error.TestNAError('Could not identify any connected HackRFs.')

        # Stop broadcasting RF data before extracting the firmware version
        # because hackrf_info doesn't display firmware version unless the HackRF
        # is freed up.
        self.stop_broadcasting_file()
        # Extract the serial number and firmware version of first HackRF.
        first_hackrf = hackrf_information.split('Found HackRF')[1]
        for line in first_hackrf.split('\n'):
            if line.split(':')[0] == 'Serial number':
                self._hackrf_serial_number = line.split(':')[1].strip()
            elif line.split(':')[0] == 'Firmware Version':
                self._hackrf_firmware_version = line.split(':')[1].split()[0]
        logging.debug('HackRF Serial Number: %s', self._hackrf_serial_number)
        logging.debug('HackRF Firmware Version: %s',
                      self._hackrf_firmware_version)

        # Verify that HackRF firmware version is up-to-date.
        if self.LATEST_FIRMWARE_VERSION != self._hackrf_firmware_version:
            logging.error('Tests may fail because your HackRF firmware is not '
                          'up-to-date. '
                          'See: https://hackrf.readthedocs.io/en/latest/updating_firmware.html#updating-the-spi-flash-firmware',
                          self._hackrf_serial_number)
        else:
            logging.debug('HackRF firmware is up to date')

        # Test that you can transmit radio waves from the HackRF.
        # Using dev/zero eliminates dependency on install_rf_data_file working.
        tx_test = self.broadcast_file(rf_data_file='/dev/zero', duration=3,
                                      run_in_background=False)
        if 'MiB/second' not in tx_test:
            logging.error('Unable to transmit RF data')
            raise
        else:
            duration = tx_test.split('\n')[-7].split(':')[1].strip()
            logging.debug('Successfully transmitted sample RF data during '
                          'HackRF validation for %s', duration)


    def broadcast_file(self, rf_data_file, duration, frequency=None, gain=None,
                       run_in_background=False):
        """ Broadcast radio signals on the HackRF based on the radio frequency
        data file.

        @param rf_data_file: string name of the radio frequency data file to be
                broadcast on the HackRF including the absolute path to it on the
                HackRF Runner.
        @param duration: int desired duration for how long the rf_data_file
                should be played in seconds.
        @param frequency: int frequency at which to play the radio signals in Hz
                should be within the antenna frequency range.
        @param gain: int the strength of the signal being trasmitted in dB,
                should be in the 0-47dB range.
        @param run_in_background: bool True iff the rf_data_file should be
                broadcasted in the background.
        @return PID of the hackrf_transfer process if run_in_background is True
                otherwise return frequency, sample rate and how much radio
                frequency data is broadcast per second.
        """
        transmit_command = 'hackrf_transfer -R -t %s -d %s' % (rf_data_file,
                           self._hackrf_serial_number)
        sample_rate = self.DEFAULT_SAMPLE_RATE
        num_samples = sample_rate * duration
        # Tests were flaky when the number of samples was an exact multiple
        # of the sample_rate: the HackRF tries to transmit RF data in an
        # additional second at which point hardly any data is left. So we
        # are transferring 1% less data in the last second to prevent the
        # HackRF from forcing an additional second for RF data transfer
        # and the flaky error is avoided.
        num_samples -= int(sample_rate * 0.01)
        transmit_command += ' -n %s' % str(num_samples)
        transmit_command += ' -s %s' % str(sample_rate)
        if frequency: transmit_command += ' -f %s' % str(frequency)
        if gain:
            if gain < 0 or gain > 47 or not isinstance(gain, int):
                logging.error('Please specify an integer gain in the 0-47dB'
                              'range')
                raise
            transmit_command += ' -x %s' % str(gain)
        if run_in_background:
            return self.host.run_background(transmit_command)
        else:
            return self.host.run(transmit_command, ignore_status=True).stderr