#!/usr/bin/env python3
# Lint as: python2, python3
# Copyright 2019 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import print_function

import argparse
import collections
import contextlib
import copy
from enum import Enum
import logging
import os
import re
import stat
import subprocess
import tempfile
import zipfile

import bundle_utils

# Type of source storage from where the generated control files should
# retrieve the xTS bundle zip file.
#  'MOBLAB' means the bucket for moblab used by 3PL.
#  'LATEST' means the latest official xTS release.
#  'DEV' means the preview version build from development branch.
SourceType = Enum('SourceType', ['MOBLAB', 'LATEST', 'DEV'])


CONFIG = None


def inject_config(config):
    global CONFIG
    CONFIG = config


_COLLECT = 'tradefed-run-collect-tests-only-internal'
_PUBLIC_COLLECT = 'tradefed-run-collect-tests-only'
_CTSHARDWARE_COLLECT = 'tradefed-run-collect-tests-only-hardware-internal'
_PUBLIC_CTSHARDWARE_COLLECT = 'tradefed-run-collect-tests-only-hardware'


_TEST_LENGTH = {1: 'FAST', 2: 'SHORT', 3: 'MEDIUM', 4: 'LONG', 5: 'LENGTHY'}

_ALL = 'all'


def render_config(year, name, base_name, test_func_name, attributes,
                  dependencies, extra_artifacts, extra_artifacts_host,
                  job_retries, max_result_size_kb, revision, build, abi,
                  needs_push_media, needs_cts_helpers, enable_default_apps,
                  vm_force_max_resolution, vm_tablet_mode, tag, uri,
                  servo_support_needed, wifi_info_needed,
                  has_precondition_escape, max_retries, timeout, run_template,
                  retry_template, target_module, target_plan, test_length,
                  priority, extra_args, authkey, sync_count, camera_facing,
                  executable_test_count, source_type='', hw_deps=None):
    """Render config for generated controlfiles, by hard-coded some templates here.
    This is to replace jinja2 dependencies.
    """

    rendered_template = f'# Copyright {year} The ChromiumOS Authors\n' + \
    '# Use of this source code is governed by a BSD-style license that can be\n' + \
    '# found in the LICENSE file.\n\n' + \
    f'# __GENERATED_BY_GENERATE_CONTROLFILES_PY__:{source_type}\n\n' + \
    '# This file has been automatically generated. Do not edit!\n'
    if servo_support_needed:
        rendered_template += 'from autotest_lib.server import utils as server_utils\n'
    if wifi_info_needed:
        rendered_template += 'from autotest_lib.server.cros.tradefed import wifi_utils\n'
    if has_precondition_escape:
        rendered_template += 'import pipes\n'
    rendered_template += '\n'

    rendered_template += 'AUTHOR = \'n/a\'\n'
    rendered_template += f'NAME = \'{name}\'\n'
    rendered_template += 'METADATA = {\n' + \
        '    \"contacts\": [\"arc-cts-eng@google.com\"],\n' + \
        '    \"bug_component\": \"b:183644\",\n' + \
        '    \"criteria\": \"A part of Android CTS\",\n}\n'
    rendered_template += f'ATTRIBUTES = \'{attributes}\'\n'
    rendered_template += f'DEPENDENCIES = \'{dependencies}\'\n'
    if hw_deps is not None:
        hw_deps_str = ','.join(f"'{s}'" for s in hw_deps)
        rendered_template += f'HW_DEPS = [{hw_deps_str}]\n'
    rendered_template += f'JOB_RETRIES = {job_retries}\n'
    rendered_template += f'TEST_TYPE = \'server\'\n'
    rendered_template += f'TIME = \'{test_length}\'\n'
    rendered_template += f'MAX_RESULT_SIZE_KB = {max_result_size_kb}\n'
    if sync_count and sync_count > 1:
        rendered_template += f'SYNC_COUNT = {sync_count}\n'
    if priority:
        rendered_template += f'PRIORITY = {priority}\n'
    rendered_template += 'DOC = \'n/a\'\n'
    if servo_support_needed:
        rendered_template += '\n# For local debugging, if your test setup doesn\'t have servo, REMOVE these\n'
        rendered_template += '# two lines.\n'
        rendered_template += 'args_dict = server_utils.args_to_dict(args)\n'
        rendered_template += 'servo_args = hosts.CrosHost.get_servo_arguments(args_dict)\n'
    rendered_template += '\n'
    if sync_count and sync_count > 1:
        rendered_template += 'from autotest_lib.server import utils as server_utils\n'
        rendered_template += f'def {test_func_name}(ntuples):\n'
        rendered_template += 'host_list = [hosts.create_host(machine) for machine in ntuples]\n'
    else:
        rendered_template += f'def {test_func_name}(machine):\n'
        if servo_support_needed:
            rendered_template += '    # REMOVE \'servo_args=servo_args\' arg for local debugging if your test\n'
            rendered_template += '    # setup doesn\'t have servo.\n'
            rendered_template += '    try:\n'
            rendered_template += '        host_list = [hosts.create_host(machine, servo_args=servo_args)]\n'
            rendered_template += '    except:\n'
            rendered_template += '        # Just ignore any servo setup flakiness.\n'
            rendered_template += '        host_list = [hosts.create_host(machine)]\n'
        else:
            rendered_template += '    host_list = [hosts.create_host(machine)]\n'
        if wifi_info_needed:
            rendered_template += '    ssid, wifipass = wifi_utils.get_wifi_ssid_pass(machine[\'hostname\'])\n'
    rendered_template += '    job.run_test(\n'
    rendered_template += f'        \'{base_name}\',\n'
    if camera_facing and camera_facing != 'nocamera':
        rendered_template += f'        camera_facing=\'{camera_facing}\',\n'
        rendered_template += '        cmdline_args=args,\n'
    rendered_template += '        hosts=host_list,\n'
    rendered_template += '        iterations=1,\n'
    if max_retries != None:
        rendered_template += f'        max_retry={max_retries},\n'
    if enable_default_apps:
        rendered_template += '        enable_default_apps=True,\n'
    if vm_force_max_resolution:
        rendered_template += '        vm_force_max_resolution=True,\n'
    if vm_tablet_mode:
        rendered_template += '        vm_tablet_mode=True,\n'
    if needs_push_media:
        rendered_template += f'        needs_push_media={needs_push_media},\n'
    if needs_cts_helpers:
        rendered_template += f'        use_helpers={needs_cts_helpers},\n'
    rendered_template += f'        tag=\'{tag}\',\n'
    rendered_template += f'        test_name=\'{name}\',\n'
    if authkey:
        rendered_template += f'        authkey=\'{authkey}\',\n'
    rendered_template += f'        run_template={run_template},\n'
    rendered_template += f'        retry_template={retry_template},\n'
    rendered_template += '        target_module='
    if target_module:
        rendered_template += f'\'{target_module}\',\n'
    else:
        rendered_template += 'None,\n'
    rendered_template += '        target_plan='
    if target_plan:
        rendered_template += f'\'{target_plan}\',\n'
    else:
        rendered_template += 'None,\n'
    if abi:
        rendered_template += f'        bundle=\'{abi}\',\n'
    if extra_artifacts:
        rendered_template += f'        extra_artifacts={extra_artifacts},\n'
    if extra_artifacts_host:
        rendered_template += f'        extra_artifacts_host={extra_artifacts_host},\n'
    if uri:
        rendered_template += f'        uri=\'{uri}\',\n'
    for arg in extra_args:
        rendered_template += f'        {arg},\n'
    if servo_support_needed:
        rendered_template += '        hard_reboot_on_failure=True,\n'
    if camera_facing:
        rendered_template += '        retry_manual_tests=True,\n'
    if executable_test_count:
        rendered_template += f'        executable_test_count={executable_test_count},\n'
    rendered_template += f'        timeout={timeout})\n\n'

    if sync_count and sync_count > 1:
        rendered_template += 'ntuples, failures = server_utils.form_ntuples_from_machines(machines,' + \
                             '                                                            SYNC_COUNT)\n'
        rendered_template += '# Use log=False in parallel_simple to avoid an exception in setting up\n'
        rendered_template += '# the incremental parser when SYNC_COUNT > 1.\n'
        rendered_template += f'parallel_simple({test_func_name}, ntuples, log=False)\n'
    else:
        rendered_template += f'parallel_simple({test_func_name}, machines)\n'
    return rendered_template


