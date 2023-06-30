# Copyright 2023 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import argparse
import collections
import copy
import logging
from typing import Any, Callable, Dict, Iterable, Optional

import bundle_utils
import generate_controlfiles_common as gcc

from .bundle import *
from .combine import *
from .common import *
from .controlfile import *
from .filters import *
from .passes import *

_source_type_to_gen_funcs = collections.defaultdict(list)


def generate_from_source_type(
        source_type: str
) -> Callable[[Callable[[Bundle, Config], Iterable[ModuleGroup]]], None]:
    """Decorator that associates a generator function with given source type.

    A generator function must be of the following signature:
    def gen(bundle: Bundle, config: Config) -> Iterable[ModuleGroup]

    Args:
        source_type: either of 'MOBLAB', 'LATEST', 'DEV'.
    """
    def inner(
            gen_func: Callable[[Bundle, Config],
                               Iterable[ModuleGroup]]) -> None:
        _source_type_to_gen_funcs[source_type].append(gen_func)

    return inner


def generators_for_source_type(
        source_type: str
) -> Iterable[Callable[[Bundle, Config], Iterable[ModuleGroup]]]:
    """Returns a list of generators associated with given source type.

    Args:
        source_type: either of 'MOBLAB', 'LATEST', 'DEV'.

    Returns:
        A list of generator functions.
    """
    return _source_type_to_gen_funcs[source_type]


@generate_from_source_type('DEV')
def gen_regression(bundle: Bundle, config: Config) -> Iterable[ModuleGroup]:
    """Generates regression controlfiles."""
    logging.info('Generating regression controlfiles')
    groups = combine_modules_by_common_word(bundle.modules)

    vm_config = config.get('VM_CONFIG', {})
    split_config = config.get('SPLIT_SUITES', {})
    shard_config = config.get('SHARD_COUNT', {})

    # yapf: disable
    passes = Concat([
        IfNot(
            has_modules(gcc.get_camera_modules()),
            [
                If(
                    filter_and(bundle.abi == 'arm', has_modules(config['BVT_PERBUILD'])),
                    [AddSuites(['suite:bvt-perbuild'])],
                ),
                If(
                    has_modules(config['SPLIT_BY_BITS_MODULES']),
                    [SplitByBits()],
                ),
                Concat([
                    If(
                        has_modules([module]),
                        [SplitByTFShards(shard_count, keep_unsharded=True)],
                    )
                    for module, shard_count in shard_config.items()
                ]),
                If(
                    vm_config,
                    [SetVMAttrs(
                        vm_config.get('MODULES_RULES'),
                        vm_config.get('UNSTABLE_MODULES_RULES'),
                    )],
                ),
                If(
                    split_config,
                    [
                        If(
                            lambda g: g.get('vm_stable'),
                            [AddSplitSuites(
                                split_config,
                                split_config.get('DEV_VM_STABLE_SUITE_FORMAT'),
                                split_config.get('DEV_VM_STABLE_SUITE_LONG'),
                                bundle.abi,
                            )],
                        ),
                        If(
                            lambda g: not g.get('vm_stable'),
                            [AddSplitSuites(
                                split_config,
                                split_config.get('DEV_SUITE_FORMAT'),
                                split_config.get('DEV_SUITE_LONG'),
                                bundle.abi,
                            )],
                        ),
                    ],
                ),
                If(
                    has_modules(config.get('SPLIT_BY_VM_FORCE_MAX_RESOLUTION', [])),
                    [SplitByAttr('vm_force_max_resolution', [False, True])],
                ),
                If(
                    has_modules(config.get('SPLIT_BY_VM_TABLET_MODE', [])),
                    [SplitByAttr('vm_tablet_mode', [False, True])],
                ),
                AddSuites(config['INTERNAL_SUITE_NAMES']),
                If(
                    lambda g: g.get('vm_stable'),
                    [
                        AddSuites([vm_config.get('STABLE_SUITE_NAME')]),
                        RemoveSuites(vm_config.get('STABLE_SKIP_SUITES')),
                    ],
                ),
                If(
                    lambda g: g.get('vm_force_max_resolution') or g.get('vm_tablet_mode'),
                    [ClearSuites()],
                ),
                If(
                    lambda g: vm_config.get('RUN_SINGLE_ABI', bundle.abi) == bundle.abi and g.get('vm'),
                    [AddSuites([vm_config.get('SUITE_NAME')])],
                ),
                Concat(
                    If(
                        has_modules([module]),
                        [AddSuites(suites)],
                    )
                    for module, suites in config['EXTRA_ATTRIBUTES'].items()
                ),
            ],
        ),
    ])
    # yapf: enable

    return passes.process_all_groups(groups)


