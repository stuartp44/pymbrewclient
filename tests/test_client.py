import io
import json
import logging
import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from pymbrewclient.cli import app
from pymbrewclient.client import BreweryClient, BreweryClientError, DeviceLookupError
from pymbrewclient.rest.client import RestApiClient
from pymbrewclient.rest.models import Beer, BreweryOverview, Device, TokenResponse, format_duration

DEVICE_PAYLOAD = {
    "uuid": "device-uuid-1",
    "serial_number": "serial-1",
    "current_state": 2,
    "process_type": 2,
    "process_state": 101,
    "user_action": 2,
    "active_session": 80675,
    "connection_status": 1,
    "last_time_online": "2026-07-18T09:56:31.100000Z",
    "software_version": "3.2.3",
    "custom_name": "Fermenter 1",
    "device_type": 1,
    "image": "https://example.com/device.png",
    "last_process_state_change": "2026-07-18T09:45:16Z",
    "process_estimate_remaining": "2026-07-18T09:57:31.542739Z",
    "text": "Needs your attention",
    "updating": False,
}

SESSION_PAYLOAD = {
    "id": 12345,
    "profile": 67890,
    "beer": {"id": 11111, "name": "Mock Beer", "style_name": "Mock Style", "image": None},
    "device": {
        "uuid": "mock-uuid-12345",
        "serial_number": "mock-serial-12345",
        "current_state": 1,
        "process_type": 2,
        "process_state": 3,
        "user_action": 4,
        "device_type": 5,
        "connection_status": 6,
        "last_time_online": "2023-10-01T12:00:00Z",
        "software_version": "1.0.0",
        "custom_name": "Mock Device",
    },
    "status": 1,
    "session_type": 0,
    "pending_command_seq": 98765,
    "pending_command_type": 3,
    "pending_command_error": 0,
    "beer_recipe_id": 54321,
    "beer_recipe_version": "1",
    "brew_timestamp": 1743857868.656157,
    "original_gravity": None,
    "timestamp_original_gravity": None,
    "is_brewpack": False,
}


