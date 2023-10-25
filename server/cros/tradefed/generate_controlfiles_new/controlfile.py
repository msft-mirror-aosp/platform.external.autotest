# Copyright 2023 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Functions for generating the actual controlfile content.

TODO(b/289468003): This still largely relies on the legacy script. Reimplement
the logic here and clean up glue code.
"""

import generate_controlfiles_common as gcc

from .bundle import Bundle
from .common import *


def _get_extension(group: ModuleGroup, abi: str, revision: str,
                   is_public: bool) -> str:
    return gcc.get_extension(group['basename'],
                             abi,
                             revision,
                             is_public=is_public,
                             camera_facing=group.get('camera_facing'),
                             hardware_suite=group.get('hardware_suite', False),
                             abi_bits=group.get('abi_bits'),
                             shard=group.get('shard', (0, 1)),
                             vm_force_max_resolution=group.get(
                                     'vm_force_max_resolution', False),
                             vm_tablet_mode=group.get('vm_tablet_mode', False))


def get_controlfile_name(group: ModuleGroup, bundle: Bundle) -> str:
    """Returns the name of the control file.

    Args:
        group: the module group corresponding to the control file.
        bundle: the bundle corresponding to the control file.

    Returns:
        The name of the control file.
    """
    extension = _get_extension(group, bundle.abi, bundle.revision,
                               bundle.source_type == 'MOBLAB')
    return f"control.{extension}"


def get_controlfile_content(group: ModuleGroup, config: Config,
                            bundle: Bundle) -> str:
    """Returns the contents of the control file.

    Args:
        group: the module group corresponding to the control file.
        config: the config dictionary.
        bundle: the bundle corresponding to the control file.

    Returns:
        The contents of the control file.
    """
    modules = group['modules']
    suites = sorted(group.get('suites', []))
    revision = bundle.revision
    build = bundle.build
    abi = bundle.abi
    uri = None if bundle.source_type == 'MOBLAB' else bundle.source_type
    abi_bits = group.get('abi_bits')
    is_public = bundle.source_type == 'MOBLAB'
    attributes = ', '.join(suites)
    shard = group.get('shard', (0, 1))
    camera_facing = group.get('camera_facing')
    hardware_suite = group.get('hardware_suite', False)
    subplan = group.get('subplan')
    vm_force_max_resolution = group.get('vm_force_max_resolution', False)
    vm_tablet_mode = group.get('vm_tablet_mode', False)

    target_module = group['basename']
    # Special case to match old behavior.
    # TODO cleanup this
    if (target_module in gcc.get_collect_modules(is_public)
                or target_module == 'all'):
        target_module = None

    tag = _get_extension(group, bundle.abi, bundle.revision, is_public)
    name = f"{config['TEST_NAME']}.{tag}"
    abi_to_run = {
            ("arm", 32): 'armeabi-v7a',
            ("arm", 64): 'arm64-v8a',
            ("x86", 32): 'x86',
            ("x86", 64): 'x86_64'
    }.get((abi, abi_bits), None)
    whole_module_set = None
    executable_test_count = None

    # TODO cleanup all references to legacy code
    return gcc.render_config(
            year=config['COPYRIGHT_YEAR'],
            name=name,
            base_name=config['TEST_NAME'],
            test_func_name=config['CONTROLFILE_TEST_FUNCTION_NAME'],
            attributes=attributes,
            dependencies=gcc.get_dependencies(modules, abi, is_public,
                                              camera_facing),
            extra_artifacts=gcc.get_extra_artifacts(modules),
            extra_artifacts_host=gcc.get_extra_artifacts_host(modules),
            job_retries=gcc.get_job_retries(modules, is_public, suites),
            max_result_size_kb=gcc.get_max_result_size_kb(modules, is_public),
            revision=revision,
            build=build,
            abi=abi,
            needs_push_media=gcc.needs_push_media(modules),
            needs_cts_helpers=gcc.needs_cts_helpers(modules),
            enable_default_apps=gcc.enable_default_apps(modules),
            vm_force_max_resolution=vm_force_max_resolution,
            vm_tablet_mode=vm_tablet_mode,
            tag=tag,
            uri=uri,
            servo_support_needed=gcc.servo_support_needed(modules, is_public),
            wifi_info_needed=gcc.wifi_info_needed(modules, is_public),
            has_precondition_escape=gcc.has_precondition_escape(
                    modules, is_public),
            max_retries=gcc.get_max_retries(modules, abi, suites, is_public,
                                            shard),
            timeout=gcc.calculate_timeout(modules, suites),
            run_template=gcc.get_run_template(
                    modules,
                    is_public,
                    abi_to_run=config.get('REPRESENTATIVE_ABI',
                                          {}).get(abi, abi_to_run),
                    shard=shard,
                    whole_module_set=whole_module_set,
                    is_hardware=hardware_suite),
            retry_template=gcc.get_retry_template(modules, is_public),
            target_module=target_module,
            target_plan=subplan,
            test_length=gcc.get_test_length(modules),
            priority=gcc.get_test_priority(modules, is_public),
            extra_args=gcc.get_extra_args(modules, is_public),
            authkey=gcc.get_authkey(is_public),
            sync_count=gcc.get_sync_count(modules, abi, is_public),
            camera_facing=camera_facing,
            executable_test_count=executable_test_count)
