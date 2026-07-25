from collections.abc import Callable
from datetime import datetime, timezone
import logging
import uuid

import paho.mqtt.client as mqtt

from pymbrewclient.rest.client import RestApiClient

from .models import MqttMessage
from .protobuf import ProtobufDecodeError, decode_device_log_payload

logger = logging.getLogger(__name__)

OnConnectedCallback = Callable[[], None]
OnDisconnectedCallback = Callable[[int], None]
OnReconnectingCallback = Callable[[int], None]
OnErrorCallback = Callable[[str], None]
OnMessageCallback = Callable[[MqttMessage], None]


class MiniBrewMqttClient:
    broker_host = "broker.minibrew.io"
    broker_port = 15675
    websocket_path = "/ws"
    keepalive = 60
    reconnect_delay_seconds = 5

    def __init__(
        self,
        rest_client: RestApiClient,
        mqtt_client_factory: Callable[..., mqtt.Client] = mqtt.Client,
    ) -> None:
        self._rest_client = rest_client
        self._mqtt_client_factory = mqtt_client_factory
        self._client_uuid_obj = uuid.uuid4()
        self.client_id = f"breweryportal-{self._client_uuid_obj}"
        self._mqtt_client = self._build_mqtt_client()
        self._subscriptions: dict[str, int] = {}
        self._has_connected_once = False
        self._disconnecting = False

        self._on_connected: OnConnectedCallback | None = None
        self._on_disconnected: OnDisconnectedCallback | None = None
        self._on_reconnecting: OnReconnectingCallback | None = None
        self._on_error: OnErrorCallback | None = None
        self._on_message: OnMessageCallback | None = None

    def __enter__(self) -> "MiniBrewMqttClient":
        self.connect()
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.disconnect()

    def set_on_connected(self, callback: OnConnectedCallback | None) -> None:
        self._on_connected = callback

    def set_on_disconnected(self, callback: OnDisconnectedCallback | None) -> None:
        self._on_disconnected = callback

    def set_on_reconnecting(self, callback: OnReconnectingCallback | None) -> None:
        self._on_reconnecting = callback

    def set_on_error(self, callback: OnErrorCallback | None) -> None:
        self._on_error = callback

    def set_on_message(self, callback: OnMessageCallback | None) -> None:
        self._on_message = callback

    def connect(self) -> None:
        self._mqtt_client.connect(self.broker_host, self.broker_port, self.keepalive)
        self._mqtt_client.loop_start()

    def disconnect(self) -> None:
        self._disconnecting = True
        try:
            self._mqtt_client.disconnect()
            self._mqtt_client.loop_stop()
        finally:
            self._disconnecting = False

    def subscribe(self, topic: str, qos: int = 0) -> tuple[int, int | None]:
        result = self._mqtt_client.subscribe(topic, qos=qos)
        self._subscriptions[topic] = qos
        return result

    def unsubscribe(self, topic: str) -> tuple[int, int | None]:
        result = self._mqtt_client.unsubscribe(topic)
        self._subscriptions.pop(topic, None)
        return result

    def subscribe_device_logs(self, device_uuid: str, qos: int = 0) -> tuple[int, int | None]:
        topic = self.get_device_logs_topic(device_uuid)
        return self.subscribe(topic, qos=qos)

    @staticmethod
    def get_device_logs_topic(device_uuid: str) -> str:
        return f"devices/logs/{device_uuid}"

    def _build_mqtt_client(self) -> mqtt.Client:
        token = self._get_api_token()
        user_uuid = self._rest_client.get_user_profile().uuid
        username = f"breweryportal-{user_uuid}"

        mqtt_client = self._mqtt_client_factory(
            client_id=self.client_id,
            clean_session=True,
            protocol=mqtt.MQTTv311,
            transport="websockets",
        )
        mqtt_client.ws_set_options(path=self.websocket_path)
        mqtt_client.reconnect_delay_set(
            min_delay=self.reconnect_delay_seconds,
            max_delay=self.reconnect_delay_seconds,
        )
        mqtt_client.tls_set()
        mqtt_client.tls_insecure_set(False)
        mqtt_client.username_pw_set(username, token)
        mqtt_client.will_set(
            topic=f"apps/lastwill/{self.client_id}",
            payload=b"offline",
            qos=0,
            retain=False,
        )
        mqtt_client.on_connect = self._handle_connect
        mqtt_client.on_disconnect = self._handle_disconnect
        mqtt_client.on_message = self._handle_message
        return mqtt_client

    def _get_api_token(self) -> str:
        self._rest_client._ensure_token()
        token = self._rest_client.token
        if token is None:
            raise RuntimeError("Unable to initialize MQTT client authentication.")
        return token

    def _handle_connect(
        self,
        _client: mqtt.Client,
        _userdata: object,
        _flags: dict[str, int],
        rc: int,
        _properties: object = None,
    ) -> None:
        if rc != 0:
            self._emit_error("MQTT connection failed.")
            return

        is_reconnect = self._has_connected_once
        self._has_connected_once = True

        if is_reconnect:
            for topic, qos in self._subscriptions.items():
                self._mqtt_client.subscribe(topic, qos=qos)

        if self._on_connected is not None:
            self._safe_callback(self._on_connected)

    def _handle_disconnect(
        self,
        _client: mqtt.Client,
        _userdata: object,
        rc: int,
        _properties: object = None,
    ) -> None:
        if not self._disconnecting and rc != 0:
            if self._on_reconnecting is not None:
                self._safe_callback(self._on_reconnecting, rc)

        if self._on_disconnected is not None:
            self._safe_callback(self._on_disconnected, rc)

    def _handle_message(
        self,
        _client: mqtt.Client,
        _userdata: object,
        msg: mqtt.MQTTMessage,
    ) -> None:
        device_uuid = _extract_device_uuid_from_topic(msg.topic)
        message = MqttMessage(
            topic=msg.topic,
            payload=bytes(msg.payload),
            received_at=datetime.now(timezone.utc),
            device_uuid=device_uuid,
        )
        if device_uuid is not None:
            try:
                message.decoded_telemetry = decode_device_log_payload(message.payload)
            except ProtobufDecodeError as error:
                message.decoding_error = str(error)
                self._emit_error("MQTT message decode failed.")

        if self._on_message is not None:
            self._safe_callback(self._on_message, message)

    def _emit_error(self, message: str) -> None:
        if self._on_error is not None:
            self._safe_callback(self._on_error, message)

    @staticmethod
    def _safe_callback(callback: Callable[..., None], *args: object) -> None:
        try:
            callback(*args)
        except Exception:
            logger.exception("MQTT callback raised an unexpected error.")


def _extract_device_uuid_from_topic(topic: str) -> str | None:
    if not topic.startswith("devices/logs/"):
        return None
    suffix = topic.removeprefix("devices/logs/")
    return suffix or None
