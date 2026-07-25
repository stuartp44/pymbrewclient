# "Commons Clause" License Condition v1.0
#
# The Software is provided to you by the Licensor under the License, as defined below, subject to the following condition.
#
# Without limiting other conditions in the License, the grant of rights under the License will not include, and the License does not grant to you, the right to Sell the Software.
#
# For purposes of the foregoing, "Sell" means practicing any or all of the rights granted to you under the License to provide to third parties, for a fee or other consideration (including without limitation fees for hosting or consulting/ support services related to the Software"), a product or service whose value derives, entirely or substantially, from the functionality of the Software. Any license notice or attribution required by the License must also include this Commons Clause License Condition notice.
#
# Software: pymbrewclient
# License: MIT License
# Licensor: Stuart Pearson
#
#
# MIT License
#
# Copyright (c) 2024 Stuart Pearson
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#
# Disclaimer: This software is an independent project and is not affiliated with, endorsed by, or associated with MiniBrew. MiniBrew's trademarks, logos, API, and other intellectual property are owned by MiniBrew and are not included in this software. Users are responsible for complying with MiniBrew's terms of service when using this software.
"""
MQTT-over-WebSocket client for the MiniBrew Brewery Portal.

Security note
-------------
The MiniBrew REST API token is used as the MQTT password.  **Never log the
token**, include it in exception messages, or pass it to external systems.
This module takes care to keep the token out of ``__repr__``, log output,
and callback arguments.
"""

import logging
import threading
import uuid
from collections.abc import Callable
from datetime import datetime, timezone
from types import TracebackType
from typing import Any

import paho.mqtt.client as _paho

from .models import DeviceLogMessage, MqttMessage
from .proto import decode_device_log

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

BROKER_HOST: str = "broker.minibrew.io"
BROKER_PORT: int = 15675
WS_PATH: str = "/ws"
KEEPALIVE: int = 60
RECONNECT_DELAY: int = 5

_DEVICE_LOG_TOPIC_PREFIX = "devices/logs/"
_DEVICE_TOPIC_PREFIX_PARTS = ("devices",)


def _extract_device_uuid(topic: str) -> str | None:
    """Return the device UUID from a ``devices/{type}/{uuid}`` topic, or ``None``."""
    parts = topic.split("/")
    if len(parts) == 3 and parts[0] == "devices":
        return parts[2]
    return None


# ---------------------------------------------------------------------------
# Callback type aliases
# ---------------------------------------------------------------------------

ConnectedCallback = Callable[[], None]
DisconnectedCallback = Callable[[], None]
ReconnectingCallback = Callable[[], None]
ErrorCallback = Callable[[Exception], None]
RawMessageCallback = Callable[[MqttMessage], None]
DeviceLogCallback = Callable[[DeviceLogMessage], None]


# ---------------------------------------------------------------------------
# MqttClient
# ---------------------------------------------------------------------------


