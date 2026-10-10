"""Regression tests for the portal's log-request and recovery protocol."""

import threading
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import paho.mqtt.client as paho

from pymbrewclient.mqtt.client import MqttClient
from pymbrewclient.mqtt.proto import decode_raw_fields


class TestLogRequests(unittest.TestCase):
    def setUp(self) -> None:
        self.paho = MagicMock()
        self.paho.publish.return_value.rc = paho.MQTT_ERR_SUCCESS
        with patch("pymbrewclient.mqtt.client._paho.Client", return_value=self.paho):
            self.client = MqttClient(api_token="test-token", user_uuid="test-user")
        clock_patch = patch("time.monotonic", return_value=100.0)
        self.clock = clock_patch.start()
        self.addCleanup(clock_patch.stop)
        self.addCleanup(self.client.disconnect)

    def connect_callback(self) -> None:
        self.client._on_paho_connect(
            self.paho, None, SimpleNamespace(session_present=False), SimpleNamespace(is_failure=False), None
        )

    def receive(self, topic: str = "devices/logs/device-1", payload: bytes = b"") -> None:
        self.client._on_paho_message(self.paho, None, SimpleNamespace(topic=topic, payload=payload))

    def test_request_matches_captured_wire_payload(self) -> None:
        self.connect_callback()
        self.client.subscribe_device_logs("device-1", qos=1)
        (topic,) = self.paho.publish.call_args.args
        kwargs = self.paho.publish.call_args.kwargs
        self.assertEqual(topic, "apps/logrequests/device-1")
        self.assertEqual(kwargs["payload"], b"\x12\x24" + self.client._client_uuid.encode() + b"\x18\x01\x28\x00")
        self.assertEqual(len(kwargs["payload"]), 42)
        self.assertEqual(decode_raw_fields(kwargs["payload"]), {2: [self.client._client_uuid.encode()], 3: [1], 5: [0]})
        self.assertEqual(kwargs["qos"], 0)
        self.assertFalse(kwargs["retain"])
        self.assertIn("devices/logrequests/device-1", self.client._subscriptions)
        self.paho.subscribe.assert_any_call("devices/logs/device-1", qos=1)

    def test_deferred_subscription_requests_logs_on_connect_and_reconnect(self) -> None:
        self.client.subscribe_device_logs("device-1")
        self.paho.publish.assert_not_called()
        self.connect_callback()
        self.assertEqual(self.paho.publish.call_count, 1)
        self.client._on_paho_disconnect(self.paho, None, None, None, None)
        self.clock.return_value = 200.0
        self.client._retry_stale_device_logs()
        self.assertEqual(self.paho.publish.call_count, 1)
        self.connect_callback()
        self.assertEqual(self.paho.publish.call_count, 2)
        self.paho.subscribe.assert_any_call("devices/logrequests/device-1")

    def test_no_telemetry_retries_at_five_seconds_and_is_rate_limited(self) -> None:
        self.connect_callback()
        self.client.subscribe_device_logs("device-1")
        self.clock.return_value = 104.999
        self.client._retry_stale_device_logs()
        self.assertEqual(self.paho.publish.call_count, 1)
        self.clock.return_value = 105.0
        self.client._retry_stale_device_logs()
        self.client._retry_stale_device_logs()
        self.assertEqual(self.paho.publish.call_count, 2)
        self.clock.return_value = 110.0
        self.client._retry_stale_device_logs()
        self.assertEqual(self.paho.publish.call_count, 3)

    def test_duplicate_packets_refresh_receipt_deadline_before_callbacks(self) -> None:
        self.connect_callback()
        self.client.subscribe_device_logs("device-1")
        for second in range(101, 112):
            self.clock.return_value = float(second)
            self.receive()
            self.receive()
            self.client._retry_stale_device_logs()
        self.assertEqual(self.paho.publish.call_count, 1)
        self.clock.return_value = 116.0
        self.client._retry_stale_device_logs()
        self.assertEqual(self.paho.publish.call_count, 2)

    def test_receipt_tracking_precedes_application_callbacks(self) -> None:
        self.connect_callback()
        self.client.subscribe_device_logs("device-1")
        self.client.on_message(lambda message: self.client._retry_stale_device_logs())
        self.clock.return_value = 105.0
        self.receive()
        self.assertEqual(self.paho.publish.call_count, 1)

    def test_recovery_is_per_device_and_response_does_not_count_as_telemetry(self) -> None:
        self.connect_callback()
        self.client.subscribe_device_logs("device-1")
        self.client.subscribe_device_logs("device-2")
        self.clock.return_value = 104.0
        self.receive()
        self.receive("devices/logrequests/device-2")
        self.clock.return_value = 105.0
        self.client._retry_stale_device_logs()
        self.assertEqual(self.paho.publish.call_count, 3)
        self.assertEqual(self.paho.publish.call_args.args, ("apps/logrequests/device-2",))

    def test_duplicate_subscriptions_do_not_restart_request(self) -> None:
        self.connect_callback()
        self.client.subscribe_device_logs("device-1")
        self.client.subscribe_device_logs("device-1")
        self.assertEqual(self.paho.publish.call_count, 1)

    def test_unsubscribe_stops_only_this_requester_and_cancels_recovery(self) -> None:
        self.connect_callback()
        self.client.subscribe_device_logs("device-1")
        self.client.unsubscribe_device_logs("device-1")
        self.assertEqual(
            decode_raw_fields(self.paho.publish.call_args.kwargs["payload"]),
            {2: [self.client._client_uuid.encode()], 3: [0], 5: [0]},
        )
        self.assertNotIn("devices/logs/device-1", self.client._subscriptions)
        self.assertNotIn("devices/logrequests/device-1", self.client._subscriptions)
        self.clock.return_value = 200.0
        self.client._retry_stale_device_logs()
        self.assertEqual(self.paho.publish.call_count, 2)

    def test_generic_unsubscribe_also_cancels_managed_device(self) -> None:
        self.connect_callback()
        self.client.subscribe_device_logs("device-1")
        self.client.unsubscribe("devices/logs/device-1")
        self.clock.return_value = 200.0
        self.client._retry_stale_device_logs()
        self.assertEqual(self.paho.publish.call_count, 2)

    def test_generic_raw_subscription_does_not_start_log_requests(self) -> None:
        self.connect_callback()
        self.client.subscribe("devices/logs/device-1")
        self.clock.return_value = 200.0
        self.client._retry_stale_device_logs()
        self.paho.publish.assert_not_called()

    def test_publish_failure_is_reported_and_can_recover(self) -> None:
        errors = []
        self.client.on_error(errors.append)
        self.paho.publish.return_value.rc = paho.MQTT_ERR_NO_CONN
        self.connect_callback()
        with self.assertLogs("pymbrewclient.mqtt.client", level="WARNING"):
            self.client.subscribe_device_logs("device-1")
        self.assertEqual(len(errors), 1)
        self.assertIsInstance(errors[0], ConnectionError)
        self.assertNotIn("test-token", str(errors[0]))
        self.paho.publish.return_value.rc = paho.MQTT_ERR_SUCCESS
        self.clock.return_value = 105.0
        self.client._retry_stale_device_logs()
        self.assertEqual(self.paho.publish.call_count, 2)

    def test_disconnect_stops_requests_but_preserves_reconnect_intent(self) -> None:
        self.connect_callback()
        self.client.subscribe_device_logs("device-1")
        self.client.disconnect()
        self.assertEqual(decode_raw_fields(self.paho.publish.call_args.kwargs["payload"])[3], [0])
        self.clock.return_value = 200.0
        self.client._retry_stale_device_logs()
        self.assertEqual(self.paho.publish.call_count, 2)
        self.connect_callback()
        self.assertEqual(decode_raw_fields(self.paho.publish.call_args.kwargs["payload"])[3], [1])

    def test_watchdog_runs_and_stops_on_disconnect(self) -> None:
        published = threading.Event()
        self.client.subscribe_device_logs("device-1")
        self.connect_callback()
        self.paho.publish.side_effect = lambda *args, **kwargs: (
            published.set() or SimpleNamespace(rc=paho.MQTT_ERR_SUCCESS)
        )
        self.clock.return_value = 105.0
        with patch("pymbrewclient.mqtt.client._LOG_CHECK_INTERVAL", 0.01):
            self.client.connect()
            self.assertTrue(published.wait(timeout=1))
            thread = self.client._log_watchdog_thread
            self.client.disconnect()
            self.assertFalse(thread.is_alive())

    def test_disconnect_from_watchdog_error_callback_does_not_join_itself(self) -> None:
        stopped = threading.Event()
        self.client.subscribe_device_logs("device-1")
        self.connect_callback()
        self.paho.publish.return_value.rc = paho.MQTT_ERR_NO_CONN

        def disconnect_on_error(error: Exception) -> None:
            self.client.disconnect()
            stopped.set()

        self.client.on_error(disconnect_on_error)
        self.clock.return_value = 105.0
        with patch("pymbrewclient.mqtt.client._LOG_CHECK_INTERVAL", 0.01):
            self.client.connect()
            self.assertTrue(stopped.wait(timeout=1))
            self.assertFalse(self.client._connected)

    def test_invalid_device_topics_are_rejected_before_subscribing(self) -> None:
        for device_uuid in ("", "devices/logs/device-1", "+", "#"):
            with self.subTest(device_uuid=device_uuid), self.assertRaises(ValueError):
                self.client.subscribe_device_logs(device_uuid)
        self.paho.subscribe.assert_not_called()
        self.paho.publish.assert_not_called()

    def test_cancelled_watchdog_cannot_request_after_a_new_connection(self) -> None:
        self.connect_callback()
        self.client.subscribe_device_logs("device-1")
        cancelled = threading.Event()
        cancelled.set()
        self.clock.return_value = 105.0
        self.client._retry_stale_device_logs(cancelled)
        self.assertEqual(self.paho.publish.call_count, 1)

    def test_error_callback_can_disconnect_during_connection_setup(self) -> None:
        connected = MagicMock()
        self.client.subscribe_device_logs("device-1")
        self.client.on_connected(connected)
        self.client.on_error(lambda error: self.client.disconnect())
        self.paho.publish.return_value.rc = paho.MQTT_ERR_NO_CONN
        self.paho.loop_start.side_effect = self.connect_callback
        self.client.connect()
        connected.assert_not_called()
        self.assertIsNone(self.client._log_watchdog_thread)
        self.assertFalse(self.client._connected)