class TestRestApiClient(unittest.TestCase):
    def setUp(self) -> None:
        self.client = RestApiClient(base_url="https://api.example.com", username="test_user", password="test_password")

    @patch("pymbrewclient.rest.client.requests.post")
    def test_get_token(self, mock_post: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.json.return_value = {"token": "mock_token", "exp": 3600}
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        token_response = self.client._get_token()

        self.assertIsInstance(token_response, TokenResponse)
        self.assertEqual(token_response.token, "mock_token")
        self.assertGreater(self.client.token_expiry, 0)
        self.assertEqual(self.client.headers["Authorization"], "Bearer mock_token")

    def test_debug_logging_is_silent_by_default(self) -> None:
        library_logger = logging.getLogger("pymbrewclient.rest.client")
        root_logger = logging.getLogger()

        original_logger_level = library_logger.level
        original_root_level = root_logger.level
        original_root_handlers = root_logger.handlers[:]

        stream = io.StringIO()
        handler = logging.StreamHandler(stream)

        try:
            library_logger.setLevel(logging.NOTSET)
            root_logger.handlers = [handler]
            root_logger.setLevel(logging.WARNING)

            self.client.token = None
            self.client._is_token_valid()

            self.assertEqual(stream.getvalue(), "")
        finally:
            root_logger.handlers = original_root_handlers
            root_logger.setLevel(original_root_level)
            library_logger.setLevel(original_logger_level)

    def test_debug_logging_follows_host_configuration(self) -> None:
        library_logger = logging.getLogger("pymbrewclient.rest.client")
        root_logger = logging.getLogger()

        original_logger_level = library_logger.level
        original_root_level = root_logger.level
        original_root_handlers = root_logger.handlers[:]

        stream = io.StringIO()
        handler = logging.StreamHandler(stream)
        handler.setLevel(logging.DEBUG)

        try:
            library_logger.setLevel(logging.NOTSET)
            root_logger.handlers = [handler]
            root_logger.setLevel(logging.DEBUG)

            self.client.token = None
            self.client._is_token_valid()

            self.assertIn("Token is invalid or expired.", stream.getvalue())
        finally:
            root_logger.handlers = original_root_handlers
            root_logger.setLevel(original_root_level)
            library_logger.setLevel(original_logger_level)

    @patch("time.time")
    def test_is_token_valid(self, mock_time: MagicMock) -> None:
        self.client.token = "mock_token"
        self.client.token_expiry = 2000
        mock_time.return_value = 1000
        self.assertTrue(self.client._is_token_valid())

        mock_time.return_value = 3000
        self.assertFalse(self.client._is_token_valid())

        self.client.token = None
        self.assertFalse(self.client._is_token_valid())

    @patch("pymbrewclient.rest.client.RestApiClient._get_token")
    @patch("time.time")
    def test_ensure_token(self, mock_time: MagicMock, mock_get_token: MagicMock) -> None:
        self.client.token = "mock_token"
        self.client.token_expiry = 2000
        mock_time.return_value = 1000
        self.client._ensure_token()
        mock_get_token.assert_not_called()

        mock_time.return_value = 3000
        self.client._ensure_token()
        mock_get_token.assert_called_once()

        self.client.token = None
        self.client._ensure_token()
        self.assertEqual(mock_get_token.call_count, 2)

    @patch("pymbrewclient.rest.client.requests.get")
    @patch("pymbrewclient.rest.client.RestApiClient._ensure_token")
    def test_get(self, mock_ensure_token: MagicMock, mock_get: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.json.return_value = {"key": "value"}
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        response = self.client.get("test-endpoint", params={"param1": "value1"})

        mock_ensure_token.assert_called_once()
        mock_get.assert_called_once_with(
            f"{self.client.base_url}/test-endpoint/", headers=self.client.headers, params={"param1": "value1"}
        )
        self.assertEqual(response.json(), {"key": "value"})

    @patch("pymbrewclient.rest.client.requests.get")
    @patch("pymbrewclient.rest.client.RestApiClient._ensure_token")
    def test_get_brewery_overview(self, mock_ensure_token: MagicMock, mock_get: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "brew_clean_idle": [],
            "fermenting": [],
            "serving": [],
            "brew_acid_clean_idle": [],
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        overview = self.client.get_brewery_overview()

        self.assertIsInstance(overview, BreweryOverview)
        self.assertEqual(len(overview.brew_clean_idle), 0)
        self.assertEqual(len(overview.fermenting), 0)

    @patch("pymbrewclient.rest.client.requests.get")
    @patch("pymbrewclient.rest.client.RestApiClient._ensure_token")
    def test_get_brewery_overview_converts_devices(self, mock_ensure_token: MagicMock, mock_get: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "brew_clean_idle": [DEVICE_PAYLOAD],
            "fermenting": [],
            "serving": [],
            "brew_acid_clean_idle": [],
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        overview = self.client.get_brewery_overview()

        mock_ensure_token.assert_called_once()
        mock_get.assert_called_once_with(
            f"{self.client.base_url}/v1/breweryoverview/", params=None, headers=self.client.headers
        )
        self.assertIsInstance(overview, BreweryOverview)
        self.assertEqual(len(overview.brew_clean_idle), 1)
        self.assertIsInstance(overview.brew_clean_idle[0], Device)

    @patch("pymbrewclient.rest.client.requests.get")
    @patch("pymbrewclient.rest.client.RestApiClient._ensure_token")
    def test_get_brewery_overview_with_unknown_fields(self, mock_ensure_token: MagicMock, mock_get: MagicMock) -> None:
        mock_device = {
            "uuid": "test-uuid-1",
            "serial_number": "SN12345",
            "device_type": 0,
            "user_action": 0,
            "process_type": 0,
            "title": "Test Device",
            "sub_title": "Connected",
            "session_id": None,
            "image": "https://example.com/device.png",
            "status_time": None,
            "stage": "Idle",
            "beer_name": None,
            "recipe_version": None,
            "beer_style": None,
            "beer_srm": None,
            "gravity": "1.00",
            "target_temp": None,
            "current_temp": None,
            "online": True,
            "updating": False,
            "needs_acid_cleaning": False,
            "is_starting": None,
            "software_version": "1.0.0",
            "unknown_field_1": "value1",
            "future_feature": 42,
        }

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "brew_clean_idle": [mock_device],
            "fermenting": [],
            "serving": [],
            "brew_acid_clean_idle": [],
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        overview = self.client.get_brewery_overview()

        self.assertEqual(overview.brew_clean_idle[0].uuid, "test-uuid-1")
        self.assertEqual(overview.brew_clean_idle[0].serial_number, "SN12345")

    @patch("pymbrewclient.rest.client.requests.get")
    @patch("pymbrewclient.rest.client.RestApiClient._ensure_token")
    def test_get_devices_uses_existing_authentication_flow(
        self, mock_ensure_token: MagicMock, mock_get: MagicMock
    ) -> None:
        mock_response = MagicMock()
        mock_response.json.return_value = [DEVICE_PAYLOAD]
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        devices = self.client.get_devices()

        mock_ensure_token.assert_called_once()
        mock_get.assert_called_once_with(
            f"{self.client.base_url}/v1/devices/", params=None, headers=self.client.headers
        )
        self.assertEqual(len(devices), 1)
        self.assertIsInstance(devices[0], Device)

    @patch("pymbrewclient.rest.client.requests.get")
    @patch("pymbrewclient.rest.client.RestApiClient._ensure_token")
    def test_get_session_info(self, mock_ensure_token: MagicMock, mock_get: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.json.return_value = SESSION_PAYLOAD
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        session_info = self.client.get_session_info(12345)

        mock_ensure_token.assert_called_once()
        mock_get.assert_called_once_with(
            f"{self.client.base_url}/v1/sessions/12345/", params=None, headers=self.client.headers
        )
        beer = session_info.beer
        self.assertIsInstance(beer, Beer)
        self.assertEqual(beer.id, 11111)
        self.assertEqual(beer.name, "Mock Beer")
        self.assertEqual(beer.style_name, "Mock Style")
        self.assertIsNone(beer.image)

    @patch("pymbrewclient.rest.client.requests.post")
    def test_get_token_error(self, mock_post: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = Exception("API error")
        mock_post.return_value = mock_response

        with self.assertRaises(Exception) as context:
            self.client._get_token()
        self.assertEqual(str(context.exception), "API error")
        mock_post.assert_called_once()


class TestDeviceModel(unittest.TestCase):
    def test_timestamp_fields_are_timezone_aware_and_fractional_seconds_are_preserved(self) -> None:
        device = Device(**DEVICE_PAYLOAD)

        self.assertEqual(device.last_time_online.tzinfo, timezone.utc)
        self.assertEqual(device.last_process_state_change.tzinfo, timezone.utc)
        self.assertEqual(device.process_estimate_remaining.tzinfo, timezone.utc)
        self.assertEqual(device.process_estimate_remaining.microsecond, 542739)

    def test_missing_and_null_timestamps_are_handled(self) -> None:
        device = Device(uuid="device-uuid-2", process_estimate_remaining=None)

        self.assertIsNone(device.last_time_online)
        self.assertIsNone(device.last_process_state_change)
        self.assertIsNone(device.process_estimate_remaining)
        self.assertIsNone(device.process_estimate_remaining_seconds)
        self.assertIsNone(device.process_estimate_remaining_formatted)

    def test_device_supports_dict_style_access_for_backward_compatibility(self) -> None:
        device = Device(**DEVICE_PAYLOAD)

        self.assertIn("uuid", device)
        self.assertEqual(device["uuid"], "device-uuid-1")
        self.assertEqual(device.get("custom_name"), "Fermenter 1")

    def test_future_estimates_calculate_expected_seconds(self) -> None:
        device = Device(**DEVICE_PAYLOAD)
        current_time = datetime(2026, 7, 18, 8, 40, 44, 542739, tzinfo=timezone.utc)

        self.assertEqual(device.get_process_estimate_remaining_seconds(current_time=current_time), 4607)
        self.assertEqual(device.get_process_estimate_remaining_formatted(current_time=current_time), "1:16:47")

    def test_past_estimates_return_zero_remaining_seconds(self) -> None:
        device = Device(**DEVICE_PAYLOAD)
        current_time = datetime(2026, 7, 18, 10, 0, 0, tzinfo=timezone.utc)

        self.assertEqual(device.get_process_estimate_remaining_seconds(current_time=current_time), 0)
        self.assertEqual(device.get_process_estimate_remaining_formatted(current_time=current_time), "0:00:00")

    def test_duration_formatting_handles_over_one_hour(self) -> None:
        self.assertEqual(format_duration(4607), "1:16:47")
        self.assertEqual(format_duration(90), "0:01:30")


class TestBreweryClient(unittest.TestCase):
    def setUp(self) -> None:
        self.client = BreweryClient(username="test_user", password="test_password", base_url="https://api.example.com")

    def test_get_devices_delegates_to_rest_client(self) -> None:
        devices = [Device(**DEVICE_PAYLOAD)]
        self.client.client.get_devices = MagicMock(return_value=devices)

        self.assertEqual(self.client.get_devices(), devices)
        self.client.client.get_devices.assert_called_once_with()

    def test_device_lookup_by_uuid_works(self) -> None:
        device = Device(**DEVICE_PAYLOAD)
        self.client.client.get_devices = MagicMock(return_value=[device])

        estimate = self.client.get_process_estimate(device_uuid="device-uuid-1")

        self.assertEqual(estimate, device.process_estimate_remaining)

    def test_device_lookup_by_active_session_works(self) -> None:
        device = Device(**DEVICE_PAYLOAD)
        self.client.client.get_devices = MagicMock(return_value=[device])

        estimate = self.client.get_process_estimate(session_id=80675)

        self.assertEqual(estimate, device.process_estimate_remaining)

    def test_missing_devices_raise_clear_error(self) -> None:
        self.client.client.get_devices = MagicMock(return_value=[])

        with self.assertRaises(DeviceLookupError) as context:
            self.client.get_process_estimate(device_uuid="missing-device")
        self.assertIn("No device found for UUID 'missing-device'.", str(context.exception))

    def test_ambiguous_selector_input_is_rejected(self) -> None:
        self.client.client.get_devices = MagicMock(return_value=[Device(**DEVICE_PAYLOAD)])

        with self.assertRaises(BreweryClientError):
            self.client.get_process_estimate()

        with self.assertRaises(BreweryClientError):
            self.client.get_process_estimate(device_uuid="device-uuid-1", session_id=80675)

    def test_duplicate_session_matches_raise_clear_error(self) -> None:
        duplicate_device = Device(**{**DEVICE_PAYLOAD, "uuid": "device-uuid-2"})
        self.client.client.get_devices = MagicMock(return_value=[Device(**DEVICE_PAYLOAD), duplicate_device])

        with self.assertRaises(DeviceLookupError) as context:
            self.client.get_process_estimate(session_id=80675)
        self.assertIn("Multiple devices found for active session ID 80675.", str(context.exception))

    def test_get_remaining_seconds_uses_device_helper(self) -> None:
        self.client.client.get_devices = MagicMock(return_value=[Device(**DEVICE_PAYLOAD)])

        remaining_seconds = self.client.get_process_estimate_remaining_seconds(device_uuid="device-uuid-1")

        self.assertIsInstance(remaining_seconds, int)


class TestCli(unittest.TestCase):
    def test_process_estimate_cli_outputs_json(self) -> None:
        runner = CliRunner()
        mock_client = MagicMock()
        mock_client.get_device.return_value = SimpleNamespace(
            process_estimate_remaining=datetime(2026, 7, 18, 9, 57, 31, 542739, tzinfo=timezone.utc),
            process_estimate_remaining_seconds=4607,
        )

        with patch("pymbrewclient.cli.initialize_brewery_client", return_value=mock_client):
            result = runner.invoke(
                app,
                [
                    "process-estimate",
                    "--username",
                    "user",
                    "--password",
                    "pass",
                    "--session-id",
                    "80675",
                    "--format",
                    "json",
                ],
            )

        self.assertEqual(result.exit_code, 0)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["process_estimate_remaining"], "2026-07-18T09:57:31.542739Z")
        self.assertEqual(payload["process_estimate_remaining_seconds"], 4607)
        self.assertEqual(payload["process_estimate_remaining_formatted"], "1:16:47")

    def test_watch_device_logs_requires_serial(self) -> None:
        runner = CliRunner()
        result = runner.invoke(
            app,
            ["watch-device-logs", "--username", "user", "--password", "pass"],
        )
        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("--serial", result.stdout)

    def test_watch_device_logs_streams_messages_as_json(self) -> None:
        """Connect, receive one device-log message, then stop via --duration 0."""
        from datetime import datetime, timezone

        from pymbrewclient.mqtt.models import DeviceLogMessage

        runner = CliRunner()

        sample_msg = DeviceLogMessage(
            topic="devices/logs/SER-001",
            payload=b"\x08\x01",
            received_at=datetime(2024, 7, 26, 12, 0, 0, tzinfo=timezone.utc),
            device_uuid="SER-001",
            session_id=1,
            process_state=80,
            current_temperature=15.0,
        )

        mock_mqtt = MagicMock()
        mock_mqtt.__enter__ = MagicMock(return_value=mock_mqtt)
        mock_mqtt.__exit__ = MagicMock(return_value=False)

        # Capture the on_device_log callback so we can invoke it synchronously
        device_log_callbacks: list = []

        def capture_on_device_log(cb: object) -> None:
            device_log_callbacks.append(cb)

        mock_mqtt.on_device_log.side_effect = capture_on_device_log

        mock_client = MagicMock()
        mock_client.create_mqtt_client.return_value = mock_mqtt

        def fake_wait(event: object, timeout: object = None) -> bool:  # type: ignore[override]
            for cb in device_log_callbacks:
                cb(sample_msg)
            return True

        with (
            patch("pymbrewclient.cli.initialize_brewery_client", return_value=mock_client),
            patch("threading.Event.wait", fake_wait),
        ):
            result = runner.invoke(
                app,
                [
                    "watch-device-logs",
                    "--username",
                    "user",
                    "--password",
                    "pass",
                    "--serial",
                    "SER-001",
                    "--format",
                    "json",
                    "--duration",
                    "0",
                ],
            )

        self.assertEqual(result.exit_code, 0, result.stdout)
        # Find the JSON object in stdout (there may be preceding non-JSON lines)
        decoder = json.JSONDecoder()
        json_start = result.stdout.find("{")
        self.assertGreater(json_start, -1, f"No JSON object found in: {result.stdout!r}")
        payload, _ = decoder.raw_decode(result.stdout, json_start)
        self.assertEqual(payload["device_uuid"], "SER-001")
        self.assertEqual(payload["session_id"], 1)
        self.assertEqual(payload["process_state"], 80)
        self.assertEqual(payload["payload"], b"\x08\x01".hex())

    def test_watch_device_logs_subscribes_all_serials(self) -> None:
        """Each --serial value is subscribed on the MQTT client."""
        runner = CliRunner()

        mock_mqtt = MagicMock()
        mock_mqtt.__enter__ = MagicMock(return_value=mock_mqtt)
        mock_mqtt.__exit__ = MagicMock(return_value=False)

        mock_client = MagicMock()
        mock_client.create_mqtt_client.return_value = mock_mqtt

        with (
            patch("pymbrewclient.cli.initialize_brewery_client", return_value=mock_client),
            patch("threading.Event.wait", return_value=True),
        ):
            result = runner.invoke(
                app,
                [
                    "watch-device-logs",
                    "--username",
                    "user",
                    "--password",
                    "pass",
                    "--serial",
                    "SER-001",
                    "--serial",
                    "SER-002",
                    "--duration",
                    "0",
                ],
            )

        self.assertEqual(result.exit_code, 0, result.stdout)
        subscribed = {call.args[0] for call in mock_mqtt.subscribe_device_logs.call_args_list}
        self.assertIn("SER-001", subscribed)
        self.assertIn("SER-002", subscribed)

    def test_serialize_output_converts_bytes_to_hex(self) -> None:
        from pymbrewclient.cli import serialize_output

        self.assertEqual(serialize_output(b"\xde\xad\xbe\xef"), "deadbeef")
        self.assertEqual(serialize_output(b""), "")
        result = serialize_output({"payload": b"\x01\x02"})
        self.assertEqual(result, {"payload": "0102"})


if __name__ == "__main__":
    unittest.main()
