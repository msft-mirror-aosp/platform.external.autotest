# -*- coding: utf-8 -*-
# Copyright 2019 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Moblab pubsub client library."""

import base64
import logging  # pylint: disable=cros-logging-import

# pylint: disable=no-name-in-module, import-error
from google.cloud import pubsub_v1

_PUBSUB_TOPIC = "moblab-notification"

_LOGGER = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Current notification version.
CURRENT_MESSAGE_VERSION = "1"

# Test upload pubsub notification attributes
LEGACY_ATTR_VERSION = "version"
LEGACY_ATTR_GCS_URI = "gcs_uri"
LEGACY_ATTR_MOBLAB_MAC = "moblab_mac_address"
LEGACY_ATTR_MOBLAB_ID = "moblab_id"
# the message data for new test result notification.
LEGACY_TEST_OFFLOAD_MESSAGE = b"NEW_TEST_RESULT"


class PubSubException(Exception):
    """Exception to be raised when the test to push to prod failed."""

    pass


def callback(message_future):
    # When timeout is unspecified, the exception method waits indefinitely.
    if message_future.exception(timeout=30):
        raise PubSubException(
            "Publishing message on {} threw an Exception {}.".format(
                "Moblab notifications", message_future.exception()
            )
        )
    else:
        _LOGGER.info(message_future.result())


class PubSubClient(object):
    """A generic pubsub client."""

    def __init__(self, batch_settings=()):
        self.publisher = (
            pubsub_v1.PublisherClient()
            if len(batch_settings) == 0
            else pubsub_v1.PublisherClient(batch_settings)
        )

    def publish_notifications(self, topic, messages=None):
        """Publishes a test result notification to a given pubsub topic.

        Args:
            topic: The Cloud pubsub topic.
            messages: A list of notification messages.

        Returns:
            A list of pubsub message ids, and empty if fails.

        Raises:
            PubSubException if failed to publish the notification.
        """
        topic_path = self.publisher.topic_path(
            "chromeos-partner-moblab", topic
        )
        message_ids = []
        for message in messages:
            resp = self.publisher.publish(
                topic_path, message["data"], **message["attributes"]
            )
            resp.add_done_callback(callback)

            try:
                message_ids.append(resp.result())
            except Exception:
                _LOGGER.exception("Failed to publish notification: %s", resp)
        return message_ids


class PubSubBasedClient(object):
    """A Cloud PubSub based implementation of the CloudConsoleClient interface."""

    def __init__(self, batch_settings=()):
        """Constructor.

        Args:
            credential: The service account credential filename. Default to
            '/home/moblab/.service_account.json'.
            pubsub_topic: The cloud pubsub topic name to use.
        """
        self.pubsub_client = PubSubClient(batch_settings)

    def _create_message(self, data, msg_attributes):
        """Creates a cloud pubsub notification object.

        Args:
            data: The message data as a string.
            msg_attributes: The message attribute map.

        Returns:
            A pubsub message object with data and attributes.
        """
        message = {}
        if data:
            message["data"] = data
        if msg_attributes:
            message["attributes"] = msg_attributes
        return message

    def _create_test_job_offloaded_message(
        self, gcs_uri, serial_number, moblab_id
    ):
        """Construct a test result notification.

        TODO(ntang): switch LEGACY to new message format.
        Args:
            gcs_uri: The test result Google Cloud Storage URI.

        Returns:
            The notification message.
        """
        data = base64.b64encode(LEGACY_TEST_OFFLOAD_MESSAGE)
        msg_attributes = {}
        msg_attributes[LEGACY_ATTR_VERSION] = CURRENT_MESSAGE_VERSION
        msg_attributes[LEGACY_ATTR_MOBLAB_MAC] = serial_number
        msg_attributes[LEGACY_ATTR_MOBLAB_ID] = moblab_id
        msg_attributes[LEGACY_ATTR_GCS_URI] = gcs_uri

        return self._create_message(data, msg_attributes)

    def send_test_job_offloaded_message(
        self, gcs_uri, serial_number, moblab_id
    ):
        """Notify the cloud console a test job is offloaded.

        Args:
            gcs_uri: The test result Google Cloud Storage URI.

        Returns:
            True if the notification is successfully sent.
            Otherwise, False.
        """
        _LOGGER.info("Notification on gcs_uri %s", gcs_uri)
        message = self._create_test_job_offloaded_message(
            gcs_uri, serial_number, moblab_id
        )
        return self.pubsub_client.publish_notifications(
            _PUBSUB_TOPIC, [message]
        )

    def send_messages_with_attributes(
        self, pubsub_topic, msg_attributes_list, data
    ):
        """Publishes a list of pubsub messages containing the 'attributes' field
           to the cloud console.

        For each message, the 'data' field is the same but the 'attributes' field
        is individualized.

        Args:
            pubsub_topic: The cloud pubsub topic.
            msg_attributes_list: A list of pubsub message attribute maps.
            data: The message data as a string; can't be none or empty.

        Returns:
            A list of pubsub message ids, and empty if fails.

        Raises:
            KeyError if data is none or empty.
        """
        messages = [
            self._create_message(data, attr) for attr in msg_attributes_list
        ]
        return self.pubsub_client.publish_notifications(pubsub_topic, messages)
