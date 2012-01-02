# Copyright (c) 2011 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

''' A module for extracting trackpad device file properties '''

import glob
import logging
import os
import re

import trackpad_util

from autotest_lib.client.bin import utils
from autotest_lib.client.bin.input.linux_input import *
from autotest_lib.client.common_lib import error
from trackpad_util import read_trackpad_test_conf, get_trackpad_device_file


class TrackpadDevice:
    ''' Management of the trackpad device file

    It is used
    (1) to extract trackpad device file properties such as device event
        playback times, and
    (2) to play back the device packets. The device file is usually
        '/dev/input/event*'.
    '''
    PLAYBACK_PROGRAM = 'evemu-play'
    DEVICE_TIME_FILE = '/tmp/time.out'

    def __init__(self, conf_path):
        self._set_dev_type_and_code()
        if self._get_trackpad_driver() == 'synaptics':
            self._ungrab_device()
        self.trackpad_device_file, msg = get_trackpad_device_file()
        if self.trackpad_device_file is None:
            raise error.TestError(msg)
        logging.info(msg)

    def _finger_i_on_MTB(self, i):
        ''' The i-th finger touches the trackpad in MTB protocol '''
        return '%s %s %d'  % (self.EV_ABS, self.ABS_MT_SLOT, i - 1)

    def _set_dev_type_and_code(self):
        ''' Set device code

        Device event types and codes are imported from linux_input.
        '''
        ev_format = '%04x'
        ev_code_x = ev_format % ABS_MT_POSITION_X
        ev_code_y = ev_format % ABS_MT_POSITION_Y
        self.ev_code_dict = {'left':  (ev_code_x,),
                             'right': (ev_code_x,),
                             'up':    (ev_code_y,),
                             'down':  (ev_code_y,),
                             None:    (ev_code_x, ev_code_y)}
        # Event types
        self.EV_KEY = ev_format % EV_KEY
        self.EV_ABS = ev_format % EV_ABS

        # Event codes
        self.ABS_MT_SLOT = ev_format % ABS_MT_SLOT
        self.ABS_MT_TRACKING_ID = ev_format % ABS_MT_TRACKING_ID
        self.BTN_TOOL_FINGER = ev_format % BTN_TOOL_FINGER
        self.BTN_TOOL_DOUBLETAP = ev_format % BTN_TOOL_DOUBLETAP
        self.BTN_TOOL_TRIPLETAP = ev_format % BTN_TOOL_TRIPLETAP

        # MTA: not supported at this time

        # MTB: the default MT type to use
        self.second_finger_on_MTB = self._finger_i_on_MTB(2)
        self.finger_off_MTB = '%s %s -1' % (self.EV_ABS,
                                            self.ABS_MT_TRACKING_ID)

        finger_MTB = '{0} %s {1}'
        finger_on_MTB = finger_MTB.format(self.EV_KEY, 1)
        finger_off_MTB = finger_MTB.format(self.EV_KEY, 0)

        self.dev_event = {
            '1st Finger Landed': finger_on_MTB  % self.BTN_TOOL_FINGER,
            '1st Finger Lifted': finger_off_MTB % self.BTN_TOOL_FINGER,
            '2nd Finger Landed': finger_on_MTB  % self.BTN_TOOL_DOUBLETAP,
            '2nd Finger Lifted': finger_off_MTB % self.BTN_TOOL_DOUBLETAP,
            '3rd Finger Landed': finger_on_MTB  % self.BTN_TOOL_TRIPLETAP,
            '3rd Finger Lifted': finger_off_MTB % self.BTN_TOOL_TRIPLETAP,
        }

    def _extract_playback_time(self, line):
        ''' Extract the actual event playback time from the line '''
        return int(float(line.split('playback ')[1]) * 1000)

    def _find_event_time(self, ev_seq):
        ''' Match the events in ev_seq against the device time file, and
        return the time stamps of the matched device events.
        '''
        ev_seq_len = len(ev_seq)
        if ev_seq_len == 0:
            return None

        with open(TrackpadDevice.DEVICE_TIME_FILE) as f:
            time_file = f.read().splitlines()

        ev = ev_seq.pop(0)
        for line in time_file:
            if ev in line:
                if len(ev_seq) == 0:
                    return self._extract_playback_time(line)
                ev = ev_seq.pop(0)
        return None

    def get_finger_time(self, ev_str):
        ''' Derive the device playback time when the 2nd finger touches '''
        ev_seq_MTB = [self.dev_event[ev_str]]
        return [self._find_event_time(ev_seq_MTB)]

    def get_2nd_finger_touch_time(self, direction):
        ''' Derive the device playback time when the 2nd finger touches '''
        ev_time = None
        # When the functionality is 'two_fingers_no_delay_2d' in config file,
        # check the ABS_MT_POSITION_X or ABS_MT_POSITION_Y event time.
        # Use the timestamp which occurs earlier.
        for ev_code in self.ev_code_dict[direction]:
            motion_code = '%s %s' % (self.EV_ABS, ev_code)
            ev_seq_MTB = [self.second_finger_on_MTB, motion_code]
            new_ev_time = self._find_event_time(ev_seq_MTB)
            ev_time = new_ev_time if ev_time is None else min(ev_time,
                                                              new_ev_time)
        return ev_time

    def get_2nd_finger_lifted_time(self):
        ''' Derive the device playback time when the 2nd finger is lifted '''
        ev_seq_MTB = [self.second_finger_on_MTB, self.finger_off_MTB]
        return self._find_event_time(ev_seq_MTB)

    def get_two_finger_touch_time_list(self):
        ''' Derive all device playback times when two fingers touch the pad '''
        with open(TrackpadDevice.DEVICE_TIME_FILE) as f:
            time_file = f.read().splitlines()

        ev = self.dev_event['2nd Finger Landed']
        touch_time_list = []
        for line in time_file:
            if ev in line:
                touch_time_list.append(self._extract_playback_time(line))
        return touch_time_list

    def _get_trackpad_driver(self):
        ''' Query which trackpad driver is used in xorg '''
        trackpad_drivers = read_trackpad_test_conf('trackpad_drivers', '.')
        xorg_log = read_trackpad_test_conf('xorg_log', '.')

        try:
            f = open(xorg_log)
        except IOError:
            raise error.TestError('Xorg log file %s does not exist.' % xorg_log)
        log_lines = f.read().splitlines()
        f.close()

        for line in log_lines:
            if 'LoadModule' in line:
                for driver in trackpad_drivers:
                    if driver in line:
                        logging.info('Trackpad driver "%s" is found.' % driver)
                        self.trackpad_driver = driver
                        return self.trackpad_driver
        raise error.TestError('Cannot find driver in %s.' %
                              str(trackpad_drivers))

    def _ungrab_device(self):
        ''' Ungrab the device if the driver is synaptics and is grabbed '''
        self.grab_value = -1
        display_environ = trackpad_util.Display().get_environ()
        synclient_list_cmd = ' '.join([display_environ, 'synclient -l'])
        self.grab_device = ' '.join([display_environ,
                                     'synclient GrabEventDevice=%d'])
        synclient_settings = utils.system_output(synclient_list_cmd)
        for line in synclient_settings.splitlines():
            if line.lstrip().startswith('GrabEventDevice'):
                self.grab_value = int(line.split('=')[1].strip())
                break
        logging.info('GrabEventDevice=%d.' % self.grab_value)
        if self.grab_value == -1:
            err_msg = 'Cannot find GrabEventDevice setting in "%s".'
            raise error.TestError(err_msg % synclient_list_cmd)
        # Ungrab the device only if it has been grabbed.
        elif self.grab_value == 1:
            try:
                utils.system(self.grab_device % 0)
            except:
                raise error.TestError('Fail to execute: %s' % ungrab_cmd)
            logging.info('The synaptics device file is ungrabbed now.')

    def playback(self, packet_data_file):
        option_slot0 = '--insert-slot0'
        play_cmd = '%s %s %s %s < %s' % (TrackpadDevice.PLAYBACK_PROGRAM,
                                      self.trackpad_device_file,
                                      option_slot0,
                                      TrackpadDevice.DEVICE_TIME_FILE,
                                      packet_data_file)
        utils.system(play_cmd)

    def __del__(self):
        # Grab the device again only if it was originally grabbed.
        if self.trackpad_driver == 'synaptics' and self.grab_value == 1:
            try:
                utils.system(self.grab_device % 1)
            except:
                raise error.TestError('Fail to execute: %s' % grab_cmd)
            logging.info('The synaptics device file is grabbed successfully.')

        # Remove the temporary device time file
        if os.path.exists(TrackpadDevice.DEVICE_TIME_FILE):
            try:
                os.remove(TrackpadDevice.DEVICE_TIME_FILE)
            except:
                logging.warn('Cannot remove the device time file: %s.' %
                             TrackpadDevice.DEVICE_TIME_FILE)