@generate_from_source_type('DEV')
def gen_perf_qual(bundle: Bundle, config: Config) -> Iterable[ModuleGroup]:
    """Generates perf qualification controlfiles."""
    perf_modules = config.get('PERF_MODULES', {})
    if not perf_modules:
        return []
    logging.info('Generating perf qualification controlfiles')
    return [
            ModuleGroup(basename=submodule,
                        modules=frozenset([submodule]),
                        suites=frozenset(suites)) for module in perf_modules
            for submodule, suites in perf_modules[module].items()
    ]


@generate_from_source_type('DEV')
def gen_extra_camera(bundle: Bundle, config: Config) -> Iterable[ModuleGroup]:
    """Generates extra camera controlfiles."""
    if not config.get('CONTROLFILE_WRITE_CAMERA'):
        return []
    logging.info('Generating extra camera controlfiles')
    return [
            ModuleGroup(basename='CtsCameraTestCases',
                        modules=frozenset(['CtsCameraTestCases']),
                        suites=frozenset(['suite:arc-cts-camera']),
                        camera_facing=camera_facing)
            for camera_facing in ('back', 'front', 'nocamera')
    ]


@generate_from_source_type('LATEST')
def gen_qual(bundle: Bundle, config: Config) -> Iterable[ModuleGroup]:
    """Generates qualification controlfiles."""
    logging.info('Generating qualification controlfiles')
    groups = combine_modules_by_common_word(bundle.modules)

    vm_config = config.get('VM_CONFIG', {})
    split_config = config.get('SPLIT_SUITES', {})
    shard_config = config.get('SHARD_COUNT', {})

    # yapf: disable
    passes = Concat([
        If(
            has_modules(config['SPLIT_BY_BITS_MODULES']),
            [SplitByBits()],
        ),
        Concat([
            If(
                has_modules([module]),
                [SplitByTFShards(shard_count)],
            )
            for module, shard_count in shard_config.items()
        ]),
        If(
            vm_config,
            [
                SetVMAttrs(
                    vm_config.get('MODULES_RULES'),
                    vm_config.get('UNSTABLE_MODULES_RULES'),
                ),
                If(
                    lambda g: g['vm_stable'],
                    [MergeSplitSuites(
                        split_config,
                        split_config.get('QUAL_VM_STABLE_SUITE_FORMAT'),
                        split_config.get('QUAL_VM_STABLE_SUITE_LONG'),
                        bundle.abi,
                        basename_prefix='all.vm_stable',
                    )],
                ),
            ],
        ),
        If(
            lambda g: 'merged' not in g,
            [MergeSplitSuites(
                split_config,
                split_config.get('QUAL_SUITE_FORMAT'),
                split_config.get('QUAL_SUITE_LONG'),
                bundle.abi,
            )],
        ),
        AddSuites(config['QUAL_SUITE_NAMES']),
        If(
            has_modules(gcc.get_camera_modules()),
            [RemoveSuites(config['QUAL_SUITE_NAMES'] + [split_config['QUAL_SUITE_LONG']])],
        ),
        If(
            filter_and('CAMERA_DUT_SUITE_NAME' in config, has_modules(gcc.get_camera_modules())),
            [AddSuites([config.get('CAMERA_DUT_SUITE_NAME')])],
        ),
    ])
    # yapf: enable

    return passes.process_all_groups(groups)


