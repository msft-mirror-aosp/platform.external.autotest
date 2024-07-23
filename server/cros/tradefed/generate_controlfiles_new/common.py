# Copyright 2023 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import collections

# Names for collect-tests-only jobs
_COLLECT = 'tradefed-run-collect-tests-only-internal'
_PUBLIC_COLLECT = 'tradefed-run-collect-tests-only'
_CTSHARDWARE_COLLECT = 'tradefed-run-collect-tests-only-hardware-internal'
_PUBLIC_CTSHARDWARE_COLLECT = 'tradefed-run-collect-tests-only-hardware'

# Name of the "all" job
_ALL = 'all'


class Config(collections.UserDict):
    """Dictionary holding config values and config-dependent helper methods."""

    def get_extension(self,
                      module,
                      abi,
                      revision,
                      is_public=False,
                      camera_facing=None,
                      hardware_suite=False,
                      abi_bits=None,
                      shard=(0, 1),
                      vm_force_max_resolution=False,
                      vm_tablet_mode=False):
        """Defines a unique string.

        Notice we chose module revision first, then abi, as the module revision
        changes regularly. This ordering makes it simpler to add/remove modules.
        @param module: CTS module which will be tested in the control file. If 'all'
                       is specified, the control file will runs all the tests.
        @param is_public: boolean variable to specify whether or not the bundle is
                       from public source or not.
        @param camera_facing: string or None indicate whether it's camerabox tests
                              for specific camera facing or not.
        @param abi_bits: 32 or 64 or None indicate the bitwidth for the specific
                         abi to run.
        @param shard: tuple of integers representing the shard index.
        @param vm_force_max_resolution: boolean variable indicating whether max
                                        resolution is enforced on VM display.
        @param vm_tablet_mode: boolean variable indicating whether enable
                                        tablet mode for VM testing.
        @return string: unique string for specific tests. If public=True then the
                        string is "<abi>.<module>", otherwise, the unique string is
                        "internal.<abi>.<module>" for internal. Note that if abi is empty,
                        the abi part is omitted.
        """
        ext_parts = []
        if not self.get('SINGLE_CONTROL_FILE') and not is_public:
            if module == _COLLECT:
                ext_parts = [revision]
            else:
                ext_parts = ['internal']
        if not self.get('SINGLE_CONTROL_FILE') and abi:
            ext_parts += [abi]
        ext_parts += [module]
        if camera_facing:
            ext_parts += ['camerabox', camera_facing]
        if hardware_suite and module not in self.get_collect_modules(
                is_public, hardware_suite):
            ext_parts += ['ctshardware']
        if vm_force_max_resolution:
            ext_parts += ['vmhires']
        if vm_tablet_mode:
            ext_parts += ['vmtablet']
        if not self.get('SINGLE_CONTROL_FILE') and abi and abi_bits:
            ext_parts += [str(abi_bits)]
        if shard != (0, 1):
            ext_parts += ['shard_%d_%d' % shard]
        return '.'.join(ext_parts)

    def servo_support_needed(self, modules, is_public=True):
        """Determines if servo support is needed for a module."""

        return not is_public and any(module in self['NEEDS_POWER_CYCLE']
                                     for module in modules)

    def wifi_info_needed(self, modules, is_public):
        """Determines if Wifi AP info needs to be retrieved."""
        return not is_public and any(module in self.get('WIFI_MODULES', [])
                                     for module in modules)

    def get_cts_hardware_modules(self, is_public):
        """Determines set of hardware modules based on is_public flag.

        Args:
            is_public: flag that is passed on command line when generating control files.
        Returns:
          set corresponding set of modules.
        """
        if is_public:
            return set(self.get('PUBLIC_HARDWARE_MODULES', []))
        else:
            return set(self.get('HARDWARE_MODULES', []))

    def get_dependencies(self, modules, abi, is_public, camera_facing):
        """Defines lab dependencies needed to schedule a module.

        @param module: CTS module which will be tested in the control file. If 'all'
                       is specified, the control file will runs all the tests.
        @param abi: string that specifies the application binary interface of the
                    current test.
        @param is_public: boolean variable to specify whether or not the bundle is
                          from public source or not.
        @param camera_facing: specify requirement of camerabox setup with target
                              test camera facing. Set to None if it's not camerabox
                              related test.
        """
        dependencies = ['arc']
        if abi in self['LAB_DEPENDENCY']:
            dependencies += self['LAB_DEPENDENCY'][abi]

        if camera_facing is not None:
            dependencies.append('camerabox_facing:' + camera_facing)

        extra_deps_map = self['PUBLIC_DEPENDENCIES'] if is_public else self[
                'LAB_DEPENDENCY']
        extra_deps = set()
        for module in modules:
            extra_deps.update(extra_deps_map.get(module, []))
        dependencies.extend(sorted(extra_deps))

        return ', '.join(dependencies)

    def get_job_retries(self, modules, is_public, suites):
        """Define the number of job retries associated with a module.

        @param module: CTS module which will be tested in the control file. If a
                       special module is specified, the control file will runs all
                       the tests without retry.
        @param is_public: true if the control file is for moblab (public) use.
        @param suites: the list of suites that the control file belongs to.
        """
        # TODO(haddowk): remove this when cts p has stabalized.
        if is_public:
            return self['CTS_JOB_RETRIES_IN_PUBLIC']
        retries = 1  # 0 is NO job retries, 1 is one retry etc.
        for module in modules:
            # We don't want job retries for module collection or special cases.
            if (module in self.get_collect_modules(is_public) or module == _ALL
                        or
                ('CtsDeqpTestCases' in self['EXTRA_MODULES']
                 and module in self['EXTRA_MODULES']['CtsDeqpTestCases'])):
                retries = 0
        return retries

    def get_max_retries(self, modules, abi, suites, is_public, shard):
        """Partners experiance issues where some modules are flaky and require more

           retries.  Calculate the retry number per module on moblab.
        @param module: CTS module which will be tested in the control file.
        @param shard: an integer tuple representing the shard index.
        """
        # Disable retries for sharded jobs for now, to avoid the
        # awkward retry behavior (see b/243725038).
        if shard != (0, 1):
            return 0

        retry = -1
        if is_public:
            if _ALL in self['PUBLIC_MODULE_RETRY_COUNT']:
                retry = self['PUBLIC_MODULE_RETRY_COUNT'][_ALL]

            # In moblab at partners we may need many more retries than in lab.
            for module in modules:
                if module in self['PUBLIC_MODULE_RETRY_COUNT']:
                    retry = max(retry,
                                self['PUBLIC_MODULE_RETRY_COUNT'][module])
        else:
            # See if we have any special values for the module, chose the largest.
            for module in modules:
                if module in self['CTS_MAX_RETRIES']:
                    retry = max(retry, self['CTS_MAX_RETRIES'][module])

        # Ugly overrides.
        # In bvt we don't want to hold the CQ/PFQ too long.
        if retry == -1 and 'suite:bvt-arc' in suites:
            retry = 3
        # Not strict as CQ for bvt-perbuild. Let per-module config take priority.
        if retry == -1 and 'suite:bvt-perbuild' in suites:
            retry = 3
        # During qualification we want at least 9 retries, possibly more.
        # TODO(kinaba&yoshiki): do not abuse suite names
        if self.get('QUAL_SUITE_NAMES') and \
                set(self['QUAL_SUITE_NAMES']) & set(suites):
            retry = max(retry, self['CTS_QUAL_RETRIES'])
        # Collection should never have a retry. This needs to be last.
        if modules.intersection(self.get_collect_modules(is_public)):
            retry = 0

        if retry >= 0:
            return retry
        # Default case omits the retries in the control file, so tradefed_test.py
        # can chose its own value.
        return None

    def get_max_result_size_kb(self, modules, is_public):
        """Returns the maximum expected result size in kB for autotest.

        @param modules: List of CTS modules to be tested by the control file.
        """
        for module in modules:
            if (module in self.get_collect_modules(is_public)
                        or module == 'CtsDeqpTestCases'):
                # CTS tests and dump logs for android-cts.
                return self['LARGE_MAX_RESULT_SIZE']
        # Individual module normal produces less results than all modules.
        return self['NORMAL_MAX_RESULT_SIZE']

    def has_precondition_escape(self, modules, is_public):
        """Determines if escape by pipes module is used in preconditions.

        @param modules: List of CTS modules to be tested by the control file.
        """
        commands = []
        for module in modules:
            if is_public:
                commands.extend(self['PUBLIC_PRECONDITION'].get(module, []))
            else:
                commands.extend(self['PRECONDITION'].get(module, []))
                commands.extend(self['LOGIN_PRECONDITION'].get(module, []))
        return any('pipes.' in cmd for cmd in commands)

    def get_extra_args(self, modules, is_public):
        """Generate a list of extra arguments to pass to the test.

        Some params are specific to a particular module, particular mode or
        combination of both, generate a list of arguments to pass into the template.

        @param modules: List of CTS modules to be tested by the control file.
        """
        extra_args = set()
        preconditions = []
        login_preconditions = []
        prerequisites = []
        for module in sorted(modules):
            if is_public:
                extra_args.add('warn_on_test_retry=False')
                extra_args.add('retry_manual_tests=True')
                preconditions.extend(self['PUBLIC_PRECONDITION'].get(
                        module, []))
            else:
                preconditions.extend(self['PRECONDITION'].get(module, []))
                login_preconditions.extend(self['LOGIN_PRECONDITION'].get(
                        module, []))
                prerequisites.extend(self['PREREQUISITES'].get(module, []))

        # Notice: we are just squishing the preconditions for all modules together
        # with duplicated command removed. This may not always be correct.
        # In such a case one should split the bookmarks in a way that the modules
        # with conflicting preconditions end up in separate control files.
        def deduped(lst):
            """Keep only the first occurrence of each element."""
            return [e for i, e in enumerate(lst) if e not in lst[0:i]]

        if preconditions:
            # To properly escape the public preconditions we need to format the list
            # manually using join.
            extra_args.add('precondition_commands=[%s]' %
                           ', '.join(deduped(preconditions)))
        if login_preconditions:
            extra_args.add('login_precondition_commands=[%s]' %
                           ', '.join(deduped(login_preconditions)))
        if prerequisites:
            extra_args.add("prerequisites=['%s']" %
                           "', '".join(deduped(prerequisites)))
        return sorted(list(extra_args))

    def get_test_length(self, modules):
        """ Calculate the test length based on the module name.

        To better optimize DUT's connected to moblab, it is better to run the
        longest tests and tests that require limited resources.  For these modules
        override from the default test length.

        @param module: CTS module which will be tested in the control file. If 'all'
                       is specified, the control file will runs all the tests.

        @return string: one of the specified test lengths:
                        ['FAST', 'SHORT', 'MEDIUM', 'LONG', 'LENGTHY']
        """
        length = 3  # 'MEDIUM'
        for module in modules:
            if module in self['OVERRIDE_TEST_LENGTH']:
                length = max(length, self['OVERRIDE_TEST_LENGTH'][module])
        return {
                1: 'FAST',
                2: 'SHORT',
                3: 'MEDIUM',
                4: 'LONG',
                5: 'LENGTHY'
        }[length]

    def get_test_priority(self, modules, is_public):
        """ Calculate the test priority based on the module name.

        On moblab run all long running tests and tests that have some unique
        characteristic at a higher priority (50).

        This optimizes the total run time of the suite assuring the shortest
        time between suite kick off and 100% complete.

        @param module: CTS module which will be tested in the control file.

        @return int: 0 if priority not to be overridden, or priority number otherwise.
        """
        if not is_public:
            return 0

        priority = 0
        overide_test_priority_dict = self.get('PUBLIC_OVERRIDE_TEST_PRIORITY',
                                              {})
        for module in modules:
            if module in overide_test_priority_dict:
                priority = max(priority, overide_test_priority_dict[module])
            elif (module in self['OVERRIDE_TEST_LENGTH']
                  or module in self['PUBLIC_DEPENDENCIES']
                  or module in self['PUBLIC_PRECONDITION']
                  or module.split('.')[0] in self['OVERRIDE_TEST_LENGTH']):
                priority = max(priority, 50)
        return priority

    def get_authkey(self, is_public):
        if is_public or not self['AUTHKEY']:
            return None
        return self['AUTHKEY']

    def get_camera_modules(self):
        """Gets a list of modules for arc-cts-camera-opendut."""
        return self.get('CAMERA_MODULES', [])

    def get_extra_artifacts(self, modules):
        artifacts = []
        for module in modules:
            if module in self['EXTRA_ARTIFACTS']:
                artifacts += self['EXTRA_ARTIFACTS'][module]
        return artifacts

    def get_extra_artifacts_host(self, modules):
        if not 'EXTRA_ARTIFACTS_HOST' in self:
            return

        artifacts = []
        for module in modules:
            if module in self['EXTRA_ARTIFACTS_HOST']:
                artifacts += self['EXTRA_ARTIFACTS_HOST'][module]
        return artifacts

    def calculate_timeout(self, modules, suites):
        """Calculation for timeout of tradefed run.

        Timeout is at least one hour, except if part of BVT_ARC.
        Notice these do get adjusted dynamically by number of ABIs on the DUT.
        """
        if 'suite:bvt-arc' in suites:
            return int(3600 * self['BVT_TIMEOUT'])
        if self.get('QUAL_SUITE_NAMES') and \
                self.get('QUAL_TIMEOUT') and \
                ((set(self['QUAL_SUITE_NAMES']) & set(suites)) and \
                not (_COLLECT in modules or _PUBLIC_COLLECT in modules)):
            return int(3600 * self['QUAL_TIMEOUT'])

        timeout = 0
        # First module gets 1h (standard), all other half hour extra (heuristic).
        default_timeout = int(3600 * self['CTS_TIMEOUT_DEFAULT'])
        delta = default_timeout
        for module in modules:
            if module in self['CTS_TIMEOUT']:
                # Modules that run very long are encoded here.
                timeout += int(3600 * self['CTS_TIMEOUT'][module])
            elif module.startswith('CtsDeqpTestCases.dEQP-VK.'):
                # TODO: Optimize this temporary hack by reducing this value or
                # setting appropriate values for each test if possible.
                timeout = max(timeout, int(3600 * 12))
            elif 'Jvmti' in module:
                # We have too many of these modules and they run fast.
                timeout += 300
            else:
                timeout += delta
                delta = default_timeout // 2
        return timeout

    def needs_push_media(self, modules):
        """Oracle to determine if to push several GB of media files to DUT."""
        if modules.intersection(set(self['NEEDS_PUSH_MEDIA'])):
            return True
        return False

    def needs_cts_helpers(self, modules):
        """Oracle to determine if CTS helpers should be downloaded from DUT."""
        if 'NEEDS_CTS_HELPERS' not in self:
            return False
        if modules.intersection(set(self['NEEDS_CTS_HELPERS'])):
            return True
        return False

    def enable_default_apps(self, modules):
        """Oracle to determine if to enable default apps (eg. Files.app)."""
        if modules.intersection(set(self['ENABLE_DEFAULT_APPS'])):
            return True
        return False

    def get_collect_modules(self, is_public, is_hardware=False):
        if is_public:
            if is_hardware:
                return set([_PUBLIC_CTSHARDWARE_COLLECT])
            return set([_PUBLIC_COLLECT])
        else:
            suffices = ['']
            if self.get('CONTROLFILE_WRITE_CAMERA', False):
                suffices.extend([".camerabox.front", ".camerabox.back"])
            if is_hardware:
                return set(_CTSHARDWARE_COLLECT + suffix
                           for suffix in suffices)
            return set(_COLLECT + suffix for suffix in suffices)

    def get_special_command_line(self, modules):
        """This function allows us to split a module like Deqp into segments."""
        cmd = []
        for module in sorted(modules):
            cmd += self['EXTRA_COMMANDLINE'].get(module, [])
        return cmd

    def get_tauto_hw_deps(self, source_type):
        """Returns the value for HW_DEPS control file field."""
        hw_deps_dev = self.get('TAUTO_HW_DEPS_DEV')
        if hw_deps_dev and source_type == 'DEV':
            return hw_deps_dev
        return self.get('TAUTO_HW_DEPS')


class ModuleGroup(collections.UserDict):
    pass
