# Lint as: python2, python3
# Copyright 2024 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import os

from autotest_lib.client.bin import utils
from autotest_lib.client.common_lib import error


class FlossTelephonyHIDDevice(object):
    """class interacts with telephony UHID device created by floss"""

    UHID_REPORT_ID = 1
    # uhid input report
    UHID_INPUT_REPORT_SIZE = 2
    UHID_INPUT_HOOK_SWITCH = 1 << 0
    UHID_INPUT_PHONE_MUTE = 1 << 1
    # uhid output report
    UHID_OUTPUT_RING = 1 << 0
    UHID_OUTPUT_OFF_HOOK = 1 << 1
    UHID_OUTPUT_MUTE = 1 << 2

    def __init__(self):
        self.hid_device = None
        self.output_report = bytearray([self.UHID_REPORT_ID, 0])

    def __del__(self):
        self.close_telephony_device()

    def open(self, device_name):
        """Opens the target HID device on the DUT in read/write binary mode.

        The device is located in the /dev folder and typically follows
        the naming convention /dev/hidraw*.
        It is possible for having multiple HID devices on the DUT.
        To distinguish and identify the correct device, the function
        initially use device name and udevadm to get correct device id.
        Then uses the device id and udevadm to determine the
        corresponding device.

        @param device_name: name of device. e.g. RASPI_AUDIO
        """
        target_hid_device_id = ''
        target_hid_device_path = ''
        hid_device_folder = '/sys/bus/hid/devices'
        device_folder = '/dev'
        for hid_device_id in os.listdir(hid_device_folder):
            cmd = [
                    'udevadm', 'info',
                    os.path.join(hid_device_folder, hid_device_id)
            ]
            udevadm_output = utils.run(cmd).stdout
            if (device_name in udevadm_output):
                target_hid_device_id = hid_device_id
                break
        if target_hid_device_id == '':
            raise error.TestError(f'No hid device id found for {device_name}')

        for hid_device in os.listdir(device_folder):
            if (hid_device.startswith('hidraw')):
                hid_device_path = os.path.join(device_folder, hid_device)
                cmd = ['udevadm', 'info', f'--name={hid_device_path}']
                udevadm_output = utils.run(cmd).stdout
                if target_hid_device_id in udevadm_output:
                    target_hid_device_path = hid_device_path
                    break
        if target_hid_device_path == '':
            raise error.TestError(f'No hid device found for {device_name}')
        self.hid_device = open(target_hid_device_path, "r+b")

    def close(self):
        """close the hid device file if already opened."""
        if self.hid_device != None:
            self.hid_device.close()

    def _write(self, output_report):
        """write binary output report to hid telephony device.

        @param output_report: bytearray of output report to hid
        telephony device.
        """
        self.hid_device.write(output_report)
        self.hid_device.flush()

    def _read(self):
        """read binary input report from hid telephony device.

        @return: bytearray of input report from hid telephony device.
        """
        ret = bytearray(self.hid_device.read(self.UHID_INPUT_REPORT_SIZE))
        if (len(ret) < self.UHID_INPUT_REPORT_SIZE):
            raise error.TestError(f'Not enougth input report length.')
        return ret

    def send_incoming_call(self):
        """send ring event as output report to hid telephony device."""
        self.output_report[1] |= self.UHID_OUTPUT_RING
        self._write(self.output_report)

    def send_answer_call(self):
        """send stop ringing event and off-hook(active call) as output report to
        hid telephony device.
        """
        self.output_report[1] &= ~self.UHID_OUTPUT_RING
        self.output_report[1] |= self.UHID_OUTPUT_OFF_HOOK
        self._write(self.output_report)

    def send_reject_call(self):
        """send stop ringing event and off-hook(reject call) as output
        report to hid telephony device.
        """
        self.output_report[1] &= ~self.UHID_OUTPUT_RING
        self.output_report[1] &= ~self.UHID_OUTPUT_OFF_HOOK
        self._write(self.output_report)

    def send_hangup_call(self):
        """send off-hook(hangup call) as output report to hid telephony
        device.
        """
        self.output_report[1] &= ~self.UHID_OUTPUT_OFF_HOOK
        self._write(self.output_report)

    def send_mic_mute(self, mute):
        """send micphone mute event as output report to hid telephony
        device.

        @param mute: True if is muted. False otherwise.
        """
        if (mute):
            self.output_report[1] |= self.UHID_OUTPUT_MUTE
        else:
            self.output_report[1] &= ~self.UHID_OUTPUT_MUTE
        self._write(self.output_report)

    def get_input_event(self):
        """read input report from hid telephony device and parse event
        data from telephony device input report into a dictionary.

        @return:
            A dictionary with two keys: "hook-switch" and "phone-mute,"
            with bool value.
            hook-switch: active call exist or not.
            phone-mute:  microphone mute or not.
        """
        ret = {"hook-switch": False, "phone-mute": False}
        input_report = self._read()
        ret["hook-switch"] = bool(input_report[1]
                                  & self.UHID_INPUT_HOOK_SWITCH)
        ret["phone-mute"] = bool(input_report[1] & self.UHID_INPUT_PHONE_MUTE)
        return ret
