# Lint as: python2, python3
# Copyright 2020 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from autotest_lib.client.common_lib import error
from autotest_lib.utils.frozen_chromite.lib import retry_util


_VPD_BASE_CMD = 'vpd -i %s %s %s'
_RW = 'RW_VPD'
_RO = 'RO_VPD'


def _check_partition(partition):
    """
    Used to validate input string in other functions.

    @param partition: If this is not 'RO_VPD' or 'RW_VPD', raise a ValueError.

    """
    if partition not in [_RW, _RO]:
        raise ValueError("partition should be 'RW_VPD' or 'RO_VPD'")


def vpd_get(host, key, partition='RW_VPD', retries=3):
    """
    Gets the VPD value associated with the input key.

    @param host: Host to run the command on.
    @param key: Key of the desired VPD value.
    @param partition: Which partition to access. 'RO_VPD' or 'RW_VPD'.
    @param retries: Number of times to try rerunning the command in case of
                    error.

    """
    _check_partition(partition)
    get_cmd = _VPD_BASE_CMD % (partition, '-g', key)
    try:
        return retry_util.RetryException(error.AutoservRunError, retries,
                                         host.run, get_cmd).stdout
    except error.AutoservRunError as e:
        if 'was not found' in str(e.result_obj.stderr):
            return None
        else:
            raise e


def vpd_set(host, vpd_dict, partition='RW_VPD', dump=False, force_dump=False,
            retries=3):
    """
    Sets the given key/value pairs in the specified VPD partition.

    @param host: Host to run the command on.
    @param vpd_dict: Dictionary containing the VPD key/value pairs to set.
                     Dictionary keys should be the VPD key strings, and values
                     should be the desired values to write.
    @param partition: Which partition to access. 'RO_VPD' or 'RW_VPD'.
    @param retries: Number of times to try rerunning the command in case of
                    error.

    """
    _check_partition(partition)
    for vpd_key in vpd_dict:
        set_cmd = _VPD_BASE_CMD % (partition, '-s',
                  (vpd_key + '=' + str(vpd_dict[vpd_key])))
        retry_util.RetryException(error.AutoservRunError, retries,
                                  host.run, set_cmd).stdout


def vpd_delete(host, key, partition='RW_VPD', retries=3):
    """
    Deletes the specified key from the specified VPD partition.

    @param host: Host to run the command on.
    @param key: The VPD value to delete.
    @param partition: Which partition to access. 'RO_VPD' or 'RW_VPD'.
    @param retries: Number of times to try rerunning the command in case of
                    error.

    """
    _check_partition(partition)
    if not vpd_get(host, key, partition=partition, retries=retries):
        return

    del_cmd = _VPD_BASE_CMD % (partition, '-d', key)
    retry_util.RetryException(error.AutoservRunError, retries, host.run,
                              del_cmd).stdout
