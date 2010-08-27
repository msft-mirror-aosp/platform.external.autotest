# -*- coding: utf-8 -*-
#
# Copyright (c) 2010 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.


# DESCRIPTION :
#
# This is a factory test to test external SD and USB ports.


import cairo
import gobject
import gtk
import pango
import os
import sys

from autotest_lib.client.bin import factory
from autotest_lib.client.bin import factory_ui_lib as ful
from autotest_lib.client.bin import test
from autotest_lib.client.bin import utils
from autotest_lib.client.common_lib import error


_STATE_WAIT_INSERT = 1
_STATE_WAIT_REMOVE = 2

_INSERT_FMT_STR = lambda t: 'insert %s drive...\n插入%s存儲...' % (t, t)
_REMOVE_FMT_STR = lambda t: 'remove %s drive...\n提取%s存儲...' % (t, t)
_TESTING_FMT_STR = lambda t:'testing %s...\n%s 檢查當中...' % (t, t)
_ERR_TOO_MANY_REMOVE_FMT_STR = \
        lambda target_dev, removed_dev: \
            'Too many device removed (%s). Please only remove %s.\n' \
            '有太多外部儲存裝置被移除 (%s)，請只移除 %s 即可\n' % \
                    (removed_dev, target_dev, removed_dev, target_dev)
_ERR_DEV_NOT_REMOVE_FMT_STR = \
        lambda t: 'Please remove %s.\n請移除 %s\n' % (t, t)

def find_root_dev():
    rootdev = utils.system_output('rootdev')
    return os.path.basename(rootdev[:-1])


def find_all_storage_dev():
    lssys = utils.run('ls -d /sys/block/sd*')
    devices = lssys.stdout.rsplit('\n')
    new_devices = set(os.path.basename(d.rstrip()) for d in devices if d)
    return new_devices


class factory_ExternalStorage(test.test):
    version = 1
    preserve_srcdir = True

    def expose_event(self, widget, event):
        context = widget.window.cairo_create()
        context.set_source_surface(self._image, 0, 0)
        context.paint()
        return True

    def rescan_storage(self, subtest_tag):
        if self._state == _STATE_WAIT_INSERT:
            new_devices = find_all_storage_dev()
            diff = new_devices - self._devices
            if diff:
                self._devices = new_devices
                factory.log('found new devs : %s' % diff)
                self._target_device = diff.pop()
                devpath = '/dev/%s' % self._target_device
                self._prompt.set_text(_TESTING_FMT_STR(devpath))
                self._image = self.testing_image
                self._pictogram.queue_draw()
                gtk.main_iteration()
                test._result = self.job.run_test('hardware_StorageFio',
                                                 dev=devpath,
                                                 quicktest=True,
                                                 tag=subtest_tag)
                self._prompt.set_text(_REMOVE_FMT_STR(self._media))
                self._state = _STATE_WAIT_REMOVE
                self._image = self.removal_image
                self._pictogram.queue_draw()
        else:
            diff = self._devices - find_all_storage_dev()
            if len(diff) > 1:
                self._error += _ERR_TOO_MANY_REMOVE_FMT_STR(
                        self._target_device, diff)
            if diff and self._target_device not in diff:
                self._error += _ERR_DEV_NOT_REMOVE_FMT_STR(
                        self._target_device)
            if diff:
                gtk.main_quit()
        return True

    def run_once(self,
                 subtest_tag=None,
                 media=None):

        factory.log('%s run_once' % self.__class__)

        self._error = ''

        os.chdir(self.srcdir)

        self._media = media
        factory.log('media = %s' % media)

        self.insertion_image = cairo.ImageSurface.create_from_png(
            '%s_insert.png' % media)
        self.removal_image = cairo.ImageSurface.create_from_png(
            '%s_remove.png' % media)
        self.testing_image = cairo.ImageSurface.create_from_png(
            '%s_testing.png' % media)

        image_size_set = set([(i.get_width(), i.get_height()) for
                              i in [self.insertion_image,
                                    self.removal_image,
                                    self.testing_image]])
        assert len(image_size_set) == 1
        image_size = image_size_set.pop()

        factory.log('subtest_tag = %s' % subtest_tag)

        label = gtk.Label('')
        label.modify_font(pango.FontDescription('courier new condensed 20'))
        label.set_alignment(0.5, 0.5)
        label.modify_fg(gtk.STATE_NORMAL, gtk.gdk.color_parse('light green'))
        self._prompt = label

        self._prompt.set_text(_INSERT_FMT_STR(self._media))
        self._state = _STATE_WAIT_INSERT
        self._image = self.insertion_image
        self._result = False
        self._devices = find_all_storage_dev()
        gobject.timeout_add(250, self.rescan_storage, subtest_tag)

        drawing_area = gtk.DrawingArea()
        drawing_area.set_size_request(*image_size)
        drawing_area.connect('expose_event', self.expose_event)
        self._pictogram = drawing_area

        vbox = gtk.VBox()
        vbox.pack_start(drawing_area, False, False)
        vbox.pack_start(label, False, False)

        test_widget = gtk.EventBox()
        test_widget.modify_bg(gtk.STATE_NORMAL, gtk.gdk.color_parse('black'))
        test_widget.add(vbox)

        ful.run_test_widget(self.job, test_widget)

        if self._error:
            raise error.TestFail(self._error)

        factory.log('%s run_once finished' % self.__class__)
