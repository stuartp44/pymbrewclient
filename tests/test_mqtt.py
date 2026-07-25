from datetime import datetime, timezone
from pathlib import Path
import unittest
from unittest.mock import MagicMock, patch

from pymbrewclient.client import BreweryClient
from pymbrewclient.mqtt.client import MiniBrewMqttClient
from pymbrewclient.mqtt.protobuf import decode_device_log_payload
from pymbrewclient.rest.client import RestApiClient
from pymbrewclient.rest.models import UserProfile


class FakeMqttClient:
    def __init__(self, **kwargs: object) -> None:
        self.kwargs = kwargs
        self.ws_path: str | None = None
        self.reconnect_delay: tuple[int, int] | None = None
        self.tls_set_called = False
        self.tls_insecure: bool | None = None
        self.username: str | None = None
        self.password: str | None = None
        self.will: tuple[str, bytes, int, bool] | None = None
        self.connected_to: tuple[str, int, int] | None = None
        self.loop_started = False
        self.loop_stopped = False
        self.disconnected = False
        self.subscribe_calls: list[tuple[str, int]] = []
        self.unsubscribe_calls: list[str] = []
        self.on_connect = None
        self.on_disconnect = None
        self.on_message = None

    def ws_set_options(self, path: str) -> None:
        self.ws_path = path

    def reconnect_delay_set(self, min_delay: int, max_delay: int) -> None:
        self.reconnect_delay = (min_delay, max_delay)

    def tls_set(self) -> None:
        self.tls_set_called = True

    def tls_insecure_set(self, value: bool) -> None:
        self.tls_insecure = value

    def username_pw_set(self, username: str, password: str) -> None:
        self.username = username
        self.password = password

    def will_set(self, topic: str, payload: bytes, qos: int, retain: bool) -> None:
        self.will = (topic, payload, qos, retain)

    def connect(self, host: str, port: int, keepalive: int) -> int:
        self.connected_to = (host, port, keepalive)
        return 0

    def loop_start(self) -> None:
        self.loop_started = True

    def disconnect(self) -> int:
        self.disconnected = True
        return 0

    def loop_stop(self) -> None:
        self.loop_stopped = True

    def subscribe(self, topic: str, qos: int = 0) -> tuple[int, int]:
        self.subscribe_calls.append((topic, qos))
        return (0, len(self.subscribe_calls))

    def unsubscribe(self, topic: str) -> tuple[int, int]:
        self.unsubscribe_calls.append(topic)
        return (0, len(self.unsubscribe_calls))


