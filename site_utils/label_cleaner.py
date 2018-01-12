#!/usr/bin/python
#
# Copyright (c) 2015 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.


"""Tool for cleaning up labels that are not in use.

Delete given labels from database when they are not in use.
Labels that match the query `SELECT_USED_LABELS_FORMAT` are considered in use.
When given labels are not in the used labels, those labels are deleted.

For example, following command deletes all labels whose name begins with
'cros-version' and are not in use.

./label_cleaner.py -p cros-version

If '-p' option is not given, we delete labels whose name is exactly
'cros-version' and are not in use.
"""


import argparse
import logging
import socket
import sys

import common
# Installed via build_externals, must be after import common.
import MySQLdb
from autotest_lib.client.common_lib import global_config
from autotest_lib.client.common_lib import logging_config
from autotest_lib.server import frontend
from chromite.lib import metrics
from chromite.lib import ts_mon_config


_METRICS_PREFIX = 'chromeos/autotest/afe_db/admin/label_cleaner'

GLOBAL_AFE = global_config.global_config.get_config_value(
        'SERVER', 'global_afe_hostname')
DB_SERVER = global_config.global_config.get_config_value('AUTOTEST_WEB', 'host')
USER = global_config.global_config.get_config_value('AUTOTEST_WEB', 'user')
PASSWD = global_config.global_config.get_config_value(
        'AUTOTEST_WEB', 'password')
DATABASE = global_config.global_config.get_config_value(
        'AUTOTEST_WEB', 'database')
RESPECT_STATIC_LABELS = global_config.global_config.get_config_value(
        'SKYLAB', 'respect_static_labels', type=bool, default=False)

SELECT_USED_LABELS_FORMAT = """
SELECT DISTINCT(label_id) FROM afe_autotests_dependency_labels UNION
SELECT DISTINCT(label_id) FROM afe_hosts_labels UNION
SELECT DISTINCT(label_id) FROM afe_jobs_dependency_labels UNION
SELECT DISTINCT(label_id) FROM afe_shards_labels UNION
SELECT DISTINCT(label_id) FROM afe_parameterized_jobs UNION
SELECT DISTINCT(meta_host) FROM afe_host_queue_entries
"""

SELECT_LABELS_FORMAT = """
SELECT id FROM afe_labels WHERE name %s
"""
SELECT_REPLACED_LABELS = """
SELECT label_id FROM afe_replaced_labels
"""

DELETE_LABELS_FORMAT = """
DELETE FROM afe_labels WHERE id in (%s)
"""


def get_used_labels(conn):
    """Get labels that are currently in use.

    @param conn: MySQLdb Connection object.

    @return: A list of label ids.
    """
    cursor = conn.cursor()
    sql = SELECT_USED_LABELS_FORMAT
    logging.debug('Running: %r', sql)
    cursor.execute(sql)
    rows = cursor.fetchall()
    return set(r[0] for r in rows)


def fetch_labels(conn, label, prefix):
    """Fetch labels from database.

    @param conn: MySQLdb Connection object.
    @param label: Label name to fetch.
    @param prefix: If True, use `label` as a prefix. Otherwise, fetch
                   labels whose name is exactly same as `label`.

    @return: A list of label ids.
    """
    cursor = conn.cursor()
    if prefix:
        sql = SELECT_LABELS_FORMAT % ('LIKE "%s%%"' % label)
    else:
        sql = SELECT_LABELS_FORMAT % ('= "%s"' % label)
    logging.debug('Running: %r', sql)
    cursor.execute(sql)
    rows = cursor.fetchall()
    # Don't delete labels whose replaced_by_static_label=True, since they're
    # actually maintained by afe_static_labels, not afe_labels.
    if not RESPECT_STATIC_LABELS:
        return set(r[0] for r in rows)
    else:
        cursor.execute(SELECT_REPLACED_LABELS)
        replaced_labels = cursor.fetchall()
        replaced_label_ids = set([r[0] for r in replaced_labels])
        return set(r[0] for r in rows) - replaced_label_ids


