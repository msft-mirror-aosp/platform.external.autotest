# Lint as: python2, python3
# Copyright 2013 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import dbus, logging, numpy, os, random, shutil, tempfile, time

from autotest_lib.client.bin import test, utils
from autotest_lib.client.common_lib import error
from autotest_lib.client.common_lib.cros.network import interface
from autotest_lib.client.cros import dbus_util, upstart
from autotest_lib.client.cros.networking import shill_proxy
from autotest_lib.client.cros.power import power_suspend, power_utils, sys_power

class power_SuspendStress(test.test):
    """Class for test."""
    version = 1

    def initialize(self, duration, idle=False, init_delay=0, min_suspend=0,
                   min_resume=5, max_resume_window=3, check_connection=True,
                   suspend_iterations=None, suspend_state='',
                   modemfwd_workaround=False):
        """
        Entry point.

        @param duration: total run time of the test
        @param idle: use sys_power.idle_suspend method.
                (use with stub_IdleSuspend)
        @param init_delay: wait this many seconds before starting the test to
                give parallel tests time to get started
        @param min_suspend: suspend durations will be chosen randomly out of
                the interval between min_suspend and min_suspend + 3 seconds.
        @param min_resume: minimal time in seconds between suspends.
        @param max_resume_window: maximum range to use between suspends. i.e.,
                we will stay awake between min_resume and min_resume +
                max_resume_window seconds.
        @param check_connection: If true, we check that the network interface
                used for testing is up after resume. Otherwsie we reboot.
        @param suspend_iterations: number of times to attempt suspend.  If
                !=None has precedence over duration.
        @param suspend_state: Force to suspend to a specific
                state ("mem" or "freeze"). If the string is empty, suspend
                state is left to the default pref on the system.
        @param modemfwd_workaround: disable the modemfwd daemon as a workaround
                for its bad behavior during modem firmware update.
        """
        self._endtime = time.time()
        if duration:
            self._endtime += duration
        self._init_delay = init_delay
        self._min_suspend = min_suspend
        self._min_resume = min_resume
        self._max_resume_window = max_resume_window
        self._check_connection = check_connection
        self._suspend_iterations = suspend_iterations
        self._suspend_state = suspend_state
        self._modemfwd_workaround = modemfwd_workaround
        self._method = sys_power.idle_suspend if idle else sys_power.suspend_for

    def _done(self):
        if self._suspend_iterations != None:
            self._suspend_iterations -= 1
            return self._suspend_iterations < 0
        return time.time() >= self._endtime

    def _get_default_network_interface(self):
        iface = shill_proxy.ShillProxy().get_default_interface_name()
        if not iface:
            return None
        return interface.Interface(iface)

    def run_once(self):
        time.sleep(self._init_delay)

        # TODO(b/324513129): remove this once we have a better solution in place.
        # **DO NOT COPY-PASTE THIS CODE IF YOU ARE NOT AFFECTED BY b/324513129**
        # If you are affected by b/324513129, please add a comment on that bug
        # and retain this comment block in the new location.
        if not upstart.is_running('powerd'):
            logging.info('starting powerd because it is not running')
            upstart.restart_job('powerd')
        logging.info('waiting for powerd availability')
        dbus_util.get_dbus_object(dbus.SystemBus(),
                                  "org.chromium.PowerManager",
                                  "/org/chromium/PowerManager", 30)

        self._suspender = power_suspend.Suspender(
                self.resultsdir,
                method=self._method,
                suspend_state=self._suspend_state)
        # TODO(b/164255562) Temporary workaround for misbehaved modemfwd
        if self._modemfwd_workaround:
            utils.stop_service('modemfwd', ignore_status=True)
        # Find the interface which is used for most communication.
        # We assume the interface connects to the gateway and has the lowest
        # metric.
        if self._check_connection:
            iface = utils.poll_for_condition(
                        self._get_default_network_interface,
                        desc='Find default network interface')
            logging.info('Found default network interface: %s', iface.name)

        pmc_core_src_dir = '/sys/kernel/debug/pmc_core'
        pmc_core_results_dir = os.path.join(self.resultsdir, 'pmc_core')
        has_pmc_core_dir = os.path.exists(pmc_core_src_dir)
        if has_pmc_core_dir:
            if not os.path.exists(pmc_core_results_dir):
                os.mkdir(pmc_core_results_dir)

        has_stb_read = os.path.exists(power_utils.STB_READ_PATH)
        amd_pmc_dir = os.path.join(self.resultsdir, 'amd_pmc')
        stb_read_tempdir = None
        if has_stb_read:
            stb_read_tempdir = tempfile.mkdtemp(prefix='stb')
            if not os.path.exists(amd_pmc_dir):
                os.mkdir(amd_pmc_dir)

        suspend_iter = 1
        while not self._done():
            time.sleep(self._min_resume +
                       random.randint(0, self._max_resume_window))
            # Check the network interface to the caller is still available
            if self._check_connection:
                # Give a 3 minutes window for the network to come back:
                # check_ethernet.hook is restarting every minutes.
                # It could take 30s for the device to come back from storage
                # to vendor mode.
                # Give the hook several tries.
                # Note check_ethernet.hook could reboot the device itself
                # as well.
                try:
                    utils.poll_for_condition(iface.is_link_operational,
                                             timeout=180,
                                             desc='Link is operational')
                except utils.TimeoutError:
                    logging.error('Link to the server gone, reboot')
                    utils.system('reboot')
                    # Reboot may return; raise a TestFail() to abort too, even
                    # though the server likely won't see this.
                    raise error.TestFail('Link is gone; rebooting')

            logging.info("Suspend %d", suspend_iter)
            self._suspender.suspend(random.randint(0, 3) + self._min_suspend)

            if has_pmc_core_dir:
                for pmc_file in os.listdir(pmc_core_src_dir):
                    outfilename = f'{pmc_file}.{suspend_iter}'
                    shutil.copy(
                            os.path.join(pmc_core_src_dir, pmc_file),
                            os.path.join(pmc_core_results_dir, outfilename))
            if has_stb_read:
                outfilename = power_utils.AMD_STB_OUTFILE_STB_REPORT
                result = power_utils.decode_raw_stb_data(
                        stb_read_tempdir, power_utils.STB_READ_PATH)

                tempdir_outfilename = os.path.join(stb_read_tempdir,
                                                   outfilename)
                if not os.path.exists(tempdir_outfilename):
                    logging.warning("suspend %d: %s", suspend_iter,
                                    tempdir_outfilename)
                elif result is not None and result.exit_status == 0:
                    shutil.copy(
                            tempdir_outfilename,
                            os.path.join(amd_pmc_dir,
                                         f'{outfilename}.{suspend_iter}'))
                else:
                    logging.warning(
                            "suspend %d: decode_raw_stb_data completed with result %s",
                            suspend_iter, str(result))
            suspend_iter += 1

    def postprocess_iteration(self):
        if self._suspender.successes:
            keyvals = {'suspend_iterations': len(self._suspender.successes)}
            for key in self._suspender.successes[0]:
                values = [result[key] for result in self._suspender.successes]
                keyvals[key + '_mean'] = numpy.mean(values)
                keyvals[key + '_stddev'] = numpy.std(values)
                keyvals[key + '_min'] = numpy.amin(values)
                keyvals[key + '_max'] = numpy.amax(values)
            self.write_perf_keyval(keyvals)
        if self._suspender.failures:
            total = len(self._suspender.failures)
            iterations = len(self._suspender.successes) + total
            timeout = kernel = firmware = spurious = 0
            for failure in self._suspender.failures:
                if type(failure) is sys_power.SuspendTimeout: timeout += 1
                if type(failure) is sys_power.KernelError: kernel += 1
                if type(failure) is sys_power.FirmwareError: firmware += 1
                if type(failure) is sys_power.SpuriousWakeupError: spurious += 1
            if total == 1:
                # just throw it as is, makes aggregation on dashboards easier
                raise self._suspender.failures[0]
            raise error.TestFail('%d suspend failures in %d iterations (%d '
                    'timeouts, %d kernel warnings, %d firmware errors, %d '
                    'spurious wakeups)' %
                    (total, iterations, timeout, kernel, firmware, spurious))


    def cleanup(self):
        """
        Clean this up before we wait ages for all the log copying to finish...
        """
        self._suspender.finalize()
        if self._modemfwd_workaround:
            utils.start_service('modemfwd', ignore_status=True)