def get_tradefed_build(line):
    """Gets the build of Android CTS from tradefed.

    @param line Tradefed identification output on startup. Example:
                Android Compatibility Test Suite 7.0 (3423912)
    @return Tradefed CTS build. Example: 2813453.
    """
    # Sample string:
    # - Android Compatibility Test Suite 7.0 (3423912)
    # - Android Compatibility Test Suite for Instant Apps 1.0 (4898911)
    # - Android Google Mobile Services (GMS) Test Suite 6.0_r1 (4756896)
    m = re.search(r' \((.*)\)', line)
    if m:
        return m.group(1)
    logging.warning('Could not identify build in line "%s".', line)
    return '<unknown>'


def get_tradefed_revision(line):
    """Gets the revision of Android CTS from tradefed.

    @param line Tradefed identification output on startup.
                Example:
                 Android Compatibility Test Suite 6.0_r6 (2813453)
                 Android Compatibility Test Suite for Instant Apps 1.0 (4898911)
    @return Tradefed CTS revision. Example: 6.0_r6.
    """
    tradefed_identifier_list = [
            r'Android Google Mobile Services \(GMS\) Test Suite (.*) \(',
            r'Android Compatibility Test Suite(?: for Instant Apps)? (.*) \(',
            r'Android Vendor Test Suite (.*) \(',
            r'Android Security Test Suite (.*) \('
    ]

    for identifier in tradefed_identifier_list:
        m = re.search(identifier, line)
        if m:
            return m.group(1)

    logging.warning('Could not identify revision in line "%s".', line)
    return None


def get_bundle_abi(filename):
    """Makes an educated guess about the ABI.

    In this case we chose to guess by filename, but we could also parse the
    xml files in the module. (Maybe this needs to be done in the future.)
    """
    if CONFIG.get('SINGLE_CONTROL_FILE'):
        return None
    if filename.endswith('arm.zip'):
        return 'arm'
    if filename.endswith('arm64.zip'):
        return 'arm64'
    if filename.endswith('x86.zip'):
        return 'x86'
    if filename.endswith('x86_64.zip'):
        return 'x86_64'

    assert(CONFIG['TRADEFED_CTS_COMMAND'] =='gts'), 'Only GTS has empty ABI'
    return ''