class TestMiniBrewMqttClient(unittest.TestCase):
    def setUp(self) -> None:
        self.rest_client = RestApiClient("user@example.com", "test-pass", "https://api.example.com")
        self.rest_client._ensure_token = MagicMock()
        self.rest_client.token = "api-token-123"
        self.rest_client.get_user_profile = MagicMock(return_value=UserProfile(uuid="user-uuid-123"))

    @patch("pymbrewclient.mqtt.client.uuid.uuid4", return_value="client-uuid-456")
    def test_client_credentials_and_configuration(self, _: MagicMock) -> None:
        mqtt = MiniBrewMqttClient(rest_client=self.rest_client, mqtt_client_factory=FakeMqttClient)
        fake = mqtt._mqtt_client

        self.assertEqual(mqtt.client_id, "breweryportal-client-uuid-456")
        self.assertEqual(fake.kwargs["client_id"], "breweryportal-client-uuid-456")
        self.assertTrue(fake.kwargs["clean_session"])
        self.assertEqual(fake.kwargs["transport"], "websockets")
        self.assertEqual(fake.ws_path, "/ws")
        self.assertEqual(fake.reconnect_delay, (5, 5))
        self.assertTrue(fake.tls_set_called)
        self.assertFalse(fake.tls_insecure)
        self.assertEqual(fake.username, "breweryportal-user-uuid-123")
        self.assertEqual(fake.password, "api-token-123")
        self.assertEqual(fake.will, ("apps/lastwill/breweryportal-client-uuid-456", b"offline", 0, False))

    def test_connect_and_disconnect_cleanup(self) -> None:
        mqtt = MiniBrewMqttClient(rest_client=self.rest_client, mqtt_client_factory=FakeMqttClient)
        fake = mqtt._mqtt_client

        mqtt.connect()
        self.assertEqual(fake.connected_to, ("broker.minibrew.io", 15675, 60))
        self.assertTrue(fake.loop_started)

        mqtt.disconnect()
        self.assertTrue(fake.disconnected)
        self.assertTrue(fake.loop_stopped)

    def test_context_manager_connects_and_disconnects(self) -> None:
        mqtt = MiniBrewMqttClient(rest_client=self.rest_client, mqtt_client_factory=FakeMqttClient)
        fake = mqtt._mqtt_client

        with mqtt:
            self.assertTrue(fake.loop_started)
        self.assertTrue(fake.loop_stopped)

    def test_device_topic_helpers_and_subscribe_unsubscribe(self) -> None:
        mqtt = MiniBrewMqttClient(rest_client=self.rest_client, mqtt_client_factory=FakeMqttClient)
        fake = mqtt._mqtt_client
        topic = mqtt.get_device_logs_topic("2403K0561-61BMUWBU")

        self.assertEqual(topic, "devices/logs/2403K0561-61BMUWBU")
        mqtt.subscribe_device_logs("2403K0561-61BMUWBU")
        mqtt.unsubscribe(topic)
        self.assertEqual(fake.subscribe_calls, [(topic, 0)])
        self.assertEqual(fake.unsubscribe_calls, [topic])

    def test_resubscribe_on_reconnect(self) -> None:
        mqtt = MiniBrewMqttClient(rest_client=self.rest_client, mqtt_client_factory=FakeMqttClient)
        fake = mqtt._mqtt_client
        topic = "devices/logs/2403K0561-61BMUWBU"
        mqtt.subscribe(topic, qos=1)
        self.assertEqual(fake.subscribe_calls, [(topic, 1)])

        fake.on_connect(fake, None, {}, 0)
        self.assertEqual(fake.subscribe_calls.count((topic, 1)), 1)
        fake.on_connect(fake, None, {}, 0)

        self.assertEqual(fake.subscribe_calls.count((topic, 1)), 2)

    def test_unsubscribed_topic_is_not_resubscribed(self) -> None:
        mqtt = MiniBrewMqttClient(rest_client=self.rest_client, mqtt_client_factory=FakeMqttClient)
        fake = mqtt._mqtt_client
        kept_topic = "devices/logs/2403K0561-61BMUWBU"
        removed_topic = "devices/logs/2403K0561-OTHERDEVICE"
        mqtt.subscribe(kept_topic)
        mqtt.subscribe(removed_topic)
        mqtt.unsubscribe(removed_topic)
        self.assertEqual(fake.subscribe_calls, [(kept_topic, 0), (removed_topic, 0)])

        fake.on_connect(fake, None, {}, 0)
        self.assertEqual(fake.subscribe_calls.count((kept_topic, 0)), 1)
        fake.on_connect(fake, None, {}, 0)
        self.assertEqual(len(fake.subscribe_calls), 3)

        self.assertEqual(fake.subscribe_calls.count((kept_topic, 0)), 2)
        self.assertEqual(fake.subscribe_calls.count((removed_topic, 0)), 1)

    def test_callbacks_receive_connection_and_message_events(self) -> None:
        mqtt = MiniBrewMqttClient(rest_client=self.rest_client, mqtt_client_factory=FakeMqttClient)
        fake = mqtt._mqtt_client
        events: list[str] = []
        messages: list[object] = []

        mqtt.set_on_connected(lambda: events.append("connected"))
        mqtt.set_on_disconnected(lambda rc: events.append(f"disconnected:{rc}"))
        mqtt.set_on_reconnecting(lambda rc: events.append(f"reconnecting:{rc}"))
        mqtt.set_on_message(lambda message: messages.append(message))

        fake.on_connect(fake, None, {}, 0)
        message = MagicMock()
        message.topic = "devices/logs/2403K0561-61BMUWBU"
        message.payload = b"\x08\x01"
        fake.on_message(fake, None, message)
        fake.on_disconnect(fake, None, 1)

        self.assertIn("connected", events)
        self.assertIn("reconnecting:1", events)
        self.assertIn("disconnected:1", events)
        self.assertEqual(len(messages), 1)

    def test_truncated_payload_reports_error_without_crashing(self) -> None:
        mqtt = MiniBrewMqttClient(rest_client=self.rest_client, mqtt_client_factory=FakeMqttClient)
        fake = mqtt._mqtt_client
        errors: list[str] = []
        messages: list[object] = []
        mqtt.set_on_error(lambda error_message: errors.append(error_message))
        mqtt.set_on_message(lambda message: messages.append(message))

        message = MagicMock()
        message.topic = "devices/logs/2403K0561-61BMUWBU"
        message.payload = b"\x08"
        fake.on_message(fake, None, message)

        self.assertEqual(errors, ["MQTT message decode failed."])
        self.assertEqual(len(messages), 1)
        self.assertIsNotNone(messages[0].decoding_error)

    def test_error_paths_do_not_expose_token(self) -> None:
        self.rest_client.token = None

        with self.assertRaises(RuntimeError) as context:
            MiniBrewMqttClient(rest_client=self.rest_client, mqtt_client_factory=FakeMqttClient)
        self.assertNotIn("api-token-123", str(context.exception))


class TestMqttProtobufDecode(unittest.TestCase):
    def test_parses_captured_fixture(self) -> None:
        fixture_path = Path(__file__).parent / "fixtures" / "mqtt_device_log.bin"
        telemetry = decode_device_log_payload(fixture_path.read_bytes())

        self.assertEqual(telemetry.session_id, 80675)
        self.assertEqual(telemetry.process_state, 101)
        self.assertEqual(telemetry.user_action_state, 28)
        self.assertAlmostEqual(telemetry.current_temperature or 0.0, 18.5, places=4)
        self.assertAlmostEqual(telemetry.target_temperature or 0.0, 20.0, places=4)
        self.assertEqual(telemetry.remaining_process_duration_seconds, 5400)
        self.assertEqual(telemetry.seconds_until_next_action, 300)
        self.assertEqual(telemetry.message_timestamp, datetime(2024, 7, 25, 16, 0, tzinfo=timezone.utc))
        self.assertEqual(telemetry.next_action_at, datetime(2024, 7, 25, 16, 5, tzinfo=timezone.utc))
        self.assertIn(99, telemetry.unknown_fields)


class TestBreweryClientMqttApi(unittest.TestCase):
    def test_create_mqtt_client_api(self) -> None:
        client = BreweryClient("test_user", "test-pass", "https://api.example.com")
        client.client._ensure_token = MagicMock()
        client.client.token = "token"
        client.client.get_user_profile = MagicMock(return_value=UserProfile(uuid="user-uuid"))

        mqtt_client = client.create_mqtt_client()

        self.assertIsInstance(mqtt_client, MiniBrewMqttClient)


if __name__ == "__main__":
    unittest.main()
