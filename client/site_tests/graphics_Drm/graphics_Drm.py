# Copyright 2016 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import logging
import os
from autotest_lib.client.bin import test
from autotest_lib.client.common_lib import error
from autotest_lib.client.common_lib import utils
from autotest_lib.client.cros import service_stopper
from autotest_lib.client.cros.graphics import graphics_utils


class DrmTest(object):

    def __init__(self, name, command=None, **kargs):
        """
        @param name(str)
        @param command(str): The shell command to run. If None, then reuse 'name'.
        @param kargs: Test options
        """

        self._opts = {
            'timeout': 20,
            'display_required': True,
            'vulkan_required': False,
            'min_kernel_version': None
        }
        self._opts.update(kargs)
        self.name = name
        self._command = command
        if self._command is None:
            self._command = name

    def can_run(self):
        """Indicate if the test can be run on the configuration."""
        num_displays = graphics_utils.get_num_outputs_on()
        if num_displays == 0 and utils.get_device_type() == 'CHROMEBOOK':
            # Sanity check to guard against incorrect silent passes.
            logging.error('Error: found Chromebook without display.')
            return False
        return True

    def should_run(self):
        """Indicate if the test should be run on current configuration."""
        supported_apis = graphics_utils.GraphicsApiHelper().get_supported_apis()
        num_displays = graphics_utils.get_num_outputs_on()
        if num_displays == 0 and self._opts['display_required']:
            # If a test needs a display and we don't have a display,
            # consider it a pass.
            logging.warning('No display connected, skipping test.')
            return False
        if self._opts['vulkan_required'] and 'vk' not in supported_apis:
            # If a test needs vulkan to run and we don't have it,
            # consider it a pass
            logging.warning('Vulkan is required by test but is not '
                            'available on system. Skipping test.')
            return False
        if self._opts['min_kernel_version']:
            kernel_version = os.uname()[2]
            min_kernel_version = self._opts['min_kernel_version']
            if utils.compare_versions(kernel_version, min_kernel_version) < 0:
                logging.warning('Test requires kernel version >= %s,'
                                'have version %s. Skipping test.'
                                % (min_kernel_version, kernel_version))
                return False
        return True

    def run(self):
        try:
            # TODO(pwang): consider TEE to another file if drmtests keep
            # spewing so much output.
            cmd_result = utils.run(
                self._command,
                timeout=self._opts['timeout'],
                stderr_is_expected=True,
                verbose=True,
                stdout_tee=utils.TEE_TO_LOGS,
                stderr_tee=utils.TEE_TO_LOGS
            )
            logging.info('Passed: %s', self._command)
            logging.debug('Duration: %s: (%0.2fs)'
                          % (self._command, cmd_result.duration))
            return True
        except error.CmdTimeoutError as e:
            logging.error('Failed: Timeout while running %s (timeout=%0.2fs)'
                          % (self._command, self._opts['timeout']))
            logging.debug(e)
            return False
        except error.CmdError as e:
            logging.error('Failed: %s (exit=%d)' % (self._command,
                                                    e.result_obj.exit_status))
            logging.debug(e)
            return False
        except Exception as e:
            logging.error('Failed: Unexpected exception while running %s'
                          % self._command)
            logging.debug(e)
            return False

drm_tests = {
    test.name: test
    for test in (
        DrmTest('atomictest', 'atomictest -t primary_pageflip',
                min_kernel_version='4.4'),
        DrmTest('drm_cursor_test'),
        DrmTest('gamma_test'),
        DrmTest('linear_bo_test'),
        DrmTest('mmap_test'),
        DrmTest('null_platform_test'),
        DrmTest('swrast_test', display_required=False),
        DrmTest('vgem_test', display_required=False),
        DrmTest('vk_glow', vulkan_required=True),
    )
}

class graphics_Drm(graphics_utils.GraphicsTest):
    """Runs one, several or all of the drm-tests."""
    version = 1
    _services = None

    def initialize(self):
        super(graphics_Drm, self).initialize()
        self._services = service_stopper.ServiceStopper(['ui'])
        self._services.stop_services()

    def cleanup(self):
        if self._services:
            self._services.restore_services()
        super(graphics_Drm, self).cleanup()

    # graphics_Drm runs all available tests if tests = None.
    def run_once(self, tests=None, perf_report=False):
        self._test_failure_report_enable = perf_report
        for test in drm_tests.itervalues():
            if tests and test.name not in tests:
                continue

            logging.info('-----------------[%s]-----------------' % test.name)
            if test.should_run():
                if test.can_run():
                    logging.debug('Running test %s.', test.name)
                    passed = test.run()
                    if not passed:
                        self.add_failures(test.name)
                else:
                    logging.info('Failed: test %s can not be run on current '
                                 'configurations.' % test.name)
                    self.add_failures(test.name)
            else:
                logging.info('Skipping test: %s.' % test.name)

        if self.get_failures():
            raise error.TestFail('Failed: %s' % self.get_failures())
