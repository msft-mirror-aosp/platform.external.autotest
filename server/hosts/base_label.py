# Copyright 2016 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""This class defines the Base Label classes."""


import logging

import common
from autotest_lib.server.hosts import afe_store
from autotest_lib.server.hosts import host_info
from autotest_lib.server.hosts import shadowing_store


def forever_exists_decorate(exists):
    """
    Decorator for labels that should exist forever once applied.

    We'll check if the label already exists on the host and return True if so.
    Otherwise we'll check if the label should exist on the host.

    @param exists: The exists method on the label class.
    """
    def exists_wrapper(self, host):
        """
        Wrapper around the label exists method.

        @param self: The label object.
        @param host: The host object to run methods on.

        @returns True if the label already exists on the host, otherwise run
            the exists method.
        """
        info = host.host_info_store.get()
        return (self._NAME in info.labels) or exists(self, host)
    return exists_wrapper


class BaseLabel(object):
    """
    This class contains the scaffolding for the host-specific labels.

    @property _NAME String that is either the label returned or a prefix of a
                    generated label.
    """

    _NAME = None

    def generate_labels(self, host):
        """
        Return the list of labels generated for the host.

        @param host: The host object to check on.  Not needed here for base case
                     but could be needed for subclasses.

        @return a list of labels applicable to the host.
        """
        return [self._NAME]


    def exists(self, host):
        """
        Checks the host if the label is applicable or not.

        This method is geared for the type of labels that indicate if the host
        has a feature (bluetooth, touchscreen, etc) and as such require
        detection logic to determine if the label should be applicable to the
        host or not.

        @param host: The host object to check on.
        """
        raise NotImplementedError('exists not implemented')


    def get(self, host):
        """
        Return the list of labels.

        @param host: The host object to check on.
        """
        if self.exists(host):
            return self.generate_labels(host)
        else:
            return []


    def get_all_labels(self):
        """
        Return all possible labels generated by this label class.

        @returns a tuple of sets, the first set is for labels that are prefixes
            like 'os:android'.  The second set is for labels that are full
            labels by themselves like 'bluetooth'.
        """
        # Another subclass takes care of prefixed labels so this is empty.
        prefix_labels = set()
        full_labels_list = (self._NAME if isinstance(self._NAME, list) else
                            [self._NAME])
        full_labels = set(full_labels_list)

        return prefix_labels, full_labels


    def update_for_task(self, task_name):
        """
        This method helps to check which labels need to be updated.
        State config labels are updated only for repair task.
        Lab config labels are updated only for deploy task.
        All labels are updated for any task.

        It is the responsibility of the subclass to override this method
        to differentiate itself as a state config label or a lab config label
        and return the appropriate boolean value.

        If the subclass doesn't override this method then that label will
        always be updated for any type of task.

        @returns True if labels should be updated for the task with given name
        """
        return True


class StringLabel(BaseLabel):
    """
    This class represents a string label that is dynamically generated.

    This label class is used for the types of label that are always
    present and will return at least one label out of a list of possible labels
    (listed in _NAME).  It is required that the subclasses implement
    generate_labels() since the label class will need to figure out which labels
    to return.

    _NAME must always be overridden by the subclass with all the possible
    labels that this label detection class can return in order to allow for
    accurate label updating.
    """

    def generate_labels(self, host):
        raise NotImplementedError('generate_labels not implemented')


    def exists(self, host):
        """Set to true since it is assumed the label is always applicable."""
        return True


class StringPrefixLabel(StringLabel):
    """
    This class represents a string label that is dynamically generated.

    This label class is used for the types of label that usually are always
    present and indicate the os/board/etc type of the host.  The _NAME property
    will be prepended with a colon to the generated labels like so:

        _NAME = 'os'
        generate_label() returns ['android']

    The labels returned by this label class will be ['os:android'].
    It is important that the _NAME attribute be overridden by the
    subclass; otherwise, all labels returned will be prefixed with 'None:'.
    """

    def get(self, host):
        """Return the list of labels with _NAME prefixed with a colon.

        @param host: The host object to check on.
        """
        if self.exists(host):
            return ['%s:%s' % (self._NAME, label)
                    for label in self.generate_labels(host)]
        else:
            return []


    def get_all_labels(self):
        """
        Return all possible labels generated by this label class.

        @returns a tuple of sets, the first set is for labels that are prefixes
            like 'os:android'.  The second set is for labels that are full
            labels by themselves like 'bluetooth'.
        """
        # Since this is a prefix label class, we only care about
        # prefixed_labels.  We'll need to append the ':' to the label name to
        # make sure we only match on prefix labels.
        full_labels = set()
        prefix_labels = set(['%s:' % self._NAME])

        return prefix_labels, full_labels


