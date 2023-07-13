# Copyright 2023 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Transformation functions for module groups.

A "pass" is a general construct that takes a list of module groups and
transforms it into another list of module groups. In the generator logic, we
first create an initial list of groups, then we prepare a list of "passes"
through which the list is being sent, one pass at a time:

    groups = initial_list_of_groups()
    for pazz in passes:
        groups = pazz.process_all_groups(groups)
    return groups

Such construct allows performing step-by-step transformations, increasing
maintainability and flexibility.
"""

import collections
import copy
import logging
import re
from typing import Any, Dict, Callable, Iterable, Optional, Union

from generate_controlfiles_new.common import ModuleGroup

from . import suite_split
from .common import ModuleGroup


class Pass:
    """Base class for all passes."""
    def process_all_groups(
            self, groups: Iterable[ModuleGroup]) -> Iterable[ModuleGroup]:
        """Processes all module groups at once.

        The default implementation calls process_one_group for each group in the
        list, then concatenates the results. Subclasses should override this
        method if the transformation cannot be separately performed for each
        group (for example when merging multiple groups into one).

        Args:
            groups: the list of module groups.

        Returns:
            The transformed list of module groups.
        """
        new_groups = []
        for group in groups:
            new_groups.extend(self.process_one_group(group))
        return new_groups

    def process_one_group(self, group: ModuleGroup) -> Iterable[ModuleGroup]:
        """Processes one module group.

        Subclasses should override this method if the transformation is to be
        separately performed for each group (for example when assigning a fixed
        attribute to each group).

        Note that the return value is a *list* of groups, which allows
        generating (splitting) multiple groups from this one group. If no new
        groups are generated, simply return [group].

        Args:
            group: a module group.

        Returns:
            The transformed list of groups.
        """
        raise NotImplementedError()


class Concat(Pass):
    """Concatenate several passes into one."""
    def __init__(self, passes: Iterable[Pass]):
        """Constructs a Concat pass.

        Args:
            passes: the list of passes to concat.
        """
        self._passes = passes

    def process_all_groups(
            self, groups: Iterable[ModuleGroup]) -> Iterable[ModuleGroup]:
        for pazz in self._passes:
            groups = pazz.process_all_groups(groups)
        return groups


class If(Pass):
    """Apply passes conditionally."""
    def __init__(self, condition: Union[Callable[[ModuleGroup], bool], bool],
                 passes: Iterable[Pass]):
        """Constructs a If pass.

        The condition can be either a fixed value, or a callable that accepts
        a module group as input. Passes are applied only to groups where the
        condition evaluates to True.

        Args:
            condition: the condition to evaluate.
            passes: the list of passes to apply.
        """
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
    """Like If but with the condition negated."""
    def __init__(self, condition: Union[Callable[[ModuleGroup], bool], bool],
                 passes: Iterable[Pass]):
        if callable(condition):
            negated = lambda g: not condition(g)
        else:
            negated = not condition
        super().__init__(negated, passes)


class AddSuites(Pass):
    """Assign suites to groups."""
    def __init__(self, suites: Optional[Iterable[str]]):
        """Constructs an AddSuites pass.

        Args:
            suites: list of suites to assign. It's declared optional to support
                lazy evaluation when used with If.
        """
        self._suites = suites

    def process_one_group(self, group: ModuleGroup) -> Iterable[ModuleGroup]:
        # Evaluate late since suites may be invalid when used within If.
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
    """Remove certain suites from groups."""
    def __init__(self, suites: Optional[Iterable[str]]):
        """Constructs an RemoveSuites pass.

        Args:
            suites: list of suites to remove. It's declared optional to support
                lazy evaluation when used with If.
        """
        self._suites = suites

    def process_one_group(self, group: ModuleGroup) -> Iterable[ModuleGroup]:
        # Evaluate late since suites may be invalid when used within If.
        suites = frozenset(self._suites)
        assert all(s.startswith('suite:') for s in suites)

        if 'suites' in group:
            group['suites'] -= suites
        return [group]

    def __str__(self) -> str:
        return f'Remove suites: {", ".join(self._suites)}'


class ClearSuites(Pass):
    """Remove all suites from groups."""
    def process_one_group(self, group: ModuleGroup) -> Iterable[ModuleGroup]:
        group['suites'] = frozenset()
        return [group]

    def __str__(self) -> str:
        return f'Clear suites'


class AddSplitSuites(Pass):
    """Assign "suite split" suites to groups.

    TODO(b/287160788): Explain.
    """
    def __init__(self, config: Dict[str, Any], suite_fmt: str, long_suite: str,
                 abi: str):
        """Constructs a AddSplitSuites pass.

        Args:
            config: the suite split config.
            suite_fmt: format string of splitted suite names. It may contain
                fields `abi` and `shard`.
            long_suite: the suite to assign to "long" tests.
            abi: the bundle abi.
        """
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
    """Combine module groups according to "suite split" suites.

    TODO(b/287160788): Explain.
    """
    def __init__(self,
                 config: Dict[str, Any],
                 suite_fmt: str,
                 long_suite: str,
                 abi: str,
                 basename_prefix: str = 'all'):
        """Constructs a MergeSplitSuites pass.

        Args:
            config: the suite split config.
            suite_fmt: format string of splitted suite names. It may contain
                fields `abi` and `shard`.
            long_suite: the suite to assign to "long" tests.
            abi: the bundle abi.
            basename_prefix: the prefix to prepend to the groups' basename.
        """
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
    """Split each group into multiple groups with varying attribute.

    For each group, the group is cloned into `len(values)` groups, each
    corresponding to one value from the `values` list. Their `key` attributes
    are then assigned with the corresponding values.
    """
    def __init__(self, key: str, values: Iterable[Any]) -> None:
        """Constructs a SplitByAttr pass.

        Args:
            key: the attribute key to split.
            values: list of values to apply.
        """
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
    """Split group into 32-bit and 64-bit versions."""
    def __init__(self) -> None:
        super().__init__('abi_bits', (32, 64))


class SplitByTFShards(SplitByAttr):
    """Split group into multiple TF shards."""
    def __init__(self, shard_count: int, keep_unsharded: bool = False) -> None:
        """Constructs a SplitByTFShards pass.

        Args:
            shard_count: the total shard count.
            keep_unsharded: whether to retain the original unsharded group in
                addition to sharded versions.
        """
        shards = [(i, shard_count) for i in range(shard_count)]
        if keep_unsharded:
            shards += [(0, 1)]
        super().__init__('shard', shards)


class SetVMAttrs(Pass):
    """Set VM attributes.

    For each group, assigns the following attributes according to given rules:
      - 'vm' indicating if the group is VM-eligible
      - 'vm_stable' indicating if the group is VM-stable (i.e. HW-agnostic)

    Rules are defined as a list of strings of the following syntax:
      - First character is either '+' (include) or '-' (exclude).
      - Remaining is a regex that matches the CTS module name.
    Rules are evaluated in list order, and the first match is returned.
    """
    def __init__(self, vm_modules_rules: Iterable[str],
                 vm_unstable_modules_rules: Iterable[str]):
        """Constructs a SetVMAttrs pass.

        Args:
            vm_modules_rules: list of rules defining which modules are
                VM-eligible
            vm_unstable_modules_rules: list of rules defining which modules are
                not VM-stable
        """
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

    def _is_in_rule(self, module: str, rule: Iterable[str]):
        """Checks if module in given rule of VM rule syntax"""
        for pattern in rule:
            assert pattern[0] in '+-'
            if re.match(pattern[1:], module):
                return True if pattern[0] == '+' else False
        return False

    def _is_vm_module(self, module: str):
        return self._is_in_rule(module, self._vm_modules_rules)

    def _is_unstable_vm_module(self, module: str):
        return self._is_in_rule(module, self._vm_unstable_modules_rules)

    def __str__(self) -> str:
        return f'Set VM attributes'


class SetAttr(Pass):
    """Set an attribute `key` to a fixed `value`."""
    def __init__(self, key: str, value: Any):
        """Constructs a SetAttr pass.

        Args:
            key: the attribute key.
            value: the value.
        """
        self._key = key
        self._value = value

    def process_one_group(self, group: ModuleGroup) -> Iterable[ModuleGroup]:
        group[self._key] = self._value
        return [group]