def get_extension(module,
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
    if not CONFIG.get('SINGLE_CONTROL_FILE') and not is_public:
        if module == _COLLECT:
            ext_parts = [revision]
        else:
            ext_parts = ['internal']
    if not CONFIG.get('SINGLE_CONTROL_FILE') and abi:
        ext_parts += [abi]
    ext_parts += [module]
    if camera_facing:
        ext_parts += ['camerabox', camera_facing]
    if hardware_suite and module not in get_collect_modules(
            is_public, hardware_suite):
        ext_parts += ['ctshardware']
    if vm_force_max_resolution:
        ext_parts += ['vmhires']
    if vm_tablet_mode:
        ext_parts += ['vmtablet']
    if not CONFIG.get('SINGLE_CONTROL_FILE') and abi and abi_bits:
        ext_parts += [str(abi_bits)]
    if shard != (0, 1):
        ext_parts += ['shard_%d_%d' % shard]
    return '.'.join(ext_parts)


def servo_support_needed(modules, is_public=True):
    """Determines if servo support is needed for a module."""

    return not is_public and any(module in CONFIG['NEEDS_POWER_CYCLE']
                                 for module in modules)


def wifi_info_needed(modules, is_public):
    """Determines if Wifi AP info needs to be retrieved."""
    return not is_public and any(module in CONFIG.get('WIFI_MODULES', [])
                                 for module in modules)


def get_controlfile_name(module,
                         abi,
                         revision,
                         is_public=False,
                         camera_facing=None,
                         abi_bits=None,
                         shard=(0, 1),
                         hardware_suite=False,
                         vm_force_max_resolution=False,
                         vm_tablet_mode=False):
    """Defines the control file name.

    @param module: CTS module which will be tested in the control file. If 'all'
                   is specified, the control file will runs all the tests.
    @param public: boolean variable to specify whether or not the bundle is from
                   public source or not.
    @param camera_facing: string or None indicate whether it's camerabox tests
                          for specific camera facing or not.
    @param abi_bits: 32 or 64 or None indicate the bitwidth for the specific
                     abi to run.
    @param shard: tuple of integers representing the shard index.
    @param vm_force_max_resolution: boolean variable indicating whether max
                                    resolution is enforced on VM display.
    @param vm_tablet_mode: boolean variable indicating whether enable tablet
                           mode for VM testing.
    @return string: control file for specific tests. If public=True or
                    module=all, then the name will be "control.<abi>.<module>",
                    otherwise, the name will be
                    "control.<revision>.<abi>.<module>".
    """
    return 'control.%s' % get_extension(
            module, abi, revision, is_public, camera_facing, hardware_suite,
            abi_bits, shard, vm_force_max_resolution, vm_tablet_mode)


def get_sync_count(_modules, _abi, _is_public):
    return 1

def get_cts_hardware_modules(is_public):
    """Determines set of hardware modules based on is_public flag.

    Args:
        is_public: flag that is passed on command line when generating control files.
    Returns:
      set corresponding set of modules.
    """
    if is_public:
        return set(CONFIG.get('PUBLIC_HARDWARE_MODULES', []))
    else:
        return set(CONFIG.get('HARDWARE_MODULES', []))


def get_suites(modules,
               abi,
               is_public,
               camera_facing=None,
               hardware_suite=False,
               vm_force_max_resolution=False,
               vm_table_mode=False):
    """Defines the suites associated with a module.

    @param module: CTS module which will be tested in the control file. If 'all'
                   is specified, the control file will runs all the tests.
    # TODO(ihf): Make this work with the "all" and "collect" generation,
    # which currently bypass this function.
    """
    cts_hardware_modules = get_cts_hardware_modules(is_public)

    if is_public:
        suites = set([CONFIG['MOBLAB_SUITE_NAME']])
        if hardware_suite:
            suites = set([CONFIG['MOBLAB_HARDWARE_SUITE_NAME']])
        return sorted(list(suites))

    suites = set(CONFIG['INTERNAL_SUITE_NAMES'])

    vm_modules = []
    nonvm_modules = []
    has_unstable_vm_modules = False
    for module in modules:
        if module in get_collect_modules(is_public, hardware_suite):
            # We collect all tests both in arc-gts and arc-gts-qual as both have
            # a chance to be complete (and used for submission).
            suites |= set(CONFIG['QUAL_SUITE_NAMES'])
        if module in CONFIG['EXTRA_ATTRIBUTES']:
            # Special cases come with their own suite definitions.
            suites |= set(CONFIG['EXTRA_ATTRIBUTES'][module])
        # We don't want to include max resolution tests or tablet mode tests in non-VM suites.
        if vm_force_max_resolution or vm_table_mode:
            suites.clear()
        if is_vm_modules(
                module) and 'VM_SUITE_NAME' in CONFIG and not camera_facing:
            # This logic put the whole control group (if combined) into
            # VM_SUITE_NAME if any module is listed in get_vm_modules(). We
            # should not do it once in production.
            # If VM_RUN_SINGLE_ABI is specified, append VM suite only if it
            # matches the current abi. The remaining logic is kept in order to
            # correctly create the stable VM suite.
            if CONFIG.get('VM_RUN_SINGLE_ABI', abi) == abi:
                suites.add(CONFIG['VM_SUITE_NAME'])
            vm_modules.append(module)
            if is_unstable_vm_modules(module):
                has_unstable_vm_modules = True
        else:
            nonvm_modules.append(module)
        # A few fast modules can run in suite:bvt-arc.
        if module in CONFIG.get('PERBUILD_TESTS', []) and (
                abi == 'arm' or abi == ''):
            suites.add('suite:bvt-arc')

    if hardware_suite:
        suites = set([CONFIG['HARDWARE_SUITE_NAME']])

    if camera_facing != None:
        suites.add('suite:arc-cts-camera')

    if vm_modules and nonvm_modules:
        logging.warning(
                '%s is also added to vm suites because of %s, please check your config',
                nonvm_modules, vm_modules)

    # For group with stalbe VM test only, remove it from HW suite, and add to
    # stable VM suite.
    if suites.intersection(set(CONFIG.get('VM_SKIP_SUITES', []))):
        if vm_modules and not nonvm_modules and not has_unstable_vm_modules:
            suites = suites - set(CONFIG.get('VM_SKIP_SUITES', []))
            if 'STABLE_VM_SUITE_NAME' in CONFIG:
                suites.add(CONFIG['STABLE_VM_SUITE_NAME'])

    return sorted(list(suites))


def get_dependencies(modules, abi, is_public, camera_facing):
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
    if abi in CONFIG['LAB_DEPENDENCY']:
        dependencies += CONFIG['LAB_DEPENDENCY'][abi]

    if camera_facing is not None:
        dependencies.append('camerabox_facing:'+camera_facing)

    for module in modules:
        if is_public and module in CONFIG['PUBLIC_DEPENDENCIES']:
            dependencies.extend(CONFIG['PUBLIC_DEPENDENCIES'][module])

    return ', '.join(dependencies)


def get_job_retries(modules, is_public, suites):
    """Define the number of job retries associated with a module.

    @param module: CTS module which will be tested in the control file. If a
                   special module is specified, the control file will runs all
                   the tests without retry.
    @param is_public: true if the control file is for moblab (public) use.
    @param suites: the list of suites that the control file belongs to.
    """
    # TODO(haddowk): remove this when cts p has stabalized.
    if is_public:
        return CONFIG['CTS_JOB_RETRIES_IN_PUBLIC']
    retries = 1  # 0 is NO job retries, 1 is one retry etc.
    for module in modules:
        # We don't want job retries for module collection or special cases.
        if (module in get_collect_modules(is_public) or module == _ALL or
            ('CtsDeqpTestCases' in CONFIG['EXTRA_MODULES'] and
             module in CONFIG['EXTRA_MODULES']['CtsDeqpTestCases']
             )):
            retries = 0
    return retries


def get_max_retries(modules, abi, suites, is_public, shard):
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
        if _ALL in CONFIG['PUBLIC_MODULE_RETRY_COUNT']:
            retry = CONFIG['PUBLIC_MODULE_RETRY_COUNT'][_ALL]

        # In moblab at partners we may need many more retries than in lab.
        for module in modules:
            if module in CONFIG['PUBLIC_MODULE_RETRY_COUNT']:
                retry = max(retry, CONFIG['PUBLIC_MODULE_RETRY_COUNT'][module])
    else:
        # See if we have any special values for the module, chose the largest.
        for module in modules:
            if module in CONFIG['CTS_MAX_RETRIES']:
                retry = max(retry, CONFIG['CTS_MAX_RETRIES'][module])

    # Ugly overrides.
    # In bvt we don't want to hold the CQ/PFQ too long.
    if retry == -1 and 'suite:bvt-arc' in suites:
        retry = 3
    # Not strict as CQ for bvt-perbuild. Let per-module config take priority.
    if retry == -1 and 'suite:bvt-perbuild' in suites:
        retry = 3
    # During qualification we want at least 9 retries, possibly more.
    # TODO(kinaba&yoshiki): do not abuse suite names
    if CONFIG.get('QUAL_SUITE_NAMES') and \
            set(CONFIG['QUAL_SUITE_NAMES']) & set(suites):
        retry = max(retry, CONFIG['CTS_QUAL_RETRIES'])
    # Collection should never have a retry. This needs to be last.
    if modules.intersection(get_collect_modules(is_public)):
        retry = 0

    if retry >= 0:
        return retry
    # Default case omits the retries in the control file, so tradefed_test.py
    # can chose its own value.
    return None


def get_max_result_size_kb(modules, is_public):
    """Returns the maximum expected result size in kB for autotest.

    @param modules: List of CTS modules to be tested by the control file.
    """
    for module in modules:
        if (module in get_collect_modules(is_public) or
            module == 'CtsDeqpTestCases'):
            # CTS tests and dump logs for android-cts.
            return CONFIG['LARGE_MAX_RESULT_SIZE']
    # Individual module normal produces less results than all modules.
    return CONFIG['NORMAL_MAX_RESULT_SIZE']


def has_precondition_escape(modules, is_public):
    """Determines if escape by pipes module is used in preconditions.

    @param modules: List of CTS modules to be tested by the control file.
    """
    commands = []
    for module in modules:
        if is_public:
            commands.extend(CONFIG['PUBLIC_PRECONDITION'].get(module, []))
        else:
            commands.extend(CONFIG['PRECONDITION'].get(module, []))
            commands.extend(CONFIG['LOGIN_PRECONDITION'].get(module, []))
    return any('pipes.' in cmd for cmd in commands)


def get_extra_args(modules, is_public):
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
            preconditions.extend(CONFIG['PUBLIC_PRECONDITION'].get(module, []))
        else:
            preconditions.extend(CONFIG['PRECONDITION'].get(module, []))
            login_preconditions.extend(
                CONFIG['LOGIN_PRECONDITION'].get(module, []))
            prerequisites.extend(CONFIG['PREREQUISITES'].get(module,[]))

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
        extra_args.add('precondition_commands=[%s]' % ', '.join(
            deduped(preconditions)))
    if login_preconditions:
        extra_args.add('login_precondition_commands=[%s]' % ', '.join(
            deduped(login_preconditions)))
    if prerequisites:
        extra_args.add("prerequisites=['%s']" % "', '".join(
            deduped(prerequisites)))
    return sorted(list(extra_args))


def get_test_length(modules):
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
        if module in CONFIG['OVERRIDE_TEST_LENGTH']:
            length = max(length, CONFIG['OVERRIDE_TEST_LENGTH'][module])
    return _TEST_LENGTH[length]


def get_test_priority(modules, is_public):
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
    overide_test_priority_dict = CONFIG.get('PUBLIC_OVERRIDE_TEST_PRIORITY', {})
    for module in modules:
        if module in overide_test_priority_dict:
            priority = max(priority, overide_test_priority_dict[module])
        elif (module in CONFIG['OVERRIDE_TEST_LENGTH'] or
                module in CONFIG['PUBLIC_DEPENDENCIES'] or
                module in CONFIG['PUBLIC_PRECONDITION'] or
                module.split('.')[0] in CONFIG['OVERRIDE_TEST_LENGTH']):
            priority = max(priority, 50)
    return priority


def get_authkey(is_public):
    if is_public or not CONFIG['AUTHKEY']:
        return None
    return CONFIG['AUTHKEY']


def _format_collect_cmd(is_public,
                        abi_to_run,
                        retry,
                        is_hardware=False,
                        is_camera=False):
    """Returns a list specifying tokens for tradefed to list all tests."""
    if retry:
        return None
    cmd = ['run', 'commandAndExit', 'collect-tests-only']
    if CONFIG['TRADEFED_DISABLE_REBOOT_ON_COLLECTION']:
        cmd += ['--disable-reboot']
    if is_camera:
        cmd += ['--module', 'CtsCameraTestCases']
    elif is_hardware:
        cmd.append('--subplan')
        cmd.append('cts-hardware')
    if not is_camera:
        for m in CONFIG.get('COLLECT_EXCLUDE_MODULES', []):
            cmd.extend(['--exclude-filter', m])
    for m in CONFIG['MEDIA_MODULES']:
        cmd.append('--module-arg')
        cmd.append('%s:skip-media-download:true' % m)
    if (not is_public and
            not CONFIG.get('NEEDS_DYNAMIC_CONFIG_ON_COLLECTION', True)):
        cmd.append('--dynamic-config-url=')
    if abi_to_run:
        cmd += ['--abi', abi_to_run]
    return cmd


def _get_special_command_line(modules, _is_public):
    """This function allows us to split a module like Deqp into segments."""
    cmd = []
    for module in sorted(modules):
        cmd += CONFIG['EXTRA_COMMANDLINE'].get(module, [])
    return cmd


def _format_modules_cmd(is_public,
                        abi_to_run,
                        shard=(0, 1),
                        modules=None,
                        retry=False,
                        whole_module_set=None,
                        is_hardware=False):
    """Returns list of command tokens for tradefed."""
    if retry:
        assert(CONFIG['TRADEFED_RETRY_COMMAND'] == 'cts' or
               CONFIG['TRADEFED_RETRY_COMMAND'] == 'retry')

        cmd = ['run', 'commandAndExit', CONFIG['TRADEFED_RETRY_COMMAND'],
               '--retry', '{session_id}']
    else:
        # For runs create a logcat file for each individual failure.
        cmd = ['run', 'commandAndExit', CONFIG['TRADEFED_CTS_COMMAND']]

        special_cmd = _get_special_command_line(modules, is_public)
        if special_cmd:
            if is_hardware:
                # For hardware suite we want to exclude [instant] modules.
                filtered = []
                i = 0
                while i < len(special_cmd):
                    if (special_cmd[i] == '--include-filter'
                                and '[instant]' in special_cmd[i + 1]):
                        i += 2
                    elif (special_cmd[i] == '--module'
                          and i + 3 < len(special_cmd)
                          and special_cmd[i + 2] == '--test'):
                        # [--module, x, --test, y] ==> [--include-filter, "x y"]
                        # because --module implicitly include [instant] modules
                        filtered.append('--include-filter')
                        filtered.append(
                                '%s %s' %
                                (special_cmd[i + 1], special_cmd[i + 3]))
                        i += 4
                    elif special_cmd[i] == '--module':
                        # [--module, x] ==> [--include-filter, x]
                        filtered.append('--include-filter')
                        filtered.append(special_cmd[i + 1])
                        i += 2
                    else:
                        filtered.append(special_cmd[i])
                        i += 1
                special_cmd = filtered
            cmd.extend(special_cmd)
        elif _ALL in modules:
            pass
        elif len(modules) == 1 and not is_hardware:
            cmd += ['--module', list(modules)[0]]
        else:
            if whole_module_set is None:
                assert (CONFIG['TRADEFED_CTS_COMMAND'] != 'cts-instant'), \
                       'cts-instant cannot include multiple modules'
                # We run each module with its own --include-filter option.
                # https://source.android.com/compatibility/cts/run
                for module in sorted(modules):
                    # b/196756614 32-bit jobs should skip [parameter] modules.
                    if is_parameterized_module(module) and abi_to_run in [
                            'x86', 'armeabi-v7a'
                    ]:
                        continue
                    cmd += ['--include-filter', module]
            else:
                # CTS-Instant does not support --include-filter due to
                # its implementation detail. Instead, exclude the complement.
                for module in sorted(whole_module_set - set(modules)):
                    cmd += ['--exclude-filter', module]

        if shard != (0, 1):
            cmd += [
                    '--shard-index',
                    str(shard[0]), '--shard-count',
                    str(shard[1])
            ]

        # For runs create a logcat file for each individual failure.
        # Not needed on moblab, nobody is going to look at them.
        if (not modules.intersection(CONFIG['DISABLE_LOGCAT_ON_FAILURE']) and
            not is_public and
            CONFIG['TRADEFED_CTS_COMMAND'] != 'gts'):
            cmd.append('--logcat-on-failure')

        if CONFIG['TRADEFED_IGNORE_BUSINESS_LOGIC_FAILURE']:
            cmd.append('--ignore-business-logic-failure')

    if CONFIG['TRADEFED_DISABLE_REBOOT']:
        cmd.append('--disable-reboot')
    if (CONFIG['TRADEFED_MAY_SKIP_DEVICE_INFO']
                and not modules.intersection(CONFIG['NEEDS_DEVICE_INFO'])):
        cmd.append('--skip-device-info')
    if abi_to_run:
        cmd += ['--abi', abi_to_run]
    # If NEEDS_DYNAMIC_CONFIG is set, disable the feature except on the modules
    # that explicitly set as needed.
    if (not is_public and CONFIG.get('NEEDS_DYNAMIC_CONFIG') and
            not modules.intersection(CONFIG['NEEDS_DYNAMIC_CONFIG'])):
        cmd.append('--dynamic-config-url=')

    return cmd


def get_run_template(modules,
                     is_public,
                     retry=False,
                     abi_to_run=None,
                     shard=(0, 1),
                     whole_module_set=None,
                     is_hardware=False):
    """Command to run the modules specified by a control file."""
    # TODO(kinaba): `_ALL` phony module is no longer used anywhere.
    # Clean it up together with all the other occurrences.
    is_all = _ALL in modules
    is_collect = (len(modules) == 1
                  and list(modules)[0] in get_collect_modules(
                          is_public, is_hardware))
    if is_all:
        return None
    elif is_collect:
        return _format_collect_cmd(is_public,
                                   abi_to_run,
                                   retry=retry,
                                   is_hardware=is_hardware,
                                   is_camera='camerabox' in list(modules)[0])
    else:
        return _format_modules_cmd(is_public,
                                   abi_to_run,
                                   shard,
                                   modules,
                                   retry=retry,
                                   whole_module_set=whole_module_set,
                                   is_hardware=is_hardware)

def get_retry_template(modules, is_public):
    """Command to retry the failed modules as specified by a control file."""
    return get_run_template(modules, is_public, retry=True)


def get_extra_modules_dict(source_type, abi):
    if source_type != SourceType.MOBLAB:
        return CONFIG['EXTRA_MODULES']

    extra_modules = copy.deepcopy(CONFIG['PUBLIC_EXTRA_MODULES'].get(abi, {}))
    if abi in CONFIG['EXTRA_SUBMODULE_OVERRIDE']:
        for _, config in extra_modules.items():
            for old, news in CONFIG['EXTRA_SUBMODULE_OVERRIDE'][abi].items():
                if old in config.keys():
                    suite = config[old]
                    config.pop(old)
                    for module in news:
                        config[module] = suite

    return extra_modules

def get_extra_hardware_modules_dict(is_public, abi):
    return CONFIG.get('HARDWAREONLY_EXTRA_MODULES', {})


def is_in_rule(module, rule):
    """Checks if module in given rule of VM rule syntax"""
    for pattern in rule:
        assert pattern[0] in '+-'
        if re.match(pattern[1:], module):
            return True if pattern[0] == '+' else False

    return False

# Camera modules are static
def get_camera_modules():
    """Gets a list of modules for arc-cts-camera-opendut."""
    return CONFIG.get('CAMERA_MODULES', [])


def is_vm_modules(module):
    """Checks if module eligible for VM."""
    return is_in_rule(module, CONFIG.get('VM_MODULES_RULES', []))


def is_unstable_vm_modules(module):
    """Checks if module is still unstable for VM."""
    return is_in_rule(module, CONFIG.get('VM_UNSTABLE_MODULES_RULES', []))


def get_extra_artifacts(modules):
    artifacts = []
    for module in modules:
        if module in CONFIG['EXTRA_ARTIFACTS']:
            artifacts += CONFIG['EXTRA_ARTIFACTS'][module]
    return artifacts


def get_extra_artifacts_host(modules):
    if not 'EXTRA_ARTIFACTS_HOST' in CONFIG:
        return

    artifacts = []
    for module in modules:
        if module in CONFIG['EXTRA_ARTIFACTS_HOST']:
            artifacts += CONFIG['EXTRA_ARTIFACTS_HOST'][module]
    return artifacts


def calculate_timeout(modules, suites):
    """Calculation for timeout of tradefed run.

    Timeout is at least one hour, except if part of BVT_ARC.
    Notice these do get adjusted dynamically by number of ABIs on the DUT.
    """
    if 'suite:bvt-arc' in suites:
        return int(3600 * CONFIG['BVT_TIMEOUT'])
    if CONFIG.get('QUAL_SUITE_NAMES') and \
            CONFIG.get('QUAL_TIMEOUT') and \
            ((set(CONFIG['QUAL_SUITE_NAMES']) & set(suites)) and \
            not (_COLLECT in modules or _PUBLIC_COLLECT in modules)):
        return int(3600 * CONFIG['QUAL_TIMEOUT'])

    timeout = 0
    # First module gets 1h (standard), all other half hour extra (heuristic).
    default_timeout = int(3600 * CONFIG['CTS_TIMEOUT_DEFAULT'])
    delta = default_timeout
    for module in modules:
        if module in CONFIG['CTS_TIMEOUT']:
            # Modules that run very long are encoded here.
            timeout += int(3600 * CONFIG['CTS_TIMEOUT'][module])
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


def needs_push_media(modules):
    """Oracle to determine if to push several GB of media files to DUT."""
    if modules.intersection(set(CONFIG['NEEDS_PUSH_MEDIA'])):
        return True
    return False


def needs_cts_helpers(modules):
    """Oracle to determine if CTS helpers should be downloaded from DUT."""
    if 'NEEDS_CTS_HELPERS' not in CONFIG:
        return False
    if modules.intersection(set(CONFIG['NEEDS_CTS_HELPERS'])):
        return True
    return False


def enable_default_apps(modules):
    """Oracle to determine if to enable default apps (eg. Files.app)."""
    if modules.intersection(set(CONFIG['ENABLE_DEFAULT_APPS'])):
        return True
    return False


def is_parameterized_module(module):
    """Determines if the given module is a parameterized module."""
    return '[' in module


def get_controlfile_content(combined,
                            modules,
                            abi,
                            revision,
                            build,
                            uri,
                            suites=None,
                            source_type=None,
                            abi_bits=None,
                            shard=(0, 1),
                            camera_facing=None,
                            hardware_suite=False,
                            whole_module_set=None,
                            vm_force_max_resolution=False,
                            vm_tablet_mode=False,
                            shard_ref_test=None):
    """Returns the text inside of a control file.

    @param combined: name to use for this combination of modules.
    @param modules: set of CTS modules which will be tested in the control
                   file. If 'all' is specified, the control file will run
                   all the tests.
    """
    is_public = (source_type == SourceType.MOBLAB)
    # We tag results with full revision now to get result directories containing
    # the revision. This fits stainless/ better.
    tag = '%s' % get_extension(combined, abi, revision, is_public,
                               camera_facing, hardware_suite, abi_bits, shard,
                               vm_force_max_resolution, vm_tablet_mode)
    # For test_that the NAME should be the same as for the control file name.
    # We could try some trickery here to get shorter extensions for a default
    # suite/ARM. But with the monthly uprevs this will quickly get confusing.
    name = '%s.%s' % (CONFIG['TEST_NAME'], tag)
    if not suites:
        suites = get_suites(modules, abi, is_public, camera_facing,
                            hardware_suite, vm_force_max_resolution,
                            vm_tablet_mode)
    suites = suites.copy()

    # while creating the control files, check if this is meant for qualification suite. i.e. arc-cts-qual
    # if it is meant for qualification suite, also add new suite ar-cts-camera-opendut which is meant for
    # qualification purposes when cameraboxes fail.
    # if suites has arc-cts-qual and module is cameramodule then add arc-cts-camera-opendut
    is_qual = bool(set(CONFIG.get('QUAL_SUITE_NAMES', [])) & set(suites))
    is_internal = bool(
            set(CONFIG.get('INTERNAL_SUITE_NAMES', [])) & set(suites))
    is_vm_stable = 'STABLE_VM_SUITE_NAME' in CONFIG and CONFIG[
            'STABLE_VM_SUITE_NAME'] in suites

    if is_qual and (set(get_camera_modules()) & set(modules)):
        camera_dut_suite = CONFIG.get('CAMERA_DUT_SUITE_NAME')
        if camera_dut_suite:
            suites.append(camera_dut_suite)
        for qual_suite in CONFIG.get('QUAL_SUITE_NAMES', []):
            suites.remove(qual_suite)
        is_qual = False
    if is_internal and (set(get_camera_modules()) & set(modules)):
        for regression_suite in CONFIG.get('INTERNAL_SUITE_NAMES', []):
            suites.remove(regression_suite)
        is_internal = False

    # TODO(b/287160788): Decide what to do with collect-tests-only and waivers.
    # Now both goes to the long suite.
    if 'SPLIT_SUITES' in CONFIG and (is_internal or is_qual or is_vm_stable):
        test = shard_ref_test if is_qual else combined
        suites.append(
                get_suite_split_shard_name(CONFIG['SPLIT_SUITES'], is_qual,
                                           test, abi, abi_bits))

    attributes = ', '.join(sorted(suites))
    uri = {
            SourceType.MOBLAB: None,
            SourceType.LATEST: 'LATEST',
            SourceType.DEV: 'DEV'
    }.get(source_type)
    target_module = None
    if (combined not in get_collect_modules(is_public) and combined != _ALL):
        target_module = combined
    for target, config in get_extra_modules_dict(source_type, abi).items():
        if combined in config.keys():
            target_module = target
    abi_to_run = {
            ("arm", 32): 'armeabi-v7a',
            ("arm", 64): 'arm64-v8a',
            ("x86", 32): 'x86',
            ("x86", 64): 'x86_64'
    }.get((abi, abi_bits), None)
    subplan = None
    if _CTSHARDWARE_COLLECT in modules or _PUBLIC_CTSHARDWARE_COLLECT in modules:
        subplan = 'cts-hardware'
    executable_test_count = None
    if _COLLECT in modules or _PUBLIC_COLLECT in modules:
        executable_test_count = CONFIG.get('COLLECT_TESTS_COUNT')
    return render_config(
            year=CONFIG['COPYRIGHT_YEAR'],
            name=name,
            base_name=CONFIG['TEST_NAME'],
            test_func_name=CONFIG['CONTROLFILE_TEST_FUNCTION_NAME'],
            attributes=attributes,
            dependencies=get_dependencies(modules, abi, is_public,
                                          camera_facing),
            extra_artifacts=get_extra_artifacts(modules),
            extra_artifacts_host=get_extra_artifacts_host(modules),
            job_retries=get_job_retries(modules, is_public, suites),
            max_result_size_kb=get_max_result_size_kb(modules, is_public),
            revision=revision,
            build=build,
            abi=abi,
            needs_push_media=needs_push_media(modules),
            needs_cts_helpers=needs_cts_helpers(modules),
            enable_default_apps=enable_default_apps(modules),
            vm_force_max_resolution=vm_force_max_resolution,
            vm_tablet_mode=vm_tablet_mode,
            tag=tag,
            uri=uri,
            servo_support_needed=servo_support_needed(modules, is_public),
            wifi_info_needed=wifi_info_needed(modules, is_public),
            has_precondition_escape=has_precondition_escape(
                    modules, is_public),
            max_retries=get_max_retries(modules, abi, suites, is_public,
                                        shard),
            timeout=calculate_timeout(modules, suites),
            run_template=get_run_template(modules,
                                          is_public,
                                          abi_to_run=CONFIG.get(
                                                  'REPRESENTATIVE_ABI',
                                                  {}).get(abi, abi_to_run),
                                          shard=shard,
                                          whole_module_set=whole_module_set,
                                          is_hardware=hardware_suite),
            retry_template=get_retry_template(modules, is_public),
            target_module=target_module,
            target_plan=subplan,
            test_length=get_test_length(modules),
            priority=get_test_priority(modules, is_public),
            extra_args=get_extra_args(modules, is_public),
            authkey=get_authkey(is_public),
            sync_count=get_sync_count(modules, abi, is_public),
            camera_facing=camera_facing,
            executable_test_count=executable_test_count,
            hw_deps=CONFIG.get('TAUTO_HW_DEPS'),
    )


def fixup_tradefed_executable_bits(basepath, executables):
    """ Do chmod u+x for files to be executed, because Python's zipfile
    module does not set the executable bit.
    """
    for subpath in executables:
        path = os.path.join(basepath, subpath)
        if os.path.exists(path):
            os.chmod(path, os.stat(path).st_mode | stat.S_IEXEC)


def get_tradefed_data(path, tradefed_path=None, extra_executables=None):
    """Queries tradefed to provide us with a list of modules.

    Notice that the parsing gets broken at times with major new CTS drops.
    """
    tradefed_path = tradefed_path or CONFIG['TRADEFED_EXECUTABLE_PATH']
    executables = extra_executables.copy(
    ) if extra_executables is not None else []
    executables.append(tradefed_path)
    fixup_tradefed_executable_bits(path, executables)

    tradefed = os.path.join(path, tradefed_path)
    cmd_list = [tradefed, 'list', 'modules']
    logging.info('Calling tradefed for list of modules.')
    with open(os.devnull, 'w') as devnull:
        # tradefed terminates itself if stdin is not a tty.
        tradefed_output = subprocess.check_output(cmd_list,
                                                  stdin=devnull).decode()

    _ABI_PREFIXES = ('arm', 'x86')
    _MODULE_PREFIXES = ('Cts', 'cts-', 'signed-Cts', 'vm-tests-tf', 'Sts')

    modules = set()
    build = '<unknown>'
    revision = None
    for line in tradefed_output.splitlines():
        # Android Compatibility Test Suite 7.0 (3423912)
        if (line.startswith('Android Compatibility Test Suite ')
                    or line.startswith('Android Google ')
                    or line.startswith('Android Vendor Test Suite')
                    or line.startswith('Android Security Test Suite')):
            logging.info('Unpacking: %s.', line)
            build = get_tradefed_build(line)
            revision = get_tradefed_revision(line)
        elif line.startswith(_ABI_PREFIXES):
            # Newer CTS shows ABI-module pairs like "arm64-v8a CtsNetTestCases"
            line = line.split()[1]
            if line not in CONFIG.get('EXCLUDE_MODULES', []):
                modules.add(line)
        elif line.startswith(_MODULE_PREFIXES):
            # Old CTS plainly lists up the module name
            modules.add(line)
        elif line.isspace() or line.startswith('Use "help"'):
            pass
        else:
            logging.warning('Ignoring "%s"', line)

    if not modules:
        raise Exception("no modules found.")
    return list(modules), build, revision


def download(uri, destination):
    """Download |uri| to local |destination|.

       |destination| must be a file path (not a directory path)."""
    if uri.startswith('http://') or uri.startswith('https://'):
        subprocess.check_call(['wget', uri, '-O', destination])
    elif uri.startswith('gs://'):
        subprocess.check_call(['gsutil', 'cp', uri, destination])
    else:
        raise Exception


@contextlib.contextmanager
def pushd(d):
    """Defines pushd."""
    current = os.getcwd()
    os.chdir(d)
    try:
        yield
    finally:
        os.chdir(current)


def unzip(filename, destination, password=''):
    """Unzips a zip file to the destination directory.

    Args:
        filename is the file to be unzipped.
        destination is where the zip file would be extracted.
        password is an optional value for unzipping. If the zip file is not
            encrypted, the value has no effect.
    """
    with pushd(destination):
        # We are trusting Android to have a valid zip file for us.
        with zipfile.ZipFile(filename) as zf:
            zf.extractall(pwd=password.encode())


def get_collect_modules(is_public, is_hardware=False):
    if is_public:
        if is_hardware:
            return set([_PUBLIC_CTSHARDWARE_COLLECT])
        return set([_PUBLIC_COLLECT])
    else:
        suffices = ['']
        if CONFIG.get('CONTROLFILE_WRITE_CAMERA', False):
            suffices.extend([".camerabox.front", ".camerabox.back"])
        if is_hardware:
            return set(_CTSHARDWARE_COLLECT + suffix for suffix in suffices)
        return set(_COLLECT + suffix for suffix in suffices)


def get_word_pattern(m, l=1):
    """Return the first few words of the CamelCase module name.

    Break after l+1 CamelCase word.
    Example: CtsDebugTestCases -> CtsDebug.
    """
    s = re.findall('^[a-z-_]+|[A-Z]*[^A-Z0-9]*', m)[0:l + 1]
    # Ignore Test or TestCases at the end as they don't add anything.
    if len(s) > l:
        if s[l].startswith('Test') or s[l].startswith('['):
            return ''.join(s[0:l])
        if s[l - 1] == 'Test' and s[l].startswith('Cases'):
            return ''.join(s[0:l - 1])
    return ''.join(s[0:l + 1])


def combine_modules_by_common_word(modules):
    """Returns a dictionary of (combined name, set of module) pairs.

    This gives a mild compaction of control files (from about 320 to 135).
    Example:
    'CtsVoice' -> ['CtsVoiceInteractionTestCases', 'CtsVoiceSettingsTestCases']
    """
    d = dict()
    # On first pass group modules with common first word together.
    for module in modules:
        pattern = get_word_pattern(module)
        v = d.get(pattern, [])
        v.append(module)
        v.sort()
        d[pattern] = v
    # Second pass extend names to maximum common prefix. This keeps control file
    # names identical if they contain only one module and less ambiguous if they
    # contain multiple modules.
    combined = dict()
    for key in sorted(d):
        # Instead if a one syllable prefix use longest common prefix of modules.
        prefix = os.path.commonprefix(d[key])
        # Beautification: strip Tests/TestCases from end of prefix, but only if
        # there is more than one module in the control file. This avoids
        # slightly strange combination of having CtsDpiTestCases1/2 inside of
        # CtsDpiTestCases (now just CtsDpi to make it clearer there are several
        # modules in this control file).
        if len(d[key]) > 1:
            prefix = re.sub('TestCases$', '', prefix)
            prefix = re.sub('Tests$', '', prefix)
        # Beautification: CtsMedia files run very long and are unstable. Give
        # each module its own control file, even though this heuristic would
        # lump them together.
        if prefix.startswith('CtsMedia') or prefix.startswith('CtsCamera'):
            # Separate each CtsMedia* modules, but group extra modules with
            # optional parametrization (ex: secondary_user, instant) together.
            prev = ' '
            for media in sorted(d[key]):
                if media.startswith(prev):
                    combined[prev].add(media)
                else:
                    prev = media
                    combined[media] = set([media])

        else:
            combined[prefix] = set(d[key])
    print('Reduced number of control files from %d to %d.' % (len(modules),
                                                              len(combined)))
    return combined


def combine_modules_by_bookmark(modules):
    """Return a manually curated list of name, module pairs.

    Ideally we split "all" into a dictionary of maybe 10-20 equal runtime parts.
    (Say 2-5 hours each.) But it is ok to run problematic modules alone.
    """
    d = dict()
    # Figure out sets of modules between bookmarks. Not optimum time complexity.
    for bookmark in CONFIG['QUAL_BOOKMARKS']:
        if modules:
            for module in sorted(modules):
                if module < bookmark:
                    v = d.get(bookmark, set())
                    v.add(module)
                    d[bookmark] = v
            # Remove processed modules.
            if bookmark in d:
                modules = modules - d[bookmark]
    # Clean up names.
    combined = dict()
    for key in sorted(d):
        v = sorted(d[key])
        # New name is first element '_-_' last element.
        # Notice there is a bug in $ADB_VENDOR_KEYS path name preventing
        # arbitrary characters.
        prefix = re.sub(r'\[[^]]*\]', '', v[0] + '_-_' + v[-1])
        combined[prefix] = set(v)
    return combined


def combine_modules_by_suite_split_shards(config, modules):
    """Combine modules based on suite splitting heuristics.

    Returns:
        A list of (key, shard_ref_test, modules):
          - key: the combined test name
          - shard_ref_test: the test name to use when querying
                get_suite_split_shard_name().
          - modules: set of combined modules.
    """
    # Runtime hints are based on DEV tests. Apply DEV grouping first.
    combined = combine_modules_by_common_word(modules)

    # Further combine DEV tests to make it one test per shard. For each shard,
    # pick one DEV test name to use when calling get_suite_split_shard_name
    # afterwards. Handle long tests separately.
    shard_modules = collections.defaultdict(set)
    shard_ref_test = {}
    long_tests = []
    for key, modules in combined.items():
        shard, is_vm_stable = get_suite_split_shard_number(config, key)
        if shard == -1:
            long_tests.append((key, modules))
            continue
        shard_modules[(shard, is_vm_stable)].update(modules)
        if (shard, is_vm_stable) not in shard_ref_test:
            shard_ref_test[(shard, is_vm_stable)] = key

    combined = []
    # For each shard, apply a naming scheme similar to
    # combine_modules_by_bookmark.
    for (shard, is_vm_stable), modules in shard_modules.items():
        key = re.sub(r'\[[^]]*\]', '', min(modules) + '_-_' + max(modules))
        if is_vm_stable:
            key = 'vm_stable.' + key
        combined.append((key, shard_ref_test[(shard, is_vm_stable)], modules))
    # Each long test has its own control file.
    for key, modules in long_tests:
        combined.append((key, key, modules))
    return combined


def write_controlfile(name,
                      modules,
                      abi,
                      revision,
                      build,
                      uri,
                      suites,
                      source_type,
                      whole_module_set=None,
                      hardware_suite=False,
                      shard_ref_test=None):
    """Write control files per each ABI or combined."""
    is_public = (source_type == SourceType.MOBLAB)
    abi_bits_list = []
    config_key = 'PUBLIC_SPLIT_BY_BITS_MODULES' if is_public else 'SPLIT_BY_BITS_MODULES'
    if modules & set(CONFIG.get(config_key, [])):
        # If |abi| is predefined (like CTS), splits the modules by
        # 32/64-bits. If not (like GTS) generate both arm and x86 jobs.
        for abi_arch in [abi] if abi else ['arm', 'x86']:
            for abi_bits in [32, 64]:
                abi_bits_list.append((abi_arch, abi_bits))
    else:
        abi_bits_list.append((abi, None))

    shard_count_map = CONFIG.get(
            'PUBLIC_SHARD_COUNT' if is_public else 'SHARD_COUNT', dict())
    shard_count = max(shard_count_map.get(m, 1) for m in modules)
    vm_force_max_resolution_list = [False]
    if (source_type == SourceType.DEV and modules
                & set(CONFIG.get('SPLIT_BY_VM_FORCE_MAX_RESOLUTION', []))):
        vm_force_max_resolution_list.append(True)
    vm_tablet_mode_list = [False]
    if (source_type == SourceType.DEV and modules
                & set(CONFIG.get('SPLIT_BY_VM_TABLET_MODE', []))):
        vm_tablet_mode_list.append(True)

    for abi, abi_bits in abi_bits_list:
        for shard_index in range(shard_count):
            for vm_force_max_resolution in vm_force_max_resolution_list:
                for vm_tablet_mode in vm_tablet_mode_list:
                    filename = get_controlfile_name(
                            name,
                            abi,
                            revision,
                            is_public,
                            hardware_suite=hardware_suite,
                            abi_bits=abi_bits,
                            shard=(shard_index, shard_count),
                            vm_force_max_resolution=vm_force_max_resolution,
                            vm_tablet_mode=vm_tablet_mode)
                    content = get_controlfile_content(
                            name,
                            modules,
                            abi,
                            revision,
                            build,
                            uri,
                            suites,
                            source_type,
                            hardware_suite=hardware_suite,
                            whole_module_set=whole_module_set,
                            abi_bits=abi_bits,
                            shard=(shard_index, shard_count),
                            vm_force_max_resolution=vm_force_max_resolution,
                            vm_tablet_mode=vm_tablet_mode,
                            shard_ref_test=shard_ref_test)
                    with open(filename, 'w') as f:
                        f.write(content)


def write_moblab_controlfiles(modules, abi, revision, build, uri):
    """Write all control files for moblab.

    Nothing gets combined.

    Moblab uses one module per job. In some cases like Deqp which can run super
    long it even creates several jobs per module. Moblab can do this as it has
    less relative overhead spinning up jobs than the lab.
    """
    for module in modules:
        # No need to generate control files with extra suffix, since --module
        # option will cover variants with optional parameters.
        if is_parameterized_module(module):
            continue
        write_controlfile(module,
                          set([module]),
                          abi,
                          revision,
                          build,
                          uri,
                          None,
                          source_type=SourceType.MOBLAB)


def write_regression_controlfiles(modules, abi, revision, build, uri,
                                  source_type):
    """Write all control files for stainless/ToT regression lab coverage.

    Regression coverage on tot currently relies heavily on watching stainless
    dashboard and sponge. So instead of running everything in a single run
    we split CTS into many jobs. It used to be one job per module, but that
    became too much in P (more than 300 per ABI). Instead we combine modules
    with similar names and run these in the same job (alphabetically).
    """

    combined = combine_modules_by_common_word(set(modules))
    for key in combined:
        write_controlfile(key, combined[key], abi, revision, build, uri,
                          None, source_type)


def write_qualification_controlfiles(modules, abi, revision, build, uri,
                                     source_type):
    """Write all control files to run "all" tests for qualification.

    Qualification was performed on N by running all tests using tradefed
    sharding (specifying SYNC_COUNT=2) in the control files. In skylab
    this is currently not implemented, so we fall back to autotest sharding
    all CTS tests into 10-20 hand chosen shards.
    """
    if CONFIG.get('SINGLE_CONTROL_FILE'):
        module_set = set(modules)
        write_controlfile('all',
                          module_set,
                          abi,
                          revision,
                          build,
                          uri,
                          None,
                          source_type,
                          whole_module_set=module_set)
    else:
        combined = combine_modules_by_bookmark(set(modules))
        for key in combined:
            write_controlfile('all.' + key, combined[key], abi, revision, build,
                              uri, CONFIG.get('QUAL_SUITE_NAMES'), source_type)


def write_qualification_suite_split_controlfiles(modules, abi, revision, build,
                                                 uri, source_type):
    """Fork of write_qualification_controlfiles with suite splitting applied."""
    combined = combine_modules_by_suite_split_shards(CONFIG['SPLIT_SUITES'],
                                                     set(modules))
    for key, shard_ref_test, modules in combined:
        write_controlfile('all.' + key,
                          modules,
                          abi,
                          revision,
                          build,
                          uri,
                          CONFIG.get('QUAL_SUITE_NAMES'),
                          source_type,
                          shard_ref_test=shard_ref_test)


def write_perf_qualification_controlfiles(_modules, abi, revision, build, uri,
                                     source_type):
    """Write control files to run performance qualification tests.
    """
    for module, config in CONFIG.get('PERF_MODULES', dict()).items():
        for submodule, suites in config.items():
            write_controlfile(submodule, set([submodule]), abi, revision,
                              build, uri, suites, source_type)


def write_qualification_and_regression_controlfile(modules, abi, revision,
                                                   build, uri, source_type):
    """Write a control file to run "all" tests for qualification and regression.
    """
    # For cts-instant, qualication control files are expected to cover
    # regressions as well. Apply both regression and qual suites.
    suites = CONFIG.get('INTERNAL_SUITE_NAMES', []) + CONFIG.get(
            'QUAL_SUITE_NAMES', [])
    module_set = set(modules)
    combined = combine_modules_by_bookmark(module_set)
    for key in combined:
        write_controlfile('all.' + key,
                          combined[key],
                          abi,
                          revision,
                          build,
                          uri,
                          suites,
                          source_type,
                          whole_module_set=module_set)


def write_collect_controlfiles(_modules,
                               abi,
                               revision,
                               build,
                               uri,
                               source_type,
                               is_hardware=False):
    """Write all control files for test collection used as reference to

    compute completeness (missing tests) on the CTS dashboard.
    """
    is_public = (source_type == SourceType.MOBLAB)
    if is_public:
        if is_hardware:
            suites = [CONFIG['MOBLAB_HARDWARE_SUITE_NAME']]
        else:
            suites = [CONFIG['MOBLAB_SUITE_NAME']]
    else:
        if is_hardware:
            suites = [CONFIG['HARDWARE_SUITE_NAME']]
        else:
            suites = CONFIG['INTERNAL_SUITE_NAMES'] \
                   + CONFIG.get('QUAL_SUITE_NAMES', [])
    for module in get_collect_modules(is_public, is_hardware=is_hardware):
        write_controlfile(module,
                          set([module]),
                          abi,
                          revision,
                          build,
                          uri,
                          suites,
                          source_type,
                          hardware_suite=is_hardware)


def write_extra_controlfiles(_modules, abi, revision, build, uri, source_type):
    """Write all extra control files as specified in config.

    This is used by moblab to load balance large modules like Deqp, as well as
    making custom modules such as WM presubmit. A similar approach was also used
    during bringup of grunt to split media tests.
    """
    for module, config in get_extra_modules_dict(source_type, abi).items():
        for submodule, suites in config.items():
            write_controlfile(submodule, set([submodule]), abi, revision,
                              build, uri, suites, source_type)


def write_hardwaresuite_controlfiles(abi, revision, build, uri, source_type):
    """Control files for Build variant hardware only tests."""
    is_public = (source_type == SourceType.MOBLAB)
    cts_hardware_modules = get_cts_hardware_modules(is_public)
    for module in cts_hardware_modules:
        write_controlfile(module, set([module]), abi, revision, build, uri, None,
                          source_type=source_type, hardware_suite=True)

    for module, config in get_extra_hardware_modules_dict(is_public, abi).items():
        for submodule, suites in config.items():
            name = get_controlfile_name(submodule, abi, revision, is_public,
                                        hardware_suite=True)
            content = get_controlfile_content(submodule,
                                              set([submodule]),
                                              abi,
                                              revision,
                                              build,
                                              uri,
                                              None,
                                              source_type,
                                              hardware_suite=True)
            with open(name, 'w') as f:
                f.write(content)


def write_extra_camera_controlfiles(abi, revision, build, uri, source_type):
    """Control files for CtsCameraTestCases.camerabox.*"""
    module = 'CtsCameraTestCases'
    is_public = (source_type == SourceType.MOBLAB)
    for facing in ['back', 'front', 'nocamera']:
        name = get_controlfile_name(module, abi, revision, is_public, facing)
        content = get_controlfile_content(module,
                                          set([module]),
                                          abi,
                                          revision,
                                          build,
                                          uri,
                                          None,
                                          source_type,
                                          camera_facing=facing)
        with open(name, 'w') as f:
            f.write(content)


def calculate_suite_split_shards(config):
    """Pre-calculate shards for suite splitting based on runtime hint.

    Args:
        config: CONFIG['SPLIT_SUITES']
    """
    max_runtime = config['MAX_RUNTIME_SECS']
    per_test_overhead = config['PER_TEST_OVERHEAD_SECS']

    def _calculate(test_runtimes, is_vm_stable):
        if not test_runtimes:
            return {}
        log_prefix = '[VM-stable]' if is_vm_stable else '[non-VM-stable]'
        calculated = {}
        cur_shard = 1
        cur_total_runtime = 0
        long_total_runtime = 0
        for test, runtime in test_runtimes.items():
            runtime += per_test_overhead
            if runtime > max_runtime:
                # Mark the test as a "long" test
                logging.info('%s Marking long test: %s (%.1fh)', log_prefix,
                             test, runtime / 3600)
                calculated[test] = -1
                long_total_runtime += runtime
                continue
            if cur_total_runtime + runtime > max_runtime:
                # Current shard is full; increment shard count
                cur_shard += 1
                cur_total_runtime = 0
            # Add test to current shard
            calculated[test] = cur_shard
            cur_total_runtime += runtime
        logging.info('%s Suite to be splitted into %d shards', log_prefix,
                     cur_shard)
        logging.info('%s Long test total runtime: %.1fh', log_prefix,
                     long_total_runtime / 3600)
        return calculated

    nonvm_test_runtimes, vm_test_runtimes = {}, {}
    for test, runtime in sorted(config['RUNTIME_HINT_SECS'].items()):
        is_vm_stable = is_vm_modules(test) and not is_unstable_vm_modules(test)
        (vm_test_runtimes
         if is_vm_stable else nonvm_test_runtimes)[test] = runtime

    config['CALCULATED_SHARDS'] = _calculate(nonvm_test_runtimes, False)
    config['CALCULATED_SHARDS_VM_STABLE'] = _calculate(vm_test_runtimes, True)


def get_suite_split_shard_number(config, test):
    """Retrieves the shard number the test belongs to.

    Args:
        config: CONFIG['SPLIT_SUITES']
        test: The combined test name, optionally with suffixes when applicable.

    Returns:
        (shard, is_vm_stable):
            shard: An integer; -1 stands for long test.
            is_vm_stable: Whether it's a VM-stable shard.
    """
    if 'CALCULATED_SHARDS' not in config:
        raise ValueError('Call calculate_suite_split_shards() first')
    if test is None:
        # This happens in cases incompatible with suite splitting algorithm;
        # assume long test for the purpose of suite split
        return -1, False
    try:
        return config['CALCULATED_SHARDS'][test], False
    except KeyError:
        try:
            return config['CALCULATED_SHARDS_VM_STABLE'][test], True
        except KeyError:
            logging.warn(
                    'Test %s not found in runtime hint, assuming long test',
                    test)
            return -1, False


def get_suite_split_shard_name(config, is_qual, test, abi, abi_bits):
    """Retrieves the shard suite name the test belongs to.

    Args:
        config: CONFIG['SPLIT_SUITES']
        is_qual: True if the test belongs to qual suite.
        test: The combined test name, optionally with suffixes when applicable.
        abi: The abi to run.
        abi_bits: (For applicable tests only) bits variant.

    Returns:
        The suite name representing the shard the test belongs to.
    """
    if test and abi_bits:
        test += f'.{abi_bits}'
    shard, is_vm_stable = get_suite_split_shard_number(config, test)
    if shard == -1:
        if is_vm_stable:
            return (config['QUAL_VM_STABLE_SUITE_LONG']
                    if is_qual else config['DEV_VM_STABLE_SUITE_LONG'])
        else:
            return (config['QUAL_SUITE_LONG']
                    if is_qual else config['DEV_SUITE_LONG'])
    if is_vm_stable:
        fmt = config['QUAL_VM_STABLE_SUITE_FORMAT'] if is_qual else config[
                'DEV_VM_STABLE_SUITE_FORMAT']
    else:
        fmt = config['QUAL_SUITE_FORMAT'] if is_qual else config[
                'DEV_SUITE_FORMAT']
    return fmt.format(abi=abi, shard=shard)


def run(source_contents, cache_dir, bundle_password=''):
    """Downloads each bundle in |uris| and generates control files for each

    module as reported to us by tradefed.
    """
    if 'SPLIT_SUITES' in CONFIG:
        calculate_suite_split_shards(CONFIG['SPLIT_SUITES'])

    for uri, source_type in source_contents:
        abi = get_bundle_abi(uri)
        is_public = (source_type == SourceType.MOBLAB)
        # Get tradefed data by downloading & unzipping the files
        with tempfile.TemporaryDirectory(prefix='cts-android_') as tmp:
            if cache_dir is not None:
                assert(os.path.isdir(cache_dir))
                bundle = os.path.join(cache_dir, os.path.basename(uri))
                if not os.path.exists(bundle):
                    logging.info('Downloading to %s.', cache_dir)
                    download(uri, bundle)
            else:
                bundle = os.path.join(tmp, os.path.basename(uri))
                logging.info('Downloading to %s.', tmp)
                download(uri, bundle)
            logging.info('Extracting %s.', bundle)
            unzip(bundle, tmp, bundle_password)
            modules, build, revision = get_tradefed_data(
                    tmp, extra_executables=CONFIG.get('EXECUTABLE_PATH_LIST'))
            if not revision:
                raise Exception('Could not determine revision.')

            logging.info('Writing all control files.')
            if source_type == SourceType.MOBLAB:
                write_moblab_controlfiles(modules, abi, revision, build, uri)

            if CONFIG['CONTROLFILE_WRITE_SIMPLE_QUAL_AND_REGRESS']:
                # Might be worth generating DEV control files, but since this
                # is used for only ARC-P CTS_Instant modules whose regression
                # is 99.99% coverved by CTS DEV runs, having only LATEST is
                # sufficient.
                if source_type == SourceType.LATEST:
                    write_qualification_and_regression_controlfile(
                            modules, abi, revision, build, uri, source_type)
            else:
                if source_type == SourceType.DEV:
                    write_regression_controlfiles(modules, abi, revision,
                                                  build, uri, source_type)
                    write_perf_qualification_controlfiles(None, abi, revision,
                                                          build, uri, source_type)
                if source_type == SourceType.LATEST:
                    if 'SPLIT_SUITES' in CONFIG:
                        write_qualification_suite_split_controlfiles(
                                modules, abi, revision, build, uri,
                                source_type)
                    else:
                        write_qualification_controlfiles(
                                modules, abi, revision, build, uri,
                                source_type)

            if CONFIG['CONTROLFILE_WRITE_CAMERA']:
                # For now camerabox is not stable for qualification purpose.
                # Hence, the usage is limited to DEV. In the future we need
                # to reconsider.
                if source_type == SourceType.DEV:
                    write_extra_camera_controlfiles(abi, revision, build, uri,
                                                    source_type)

            if CONFIG.get('CONTROLFILE_WRITE_COLLECT', True):
                # Collect-test control files are used for checking the test
                # completeness before qualification. Not needed for DEV.
                if source_type == SourceType.LATEST or source_type == SourceType.MOBLAB:
                    for_hardware_suite = [False]
                    if 'HARDWARE_MODULES' in CONFIG:
                        for_hardware_suite.append(True)
                    for is_hardware in for_hardware_suite:
                        write_collect_controlfiles(modules,
                                                   abi,
                                                   revision,
                                                   build,
                                                   uri,
                                                   source_type,
                                                   is_hardware=is_hardware)

            if CONFIG['CONTROLFILE_WRITE_EXTRA']:
                # "EXTRA" control files are for workaround test instability
                # by running only sub-tests. For now let's attribute them to
                # qualification suites, since it is sometimes critical to
                # have the stability for qualification. If needed we need to
                # implement some way to add them to DEV suites as well.
                if source_type == SourceType.LATEST or source_type == SourceType.MOBLAB:
                    write_extra_controlfiles(None, abi, revision, build, uri,
                                             source_type)

            # "Hardware only" jobs are for reducing tests on qualification.
            if source_type == SourceType.LATEST or source_type == SourceType.MOBLAB:
                write_hardwaresuite_controlfiles(abi, revision, build, uri,
                                                 source_type)


def main(config):
    """ Entry method of generator """

    global CONFIG
    CONFIG = config

    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(
        description='Create control files for a CTS bundle on GS.',
        formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument(
            '--is_public',
            dest='is_public',
            default=False,
            action='store_true',
            help='Generate the public control files for CTS, default generate'
            ' the internal control files')
    parser.add_argument(
            '--is_latest',
            dest='is_latest',
            default=False,
            action='store_true',
            help='Generate the control files for CTS from the latest CTS bundle'
            ' stored in the internal storage')
    parser.add_argument(
            '--is_all',
            dest='is_all',
            default=False,
            action='store_true',
            help='Generate the public, latest, and dev control files')
    parser.add_argument(
            '--cache_dir',
            dest='cache_dir',
            default=None,
            action='store',
            help='Cache directory for downloaded bundle file. Uses the cached '
            'bundle file if exists, or caches a downloaded file to this '
            'directory if not.')
    args = parser.parse_args()

    config_path = CONFIG['BUNDLE_CONFIG_PATH']
    url_config = bundle_utils.load_config(config_path)

    source_contents = []
    if args.is_public or args.is_all:
        urls = bundle_utils.make_urls_for_all_abis(url_config, None)
        for url in urls:
            source_contents.append((url, SourceType.MOBLAB))
    if args.is_latest or args.is_all:
        urls = bundle_utils.make_urls_for_all_abis(url_config, 'LATEST')
        for url in urls:
            source_contents.append((url, SourceType.LATEST))
    if (not args.is_public and not args.is_latest) or args.is_all:
        urls = bundle_utils.make_urls_for_all_abis(url_config, 'DEV')
        for url in urls:
            source_contents.append((url, SourceType.DEV))
    run(source_contents, args.cache_dir,
        bundle_utils.get_bundle_password(url_config))