@generate_from_source_type('LATEST')
def gen_internal_collect(bundle: Bundle,
                         config: Config) -> Iterable[ModuleGroup]:
    """Generates internal collect controlfiles."""
    logging.info('Generating internal collect controlfiles')

    COLLECT = 'tradefed-run-collect-tests-only-internal'
    CTSHARDWARE_COLLECT = 'tradefed-run-collect-tests-only-hardware-internal'

    for_hardware_suite = [False]
    if 'HARDWARE_MODULES' in config:
        for_hardware_suite.append(True)
    suffices = ['']
    if config.get('CONTROLFILE_WRITE_CAMERA'):
        suffices.extend(['.camerabox.front', '.camerabox.back'])

    groups = []
    for hardware_suite in for_hardware_suite:
        if hardware_suite:
            suites = [config['HARDWARE_SUITE_NAME']]
        else:
            suites = (config['INTERNAL_SUITE_NAMES'] +
                      config.get('QUAL_SUITE_NAMES', []))
            if 'SPLIT_SUITES' in config:
                suites.append(config['SPLIT_SUITES']['QUAL_SUITE_LONG'])
        suites = frozenset(suites)

        for suffix in suffices:
            basename = CTSHARDWARE_COLLECT if hardware_suite else COLLECT
            basename += suffix
            subplan = 'cts-hardware' if hardware_suite and not suffix else None
            groups.append(
                    ModuleGroup(
                            basename=basename,
                            # TODO clean up the semantics of "modules"
                            modules=set([basename]),
                            suites=suites,
                            hardware_suite=hardware_suite,
                            subplan=subplan,
                    ))
    return groups


@generate_from_source_type('LATEST')
def gen_internal_hardwaresuite(bundle: Bundle,
                               config: Config) -> Iterable[ModuleGroup]:
    """Generates internal hardware suite controlfiles."""
    modules = config.get('HARDWARE_MODULES', [])
    extra_modules = config.get('HARDWAREONLY_EXTRA_MODULES', {})
    if not modules and not extra_modules:
        return []

    logging.info('Generating internal hardware suite controlfiles')
    groups = [
            ModuleGroup(basename=module, modules=frozenset([module]))
            for module in modules
    ] + [
            ModuleGroup(basename=submodule, modules=frozenset([submodule]))
            for module in extra_modules for submodule in extra_modules[module]
    ]

    passes = Concat([
            If(
                    has_modules(config['SPLIT_BY_BITS_MODULES']),
                    [SplitByBits()],
            ),
            AddSuites([config['HARDWARE_SUITE_NAME']]),
            SetAttr('hardware_suite', True),
    ])

    return passes.process_all_groups(groups)


@generate_from_source_type('LATEST')
def gen_internal_extra(bundle: Bundle,
                       config: Config) -> Iterable[ModuleGroup]:
    """Generates internal extra controlfiles."""
    if not config.get('CONTROLFILE_WRITE_EXTRA'):
        return []
    extra_modules = config['EXTRA_MODULES']
    if not extra_modules:
        return []

    logging.info('Generating internal extra controlfiles')
    return [
            ModuleGroup(basename=submodule,
                        modules=frozenset([submodule]),
                        suites=frozenset(suites)) for module in extra_modules
            for submodule, suites in extra_modules[module].items()
    ]


@generate_from_source_type('MOBLAB')
def gen_moblab(bundle: Bundle, config: Config) -> Iterable[ModuleGroup]:
    """Generates moblab controlfiles."""
    logging.info('Generating moblab controlfiles')
    groups = [
            ModuleGroup(basename=module, modules=frozenset([module]))
            for module in bundle.modules if '[' not in module
    ]

    passes = Concat([
            If(
                    has_modules(config.get('PUBLIC_SPLIT_BY_BITS_MODULES',
                                           [])),
                    [SplitByBits()],
            ),
            AddSuites([config['MOBLAB_SUITE_NAME']]),
    ])

    return passes.process_all_groups(groups)


@generate_from_source_type('MOBLAB')
def gen_moblab_collect(bundle: Bundle,
                       config: Config) -> Iterable[ModuleGroup]:
    """Generates moblab collect controlfiles."""
    logging.info('Generating moblab collect controlfiles')

    COLLECT = 'tradefed-run-collect-tests-only'
    CTSHARDWARE_COLLECT = 'tradefed-run-collect-tests-only-hardware'

    for_hardware_suite = [False]
    if 'HARDWARE_MODULES' in config:
        for_hardware_suite.append(True)

    groups = []
    for hardware_suite in for_hardware_suite:
        if hardware_suite:
            suites = frozenset([config['MOBLAB_HARDWARE_SUITE_NAME']])
        else:
            suites = frozenset([config['MOBLAB_SUITE_NAME']])
        basename = CTSHARDWARE_COLLECT if hardware_suite else COLLECT
        subplan = 'cts-hardware' if hardware_suite else None
        groups.append(
                ModuleGroup(
                        basename=basename,
                        # TODO clean up the semantics of "modules"
                        modules=set([basename]),
                        suites=suites,
                        hardware_suite=hardware_suite,
                        subplan=subplan,
                ))
    return groups


