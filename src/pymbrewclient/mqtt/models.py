# "Commons Clause" License Condition v1.0
#
# The Software is provided to you by the Licensor under the License, as defined below, subject to the following condition.
#
# Without limiting other conditions in the License, the grant of rights under the License will not include, and the License does not grant to you, the right to Sell the Software.
#
# For purposes of the foregoing, "Sell" means practicing any or all of the rights granted to you under the License to provide to third parties, for a fee or other consideration (including without limitation fees for hosting or consulting/ support services related to the Software), a product or service whose value derives, entirely or substantially, from the functionality of the Software. Any license notice or attribution required by the License must also include this Commons Clause License Condition notice.
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
Typed message models for the MiniBrew MQTT client.
"""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class MqttMessage:
    """A raw MQTT message received from the broker."""

    topic: str
    """The full MQTT topic the message was published on."""

    payload: bytes
    """The raw message payload bytes, always preserved."""

    received_at: datetime
    """Timezone-aware UTC datetime when this message was received by the client."""

    device_uuid: str | None = None
    """
    Device UUID extracted from the topic when the topic follows the
    ``devices/{message_type}/{device_uuid}`` pattern; ``None`` otherwise.
    """


@dataclass
class DeviceLogMessage:
    """
    A decoded MiniBrew device-log telemetry message from the
    ``devices/logs/{SerialNumber}`` MQTT topic.

    **Schema caveat**: MiniBrew's official ``.proto`` source
    (``minibrew/minibrew-protobuf``) is a private repository and is not
    publicly available.  The field numbers used for decoding were
    reconstructed from the MiniBrew REST API response structure and the
    community-maintained ``minibrew/enduser-docker-server`` project.
    Fields may be mapped to wrong values until the official schema is
    confirmed.  The raw :attr:`payload` is always retained.

    All decoded fields default to ``None`` when absent from the message
    or when decoding fails.
    """

    topic: str
    """The full MQTT topic."""

    payload: bytes
    """Raw protobuf bytes — always present regardless of decode success."""

    received_at: datetime
    """Timezone-aware UTC datetime when this message was received."""

    device_uuid: str | None = None
    """Device serial / UUID extracted from the topic path."""

    # --- Decoded telemetry fields ----------------------------------------

    sequence_number: int | None = None
    """Per-device message sequence number from live envelope field 1."""

    session_id: int | None = None
    """Active brewing session ID (live envelope field 4 or telemetry field 11)."""

    device_timestamp: datetime | None = None
    """
    Timezone-aware UTC datetime from the device's own clock
    (live envelope field 5 or telemetry field 1). Derived from Unix epoch milliseconds.
    """

    current_state: int | None = None
    """Current device-state integer (nested state field 1, observed)."""

    process_type: int | None = None
    """Process-type integer (nested state field 2, observed)."""

    process_state: int | None = None
    """
    Process-state integer (nested state field 3, observed).
    See ``PROCESS_STATE_LABELS`` in the MiniBrew community docs for a
    complete mapping (e.g. 80 → FERMENTATION_TEMP_CONTROL).
    """

    user_action: int | None = None
    """
    User-action state integer (nested state field 8, observed).
    See ``USER_ACTION_LABELS`` in the MiniBrew community docs.
    """

    current_temperature: float | None = None
    """Current temperature in °C (telemetry field 19, observed)."""

    target_temperature: float | None = None
    """Target temperature in °C (telemetry field 18, observed)."""

    wifi_rssi_dbm: float | None = None
    """Wi-Fi received signal strength in dBm (measurement ID 24, confirmed)."""

    seconds_until_next_action: int | None = None
    """Seconds until the next required user action (telemetry field 26, observed)."""

    next_action_at: datetime | None = None
    """
    Timezone-aware UTC datetime calculated from :attr:`device_timestamp` plus
    :attr:`seconds_until_next_action`.
    """

    decode_error: str | None = None
    """
    A brief description of any error encountered during protobuf decoding.
    When set, some or all decoded telemetry fields may be ``None``.
    The raw :attr:`payload` is unaffected.
    """

    raw_fields: dict[int, list[object]] = field(default_factory=dict)
    """
    Raw fields from the MQTT payload's outermost protobuf message.
    For live wrapped messages these are the envelope fields.
    """

    telemetry_fields: dict[int, list[object]] = field(default_factory=dict)
    """
    Raw fields from the decoded telemetry message. For an unwrapped telemetry
    payload this is equal to :attr:`raw_fields`; for a live envelope it is
    decoded from envelope field 3.
    """

    state_fields: dict[int, list[object]] = field(default_factory=dict)
    """
    Raw fields decoded from the nested state message in telemetry field 2.
    This preserves observed but not yet semantically identified state values.
    """

    measurements: dict[int, float] = field(default_factory=dict)
    """
    Measurement ID to float value from repeated telemetry field 3 entries.
    Confirmed IDs are also exposed as named fields; all readings remain here
    so unknown measurements are preserved.
    """