class LabelRetriever(object):
    """This class will assist in retrieving/updating the host labels."""

    def _populate_known_labels(self, label_list, task_name):
        """Create a list of known labels that is created through this class."""
        for label_instance in label_list:
            # populate only the labels that need to be updated for this task.
            if label_instance.update_for_task(task_name):
                prefixed_labels, full_labels = label_instance.get_all_labels()
                self.label_prefix_names.update(prefixed_labels)
                self.label_full_names.update(full_labels)


    def __init__(self, label_list):
        self._labels = label_list
        # These two sets will contain the list of labels we can safely remove
        # during the update_labels call.
        self.label_full_names = set()
        self.label_prefix_names = set()


    def get_labels(self, host):
        """
        Retrieve the labels for the host.

        @param host: The host to get the labels for.
        """
        labels = []
        for label in self._labels:
            logging.info('checking label %s', label.__class__.__name__)
            try:
                labels.extend(label.get(host))
            except Exception:
                logging.exception('error getting label %s.',
                                  label.__class__.__name__)
        return labels


    def get_labels_for_update(self, host, task_name):
        """
        Retrieve the labels for the host which needs to be updated.

        @param host: The host to get the labels for updating.
        @param task_name: task name(repair/deploy) for the operation.

        @returns labels to be updated
        """
        labels = []
        for label in self._labels:
            logging.info('checking label update %s', label.__class__.__name__)
            try:
                # get only the labels which need to be updated for this task.
                if label.update_for_task(task_name):
                    labels.extend(label.get(host))
            except Exception:
                logging.exception('error getting label %s.',
                                  label.__class__.__name__)
        return labels


    def _is_known_label(self, label):
        """
        Checks if the label is a label known to the label detection framework.

        @param label: The label to check if we want to skip or not.

        @returns True to skip (which means to keep this label, False to remove.
        """
        return (label in self.label_full_names or
                any([label.startswith(p) for p in self.label_prefix_names]))


    def _carry_over_unknown_labels(self, old_labels, new_labels):
        """Update new_labels by adding back old unknown labels.

        We only delete labels that we might have created earlier.  There are
        some labels we should not be removing (e.g. pool:bvt) that we
        want to keep but won't be part of the new labels detected on the host.
        To do that we compare the passed in label to our list of known labels
        and if we get a match, we feel safe knowing we can remove the label.
        Otherwise we leave that label alone since it was generated elsewhere.

        @param old_labels: List of labels already on the host.
        @param new_labels: List of newly detected labels. This list will be
                updated to add back labels that are not tracked by the detection
                framework.
        """
        missing_labels = set(old_labels) - set(new_labels)
        for label in missing_labels:
            if not self._is_known_label(label):
                new_labels.append(label)


    def _commit_info(self, host, new_info, keep_pool):
        if keep_pool and isinstance(host.host_info_store,
                                    shadowing_store.ShadowingStore):
            primary_store = afe_store.AfeStoreKeepPool(host.hostname)
            host.host_info_store.commit_with_substitute(
                    new_info,
                    primary_store=primary_store,
                    shadow_store=None)
            return

        host.host_info_store.commit(new_info)


    def update_labels(self, host, task_name='', keep_pool=False):
        """
        Retrieve the labels from the host and update if needed.

        @param host: The host to update the labels for.
        """
        # If we haven't yet grabbed our list of known labels, do so now.
        if not self.label_full_names and not self.label_prefix_names:
            self._populate_known_labels(self._labels, task_name)

        # Label detection hits the DUT so it can be slow. Do it before reading
        # old labels from HostInfoStore to minimize the time between read and
        # commit of the HostInfo.
        new_labels = self.get_labels_for_update(host, task_name)
        old_info = host.host_info_store.get()
        self._carry_over_unknown_labels(old_info.labels, new_labels)
        new_info = host_info.HostInfo(
                labels=new_labels,
                attributes=old_info.attributes,
                stable_versions=old_info.stable_versions,
        )
        if old_info != new_info:
            self._commit_info(host, new_info, keep_pool)
