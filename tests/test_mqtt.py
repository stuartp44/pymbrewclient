import struct
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

from pymbrewclient.mqtt.client import (
    BROKER_HOST,
    BROKER_PORT,
    KEEPALIVE,
    RECONNECT_DELAY,
    WS_PATH,
    MqttClient,
    _extract_device_uuid,
)
from pymbrewclient.mqtt.models import DeviceLogMessage, MqttMessage
from pymbrewclient.mqtt.proto import decode_device_log, decode_raw_fields
from requests.certs import where as requests_ca_bundle

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def _encode_varint(value: int) -> bytes:
    result = []
    while value > 127:
        result.append((value & 0x7F) | 0x80)
        value >>= 7
    result.append(value)
    return bytes(result)


def _encode_float32(value: float) -> bytes:
    return struct.pack("<f", value)


def _build_device_log_payload(
    session_id: int = 12345,
    device_timestamp_ms: int = 1721993600000,
    current_state: int = 1,
    process_type: int = 4,
    process_state: int = 80,
    user_action: int = 0,
    current_temperature: float = 15.1,
    target_temperature: float = 14.91,
    unknown_field_8: int = 4607,
    unknown_field_30: int = 300,
) -> bytes:
    """Build a minimal valid protobuf payload matching the observed schema."""
    state = b""
    state += _encode_varint((1 << 3) | 0) + _encode_varint(current_state)
    state += _encode_varint((2 << 3) | 0) + _encode_varint(process_type)
    state += _encode_varint((3 << 3) | 0) + _encode_varint(process_state)
    state += _encode_varint((8 << 3) | 0) + _encode_varint(user_action)

    data = b""
    data += _encode_varint((1 << 3) | 0) + _encode_varint(device_timestamp_ms)
    data += _encode_varint((2 << 3) | 2) + _encode_varint(len(state)) + state
    data += _encode_varint((8 << 3) | 0) + _encode_varint(unknown_field_8)
    data += _encode_varint((11 << 3) | 0) + _encode_varint(session_id)
    data += _encode_varint((18 << 3) | 5) + _encode_float32(target_temperature)
    data += _encode_varint((19 << 3) | 5) + _encode_float32(current_temperature)
    data += _encode_varint((30 << 3) | 0) + _encode_varint(unknown_field_30)
    return data


def _make_mqtt_message(topic: str, payload: bytes) -> MqttMessage:
    return MqttMessage(
        topic=topic,
        payload=payload,
        received_at=datetime(2024, 7, 26, 12, 0, 0, tzinfo=timezone.utc),
        device_uuid=_extract_device_uuid(topic),
    )


# ---------------------------------------------------------------------------
# MqttClient construction tests
# ---------------------------------------------------------------------------


