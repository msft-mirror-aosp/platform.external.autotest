# Copyright 2023 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import collections
import copy
import logging
import re
from typing import Any, Callable, Iterable, Union

from generate_controlfiles_new.common import ModuleGroup

from . import suite_split
from .common import ModuleGroup


class Pass:
    def process_all_groups(
            self, groups: Iterable[ModuleGroup]) -> Iterable[ModuleGroup]:
        new_groups = []
        for group in groups:
            new_groups.extend(self.process_one_group(group))
        return new_groups

    def process_one_group(self, group: ModuleGroup) -> Iterable[ModuleGroup]:
        raise NotImplementedError()


class Concat(Pass):
    def __init__(self, passes: Iterable[Pass]):
        self._passes = passes

    def process_all_groups(
            self, groups: Iterable[ModuleGroup]) -> Iterable[ModuleGroup]:
        for pazz in self._passes:
            groups = pazz.process_all_groups(groups)
        return groups


class If(Pass):
    def __init__(self, condition: Union[Callable[[ModuleGroup], bool], bool],
                 passes: Iterable[Pass]):
        if callable(condition):
            self._condition_func = condition
        else:
            self._condition_func = lambda _: condition
        self._pass = Concat(passes)

    def process_all_groups(
            self, groups: Iterable[ModuleGroup]) -> Iterable[ModuleGroup]:
        true_groups, false_groups = [], []
        for group in groups:
            (true_groups
             if self._condition_func(group) else false_groups).append(group)
        if true_groups:
            true_groups = self._pass.process_all_groups(true_groups)
        return true_groups + false_groups


class IfNot(If):
    def __init__(self, condition: Union[Callable[[ModuleGroup], bool], bool],
                 passes: Iterable[Pass]):
        if callable(condition):
            negated = lambda g: not condition(g)
        else:
            negated = not condition
        super().__init__(negated, passes)


class AddSuites(Pass):
    def __init__(self, suites):
        self._suites = suites

    def process_one_group(self, group: ModuleGroup) -> Iterable[ModuleGroup]:
        suites = frozenset(self._suites)
        assert all(s.startswith('suite:') for s in suites)

        if 'suites' not in group:
            group['suites'] = suites
        else:
            group['suites'] |= suites
        return [group]

    def __str__(self) -> str:
        return f'Add suites: {", ".join(self._suites)}'


class RemoveSuites(Pass):
    def __init__(self, suites):
        self._suites = suites

    def process_one_group(self, group: ModuleGroup) -> Iterable[ModuleGroup]:
        suites = frozenset(self._suites)
        assert all(s.startswith('suite:') for s in suites)

        if 'suites' in group:
            group['suites'] -= suites
        return [group]

    def __str__(self) -> str:
        return f'Remove suites: {", ".join(self._suites)}'


class ClearSuites(Pass):
    def process_one_group(self, group: ModuleGroup) -> Iterable[ModuleGroup]:
        group['suites'] = frozenset()
        return [group]

    def __str__(self) -> str:
        return f'Clear suites'


class AddSplitSuites(Pass):
    def __init__(self, config, suite_fmt, long_suite, abi):
        self._config = config
        self._suite_fmt = suite_fmt
        self._long_suite = long_suite
        self._abi = abi

    def process_all_groups(
            self, groups: Iterable[ModuleGroup]) -> Iterable[ModuleGroup]:
        groups = sorted(groups, key=lambda g: g['basename'])

        splitter = suite_split.Splitter(
                self._config['MAX_RUNTIME_SECS'],
                self._config['PER_TEST_OVERHEAD_SECS'],
                self._config['RUNTIME_HINT_SECS'],
        )

        for group in groups:
            shard = splitter.get_shard(group['basename'],
                                       group.get('abi_bits', None))
            if shard == suite_split.LONG_SUITE:
                group['suites'] |= frozenset([self._long_suite])
                continue
            split_suite = self._suite_fmt.format(abi=self._abi, shard=shard)
            group['suites'] |= frozenset([split_suite])

        total_shards, long_total_runtime = splitter.stats()
        logging.info('Suite to be splitted into %d shards', total_shards)
        logging.info('Long test total runtime: %.1fh',
                     long_total_runtime / 3600)
        return groups

    def __str__(self) -> str:
        return f'Add split suites abi={self._abi}'