class MqttClient:
    """MQTT-over-WebSocket client for the MiniBrew Brewery Portal.

    Do not instantiate directly; use
    :meth:`~pymbrewclient.client.BreweryClient.create_mqtt_client` instead.

    Example::

        client = BreweryClient(username="you@example.com", ******)

        with client.create_mqtt_client() as mqtt:
            mqtt.on_connected(lambda: print("connected"))
            mqtt.subscribe_device_logs("7391Q4827-5NZC8R2M")

    .. warning::

        The MiniBrew REST API token is used as the MQTT password.
        **Do not log, print, or expose the MqttClient instance in contexts that
        would reveal the token.**  This class's ``__repr__`` deliberately omits
        sensitive fields.
    """

    def __init__(self, api_token: str, user_uuid: str) -> None:
        """
        :param api_token: A valid MiniBrew REST API token.  Used as the MQTT
            password.  **Never log this value.**
        :param user_uuid: The authenticated user's UUID, used to construct the
            MQTT username (``breweryportal-{user_uuid}``).
        """
        self._api_token = api_token  # intentionally private — never logged
        self._user_uuid = user_uuid

        self._client_uuid = str(uuid.uuid4())
        self._client_id = f"breweryportal-{self._client_uuid}"
        self._username = f"breweryportal-{self._user_uuid}"

        self._subscriptions: set[str] = set()
        self._subscription_lock = threading.Lock()

        self._connected = False
        self._ever_connected = False

        # Callbacks
        self._on_connected_callbacks: list[ConnectedCallback] = []
        self._on_disconnected_callbacks: list[DisconnectedCallback] = []
        self._on_reconnecting_callbacks: list[ReconnectingCallback] = []
        self._on_error_callbacks: list[ErrorCallback] = []
        self._on_raw_message_callbacks: list[RawMessageCallback] = []
        self._on_device_log_callbacks: list[DeviceLogCallback] = []

        self._paho_client = self._build_paho_client()

    # ------------------------------------------------------------------
    # Internal paho-mqtt construction
    # ------------------------------------------------------------------

    def _build_paho_client(self) -> _paho.Client:
        """Construct and configure the underlying paho-mqtt client."""
        will_topic = f"apps/lastwill/{self._client_id}"

        client = _paho.Client(
            callback_api_version=_paho.CallbackAPIVersion.VERSION2,
            client_id=self._client_id,
            protocol=_paho.MQTTv311,
            transport="websockets",
            clean_session=True,
        )
        client.ws_set_options(path=WS_PATH)
        client.tls_set()  # TLS with system CA bundle; certificate verification enabled
        client.username_pw_set(self._username, self._api_token)
        client.will_set(topic=will_topic, payload="offline", qos=0, retain=False)
        client.reconnect_delay_set(min_delay=RECONNECT_DELAY, max_delay=RECONNECT_DELAY)

        client.on_connect = self._on_paho_connect
        client.on_disconnect = self._on_paho_disconnect
        client.on_message = self._on_paho_message
        client.on_pre_connect = self._on_paho_pre_connect

        return client

    # ------------------------------------------------------------------
    # paho callbacks
    # ------------------------------------------------------------------

    def _on_paho_pre_connect(self, client: _paho.Client, userdata: Any) -> None:  # noqa: ANN401
        """Called by paho just before a (re)connection attempt."""
        if self._ever_connected:
            logger.debug("MQTT reconnecting to %s:%d", BROKER_HOST, BROKER_PORT)
            self._fire_reconnecting()

    def _on_paho_connect(
        self,
        client: _paho.Client,
        userdata: Any,  # noqa: ANN401
        connect_flags: _paho.ConnectFlags,
        reason_code: _paho.ReasonCode,
        properties: Any,  # noqa: ANN401
    ) -> None:
        """Called when paho establishes or re-establishes the connection."""
        if reason_code.is_failure:
            logger.warning("MQTT connect failed: %s", reason_code)
            self._fire_error(ConnectionError(f"MQTT connect failed: {reason_code}"))
            return

        logger.debug("MQTT connected (session_present=%s)", connect_flags.session_present)
        self._connected = True
        self._ever_connected = True

        # Resubscribe to all topics (handles reconnect + clean_session=True)
        with self._subscription_lock:
            topics = list(self._subscriptions)
        for topic in topics:
            logger.debug("MQTT resubscribing to %s", topic)
            client.subscribe(topic)

        self._fire_connected()

    def _on_paho_disconnect(
        self,
        client: _paho.Client,
        userdata: Any,  # noqa: ANN401
        disconnect_flags: _paho.DisconnectFlags,
        reason_code: _paho.ReasonCode,
        properties: Any,  # noqa: ANN401
    ) -> None:
        """Called when paho loses the connection."""
        self._connected = False
        logger.debug("MQTT disconnected: %s", reason_code)
        self._fire_disconnected()

    def _on_paho_message(self, client: _paho.Client, userdata: Any, msg: _paho.MQTTMessage) -> None:  # noqa: ANN401
        """Called for every incoming MQTT PUBLISH."""
        received_at = datetime.now(tz=timezone.utc)
        device_uuid = _extract_device_uuid(msg.topic)

        raw_msg = MqttMessage(
            topic=msg.topic,
            payload=bytes(msg.payload),
            received_at=received_at,
            device_uuid=device_uuid,
        )

        self._fire_raw_message(raw_msg)

        if msg.topic.startswith(_DEVICE_LOG_TOPIC_PREFIX):
            decoded = decode_device_log(raw_msg)
            if decoded.decode_error:
                logger.debug("MQTT device-log decode error on %s: %s", msg.topic, decoded.decode_error)
            self._fire_device_log(decoded)

    # ------------------------------------------------------------------
    # Callback firing helpers
    # ------------------------------------------------------------------

    def _fire_connected(self) -> None:
        for cb in self._on_connected_callbacks:
            try:
                cb()
            except Exception as exc:  # noqa: BLE001
                logger.debug("Exception in on_connected callback: %s", exc)

    def _fire_disconnected(self) -> None:
        for cb in self._on_disconnected_callbacks:
            try:
                cb()
            except Exception as exc:  # noqa: BLE001
                logger.debug("Exception in on_disconnected callback: %s", exc)

    def _fire_reconnecting(self) -> None:
        for cb in self._on_reconnecting_callbacks:
            try:
                cb()
            except Exception as exc:  # noqa: BLE001
                logger.debug("Exception in on_reconnecting callback: %s", exc)

    def _fire_error(self, error: Exception) -> None:
        for cb in self._on_error_callbacks:
            try:
                cb(error)
            except Exception as exc:  # noqa: BLE001
                logger.debug("Exception in on_error callback: %s", exc)

    def _fire_raw_message(self, msg: MqttMessage) -> None:
        for cb in self._on_raw_message_callbacks:
            try:
                cb(msg)
            except Exception as exc:  # noqa: BLE001
                logger.debug("Exception in on_message callback: %s", exc)

    def _fire_device_log(self, msg: DeviceLogMessage) -> None:
        for cb in self._on_device_log_callbacks:
            try:
                cb(msg)
            except Exception as exc:  # noqa: BLE001
                logger.debug("Exception in on_device_log callback: %s", exc)

    # ------------------------------------------------------------------
    # Public connection API
    # ------------------------------------------------------------------

    def connect(self) -> None:
        """Open the WebSocket connection to the MiniBrew MQTT broker.

        Starts a background network thread.  Returns immediately; connection
        events are delivered via :meth:`on_connected` / :meth:`on_disconnected`
        callbacks.
        """
        logger.debug("MQTT connecting to %s:%d%s", BROKER_HOST, BROKER_PORT, WS_PATH)
        self._paho_client.connect(host=BROKER_HOST, port=BROKER_PORT, keepalive=KEEPALIVE)
        self._paho_client.loop_start()

    def disconnect(self) -> None:
        """Disconnect from the broker and stop the background network thread.

        Safe to call even when not connected.
        """
        logger.debug("MQTT disconnecting")
        self._paho_client.disconnect()
        self._paho_client.loop_stop()
        self._connected = False

    # ------------------------------------------------------------------
    # Subscription API
    # ------------------------------------------------------------------

    def subscribe(self, topic: str, qos: int = 0) -> None:
        """Subscribe to an arbitrary MQTT topic.

        The topic is remembered and resubscribed automatically after each
        reconnect.

        :param topic: Full MQTT topic string (wildcards ``+`` and ``#`` are
            supported).
        :param qos: Quality of Service level (0 or 1).
        """
        with self._subscription_lock:
            self._subscriptions.add(topic)
        if self._connected:
            self._paho_client.subscribe(topic, qos=qos)
        logger.debug("MQTT subscribed to %s (qos=%d)", topic, qos)

    def unsubscribe(self, topic: str) -> None:
        """Unsubscribe from an arbitrary MQTT topic.

        The topic is also removed from the auto-resubscribe set.

        :param topic: Full MQTT topic string, as previously passed to
            :meth:`subscribe`.
        """
        with self._subscription_lock:
            self._subscriptions.discard(topic)
        if self._connected:
            self._paho_client.unsubscribe(topic)
        logger.debug("MQTT unsubscribed from %s", topic)

    @staticmethod
    def device_log_topic(device_uuid: str) -> str:
        """Return the ``devices/logs/{device_uuid}`` topic for a device.

        :param device_uuid: Device serial number or UUID.
        """
        return f"{_DEVICE_LOG_TOPIC_PREFIX}{device_uuid}"

    def subscribe_device_logs(self, device_uuid: str, qos: int = 0) -> None:
        """Subscribe to real-time telemetry logs for a specific device.

        Incoming messages are delivered as :class:`~pymbrewclient.mqtt.models.DeviceLogMessage`
        instances to callbacks registered with :meth:`on_device_log`.

        :param device_uuid: Device serial number or UUID (e.g. ``"7391Q4827-5NZC8R2M"``).
        :param qos: Quality of Service level (0 or 1).
        """
        self.subscribe(self.device_log_topic(device_uuid), qos=qos)

    def unsubscribe_device_logs(self, device_uuid: str) -> None:
        """Unsubscribe from device log telemetry for a specific device.

        :param device_uuid: Device serial number or UUID.
        """
        self.unsubscribe(self.device_log_topic(device_uuid))

    # ------------------------------------------------------------------
    # Callback registration
    # ------------------------------------------------------------------

    def on_connected(self, callback: ConnectedCallback) -> None:
        """Register a callback invoked when the connection is established.

        For reconnect events the callback fires after all subscriptions are
        restored.

        :param callback: A zero-argument callable.
        """
        self._on_connected_callbacks.append(callback)

    def on_disconnected(self, callback: DisconnectedCallback) -> None:
        """Register a callback invoked when the connection is lost.

        :param callback: A zero-argument callable.
        """
        self._on_disconnected_callbacks.append(callback)

    def on_reconnecting(self, callback: ReconnectingCallback) -> None:
        """Register a callback invoked just before a reconnection attempt.

        :param callback: A zero-argument callable.
        """
        self._on_reconnecting_callbacks.append(callback)

    def on_error(self, callback: ErrorCallback) -> None:
        """Register a callback invoked when a connection-level error occurs.

        The callback receives the exception as its sole argument.  The token
        is never included in the exception object.

        :param callback: A callable accepting one :class:`Exception` argument.
        """
        self._on_error_callbacks.append(callback)

    def on_message(self, callback: RawMessageCallback) -> None:
        """Register a callback invoked for every incoming MQTT message.

        The callback receives a :class:`~pymbrewclient.mqtt.models.MqttMessage`
        containing the raw payload bytes.

        :param callback: A callable accepting one
            :class:`~pymbrewclient.mqtt.models.MqttMessage` argument.
        """
        self._on_raw_message_callbacks.append(callback)

    def on_device_log(self, callback: DeviceLogCallback) -> None:
        """Register a callback invoked for decoded device-log messages.

        The callback receives a :class:`~pymbrewclient.mqtt.models.DeviceLogMessage`.
        If decoding fails, ``decode_error`` is set on the message; the raw
        payload is always preserved.

        :param callback: A callable accepting one
            :class:`~pymbrewclient.mqtt.models.DeviceLogMessage` argument.
        """
        self._on_device_log_callbacks.append(callback)

    # ------------------------------------------------------------------
    # Context manager
    # ------------------------------------------------------------------

    def __enter__(self) -> "MqttClient":
        self.connect()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self.disconnect()

    # ------------------------------------------------------------------
    # Representation — token intentionally excluded
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return (
            f"MqttClient("
            f"client_id={self._client_id!r}, "
            f"username={self._username!r}, "
            f"broker={BROKER_HOST!r}:{BROKER_PORT}, "
            f"connected={self._connected!r}"
            f")"
        )
