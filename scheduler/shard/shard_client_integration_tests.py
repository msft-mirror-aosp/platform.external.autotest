#!/usr/bin/python2
#pylint: disable-msg=C0111

# Copyright (c) 2014 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import unittest

import common
from autotest_lib.client.common_lib import global_config
from autotest_lib.frontend import setup_django_environment
from autotest_lib.frontend.afe import frontend_test_utils
from autotest_lib.frontend.afe import models
from autotest_lib.scheduler import rdb_testing_utils
from autotest_lib.scheduler import scheduler_models
from autotest_lib.scheduler.shard import shard_client


class ShardClientIntegrationTest(rdb_testing_utils.AbstractBaseRDBTester,
                                 unittest.TestCase):
    """Integration tests for the shard_client."""


    def setup_global_config(self):
        """Mock out global_config for shard client creation."""
        global_config.global_config.override_config_value(
                'SHARD', 'is_slave_shard', 'True')
        global_config.global_config.override_config_value(
                'SHARD', 'shard_hostname', 'host1')


    def initialize_shard_client(self):
        self.setup_global_config()
        return shard_client.get_shard_client()


    def testIncompleteJobThrottling(self):
        client = self.initialize_shard_client()
        job = self.create_job(deps=set(['a']), shard_hostname=client.hostname)
        scheduler_models.initialize()
        hqe = scheduler_models.HostQueueEntry.fetch(
                where='job_id = %s' % job.id)[0]

        global_config.global_config.override_config_value(
                'SHARD', 'throttle_incomplete_jobs_upload', 'False')
        job_ids = client._get_incomplete_job_ids(0)
        assert(job_ids == [job.id])

        global_config.global_config.override_config_value(
                'SHARD', 'throttle_incomplete_jobs_upload', 'True')
        job_ids = client._get_incomplete_job_ids(0)
        assert(job_ids == [])
        job_ids = client._get_incomplete_job_ids(1)
        assert(job_ids == [job.id])


    def testCompleteStatusBasic(self):
        """Test that complete jobs are uploaded properly."""

        client = self.initialize_shard_client()
        job = self.create_job(deps=set(['a']), shard_hostname=client.hostname)
        scheduler_models.initialize()
        hqe = scheduler_models.HostQueueEntry.fetch(
                where='job_id = %s' % job.id)[0]

        # This should set both the shard_id and the complete bit.
        hqe.set_status('Completed')

        # Only incomplete jobs should be in known ids.
        job_ids = client._get_incomplete_job_ids(10)
        assert(job_ids == [])

        # Jobs that have successfully gone through a set_status should
        # be ready for upload.
        jobs = client._get_jobs_to_upload(10)
        assert(job.id in [j.id for j in jobs])


    def testOnlyShardId(self):
        """Test that setting only the shardid prevents the job from upload."""

        client = self.initialize_shard_client()
        job = self.create_job(deps=set(['a']), shard_hostname=client.hostname)
        scheduler_models.initialize()
        hqe = scheduler_models.HostQueueEntry.fetch(
                where='job_id = %s' % job.id)[0]

        def _local_update_field(hqe, field_name, value):
            """Turns update_field on the complete field into a no-op."""
            if field_name == 'complete':
                return
            models.HostQueueEntry.objects.filter(id=hqe.id).update(
                    **{field_name: value})
            setattr(hqe, field_name, value)

        self.god.stub_with(scheduler_models.HostQueueEntry, 'update_field',
                _local_update_field)

        # This should only update the shard_id.
        hqe.set_status('Completed')

        # Retrieve the hqe along an independent code path so we're assured of
        # freshness, then make sure it has shard=None and an unset complete bit.
        modified_hqe = self.db_helper.get_hqes(job_id=job.id)[0]
        assert(modified_hqe.id == hqe.id and
               modified_hqe.complete == 0 and
               modified_hqe.job.shard == None)

        # Make sure the job with a shard but without complete is still
        # in known_ids.
        job_ids = client._get_incomplete_job_ids(10)
        assert(set(job_ids) == set([job.id]))

        # Make sure the job with a shard but without complete is not
        # in uploaded jobs.
        jobs = client._get_jobs_to_upload(10)
        assert(jobs == [])


    def testHostSerialization(self):
        """Test simple host serialization."""
        client = self.initialize_shard_client()
        host = self.db_helper.create_host(name='test_host')
        serialized_host = host.serialize()
        models.Host.objects.all().delete()
        models.Host.deserialize(serialized_host)
        models.Host.objects.get(hostname='test_host')


    def testUserExists(self):
        """Test user related race conditions."""
        client = self.initialize_shard_client()
        user = self.db_helper.create_user(name='test_user')
        serialized_user = user.serialize()

        # Master sends a user with the same login but different id
        serialized_user['id'] = '3'
        models.User.deserialize(serialized_user)
        models.User.objects.get(id=3, login='test_user')

        # Master sends a user with the same id, different login
        serialized_user['login'] = 'fake_user'
        models.User.deserialize(serialized_user)
        models.User.objects.get(id=3, login='fake_user')

        # Master sends a new user
        user = self.db_helper.create_user(name='new_user')
        serialized_user = user.serialize()
        models.User.objects.all().delete()
        models.User.deserialize(serialized_user)
        models.User.objects.get(login='new_user')


    def testProcessHeartbeatResponseIgnoresKnownJobs(self):
        known_job = self.create_job(deps={'a'})
        known_serialized_job = known_job.serialize()
        self._set_job_deps(known_serialized_job, {'b'})

        client = self.initialize_shard_client()
        client.process_heartbeat_response(
            _response_with_job(known_serialized_job))
        self.assert_job_in_shard_database(known_job.id, deps={'a'})


    def _set_job_deps(self, serialized_job, deps):
        temp = self.create_job(deps=deps)
        serialized_temp = temp.serialize()
        serialized_job['dependency_labels'] = (
            serialized_temp['dependency_labels']
        )


    def assert_job_in_shard_database(self, job_id, deps):
        jobs = models.Job.objects.filter(id=job_id)
        self.assertEqual(1, len(jobs))
        job = jobs[0]
        got = set([l.name for l in job.dependency_labels.all()])
        self.assertEqual(got, deps)



def _response_with_job(job):
    return {
        'hosts': [],
        'jobs': [job],
        'suite_keyvals': [],
    }


if __name__ == '__main__':
    unittest.main()