class MergeSplitSuites(Pass):
    def __init__(self,
                 config,
                 suite_fmt,
                 long_suite,
                 abi,
                 basename_prefix='all'):
        self._config = config
        self._suite_fmt = suite_fmt
        self._long_suite = long_suite
        self._abi = abi
        self._basename_prefix = basename_prefix

    def process_all_groups(self, groups):
        groups = sorted(groups, key=lambda g: g['basename'])

        splitter = suite_split.Splitter(
                self._config['MAX_RUNTIME_SECS'],
                self._config['PER_TEST_OVERHEAD_SECS'],
                self._config['RUNTIME_HINT_SECS'],
        )
        shard_groups = collections.defaultdict(list)
        new_groups = []

        for group in groups:
            shard = splitter.get_shard(group['basename'],
                                       group.get('abi_bits'))
            if shard == suite_split.LONG_SUITE:
                group['suites'] = frozenset([self._long_suite])
                new_groups.append(group)
                continue
            shard_groups[shard].append(group)

        for shard, groups in shard_groups.items():
            split_suite = self._suite_fmt.format(abi=self._abi, shard=shard)
            merged_group = ModuleGroup(modules=set(),
                                       suite=frozenset([split_suite]))

            for group in groups:
                if 'abi_bits' in group:
                    # Have the group remain standalone to match old behavior.
                    group['suites'] = frozenset([split_suite])
                    new_groups.append(group)
                    continue
                merged_group['modules'] |= group['modules']

            basename = re.sub(
                    r'\[[^]]*\]', '',
                    min(merged_group['modules']) + '_-_' +
                    max(merged_group['modules']))
            merged_group['basename'] = basename
            merged_group['modules'] = frozenset(merged_group['modules'])
            merged_group['suites'] = frozenset([split_suite])
            new_groups.append(merged_group)

        for group in new_groups:
            group['basename'] = f'{self._basename_prefix}.{group["basename"]}'
            group['merged'] = True

        total_shards, long_total_runtime = splitter.stats()
        logging.info('Suite to be splitted into %d shards', total_shards)
        logging.info('Long test total runtime: %.1fh',
                     long_total_runtime / 3600)
        return new_groups

    def __str__(self):
        return f'Add split suites abi={self._abi}'


class SplitByAttr(Pass):
    def __init__(self, key: str, values: Iterable[Any]) -> None:
        self._key = key
        self._values = values

    def process_one_group(self, group: ModuleGroup) -> Iterable[ModuleGroup]:
        if self._key in group:
            raise ValueError(
                    f'group already split by {self._key}, check your config: {group}'
            )
        groups = []
        for val in self._values:
            splitted = copy.deepcopy(group)
            splitted[self._key] = val
            groups.append(splitted)
        return groups

    def __str__(self) -> str:
        return f'Split by {self._key}'


class SplitByBits(SplitByAttr):
    def __init__(self) -> None:
        super().__init__('abi_bits', (32, 64))


class SplitByTFShards(SplitByAttr):
    def __init__(self, shard_count: int, keep_unsharded: bool = False) -> None:
        shards = [(i, shard_count) for i in range(shard_count)]
        if keep_unsharded:
            shards += [(0, 1)]
        super().__init__('shard', shards)


class SetVMAttrs(Pass):
    def __init__(self, vm_modules_rules, vm_unstable_modules_rules):
        self._vm_modules_rules = vm_modules_rules
        self._vm_unstable_modules_rules = vm_unstable_modules_rules

    def process_one_group(self, group: ModuleGroup) -> Iterable[ModuleGroup]:
        vm_modules = []
        nonvm_modules = []
        has_unstable_vm_modules = False
        for m in group['modules']:
            if self._is_vm_module(m):
                vm_modules.append(m)
                if self._is_unstable_vm_module(m):
                    has_unstable_vm_modules = True
            else:
                nonvm_modules.append(m)

        if vm_modules:
            group['vm'] = True
            if nonvm_modules:
                logging.warn(
                        '%s is also added to vm suites because of %s, please check your config',
                        nonvm_modules, vm_modules)
            group['vm_stable'] = not has_unstable_vm_modules
        else:
            group['vm'] = group['vm_stable'] = False
        return [group]

    def _is_in_rule(self, module, rule):
        """Checks if module in given rule of VM rule syntax"""
        for pattern in rule:
            assert pattern[0] in '+-'
            if re.match(pattern[1:], module):
                return True if pattern[0] == '+' else False
        return False

    def _is_vm_module(self, module):
        return self._is_in_rule(module, self._vm_modules_rules)

    def _is_unstable_vm_module(self, module):
        return self._is_in_rule(module, self._vm_unstable_modules_rules)

    def __str__(self) -> str:
        return f'Set VM attributes'


class SetAttr(Pass):
    def __init__(self, key: str, value: Any):
        self._key = key
        self._value = value

    def process_one_group(self, group: ModuleGroup) -> Iterable[ModuleGroup]:
        group[self._key] = self._value
        return [group]