@generate_from_source_type('MOBLAB')
def gen_moblab_hardwaresuite(bundle: Bundle,
                             config: Config) -> Iterable[ModuleGroup]:
    """Generates moblab hardware suite controlfiles."""
    modules = config.get('PUBLIC_HARDWARE_MODULES', [])
    extra_modules = config.get('HARDWAREONLY_EXTRA_MODULES', {})
    if not modules and not extra_modules:
        return []

    logging.info('Generating moblab hardware suite controlfiles')
    groups = [
            ModuleGroup(basename=module, modules=frozenset([module]))
            for module in modules
    ] + [
            ModuleGroup(basename=submodule, modules=frozenset([submodule]))
            for module in extra_modules for submodule in extra_modules[module]
    ]

    passes = Concat([
            If(
                    has_modules(config.get('PUBLIC_SPLIT_BY_BITS_MODULES',
                                           [])),
                    [SplitByBits()],
            ),
            AddSuites([config['MOBLAB_HARDWARE_SUITE_NAME']]),
            SetAttr('hardware_suite', True),
    ])

    return passes.process_all_groups(groups)


@generate_from_source_type('MOBLAB')
def gen_moblab_extra(bundle: Bundle, config: Config) -> Iterable[ModuleGroup]:
    """Generates moblab extra controlfiles."""
    if not config.get('CONTROLFILE_WRITE_EXTRA'):
        return []
    extra_modules = config['PUBLIC_EXTRA_MODULES'].get(bundle.abi)
    if not extra_modules:
        return []

    logging.info('Generating moblab extra controlfiles')

    overrides = config['EXTRA_SUBMODULE_OVERRIDE'].get(bundle.abi)
    if overrides:
        extra_modules = copy.deepcopy(extra_modules)
        for module in extra_modules:
            for old, news in overrides.items():
                if old in extra_modules[module].keys():
                    suites = extra_modules[module][old]
                    extra_modules[module].pop(old)
                    for submodule in news:
                        extra_modules[module][submodule] = suites

    return [
            ModuleGroup(basename=submodule,
                        modules=frozenset([submodule]),
                        suites=frozenset(suites)) for module in extra_modules
            for submodule, suites in extra_modules[module].items()
    ]


def gen_controlfiles_for_source_type(source_type: str, config: Config,
                                     cache_dir: Optional[str]) -> None:
    """Generate controlfiles for given source type.

    Args:
        source_type: either of 'MOBLAB', 'LATEST', 'DEV'.
        config: the config dictionary.
        cache_dir: optional path to the bundle cache.
    """
    gen_funcs = generators_for_source_type(source_type)
    if not gen_funcs:
        logging.warn('No generators associated with source type %s',
                     source_type)
        return
    logging.info('Generating controlfiles for source type %s', source_type)

    config_path = config['BUNDLE_CONFIG_PATH']
    url_config = bundle_utils.load_config(config_path)

    for abi in bundle_utils.get_abi_info(url_config):
        bundle = Bundle.download(config, url_config, source_type, abi,
                                 cache_dir)
        groups = []
        for gen in gen_funcs:
            groups += gen(bundle, config)

        logging.info('Writing controlfiles for abi: %s', abi)
        for group in groups:
            filename = get_controlfile_name(group, bundle)
            content = get_controlfile_content(group, config, bundle)
            logging.debug('Writing file: %s', filename)
            with open(filename, 'w') as f:
                f.write(content)


def main(config: Dict[str, Any]) -> None:
    """Entry point of the script.

    Args:
        config: the config dictionary.
    """
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
    parser.add_argument('--log_level', default='INFO', help='Sets log level.')
    args = parser.parse_args()

    logging.basicConfig(level=args.log_level)
    gcc.inject_config(config)
    config = Config(config)

    if args.is_public or args.is_all:
        gen_controlfiles_for_source_type('MOBLAB', config, args.cache_dir)

    if args.is_latest or args.is_all:
        gen_controlfiles_for_source_type('LATEST', config, args.cache_dir)
        # TODO generate CTS-Instant controlfiles

    if (not args.is_public and not args.is_latest) or args.is_all:
        gen_controlfiles_for_source_type('DEV', config, args.cache_dir)