class TestMqttClientConstruction(unittest.TestCase):
    """Tests for client_id and username construction, credential wiring."""

    def _make_client(self) -> MqttClient:
        with (patch("pymbrewclient.mqtt.client._paho.Client") as mock_paho_cls,):
            mock_paho = MagicMock()
            mock_paho_cls.return_value = mock_paho
            return MqttClient(api_token="test-token-xyz", user_uuid="user-uuid-abc")

    def test_client_id_uses_breweryportal_prefix(self) -> None:
        client = self._make_client()
        self.assertTrue(client._client_id.startswith("breweryportal-"))

    def test_client_id_contains_uuid4(self) -> None:

        client = self._make_client()
        uuid_part = client._client_id.removeprefix("breweryportal-")
        self.assertRegex(uuid_part, r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")

    def test_client_uuid_is_unique_per_instance(self) -> None:
        with patch("pymbrewclient.mqtt.client._paho.Client"):
            c1 = MqttClient(api_token="token", user_uuid="u1")
            c2 = MqttClient(api_token="token", user_uuid="u1")
        self.assertNotEqual(c1._client_id, c2._client_id)

    def test_username_uses_breweryportal_prefix(self) -> None:
        client = self._make_client()
        self.assertEqual(client._username, "breweryportal-user-uuid-abc")

    def test_api_token_used_as_mqtt_password(self) -> None:
        """The REST API token must be passed as the MQTT password."""
        with patch("pymbrewclient.mqtt.client._paho.Client") as mock_paho_cls:
            mock_paho = MagicMock()
            mock_paho_cls.return_value = mock_paho
            MqttClient(api_token="secret-api-token", user_uuid="user-uuid-123")

        args, kwargs = mock_paho.username_pw_set.call_args
        # paho-mqtt called with positional args: (username, password)
        self.assertEqual(args[0], "breweryportal-user-uuid-123")
        self.assertEqual(args[1], "secret-api-token")

    def test_token_absent_from_repr(self) -> None:
        """The API token must never appear in __repr__."""
        with patch("pymbrewclient.mqtt.client._paho.Client"):
            client = MqttClient(api_token="super-secret-token", user_uuid="uid")
        self.assertNotIn("super-secret-token", repr(client))

    def test_repr_contains_expected_fields(self) -> None:
        with patch("pymbrewclient.mqtt.client._paho.Client"):
            client = MqttClient(api_token="token", user_uuid="uid")
        r = repr(client)
        self.assertIn("client_id=", r)
        self.assertIn("username=", r)
        self.assertIn("broker=", r)
        self.assertIn("connected=", r)


# ---------------------------------------------------------------------------
# Broker and TLS configuration tests
# ---------------------------------------------------------------------------


class TestMqttBrokerConfiguration(unittest.TestCase):
    def test_broker_constants(self) -> None:
        self.assertEqual(BROKER_HOST, "broker.minibrew.io")
        self.assertEqual(BROKER_PORT, 15675)
        self.assertEqual(WS_PATH, "/ws")
        self.assertEqual(KEEPALIVE, 60)

    def test_paho_client_uses_websocket_transport(self) -> None:
        with patch("pymbrewclient.mqtt.client._paho.Client") as mock_cls:
            mock_cls.return_value = MagicMock()
            MqttClient(api_token="t", user_uuid="u")
        _, kwargs = mock_cls.call_args
        self.assertEqual(kwargs["transport"], "websockets")

    def test_paho_client_uses_mqtt_v311(self) -> None:
        import paho.mqtt.client as paho

        with patch("pymbrewclient.mqtt.client._paho.Client") as mock_cls:
            mock_cls.return_value = MagicMock()
            MqttClient(api_token="t", user_uuid="u")
        _, kwargs = mock_cls.call_args
        self.assertEqual(kwargs["protocol"], paho.MQTTv311)

    def test_paho_client_uses_clean_session(self) -> None:
        with patch("pymbrewclient.mqtt.client._paho.Client") as mock_cls:
            mock_cls.return_value = MagicMock()
            MqttClient(api_token="t", user_uuid="u")
        _, kwargs = mock_cls.call_args
        self.assertTrue(kwargs["clean_session"])

    def test_tls_is_enabled(self) -> None:
        with patch("pymbrewclient.mqtt.client._paho.Client") as mock_cls:
            mock_paho = MagicMock()
            mock_cls.return_value = mock_paho
            MqttClient(api_token="t", user_uuid="u")
        mock_paho.tls_set.assert_called_once_with(ca_certs=requests_ca_bundle())
        mock_paho.tls_insecure_set.assert_not_called()

    def test_ws_path_is_set(self) -> None:
        with patch("pymbrewclient.mqtt.client._paho.Client") as mock_cls:
            mock_paho = MagicMock()
            mock_cls.return_value = mock_paho
            MqttClient(api_token="t", user_uuid="u")
        mock_paho.ws_set_options.assert_called_once_with(path="/ws")

    def test_keepalive_passed_to_connect(self) -> None:
        with patch("pymbrewclient.mqtt.client._paho.Client") as mock_cls:
            mock_paho = MagicMock()
            mock_cls.return_value = mock_paho
            client = MqttClient(api_token="t", user_uuid="u")
            client.connect()
        mock_paho.connect.assert_called_once_with(host=BROKER_HOST, port=BROKER_PORT, keepalive=KEEPALIVE)

    def test_reconnect_delay_is_five_seconds(self) -> None:
        with patch("pymbrewclient.mqtt.client._paho.Client") as mock_cls:
            mock_paho = MagicMock()
            mock_cls.return_value = mock_paho
            MqttClient(api_token="t", user_uuid="u")
        mock_paho.reconnect_delay_set.assert_called_once_with(min_delay=RECONNECT_DELAY, max_delay=RECONNECT_DELAY)


# ---------------------------------------------------------------------------
# Last Will tests
# ---------------------------------------------------------------------------


class TestLastWill(unittest.TestCase):
    def test_last_will_topic_format(self) -> None:
        with patch("pymbrewclient.mqtt.client._paho.Client") as mock_cls:
            mock_paho = MagicMock()
            mock_cls.return_value = mock_paho
            client = MqttClient(api_token="t", user_uuid="u")

        expected_topic = f"apps/lastwill/{client._client_id}"
        mock_paho.will_set.assert_called_once_with(topic=expected_topic, payload="offline", qos=0, retain=False)

    def test_last_will_payload_is_offline(self) -> None:
        with patch("pymbrewclient.mqtt.client._paho.Client") as mock_cls:
            mock_paho = MagicMock()
            mock_cls.return_value = mock_paho
            MqttClient(api_token="t", user_uuid="u")
        _, kwargs = mock_paho.will_set.call_args
        self.assertEqual(kwargs["payload"], "offline")
        self.assertEqual(kwargs["qos"], 0)
        self.assertFalse(kwargs["retain"])


# ---------------------------------------------------------------------------
# Device topic construction
# ---------------------------------------------------------------------------


class TestDeviceTopicConstruction(unittest.TestCase):
    def test_device_log_topic(self) -> None:
        self.assertEqual(MqttClient.device_log_topic("7391Q4827-5NZC8R2M"), "devices/logs/7391Q4827-5NZC8R2M")

    def test_extract_device_uuid_from_device_topic(self) -> None:
        self.assertEqual(_extract_device_uuid("devices/logs/7391Q4827-5NZC8R2M"), "7391Q4827-5NZC8R2M")
        self.assertEqual(_extract_device_uuid("devices/events/ABC-123"), "ABC-123")

    def test_extract_device_uuid_returns_none_for_other_topics(self) -> None:
        self.assertIsNone(_extract_device_uuid("apps/lastwill/some-id"))
        self.assertIsNone(_extract_device_uuid("backend/notifications/user-id"))


# ---------------------------------------------------------------------------
# Subscribe / unsubscribe / auto-resubscribe tests
# ---------------------------------------------------------------------------


class TestSubscriptions(unittest.TestCase):
    def _make_client(self) -> tuple[MqttClient, MagicMock]:
        with patch("pymbrewclient.mqtt.client._paho.Client") as mock_cls:
            mock_paho = MagicMock()
            mock_cls.return_value = mock_paho
            client = MqttClient(api_token="t", user_uuid="u")
        return client, mock_paho

    def test_subscribe_adds_to_subscription_set(self) -> None:
        client, _ = self._make_client()
        client._connected = False
        client.subscribe("devices/logs/my-device")
        self.assertIn("devices/logs/my-device", client._subscriptions)

    def test_subscribe_calls_paho_when_connected(self) -> None:
        client, mock_paho = self._make_client()
        client._connected = True
        client.subscribe("devices/logs/my-device", qos=1)
        mock_paho.subscribe.assert_called_with("devices/logs/my-device", qos=1)

    def test_unsubscribe_removes_from_set(self) -> None:
        client, _ = self._make_client()
        client._subscriptions.add("devices/logs/my-device")
        client._connected = False
        client.unsubscribe("devices/logs/my-device")
        self.assertNotIn("devices/logs/my-device", client._subscriptions)

    def test_subscribe_device_logs_uses_correct_topic(self) -> None:
        client, mock_paho = self._make_client()
        client._connected = True
        client.subscribe_device_logs("7391Q4827-5NZC8R2M")
        mock_paho.subscribe.assert_called_with("devices/logs/7391Q4827-5NZC8R2M", qos=0)

    def test_auto_resubscribe_on_connect(self) -> None:
        """All remembered topics are resubscribed on each connect callback."""
        client, mock_paho = self._make_client()
        client._subscriptions = {"devices/logs/dev-1", "devices/logs/dev-2"}

        # Simulate paho on_connect with a successful reason code
        mock_reason_code = MagicMock()
        mock_reason_code.is_failure = False
        mock_connect_flags = MagicMock()
        mock_connect_flags.session_present = False

        client._on_paho_connect(mock_paho, None, mock_connect_flags, mock_reason_code, None)

        subscribed_topics = {c[0][0] for c in mock_paho.subscribe.call_args_list}
        self.assertIn("devices/logs/dev-1", subscribed_topics)
        self.assertIn("devices/logs/dev-2", subscribed_topics)

    def test_auto_resubscribe_skipped_on_connect_failure(self) -> None:
        client, mock_paho = self._make_client()
        client._subscriptions = {"devices/logs/dev-1"}

        mock_reason_code = MagicMock()
        mock_reason_code.is_failure = True
        mock_connect_flags = MagicMock()

        client._on_paho_connect(mock_paho, None, mock_connect_flags, mock_reason_code, None)

        mock_paho.subscribe.assert_not_called()


# ---------------------------------------------------------------------------
# Connection lifecycle
# ---------------------------------------------------------------------------


class TestConnectionLifecycle(unittest.TestCase):
    def _make_client(self) -> tuple[MqttClient, MagicMock]:
        with patch("pymbrewclient.mqtt.client._paho.Client") as mock_cls:
            mock_paho = MagicMock()
            mock_cls.return_value = mock_paho
            client = MqttClient(api_token="t", user_uuid="u")
        return client, mock_paho

    def test_connect_calls_loop_start(self) -> None:
        client, mock_paho = self._make_client()
        client.connect()
        mock_paho.loop_start.assert_called_once()

    def test_disconnect_calls_loop_stop(self) -> None:
        client, mock_paho = self._make_client()
        client.disconnect()
        mock_paho.loop_stop.assert_called_once()

    def test_disconnect_calls_paho_disconnect(self) -> None:
        client, mock_paho = self._make_client()
        client.disconnect()
        mock_paho.disconnect.assert_called_once()

    def test_disconnect_clears_connected_flag(self) -> None:
        client, mock_paho = self._make_client()
        client._connected = True
        client.disconnect()
        self.assertFalse(client._connected)

    def test_context_manager_connects_and_disconnects(self) -> None:
        with patch("pymbrewclient.mqtt.client._paho.Client") as mock_cls:
            mock_paho = MagicMock()
            mock_cls.return_value = mock_paho
            client = MqttClient(api_token="t", user_uuid="u")

        with client:
            mock_paho.connect.assert_called_once()
            mock_paho.loop_start.assert_called_once()

        mock_paho.disconnect.assert_called_once()
        mock_paho.loop_stop.assert_called_once()

    def test_connected_callback_fires_on_successful_connect(self) -> None:
        client, mock_paho = self._make_client()
        fired = []
        client.on_connected(lambda: fired.append(True))

        mock_reason = MagicMock()
        mock_reason.is_failure = False
        mock_flags = MagicMock()
        mock_flags.session_present = False

        client._on_paho_connect(mock_paho, None, mock_flags, mock_reason, None)
        self.assertEqual(fired, [True])

    def test_disconnected_callback_fires(self) -> None:
        client, mock_paho = self._make_client()
        fired = []
        client.on_disconnected(lambda: fired.append(True))

        mock_reason = MagicMock()
        mock_flags = MagicMock()
        client._on_paho_disconnect(mock_paho, None, mock_flags, mock_reason, None)
        self.assertEqual(fired, [True])

    def test_reconnecting_callback_fires_on_second_pre_connect(self) -> None:
        client, mock_paho = self._make_client()
        fired = []
        client.on_reconnecting(lambda: fired.append(True))

        # First pre-connect: _ever_connected is False → no reconnecting event
        client._on_paho_pre_connect(mock_paho, None)
        self.assertEqual(fired, [])

        # Mark as previously connected, then fire again
        client._ever_connected = True
        client._on_paho_pre_connect(mock_paho, None)
        self.assertEqual(fired, [True])

    def test_error_callback_fires_on_connect_failure(self) -> None:
        client, mock_paho = self._make_client()
        errors = []
        client.on_error(lambda e: errors.append(e))

        mock_reason = MagicMock()
        mock_reason.is_failure = True
        mock_flags = MagicMock()

        client._on_paho_connect(mock_paho, None, mock_flags, mock_reason, None)
        self.assertEqual(len(errors), 1)
        self.assertIsInstance(errors[0], ConnectionError)

    def test_token_absent_from_error_exception(self) -> None:
        """The API token must not appear in error callback exceptions."""
        client, mock_paho = self._make_client()
        errors: list[Exception] = []
        client.on_error(lambda e: errors.append(e))

        mock_reason = MagicMock()
        mock_reason.is_failure = True
        mock_reason.__str__ = lambda self: "auth failure"
        mock_flags = MagicMock()

        client._on_paho_connect(mock_paho, None, mock_flags, mock_reason, None)

        self.assertTrue(errors)
        self.assertNotIn("test-token-xyz", str(errors[0]))


# ---------------------------------------------------------------------------
# Raw message callback
# ---------------------------------------------------------------------------


class TestRawMessageCallback(unittest.TestCase):
    def _make_client(self) -> tuple[MqttClient, MagicMock]:
        with patch("pymbrewclient.mqtt.client._paho.Client") as mock_cls:
            mock_paho = MagicMock()
            mock_cls.return_value = mock_paho
            client = MqttClient(api_token="t", user_uuid="u")
        return client, mock_paho

    def test_on_message_delivers_raw_message(self) -> None:
        client, mock_paho = self._make_client()
        received: list[MqttMessage] = []
        client.on_message(received.append)

        mock_msg = MagicMock()
        mock_msg.topic = "devices/events/my-dev"
        mock_msg.payload = b"\x01\x02\x03"

        client._on_paho_message(mock_paho, None, mock_msg)

        self.assertEqual(len(received), 1)
        self.assertEqual(received[0].topic, "devices/events/my-dev")
        self.assertEqual(received[0].payload, b"\x01\x02\x03")
        self.assertIsNotNone(received[0].received_at.tzinfo)

    def test_on_message_extracts_device_uuid(self) -> None:
        client, mock_paho = self._make_client()
        received: list[MqttMessage] = []
        client.on_message(received.append)

        mock_msg = MagicMock()
        mock_msg.topic = "devices/logs/7391Q4827-5NZC8R2M"
        mock_msg.payload = b"\x00"

        client._on_paho_message(mock_paho, None, mock_msg)

        self.assertEqual(received[0].device_uuid, "7391Q4827-5NZC8R2M")


# ---------------------------------------------------------------------------
# Protobuf fixture parsing
# ---------------------------------------------------------------------------


class TestDeviceLogFixtureParsing(unittest.TestCase):
    """Parse a captured device-log payload from tests/fixtures/."""

    def setUp(self) -> None:
        fixture_path = FIXTURES_DIR / "device_log.hex"
        self.payload = bytes.fromhex(fixture_path.read_text().strip())

    def test_fixture_file_exists_and_is_nonempty(self) -> None:
        self.assertGreater(len(self.payload), 0)

    def test_decode_session_id(self) -> None:
        msg = _make_mqtt_message("devices/logs/test-dev", self.payload)
        decoded = decode_device_log(msg)
        self.assertEqual(decoded.session_id, 80851)

    def test_decode_device_timestamp(self) -> None:
        msg = _make_mqtt_message("devices/logs/test-dev", self.payload)
        decoded = decode_device_log(msg)
        expected = datetime(2026, 7, 25, 19, 58, 43, 644000, tzinfo=timezone.utc)
        self.assertEqual(decoded.device_timestamp, expected)

    def test_decode_nested_state(self) -> None:
        msg = _make_mqtt_message("devices/logs/test-dev", self.payload)
        decoded = decode_device_log(msg)
        self.assertEqual(decoded.current_state, 1)
        self.assertEqual(decoded.process_type, 4)
        self.assertEqual(decoded.process_state, 80)
        self.assertEqual(decoded.user_action, 0)
        self.assertEqual(decoded.state_fields[7], [b"-"])

    def test_decode_process_state(self) -> None:
        msg = _make_mqtt_message("devices/logs/test-dev", self.payload)
        decoded = decode_device_log(msg)
        self.assertEqual(decoded.process_state, 80)  # FERMENTATION_TEMP_CONTROL

    def test_decode_user_action(self) -> None:
        msg = _make_mqtt_message("devices/logs/test-dev", self.payload)
        decoded = decode_device_log(msg)
        self.assertEqual(decoded.user_action, 0)

    def test_decode_current_temperature(self) -> None:
        msg = _make_mqtt_message("devices/logs/test-dev", self.payload)
        decoded = decode_device_log(msg)
        self.assertIsNotNone(decoded.current_temperature)
        self.assertAlmostEqual(decoded.current_temperature, 19.3, places=2)

    def test_decode_target_temperature(self) -> None:
        msg = _make_mqtt_message("devices/logs/test-dev", self.payload)
        decoded = decode_device_log(msg)
        self.assertIsNotNone(decoded.target_temperature)
        self.assertAlmostEqual(decoded.target_temperature, 19.0, places=2)

    def test_decode_next_action(self) -> None:
        decoded = decode_device_log(_make_mqtt_message("devices/logs/test-dev", self.payload))
        self.assertEqual(decoded.seconds_until_next_action, 851903)
        expected = datetime(2026, 8, 4, 16, 37, 6, 644000, tzinfo=timezone.utc)
        self.assertEqual(decoded.next_action_at, expected)

    def test_decode_measurements_preserves_all_sensor_ids(self) -> None:
        msg = _make_mqtt_message("devices/logs/test-dev", self.payload)
        decoded = decode_device_log(msg)
        expected = {
            0: 27.3,
            3: 19.3,
            4: 18.2,
            13: 121.0,
            19: 0.0,
            21: 0.0,
            22: 0.0,
            23: 0.0,
            24: -45.0,
            26: 100.0,
            27: 0.0,
        }
        self.assertEqual(decoded.measurements.keys(), expected.keys())
        for measurement_id, value in expected.items():
            self.assertAlmostEqual(decoded.measurements[measurement_id], value, places=2)

    def test_decode_wifi_rssi(self) -> None:
        decoded = decode_device_log(_make_mqtt_message("devices/logs/test-dev", self.payload))
        self.assertEqual(decoded.wifi_rssi_dbm, -45.0)

    def test_raw_payload_is_preserved(self) -> None:
        msg = _make_mqtt_message("devices/logs/test-dev", self.payload)
        decoded = decode_device_log(msg)
        self.assertEqual(decoded.payload, self.payload)

    def test_no_decode_error(self) -> None:
        msg = _make_mqtt_message("devices/logs/test-dev", self.payload)
        decoded = decode_device_log(msg)
        self.assertIsNone(decoded.decode_error)

    def test_mqtt_callback_delivers_decoded_captured_payload(self) -> None:
        with patch("pymbrewclient.mqtt.client._paho.Client") as mock_cls:
            mock_paho = MagicMock()
            mock_cls.return_value = mock_paho
            client = MqttClient(api_token="t", user_uuid="u")

        received: list[DeviceLogMessage] = []
        client.on_device_log(received.append)
        mock_msg = MagicMock(topic="devices/logs/test-dev", payload=self.payload)
        client._on_paho_message(mock_paho, None, mock_msg)

        self.assertEqual(len(received), 1)
        self.assertEqual(received[0].session_id, 80851)
        self.assertEqual(received[0].process_state, 80)
        self.assertAlmostEqual(received[0].measurements[3], 19.3, places=2)


class TestLiveDeviceLogEnvelopeParsing(unittest.TestCase):
    """Parse the envelope received by the live MQTT watch command."""

    def setUp(self) -> None:
        fixture_path = FIXTURES_DIR / "device_log_envelope.hex"
        self.payload = bytes.fromhex(fixture_path.read_text().strip())
        self.decoded = decode_device_log(_make_mqtt_message("devices/logs/test-dev", self.payload))

    def test_decodes_envelope_metadata(self) -> None:
        self.assertEqual(self.decoded.sequence_number, 24098)
        self.assertEqual(self.decoded.session_id, 80851)
        expected = datetime(2026, 7, 25, 20, 6, 0, 644000, tzinfo=timezone.utc)
        self.assertEqual(self.decoded.device_timestamp, expected)

    def test_decodes_nested_telemetry(self) -> None:
        self.assertEqual(self.decoded.current_state, 1)
        self.assertEqual(self.decoded.process_type, 4)
        self.assertEqual(self.decoded.process_state, 80)
        self.assertEqual(self.decoded.user_action, 0)
        self.assertEqual(self.decoded.current_temperature, 19.2)
        self.assertEqual(self.decoded.target_temperature, 19.0)
        self.assertEqual(self.decoded.wifi_rssi_dbm, -36.0)
        self.assertEqual(self.decoded.measurements[3], 19.2)
        self.assertEqual(self.decoded.measurements[24], -36.0)

    def test_decodes_next_action_matching_portal(self) -> None:
        self.assertEqual(self.decoded.seconds_until_next_action, 851466)
        expected = datetime(2026, 8, 4, 16, 37, 6, 644000, tzinfo=timezone.utc)
        self.assertEqual(self.decoded.next_action_at, expected)

    def test_preserves_envelope_and_telemetry_fields(self) -> None:
        self.assertEqual(self.decoded.raw_fields[1], [24098])
        self.assertIn(3, self.decoded.raw_fields)
        self.assertEqual(self.decoded.telemetry_fields[11], [80851])
        self.assertIsNone(self.decoded.decode_error)


# ---------------------------------------------------------------------------
# Graceful error handling for malformed messages
# ---------------------------------------------------------------------------


class TestMalformedProtoHandling(unittest.TestCase):
    def test_empty_payload_decodes_without_error(self) -> None:
        msg = _make_mqtt_message("devices/logs/dev", b"")
        decoded = decode_device_log(msg)
        self.assertIsNone(decoded.decode_error)
        self.assertIsNone(decoded.session_id)

    def test_truncated_payload_sets_decode_error(self) -> None:
        # Start a valid varint tag but truncate mid-payload
        truncated = b"\x08"  # tag for field 1 varint, but value bytes missing
        msg = _make_mqtt_message("devices/logs/dev", truncated)
        decoded = decode_device_log(msg)
        self.assertIsNotNone(decoded.decode_error)

    def test_truncated_payload_preserves_raw_bytes(self) -> None:
        truncated = b"\x08"
        msg = _make_mqtt_message("devices/logs/dev", truncated)
        decoded = decode_device_log(msg)
        self.assertEqual(decoded.payload, truncated)

    def test_unknown_fields_are_captured_in_raw_fields(self) -> None:
        """Future fields with unknown numbers are preserved in raw_fields."""
        payload = _encode_varint((99 << 3) | 0) + _encode_varint(42)
        msg = _make_mqtt_message("devices/logs/dev", payload)
        decoded = decode_device_log(msg)
        self.assertIn(99, decoded.raw_fields)
        self.assertIsNone(decoded.decode_error)

    def test_malformed_nested_state_sets_decode_error(self) -> None:
        state = b"\x08"
        payload = _encode_varint((2 << 3) | 2) + _encode_varint(len(state)) + state
        decoded = decode_device_log(_make_mqtt_message("devices/logs/dev", payload))
        self.assertIsNotNone(decoded.decode_error)
        self.assertIn("Nested state decode failed", decoded.decode_error)

    def test_malformed_measurement_sets_decode_error(self) -> None:
        measurement = b"\x08"
        payload = _encode_varint((3 << 3) | 2) + _encode_varint(len(measurement)) + measurement
        decoded = decode_device_log(_make_mqtt_message("devices/logs/dev", payload))
        self.assertIsNotNone(decoded.decode_error)
        self.assertIn("Measurement decode failed", decoded.decode_error)

    def test_malformed_live_envelope_sets_decode_error(self) -> None:
        payload = (
            _encode_varint((3 << 3) | 2)
            + _encode_varint(1)
            + b"\x08"
            + _encode_varint((5 << 3) | 0)
            + _encode_varint(1721993600000)
        )
        decoded = decode_device_log(_make_mqtt_message("devices/logs/dev", payload))
        self.assertIsNotNone(decoded.decode_error)
        self.assertIn("Telemetry decode failed", decoded.decode_error)

    def test_malformed_message_does_not_raise(self) -> None:
        """Decoding errors must never propagate as exceptions."""
        bad_payloads = [
            b"\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff",  # overlong varint
            b"\x0d\x00\x00",  # truncated 32-bit field
            b"\x09\x00\x00\x00\x00\x00\x00\x00",  # truncated 64-bit field
        ]
        for payload in bad_payloads:
            with self.subTest(payload=payload.hex()):
                msg = _make_mqtt_message("devices/logs/dev", payload)
                decoded = decode_device_log(msg)
                self.assertIsNotNone(decoded.decode_error)

    def test_device_log_callback_fires_even_on_decode_error(self) -> None:
        """The on_device_log callback must fire for malformed messages."""
        with patch("pymbrewclient.mqtt.client._paho.Client") as mock_cls:
            mock_paho = MagicMock()
            mock_cls.return_value = mock_paho
            client = MqttClient(api_token="t", user_uuid="u")

        received: list[DeviceLogMessage] = []
        client.on_device_log(received.append)

        mock_msg = MagicMock()
        mock_msg.topic = "devices/logs/dev"
        mock_msg.payload = b"\x08"  # truncated
        client._on_paho_message(mock_paho, None, mock_msg)

        self.assertEqual(len(received), 1)
        self.assertIsNotNone(received[0].decode_error)


# ---------------------------------------------------------------------------
# decode_raw_fields unit tests
# ---------------------------------------------------------------------------


class TestDecodeRawFields(unittest.TestCase):
    def test_decode_single_varint(self) -> None:
        # field 1, wire type 0 (varint), value 42
        data = _encode_varint((1 << 3) | 0) + _encode_varint(42)
        raw = decode_raw_fields(data)
        self.assertEqual(raw[1], [42])

    def test_decode_single_float32(self) -> None:
        data = _encode_varint((5 << 3) | 5) + _encode_float32(3.14)
        raw = decode_raw_fields(data)
        result = struct.unpack("<f", raw[5][0])[0]
        self.assertAlmostEqual(result, 3.14, places=4)

    def test_decode_repeated_field(self) -> None:
        data = _encode_varint((2 << 3) | 0) + _encode_varint(10) + _encode_varint((2 << 3) | 0) + _encode_varint(20)
        raw = decode_raw_fields(data)
        self.assertEqual(raw[2], [10, 20])

    def test_decode_length_delimited_field(self) -> None:
        value = b"hello"
        data = _encode_varint((3 << 3) | 2) + _encode_varint(len(value)) + value
        raw = decode_raw_fields(data)
        self.assertEqual(raw[3], [b"hello"])

    def test_empty_bytes_returns_empty_dict(self) -> None:
        self.assertEqual(decode_raw_fields(b""), {})


# ---------------------------------------------------------------------------
# Token redaction in logs
# ---------------------------------------------------------------------------


class TestTokenRedaction(unittest.TestCase):
    def test_token_not_logged_at_debug(self) -> None:
        """Confirm the MQTT client module does not log the raw token."""
        import io
        import logging

        stream = io.StringIO()
        handler = logging.StreamHandler(stream)
        logger = logging.getLogger("pymbrewclient.mqtt.client")
        original_handlers = logger.handlers[:]
        original_level = logger.level

        try:
            logger.addHandler(handler)
            logger.setLevel(logging.DEBUG)
            handler.setLevel(logging.DEBUG)

            with patch("pymbrewclient.mqtt.client._paho.Client") as mock_cls:
                mock_paho = MagicMock()
                mock_cls.return_value = mock_paho
                client = MqttClient(api_token="very-secret-api-token", user_uuid="u")
                client.connect()
                client.subscribe("test/topic")
                client.disconnect()

            log_output = stream.getvalue()
            self.assertNotIn("very-secret-api-token", log_output)
        finally:
            logger.handlers = original_handlers
            logger.setLevel(original_level)


# ---------------------------------------------------------------------------
# BreweryClient.create_mqtt_client integration
# ---------------------------------------------------------------------------


class TestBreweryClientCreateMqttClient(unittest.TestCase):
    def test_create_mqtt_client_returns_mqtt_client(self) -> None:
        from pymbrewclient.client import BreweryClient
        from pymbrewclient.rest.models import UserProfile

        with (
            patch("pymbrewclient.rest.client.RestApiClient._ensure_token"),
            patch("pymbrewclient.rest.client.RestApiClient.get_user_profile") as mock_profile,
            patch("pymbrewclient.mqtt.client._paho.Client") as mock_paho_cls,
        ):
            mock_paho = MagicMock()
            mock_paho_cls.return_value = mock_paho
            mock_profile.return_value = UserProfile(uuid="profile-uuid-xyz")

            bc = BreweryClient("u", "p", base_url="https://api.example.com")
            bc.client.token = "rest-token-abc"

            mqtt = bc.create_mqtt_client()

        self.assertIsInstance(mqtt, MqttClient)

    def test_create_mqtt_client_reuses_rest_token(self) -> None:
        from pymbrewclient.client import BreweryClient
        from pymbrewclient.rest.models import UserProfile

        with (
            patch("pymbrewclient.rest.client.RestApiClient._ensure_token"),
            patch("pymbrewclient.rest.client.RestApiClient.get_user_profile") as mock_profile,
            patch("pymbrewclient.mqtt.client._paho.Client") as mock_paho_cls,
        ):
            mock_paho = MagicMock()
            mock_paho_cls.return_value = mock_paho
            mock_profile.return_value = UserProfile(uuid="profile-uuid-xyz")

            bc = BreweryClient("u", "p", base_url="https://api.example.com")
            bc.client.token = "the-rest-token"

            bc.create_mqtt_client()

        # REST token used as MQTT password
        args, kwargs = mock_paho.username_pw_set.call_args
        self.assertEqual(args[0], "breweryportal-profile-uuid-xyz")
        self.assertEqual(args[1], "the-rest-token")

    def test_create_mqtt_client_uses_user_uuid_for_username(self) -> None:
        from pymbrewclient.client import BreweryClient
        from pymbrewclient.rest.models import UserProfile

        with (
            patch("pymbrewclient.rest.client.RestApiClient._ensure_token"),
            patch("pymbrewclient.rest.client.RestApiClient.get_user_profile") as mock_profile,
            patch("pymbrewclient.mqtt.client._paho.Client") as mock_paho_cls,
        ):
            mock_paho = MagicMock()
            mock_paho_cls.return_value = mock_paho
            mock_profile.return_value = UserProfile(uuid="my-user-uuid-123")

            bc = BreweryClient("u", "p", base_url="https://api.example.com")
            bc.client.token = "tok"

            mqtt = bc.create_mqtt_client()

        self.assertEqual(mqtt._username, "breweryportal-my-user-uuid-123")

    def test_multiple_mqtt_clients_have_unique_client_ids(self) -> None:
        from pymbrewclient.client import BreweryClient
        from pymbrewclient.rest.models import UserProfile

        with (
            patch("pymbrewclient.rest.client.RestApiClient._ensure_token"),
            patch("pymbrewclient.rest.client.RestApiClient.get_user_profile") as mock_profile,
            patch("pymbrewclient.mqtt.client._paho.Client") as mock_paho_cls,
        ):
            mock_paho_cls.return_value = MagicMock()
            mock_profile.return_value = UserProfile(uuid="uid")

            bc = BreweryClient("u", "p", base_url="https://api.example.com")
            bc.client.token = "tok"

            m1 = bc.create_mqtt_client()
            m2 = bc.create_mqtt_client()

        self.assertNotEqual(m1._client_id, m2._client_id)


if __name__ == "__main__":
    unittest.main()