def _delete_labels(conn, labels):
    """Helper function of `delete_labels`."""
    labels_str = ','.join([str(l) for l in labels])
    sql = DELETE_LABELS_FORMAT % labels_str
    logging.debug('Running: %r', sql)
    conn.cursor().execute(sql)
    conn.commit()


def delete_labels(conn, labels, max_delete):
    """Delete given labels from database.

    @param conn: MySQLdb Connection object.
    @param labels: iterable of labels to delete.
    @param max_delete: Max number of records to delete in a query.
    """
    while labels:
        chunk = labels[:max_delete]
        labels = labels[max_delete:]
        _delete_labels(conn, chunk)


def is_primary_server():
    """Check if this server's status is primary

    @return: True if primary, False otherwise.
    """
    server = frontend.AFE(server=GLOBAL_AFE).run(
            'get_servers', hostname=socket.getfqdn())
    if server and server[0]['status'] == 'primary':
        return True
    return False


def clean_labels(options):
    """Cleans unused labels from AFE database"""
    msg = 'Label cleaner starts. Will delete '
    if options.prefix:
        msg += 'all labels whose prefix is "%s".'
    else:
        msg += 'a label "%s".'
    logging.info(msg, options.label)
    logging.info('Target database: %s.', options.db_server)
    if options.check_status and not is_primary_server():
        raise Exception('Cannot run in a non-primary server')

    conn = MySQLdb.connect(host=options.db_server, user=USER, passwd=PASSWD,
                           db=DATABASE)

    labels = fetch_labels(conn, options.label, options.prefix)
    logging.info('Found total %d labels', len(labels))
    metrics.Gauge(_METRICS_PREFIX + '/total_labels_count').set(
            len(labels), fields={'target_db': options.db_server})

    used_labels = get_used_labels(conn)
    logging.info('Found %d labels are used', len(used_labels))
    metrics.Gauge(_METRICS_PREFIX + '/used_labels_count').set(
            len(used_labels), fields={'target_db': options.db_server})

    to_delete = list(labels - used_labels)
    logging.info('Deleting %d unused labels', len(to_delete))
    delete_labels(conn, to_delete, options.max_delete)
    metrics.Counter(_METRICS_PREFIX + '/labels_deleted').increment_by(
            len(to_delete), fields={'target_db': options.db_server})


def main():
    """Cleans unused labels from AFE database"""
    parser = argparse.ArgumentParser(
            formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--db', dest='db_server',
                        help='Database server', default=DB_SERVER)
    parser.add_argument('-p', dest='prefix', action='store_true',
            help=('Use argument <label> as a prefix for matching. '
                  'For example, when the argument <label> is "cros-version" '
                  'and this option is enabled, then labels whose name '
                  'beginning with "cros-version" are matched. When this '
                  'option is disabled, we match labels whose name is '
                  'exactly same as the argument <label>.'))
    parser.add_argument('-n', dest='max_delete', type=int,
           help=('Max number of records to delete in each query.'),
           default=100)
    parser.add_argument('-s', dest='check_status', action='store_true',
           help=('Enforce to run only in a server that has primary status'))
    parser.add_argument('label', help='Label name to delete')
    options = parser.parse_args()

    logging_config.LoggingConfig().configure_logging(
            datefmt='%Y-%m-%d %H:%M:%S',
            verbose=True)

    with ts_mon_config.SetupTsMonGlobalState('afe_label_cleaner',
                                             auto_flush=False):
        try:
            clean_labels(options)
        except:
            metrics.Counter(_METRICS_PREFIX + '/tick').increment(
                    fields={'target_db': options.db_server,
                            'success': False})
            raise
        else:
            metrics.Counter(_METRICS_PREFIX + '/tick').increment(
                    fields={'target_db': options.db_server,
                            'success': True})
        finally:
            metrics.Flush()


if __name__ == '__main__':
    sys.exit(main())
